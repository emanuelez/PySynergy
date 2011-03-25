#!/usr/bin/env python
# encoding: utf-8
"""
ccm_history_to_graphs.py

Create commit graphs from ccm history pulled from Synergy via fetch-ccm-history.py

Created by Aske Olsson and Emanuele Zattin 2011-02-22.
Copyright (c) 2011 Nokia. All rights reserved.
"""

import FileObject
import TaskObject
import pygraphviz as gv
import convert_history as ch
from pygraphviz import *
from pygraph.classes.digraph import digraph
from pygraph.classes.hypergraph import hypergraph

def create_graphs_from_releases(releases):
    # Find first release i.e. where previous is none
    for k, v in releases.iteritems():
        if v['previous'] is None:
            release = k
            break
    #print release, "is initial release, skipping graphing"
    release = releases[release]['next']

    graphs = {}
    while release:
        #print "Creating graph for", release
        graphs[release] = {}
        object_graph, task_graph, release_graph, commit_graph = create_graphs(releases[release])
        graphs[release]['commit'] = commit_graph
        graphs[release]['task'] = task_graph
        graphs[release]['object'] = object_graph
        graphs[release]['release'] = release_graph

        #draw graphs:
        #object_graph_to_image(object_graph, releases[release])
        #task_graph_to_image(object_graph, task_graph, releases[release])
        #release_graph_to_image(object_graph, release_graph, releases[release])
        #commit_graph_to_image(commit_graph, releases[release], task_graph)
        #next release
        release = releases[release]['next']


    return graphs


def find_objects_without_associated_tasks(objects, tasks):
    objects_from_tasks = []
    # compare objects in the tasks with objects in release, to see if there is any single objects
    object_names= set([o.get_object_name() for o in objects])
    objects_from_tasks = set([o for task in tasks for o in task.get_objects()])
    single_object_names = object_names - objects_from_tasks
    single_objects = [o for o in objects if o.get_object_name() in single_object_names]
    return single_objects

def get_commit_history(release):
    commits = create_graphs(release)

    return commits


def create_graphs(release):
    tasks = release['tasks']
    objects = release['objects']

    object_graph = create_object_graph(objects)
    object_graph_to_image(object_graph, release)

    task_graph = create_task_graph(tasks, objects)
    task_graph_to_image(object_graph, task_graph, release)

    release_graph = create_release_graph(objects, release['name'], release['previous']);
    release_graph_to_image(object_graph, release_graph, release)

    commit_graph = ch.convert_history(object_graph, task_graph, release_graph, objects)
    commit_graph_to_image(commit_graph, release, task_graph)

    return object_graph, task_graph, release_graph, commit_graph


def create_release_graph(objects, release, previous):
    release_graph = hypergraph()
    release_graph.add_nodes([o.get_object_name() for o in objects])
    release_graph.add_edges([release, previous])

    object_names = [o.get_object_name() for o in objects]
    for o in objects:
        # Bind objects to this release
        if o.get_successors() is None:
            #print "linking", o.get_object_name(), "to release", release
            release_graph.link(o.get_object_name(), release)

        # Bind objects to previous release
        predecessors = o.get_predecessors()
        if predecessors is not None:
            for p in predecessors:
                if p not in object_names:
                    if not release_graph.has_node(p):
                        release_graph.add_node(p)
                        #print "linking", p, "to release", previous
                        release_graph.link(p, previous)

    return release_graph


def create_task_graph(tasks, objects):
    task_graph = hypergraph()
    task_graph.add_nodes([o.get_object_name() for o in objects])
    task_graph.add_hyperedges([t.get_object_name() for t in tasks])
    #link the objects and the tasks
    for t in tasks:
        for o in t.get_objects():
            #print "linking:", o, "and", t.get_object_name()
            if t.get_object_name() not in task_graph.links(o):
                task_graph.link(o, t.get_object_name())
    # Add single_objects to task_graph
    for o in find_objects_without_associated_tasks(objects, tasks):
        task_graph.add_hyperedge(o.get_object_name())
        #print "linking:", o.get_object_name(), "and", o.get_object_name()
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
        if predecessors is not None:
            for p in predecessors:
                if p not in object_names:
                    if not object_graph.has_node(p):
                        object_graph.add_node(p)
                        object_graph.add_edge((p,o.get_object_name()))

    return object_graph


