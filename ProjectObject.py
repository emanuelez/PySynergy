#!/usr/bin/env python
# encoding: utf-8
"""
ProjectObject.py

Created by Aske Olsson on 2011-05-05.
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

from SynergyObject import SynergyObject

class ProjectObject(SynergyObject):
    """ This class wraps a Synergy project object with information about author, create time, tasks, status etc. """

    def __init__(self, objectname, delimiter, owner, status, create_time, task):
        super(ProjectObject, self).__init__(objectname, delimiter, owner, status, task)
        self.created_time = create_time
        self.baseline_predecessor = []
        self.baseline_successor = []
        self.tasks_in_rp = None
        self.baselines = None
        self.released_time = datetime.min
        self.members = None


    def get_baseline_predecessor(self):
        return self.baseline_predecessor

    def set_baseline_predecessor(self, baseline_predecessor):
        self.baseline_predecessor = baseline_predecessor

    def get_baseline_successor(self):
        return self.baseline_successor

    def set_baseline_successor(self, baseline_successor):
        self.baseline_successor = baseline_successor

    def get_baselines(self):
        return self.baselines

    def set_baselines(self, baselines):
        self.baselines = baselines

    def get_tasks_in_rp(self):
        return self.tasks_in_rp

    def set_tasks_in_rp(self, tasks_in_rp):
        self.tasks_in_rp = tasks_in_rp

    def set_attributes(self, attributes):
        self.attributes = attributes
        self.released_time = self.find_status_time('released', self.attributes['status_log'])

    def get_members(self):
        return self.members

    def set_members(self, members):
        self.members = members
        
