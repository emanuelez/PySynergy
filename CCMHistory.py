#!/usr/bin/env python
# encoding: utf-8
"""
CCMHistory.py

Fetch ccm (Synergy, Continuus) history from a repository

Created by Emanuele Zattin and Aske Olsson on 2011-01-26.
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
import os
import sys
from SynergyObject import SynergyObject

import SynergySession
import SynergySessions
from TaskObject import TaskObject
import ccm_cache
from SynergyUtils import ObjectHistory, TaskUtil
import ccm_objects_in_project as ccm_objects
import ccm_type_to_file_permissions as ccm_type


class CCMHistory(object):
    """Get History (objects and tasks) in a Synergy (ccm) database between baseline projects"""

    def __init__(self, ccm, ccmpool, history, outputfile):
        self.ccm = ccm
        self.ccmpool = ccmpool
        self.delim = self.ccm.delim()
        self.history = history
        self.history_created = []
        self.tag = ""
        self.outputfile = outputfile
        self.project_objects = None
        self.baseline_objects = None

    def get_project_history(self, base_project, latest_project):

        release_chain = deque(get_project_chain(latest_project, base_project, self.ccm))

        base_project = release_chain.popleft()
        baseline_project = ccm_cache.get_object(base_project, self.ccm)
        self.tag = baseline_project.get_name() + self.delim + baseline_project.get_version()

        # Initialize history
        if self.tag not in self.history.keys():
            self.history[self.tag] = {'objects': [], 'tasks': []}
            self.history['delimiter'] = self.delim
        self.history[self.tag]['previous'] = None
        #if self.history[self.tag].has_key('next'):
        #    if not release_chain[0] in self.history[self.tag]['next']:
        #        self.history[self.tag]['next'].append(release_chain[0])
        #else:
        #    self.history[self.tag]['next']= [release_chain[0]]
        
        print "getting all objects for:", self.tag, "..."
        self.baseline_objects = None
        # Do the first project as a full project
        self.find_project_diff(baseline_project, None)
        self.history[self.tag]['name'] = self.tag
        self.history[self.tag]['fourpartname'] = baseline_project.get_object_name()
        self.history[self.tag]['created'] = baseline_project.get_created_time()
        self.history[self.tag]['author'] = baseline_project.get_author()
        # Add the objects and paths to the history, to be used for finding empty directories
        empty_dirs = find_empty_dirs(self.baseline_objects)
        self.history[self.tag]['empty_dirs'] = empty_dirs

        while release_chain:
            next = release_chain.popleft()
            next_project = ccm_cache.get_object(next, self.ccm)

            # Set next project for the current baseline_project
            if self.history[self.tag].has_key('next'):
                if not next_project.get_name() + self.delim + next_project.get_version() in self.history[self.tag]['next']:
                    self.history[self.tag]['next'].append(next_project.get_name() + self.delim + next_project.get_version())
            else:
                self.history[self.tag]['next'] = [next_project.get_name() + self.delim + next_project.get_version()]

            #Print Info about baseline_project
            print self.tag, "done processing, Info:"
            print "Name        ", self.tag
            print "4partname   ", self.history[self.tag]['fourpartname']
            print "Number of:  "
            print "    Tasks:  ", str(len(self.history[self.tag]['tasks']))
            print "    Files:  ", str(len(self.history[self.tag]['objects']))
            print "Previous <- ", self.history[self.tag]['previous']
            print "Next   ->   ", self.history[self.tag]['next']
            print ""

            self.tag = next_project.get_name() + self.delim + next_project.get_version()
            print "Next project:", next_project.get_object_name()
            if self.tag not in self.history.keys():
                self.history[self.tag] = {'objects': [], 'tasks': []}
            self.history[self.tag]['previous'] = baseline_project.get_name() + self.delim + baseline_project.get_version()

            print "Toplevel Project:", next_project.get_object_name()
            # do the history thing
            self.history[self.tag]['name'] = self.tag
            self.history[self.tag]['fourpartname'] = next_project.get_object_name()
            self.find_project_diff(baseline_project, next_project)
            self.history[self.tag]['created'] = next_project.get_created_time()
            self.history[self.tag]['author'] = next_project.get_author()
            # Add the objects and paths to the history, to be used for finding empty directories
            empty_dirs = find_empty_dirs(self.project_objects)
            print "Empty dirs:\n%s" % '\n'.join(sorted(empty_dirs))
            self.history[self.tag]['empty_dirs'] = empty_dirs

            # set new baseline project
            baseline_project = next_project
            # set the baseline_objects for the next iteration and
            self.baseline_objects = self.project_objects
            self.project_objects = []

            #Store data
            fname = self.outputfile + '_' + self.tag
            self.persist_data(fname, self.history[self.tag])
            self.history_created.append(fname)
            # delete the _inc file if it exists
            if os.path.isfile(fname + '_inc' + '.p'):
                os.remove(fname + '_inc' + '.p')


        # Info for last project:
        if not self.history[self.tag].has_key('next'):
            self.history[self.tag]['next'] = []
        print self.tag, "done processing, Info:"
        print "Name        ", self.tag
        print "4partname   ", self.history[self.tag]['fourpartname']
        print "Number of:  "
        print "    Tasks:  ", str(len(self.history[self.tag]['tasks']))
        print "    Files:  ", str(len(self.history[self.tag]['objects']))
        print "Previous <- ", self.history[self.tag]['previous']
        print "Next   ->   ", self.history[self.tag]['next']
        print ""

        # Get the different types in the db and their corresponding file permissions
        ccm_types = ccm_type.get_types_and_permissions(self.ccm)
        self.history['ccm_types'] = ccm_types

        return self.history

    def find_project_diff(self, baseline_project, next_project):

        # Get all objects and paths for baseline_project
        if not self.baseline_objects:
            self.baseline_objects = baseline_project.get_members()
            if self.baseline_objects is None or len(self.baseline_objects) == 1 or not isinstance(self.baseline_objects, dict):
                self.baseline_objects = ccm_objects.get_objects_in_project(baseline_project.get_object_name(), ccmpool=self.ccmpool)
                baseline_project.set_members(self.baseline_objects)
                ccm_cache.force_cache_update_for_object(baseline_project)
        if next_project:
            # Get all objects and paths for next project
            self.project_objects = next_project.get_members()
            if self.project_objects is None or len(self.project_objects) == 1  or not isinstance(self.project_objects, dict):
                self.project_objects = ccm_objects.get_objects_in_project(next_project.get_object_name(), ccmpool=self.ccmpool)
                next_project.set_members(self.project_objects)
                ccm_cache.force_cache_update_for_object(next_project)
            # Find difference between baseline_project and next_project
            new_objects, old_objects = get_changed_objects(self.baseline_objects, self.project_objects)
            next_projects = [o for o in self.project_objects.keys() if ':project:' in o]
            baseline_projects = [o for o in self.baseline_objects.keys() if ':project:' in o]
            object_history = ObjectHistory(self.ccm, next_project.get_object_name(), old_objects=old_objects, old_release=baseline_project.get_object_name(), new_projects=next_projects, old_projects=baseline_projects)
        else:
            # root project, get ALL objects in release
            new_objects = self.baseline_objects
            old_objects = []
            object_history = ObjectHistory(self.ccm, baseline_project.get_object_name())


        num_of_objects = len([o for o in new_objects.keys() if ":project:" not in o])
        print "objects to process : %s" % num_of_objects
        objects = {}
        if self.tag in self.history.keys():
            if 'objects' in self.history[self.tag]:
                #Add all existing objects
                for o in self.history[self.tag]['objects']:
                    objects[o] = ccm_cache.get_object(o, self.ccm)
                print "no of old objects loaded %d" % len(objects.keys())
        else:
            self.history[self.tag] = {'objects': [], 'tasks': []}

        object_names = set([o for o in new_objects.keys() if ':project:' not in o]) - set(objects.keys())
        for o in object_names:
            object = ccm_cache.get_object(o, self.ccm)
            if next_project:
                # get the object history between releases
                objects.update(object_history.get_history(object, new_objects[object.get_object_name()]))
            else:
                # just get all the objects in the release
                print 'Processing: %s\npath: %s' %(object.get_object_name(), new_objects[object.get_object_name()])
                object.set_path(new_objects[object.get_object_name()])
                objects[object.get_object_name()] = object

            num_of_objects -=1
            print 'Objects left: %d' %num_of_objects

        print "number of files:", str(len(objects.values()))
        self.history[self.tag]['objects'] = objects.keys()

        # Create tasks from objects, but not for initial project
        if next_project:
            self.find_tasks_from_objects(objects.values(), next_project)

        # Handle new projects:
        if next_project:
            new_created_projects = get_new_projects(old_objects, new_objects, self.delim)
            dir_lookup ={}
            # create lookup for path to directory-4-part-name {path : dir-name}
            for k,v in new_objects.iteritems():
                if ':dir:' in k:
                    for i in v:
                        dir_lookup[i] = k
            project_dirs = [dir for project in new_created_projects for dir in new_objects[project]]
            directories = [d for k,v in new_objects.iteritems() for d in v if ':dir:' in k]
            changed_directories = set(directories).intersection(set(project_dirs))
            changed_directories = remove_subdirs_under_same_path(changed_directories)
            dirs = [dir_lookup[d] for d in changed_directories]
            # find task and add all objects to the task, which shares the path.
            project_tasks = self.find_task_from_dirs(dirs)
            print "Checking for new subprojects"
            # check directories for new subdirectories and add their content
            directories = self.get_new_dirs(self.project_objects, new_objects)
            # Limit directories to only directories not already processed as a new project
            directories = set(directories) - set(dirs)
             # find task and add all objects to the task, which shares the path.
            dir_tasks = self.find_task_from_dirs(directories)
            # merge project and dir tasks
            for k,v in dir_tasks.iteritems():
                if not project_tasks.has_key(k):
                    project_tasks[k] = v
            # if real synergy tasks isn't found check the path of the directories and skip possible subdirs
            tasks = self.reduce_dir_tasks(project_tasks)
            print "Project and dir tasks reduced..."
            print tasks
            self.update_tasks_with_directory_contens(tasks)

        # remove possible duplicates from objects
        self.history[self.tag]['objects'] = list(set(self.history[self.tag]['objects']))


    def update_tasks_with_directory_contens(self, tasks):
        for k,v in tasks.iteritems():
            objects = self.find_children_of_dir(k)
            #if len(v) > 1:
            #    # TODO something
            #    pass
            self.update_task_in_history_with_objects(v[0], objects)
            self.update_history_with_objects(objects)

    def update_task_in_history_with_objects(self, task, objects):
        # Find the task in history if its there
        found = False
        for t in self.history[self.tag]['tasks']:
            if t.get_object_name() == task:
                if t.objects:
                    t.objects.extend([o for o in objects if ':project:' not in o])
                    t.objects = list(set(t.objects))
                else:
                    t.objects = [o for o in objects if ':project:' not in o]
                found = True
        if not found:
            t = ccm_cache.get_object(task, self.ccm)
            if t.type == 'task':
                t.objects = [o for o in objects if ':project:' not in o]
                self.history[self.tag]['tasks'].append(t)
            elif t.type == 'dir':
                # Make a task from the directory object
                task_obj = TaskObject("%s%s%s:task:%s" %(t.name, self.delim, t.version, t.instance), self.delim, t.author, t.status, t.created_time, t.tasks)
                task_obj.set_attributes(t.attributes)
                task_obj.complete_time = t.get_integrate_time()
                task_obj.objects = [o for o in objects if ':project:' not in o]
                self.history[self.tag]['tasks'].append(task_obj)

    def find_children_of_dir(self, dir):
        objects = []
        for k,v in self.project_objects.iteritems():
            for path in v:
                for p in self.project_objects[dir]:
                    if path.startswith(p):
                        # don't add directories
                        if not ':dir:' in k:
                            objects.append(k)
        return objects

    def find_task_from_dirs(self, dirs):
        tasks = {}
        for dir in dirs:
            print "Finding directory %s in tasks" % dir
            # Try to get the task from the tasks already found
            obj = ccm_cache.get_object(dir, self.ccm)
            tmp_task = obj.get_tasks()
            task = list(set(tmp_task) & set([t.get_object_name() for t in self.history[self.tag]['tasks']]))

            if not task:
                # Use object name as task name
                task = [dir]

            print "task found: %s" % ','.join(task)
            tasks[dir]= task
        return tasks

    def persist_data(self, fname, data):
        fname += '.p'
        print "saving..."
        fh = open(fname, 'wb')
        cPickle.dump(data, fh, cPickle.HIGHEST_PROTOCOL)
        fh.close()
        print "done..."

    def find_tasks_from_objects(self, objects, project):
        tasks = {}
        if self.tag in self.history.keys():
            if 'tasks' in self.history[self.tag]:
                for t in self.history[self.tag]['tasks']:
                    print "loading old task:", t.get_object_name()
                    tasks[t.get_object_name()] = t

        #Build a list of all tasks
        task_list = [task for o in objects for task in o.get_tasks()]
        num_of_tasks = len(set(task_list))
        print "Tasks with associated objects:", num_of_tasks

        task_util = TaskUtil(self.ccm)
        for t in set(task_list)-set(tasks.keys()):
            try:
                task = ccm_cache.get_object(t, self.ccm)
            except ccm_cache.ObjectCacheException:
                continue
            if task_util.task_in_project(task, project):
                tasks[task.get_object_name()] = task
            # Add objects to tasks
        [t.add_object(o.get_object_name()) for o in objects for t in tasks.values() if t.get_object_name() in o.get_tasks()]
        print "No of tasks in release %s: %d" % (project.get_object_name(), len(tasks.keys()))
        self.history[self.tag]['tasks'] = tasks.values()
        fname = self.outputfile + '_' + self.tag + '_inc'
        self.persist_data(fname, self.history[self.tag])

    def update_history_with_objects(self, objects):
        self.history[self.tag]['objects'].extend([o for o in objects if ':project:' not in o])

    def get_new_dirs(self, members, new_objects):
        new_directories = [d for d in new_objects.keys() if ':dir:' in d]
        directories = []
        for dir in new_directories:
            dir_obj = ccm_cache.get_object(dir, self.ccm)
            new_dirs = [d for d in dir_obj.new_objects if d.endswith('/')]
            for d in new_dirs:
                # Get the corresponding directory four-part-name
                paths = members[dir]
                name = get_dir_with_path(paths, d, members)
                directories.append(name)
        print "new directories found:"
        print '\n'.join([d + ', '.join(members[d]) for d in directories])
        return directories

    def reduce_dir_tasks(self, tasks):
        # find the fake tasks
        fake_tasks = []
        for k,v in tasks.iteritems():
            #if len(v) > 1:
            #hmmm
            if not v[0].startswith('task'):
                fake_tasks.append(k)

        # Find the paths of the directories the fake tasks corresponds to
        paths = {}
        for dir in fake_tasks:
            for p in self.project_objects[dir.replace(':task:', ':dir:')]:
                paths[p] = dir
            # remove the entry from the tasks dict
            del tasks[dir]

        dirs = remove_subdirs_under_same_path(paths.keys())

        tmp_tasks = {}
        for dir in dirs:
                tmp_tasks[paths[dir]] = [paths[dir]]

        tasks.update(tmp_tasks)
        return tasks

def get_dir_with_path(paths, dir, objects):
    paths_of_dir = [p +'/' + dir.strip('/') for p in paths]
    for k,v in objects.iteritems():
        if v == paths_of_dir:
            return k


def get_changed_objects(old_release, new_release):
    new_objects = {}
    old_objects = {}
    diff = set(new_release.keys())-set(old_release.keys())
    for o in diff:
        new_objects[o] = new_release[o]

    diff = set(old_release.keys())-set(new_release.keys())
    for o in diff:
        old_objects[o] = old_release[o]

    return new_objects, old_objects

def get_new_projects(old_objects, new_objects, delim):
    new_p = []
    new_projects = [SynergyObject(o, delim) for o in new_objects if ':project:' in o]
    old_projects = [SynergyObject(o, delim) for o in old_objects if ':project:' in o]
    old_projects_names = ["%s%s:%s:%s" % (o.name, delim, o.type, o.instance) for o in old_projects]
    for o in new_projects:
        threepartname = "%s%s:%s:%s" % (o.name, delim, o.type, o.instance)
        if not threepartname in old_projects_names:
            new_p.append(o.get_object_name())
    return new_p

def remove_subdirs_under_same_path(paths):
    spare = []
    for p in paths:
        candidates = [d for d in paths if d.startswith(p)]
        for c in candidates:
            if not p == c:
                spare.append(c)
    for d in set(spare):
        paths.remove(d)

    return paths

def get_project_chain(from_project, to_project, ccm):
    # Do it reverse:
    successor = ccm_cache.get_object(to_project, ccm)
    chain = [successor.get_object_name()]
    while successor.get_object_name() != from_project:
        successor = ccm_cache.get_object(successor.baseline_predecessor, ccm)
        if successor:
            chain.append(successor.get_object_name())
        else:
            break
    chain.reverse()
    return chain

def find_empty_dirs(objects):
    dirs = [d for o, paths in objects.iteritems() for d in paths if ':dir:' in o]
    files = [d for o, paths in objects.iteritems() for d in paths if ':dir:' not in o]
    used_dirs = [path.rsplit('/', 1)[0] for path in files]
    empty_dirs = set(dirs)-set(used_dirs)
    return empty_dirs


def main():
    # make all stdout stderr writes unbuffered/ instant/ inline
    #sys.stdout =  os.fdopen(sys.stdout.fileno(), 'w', 0);
    #sys.stderr =  os.fdopen(sys.stderr.fileno(), 'w', 0);

    ccm_db = sys.argv[1]
    start_project = sys.argv[2]
    end_project = sys.argv[3]
    outputfile = sys.argv[4]


    print "Starting Synergy session on", ccm_db, "..."
    ccm = SynergySession.SynergySession(ccm_db)
    ccmpool = SynergySessions.SynergySessions(database=ccm_db, nr_sessions=15)
    print "session started"
    #delim = ccm.delim()
    history = {}
    fname = outputfile + '.p'
    if os.path.isfile(fname):
        print "Loading", fname, "..."
        fh = open(fname, 'rb')
        history = cPickle.load(fh)
        fh.close()
    else:
        cwd = os.getcwd()
        content = os.listdir(cwd)
        for f in content:
            if not os.path.isdir(f):
                if outputfile in f:
                    if f.endswith('.p'):
                        print "Loading file", f
                        # Try to pickle it
                        fh = open(f, 'rb')
                        hist = cPickle.load(fh)
                        fh.close()
                        if 'name' in hist.keys():
                            history[hist['name']] = hist

    print "history contains:", sorted(history.keys())
    #print history
    fetch_ccm = CCMHistory(ccm, ccmpool, history, outputfile)
    history = fetch_ccm.get_project_history(start_project, end_project)


    fh = open(outputfile + '.p', 'wb')
    cPickle.dump(history, fh, cPickle.HIGHEST_PROTOCOL)
    fh.close()



if __name__ == '__main__':
    main()
