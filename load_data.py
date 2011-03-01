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


