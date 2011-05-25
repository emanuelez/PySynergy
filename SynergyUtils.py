#!/usr/bin/env python
# encoding: utf-8
"""
SynergyUtils.py

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

import SynergyObject
import ccm_cache
import re
from itertools import product

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
                p = re.compile("^(.+)-(.+?)@(.*)$")
                m = p.match(s)
                if m:
                    path = m.group(1)
                    #childversion = m.group(2)
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

    def task_in_project(self, task, project):
        # option 1: check if task is used in released project:
        ret_val = self.task_used_in_project(task, project)
        if not ret_val:
            # option 2: check the reconfigure properties of the projects
            ret_val = self.task_in_rp_of_project(task, project)
        if not ret_val:
            # option 3: check if task is in the project's own baseline
            ret_val = self.task_in_baseline_of_project(task, project)
        return ret_val

    def task_used_in_project(self, task, project):
        projects = task.get_released_projects()
        for p in projects:
            if project.get_object_name() in p:
                #print "used in:", p
                return True
        return False

    def task_in_rp_of_project(self, task, project):
        tasks = project.get_tasks_in_rp()
        for t in tasks:
            if task.get_object_name == t:
                return True
        return False

    def task_in_baseline_of_project(self, task, project):
        # check if the task is in same baseline as project
        proj_baselines = project.get_baselines()
        task_baselines = task.get_baselines()
        common_baselines = set(proj_baselines).intersection(set(task_baselines))
        if common_baselines:
            return True
        return False

    def fill_task_info(self, task):
        print "Fetching task info", task.get_object_name()
        #Find related task (s30)
        related_task = self.ccm.query("has_task_in_CUIinsp('{0}')".format(task.get_object_name())).format('%objectname').format("%owner").format("%status").format("%create_time").format("%task").run()

        for t in related_task:
            insp_task = ccm_cache.get_object(t['objectname'], self.ccm)
            if task.attributes.has_key('inspection_tasks'):
                #update the tasks
                task.attributes['inspection_tasks'].update({insp_task.get_display_name() : insp_task.attributes})
            else:
                #add the inspection task
                task.attributes.update({'inspection_tasks': {insp_task.get_display_name() : insp_task.attributes}})


class ObjectHistory(object):
    """ Get the history of one object backwards in time """

    def __init__(self, ccm, current_release, old_objects, old_release = None, new_projects=None, old_projects=None):
        self.ccm = ccm
        self.history = {}
        self.temp_history = {}
        self.current_release = current_release
        self.old_release = old_release
        self.release_lookup = {}
        self.successor_chain_lookup ={}
        self.old_objects = old_objects
        self.old_subproject_list = old_projects
        if old_projects:
            print "Length of old subproject list %d" % len(self.old_subproject_list)
        self.current_subproject_list = new_projects
        print "Length of current subproject list %d" % len(self.current_subproject_list)

    def get_history(self, fileobject, paths):
        recursion_depth = 1
        print 'Processing:', fileobject.get_object_name(), "from", self.current_release, "to", self.old_release

        # clear old history
        self.history = {}
        self.temp_history = {}
        fileobject.set_path(paths)

        if self.current_release != self.old_release and self.old_release is not None:
            # Check if a newer version of the file was already released
            old_objects = [o for o in self.old_objects if fileobject.get_name() in o and fileobject.get_type() in o and fileobject.get_instance() in o]
            print "old objects: %s" % old_objects
            old_object_is_in_newer_release = False
            for o in old_objects:
                old_object = SynergyObject.SynergyObject(o, fileobject.get_separator())
                old_object_is_in_newer_release = self.check_successor_chain_for_object(fileobject, old_object, 0)
            if not old_object_is_in_newer_release or len(old_objects) == 0:
                history_ok = self.recursive_get_history(fileobject, recursion_depth)
            else:
                history_ok = False

            if history_ok:
                # Add temp_history to real history dictionary
                self.history.update(self.temp_history)
            else:
                print "history marked not ok"
                print "history was:"
                for o in self.temp_history.values():
                    for s in o.get_successors():
                        print '%s -> %s' %(o.get_object_name(), s)
                print ''

        print "Filepath:", paths
        print ""
        self.history[fileobject.get_object_name()] = fileobject

        return self.history

    def add_to_history(self, fileobject):
        self.temp_history[fileobject.get_object_name()] = fileobject

    def recursive_get_history(self, fileobject, recursion_depth):
        """ Recursivly find the history of the file object, optionally stopping at the 'old_release' project """
        next_iter = False
        print ""
        print 'Processing:', fileobject.get_object_name(), fileobject.get_status()
        print 'Recursion depth %d' % recursion_depth
        retval = True
        #Check if recursion_depth is reached
        if recursion_depth > 20:
            print 'Giving up on %s' % fileobject.get_object_name()

            return False
        recursion_depth += 1

        predecessors = fileobject.get_predecessors()
        for p in predecessors:
            try:
                predecessor = ccm_cache.get_object(p, self.ccm)
            except ccm_cache.ObjectCacheException:
                # Object couldn't be retrived from ccm, give up on this
                print "Couldn't get %s from Synergy" %p
                return True
            print "Predecessor:", predecessor.get_object_name()

            # check predecessor release to see if this object should be added to the set.
            if self.old_release:
                # Get the release(s) for the predecessor
                releases = predecessor.get_releases()
                if releases:
                    # Check if the "old" release is the the releases for the predecessor and stop if true
                    if [r for r in releases if r in self.current_subproject_list or r in self.old_subproject_list]:
                        # Object is already released, continue with the next predecessor
                        print predecessor.get_object_name(), "is already released"
                        continue
                    print "Couldn't find release in current_subproject_list or old_subproject_list"

                    #Check if chain of successors contains previous object - if true discard the chain
                    if self.successor_is_released(predecessor, fileobject, 0):
                        print "Successor is already released", fileobject.get_object_name()
                        continue

                    #Check if projects are releated to old release. Latest first
                    for r in releases:
                        project = ccm_cache.get_object(r, self.ccm)
                        if self.project_is_some_predecessor(project, 0):
                            print "Found Relationship between:", project.get_object_name(), "and", self.old_release
                            next_iter = True
                            break
                    if next_iter:
                        continue
                else:
                    #Check if a successor is released
                    if self.successor_is_released(predecessor, fileobject, 0):
                        print "Successor is already released", fileobject.get_object_name()
                        continue

            # Check if predecessor is already added to history - if so add this as successor to fileobject, else add new predecessor to history
            if not self.temp_history.has_key(predecessor.get_object_name()):
                print "Adding", predecessor.get_object_name(), predecessor.get_status(),  "to history"
                path = fileobject.get_path()
                predecessor.set_path(path)
                self.add_to_history(predecessor)
                retval &= self.recursive_get_history(predecessor, recursion_depth)
                if not retval:
                    # Giving up on history break out of loop
                    break
        return retval

    def project_is_some_predecessor(self, project, recursion_depth):
        if recursion_depth > 20:
            return False
        recursion_depth += 1
        print "Checking if", project.get_object_name(), "is some predecessor of", self.current_release, "or", self.old_release, "..."
        successors = project.get_baseline_successor()
        for successor in successors:
            print "successor:", successor
            if successor in self.old_subproject_list:
                print "Found", successor, "in previous subprojects"
                return True
            elif successor in self.current_subproject_list:
                print "Found", successor, "in current subprojects"
                return True
            else:
                successor = ccm_cache.get_object(successor, self.ccm)
                if self.project_is_some_predecessor(successor, recursion_depth):
                    return True
        return False

    def successor_is_released(self, predecessor, fileobject, recursion_depth):
        if recursion_depth > 20:
            return False
        recursion_depth += 1
        print "Checking if successor is released, for", fileobject.get_object_name(), "by predecessor", predecessor.get_object_name()
        ret_val = False
        successors = predecessor.get_successors()
        for s in successors:

            if s in self.release_lookup.keys():
                return self.release_lookup[s]
            if s != fileobject.get_object_name():
                successor = ccm_cache.get_object(s, self.ccm)
                print "successor:", successor.get_object_name()
                #check releases of successor
                releases = successor.get_releases()
                if [r for r in releases if r in self.old_subproject_list]:
                    print "successor:", successor.get_object_name(), "is released"
                    self.release_lookup[successor.get_object_name()] = True
                    return True
                elif [r for r in releases if r in self.current_subproject_list]:
                    print "successor:", successor.get_object_name(), "is released in current project, don't continue"
                    self.release_lookup[successor.get_object_name()] = False
                    return False
                else:
                    ret_val = self.successor_is_released(successor, fileobject, recursion_depth)
                    self.release_lookup[successor.get_object_name()] = ret_val
            else:
                # if there is only one successor and it is the fileobject assume it to be released if the predecessor is in released state
                if len(successors) == 1 and predecessor.get_status() == 'released':
                    return True

        return ret_val

    def check_successor_chain_for_object(self, 	fileobject, old_object, recursion_depth):
        if recursion_depth > 10:
            return False
        recursion_depth += 1
        print "Checking if successor chain for %s contains %s" % (fileobject.get_object_name(), old_object.get_object_name())
        ret_val = False
        successors = fileobject.get_successors()
        for s in successors:
            if s == old_object.get_object_name():
                return True
            successor = ccm_cache.get_object(s, self.ccm)
            print "successor:", successor.get_object_name()
            ret_val = self.check_successor_chain_for_object(successor, old_object, recursion_depth)
            if ret_val:
                    break
        return ret_val
