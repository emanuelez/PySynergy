#!/usr/bin/env python
# encoding: utf-8
"""
ccm_history_to_graphs.py

Create commit graphs from ccm history pulled from Synergy via CCMHistory.py

Created by Aske Olsson and Emanuele Zattin 2011-02-22.
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
from _collections import deque
import cPickle
import pygraphviz as gv
import ccm_cache
import convert_history as ch
from pygraph.classes.digraph import digraph
from pygraph.classes.hypergraph import hypergraph

def create_graphs_from_releases(releases):
    # Find first release i.e. where previous is none
    release = None
    for k, v in releases.iteritems():
        if k == 'delimiter':
            continue
        if k == 'ccm_types':
            continue
        if v['previous'] is None:
            release = k
            break

    #print release, "is initial release, skipping graphing"
    release_queue = deque(releases[release]['next'])

    graphs = {}
    while release_queue:
        release = release_queue.popleft()
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

        #next release(s)
        release_queue.extend(releases[release]['next'])

    return graphs


def find_objects_without_associated_tasks(objects, tasks):
    # compare objects in the tasks with objects in release, to see if there is any single objects
    objects_from_tasks = set([o for task in tasks for o in task.get_objects()])
    single_objects = set(objects) - objects_from_tasks
    return single_objects

def get_commit_history(release):
    commits = create_graphs(release)

    return commits


def create_graphs(release):
    tasks = release['tasks']
    objects = release['objects']

    object_graph = create_object_graph(objects)
    task_graph = create_task_graph(tasks, objects)
    release_graph = create_release_graph(objects, release['name'], release['previous'])
    if print_graphs():
        object_graph_to_image(object_graph, release)
        task_graph_to_image(object_graph, task_graph, release)
        release_graph_to_image(object_graph, release_graph, release)

    commit_graph = ch.convert_history(object_graph, task_graph, release_graph, objects)
    if print_graphs():
        commit_graph_to_image(commit_graph, release, task_graph)

    return object_graph, task_graph, release_graph, commit_graph

def print_graphs():
    f = open('config.p', 'rb')
    config = cPickle.load(f)
    f.close()

    return config['print_graphs']

def create_release_graph(objects, release, previous):
    release_graph = hypergraph()
    release_graph.add_nodes(objects)
    release_graph.add_edges([release, previous])

    file_objects = [ccm_cache.get_object(o) for o in objects]
    for o in file_objects:
        link = True
        # Bind objects to this release
        successors = o.get_successors()
        if successors:
            for s in successors:
                if s not in release_graph.nodes():
                    link &= True
                else:
                    link &=False
        if link:
            if o.get_object_name() not in release_graph.links(release):
                release_graph.link(o.get_object_name(), release)

        # Bind objects to previous release
        predecessors = o.get_predecessors()
        if predecessors is not None:
            for p in predecessors:
                if p not in objects:
                    if not release_graph.has_node(p):
                        release_graph.add_node(p)
                        #print "linking", p, "to release", previous
                        release_graph.link(p, previous)

    return release_graph


def create_task_graph(tasks, objects):
    task_graph = hypergraph()
    task_graph.add_nodes(objects)
    task_graph.add_hyperedges([t.get_object_name() for t in tasks])
    #link the objects and the tasks
    for t in tasks:
        for o in t.get_objects():
            #print "linking:", o, "and", t.get_object_name()
            if t.get_object_name() not in task_graph.links(o):
                task_graph.link(o, t.get_object_name())
    # Add single_objects to task_graph
    for o in find_objects_without_associated_tasks(objects, tasks):
        task_graph.add_hyperedge(o)
        #print "linking:", o.get_object_name(), "and", o.get_object_name()
        task_graph.link(o, o)

    return task_graph


def create_object_graph(objects):

    object_graph = digraph()
    object_graph.add_nodes(objects)

    file_objects = []
    for o in objects:
        file_objects.append(ccm_cache.get_object(o))

    for o in file_objects:
        for p in o.get_predecessors():
            if not object_graph.has_node(p):
                object_graph.add_node(p)
    
    # Create relationship list
    for o in file_objects:
        # Bind objects to previous release
        predecessors = o.get_predecessors()
        if predecessors:
            for p in predecessors:
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


def commit_graph_to_image(commit_graph, release, task_graph, name=None):

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
            label = create_label(n, task_graph)
            node.attr['label'] = label
        node.attr['shape'] = 'box'

    # create edges
    for e in cgraph.edges():
        G.add_edge(e)


    G.layout(prog='dot')
    if not name:
        name = release['name']
    G.draw(name + ".png", format='png')

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


def create_label(node, task_graph):
    l = ["Task: %s" % node]
    l.append("\\l")
    l.append("Objects:")
    l.append("\\l")
    for o in task_graph.links(node):
        l.append(o)
        l.append("\\l")

    return ''.join(l)


def fix_orphan_nodes(commit_graph, release):
    new_graph = digraph()
    new_graph.add_nodes(commit_graph.nodes())
    [new_graph.add_edge(edge) for edge in commit_graph.edges()]
    orphan_nodes = [node for node in new_graph.nodes() if not new_graph.incidents(node)]
    [new_graph.add_edge((release, node)) for node in orphan_nodes if node != release]
    return new_graph

