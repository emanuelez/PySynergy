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
from operator import attrgetter
from pygraph.classes.graph import graph
from pygraph.algorithms.sorting import topological_sorting
from pygraph.algorithms.accessibility import accessibility
from pygraph.algorithms.accessibility import cut_nodes
import convert_history as ch
import ccm_history_to_graphs as htg
import re

def ccm_fast_export(releases, graphs):
    global acn_ancestors
    logger.basicConfig(filename='ccm_fast_export.log',level=logger.DEBUG)

    commit_lookup = {}

    # Get the  initial release
    release = next((key for key, value in releases.iteritems() if not value['previous']))
    logger.info("Starting at %s as initial release" % release)

    #initial_release_time = time.mktime(releases[release]['created'].timetuple())
    initial_release_time = 0.0 # epoch for now since releases[release] has no 'created' key :(
    mark = 0

    files = []
    #Create the initial release
    for o in releases[release]['objects']:
        if o.get_type() != 'dir':
            mark = create_blob(o, get_mark(mark), release)
            for p in o.get_path():
                files.append('M 100644 :'+str(mark) + ' ' + p)

    empty_dirs = releases[release]['empty_dirs']
    logger.info("Empty dirs for release %s\n%s" %(release, empty_dirs))
    mark = create_blob_for_empty_dir(get_mark(mark))

    #file_list = create_file_list(objects, object_lookup, empty_dirs=empty_dirs, empty_dir_mark=mark)
    if empty_dirs:
        for d in empty_dirs:
            if mark:
                path = d + '/.gitignore'
                files.append('M 100644 :' + str(mark) + ' ' + path)

    mark = get_mark(mark)

    commit_info = ['reset refs/tags/' + release, 'commit refs/tags/' + release, 'mark :' + str(mark),
                   'author Nokia <nokia@nokia.com> ' + str(int(initial_release_time)) + " +0000",
                   'committer Nokia <nokia@nokia.com> ' + str(int(initial_release_time)) + " +0000", 'data 15',
                   'Initial commit', '\n'.join(files), '']
    print '\n'.join(commit_info)

    logger.info("git-fast-import:\n%s" %('\n'.join(commit_info)))

    commit_lookup[release] = mark
    # do the following releases (graphs)
    release = releases[release]['next']
    while release:
        previous_release = releases[release]['previous']

        logger.info("Next release: %s" % release)
        commit_graph = graphs[release]['commit']
        commit_graph = fix_orphan_nodes(commit_graph, previous_release)

        htg.digraph_to_image(commit_graph, "%s_before" % release)

        commit_graph = ch.spaghettify_digraph(commit_graph, previous_release, release)

        htg.digraph_to_image(commit_graph, "%s_after" % release)

        # Find the cutting nodes
        logger.info("Finding the cutting nodes")
        undirected = graph()
        undirected.add_nodes(commit_graph.nodes())
        [undirected.add_edge(edge) for edge in commit_graph.edges()]
        cutting_nodes = cut_nodes(undirected)
        del undirected

        # Create the reverse commit graph
        logger.info("Building the reverse commit graph")
        reverse_commit_graph = commit_graph.reverse()

        # Compute the accessibility matrix of the reverse commit graph
        logger.info("Compute the ancestors")
        ancestors = accessibility(reverse_commit_graph)
        del reverse_commit_graph

        logger.info("Ancestors of the release: %s" % str(ancestors[release]))

        # Clean up the ancestors matrix
        for k, v in ancestors.iteritems():
            if k in v:
                v.remove(k)

        # Get the commits order
        commits = topological_sorting(commit_graph)

        # Fix the commits order list
        commits.remove(previous_release)
        commits.remove(release)

        last_cutting_node = None

        # Check if the release (Synergy project has changed name, if it has the
        # 'base' directory name needs to be renamed
        if releases.has_key('delimiter'):
            delim = release['delimiter']
        else:
            delim = '-'
        previous_name = previous_release.split(delim)[0]
        current_name = release.split(delim)[0]
        if current_name != previous_name:
            logger.info("Name changed: %s -> %s" %(previous_name, current_name))
            mark, commit = rename_toplevel_dir(previous_name, current_name, release, releases, mark)
            print '\n'.join(commit)
            # adjust the commit lookup
            commit_lookup[previous_release] = mark

        for counter, commit in enumerate(commits):
            logger.info("Commit %i/%i" % (counter+1, len(commits)))

            acn_ancestors = []
            if last_cutting_node is not None:
                acn_ancestors = ancestors[last_cutting_node]

            # Create the references lists. It lists the parents of the commit
            reference = [commit_lookup[parent] for parent in ancestors[commit] if parent not in acn_ancestors]

            if len(reference) > 1:
                # Merge commit
                mark = create_merge_commit(commit, release, releases, mark, reference, graphs, set(ancestors[commit]) - set(acn_ancestors))
            else:
                # Normal commit
                mark = create_commit(commit, release, releases, mark, reference, graphs)

            # Update the lookup table
            commit_lookup[commit] = mark

            # Update the last cutting edge if necessary
            if commit in cutting_nodes:
                last_cutting_node = commit

        if last_cutting_node is not None:
            acn_ancestors = ancestors[last_cutting_node]

        reference = [commit_lookup[parent] for parent in ancestors[release] if parent not in acn_ancestors]
        mark, merge_commit = create_release_merge_commit(releases, release, get_mark(mark), reference, graphs, set(ancestors[release]) - set(acn_ancestors))
        print '\n'.join(merge_commit)

        commit_lookup[release] = mark
        release = releases[release]['next']
        #release = None

    #reset to master
    reset = ['reset refs/heads/master', 'from :' + str(mark)]
    logger.info("git-fast-import:\n%s" %('\n'.join(reset)))
    print '\n'.join(reset)

