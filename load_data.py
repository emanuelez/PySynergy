#!/usr/bin/env python
# encoding: utf-8
"""
load_data.py

Output Synergy data as git fast import/export format

Created by Aske Olsson 2011-02-23.
Copyright (c) 2011 Nokia. All rights reserved.
"""

import FileObject
import TaskObject
import cPickle
f = open('s30_hist.p', 'rb')
history = cPickle.load(f)
import CCMHistoryGraph
import convert_history as ch
import ccm_history_to_graphs as cg
import ccm_fast_export as cfe

cgraphs = cg.create_graphs_from_releases(history)

cfe.ccm_fast_export(history, cgraphs)


