#!/usr/bin/env python
# encoding: utf-8
"""
FileObject.py

Created by Emanuele Zattin and Aske Olsson on 2011-01-26.
Copyright (c) 2011 Nokia. All rights reserved.
"""

import SynergyObject

from datetime import datetime

class FileObject(SynergyObject.SynergyObject):
    """ This class wraps a Synergy object with information about author, create time, tasks, status etc. """

    def __init__(self, objectname, delimiter, owner, status, create_time, task):
        super(FileObject, self).__init__(objectname, delimiter, owner, status, create_time, task)
        self.content = None
        self.commit_message = None
        self.integrate_time = None
        self.predecessors = None
        self.successors = None
        self.path = None
        self.dir_changes = None


    def get_integrate_time(self):
        return self.integrate_time

    def set_integrate_time(self, time):
        self.integrate_time = time

    def get_predecessors(self):
        return self.predecessors

    def set_predecessors(self, predecessors):
        self.predecessors = predecessors

    def add_predecessor(self, predecessor):
        if self.predecessors is None:
            self.predecessors = [predecessor]
        else:
            self.predecessors.append(predecessor)

    def set_successors(self, successors):
        self.successors = successors

    def add_successor(self, successor):
        if self.successors is None:
            self.successors = [successor]
        else:
            self.successors.append(successor)

    def get_successors(self):
        return self.successors

    def get_path(self):
        return self.path

    def set_path(self, path):
        self.path = path

    def get_content(self):
        return self.content

    def set_content(self, content):
        self.content = content

    def set_dir_changes(self, dir_changes):
        self.dir_changes = dir_changes

    def get_dir_changes(self):
        return self.dir_changes

    def add_dir_changes(self, dir_changes):
        if self.dir_changes:
        #append new changes
            for k in dir_changes:
                l1 = dir_changes[k]
                l2 = self.dir_changes[k]
                l1.extend(l2)
                self.dir_changes[k] = list(set(l1))
        else:
            self.dir_changes = dir_changes

    def set_attributes(self, attributes):
        self.attributes = attributes
        self.integrate_time = self.find_status_time('integrate', self.attributes['status_log'])
        #self.content = self.attributes['source']
        #self.commit_message = self.find_commit_message_from_content()

    def get_attributes(self):
        return attributes


    def find_status_time(self, status, status_log):
        earliest = datetime.today()
        for line in status_log.splitlines():
            if status in line and 'ccm_root' not in line:
                time = datetime.strptime(line.partition(': Status')[0], "%a %b %d %H:%M:%S %Y")
                if time < earliest:
                    earliest = time

        return earliest

    def find_commit_message_from_content(self):
        start = self.content.find('REASON')
        newline_end = self.content.find('\n\n', start)
        version_end = self.content.find('VERSION', start)
        if newline_end != -1 and version_end != -1 and newline_end < version_end:
            end = newline_end
        else:
            end = version_end

        if start != -1 and end != -1:
            return self.content[start:end]
        return ''



