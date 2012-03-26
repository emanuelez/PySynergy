#!/usr/bin/env python
# encoding: utf-8
"""
FileObject.py

Created by Emanuele Zattin and Aske Olsson on 2011-01-26.
Copyright (c) 2011, Nokia
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

Neither the name of the Nokia nor the names of its contributors may be used to
endorse or promote products derived from this software without specific prior
written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.
IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import SynergyObject
from datetime import datetime

class FileObject(SynergyObject.SynergyObject):
    """ This class wraps a Synergy object with information about
        author, create time, tasks, status etc. """

    def __init__(self, objectname, delimiter, owner, status, create_time, task):
        super(FileObject, self).__init__(objectname, delimiter, owner,
                                         status, task)
        self.created_time = create_time
        self.releases = None

    def get_integrate_time(self):
        """ Get integrate time of object (commit time) """
        now = datetime.today()
        time = self.find_status_time('integrate',
                                     self.attributes['status_log'])
        if now <= time:
            # Try checkpoint attribute
            time = self.find_status_time('checkpoint',
                                         self.attributes['status_log'])
        else:
            # Last resort inaccurate time, but might be better than now
            # working attribute
            time = self.find_status_time('working', self.attributes['status_log'])
        return time

    def set_attributes(self, attributes):
        """ Set attributes """
        self.attributes = attributes

    def get_releases(self):
        """ Get releases """
        return self.releases

    def set_releases(self, releases):
        """ Set Releases """
        self.releases = releases

