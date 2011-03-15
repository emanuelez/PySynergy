#!/usr/bin/env python
# encoding: utf-8
"""
Get object hierarchy for project as a dict:
    object_name : [path(s)]

Created by Aske Olsson 2011-03-11
Copyright (c) 2011 Nokia. All rights reserved.
"""

from SynergySession import SynergySession
from SynergyObject import SynergyObject
from collections import deque

def get_objects_in_project(project, ccm=None, database=None):
    if not ccm:
        if not database:
            raise SynergyException('No ccm instance nor database given\nCannot start ccm session!\n')
        ccm = SynergySession(database)

    delim = ccm.delim()
    queue = deque([SynergyObject(project, delim)])

    hierarchy = {}
    dir_structure = {}
    proj_lookup = {}
    cwd = ''

    while queue:
        obj = queue.popleft()
        #print 'Processing:', obj.get_object_name()
        parent_proj = None

        if obj.get_type() == 'dir':
            # Processing a dir set 'working dir'
            cwd = dir_structure[obj.get_object_name()]
            parent_proj = proj_lookup[obj.get_object_name()]

        result = get_members(obj, ccm, parent_proj)
        objects = [SynergyObject(o['objectname'], delim) for o in result]

        # if a project is being queried it might have more than one dir with the
        # same name as the project associated, find the directory that has the
        # project associated as the directory's parent
        if obj.get_type() == 'project':
            if len(objects) > 1:
                objects = find_root_project(obj, objects, ccm)

        for o in objects:
            if o.get_type() == 'dir':
                # add the directory to the queue and record its parent project
                queue.append(o)
                dir_structure[o.get_object_name()] = '%s%s/' % (cwd, o.get_name())
                if obj.get_type() == 'project':
                    proj_lookup[o.get_object_name()] = obj.get_object_name()
                elif obj.get_type() == 'dir':
                    proj_lookup[o.get_object_name()] = proj_lookup[obj.get_object_name()]
                    # Also add the directory to the Hierachy to get empty dirs
                    if o.get_object_name() in hierarchy.keys():
                        hierarchy[o.get_object_name()].append('%s%s' % (cwd, o.get_name()))
                    else:
                        hierarchy[o.get_object_name()] = ['%s%s' % (cwd, o.get_name())]
            elif o.get_type() == 'project':
                # Add the project to the queue
                queue.append(o)
            else:
                # Add the object to the hierarchy
                if obj.get_type() == 'dir':
                    if o.get_object_name() in hierarchy.keys():
                        hierarchy[o.get_object_name()].append('%s%s' % (cwd, o.get_name()))
                    else:
                        hierarchy[o.get_object_name()] = ['%s%s' % (cwd, o.get_name())]
                    #print "Object:", o.get_object_name(), 'has path:'
                    #print '%s%s' % (cwd, o.get_name())

    return hierarchy

def find_root_project(project, objects, ccm):
    delim = ccm.delim()
    for o in objects:
        result = ccm.query("has_child('{0}', '{1}')".format(o.get_object_name(), project.get_object_name())).format('%objectname').run()
        for r in result:
            if r['objectname'] == project.get_object_name():
                return [o]

def get_members(obj, ccm, parent_proj):
    if obj.get_type() == 'dir':
        objects = ccm.query("is_child_of('{0}', '{1}')".format(obj.get_object_name(), parent_proj)).format('%objectname').run()
    else:
        # For projects only get the directory of the project
        objects = ccm.query("is_member_of('{0}') and type='dir' and name='{1}'".format(obj.get_object_name(), obj.get_name())).format('%objectname').run()
    return objects

class SynergyException(Exception):
    """User defined exception raised by SynergySession"""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)



def main():
    # Test

if __name__ == '__main__':
    main()