def create_release_merge_commit(releases, release, mark, reference, graphs, ancestors):
    object_lookup = {}
    objects = []

    logger.info("Ancestors: %i" % len(ancestors))

    # Also add all the objects of the parents
    for parent in ancestors:
        if parent in graphs[release]['task'].edges():
            logger.info("Parent %s is in the task hypergraph" % parent)
            synergy_objects = get_objects_from_graph(parent, graphs[release]['task'], releases[release]['objects'])
            logger.info("Synergy objects: %i" % len(synergy_objects))
            objects.extend(synergy_objects)

#    [objects.extend(get_objects_from_graph(parent, graphs[release]['task'], releases[release]['objects']))
#    for parent in ancestors
#    if parent in graphs[release]['task']]

    # Sort objects to get correct commit order, if multiple versions of one file is in in the task
    logger.info("Unfiltered objects: %i" % len(objects))

    objects = reduce_objects_for_commit(objects)

    logger.info("Filtered objects: %i" % len(objects))

    for o in objects:
        if not o.get_type() == 'dir':
            mark = create_blob(o, get_mark(mark), release)
            object_lookup[o.get_object_name()] = mark

    empty_dirs = releases[release]['empty_dirs']
    logger.info("Empty dirs for release %s\n%s" %(release, empty_dirs))
    mark = create_blob_for_empty_dir(get_mark(mark))

    logger.info("Object lookup: %i" % len(object_lookup))

    file_list = create_file_list(objects, object_lookup, empty_dirs=empty_dirs, empty_dir_mark=mark)

    logger.info("File list: %i" % len(file_list))

    msg = ['commit refs/tags/' + release, 'mark :' + str(mark)]
    if 'author' not in releases[release]:
        releases[release]['author'] = "Nobody"
    msg.append('author %s <%s@nokia.com> ' % (releases[release]['author'], releases[release]['author']) + str(int(time.mktime(releases[release]['created'].timetuple()))) + " +0000")
    msg.append('committer %s <%s@nokia.com> ' % (releases[release]['author'], releases[release]['author']) + str(int(time.mktime(releases[release]['created'].timetuple()))) + " +0000")

    commit_msg = "Release " + release
    msg.append('data ' + str(len(commit_msg)))
    msg.append(commit_msg)
    msg.append('from :' + str(reference[0]))
    if len(reference) > 1:
        merge = ['merge :' + str(i) for i in reference[1:]]
        msg.append('\n'.join(merge))
    if file_list:
        msg.append(file_list)
    if msg[-1] != '':
        msg.append('')
    logger.info("git-fast-import RELEASE-MERGE-COMMIT:\n%s" %('\n'.join(msg)))
    return mark, msg

