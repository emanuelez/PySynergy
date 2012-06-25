#!/usr/bin/env python
# encoding: utf-8
"""
ccm_fast_export.py

Output Synergy data as git fast import/export format

Created by Aske Olsson 2011-02-23.
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
import logging as logger
from subprocess import Popen, PIPE
import time
from pygraph.classes.graph import graph
from pygraph.algorithms.sorting import topological_sorting
from pygraph.algorithms.accessibility import accessibility
from pygraph.algorithms.accessibility import cut_nodes
from SynergyObject import SynergyObject
import ccm_cache
import convert_history as ch
import ccm_history_to_graphs as htg
import re
from users import users

object_mark_lookup = {}
users

def ccm_fast_export(releases, graphs):
    global acn_ancestors
    global users
    users = users()
    logger.basicConfig(filename='ccm_fast_export.log',level=logger.DEBUG)

    commit_lookup = {}

    # Get the  initial release
    for k, v in releases.iteritems():
        if k == 'delimiter':
            continue
        if k == 'ccm_types':
            continue
        if v['previous'] is None:
            release = k
            break
    logger.info("Starting at %s as initial release" % release)

    if 'created' not in releases[release]:
        initial_release_time = 0.0 # epoch for now since releases[release] has no 'created' key :(
    else:
        initial_release_time = time.mktime(releases[release]['created'].timetuple())
    mark = 0

    files = []
    # Create the initial release
    # get all the file objects:
    file_objects = (ccm_cache.get_object(o) for o in releases[release]['objects'])
    project_obj = ccm_cache.get_object(releases[release]['fourpartname'])
    paths = project_obj.get_members()
    for o in file_objects:
        if o.get_type() != 'dir':
            object_mark, mark = create_blob(o, mark)
            for p in paths[o.get_object_name()]:
                files.append('M ' + releases['ccm_types']['permissions'][o.get_type()] + ' :'+str(object_mark) + ' ' + p)

    empty_dirs = releases[release]['empty_dirs']
    logger.info("Empty dirs for release %s\n%s" %(release, empty_dirs))
    mark = create_blob_for_empty_dir(get_mark(mark))

    #file_list = create_file_list(objects, object_lookup, releases['ccm_types'], empty_dirs=empty_dirs, empty_dir_mark=mark)
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

    tag_msg = 'Release: %s' %release
    annotated_tag = ['tag %s' % release,
               'from :%s' % str(mark),
               'tagger Nokia <nokia@nokia.com> ' + str(int(initial_release_time)) + " +0000",
               'data %s' % len(tag_msg),
               tag_msg]
    print '\n'.join(annotated_tag)
    
    commit_lookup[release] = mark
    # do the following releases (graphs)
    release_queue = deque(releases[release]['next'])
    while release_queue:
        release = release_queue.popleft()
        previous_release = releases[release]['previous']

        logger.info("Next release: %s" % release)
        commit_graph = graphs[release]['commit']
        commit_graph = fix_orphan_nodes(commit_graph, previous_release)

        commit_graph = ch.spaghettify_digraph(commit_graph, previous_release, release)

        #htg.commit_graph_to_image(commit_graph, releases[release], graphs[release]['task'], name=releases[release]['name']+'_after' )

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
            delim = releases['delimiter']
        else:
            delim = '-'
        previous_name = previous_release.split(delim)[0]
        current_name = release.split(delim)[0]
        if current_name != previous_name:
            logger.info("Name changed: %s -> %s" %(previous_name, current_name))
            from_mark = commit_lookup[previous_release]
            mark, commit = rename_toplevel_dir(previous_name, current_name, release, releases, mark, from_mark)
            print '\n'.join(commit)
            # adjust the commit lookup
            commit_lookup[previous_release] = mark

        for counter, commit in enumerate(commits):
            logger.info("Commit %i/%i" % (counter+1, len(commits)))

            acn_ancestors = []
            if last_cutting_node is not None:
                acn_ancestors = ancestors[last_cutting_node]

            # Create the references lists. It lists the parents of the commit
            #reference = [commit_lookup[parent] for parent in ancestors[commit] if parent not in acn_ancestors]
            reference = [commit_lookup[parent] for parent in commit_graph.incidents(commit)]

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
        logger.info("Reference %s" %str([parent for parent in ancestors[release] if parent not in acn_ancestors]))
        if not reference:
            logger.info("Reference previous %s, mark: %d" % (releases[release]['previous'], commit_lookup[releases[release]['previous']]))
            reference = [commit_lookup[ releases[release]['previous'] ] ]

        mark, merge_commit = create_release_merge_commit(releases, release, get_mark(mark), reference, graphs, set(ancestors[release]) - set(acn_ancestors))
        print '\n'.join(merge_commit)
        annotated_tag = create_annotated_tag(releases, release, mark)
        print '\n'.join(annotated_tag)

        commit_lookup[release] = mark
        release_queue.extend(releases[release]['next'])
        #release = releases[release]['next']
        #release = None

    #reset to master
    master = get_master_tag()
    reset = ['reset refs/heads/master', 'from :' + str(commit_lookup[master])]
    logger.info("git-fast-import:\n%s" %('\n'.join(reset)))
    print '\n'.join(reset)

def create_annotated_tag(releases, release, mark):
    global users
    tagger = users.get_user(releases[release]['author'])
    msg = 'Release: %s' %release
    tag_msg = ['tag %s' % release,
               'from :%s' % str(mark),
               'tagger %s <%s> ' % (tagger['name'], tagger['mail']) + str(int(time.mktime(releases[release]['created'].timetuple()))) + " +0000",
               'data %s' % len(msg),
               msg]

    return tag_msg

def create_release_merge_commit(releases, release, mark, reference, graphs, ancestors):
    global users
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
            object_mark, mark = create_blob(o, mark)
            object_lookup[o.get_object_name()] = object_mark

    empty_dirs = releases[release]['empty_dirs']
    logger.info("Empty dirs for release %s\n%s" %(release, empty_dirs))
    mark = create_blob_for_empty_dir(get_mark(mark))

    logger.info("Object lookup: %i" % len(object_lookup))
    file_list = create_file_list(objects, object_lookup, releases['ccm_types']['permissions'], releases[release]['fourpartname'], empty_dirs=empty_dirs, empty_dir_mark=mark, all_files_for_release=True)

    logger.info("File list: %i" % len(file_list))
    mark = get_mark(mark)
    msg = ['commit refs/tags/' + release, 'mark :' + str(mark)]
    if 'author' not in releases[release]:
        releases[release]['author'] = "Nobody"
    author = users.get_user(releases[release]['author'])
    msg.append('author %s <%s> ' % (author['name'], author['mail']) + str(int(time.mktime(releases[release]['created'].timetuple()))) + " +0000")
    msg.append('committer %s <%s> ' % (author['name'], author['mail']) + str(int(time.mktime(releases[release]['created'].timetuple()))) + " +0000")

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

    delimiter = objects[0].separator
    if ':task:' in n:
        # Get the correct task name so commit message can be filled
        task_name = get_task_object_from_splitted_task_name(n, delimiter)
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
            object_mark, mark = create_blob(o, mark)
            object_lookup[o.get_object_name()] = object_mark


    file_list = create_file_list(objects, object_lookup, releases['ccm_types']['permissions'], releases[release]['fourpartname'])

    if ':task:' in n:
        mark, commit = make_commit_from_task(task, n, get_mark(mark), reference, release, file_list)
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
        if not objects:
            delimiter = '-'
        else:
            delimiter = objects[0].separator
        # Get the correct task name so commit message can be filled
        task_name = get_task_object_from_splitted_task_name(n, delimiter)
        logger.info("Task name: %s" % task_name)
        task = find_task_in_release(task_name, releases[release]['tasks'])

        # sort objects to get correct commit order, if multiple versions of one file is in in the task
        objects = reduce_objects_for_commit(objects)
        for o in objects:
            if not o.get_type() == 'dir':
                object_mark, mark = create_blob(o, mark)
                object_lookup[o.get_object_name()] = object_mark


        file_list = create_file_list(objects, object_lookup, releases['ccm_types']['permissions'], releases[release]['fourpartname'])
        mark, commit = make_commit_from_task(task, n, get_mark(mark), reference, release, file_list)
        print '\n'.join(commit)
        return mark

    else:
        # It's a single object
        logger.info("Single Object: %s" % n)
        single_object = get_object(n, releases[release]['objects'])
        if not single_object.get_type() == 'dir':
            object_mark, mark = create_blob(single_object, mark)
            object_lookup[single_object.get_object_name()] = object_mark

        file_list = create_file_list([single_object], object_lookup, releases['ccm_types']['permissions'], releases[release]['fourpartname'])
        mark, commit = make_commit_from_object(single_object, get_mark(mark), reference, release, file_list)
        print '\n'.join(commit)
        return mark

def make_commit_from_task(task, task_name, mark, reference, release, file_list):
    global users
    # Use the first task for author, time etc...
    author = users.get_user(task[0].get_author())
    commit_info = ['commit refs/tags/' + release, 'mark :' + str(mark),
                   'author %s <%s> ' % (author['name'], author['mail']) + str(
                       int(time.mktime(task[0].get_complete_time().timetuple()))) + " +0000",
                   'committer %s <%s> ' % (author['name'], author['mail']) + str(
                       int(time.mktime(task[0].get_complete_time().timetuple()))) + " +0000"]
    commit_msg = create_commit_msg_from_task(task, task_name)
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
    global users
    author = users.get_user(o.get_author())
    commit_info = ['commit refs/tags/' + release, 'mark :' + str(mark),
                   'author %s <%s> ' % (author['name'], author['mail']) + str(
                       int(time.mktime(o.get_integrate_time().timetuple()))) + " +0000",
                   'committer %s <%s> ' % (author['name'], author['mail']) + str(
                       int(time.mktime(o.get_integrate_time().timetuple()))) + " +0000"]
    commit_msg = "Object not associated to task: " + o.get_object_name()
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

def create_file_list(objects, lookup, ccm_types, project, empty_dirs=None, empty_dir_mark=None, all_files_for_release=False):
    global object_mark_lookup
    project_object = ccm_cache.get_object(project)
    paths = project_object.get_members()
    l = []
    for o in objects:
        if o.get_type() != 'dir':
            perm = ccm_types[o.get_type()]
            object_paths = get_object_paths(o, paths)
            for p in object_paths:
                l.append('M ' + perm + ' :' + str(lookup[o.get_object_name()]) + ' ' + p)
        else:
            #Get deleted items
            deleted = o.get_deleted_objects()
            if deleted:
                for d in deleted:
                    object_paths = get_object_paths(o, paths)
                    for p in object_paths:
                        # p is the path of the directory
                        if d.endswith('/'):
                            tmp = d.rsplit('/', 1)[0]
                        else:
                            tmp = d
                        l.append('D ' + p + '/' + tmp)

    if all_files_for_release:
        # delete top level dir first:
        l.append('D ' + project_object.name)
        # Insert all files in the release
        logger.info("Loading all objects for %s"  %project_object.get_object_name())
        for object, paths in project_object.members.iteritems():
            if not ':dir:' in object and not ':project:' in object:
                perm = ccm_types[object.split(':')[1]]
                for p in paths:
                    l.append('M ' + perm + ' :' + str(object_mark_lookup[object]) + ' ' + p)

    if empty_dirs:
        for d in empty_dirs:
            if empty_dir_mark:
                path = d + '/.gitignore'
                l.append('M 100644 :' + str(empty_dir_mark) + ' ' + path)

    if not l:
        return []
    return '\n'.join(l)

def get_object_paths(object, project_paths):
    if project_paths.has_key(object.get_object_name()):
        return project_paths[object.get_object_name()]
    path = get_path_of_object_in_release(object, project_paths)
    return path

def get_path_of_object_in_release(object, project_paths):
    logger.info("Finding path of %s" %object.get_object_name())
    for k, v in project_paths.iteritems():
        if k.startswith(object.name):
            logger.info("Found similar object %s" % k)
            # Check if three part name matches:
            tmp = SynergyObject(k, object.separator)
            if object.name == tmp.name and object.type == tmp.type and object.instance == tmp.instance:
                logger.info("Path of %s: %s" % (object.get_object_name(), ','.join(v)))
                # Must be this object
                return v
    logger.info("No path found for %s" % object.get_object_name())
    return []

def create_commit_msg_from_task(tasks, task_name):
    msg = []
    logger.info("TASKNAME: %s" %task_name)
    if len(tasks) > 1:
        msg.append("Multiple tasks: %s\n" %', '.join([t.get_display_name() for t in tasks]))
    if '_TASKSPLIT_' in task_name:
        split = task_name.split('_TASKSPLIT_')[1]
        msg.append("Task %s split %s\n" %(tasks[0].get_display_name(), split ))
    for task in tasks:
        attr = task.get_attributes()

        #Do Task synopsis and description first
        if attr.has_key('task_synopsis'):
            msg.append(attr['task_synopsis'].strip())
            msg.append('')
        if attr.has_key('task_description'):
            if not attr['task_description'].strip() == "":
                msg.append('Synergy-description: %s' %attr['task_description'].strip())
                msg.append('')

        for k, v in attr.iteritems():
            if k == 'task_synopsis':
                continue
            if k == 'task_description':
                continue
            if k == 'status_log':
                continue
            if not len(v.strip()):
                continue
            msg.append('Synergy-'+k.replace('_', '-')+': '+v.strip().replace("\n", " "))
        msg.append('\n')
    return '\n'.join(msg)

def find_task_in_release(task, tasks):
    ret = []
    for t in tasks:
        if t.get_object_name() in task:
            ret.append(t)
    return ret

def get_objects_from_graph(task, graph, objects):
    objs = []
    for o in graph.links(task):
        for obj in objects:
            if obj == o:
                objs.append(obj)
                break
    return [ccm_cache.get_object(o) for o in objs]

def get_task_object_from_splitted_task_name(task, delim):
    # common task or splitted task
    if task.startswith('common'):
        # two tasks combined, strip common and split the tasks: common-task64827-1:task:ou1s40-task64849-1:task:ou1s40
        p = re.compile("common-(.*:.*:.*)-(.*%s.*)" %delim)
        m = p.match(task)
        if m:
            return [m.group(1), m.group(2)]
    else:
        #Splitted task
        if '_TASKSPLIT_' in task:
            return [task.split('_TASKSPLIT_')[0]]
        return [task]

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
        o = sort_objects_by_history(v)
        ret_val.append(o)

    return ret_val

def sort_objects_by_history(objects):
    object_names = [o.get_object_name() for o in objects]
    latest_object = objects[0]
    for o in objects:
        latest = True
        for s in o.successors:
            if s not in object_names:
                latest &= True
            else:
                latest &= False
        if latest:
            latest_object = o

    return latest_object

def get_object(o, objects):
    for obj in objects:
        if obj == o:
            return ccm_cache.get_object(obj)

def decide_type(obj):
    cache_path = ccm_cache.load_ccm_cache_path()
    dir, filename = ccm_cache.get_path_for_object(obj.get_object_name(), cache_path)
    command = ['file', '-i', '-b', filename]
    result = run_command(command)
    logger.info('Result %s' % result)
    if 'binary' in result:
        return 'binary'
    else:
        return 'ascii'

def create_blob(obj, mark):
    global object_mark_lookup
    if object_mark_lookup.has_key(obj.get_object_name()):
        object_mark = object_mark_lookup[obj.get_object_name()]
        logger.info("Used lookup-mark: %s for: %s" % (str(object_mark), obj.get_object_name()))
        return object_mark, mark
    else:
        #create the blob
        next_mark = get_mark(mark)
        blob = ['blob', 'mark :' + str(next_mark)]
        logger.info("Creating lookup-mark: %s for %s" % (str(next_mark), obj.get_object_name()))
        if skip_binary():
            # Skip for binary files
            # Types and super type in Synergy can't be trusted, figure out the type manually
            type = decide_type(obj)
            if type == 'ascii':
                content = ccm_cache.get_source(obj.get_object_name())
            else: # binary
                content = ''
        else:
            content = ccm_cache.get_source(obj.get_object_name())
        length = len(content)
        blob.append('data '+ str(length))
        blob.append(content)
        print '\n'.join(blob)
        object_mark_lookup[obj.get_object_name()] = next_mark
        return next_mark, next_mark

def create_blob_for_empty_dir(mark):
    blob = ['blob', 'mark :' + str(mark), 'data 0']
    print '\n'.join(blob)
    return mark

def rename_toplevel_dir(previous_name, current_name, release, releases, mark, from_mark):
    global users
    mark = get_mark(mark)
    logger.info("Commit for project name change: %s -> %s" %(previous_name, current_name))

    # Use the release author
    author = users.get_user(releases[release]['author'])
    # Use the release time from previous release
    create_time = time.mktime(releases[releases[release]['previous']]['created'].timetuple())

    commit_info = ['commit refs/tags/' + release,
                   'mark :' + str(mark),
                   'author %s <%s@nokia.com> ' % (author['name'], author['mail']) + str(int(create_time)) + " +0000",
                   'committer %s <%s@nokia.com> ' % (author['name'], author['mail']) + str(int(create_time)) + " +0000"]
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


def get_master_tag():
    f = open('config.p', 'rb')
    config = cPickle.load(f)
    f.close()
    object = ccm_cache.get_object(config['master'])
    tag = object.name + object.separator + object.version
    return tag

def skip_binary():
    f = open('config.p', 'rb')
    config = cPickle.load(f)
    f.close()
    return config['skip_binary_files']

def run_command(command):
    """Execute a command"""
    p = Popen(command, stdout=PIPE, stderr=PIPE)

    # Store the result as a single string.
    stdout, stderr = p.communicate()

    if stderr:
        return stderr

    return stdout
