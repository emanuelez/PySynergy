#!/usr/bin/env python
# encoding: utf-8
"""
ccm_history_to_graphs.py

Create commit graphs from ccm history pulled from Synergy via fetch-ccm-history.py

Created by Aske Olsson 2011-02-22.
Copyright (c) 2011 Nokia. All rights reserved.
"""

import FileObject
import TaskObject
import CCMHistoryGraph as ccm_graph
import pygraphviz as gv
from pygraphviz import *

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
        object_graph, task_graph, release_graph, commit_graph = ccm_graph.create_graphs(releases[release])
        graphs[release]['commit'] = commit_graph
        graphs[release]['task'] = task_graph
        graphs[release]['object'] = object_graph
        graphs[release]['release'] = release_graph

        #draw graphs:
        object_graph_to_image(object_graph, releases[release])
        task_graph_to_image(object_graph, task_graph, releases[release])
        release_graph_to_image(object_graph, release_graph, releases[release])
        commit_graph_to_image(commit_graph, releases[release], task_graph)
        #next release
        release = releases[release]['next']


    return graphs

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
    orphan_nodes = [node for node in commit_graph.nodes() if commit_graph.incidents(node) == []]
    [commit_graph.add_edge((release, node)) for node in orphan_nodes if node != release]
    return commit_graph