def create_merge_commit(n, release, releases, mark, reference, graphs, ancestors):
    global task, single_object
    logger.info("Creating commit for %s" % n)
    object_lookup = {}

    objects = get_objects_from_graph(n, graphs[release]['task'], releases[release]['objects'])

    # Also add all the objects of the parents
    [objects.extend(get_objects_from_graph(parent, graphs[release]['task'], releases[release]['objects']))
    for parent in ancestors
    if parent in graphs[release]['task'].edges()]

    object_names = ', '.join(sorted([o.get_object_name() for o in objects]))

    logger.info("Objects from graph\n%s" % object_names)

    if ':task:' in n:
        # Get the correct task name so commit message can be filled
        task_name = get_task_object_from_splitted_task_name(n)
        if len(task_name) > 1:
            # Use the first task, TODO use both
            task_name = task_name[0]
        else:
            task_name = task_name[0]
        task = find_task_in_release(task_name, releases[release]['tasks'])

    else:
        # It's a single object
        logger.info("Single Object: %s" % n)
        single_object = get_object(n, releases[release]['objects'])
        logger.info("Single object from graph\n%s" % single_object.get_object_name())
        objects.append(single_object)

    # Sort objects to get correct commit order, if multiple versions of one file is in in the task
    objects = reduce_objects_for_commit(objects)

    for o in objects:
        if not o.get_type() == 'dir':
            mark = create_blob(o, get_mark(mark), release)
            object_lookup[o.get_object_name()] = mark


    file_list = create_file_list(objects, object_lookup)

    if ':task:' in n:
        mark, commit = make_commit_from_task(task, get_mark(mark), reference, release, file_list)
    else:
        mark, commit = make_commit_from_object(single_object, get_mark(mark), reference, release, file_list)

    print '\n'.join(commit)
    return mark

def create_commit(n, release, releases, mark, reference, graphs):
    logger.info("Creating commit for %s" % n)
    object_lookup = {}
    # Find n in release
    if ':task:' in n:
        # It's a task
        logger.info("Task: %s" % n)
        objects = get_objects_from_graph(n, graphs[release]['task'], releases[release]['objects'])
        # Get the correct task name so commit message can be filled
        task_name = get_task_object_from_splitted_task_name(n)
        if len(task_name) > 1:
            # Use the first task, TODO use both
            task_name = task_name[0]
        else:
            task_name = task_name[0]
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
        logger.info("Single Object: %s" % n)
        single_object = get_object(n, releases[release]['objects'])
        if not single_object.get_type() == 'dir':
            mark = create_blob(single_object, get_mark(mark), release)
            object_lookup[single_object.get_object_name()] = mark

        file_list = create_file_list([single_object], object_lookup)
        mark, commit = make_commit_from_object(single_object, get_mark(mark), reference, release, file_list)
        print '\n'.join(commit)
        return mark

def make_commit_from_task(task, mark, reference, release, file_list):
    commit_info = ['commit refs/tags/' + release, 'mark :' + str(mark),
                   'author %s <%s@nokia.com> ' % (task.get_author(), task.get_author()) + str(
                       int(time.mktime(task.get_complete_time().timetuple()))) + " +0000",
                   'committer %s <%s@nokia.com> ' % (task.get_author(), task.get_author()) + str(
                       int(time.mktime(task.get_complete_time().timetuple()))) + " +0000"]
    commit_msg = create_commit_msg_from_task(task)
    commit_info.append('data ' + str(len(commit_msg)))
    commit_info.append(commit_msg)
    commit_info.append('from :' + str(reference[0]))
    if len(reference) > 1:
        merge = ['merge :' + str(i) for i in reference[1:]]
        commit_info.append('\n'.join(merge))
    if file_list:
        commit_info.append(file_list)
    commit_info.append('')
    logger.info("git-fast-import COMMIT:\n%s" %('\n'.join(commit_info)))
    return mark, commit_info

def make_commit_from_object(o, mark, reference, release, file_list):
    commit_info = ['commit refs/tags/' + release, 'mark :' + str(mark),
                   'author %s <%s@nokia.com> ' % (o.get_author(), o.get_author()) + str(
                       int(time.mktime(o.get_integrate_time().timetuple()))) + " +0000",
                   'committer %s <%s@nokia.com> ' % (o.get_author(), o.get_author()) + str(
                       int(time.mktime(o.get_integrate_time().timetuple()))) + " +0000"]
    commit_msg = "Object not associated to task in release: " + o.get_object_name()
    commit_info.append('data ' + str(len(commit_msg)))
    commit_info.append(commit_msg)
    commit_info.append('from :' + str(reference[0]))
    if len(reference) > 1:
        merge = ['merge :' + str(i) for i in reference[1:]]
        commit_info.append('\n'.join(merge))
    if file_list:
        commit_info.append(file_list)
    commit_info.append('')
    logger.info("git-fast-import COMMIT:\n%s" %('\n'.join(commit_info)))
    return mark, commit_info

