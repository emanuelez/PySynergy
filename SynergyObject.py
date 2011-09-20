#!/usr/bin/env python
# encoding: utf-8
"""
SynergyObject.py

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

from datetime import datetime

import re
from SynergySession import SynergyException

class SynergyObject(object):
    """ This class wraps a basic Synergy object i.e. four-part-name """

    def __init__(self, objectname, delimiter, owner=None, status=None, task=None):

        self.set_separator(delimiter.rstrip())

        p = re.compile(self.get_object_name_pattern())
        m = p.match(objectname)
        if m:
            self.name = m.group(1)
            self.version = m.group(2)
            self.type = m.group(3)
            self.instance = m.group(4)
        else :
            raise SynergyException("The provided description %s is not an objectname" % objectname)

        self.author = owner
        self.status = status
        self.created_time = datetime.min
        self.tasks = task
        self.predecessors = []
        self.successors = []
        self.attributes = None
        self.info_databases = []

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

    def get_predecessors(self):
        return self.predecessors

    def set_predecessors(self, predecessors):
        self.predecessors = predecessors

    def get_successors(self):
        return self.successors

    def set_successors(self, successors):
        self.successors = successors

    def get_attributes(self):
        return self.attributes

    def set_attributes(self, attributes):
        self.attributes = attributes
        
    def find_status_time(self, status, status_log):
        earliest = datetime.today()
        for line in status_log.splitlines():
            if status in line and 'ccm_root' not in line:
                time = datetime.strptime(line.partition(': Status')[0], "%a %b %d %H:%M:%S %Y")
                if time < earliest:
                    earliest = time
        return earliest