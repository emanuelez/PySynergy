#!/usr/bin/env python
# encoding: utf-8
"""
SynergyUtils.py

Created by Emanuele Zattin and Aske Olsson on 2011-01-26.
Copyright (c) 2011 Nokia. All rights reserved.
"""

import SynergySession
import FileObject
import TaskObject
from datetime import datetime
import re
from operator import itemgetter
from itertools import product
import os.path
import os

class CCMFilePath(object):
    """Get the file path of an object from Synergy"""

    def __init__(self, ccm):

        self.ccm = ccm
        self.top_reached = None
        self.delim = self.ccm.delim()
        self.path_lookup = {}
        #self.project_lookup = {}

    def get_path(self, object_name, current_release):
        # Get the path of object
        self.top_reached = None
        self.current_release = current_release
        result = self.recurse_file_path(object_name)
        return result


    def recurse_file_path(self, object_name):
        ret_val = None
        #print "Object:", object_name
        result = self.ccm.finduse(object_name).option("-released_proj").run().splitlines()
        #lets first try to see if any of the cached projects are already in the list
        r = [(k,j) for (k,j) in product(self.path_lookup.keys(), result) if k in j]
        if r:
            print "Trying", r[0][1], "first for", object_name
            #put the matching project to end of array
            result.remove(r[0][1])
            result.append(r[0][1])

        #reverse the list, as the matching project is mostly in the latter part
        result.reverse()
        for s in result:
            if not self.top_reached:
                s = s.strip()
                # match
                p = re.compile("^(.+?)-(.+?)@(.*)$")
                m = p.match(s)
                if m:
                    path = m.group(1)
                    childversion = m.group(2)
                    parentproject = m.group(3)

                    if parentproject == self.current_release:
                        #print 'Top reached'
                        self.top_reached = 1
                        # add to lookup table
                        self.path_lookup[object_name] = path
                        return path
                    else:
                        #try lookup table
                        if parentproject in self.path_lookup.keys():
                            #print "Path cached for:", object_name, self.path_lookup[parentproject]
                            self.top_reached = 1
                            # Add remaning path
                            p = [self.path_lookup[parentproject]]
                            p.extend(path.split('/')[1:])
                            p = '/'.join(p)
                            return p

                        if ':project:' not in parentproject:
                            #Sometimes the greatness of Synergy will return a name-version instead of a four-part-name, so convert it into a four-part-name:
                            splitted_name = parentproject.split(self.delim)
                            fourpart = self.ccm.query("name='{0}' and version='{1}' and type='project'".format(splitted_name[0], splitted_name[1])).format('%objectname').run()
                            if fourpart:
                                parentproject = fourpart[0]['objectname']

                        parent = self.recurse_file_path(parentproject)
                        if parent:
                            p = [parent]
                            p.extend(path.split('/')[1:])
                            p = '/'.join(p)
                            #Only add path and  if we are processing a project
                            if ':project:' in object_name:
                                # add this project to lookup table with complete path
                                self.path_lookup[object_name] = p
                            return p

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
        print "Fetching task info", task.get_object_name()
        task.set_attributes(self.synergy_utils.get_all_attributes(task))
        #Find related task (s30)
        releated_task = self.ccm.query("has_task_in_CUIinsp('{0}')".format(task.get_object_name())).format('%objectname').format("%owner").format("%status").format("%create_time").format("%task").run()
        #There should be only one releated task - inspection task
        if len(releated_task) == 1:
            insp_task = TaskObject.TaskObject(releated_task[0]['objectname'], self.delim, releated_task[0]['owner'], releated_task[0]['status'], releated_task[0]['create_time'], releated_task[0]['task'])
            attributes = self.synergy_utils.get_all_attributes(insp_task)
            task.get_attributes().update({'inspection_task': attributes})

        task_objects = self.ccm.task(task.get_tasks(), True).option('-sh').option('obj').format("%objectname").format("%owner").format("%status").format("%create_time").format("%task").run()

        current_task_objects = task.get_objects()
        for o in task_objects:
            if o['objectname'] not in current_task_objects:
                print "object:", o['objectname'], "not found in objects, but associated to:", task.get_object_name()
                #fileobject = FileObject.FileObject(o['objectname'], self.delim, o['owner'], o['status'], o['create_time'], o['task'])
                #content = self.ccm.cat(fileobject.get_object_name()).run()
                #fileobject.set_content(content)
                #fileobject.set_attributes(self.synergy_utils.get_all_attributes(fileobject))
                #predecessors = self.ccm.query("is_predecessor_of('{0}')".format(fileobject.get_object_name())).format("%owner").format("%status").format("%create_time").format("%task").format("%objectname").run()
                #for p in predecessors:
                #    predecessor = FileObject.FileObject(p['objectname'], fileobject.get_separator(), p['owner'], p['status'], p['create_time'], p['task'])
                #    fileobject.add_predecessor(predecessor.get_object_name())
                #    if fileobject.get_type() == 'dir':
                #        fileobject.add_dir_changes(self.synergy_utils.get_dir_changes(fileobject, predecessor))
                #        if fileobject.get_dir_changes():
                #            print "Directory changes:"
                #            print "Deleted objects:", ', '.join(fileobject.get_dir_changes()['deleted'])
                #            print "New objects:    ", ', '.join(fileobject.get_dir_changes()['new'])
                #successors = self.ccm.query("is_successor_of('{0}')".format(fileobject.get_object_name())).format("%objectname").run()
                #for s in successors:
                #    fileobject.add_successor(s['objectname'])
                ##print fileobject.get_object_name()
                #task.add_object(fileobject)

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

    def __init__(self, ccm, current_release, old_release = None):
        self.ccm = ccm
        self.delim = ccm.delim()
        self.history = {}
        self.synergy_utils = SynergyUtils(self.ccm)
        self.current_release = current_release
        self.ccm_file_path = CCMFilePath(ccm)
        self.old_release = old_release
        self.dir = 'data/' + self.current_release.split(self.delim)[1].split(':')[0]
        self.release_lookup = {}
        if old_release:
            #Fill subproject old list
            sub = self.ccm.query("recursive_is_member_of('{0}', 'none') and type='project'".format(old_release)).format('%objectname').run()
            self.old_subproject_list = [s['objectname'] for s in sub]
            self.old_subproject_list.append(old_release)
        #Fill subproject current list
        sub = self.ccm.query("recursive_is_member_of('{0}', 'none') and type='project'".format(current_release)).format('%objectname').run()
        self.current_subproject_list = [s['objectname'] for s in sub]
        self.current_subproject_list.append(current_release)


    def get_history(self, fileobject):
        #print ""
        print 'Processing:', fileobject.get_object_name(), "from", self.current_release, "to", self.old_release

        # clear old history
        self.history = {}
        path = self.ccm_file_path.get_path(fileobject.get_object_name(), self.current_release)

        fileobject.set_path(path)
        content = self.ccm.cat(fileobject.get_object_name()).run()
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        f = open(self.dir + '/' + fileobject.get_object_name(), 'wb')
        f.write(content)
        f.close()

        fileobject.set_attributes(self.synergy_utils.get_all_attributes(fileobject))

        if self.old_release == self.current_release:
            #handle directory objects
            if fileobject.get_type() == 'dir':
                #get predecessors and do a diff on dir objects
                predecessors = self.ccm.query("is_predecessor_of('{0}')".format(fileobject.get_object_name())).format("%owner").format("%status").format("%create_time").format("%task").run()
                for p in predecessors:
                    predecessor = FileObject.FileObject(p['objectname'], fileobject.get_separator(), p['owner'], p['status'], p['create_time'], p['task'])
                    fileobject.add_dir_changes(self.synergy_utils.get_dir_changes(fileobject, predecessor))
                if fileobject.get_dir_changes():
                    print "Directory changes:"
                    print "Deleted objects:", ', '.join(fileobject.get_dir_changes()['deleted'])
                    print "New objects:    ", ', '.join(fileobject.get_dir_changes()['new'])
        else:
            self.recursive_get_history(fileobject)
        print "Filepath:", path
        print ""
        self.history[fileobject.get_object_name()] = fileobject


        return self.history

    def add_to_history(self, fileobject):
        self.history[fileobject.get_object_name()] = fileobject

    def recursive_get_history(self, fileobject):
        """ Recursivly find the history of the file object, optionally stopping at the 'old_release' project """
        next_iter = False
        delim = fileobject.get_separator()
        print ""
        print 'Processing:', fileobject.get_object_name(), fileobject.get_status()
        predecessors = self.ccm.query("is_predecessor_of('{0}')".format(fileobject.get_object_name())).format("%owner").format("%status").format("%create_time").format("%task").run()
        for p in predecessors:
            predecessor = FileObject.FileObject(p['objectname'], delim, p['owner'], p['status'], p['create_time'], p['task'])
            print "Predecessor:", predecessor.get_object_name()

            #handle directory objects
            if fileobject.get_type() == 'dir':
                fileobject.add_dir_changes(self.synergy_utils.get_dir_changes(fileobject, predecessor))
                if fileobject.get_dir_changes():
                    print "Directory changes:"
                    print "Deleted objects:", ', '.join(fileobject.get_dir_changes()['deleted'])
                    print "New objects:    ", ', '.join(fileobject.get_dir_changes()['new'])
            fileobject.add_predecessor(predecessor.get_object_name())

            # get toplevel project / toplevel release and path for predecessor
            path = self.ccm_file_path.get_path(predecessor.get_object_name(), self.old_release)
            # check predecessor release to see if this object should be added to the set.
            if self.old_release:

                # Get the release(s) for the predecessor
                releases = self.ccm.query("has_member('{0}') and status='released'".format(predecessor.get_object_name())).format('%objectname').format('%create_time').run()
                if releases:
                    #print '\n'.join([r['objectname'] for r in releases])
                    # Check if the "old" release is the the releases for the predecessor and stop if true
                    if [r['objectname'] for r in releases if r['objectname'] in self.current_subproject_list or r['objectname'] in self.old_subproject_list]:
                        # Object is already released, continue with the next predecessor
                        print predecessor.get_object_name(), "is already released"
                        continue
                    #Check if projects are releated to old release. Latest first
                    rels = self.sort_releases_by_create_time(releases)
                    for r in rels:
                        if self.project_is_some_predecessor(r):
                            print "Found Relationship between:", r, "and", self.old_release
                            next_iter = True
                            break
                    if next_iter:
                        continue
                else:
                    #Check if a successor is released
                    if self.successor_is_released(predecessor, fileobject):
                        print "Successor is already released", fileobject.get_object_name()
                        continue



             # Check if predecessor is already added to history - if so add this as successor to fileobject, else add new predecessor to history
            if self.history.has_key(predecessor.get_object_name()):
                print "Updating", predecessor.get_object_name(), predecessor.get_status(),  "in history. Path:", path
                predecessor = self.history[predecessor.get_object_name()]
                predecessor.add_successor(fileobject.get_object_name())
                self.add_to_history(predecessor)
            else:
                print "Adding", predecessor.get_object_name(), predecessor.get_status(),  "to history. Path:", path
                predecessor.set_attributes(self.synergy_utils.get_all_attributes(predecessor))
                if not path:
                    #Path couldn't be found object is probably not released... use path of successor as that is the one we have...
                    path = fileobject.get_path()

                predecessor.set_path(path)
                content = self.ccm.cat(predecessor.get_object_name()).run()
                #predecessor.set_content(content)
                if not os.path.exists(self.dir):
                    os.makedirs(self.dir)
                fname = self.dir + '/' + predecessor.get_object_name()
                f = open(fname, 'wb')
                f.write(content)
                f.close()
                predecessor.add_successor(fileobject.get_object_name())
                self.recursive_get_history(predecessor)
                self.add_to_history(predecessor)

    def sort_releases_by_create_time(self, releases):
        rels = [(r['objectname'], datetime.strptime(r['create_time'], "%a %b %d %H:%M:%S %Y")) for r in releases]
        r = sorted(rels, key=itemgetter(1), reverse=True)
        sorted_releases = [rel[0] for rel in r]
        return sorted_releases

    def project_is_some_predecessor(self, project):
        print "Checking if", project, "is some predecessor of", self.current_release, "or", self.old_release, "..."
        successors = self.ccm.query("has_baseline_project('{0}') and status='released'".format(project)).format("%objectname").run()
        for successor in successors:
            successor = successor['objectname']
            print "successor:", successor
            if successor in self.old_subproject_list:
                print "Found", successor, "in previous subprojects"
                return True
            elif successor in self.current_subproject_list:
                print "Found", successor, "in current subprojects"
                return True
            else:
                if self.project_is_some_predecessor(successor):
                    return True

        return False

    def successor_is_released(self, predecessor, fileobject):
        print "Checking if successor is released, for", fileobject.get_object_name(), "by predecessor", predecessor.get_object_name()
        ret_val = False
        successors = self.ccm.query("is_successor_of('{0}')".format(predecessor.get_object_name())).format("%owner").format("%status").format("%create_time").format("%task").run()
        for s in successors:
            if s['objectname'] in self.release_lookup.keys():
                return self.release_lookup[s['objectname']]
            if s['objectname'] != fileobject.get_object_name():
                s = FileObject.FileObject(s['objectname'], predecessor.get_separator(), s['owner'], s['status'], s['create_time'], s['task'])
                print "successor:", s.get_object_name()
                #check releases of successor
                releases = self.ccm.query("has_member('{0}') and status='released'".format(s.get_object_name())).format('%objectname').format('%create_time').run()
                #print '\n'.join([r['objectname'] for r in releases])
                if [r['objectname'] for r in releases if r['objectname'] in self.old_subproject_list]:
                    print "successor:", s.get_object_name(), "is released"
                    self.release_lookup[s.get_object_name()] = True
                    return True
                elif [r['objectname'] for r in releases if r['objectname'] in self.current_subproject_list]:
                    print "successor:", s.get_object_name(), "is released in current project, don't continue"
                    return False
                    self.release_lookup[s.get_object_name()] = False
                else:
                    ret_val = self.successor_is_released(s, fileobject)
                    self.release_lookup[s.get_object_name()] = ret_val
        return ret_val



class SynergyUtils(object):
    """Misc synergy utils"""

    def __init__(self, ccm):
        self.ccm = ccm
        self.attribute_blacklist = ['_archive_info', '_modify_time', 'binary_scan_file_time',
        'cluster_id', 'comment',  'create_time', 'created_in', 'cvtype', 'dcm_receive_time',
        'handle_source_as', 'is_asm', 'is_model', 'local_to', 'modify_time', 'name',
        'owner', 'project', 'release', 'source_create_time', 'source_modify_time',
        'status', 'subsystem', 'version', 'wa_type', '_relations', 'est_duration',
        'groups' , 'platform', 'priority', 'task_subsys', 'assigner', 'assignment_date',
        'completed_id', 'completed_in', 'completion_date', 'creator', 'modifiable_in',
        'registration_date', 'source']

    def get_all_attributes(self, obj):
        attr_list = self.ccm.attr(obj.get_object_name()).option('-l').run().splitlines()
        attributes = {}
        for attr in attr_list:
            attr = attr.partition(' ')[0]
            if attr not in self.attribute_blacklist:
                print "setting attribute:", attr
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
        print content
        return content





