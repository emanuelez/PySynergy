#!/usr/bin/env python
# encoding: utf-8
"""
SynergyUtils.py

Created by Aske Olsson 2010-12-13.
Copyright (c) 2010 Aske Olsson. All rights reserved.
"""

import SynergySession
import FileObject
import TaskObject
from datetime import datetime
import re
from operator import itemgetter


class CCMFilePath(object):
    """Get the file path of a file from Synergy"""

    def __init__(self, ccm, toplevel_project):

        self.ccm = ccm
        self.top_reached = None
        self.toplevel_project = toplevel_project
        self.delim = self.ccm.delim()
        self.lookup = {}

    def get_file_path(self, object_name):
        self.top_reached = None
        result = self.recurse_file_path(object_name)
        if result:
            result = self.finalize_path(result)
        #print 'Final path:', result
        return result

    def finalize_path(self, path):
        final_path = []
        for index in range(len(path)):
            final_path.append(path[index].rpartition('/')[0])
            final_path.append('/')
        return ''.join(final_path)


    def recurse_file_path(self, object_name):
        ret_val = None
        #print 'Proccessing:', object_name
        result = self.ccm.finduse(object_name).option("-released_proj").run().splitlines()
        result.reverse()
        for s in result:
            if not self.top_reached:
                #print 'Trying:', s
                if 'MCL' in s:
                    s = s.strip()
                    # match
                    p = re.compile("^(.+?)-(.+?)@(.*)$")
                    m = p.match(s)
                    if m:
                        path = m.group(1)
                        childversion = m.group(2)
                        parentproject = m.group(3)

                        if parentproject == self.toplevel_project:
                            #print 'Top reached'
                            self.top_reached = 1
                            # add to lookup table
                            self.lookup[parentproject] = path
                            return [path]
                        else:
                            #try lookup table
                            if parentproject in self.lookup.keys():
                                #print "Path cached for:", object_name, ' '.join(self.lookup[parentproject])
                                self.top_reached = 1
                                return self.lookup[parentproject]

                            if ':project:' not in parentproject:
                                #Sometimes the greatness of Synergy will return a name-version instead of a four-part-name, so convert it into a four-part-name:
                                splitted_name = parentproject.split(self.delim)
                                fourpart = self.ccm.query("name='{0}' and version='{1}' and type='project'".format(splitted_name[0], splitted_name[1])).format('%objectname').run()
                                if fourpart:
                                    parentproject = fourpart[0]['objectname']

                            parent = self.recurse_file_path(parentproject)
                            #print 'Got:', parent
                            if parent is None:
                                #print parentproject, "didn't match"
                                ret_val = None
                            else:
                                l = parent
                                l.append(path)
                                # alse add this project to lookup table with complete path
                                self.lookup[parentproject] = l
                                ret_val = l

        return ret_val


class TaskUtil(object):
    """Various task releated methods"""

    def __init__(self, ccm):
        self.ccm = ccm
        self.delim = self.ccm.delim()
        self.synergy_utils = SynergyUtils(self.ccm)

    def task_in_project(self, task, project):
        # option 1: check if task is used in released project:
        ret_val = self.task_used_in_project(task, project)
        if not ret_val:
            # get 4part name of task for the two other checks
            task = self.ccm.query("name='{0}' and instance='{1}'".format('task' + task.split('#')[1], task.split('#')[0])).format("%objectname").run()[0]['objectname']
            # option 2: check the reconfigure properties of the projects
            ret_val = self.task_in_rp_of_project(task, project)
        if not ret_val:
            # option 3: check if task is in the project's own baseline
            ret_val = self.task_in_baseline_of_project(task, project)
        return ret_val

    def task_used_in_project(self, task, project):
        projects = self.ccm.finduse(task).option('-task').option('-released_proj').run().splitlines()
        for p in projects[1:]: # aviod [0], the task synopsis as this could contain the scope...
            p = p.strip()
            if project in p:
                #print "used in:", p
                return True
        return False

    def task_in_rp_of_project(self, task, project):
        tasks = self.ccm.rp(project).option('-show').option('all_tasks').run()
        for t in tasks:
            t = t['objectname'].strip()
            if task == t:
                return True
        return False

    def task_in_baseline_of_project(self, task, project):
        # check if the task is in same baselineas project
        baselines = self.ccm.query("has_project_in_baseline('{0}') and has_task_in_baseline('{1}')".format(project, task)).format('%objectname').run()
        if baselines:
            return True
        return False



    def fill_task_info(self, task):
        task.set_attributes(self.synergy_utils.get_all_attributes(task))
        #Find related task (s30)
        releated_task = self.ccm.query("has_task_in_CUIinsp('{0}')".format(task.get_object_name())).format('%objectname').format("%owner").format("%status").format("%create_time").format("%task").run()
        #There should be only one releated task - inspection task
        if len(releated_task) == 1:
            insp_task = TaskObject.TaskObject(releated_task[0]['objectname'], self.delim, releated_task[0]['owner'], releated_task[0]['status'], releated_task[0]['create_time'], releated_task[0]['task'])
            attributes = self.synergy_utils.get_all_attributes(insp_task)
            task.get_attributes().update({'inspection_task': attributes})

        task_objects = self.ccm.task(task.get_tasks(), True).option('-sh').option('obj').format("%objectname").format("%owner").format("%status").format("%create_time").format("%task").run()

        current_task_objects = [obj.get_object_name() for obj in task.get_objects()]
        for o in task_objects:
            if o['objectname'] not in current_task_objects:
                fileobject = FileObject.FileObject(o['objectname'], self.delim, o['owner'], o['status'], o['create_time'], o['task'])
                fileobject.set_attributes(self.synergy_utils.get_all_attributes(fileobject))
                predecessors = self.ccm.query("is_predecessor_of('{0}')".format(fileobject.get_object_name())).format("%objectname").run()
                for p in predecessors:
                    fileobject.add_predecessor(p['objectname'])
                successors = self.ccm.query("is_successor_of('{0}')".format(fileobject.get_object_name())).format("%objectname").run()
                for s in successors:
                    fileobject.add_successor(s['objectname'])
                #print fileobject.get_object_name()
                task.add_object(fileobject)

    def find_status_time(self, status, status_log):
        earliest = datetime.today()
        for line in status_log.splitlines():
            if status in line and 'ccm_root' not in line:
                time = datetime.strptime(line.partition(': Status')[0], "%a %b %d %H:%M:%S %Y")
                if time < earliest:
                    earliest = time

        return earliest


