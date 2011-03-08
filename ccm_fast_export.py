#!/usr/bin/env python
# encoding: utf-8
"""
ccm_fast_export.py

Output Synergy data as git fast import/export format

Created by Aske Olsson 2011-02-23.
Copyright (c) 2011 Nokia. All rights reserved.
"""
import logging as logger
import time
from datetime import datetime
from copy import copy
from operator import itemgetter, attrgetter
from collections import deque
from pygraph.classes.digraph import digraph
from pygraph.algorithms.sorting import topological_sorting

def ccm_fast_export(releases, graphs):
    logger.basicConfig(filename='ccm_fast_export.log',level=logger.DEBUG)

    commit_lookup = {}
    #Start at initial release
    for k, v in releases.iteritems():
        if v['previous'] is None:
            release = k
            break
    logger.info("Starting at %s as initial release" %(release))

    #initial_release_time = time.mktime(releases[release]['created'].timetuple())
    initial_release_time = 0.0 # epoch for now since releases[release] has no 'created' key :(
    mark = 0

    files = []
    #Create the initial release
    for o in releases[release]['objects']:
        if o.get_type() != 'dir':
            mark = create_blob(o, get_mark(mark), release)
            files.append('M 100644 :'+str(mark) + ' ' + o.get_path())

    mark = get_mark(mark)
    commit_info = []
    commit_info.append('reset refs/tags/' + release)
    commit_info.append('commit refs/tags/' + release)
    commit_info.append('mark :' + str(mark))
    commit_info.append('author Nokia <nokia@nokia.com> ' + str(int(initial_release_time)) + " +0000")
    commit_info.append('committer Nokia <nokia@nokia.com> ' + str(int(initial_release_time)) + " +0000")
    commit_info.append('data 15')
    commit_info.append('Initial commit')
    commit_info.append('\n'.join(files))
    commit_info.append('')
    print '\n'.join(commit_info)

    logger.info("git-fast-import:\n%s" %('\n'.join(commit_info)))

    commit_lookup[release] = mark
    # do the following releases (graphs)
    release = releases[release]['next']
    while release:
        previous_release = releases[release]['previous']
        logger.info("Next release: %s" %(release))
        commit_graph = graphs[release]['commit']
        commit_graph = fix_orphan_nodes(commit_graph, previous_release)

        # Get the commits order
        commits = topological_sorting(commit_graph)

        # Fix the commits order list
        commits.remove(previous_release)
        commits.remove(release)

        for counter, commit in enumerate(commits):
            logger.info("Commit %i/%i" % (counter, len(commits)))

            # Create the references lists. It lists the parents of the commit
            reference = [commit_lookup[parent] for parent in commit_graph.incidents(commit)]

            if len(reference) > 1:
                # Merge commit
                mark = create_merge_commit(commit, release, releases, mark, reference, graphs)
            else:
                # Normal commit
                mark = create_commit(commit, release, releases, mark, reference, graphs)

            # Update the lookup table
            commit_lookup[commit] = mark

        print commit, commits, commit_lookup
        reference = [commit_lookup[parent] for parent in commit_graph.incidents(release)]
        mark, merge_commit = create_release_merge_commit(releases, release, get_mark(mark), reference)
        print '\n'.join(merge_commit)

        commit_lookup[release] = mark
        release = releases[release]['next']
        #release = None

    #reset to master
    reset = ['reset refs/heads/master']
    reset.append('from :' + str(mark))
    logger.info("git-fast-import:\n%s" %('\n'.join(reset)))
    print '\n'.join(reset)

def create_release_merge_commit(releases, release, mark, reference):
    msg = []
    msg.append('commit refs/tags/' + release)
    msg.append('mark :' + str(mark))
    msg.append('author %s <%s@nokia.com> ' % (releases[release]['author'], releases[release]['author']) + str(int(time.mktime(releases[release]['created'].timetuple()))) + " +0000")
    msg.append('committer %s <%s@nokia.com> ' % (releases[release]['author'], releases[release]['author']) + str(int(time.mktime(releases[release]['created'].timetuple()))) + " +0000")
    commit_msg = "Release " + release
    msg.append('data ' + str(len(commit_msg)))
    msg.append(commit_msg)
    msg.append('from :' + str(reference[0]))
    if len(reference) > 1:
        merge = ['merge :' + str(i) for i in reference[1:]]
        msg.append('\n'.join(merge))
    msg.append('')
    logger.info("git-fast-import MERGE-COMMIT:\n%s" %('\n'.join(msg)))
    return mark, msg