def create_file_list(objects, lookup, empty_dirs=None, empty_dir_mark=None):
    l = []
    for o in objects:
        if o.get_type() != 'dir':
            #exe = '100755' if o.is_executable() else '100644'
            exe = '100644'
            for p in o.get_path():
                l.append('M ' + exe + ' :' + str(lookup[o.get_object_name()]) + ' ' + p)
        else:
            #Get deleted items
            if o.get_dir_changes():
                deleted = o.get_dir_changes()['deleted']
                for d in deleted:
                    for p in o.get_path():
                        # p is the path of the directory
                        l.append('D ' + p + '/' + d)

    if empty_dirs:
        for d in empty_dirs:
            if empty_dir_mark:
                path = d + '/.gitignore'
                l.append('M 100644 :' + str(empty_dir_mark) + ' ' + path)

    if not l:
        return None
    return '\n'.join(l)

def create_commit_msg_from_task(task):
    msg = []
    attr = task.get_attributes()

    #Do Task synopsis and description first
    if attr.has_key('task_synopsis'):
        msg.append('Synergy-synopsis: %s' %attr['task_synopsis'].strip())
        msg.append('')
    if attr.has_key('task_description'):
        if not attr['task_description'].strip() == "":
            msg.append('Synergy-description: %s' %attr['task_description'].strip())
            msg.append('')

    insp = None
    for k, v in attr.iteritems():
        if k == 'task_synopsis':
            continue
        if k == 'task_description':
            continue
        if k == 'inspection_task':
            insp = v.copy()
            continue
        if k == 'status_log':
            continue
        if not len(v.strip()):
            continue
        msg.append('Synergy-'+k.replace('_', '-')+': '+v.strip().replace("\n", " "))
    if insp:
        for k, v in insp.iteritems():
            if k == 'status_log':
                continue
            if not len(v.strip()):
                continue
            k = k.replace('task_', '').replace('insp_', '').replace('_', '-')
            for line in v.splitlines():
                msg.append('Synergy-insp-%s: %s' % (k, line.rstrip()))
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
    # common task or splitted task
    if task.startswith('common'):
        # two tasks combined, strip common and split the tasks: common-task64827-1:task:ou1s40-task64849-1:task:ou1s40
        p = re.compile("common-(.*:task:.*)-(task.*)")
        m = p.match(task)
        if m:
            return [m.group(1), m.group(2)]
    else:
        #Splitted task
        return [task.rsplit('_')[0]]

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
    blob = ['blob', 'mark :' + str(mark)]
    fname = 'data/' + release + '/' + obj.get_object_name()
    f = open(fname, 'rb')
    content = f.read()
    f.close()
    length = len(content)
    blob.append('data '+ str(length))
    blob.append(content)
    print '\n'.join(blob)
    return mark

def create_blob_for_empty_dir(mark):
    blob = ['blob', 'mark :' + str(mark), 'data 0']
    print '\n'.join(blob)
    return mark

def rename_toplevel_dir(previous_name, current_name, release, releases, mark):

    from_mark = mark
    mark = get_mark(mark)
    logger.info("Commit for project name change: %s -> %s" %(previous_name, current_name))

    # Use the release author
    author = releases[release]['author']
    # Use the release time from previous release
    create_time = time.mktime(releases[releases[release]['previous']]['created'].timetuple())

    commit_info = ['commit refs/tags/' + release,
                   'mark :' + str(mark),
                   'author %s <%s@nokia.com> ' % (author, author) + str(int(create_time)) + " +0000",
                   'committer %s <%s@nokia.com> ' % (author, author) + str(int(create_time)) + " +0000"]
    commit_msg = 'Renamed toplevel directory to %s' % current_name
    commit_info.append('data ' + str(len(commit_msg)))
    commit_info.append(commit_msg)
    commit_info.append('from :' + str(from_mark))
    commit_info.append('R %s %s' %(previous_name, current_name))
    commit_info.append('')
    logger.info("git-fast-import NAME CHANGE COMMIT:\n%s" %('\n'.join(commit_info)))
    return mark, commit_info


def fix_orphan_nodes(commit_graph, release):
    orphan_nodes = [node for node in commit_graph.nodes() if commit_graph.incidents(node) == []]
    [commit_graph.add_edge((release, node)) for node in orphan_nodes if node != release]
    return commit_graph

def get_mark(mark):
    mark +=1
    return mark


