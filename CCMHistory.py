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
Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the
distribution.
Neither the name of the Nokia nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.    IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import cPickle
import os
import sys

import SynergySession
import SynergySessions
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

    def get_project_history(self, start_project, end_project):
        latestproject = ccm_cache.get_object(start_project, self.ccm)

        self.tag = latestproject.get_name() + self.delim + latestproject.get_version()
        baseline_project = ccm_cache.get_object(latestproject.get_baseline_predecessor())
        print "Baseline project:", baseline_project.get_object_name()
        if self.tag not in self.history.keys():
            self.history[self.tag] = {'objects': [], 'tasks': []}
        self.history[self.tag]['next'] = None
        self.history['delimiter'] = self.delim

        while baseline_project:
            print "Toplevel Project:", latestproject.get_object_name()
            # do the history thing
            self.history[self.tag]['name'] = self.tag
            self.find_project_diff(latestproject.get_object_name(), baseline_project.get_object_name())
            self.history[self.tag]['created'] = latestproject.get_created_time()
            self.history[self.tag]['author'] = latestproject.get_author()
            # Add the objects and paths to the history, to be used for finding empty directories
            empty_dirs = find_empty_dirs(self.project_objects)
            print "Empty dirs:\n%s" % '\n'.join(sorted(empty_dirs))
            self.history[self.tag]['empty_dirs'] = empty_dirs

            next = latestproject.get_name() + self.delim + latestproject.get_version()

            # Find next baseline project
            latestproject = baseline_project
            baseline_project = ccm_cache.get_object(latestproject.get_baseline_predecessor())
            #Set previous project
            self.history[self.tag]['previous'] = latestproject.get_name() + self.delim + latestproject.get_version()

            #Store data
            fname = self.outputfile + '_' + self.tag
            self.persist_data(fname, self.history[self.tag])
            self.history_created.append(fname)
            # delete the _inc file if it exists
            if os.path.isfile(fname + '_inc' + '.p'):
                os.remove(fname + '_inc' + '.p')

            #Print Info
            print self.tag, "done processing, Info:"
            print "Name        ", self.tag
            print "Previous <- ", self.history[self.tag]['previous']
            print "Next   ->   ", self.history[self.tag]['next']
            print "Number of:  "
            print "    Tasks:  ", str(len(self.history[self.tag]['tasks']))
            print "    Files:  ", str(len(self.history[self.tag]['objects']))
            print ""

            #Finally set the new (old) tag for the release
            self.tag = latestproject.get_name() + self.delim + latestproject.get_version()
            if self.tag not in self.history.keys():
                self.history[self.tag] = {'objects': [], 'tasks': []}
            self.history[self.tag]['next'] = next

            # set the baseline_objects as objects for the next iteration
            self.project_objects = self.baseline_objects
            if baseline_project:
                print "baseline project version:", baseline_project.get_version()
            else:
                print "baseline project version:", baseline_project

            if latestproject.get_object_name() == end_project:
                print "End project reached", latestproject.get_object_name()
                baseline_project = None

        self.history[self.tag]['previous'] = None
        print "getting all objects for:", latestproject.get_version(), "..."
        # Do the last project as a full project
        self.find_project_diff(latestproject.get_object_name(), baseline_project)
        self.history[self.tag]['name'] = self.tag
        self.history[self.tag]['created'] = latestproject.get_created_time()
        self.history[self.tag]['author'] = latestproject.get_author()
        # Add the objects and paths to the history, to be used for finding empty directories
        empty_dirs = find_empty_dirs(self.project_objects)
        print "Empty dirs:\n%s" % '\n'.join(empty_dirs)
        self.history[self.tag]['empty_dirs'] = empty_dirs

        #Print Info
        print self.tag, "done processing, Info:"
        print "Name        ", self.tag
        print "Previous <- ", self.history[self.tag]['previous']
        print "Next   ->   ", self.history[self.tag]['next']
        print "Number of:  "
        print "    Tasks:  ", str(len(self.history[self.tag]['tasks']))
        print "    Files:  ", str(len(self.history[self.tag]['objects']))
        print ""

        # Get the different types in the db and their corresponding file permissions
        ccm_types = ccm_type.get_types_and_permissions(self.ccm)
        self.history['ccm_types'] = ccm_types

        return self.history

    def find_project_diff(self, latestproject, baseline_project):
        toplevel_project = latestproject

        #Get all objects and paths for latestproject
        if not self.project_objects:
            proj_obj = ccm_cache.get_object(latestproject, self.ccm)
            self.project_objects = proj_obj.get_members()
            if self.project_objects is None:
                self.project_objects = ccm_objects.get_objects_in_project(latestproject, ccmpool=self.ccmpool)
                proj_obj.set_members(self.project_objects)
                ccm_cache.force_cache_update_for_object(proj_obj)

        if baseline_project:
            #Get all objects and paths for baseline project
            proj_obj = ccm_cache.get_object(baseline_project, self.ccm)
            self.baseline_objects = proj_obj.get_members()
            if self.baseline_objects is None:
                self.baseline_objects = ccm_objects.get_objects_in_project(baseline_project, ccmpool=self.ccmpool)
                proj_obj.set_members(self.baseline_objects)
                ccm_cache.force_cache_update_for_object(proj_obj)
            # Find difference between latestproject and baseline_project
            new_objects, old_objects = self.get_changed_objects(self.project_objects, self.baseline_objects)
            new_projects = [o for o in self.project_objects.keys() if ':project:' in o]
            old_projects = [o for o in self.baseline_objects.keys() if ':project:' in o]
            object_history = ObjectHistory(self.ccm, toplevel_project, old_objects, baseline_project, new_projects, old_projects)
        else:
            # root project, get ALL objects in release
            new_objects = self.project_objects
            new_projects = [o for o in self.project_objects.keys() if ':project:' in o]
            object_history = ObjectHistory(self.ccm, toplevel_project, toplevel_project, None, toplevel_project, new_projects)

        num_of_objects = len([o for o in new_objects.keys() if ":project:" not in o])
        print "objects to process for",  latestproject, ": ", num_of_objects
        objects = {}
        persist = 0
        if self.tag in self.history.keys():
            if 'objects' in self.history[self.tag]:
                #Add all existing objects
                for o in self.history[self.tag]['objects']:
                    objects[o.get_object_name()] = o
                print "no of old objects loaded %d" % len(objects.keys())
        else:
            self.history[self.tag] = {'objects': [], 'tasks': []}

        object_names = set([o for o in new_objects.keys() if ':project:' not in o]) - set(objects.keys())
        for o in object_names:
            object = ccm_cache.get_object(o, self.ccm)
            objects.update(object_history.get_history(object, new_objects[object.get_object_name()]))

            #persist +=1
            #if persist % 5000 == 0:
            #    self.history[self.tag]['objects'] = objects.values()
            #    fname = self.outputfile + '_' + self.tag + '_inc'
            #    self.persist_data(fname, self.history[self.tag])
            num_of_objects -=1
            print 'Objects left: %d' %num_of_objects

        print "number of files:", str(len(objects.values()))
        self.history[self.tag]['objects'] = objects.values()

        # Create tasks from objects, but not for initial project
        if baseline_project:
            self.find_tasks_from_objects(objects.values(), latestproject)


    def persist_data(self, fname, data):
        fname += '.p'
        print "saving..."
        fh = open(fname, 'wb')
        cPickle.dump(data, fh, cPickle.HIGHEST_PROTOCOL)
        fh.close()
        print "done..."

    def find_tasks_from_objects(self, objects, project_name):
        tasks = {}
        #        not_used = []
        project = ccm_cache.get_object(project_name, self.ccm)
        if self.tag in self.history.keys():
            if 'tasks' in self.history[self.tag]:
                for t in self.history[self.tag]['tasks']:
                    print "loading old task:", t.get_display_name()
                    tasks[t.get_object_name()] = t

        #Build a list of all tasks
        task_list = [task for o in objects for task in o.get_tasks()]
        num_of_tasks = len(task_list)
        print "Tasks with associated objects:", num_of_tasks

        task_util = TaskUtil(self.ccm)
        for t in set(task_list)-set(tasks.keys()):
            task = ccm_cache.get_object(t, self.ccm)
            if task_util.task_used_in_project(task, project):
                tasks[task.get_object_name()] = task
            # Add objects to tasks
        [t.add_object(o.get_object_name()) for o in objects for t in tasks.values() if t.get_object_name() in o.get_tasks()]
        print "No of tasks in release %s: %d" % (project, len(tasks.keys()))
        self.history[self.tag]['tasks'] = tasks.values()
        fname = self.outputfile + '_' + self.tag + '_inc'
        self.persist_data(fname, self.history[self.tag])


    def get_changed_objects(self, new_release, old_release):
        new_objects = {}
        old_objects = {}
        diff = set(new_release.keys())-set(old_release.keys())
        for o in diff:
            new_objects[o] = new_release[o]

        diff = set(old_release.keys())-set(new_release.keys())
        for o in diff:
            old_objects[o] = old_release[o]

        return new_objects, old_objects

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
