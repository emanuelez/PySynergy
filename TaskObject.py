#!/usr/bin/env python
# encoding: utf-8
"""
TaskObject.py

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
#import SynergySession

from datetime import datetime

class TaskObject(SynergyObject.SynergyObject):
    """ This class wraps a Synergy object with information about author, create time, tasks, status etc. """

    def __init__(self, objectname, delimiter, owner, status, create_time, task):
        super(TaskObject, self).__init__(objectname, delimiter, owner, status, task)
        self.created_time = create_time
        self.synopsis = None
        self.description = None
        self.release = None
        self.objects = None
        self.complete_time = None
        self.released_projects = None
        self.baselines = None


    def get_display_name(self):
        name = [self.get_instance(), "#", self.get_name().strip('task')]
        return ''.join(name)

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

    def get_released_projects(self):
        return self.released_projects

    def set_released_projects(self, released_projects):
        self.released_projects = released_projects

    def get_baselines(self):
        return self.baselines

    def set_baselines(self, baselines):
        self.baselines = baselines

    def set_attributes(self, attributes):
        self.attributes = attributes
        self.complete_time = self.find_status_time('complete', self.attributes['status_log'], self.instance)
        if 'task_description' in self.attributes.keys():
            self.description = self.attributes['task_description']
        if 'task_number' in self.attributes.keys():
            self.attributes['task_number'] = self.get_display_name()

    def find_status_time(self, status, status_log, db):
        earliest = datetime.today()
        for line in status_log.splitlines():
            if status in line and db in line:
                time = datetime.strptime(line.partition(': Status')[0], "%a %b %d %H:%M:%S %Y")
                if time < earliest:
                    earliest = time

        return earliest