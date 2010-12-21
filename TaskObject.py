#!/usr/bin/env python
# encoding: utf-8
"""
TaskObject.py

Created by Aske Olsson 2010-12-16.
Copyright (c) 2010 Aske Olsson. All rights reserved.
"""

import SynergyObject
import SynergySession

from datetime import datetime

class TaskObject(SynergyObject.SynergyObject):
    """ This class wraps a Synergy object with information about author, create time, tasks, status etc. """
    
    def __init__(self, objectname, delimiter, owner, status, create_time, task):
        super(TaskObject, self).__init__(objectname, delimiter, owner, status, create_time, task)
        
        self.synopsis = None
        self.description = None
        self.release = None
        self.objects = None
        self.complete_time = None
        
    def get_synopsis(self):
        return self.synopsis
    
    def set_synopsis(self, synopsis):
        self.synopsis = synopsis

    def get_description(self):
        return self.description
    
    def set_description(self, description):
        self.description = description

    def get_release(self):
        return self.release
    
    def set_release(self, release):
        self.release = release

    def get_objects(self):
        return self.objects
    
    def set_objects(self, objects):
        self.objects = objects
        
    def add_object(self, o):
        if self.objects is None:
            self.objects = [o]
        else:
            self.objects.append(o)
    def get_complete_time(self):
        return self.complete_time
    
    def set_complete_time(self, complete_time):
        self.complete_time = complete_time

    def print_status(self):
        print "Object information:"   
        print "Name:         ", self.get_name()
        print "Version:      ", self.get_version()
        print "Type:         ", self.get_type()
        print "Instance:     ", self.get_instance()
        print "Author:       ", self.get_author()
        print "Status:       ", self.get_status()
        print "Create time:  ", self.get_created_time()
        print "Complete time:", self.get_complete_time()
        print "Tasks:        ", self.get_tasks()
        print "Objects:      ",  '\n               '.join(sorted([o.get_object_name() for o in self.objects]))
#        print "Description:\n"
#        print self.description
        
        

