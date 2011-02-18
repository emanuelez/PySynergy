# encoding: utf-8
"""
CCMHistoryGraph.py

Graph representation of Synergy History

Created by Aske Olsson 2010-12-10.
Copyright (c) 2010 Aske Olsson. All rights reserved.
"""

import FileObject
import TaskObject
import cPickle
from datetime import datetime
from operator import itemgetter, attrgetter
from itertools import product
from itertools import permutations
from itertools import combinations
from itertools import count
from pygraph.classes.digraph import digraph
from pygraph.classes.hypergraph import hypergraph
from pygraph.readwrite.dot import write
from pygraph.algorithms.cycles import find_cycle
from pygraph.algorithms.critical import transitive_edges
from pygraph.algorithms.accessibility import mutual_accessibility

class CCMHistoryGraph(object):
    """ Create a graph object of tasks and objects from a ccm release"""
    def __init(self, release):
        pass

    def find_objects_without_associated_tasks(self, objects, tasks):
        objects_from_tasks = []
        # compare objects in the tasks with objects in release, to see if there is any single objects
        objects_from_tasks = [o for task in tasks for o in task.get_objects()]
        single_objects = [o for o in objects if o not in objects_from_tasks]
        return single_objects

    def get_commit_history(self, release, previous_release)
        commits = self.create_graphs(release, previous_release)

        return commits

    def create_graphs(self, release, previous_release):
        tasks = release['tasks']
        objects = release['objects']

        object_graph = self.create_object_graph(objects)
        task_graph = self.create_task_graph(task, objects)
        release_graph = create_release_graph(objects, release['name'], release['previous');
        commit_graph = self.convert_history(object_graph, task_graph, release_graph)

        return commit_graph

    def convert_history(files, tasks, releases):
        """Converts the Synergy history between two releases to a Git compatible one."""

        [files.del_edge(edge) for i, edge in transitive_edges(files)]
        print "Removed transitive edges from the File History graph."

        tasks = sanitize_tasks(tasks)
        print "Tasks hypergraph sanitized."

        commits = create_commits_graph(files, tasks, releases)

        print "First commits graph created."

        # Cycles detection
        while find_cycle(commits):
            cycle = find_cycle(commits)
            print "Cycles found!"
            print "Cycle:", cycle

            # Generate the reduced file history graph
            reduced_graph = create_reduced_graph(files, tasks, cycle)
            print "Reduced graph:", reduced_graph

            # Find the longest cycle in the reduced graph
            longest_cycle = max(mutual_accessibility(reduced_graph).values(), key=len)

            candidate_cuts = []

            for edge in zip(longest_cycle, longest_cycle[1:] + longest_cycle[0:1]):
                node1, node2 = edge
                # Find to which task the edge belongs to
                if tasks.links(node1) == tasks.links(node2):
                    task = tasks.links(node1)[0]
                    # Find which cuts are compatible and add them to the candidates list
                    candidate_cuts.extend( [cut for cut in find_cuts(tasks.links(task))
                            if (node1 in cut and node2 not in cut)
                            or (node2 in cut and node2 not in cut)])

            print "Candidate_cuts:", candidate_cuts

            for (counter, cut) in enumerate(candidate_cuts):
                print "Cut:", cut

                # Apply the cut
                task = tasks.links(cut[0])[0] # All the nodes in the cut belong to the same task and there are no overlapping tasks

                task_name = ""
                for i in count(1):
                    task_name = task + "_" + str(i)
                    if task_name not in tasks.edges():
                        print "Adding task", task_name
                        tasks.add_edge(task_name)
                        break

                for node in cut:
                    print "Unlinking file %s from task %s" % (node, task)
                    tasks.unlink(node, task)
                    tasks.graph.del_edge(((node,'n'), (task,'h'))) # An ugly hack to work around a bug in pygraph
                    print "Linking file %s to task %s" % (node, task_name)
                    tasks.link(node, task_name)

                # If no more cycles are found in the updated reduced graph then break
                commits2 = create_commits_graph(files, tasks, releases)

                cycle2 = find_cycle(commits2)
                if set(cycle) & set(cycle2) == set(cycle):
                    # Undo the changes!
                    print "The cycle was not removed. Undoing changes..."
                    print "\tDeleting task", task_name
                    tasks.del_edge(task_name)

                    for node in cut:
                        print "\tLinking file %s to task %s" % (node, task)
                        tasks.link(node, task)
                    print "Done."
                else:
                    print "Cut found."
                    commits = create_commits_graph(files, tasks, releases)
                    break
            else:
                # Error! This should not happen
                print "Cut not found."

        else:
            print "No cycles found"

        return commits




    def sanitize_tasks(task_graph):
        common_objects = [(t1, t2, set(task_graph.links(t1)) & set(task_graph.links(t2)))
                          for (t1, t2) in combinations(task_graph.edges(), 2)
                          if set(task_graph.links(t1)) & set(task_graph.links(t2))]

        for (t1, t2, common_objs) in common_objects:
            for obj in common_objs:
                task_graph.unlink(obj, t1)
                task_graph.unlink(obj, t2)

                task_name = obj
                task_graph.add_edge(task_name)
                task_graph.link(obj, task_name)

        return tasks

    def create_reduced_graph(files, tasks, cycle):
        reduced = digraph()

        # Add the nodes
        [reduced.add_nodes(tasks.links(task)) for task in cycle]

        # Add the file history edges
        for node in reduced:
            for incident in files.incidents(node):
                if incident in reduced.nodes():
                    if (incident, node) not in reduced.edges():
                        reduced.add_edge((incident, node))

        # Add the tasks edges
        for node in reduced:
            task = tasks.links(node)[0]
            for node1, node2 in permutations(tasks.links(task),2):
                if (node1, node2) not in reduced.edges():
                    reduced.add_edge((node1, node2))

        return reduced

    def create_commits_graph(self, object_graph, task_graph, release_graph):
        commit_graph = digraph()

        #Create nodes
        [commit_graph.add_node(task) for task in task_graph.edges()]
        [commit_graph.add_node(release) for release in release_graph.edges()]

        # Create the edges from the tasks to the releases
        [commit_graph.add_edge((task, release)) for (release, task) in product(release_graph.edges(), task_graph.edges()) if set(release_graph.links(release)) & set(task_graph.links(task))]

        # Create the edges from tasks to tasks and from releases to tasks
        for (t1, t2) in [(t1, t2) for (t1, t2) in permutations(task_graph.edges(), 2)]:
            for (obj1, obj2) in [(obj1, obj2) for (obj1, obj2) in product(task_graph.links(t1), task_graph.links(t2)) if (obj1, obj2) in object_graph.edges()]:
                for release in release_graph.edges():
                    if commit_graph.has_edge((t1, release)):
                        if not commit_graph.has_edge((release, t2)):
                            commit_graph.add_edge((release, t2))
                        break
                else:
                    if not commit_graph.has_edge((t1, t2)):
                        commit_graph.add_edge((t1, t2))

        return commit_graph

    def create_release_graph(self, objects, release, previous):
        release_graph = hypergraph()
        release_graph.add_nodes([o.get_object_name() for o in objects])
        release_graph.add_edges([release, previous])

        object_names = [o.get_object_name() for o in objects]
        for o in objects:
            # Bind objects to this release
            if o.get_successors() is None:
                release_graph.link(o.get_object_name(), release)

            # Bind objects to previous release
            predecessors = o.get_predecessors()
            for p in predecessors:
                if p not in object_names:
                    release_graph.link(o.get_object_name(), previous)

        return release_graph


    def create_task_graph(self, tasks, objects):
        task_graph = hypergraph()
        task_graph.add_nodes([o.get_object_name() for o in objects])
        task_graph.add_hyperedges([t.get_object_name() for t in tasks])
        #link the objects and the tasks
        for t in tasks:
            for o in t.get_objects():
                task_graph.link(o, t.get_object_name())
        # Add single_objects to task_graph
        for o in self.find_objects_without_associated_tasks(objects, tasks):
            task_graph.add_hyperedge(o.get_object_name())
            task_graph.link(o.get_object_name(), o.get_object_name())

        return task_graph


    def create_object_graph(self, objects):
        # create dict to map objectname to file object
        mapped_objects = {}
        for o in objects:
            mapped_objects[o.get_object_name()] = o
        object_graph = digraph()
        object_graph.add_nodes([o.get_object_name() for o in objects])
        # Create relationship list
        successors = [(i.get_object_name(), [] if i.get_successors() is None else [mapped_objects[j] for j in i.get_successors()] ) for i in objects]
        #
        for obj, suc in successors:
            for s in suc:
                object_graph.add_edge((obj, s))

        return object_graph

    def find_cuts(s):
        subsets = reduce(lambda z, x: z + [y + [x] for y in z], s, [[]])[1:-1]
        cuts = []
        [cuts.append(i) for i in subsets if complementary_set(s, i) not in cuts]
        return cuts

    def complementary_set(s, ss):
        return list(set(s) - set(ss))

def main():
    #
    #print "Creating graph..."
    #graph = CCMHistoryGraph();
    #graph.create_graphs(release)
    f = open('history.p', 'rb')
    releases = cPickle.load(f)
    ccm_graph = CCMHistoryGraph()
    object_graph = ccm_graph.create_object_graph(releases['s30_11w03_sb9_fam']['objects'])
    task_graph = ccm_graph.create_task_graph(releases['s30_11w03_sb9_fam']['tasks'], releases['s30_11w03_sb9_fam']['objects'])

if __name__ == '__main__':
    main()
