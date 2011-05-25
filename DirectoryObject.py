#!/usr/bin/env python
# encoding: utf-8
"""
DirectoryObject.py

Created by Aske Olsson on 2011-05-09.
Copyright (c) 2011, Nokia
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
from FileObject import FileObject

class DirectoryObject(FileObject):
    """ This class wraps a Synergy directory object with information about deleted/new items """

    def __init__(self, objectname, delimiter, owner, status, create_time, task):
        super(DirectoryObject, self).__init__(objectname, delimiter, owner, status, create_time, task)
        self.new_objects = None
        self.deleted_objects = None

    def set_new_objects(self, new_objects):
        self.new_objects = new_objects

    def get_new_objects(self):
        return self.new_objects

    def set_deleted_objects(self, deleted_objects):
        self.deleted_objects = deleted_objects

    def get_deleted_objects(self):
        return self.deleted_objects
