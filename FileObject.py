#!/usr/bin/env python
# encoding: utf-8
"""
FileObject.py

Created by Emanuele Zattin and Aske Olsson on 2011-01-26.
Copyright (c) 2011 Nokia. All rights reserved.
"""

import SynergyObject

#from datetime import datetime

class FileObject(SynergyObject.SynergyObject):
    """ This class wraps a Synergy object with information about author, create time, tasks, status etc. """

    def __init__(self, objectname, delimiter, owner, status, create_time, task):
        super(FileObject, self).__init__(objectname, delimiter, owner, status, task)
        self.created_time = create_time
        self.content = None
        self.commit_message = None
        self.path = None
        self.releases = None

    def get_integrate_time(self):
        return self.find_status_time('integrate', self.attributes['status_log'])

    def get_path(self):
        return self.path

    def set_path(self, path):
        self.path = path

    def set_attributes(self, attributes):
        self.attributes = attributes

    def get_releases(self):
        return self.releases

    def set_releases(self, releases):
        self.releases = releases