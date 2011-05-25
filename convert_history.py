#!/usr/bin/env python
# encoding: utf-8
"""
convert_history.py

Created by Emanuele Zattin on 2011-01-26.
Copyright (c) 2011, Nokia
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

Neither the name of the Nokia nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.    IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from itertools import product
from itertools import permutations
from itertools import combinations
from itertools import count
from pygraph.classes.digraph import digraph
from pygraph.classes.graph import graph
from pygraph.classes.hypergraph import hypergraph
from pygraph.algorithms.cycles import find_cycle
from pygraph.algorithms.critical import transitive_edges
from pygraph.algorithms.accessibility import mutual_accessibility
from pygraph.algorithms.accessibility import connected_components
import networkx as nx
import logging as log

def main():
    """A test method"""
    
    # The file history graph
    fh = digraph()

    fh.add_nodes(['F1-1', 'F1-2', 'F1-3', 'F1-4', 'F1-5', 'F1-6', 'F1-7'])
    fh.add_nodes(['F2-1', 'F2-2', 'F2-3', 'F2-4', 'F2-5', 'F2-6', 'F2-7', 'F2-8'])

    fh.add_edge(('F1-1', 'F1-2'))
    fh.add_edge(('F1-1', 'F1-3'))
    fh.add_edge(('F1-3', 'F1-4'))
    fh.add_edge(('F1-3', 'F1-6'))
    fh.add_edge(('F1-2', 'F1-5'))
    fh.add_edge(('F1-5', 'F1-6'))
    fh.add_edge(('F1-4', 'F1-7'))
    fh.add_edge(('F1-6', 'F1-7'))
    fh.add_edge(('F1-2', 'F1-4'))

    fh.add_edge(('F2-1', 'F2-2'))
    fh.add_edge(('F2-2', 'F2-3'))
    fh.add_edge(('F2-2', 'F2-4'))
    fh.add_edge(('F2-2', 'F2-5'))
    fh.add_edge(('F2-3', 'F2-7'))
    fh.add_edge(('F2-4', 'F2-6'))
    fh.add_edge(('F2-5', 'F2-6'))
    fh.add_edge(('F2-6', 'F2-8'))
    fh.add_edge(('F2-7', 'F2-8'))

    #print "File History graph ready."

    # The tasks hypergraph
    tasks = hypergraph()

    tasks.add_nodes(fh.nodes())

    tasks.add_edges(['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8'])

    tasks.link('F1-1', 'T1')
    tasks.link('F2-1', 'T2')
    tasks.link('F1-2', 'T3')
    tasks.link('F2-2', 'T3')
    tasks.link('F2-5', 'T3')
    tasks.link('F1-4', 'T3')
    tasks.link('F1-5', 'T4')
    tasks.link('F1-6', 'T4')
    tasks.link('F2-3', 'T4')
    tasks.link('F2-4', 'T5')
    tasks.link('F2-6', 'T5')
    tasks.link('F1-3', 'T6')
    tasks.link('F1-4', 'T6')
    tasks.link('F1-7', 'T7')
    tasks.link('F2-7', 'T3')
    tasks.link('F2-8', 'T8')

    #print "Tasks hypergraph ready."

    # The releases hypergraph
    releases = hypergraph()

    releases.add_nodes(fh.nodes())

    releases.add_edges(['R1', 'R2'])

    releases.link('F1-1', 'R1')
    releases.link('F2-1', 'R1')
    releases.link('F1-7', 'R2')
    releases.link('F2-8', 'R2')

    #print "Releases hypergraph ready."

    convert_history(fh, tasks, releases, None)

def convert_history(files, tasks, releases, fileobjects):
    """Converts the Synergy history between two releases to a Git compatible one."""
    
    log.basicConfig(filename='convert_history.log',level=log.DEBUG)    

    log.info("Looking for cycles in the File History graph")
    while find_cycle(files):
        cycle = find_cycle(files)
        log.info("\tA cycle was found!")
        log.info("\tCycle: %s" % ", ".join(cycle))

        # Find the newest file
        newest = max(cycle, key=lambda x: [fileobject.get_integrate_time() for fileobject in fileobjects if fileobject.get_objectname() == x][0])
        log.info("\tObject %s is the newest in the cycle: it should not have successors!" % newest)

        # Remove the outgoing link from the newest file
        for successor in files.neighbors(newest):
            if successor in cycle:
                files.del_edge((newest, successor))
                log.info("\tRemoved the %s -> %s edge" % (newest, successor))

    log.info("Remove transitive edges in the File History graph")
    for edge in transitive_edges(files):
        if edge in files.edges():
            files.del_edge(edge)
        else:
            log.warning("Weird, transitive edge not found!")

    log.info("Sanitize tasks")
    sanitized_tasks = _sanitize_tasks(tasks)

    log.info("Create commits graph")
    commits = create_commits_graph(files, sanitized_tasks, releases)

    #print "First commits graph created."

    log.info("Looking for cycles in the Commits graph")
    while find_cycle(commits):
        log.info("Finding strictly connected components")
        cycle = max(mutual_accessibility(commits).values(), key=len)

        #cycle = find_cycle(commits)

        log.info("\tA cycle was found!")
        log.info("\tCycle: %s" % ", ".join(cycle))
        
        log.info("Find the nodes in the cycle going from one task to another")
        culpript_edges = []
        for task in cycle:
            for obj in tasks.links(task):
                for neighbor in files.neighbors(obj):
                    if neighbor not in tasks.links(task) and tasks.links(neighbor)[0] in cycle:
                        culpript_edges.append((obj, neighbor))


        log.info("Connect the nodes found")
        culpript_nodes = set()
        for head, tail in culpript_edges:
            culpript_nodes.add(head)
            culpript_nodes.add(tail)
        for head, tail in permutations(culpript_nodes, 2):
            if tasks.links(head)[0] == tasks.links(tail)[0] and (head, tail) not in culpript_edges:
                log.info("\tAdding edge (%s, %s)" % (head, tail))
                culpript_edges.append((head, tail))

        reduced_digraph = digraph()
        reduced_digraph.add_nodes(culpript_nodes)
        [reduced_digraph.add_edge(edge) for edge in culpript_edges]

        shortest_cycle = max(mutual_accessibility(reduced_digraph).values(), key=len)
        log.info("Cycle in objects: %s" % shortest_cycle)

        candidate_cuts = []

        # Find the tasks
        t = set()
        for node in shortest_cycle:
            t.add(tasks.links(node)[0])
        log.info("T: %s" % str(t))

        for i in t:
            log.info("Cuts for task %s" % i)
            # Find the objects in the cycle belonging to task i
            obj_in_task = set(tasks.links(i)) & set(shortest_cycle)
            log.info("Objects in cycle and task: %s" % obj_in_task)
            if len(obj_in_task) > 1:
                for j in range(1, len(obj_in_task)/2+1):
                    candidate_cuts.extend([k for k in combinations(obj_in_task, j)])


        #for node1, node2 in zip(shortest_cycle, shortest_cycle[1:] + shortest_cycle[0:1]):
        #    # Find to which task the edge belongs to
        #    if tasks.links(node1) == tasks.links(node2):
        #        task = tasks.links(node1)[0]
        #        # Find which cuts are compatible and add them to the candidates list
        #        candidate_cuts.extend( [cut for cut in _find_cuts(tasks.links(task))
        #                if (node1 in cut and node2 not in cut)
        #                or (node2 in cut and node2 not in cut)])

        log.info("Candidate_cuts: %s" % str(candidate_cuts))

        for (counter, cut) in enumerate(candidate_cuts):
            log.info("Cut: %s" % cut)

            # Apply the cut
            task = tasks.links(cut[0])[0] # All the nodes in the cut belong to the same task and there are no overlapping tasks

            task_name = ""
            for i in count(1):
                task_name = task + "_" + str(i)
                if task_name not in tasks.edges():
                    log.info("Adding task %s" % task_name)
                    tasks.add_edge(task_name)
                    break

            for node in cut:
                log.info("Unlinking file %s from task %s" % (node, task))
                tasks.unlink(node, task)
                tasks.graph.del_edge(((node,'n'), (task,'h'))) # An ugly hack to work around a bug in pygraph
                log.info("Linking file %s to task %s" % (node, task_name))
                tasks.link(node, task_name)

            # If no more cycles are found in the updated reduced graph then break
            commits2 = create_commits_graph(files, tasks, releases)

            cycle2 = find_cycle(commits2)
            if set(cycle) & set(cycle2) == set(cycle):
                # Undo the changes!
                log.info("The cycle was not removed. Undoing changes...")
                log.info("\tDeleting task %s" % task_name)
                tasks.del_edge(task_name)

                for node in cut:
                    log.info("\tLinking file %s to task %s" % (node, task))
                    tasks.link(node, task)
                log.info("Done.")
            else:
                log.info("Cut found.")
                commits = create_commits_graph(files, tasks, releases)
                break
        else:
            # Error! This should not happen
            log.info("Cut not found.")
            raise Exception("Cut not found")

    else:
        log.info("No cycles found")

    return commits

def spaghettify_digraph(g, head, tail):
    original = digraph()
    original.add_nodes(g.nodes())
    [original.add_edge(edge) for edge in g.edges()]
    
    heads = set(original.neighbors(head))
    tails = set(original.incidents(tail))
    
    trimmed = _trim_digraph(original, head, tail)
    
    components = connected_components(trimmed)
    
    hc = {} # {[heads], component}
    tc = {} # {[tails], component}
    
    for component in set(components.values()):
        # Find the nodes in the component
        nodes = set([k for k, v in components.iteritems() if v == component])
        hc[frozenset(heads.intersection(nodes))] = component
        tc[frozenset(tails & nodes)] = component

    for component in xrange(1, len(hc)):
        current_heads = next((t for t, c in hc.iteritems() if c == component + 1))
        current_tails = next((t for t, c in tc.iteritems() if c == component))

        for current_head, current_tail in product(current_heads, current_tails):
            original.add_edge((current_tail, current_head))
            if (head, current_head) in original.edges():
                original.del_edge((head, current_head))
            if (current_tail, tail) in original.edges():
                original.del_edge((current_tail, tail))
            
    return original
    
def _trim_digraph(original, head, tail):
    result = graph()
    result.add_nodes(original.nodes())
    [result.add_edge(edge) for edge in original.edges()]
    
    result.del_node(head)
    result.del_node(tail)
    return result   

def _sanitize_tasks(tasks):
    common_objects = [(t1, t2, set(tasks.links(t1)) & set(tasks.links(t2)))
                      for (t1, t2) in combinations(tasks.edges(), 2)
                      if set(tasks.links(t1)) & set(tasks.links(t2))]

    for (t1, t2, common_objs) in common_objects:
        for obj in common_objs:
            tasks.unlink(obj, t1)
            tasks.unlink(obj, t2)
            
            [tasks.del_edge(t) for t in (t1, t2) if not tasks.links(t)]

            task_name = '-'.join(['common', t1, t2])
            tasks.add_edge(task_name)
            tasks.link(obj, task_name)

    return tasks

def _find_cuts(s):
    subsets = reduce(lambda z, x: z + [y + [x] for y in z], s, [[]])[1:-1]
    cuts = []
    [cuts.append(i) for i in subsets if _complementary_set(s, i) not in cuts]
    return cuts

def _complementary_set(s, ss):
    return list(set(s) - set(ss))

def create_commits_graph(files, tasks, releases):
    """Create a commits graph from files, tasks and releases"""
    commits = digraph()

    # Create the nodes
    #print "\tCreate the nodes..."
    #print "\t\tFrom the tasks"
    [commits.add_node(task) for task in tasks.edges()]
    #print "\t\tFrom the releases"
    [commits.add_node(release) for release in releases.edges()]

    # Create the edges from the tasks to the releases
    #print "\tCreate the nodes..."
    #print "\t\tFrom tasks to releases"
    [commits.add_edge((task, release)) for (release, task) in product(releases.edges(), tasks.edges()) if set(releases.links(release)) & set(tasks.links(task))]

    # Create the edges from the releases to the tasks
    #print "\t\tFrom releases to tasks"
    product_number = len(releases.edges()) * len(tasks.edges())
    for (counter, (release, task)) in enumerate(product(releases.edges(), tasks.edges())):
        log.info("Edge (%d/%d) from release %s to task %s" % (counter, product_number, release, task))
        [commits.add_edge((release, task))
         for obj_in_release
         in releases.links(release)
         if set(files.neighbors(obj_in_release)) & set(tasks.links(task))
         and not commits.has_edge((release, task))]

    # Create the edges from tasks to tasks and from releases to tasks
    #print "\t\tFrom tasks to tasks"
    for (counter, obj1) in enumerate(files.nodes()):
        log.info("From task to task: object %d/%d" % (counter, len(files.nodes())))
        if not tasks.has_node(obj1):
            # obj1 is the node belonging to the previous release
            continue
        task1 = tasks.links(obj1)[0]
        for obj2 in files.neighbors(obj1):
            task2 = tasks.links(obj2)[0]
            if not task1 == task2 and not commits.has_edge((task1, task2)):
                commits.add_edge((task1, task2))

    return commits

def _create_reduced_graph(files, tasks, cycle):
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


if __name__ == '__main__':
    main()