def create_merge_commit(n, release, releases, mark, reference, graphs):
    logger.info("Creating commit for %s" % n)
    object_lookup = {}

    objects = get_objects_from_graph(n, graphs[release]['task'], releases[release]['objects'])

    # Also add all the objects of the parents
    # TODO: I suspect proplems here
    for parent in graphs[release]['commit'].incidents(n):
        objects.extend(get_objects_from_graph(parent, graphs[release]['task'], releases[release]['objects']))

    # Get the correct task name so commit message can be filled
    task_name = get_task_object_from_splitted_task_name(n)
    task = find_task_in_release(task_name, releases[release]['tasks'])

    # Sort objects to get correct commit order, if multiple versions of one file is in in the task
    objects = reduce_objects_for_commit(objects)

    for o in objects:
        if not o.get_type() == 'dir':
            mark = create_blob(o, get_mark(mark), release)
            object_lookup[o.get_object_name()] = mark


    file_list = create_file_list(objects, object_lookup)
    mark, commit = make_commit_from_task(task, get_mark(mark), reference, release, file_list)
    print '\n'.join(commit)
    return mark

def create_commit(n, release, releases, mark, reference, graphs):
    logger.info("Creating commit for %s" %(n))
    object_lookup = {}
    # Find n in release
    if ':task:' in n:
        # It's a task
        logger.info("Task: %s" %(n))
        objects = get_objects_from_graph(n, graphs[release]['task'], releases[release]['objects'])
        # Get the correct task name so commit message can be filled
        task_name = get_task_object_from_splitted_task_name(n)
        task = find_task_in_release(task_name, releases[release]['tasks'])

        # sort objects to get correct commit order, if multiple versions of one file is in in the task
        objects = reduce_objects_for_commit(objects)
        for o in objects:
            if not o.get_type() == 'dir':
                mark = create_blob(o, get_mark(mark), release)
                object_lookup[o.get_object_name()] = mark


        file_list = create_file_list(objects, object_lookup)
        mark, commit = make_commit_from_task(task, get_mark(mark), reference, release, file_list)
        print '\n'.join(commit)
        return mark

    else:
        # It's a single object
        logger.info("Single Object: %s" %(n))
        o = get_object(n, releases[release]['objects'])
        if not o.get_type() == 'dir':
            mark = create_blob(o, get_mark(mark), release)
            object_lookup[o.get_object_name()] = mark

        file_list = create_file_list([o], object_lookup)
        mark, commit = make_commit_from_object(o, get_mark(mark), reference, release, file_list)
        print '\n'.join(commit)
        return mark

def make_commit_from_task(task, mark, reference, release, file_list):
    commit_info = []
    commit_info.append('commit refs/tags/' + release)
    commit_info.append('mark :' + str(mark))
    commit_info.append('author %s <%s@nokia.com> ' % (task.get_author(), task.get_author()) + str(int(time.mktime(task.get_complete_time().timetuple()))) + " +0000")
    commit_info.append('committer %s <%s@nokia.com> ' % (task.get_author(), task.get_author()) + str(int(time.mktime(task.get_complete_time().timetuple()))) + " +0000")
    commit_msg = create_commit_msg_from_task(task)
    commit_info.append('data ' + str(len(commit_msg)))
    commit_info.append(commit_msg)
    commit_info.append('from :' + str(reference[0]))
    if len(reference) > 1:
        merge = ['merge :' + str(i) for i in reference[1:]]
        commit_info.append('\n'.join(merge))
    commit_info.append(file_list)
    commit_info.append('')
    logger.info("git-fast-import COMMIT:\n%s" %('\n'.join(commit_info)))
    return mark, commit_info