def object_graph_to_image(object_graph, release):

    G=gv.AGraph(strict=False,directed=True)
    G.node_attr['shape'] = 'box'
    G.graph_attr['rankdir'] = 'LR'

    G.add_nodes_from(object_graph.nodes())
    G.add_edges_from(object_graph.edges())

    G.layout(prog='dot')
    G.draw(release['name'] + "_objects.png", format='png')


def task_graph_to_image(object_graph, task_graph, release):
    G=gv.AGraph(directed=True)
    G.node_attr['shape'] = 'box'
    G.graph_attr['rankdir'] = 'LR'

    G.add_nodes_from(object_graph.nodes())
    G.add_edges_from(object_graph.edges())

    subgraphs = []
    #add subgraphs:
    for e in task_graph.edges():
        nodes = task_graph.links(e)
        G.add_subgraph(nbunch=nodes, name='cluster'+e, style='filled', color='lightgrey', label=e)

    G.layout(prog='dot')
    G.draw(release['name'] + "_tasks.png", format='png')
    #G.write(release['name'] + "_tasks.dot")


def release_graph_to_image(object_graph, release_graph, release):
    G=gv.AGraph(directed=True)
    G.node_attr['shape'] = 'box'
    G.graph_attr['rankdir'] = 'LR'

    G.add_nodes_from(object_graph.nodes())
    G.add_edges_from(object_graph.edges())

    #add subgraphs:
    i = 0
    for e in sorted(release_graph.edges()):
        nodes = release_graph.links(e)
        if not i:
            rank_attr = 'source'
        else:
            rank_attr = 'sink'
        G.add_subgraph(nbunch=nodes, name='cluster_'+e, style='filled', color='cornflowerblue', label=e)
        G.add_subgraph(nbunch=nodes, rank=rank_attr)
        i +=1

    G.layout(prog='dot')
    G.draw(release['name'] + "_release.png", format='png')
    #G.write(release['name'] + "_release.dot")


def commit_graph_to_image(commit_graph, release, task_graph):

    #first fix orphan_nodes:
    cgraph = fix_orphan_nodes(commit_graph, release['previous'])
    G=gv.AGraph(strict=False,directed=True)
    G.node_attr['shape'] = 'box'
    #G.node_attr['style'] = 'filled'
    G.graph_attr['rankdir'] = 'LR'

    # create nodes
    for n in cgraph.nodes():
        G.add_node(n)
        node = G.get_node(n)
        if "task" in n:
            label = create_label(n, release, task_graph)
            node.attr['label'] = label
        node.attr['shape'] = 'box'

    # create edges
    for e in cgraph.edges():
        G.add_edge(e)


    G.layout(prog='dot')
    G.draw(release['name'] + ".png", format='png')

def digraph_to_image(g, name):
    G = gv.AGraph(strict=False, directed=True)
    G.node_attr['shape'] = 'box'
    G.node_attr['rankdir'] = 'LR'

    for node in g.nodes():
        G.add_node(node)
        gv_node = G.get_node(node)
        gv_node.attr['label'] = node
        gv_node.attr['shape'] = 'box'

    for edge in g.edges():
        G.add_edge(edge)

    G.layout(prog='dot')
    G.draw("%s.png" % name, format='png')


def create_label(node, release, task_graph):
    l = ["Task: " + node]
    l.append("\\l")
    l.append("Objects:")
    l.append("\\l")
    for o in task_graph.links(node):
        l.append(o)
        l.append("\\l")

    return ''.join(l)


def fix_orphan_nodes(commit_graph, release):
    orphan_nodes = [node for node in commit_graph.nodes() if not commit_graph.incidents(node)]
    [commit_graph.add_edge((release, node)) for node in orphan_nodes if node != release]
    return commit_graph

