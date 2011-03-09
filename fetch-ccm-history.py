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

from operator import itemgetter, attrgetter

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

    def get_project_history(self, project):
        # find latest top-level project
        result = self.ccm.query("name='{0}' and create_time > time('%today_minus2months') and status='released'".format(project)).format("%objectname").format("%create_time").format('%version').format("%owner").format("%status").format("%task").run()
        #objectname, delimiter, owner, status, create_time, task):
        latest = datetime(1,1,1, tzinfo=None)
        latestproject = []
        for s in result:
            time = datetime.strptime(s['create_time'], "%a %b %d %H:%M:%S %Y")
            if time > latest:
                latest = time
                latestproject = SynergyObject.SynergyObject(s['objectname'], self.delim, s['owner'], s['status'], s['create_time'], s['task'])
                self.tag = s['version']
        print "Latest project:", latestproject.get_object_name(), "created:", latest

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
            self.create_history(latestproject.get_object_name(), baseline_project.get_object_name())
            self.history[self.tag]['created'] = latestproject.get_created_time()

            next = latestproject.get_version()

            # Find next baseline project
            latestproject = baseline_project
            baseline = self.ccm.query("is_baseline_project_of('{0}')".format(latestproject.get_object_name())).format("%objectname").format("%create_time").format('%version').format("%owner").format("%status").format("%task").run()[0]
            baseline_project = SynergyObject.SynergyObject(baseline['objectname'], self.delim, baseline['owner'], baseline['status'], baseline['create_time'], baseline['task'])

            #Set previous project and name of current release:
            self.history[self.tag]['previous'] = latestproject.get_version()
            self.history[self.tag]['name'] = self.tag

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

            print "baseline project version:", baseline_project.get_version()

        self.history[self.tag]['previous'] = None
        print "getting all objects for:", latestproject.get_version(), "..."
        # Do the last project as a full project
        self.find_project_diff(latestproject.get_object_name(), baseline_project, latestproject.get_object_name())
        self.history[self.tag]['name'] = self.tag
        self.history[self.tag]['created'] = latestproject.get_created_time()
        #Print Info
        self.history[self.tag]['previous'] = None
        print self.tag, "done processing, Info:"
        print "Name        ", self.tag
        print "Previous <- ", self.history[self.tag]['previous']
        print "Next   ->   ", self.history[self.tag]['next']
        print "Number of:  "
        print "    Tasks:  ", str(len(self.history[self.tag]['tasks']))
        print "    Files:  ", str(len(self.history[self.tag]['objects']))
        print ""

        return self.history


    def create_history(self, latestproject, baseline_project):
        #clear changed objects and find all objects from this release
        self.find_project_diff(latestproject, baseline_project, latestproject)

    def find_project_diff(self, latestproject, baseline_project, toplevel_project):
        # Find difference between latestproject and baseline_project
        if baseline_project:
            object_hist_pool = ObjectHistoryPool(self.ccmpool, toplevel_project, baseline_project)
            objects_changed = self.ccm.query("recursive_is_member_of('{0}', 'none') and not recursive_is_member_of('{1}', 'none')".format(latestproject, baseline_project)).format("%objectname").format("%owner").format("%status").format("%create_time").format("%task").run()
        else:
            # root project, get ALL objects in release
            object_hist_pool = ObjectHistoryPool(self.ccmpool, toplevel_project, toplevel_project)
            objects_changed = self.ccm.query("recursive_is_member_of('{0}', 'none')".format(latestproject)).format("%objectname").format("%owner").format("%status").format("%create_time").format("%task").run()

        print "DEBUG: instantiated an object_hist_pool, type is: " + str(type(object_hist_pool))
        print "DEBUG: object_hist_pool[0]'s type is: " + str(type(object_hist_pool[0]))

        # make the objects_changed dictionary into an array, to be able to walk it by index
        objects_changed_indexable = []
        for o in objects_changed:
            objects_changed_indexable.append(o)

        num_of_objects = len([o for o in objects_changed if ":project:" not in o])
        print "objects to process for",  latestproject, ": ", num_of_objects
        objects = {}
        persist = 1
        if self.tag in self.history.keys():
            if 'objects' in self.history[self.tag]:
                #Add all existin objects
                for o in self.history[self.tag]['objects']:
                    objects[o.get_object_name()] = o
        else:
            self.history[self.tag] = {'objects': [], 'tasks': []}

        # Check history for all objects and add them to history
        objects_changed_processing_progress_idx = 0
        while True: # this is the objects_changed progress outer loop, which is broken when the last object in objects_changed has been processed in a processing pool
            # build the processing pool
            current_pool_fill_idx = 0
            current_pool_ObjectArray = []
            print "DEBUG: Populate a processing pool..."
            while True:
                tempobject = objects_changed_indexable[objects_changed_processing_progress_idx]
                print "DEBUG: -  start checking: tempobject['objectname'] = " + str(tempobject['objectname']) + " for pool inclusion"
                if tempobject['objectname'] not in objects.keys(): 
                    print "DEBUG: --  tempobject['objectname'] = " + str(tempobject['objectname']) + " not already in objects.keys()"
                    if ':project:' not in tempobject['objectname']:
                        print "DEBUG: ---  ':project:' not in tempobject['objectname'] = " + str(tempobject['objectname'])
                        print "DEBUG:      objects_changed_indexable[objects_changed_processing_progress_idx] type = " + str(type(objects_changed_indexable[objects_changed_processing_progress_idx]))
                        current_pool_ObjectArray.append(objects_changed_indexable[objects_changed_processing_progress_idx])
                        print "DEBUG: current_pool_fill_idx = " + str(current_pool_fill_idx)                       
                        print "DEBUG: ----  current_pool_ObjectArray[" + str(current_pool_fill_idx) + "] = " + str(current_pool_ObjectArray[current_pool_fill_idx])
                        if (current_pool_fill_idx >= self.ccmpool.nr_sessions-1):
                            break
                        current_pool_fill_idx += 1
                if (objects_changed_processing_progress_idx >= len(objects_changed_indexable)-1):
                    break
                objects_changed_processing_progress_idx += 1
    
            print "DEBUG: start processing pool"
            ccm_session_idx = 0
            print "DEBUG: type(object_hist_pool) = " + str(type(object_hist_pool))
            print "DEBUG: type(ccm_session_idx) = " + str(type(ccm_session_idx))
            for workobject in current_pool_ObjectArray:
                print "DEBUG: type(workobject) = " + str(type(workobject))
                # now we have a processing pool, of finite size, kick off the pool
                print "DEBUG: +  object_hist_pool[" + str(ccm_session_idx) + "].start_get_history("
                object_hist_pool[ccm_session_idx].start_get_history(FileObject.FileObject(workobject['objectname'], self.delim, workobject['owner'], workobject['status'], workobject['create_time'], workobject['task']))
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
            if (objects_changed_processing_progress_idx >= len(objects_changed_indexable)-1):
                break

            persist += len(current_pool_ReturnObjectsArray)

            if persist % 100 == 0:
                self.history[self.tag]['objects'] = objects.values()
                fname = self.outputfile + '_' + self.tag + '_inc'
                self.persist_data(fname, self.history[self.tag])

            num_of_objects -= len(current_pool_ObjectArray)
            print "objects left:", num_of_objects


        print "number of files:", str(len(objects.values()))
        self.history[self.tag]['objects'] = objects.values()

        # Create tasks from objects
        self.find_tasks_from_objects(objects.values(), latestproject)


    def find_tasks_from_objects(self, objects, project):
        task_util = TaskUtil(self.ccm)
        tasks = {}
        not_used = []

        if self.tag in self.history.keys():
            if 'tasks' in self.history[self.tag]:
                for t in self.history[self.tag]['tasks']:
                    print "loading old task:", t.get_display_name()
                    tasks[t.get_display_name()] = t

        num_of_tasks = sum([len(o.get_tasks().split(',')) for o in objects])
        print "Tasks with associated objects:", num_of_tasks
        #Find all tasks from the objects found
        for o in objects:
            for task in o.get_tasks().split(','):
                if task != "<void>":
                    if task not in tasks.keys():
                        if task not in not_used:
                            # create task object
                            print "Task:", task
                            if task_util.task_in_project(task, project):
                                result = self.ccm.query("name='{0}' and instance='{1}'".format('task' + task.split('#')[1], task.split('#')[0])).format("%objectname").format("%owner").format("%status").format("%create_time").format("%task_synopsis").format("%release").run()

                                t = result[0]
                                # Only use completed tasks!
                                if t['status'] == 'completed':
                                    to = TaskObject.TaskObject(t['objectname'], self.delim, t['owner'], t['status'], t['create_time'], task)
                                    to.set_synopsis(t['task_synopsis'])
                                    to.set_release(t['release'])
                                    print "adding", o.get_object_name(), "to", task
                                    to.add_object(o.get_object_name())

                                    tasks[task] = to
                            else:
                                not_used.append(task)
                    else:
                        if o.get_object_name() not in tasks[task].get_objects():
                            print "adding", o.get_object_name(), "to", task
                            tasks[task].add_object(o.get_object_name())
            num_of_tasks -= 1
            print "tasks left:", num_of_tasks

        num_of_tasks = len(tasks.keys())
        print "Tasks in release to process for info:", num_of_tasks

        # Fill out all task info
        for task in tasks.values():
            if not task.get_attributes():
                task_util.fill_task_info(task)
            num_of_tasks -= 1
            print "tasks left:", num_of_tasks

        self.history[self.tag]['tasks'] = tasks.values()
        fname = self.outputfile + '_' + self.tag + '_inc'
        self.persist_data(fname, self.history[self.tag])


    def persist_data(self, fname, data):
        fname = fname + '.p'
        print "saving..."
        fh = open(fname, 'wb')
        cPickle.dump(data, fh, cPickle.HIGHEST_PROTOCOL)
        fh.close()
        print "done..."


def main():
    ccm_db = sys.argv[1]
    project = sys.argv[2]
    outputfile = sys.argv[3]

    print "Starting Synergy session on", ccm_db, "..."
    ccm = SynergySession.SynergySession(ccm_db)
    ccmpool = SynergySessions.SynergySessions(database=ccm_db, nr_sessions=10)
    print "session started"
    delim = ccm.delim()
    history = {}
    fname = outputfile + '.p'
    if os.path.isfile(fname):
        print "Loading", fname, "..."
        fh = open(fname, 'rb')
        history = cPickle.load(fh)
        fh.close()
        print "history contains:", history.keys()

    #print history
    fetch_ccm = CCMHistory(ccm, ccmpool, history, outputfile)
    history = fetch_ccm.get_project_history(project)


    fh = open(outputfile + '.p', 'wb')
    cPickle.dump(history, fh, cPickle.HIGHEST_PROTOCOL)
    fh.close()



if __name__ == '__main__':
    main()
