#!/usr/bin/env python
# encoding: utf-8
"""
fetch-ccm-history.py

Fetch ccm (Synergy, Continuus) history from a repository

Created by Emanuele Zattin and Aske Olsson on 2011-01-26.
Copyright (c) 2011 Nokia. All rights reserved.
"""

from datetime import datetime
import time
import cPickle
import os.path
import os
import sys

import SynergySession
import SynergySessions
import FileObject
import TaskObject
import SynergyObject
from SynergyUtils import ObjectHistory, TaskUtil, SynergyUtils, ObjectHistoryPool
import ccm_objects_in_project as ccm_objects

from collections import deque
from operator import itemgetter, attrgetter
from multiprocessing import Process, Queue

class Timer():
    def __init__(self):
        self.time = []
    def __enter__(self):
        self.start = time.time()
    def __exit__(self, *args):
        end = time.time() - self.start
        self.time.append(end)
        if len(self.time) % 100 == 0:
            print "time used processing last 100 objects:", sum(self.time[-100:])
        if len(self.time) % 1000 == 0:
            print "time used processing last 1000 objects:", sum(self.time[-1000:])
            self.time = []

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
        self.timer = Timer()
        self.project_objects = None
        self.baseline_objects = None

    def get_project_history(self, start_project, end_project):
        # find latest top-level project
        #result = self.ccm.query("name='{0}' and create_time > time('%today_minus2months') and status='released'".format(project)).format("%objectname").format("%create_time").format('%version').format("%owner").format("%status").format("%task").run()
        ##objectname, delimiter, owner, status, create_time, task):
        #latest = datetime(1,1,1, tzinfo=None)
        #latestproject = []
        #for s in result:
        #    time = datetime.strptime(s['create_time'], "%a %b %d %H:%M:%S %Y")
        #    if time > latest:
        #        latest = time
        #        latestproject = SynergyObject.SynergyObject(s['objectname'], self.delim, s['owner'], s['status'], s['create_time'], s['task'])
        #        self.tag = s['version']
        #print "Latest project:", latestproject.get_object_name(), "created:", latest

        latestproject = SynergyObject.SynergyObject(start_project, self.delim)
        # fill latestproject object with information
        info = self.ccm.query("name='%s' and version='%s' and type='%s' and instance='%s'" %(latestproject.get_name(), latestproject.get_version(), latestproject.get_type(), latestproject.get_instance()) ).format("%objectname").format("%create_time").format('%version').format("%owner").format("%status").format("%task").run()[0]
        latestproject.author = info['owner']
        latestproject.status = info['status']
        latestproject.created_time = datetime.strptime(info['create_time'], "%a %b %d %H:%M:%S %Y")
        latestproject.tasks = info['task']

        self.tag = latestproject.get_version()

        #find baseline of latestproject:
        base = self.ccm.query("is_baseline_project_of('{0}')".format(latestproject.get_object_name())).format("%objectname").format("%create_time").format('%version').format("%owner").format("%status").format("%task").run()[0]
        baseline_project = SynergyObject.SynergyObject(base['objectname'], self.delim, base['owner'], base['status'], base['create_time'], base['task'])
        print "Baseline project:", baseline_project.get_object_name()
        if self.tag not in self.history.keys():
            self.history[self.tag] = {'objects': [], 'tasks': []}
        self.history[self.tag]['next'] = None

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

            next = latestproject.get_version()

            # Find next baseline project
            latestproject = baseline_project
            baseline = self.ccm.query("is_baseline_project_of('{0}')".format(latestproject.get_object_name())).format("%objectname").format("%create_time").format('%version').format("%owner").format("%status").format("%task").run()
            if baseline:
                baseline_object = baseline[0]
                baseline_project = SynergyObject.SynergyObject(baseline_object['objectname'], self.delim, baseline_object['owner'], baseline_object['status'], baseline_object['create_time'], baseline_object['task'])
            else:
                baseline_project = None

            #Set previous project
            self.history[self.tag]['previous'] = latestproject.get_version()

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

            #Drop entry from dict to save memory
            #del self.history[self.tag]

            #Finally set the new (old) tag for the release
            self.tag = latestproject.get_version()
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

        return self.history


    def find_project_diff(self, latestproject, baseline_project):
        toplevel_project = latestproject

        #Get all objects and paths for latestproject
        if not self.project_objects:
            self.project_objects = ccm_objects.get_objects_in_project(latestproject, ccmpool=self.ccmpool)

        if baseline_project:
            #Get all objects and paths for baseline project
            self.baseline_objects = ccm_objects.get_objects_in_project(baseline_project, ccmpool=self.ccmpool)
            #new_objects = self.ccm.query("recursive_is_member_of('{0}', 'none') and not recursive_is_member_of('{1}', 'none')".format(latestproject, baseline_project)).format("%objectname").format("%owner").format("%status").format("%create_time").format("%task").run()
            # Find difference between latestproject and baseline_project
            new_objects, old_objects = self.get_changed_objects(self.project_objects, self.baseline_objects)
            object_hist_pool = ObjectHistoryPool(self.ccmpool, toplevel_project, old_objects, baseline_project)

        else:
            # root project, get ALL objects in release
            object_hist_pool = ObjectHistoryPool(self.ccmpool, toplevel_project, None, toplevel_project)
            new_objects = self.project_objects
            #new_objects = self.ccm.query("recursive_is_member_of('{0}', 'none')".format(latestproject)).format("%objectname").format("%owner").format("%status").format("%create_time").format("%task").run()

        print "DEBUG: instantiated an object_hist_pool, type is: " + str(type(object_hist_pool))
        print "DEBUG: object_hist_pool[0]'s type is: " + str(type(object_hist_pool[0]))

        # make the new_objects dictionary into an array, to be able to walk it by index
        new_objects_indexable = []
        for o in new_objects.keys():
            new_objects_indexable.append(o)

        num_of_objects = len([o for o in new_objects.keys() if ":project:" not in o])
        print "objects to process for",  latestproject, ": ", num_of_objects
        objects = {}
        persist = 0
        if self.tag in self.history.keys():
            if 'objects' in self.history[self.tag]:
                #Add all existin objects
                for o in self.history[self.tag]['objects']:
                    objects[o.get_object_name()] = o
        else:
            self.history[self.tag] = {'objects': [], 'tasks': []}

        # Check history for all objects and add them to history
        new_objects_processing_progress_idx = 0
        while True: # this is the new_objects progress outer loop, which is broken when the last object in new_objects has been processed in a processing pool
            # build the processing pool
            current_pool_fill_idx = 0
            current_pool_ObjectArray = []
            print "DEBUG: Populate a processing pool..."
            while True:
                tempobject = new_objects_indexable[new_objects_processing_progress_idx]
                print "DEBUG: -  start checking: tempobject = " + str(tempobject) + " for pool inclusion"
                if tempobject not in objects.keys():
                    print "DEBUG: --  tempobject = " + str(tempobject) + " not already in objects.keys()"
                    if ':project:' not in tempobject:
                        print "DEBUG: ---  ':project:' not in tempobject = " + str(tempobject)
                        print "DEBUG:      new_objects_indexable[new_objects_processing_progress_idx] type = " + str(type(new_objects_indexable[new_objects_processing_progress_idx]))
                        current_pool_ObjectArray.append(new_objects_indexable[new_objects_processing_progress_idx])
                        print "DEBUG: current_pool_fill_idx = " + str(current_pool_fill_idx)
                        print "DEBUG: ----  current_pool_ObjectArray[" + str(current_pool_fill_idx) + "] = " + str(current_pool_ObjectArray[current_pool_fill_idx])
                        if (current_pool_fill_idx >= self.ccmpool.nr_sessions-1):
                            break
                        current_pool_fill_idx += 1
                if (new_objects_processing_progress_idx >= len(new_objects_indexable)-1):
                    break
                new_objects_processing_progress_idx += 1

            print "DEBUG: start processing pool"
            ccm_session_idx = 0
            print "DEBUG: type(object_hist_pool) = " + str(type(object_hist_pool))
            print "DEBUG: type(ccm_session_idx) = " + str(type(ccm_session_idx))
            for workobject in current_pool_ObjectArray:
                print "DEBUG: type(workobject) = " + str(type(workobject))
                # now we have a processing pool, of finite size, kick off the pool
                print "DEBUG: +  object_hist_pool[" + str(ccm_session_idx) + "].start_get_history("
                #create FileObject
                so = SynergyObject.SynergyObject(workobject, self.delim)
                res = self.ccm.query("name='{0}' and version='{1}' and type='{2}' and instance='{3}'".format(so.get_name(), so.get_version(), so.get_type(), so.get_instance())).format("%objectname").format("%owner").format("%status").format("%create_time").format("%task").run()
                fileobj = FileObject.FileObject(res[0]['objectname'], self.delim, res[0]['owner'], res[0]['status'], res[0]['create_time'], res[0]['task']), new_objects[workobject]
                object_hist_pool[ccm_session_idx].start_get_history(fileobj, new_objects[workobject])
                ccm_session_idx += 1

            # join the processing pool
            current_pool_ReturnObjectsArray = []
            with self.timer:
                ccm_session_idx = 0
                for workobject in current_pool_ObjectArray:
                    print "DEBUG: Waiting for object_hist_pool[" + str(ccm_session_idx) + "]"
                    current_pool_ReturnObjectsArray.append(object_hist_pool[ccm_session_idx].join_get_history())
                    ccm_session_idx += 1

            # update the objects not already in the objects array (in case the same object is effectively processed multiple times in the same pool)
            for retObject in current_pool_ReturnObjectsArray:
                print "retObject = " + str(retObject)
                print "retObject type = " + str(type(retObject))
                if (retObject not in objects.keys()):
                    objects.update(retObject)

            # break out of the pool processing loop if all elemenets have been processed
            if (new_objects_processing_progress_idx >= len(new_objects_indexable)-1):
                break

            persist += len(current_pool_ReturnObjectsArray)

            if persist >= 100:
                self.history[self.tag]['objects'] = objects.values()
                fname = self.outputfile + '_' + self.tag + '_inc'
                self.persist_data(fname, self.history[self.tag])
                persist = 0

            num_of_objects -= len(current_pool_ObjectArray)
            print "objects left:", num_of_objects

        print "number of files:", str(len(objects.values()))
        self.history[self.tag]['objects'] = objects.values()

        # Create tasks from objects, but not for initial project
        if baseline_project:
            self.find_tasks_from_objects(objects.values(), latestproject)


    def find_tasks_from_objects(self, objects, project):
        tasks = {}
        not_used = []

        if self.tag in self.history.keys():
            if 'tasks' in self.history[self.tag]:
                for t in self.history[self.tag]['tasks']:
                    print "loading old task:", t.get_display_name()
                    tasks[t.get_display_name()] = t

        num_of_tasks = sum([len(o.get_tasks().split(',')) for o in objects])
        print "Tasks with associated objects:", num_of_tasks

        #Build a list of all tasks
        tasklist = [task for o in objects for task in o.get_tasks().split(',') if task != '<void>' ]

        queue = deque(set(tasklist) - set(tasks.keys()))
        #create task objects in parallel
        while queue:
            print "queue size:", len(queue)
            processes = []
            queues = []
            for i in range(self.ccmpool.nr_sessions):
                # Break if queue is empty
                if not queue:
                    break
                # make processes
                task = queue.popleft()
                ccm = self.ccmpool[i]
                queues.append(Queue())
                processes.append(Process(target=self.create_task_object, args=(task, ccm, project, queues[i])))

            for p in processes:
                p.start()

            for i in range(len(processes)):
                res = queues[i].get()
                if res:
                    tasks[res.get_display_name()] = res
                    print "res %s next %d" % (res.get_display_name(),i)
                else:
                    print "res %s next %d" % (res,i)
                processes[i].join()

            print "No of tasks added to release so far: %d for project %s" % (len(tasks.keys()), project)

        # Add objects to tasks
        [t.add_object(o.get_object_name()) for o in objects for t in tasks.values() if t.get_display_name() in o.get_tasks()]
        print "No of tasks in release %s: %d" % (project, len(tasks.keys()))
        self.history[self.tag]['tasks'] = tasks.values()
        fname = self.outputfile + '_' + self.tag + '_inc'
        self.persist_data(fname, self.history[self.tag])

    def create_task_object(self, task, ccm, project, q):
        task_util = TaskUtil(ccm)
        # create task object
        print "Task:", task
        if task_util.task_in_project(task, project):
            result = ccm.query("name='{0}' and instance='{1}'".format('task' + task.split('#')[1], task.split('#')[0])).format("%objectname").format("%owner").format("%status").format("%create_time").format("%task_synopsis").format("%release").run()

            t = result[0]
            # Only use completed tasks!
            if t['status'] == 'completed':
                to = TaskObject.TaskObject(t['objectname'], self.delim, t['owner'], t['status'], t['create_time'], task)
                to.set_synopsis(t['task_synopsis'])
                to.set_release(t['release'])
                # Fill all task info
                task_util.fill_task_info(to)
                q.put(to)
        else:
            print "Task %s not used in %s!" %(task, project)
            q.put(None)
        q.close()

    def persist_data(self, fname, data):
        fname = fname + '.p'
        print "saving..."
        fh = open(fname, 'wb')
        cPickle.dump(data, fh, cPickle.HIGHEST_PROTOCOL)
        fh.close()
        print "done..."


    def get_changed_objects(self, new_release, old_release):
        new_objects = {}
        old_objects = {}
        diff = set(new_release.keys())-set(old_release.keys())
        for o in diff:
            new_objects[o] = new_release[o]

        diff = set(old_release.keys())-set(new_release.keys())
        for o in diff:
            old_objects[o] = old_release[o]

        return (new_objects, old_objects)

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
    delim = ccm.delim()
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
