#!/usr/bin/env python
# encoding: utf-8
"""
fetch-ccm-history.py

Fetch ccm (Synergy, Continuus) history from a repository

Created by Aske Olsson 2011-01-11.
Copyright (c) 2010 Aske Olsson. All rights reserved.
"""

import SynergySession
import FileObject
import TaskObject
import SynergyObject
from SynergyUtils import ObjectHistory, TaskUtil, CCMFilePath, SynergyUtils

from operator import itemgetter, attrgetter

from datetime import datetime
import time
import cPickle
import os.path
import os
import sys

class CCMHistory(object):
    """Get History (objects and tasks) in a Synergy (ccm) database between baseline projects"""

    def __init__(self, ccm, history, outputfile):
        self.ccm = ccm
        self.delim = self.ccm.delim()
        self.history = history
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
            self.tag = latestproject.get_version()
            if self.tag not in self.history.keys():
                self.history[self.tag] = {'objects': [], 'tasks': []}
            self.history[self.tag]['next'] = next

        return self.history


    def create_history(self, latestproject, baseline_project):
        #clear changed objects and find all objects from this release
        self.find_project_diff(latestproject, baseline_project, latestproject)


    def find_project_diff(self, latestproject, baseline_project, toplevel_project):
        #print "diffenence between", latestproject, "and", baseline_project
        object_hist = ObjectHistory(self.ccm, toplevel_project)
        objects_changed = self.ccm.query("is_member_of('{0}') and not is_member_of('{1}')".format(latestproject, baseline_project)).format("%objectname").format("%owner").format("%status").format("%create_time").format("%task").run()
        objects = {}
        existing_objects = []
        persist = False
        if self.tag in self.history.keys():
            if 'objects' in self.history[self.tag]:
                existing_objects = [o.get_object_name() for o in self.history[self.tag]['objects']]
        else:
            self.history[self.tag] = {'objects': [], 'tasks': []}
        for o in objects_changed:
            #print o['objectname']
            if o['objectname'] not in existing_objects:
                if ':project:' in o['objectname']:
                    #print o['objectname']
                    #Find diffenence of subprojects
                    #first find subprojects baseline project
                    subproject = o['objectname']
                    subproject_baseline = self.ccm.query("is_baseline_project_of('{0}')".format(subproject)).format("%objectname").format("%create_time").format('%version').run()
                    #print subproject_baseline
                    if subproject_baseline:
                        subproject_baseline = subproject_baseline[0]
                        print "Subproject", subproject
                        self.find_project_diff(subproject, subproject_baseline['objectname'], toplevel_project)
                    else:
                        print "subproject", subproject, "has no baseline project"
                        #Lets see if the project has a predecessor:
                        subproject_predecessor = self.ccm.query("is_predecessor_of('{0}')".format(subproject)).format("%objectname").format("%create_time").format('%version').run()
                        if subproject_predecessor:
                            print "project had a predecessor:", subproject_predecessor
                            self.find_project_diff(subproject, subproject_predecessor[0]['objectname'], toplevel_project)
#                            baseline_project = subproject_predecessor[0]['objectname']
                        else:
                            print "no predecessor..."
                    #print ""

                else:
                    # Get history for this file between these to baselines/ projects
                    with self.timer:
                        objects.update(object_hist.get_history(FileObject.FileObject(o['objectname'], self.delim, o['owner'], o['status'], o['create_time'], o['task']), baseline_project))
                    persist = True
                    #self.changed_objects.update(object_hist.get_history(FileObject.FileObject(o['objectname'], self.delim, o['owner'], o['status'], o['create_time'], o['task']), baseline_project))
                else:
                    print o['objectname'], "already in history"
        # Create tasks from objects
        self.find_tasks_from_objects(objects.values(), latestproject)
        #persist data
        self.history[self.tag]['objects'].extend(objects.values())
        if persist:
            fname = self.outputfile + '_' + self.tag + '_inc'
            self.persist_data(fname, self.history[self.tag])


    def find_tasks_from_objects(self, objects, project):
        task_util = TaskUtil(self.ccm)
        tasks = {}
        not_used = []
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
                                    to.add_object(o)

                                    tasks[task] = to
                            else:
                                not_used.append(task)
                    else:
                        tasks[task].add_object(o)

        # Fill out all task info
        for task in tasks.values():
            task_util.fill_task_info(task)

        self.history[self.tag]['tasks'].extend(tasks.values())


    def get_project_objects(self, project):
        object_hist = ObjectHistory(self.ccm, project)
        objects_changed = self.ccm.query("is_member_of('{0}')".format(project)).format("%objectname").format("%owner").format("%status").format("%create_time").format("%task").run()
        objects = {}
        existing_objects = []
        persist = False
        if self.tag in self.history.keys():
            if 'objects' in self.history[self.tag]:
                existing_objects = [o.get_object_name() for o in self.history[self.tag]['objects']]
        else:
            self.history[self.tag] = {'objects': [], 'tasks': []}

        for o in objects_changed:
        #print o['objectname']
            if o['objectname'] not in existing_objects:
                if ':project:' in o['objectname']:
                    #print o['objectname']
                    #Find diffenence of subprojects
                    #first find subprojects baseline project
                    subproject = o['objectname']
                    print "Subproject", subproject
                    self.get_project_objects(subproject)

                else:
                    with self.timer:
                        objects.update(object_hist.get_history(FileObject.FileObject(o['objectname'], self.delim, o['owner'], o['status'], o['create_time'], o['task']), project))
                    persist = True
                    #self.changed_objects.update(object_hist.get_history(FileObject.FileObject(o['objectname'], self.delim, o['owner'], o['status'], o['create_time'], o['task']), baseline_project))
            else:
                print o['objectname'], "already in history"
        # Create tasks from objects
        self.find_tasks_from_objects(objects.values(), project)
        #persist data
        self.history[self.tag]['objects'].extend(objects.values())
        if persist:
            fname = self.outputfile + '_' + self.tag + '_inc'
            self.persist_data(fname, self.history[self.tag])


    def persist_data(self, fname, data):
        fname = fname + '.p'
        print "saving..."
        fh = open(fname, 'wb')
        cPickle.dump(data, fh)
        fh.close()
        print "done..."

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


def main():
    # make all stdout stderr writes unbuffered/ instant/ inline
    sys.stdout =  os.fdopen(sys.stdout.fileno(), 'w', 0);
    sys.stderr =  os.fdopen(sys.stderr.fileno(), 'w', 0);

    ccm_db = sys.argv[1]
    project = sys.argv[2]
    outputfile = sys.argv[3]

    print "Starting Synergy session on", ccm_db, "..."
    ccm = SynergySession.SynergySession(ccm_db)
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
    fetch_ccm = CCMHistory(ccm, history, outputfile)

    history = fetch_ccm.get_project_history(project)


    fh = open(outputfile + '.p', 'wb')
    cPickle.dump(history, fh)
    fh.close()



if __name__ == '__main__':
    main()