class ObjectHistory(object):
    """ Get the history of one object backwards in time """

    def __init__(self, ccm, toplevel_project):
        self.ccm = ccm
        self.history = {}
        self.synergy_utils = SynergyUtils(self.ccm)
        self.toplevel_project = toplevel_project
        self.ccm_file_path = CCMFilePath(ccm, toplevel_project)

    def get_history(self, fileobject, stop_at_release = None):
        print 'Processing:', fileobject.get_object_name()
        # clear old history
        self.history = {}
        # Get the file history recursively
        path = self.ccm_file_path.get_file_path(fileobject.get_object_name())
        fileobject.set_attributes(self.synergy_utils.get_all_attributes(fileobject))
        #print "Object", fileobject.get_object_name(), "path:", path
        fileobject.set_path(path)
        if stop_at_release == self.toplevel_project:
            #handle directory objects
            if fileobject.get_type() == 'dir':
                #get predecessors and do a diff on dir objects
                predecessors = self.ccm.query("is_predecessor_of('{0}')".format(fileobject.get_object_name())).format("%owner").format("%status").format("%create_time").format("%task").run()
                if len(predecessors) > 1:
                    print "several predecessors found for:", fileobject.get_object_name()
                for p in predecessors:
                    predecessor = FileObject.FileObject(p['objectname'], fileobject.get_separator(), p['owner'], p['status'], p['create_time'], p['task'])
                    fileobject.set_dir_changes(self.synergy_utils.get_dir_changes(fileobject, predecessor))
        else:
            self.recursive_get_history(fileobject, stop_at_release)
        self.history[fileobject.get_object_name()] = fileobject


        return self.history

    def add_to_history(self, fileobject):
        self.history[fileobject.get_object_name()] = fileobject

    def recursive_get_history(self, fileobject, stop_at_release):
        """ Recursivly find the history of the file object, optionally stopping at the 'stop_at_release' project """
        next_iter = False
        delim = fileobject.get_separator()
        #print 'Processing:', fileobject.get_object_name()
        predecessors = self.ccm.query("is_predecessor_of('{0}')".format(fileobject.get_object_name())).format("%owner").format("%status").format("%create_time").format("%task").run()
        for p in predecessors:
            predecessor = FileObject.FileObject(p['objectname'], delim, p['owner'], p['status'], p['create_time'], p['task'])

            #handle directory objects
            if fileobject.get_type() == 'dir':
                fileobject.set_dir_changes(self.synergy_utils.get_dir_changes(fileobject, predecessor))
            fileobject.add_predecessor(predecessor.get_object_name())
            # check predecessor release to see if this object should be added to the set.
            if stop_at_release:
                # Get the release(s) for the predecessor
                releases = self.ccm.query("has_member('{0}') and status='released'".format(predecessor.get_object_name())).format('%objectname').format('%create_time').run()
                if releases:
                    # Check if the "stop" release is the the releaes for the predecessor and return/stop if true
                    if stop_at_release in [r['objectname'] for r in releases if r['objectname'] == stop_at_release]:
                        continue
                    #Check if projects are releated to stop release. Latest first
                    rels = self.sort_releases_by_create_time(releases)
                    for r in rels:
                        if self.project_is_some_predecessor(r, stop_at_release):
                            print "Found Relationship between:", r, "and", stop_at_release
                            next_iter = True
                            break
                    if next_iter:
                        continue
                else:
                    #Check if a successor is released
                    if self.successor_is_released(predecessor, fileobject, stop_at_release):
                        print "Successor is already released", fileobject.get_object_name()
                        continue


            print "Adding", predecessor.get_object_name(), "to history"
             # Check if predecessor is already added to history - if so add this as successor to fileobject, else add new predecessor to history
            if self.history.has_key(predecessor.get_object_name()):
                 predecessor = self.history[predecessor.get_object_name()]
                 predecessor.add_successor(fileobject.get_object_name())
                 self.add_to_history(predecessor)
            else:
                predecessor.set_attributes(self.synergy_utils.get_all_attributes(predecessor))
                path = self.ccm_file_path.get_file_path(predecessor.get_object_name())
                if not path:
                    #Path couldn't be found object is probably not released... use path of successor
                    path = fileobject.get_path()
                predecessor.set_path(path)
                #print "Object", predecessor.get_object_name(), "path:", path
                predecessor.add_successor(fileobject.get_object_name())
                self.recursive_get_history(predecessor, stop_at_release)
                self.add_to_history(predecessor)

    def sort_releases_by_create_time(self, releases):
        rels = [(r['objectname'], datetime.strptime(r['create_time'], "%a %b %d %H:%M:%S %Y")) for r in releases]
        r = sorted(rels, key=itemgetter(1), reverse=True)
        sorted_releases = [rel[0] for rel in r]
        return sorted_releases

    def project_is_some_predecessor(self, project, stop_at_release):
        ret_val = False
        successors = self.ccm.query("has_baseline_project('{0}') and status='released'".format(project)).format("%objectname").run()
        for successor in successors:
            successor = successor['objectname']
            if successor == stop_at_release:
                return True
            else:
                ret_val = self.project_is_some_predecessor(successor, stop_at_release)

        return ret_val

    def successor_is_released(self, predecessor, fileobject, release):
        ret_val = False
        successors = self.ccm.query("is_successor_of('{0}')".format(predecessor.get_object_name())).format("%owner").format("%status").format("%create_time").format("%task").run()
        for s in successors:
            if s['objectname'] is not fileobject.get_object_name():
                s = FileObject.FileObject(s['objectname'], predecessor.get_separator(), s['owner'], s['status'], s['create_time'], s['task'])
                #check releases of successor
                releases = self.ccm.query("has_member('{0}') and status='released'".format(s.get_object_name())).format('%objectname').format('%create_time').run()
                if release in [r['objectname'] for r in releases if r['objectname'] == release]:
                    ret_val = True
                else:
                    retval = self.successor_is_released(s, fileobject, release)
        return ret_val



