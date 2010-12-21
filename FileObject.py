#!/usr/bin/env python
# encoding: utf-8
"""
FileObject.py

Created by Aske Olsson 2010-12-10.
Copyright (c) 2010 Aske Olsson. All rights reserved.
"""

import SynergyObject

from datetime import datetime

class FileObject(SynergyObject.SynergyObject):
    """ This class wraps a Synergy object with information about author, create time, tasks, status etc. """
    
    def __init__(self, objectname, delimiter, owner, status, create_time, task):
        super(FileObject, self).__init__(objectname, delimiter, owner, status, create_time, task)
        self.content = None
        self.commit_msg = None
        self.integrate_time = None
        self.predecessors = None
        self.successors = None
        
                
    def get_integrate_time(self):
        if self.integrate_time is None:
            return "Not defined"
        else:
            return self.integrate_time
    
    def set_integrate_time(self, time):
        self.integrate_time = time
    
    def get_predecessors(self):
        if self.predecessors is None:
            return "Not defined"
        else:
            return self.predecessors
    
    def set_predecessors(self, predecessors):
        self.predecessors = predecessors
       
    def add_predecessor(self, predecessor):
        if self.predecessors is None:
            self.predecessors = [predecessor]
        else:
            self.predecessors.append(predecessor)

    def add_successor(self, successor):
        if self.successors is None:
            self.successors = [successor]
        else:
            self.successors.append(successor)
            
    def get_successors(self):
        if self.successors is None:
            return "Not defined"
        else:
            return self.successors        
            
    def get_path(self):
        return self.path
    
    def set_path(self, path):
        self.path = path
            
    def get_content(self):
        return self.content
    
    def set_content(self, content):
        self.content = content
        
    def get_commit_message(self):
        return self.commit_msg
    
    def set_commit_message(self, msg):
        self.commit_msg = msg
            
    def print_status(self):
        print "Object information:"   
        print "Name:", self.get_name()
        print "Version:", self.get_version()
        print "Type:", self.get_type()
        print "Instance:", self.get_instance()
        print "Author:", self.get_author()
        print "Status:", self.get_status()
        print "Create time:", self.get_created_time()
        print "Integrate time:", self.get_integrate_time()
        print "Tasks:", self.get_tasks()
        print "Predecessors:", ''.join(self.get_predecessors())
        print "Successors:", ''.join(self.get_successors())
        if self.content:
            print "*****\n"
            #print self.content
            print "*****\n"
            
            