def make_commit_from_object(o, mark, reference, release, file_list):
    commit_info = []
    commit_info.append('commit refs/tags/' + release)
    commit_info.append('mark :' + str(mark))
    commit_info.append('author %s <%s@nokia.com> ' % (o.get_author(), o.get_author()) + str(int(time.mktime(o.get_integrate_time().timetuple()))) + " +0000")
    commit_info.append('committer %s <%s@nokia.com> ' % (o.get_author(), o.get_author()) + str(int(time.mktime(o.get_integrate_time().timetuple()))) + " +0000")
    commit_msg = "Object not associated to task in release: " + o.get_object_name()
    commit_info.append('data ' + str(len(commit_msg)))
    commit_info.append(commit_msg)
    commit_info.append('from :' + str(reference[0]))
    if len(reference) > 1:
        merge = ['merge :' + str(i) for i in reference[1:]]
        commit_info.append('\n'.join(merge))
    commit_info.append(file_list)
    commit_info.append('')
    logger.info("git-fast-import COMMIT:\n%s" %('\n'.join(commit_info)))
    return mark, commit_info

def create_file_list(objects, lookup):
    l = []
    for o in objects:
        if o.get_type() != 'dir':
            #exe = '100755' if o.is_executable() else '100644'
            exe = '100644'
            l.append('M ' + exe + ' :' + str(lookup[o.get_object_name()]) + ' ' + o.get_path())
        else:
            #Get deleted items:
            deleted = o.get_dir_changes()['deleted']
            for d in deleted:
                l.append('D ' + o.get_path() + '/' + d)

    return '\n'.join(l)

def create_commit_msg_from_task(task):
    msg = []
    attr = task.get_attributes()
    msg.append(attr['task_synopsis'])

    msg.append('')
    insp = None
    for k, v in attr.iteritems():
        if k == 'task_synopsis':
            continue
        if k == 'inspection_task':
            insp = v.copy()
            continue
        if k == 'status_log':
            continue
        msg.append('<'+k+'>')
        msg.append(v.strip())
        msg.append('</'+k+'>')
        msg.append('')
    if insp:
        msg.append('<inspection information>')
        for k, v in insp.iteritems():
            if k == 'status_log':
                continue
            msg.append('<'+k+'>')
            msg.append(v.strip())
            msg.append('</'+k+'>')
            msg.append('')
        msg.append('</inspection information>')
    return '\n'.join(msg)

def find_task_in_release(task, tasks):
    for t in tasks:
        if t.get_object_name() == task:
            return t

def get_objects_from_task(task, objects):
    objs = []
    for o in task.get_objects():
        for obj in objects:
            if obj.get_object_name() == o:
                objs.append(obj)
                break
    return objs

def get_objects_from_graph(task, graph, objects):
    objs = []
    for o in graph.links(task):
        for obj in objects:
            if obj.get_object_name() == o:
                objs.append(obj)
                break
    return objs

def get_task_object_from_splitted_task_name(task):
    return task.rsplit('_')[0]

def reduce_objects_for_commit(objects):
    ret_val = []
    objs = {}
    for o in objects:
        key = o.get_name() + ':' + o.get_type() + ':' + o.get_instance()
        if key in objs.keys():
            objs[key].append(o)
        else:
            objs[key] = [o]

    for v in objs.values():
        o = sort_objects_by_integrate_time(v)
        ret_val.append(o.pop())

    return ret_val

def sort_objects_by_integrate_time(objects):
    #Sort first by integrate time, but also by version as several objects may be checked in at the same time (checkpoint->integrate).
    sorted_objects = sorted(objects, key=attrgetter('integrate_time', 'version'))
    return sorted_objects

def get_object(o, objects):
    for obj in objects:
        if obj.get_object_name() == o:
            return obj

def create_blob(obj, mark, release):
    blob =['blob']
    blob.append('mark :'+str(mark))
    fname = 'data/' + release + '/' + obj.get_object_name()
    #f = open(fname, 'rb')
    #content = f.read()
    #f.close()
    #length = len(content)
    #blob.append('data '+ str(length))
    #blob.append(content)
    print '\n'.join(blob)
    return mark

def fix_orphan_nodes(commit_graph, release):
    orphan_nodes = [node for node in commit_graph.nodes() if commit_graph.incidents(node) == []]
    [commit_graph.add_edge((release, node)) for node in orphan_nodes if node != release]
    return commit_graph

def get_mark(mark):
    mark +=1
    return mark


