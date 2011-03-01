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
        #next release
        release = releases[release]['next']


    return graphs
    # Create first graph
#    commit_graph = ccm_graph.create_graphs(releases[release])