class SynergyUtils(object):
    """Misc synergy utils"""

    def __init__(self, ccm):
        self.ccm = ccm
        self.unwanted_attributes = ['_archive_info', '_modify_time', 'binary_scan_file_time',
        'cluster_id', 'comment',  'create_time', 'created_in', 'cvtype', 'dcm_receive_time',
        'handle_source_as', 'is_asm', 'is_model', 'local_to', 'modify_time', 'name',
        'owner', 'project', 'release', 'source_create_time', 'source_modify_time',
        'status', 'subsystem', 'version', 'wa_type', '_relations', 'est_duration',
        'groups' , 'platform', 'priority', 'task_subsys' ]


    def get_all_attributes(self, obj):
        attr_list = self.ccm.attr(obj.get_object_name()).option('-l').run().splitlines()
        attributes = {}
        for attr in attr_list:
            attr = attr.partition(' ')[0]
            if attr not in self.unwanted_attributes:
                attributes[attr] = self.ccm.attr(obj.get_object_name()).option('-s').option(attr).run()
        return attributes


    def get_dir_changes(self, fileobject, predecessor):
        diff = self.ccm.diff(fileobject.get_object_name(), predecessor.get_object_name()).run().splitlines()
        deleted = []
        new = []
        for line in diff:
            if line.startswith('<'):
                deleted.append(line.split()[1])
            if line.startswith('>'):
                new.append(line.split()[1])
        content = {'deleted': deleted, 'new' : new}
        print fileobject.get_object_name(), content
        return content














