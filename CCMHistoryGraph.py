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
import convert_history as ch

#class CCMHistoryGraph(object):
#    """ Create a graph object of tasks and objects from a ccm release"""
#    def __init(self, release):
#        pass

def find_objects_without_associated_tasks(objects, tasks):
    objects_from_tasks = []
    # compare objects in the tasks with objects in release, to see if there is any single objects
    objects_from_tasks = [o for task in tasks for o in task.get_objects()]
    single_objects = [o for o in objects if o.get_object_name() not in objects_from_tasks]
    return single_objects

def get_commit_history(release):
    commits = create_graphs(release)

    return commits

def create_graphs( release):
    tasks = release['tasks']
    objects = release['objects']

    object_graph = create_object_graph(objects)
    task_graph = create_task_graph(tasks, objects)
    release_graph = create_release_graph(objects, release['name'], release['previous']);
    commit_graph = ch.convert_history(object_graph, task_graph, release_graph, objects)

    return commit_graph


def create_release_graph(objects, release, previous):
    release_graph = hypergraph()
    release_graph.add_nodes([o.get_object_name() for o in objects])
    release_graph.add_edges([release, previous])

    object_names = [o.get_object_name() for o in objects]
    for o in objects:
        # Bind objects to this release
        if o.get_successors() is None:
            print "linking", o.get_object_name(), "to release", release
            release_graph.link(o.get_object_name(), release)

        # Bind objects to previous release
        predecessors = o.get_predecessors()
        for p in predecessors:
            if p not in object_names:
                if not release_graph.has_node(p):
                    release_graph.add_node(p)
                    print "linking", p, "to release", previous
                    release_graph.link(p, previous)

    return release_graph


def create_task_graph(tasks, objects):
    task_graph = hypergraph()
    task_graph.add_nodes([o.get_object_name() for o in objects])
    task_graph.add_hyperedges([t.get_object_name() for t in tasks])
    #link the objects and the tasks
    for t in tasks:
        for o in t.get_objects():
            print "linking:", o, "and", t.get_object_name()
            task_graph.link(o, t.get_object_name())
    # Add single_objects to task_graph
    for o in find_objects_without_associated_tasks(objects, tasks):
        task_graph.add_hyperedge(o.get_object_name())
        print "linking:", o.get_object_name(), "and", o.get_object_name()
        task_graph.link(o.get_object_name(), o.get_object_name())

    return task_graph


def create_object_graph(objects):
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
            object_graph.add_edge((obj, s.get_object_name()))

    object_names = [o.get_object_name() for o in objects]
    for o in objects:
        # Bind objects to previous release
        predecessors = o.get_predecessors()
        for p in predecessors:
            if p not in object_names:
                if not object_graph.has_node(p):
                    object_graph.add_node(p)
                    object_graph.add_edge((p,o.get_object_name()))

    return object_graph


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
