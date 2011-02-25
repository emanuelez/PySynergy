#!/usr/bin/env python
# encoding: utf-8
"""
SynergyObject.py

Created by Emanuele Zattin and Aske Olsson on 2011-01-26.
Copyright (c) 2011 Nokia. All rights reserved..
"""
from datetime import datetime

import re

class SynergyObject(object):
    """ This class wraps a basic Synergy object i.e. four-part-name """
    
    def __init__(self, objectname, delimiter, owner, status, create_time, task):
        self.set_separator(delimiter.rstrip())

        p = re.compile(self.get_object_name_pattern())
        m = p.match(objectname)
        if m:
            self.name = m.group(1)
            self.version = m.group(2)
            self.type = m.group(3)
            self.instance = m.group(4)
        else :
            raise SynergySession.SynergyException('The provided description ' + description + ' is not an objectname')
        
        self.author = owner
        self.status = status
        self.created_time = datetime.strptime(create_time, "%a %b %d %H:%M:%S %Y")
        self.tasks = task
        
            
    def get_separator(self):
        return self.separator

    def set_separator(self, separator):
        self.separator = separator
        
    def get_object_name_pattern(self):
        return "(.+)" + self.separator + "(.+):(.+):(.+)"
    
    def get_display_name_pattern(self):
        return "(.+)#(.+)"
    
    def get_name(self):
        return self.name
    
    def set_name(self, name):
        self.name = name
    
    def get_version(self):
        return self.version
    
    def set_version(self, version):
        self.version = version
    
    def get_type(self):
        return self.type
    
    def set_type(self, type):
        self.type = type
    
    def get_instance(self):
        return self.instance
    
    def set_instance(self, instance):
        self.instance = instance
        
    def get_object_name(self):
        return self.name + self.separator + self.version + ":" +  self.type + ":" + self.instance
    
    def get_author(self):
        return self.author
    
    def get_status(self):
        return self.status
    
    def get_created_time(self):
        return self.created_time
    
    def get_tasks(self):
        return self.tasks
    
