#!/usr/bin/env python
# encoding: utf-8
"""
user_finger.py

Created by Aske Olsson on 2011-06-28.
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
import pickle
import re
from subprocess import Popen, PIPE
import logging as logger
import user
import user_srv_factory as factory

def get_finger_configuration():
    f = open('config.p', 'rb')
    config = pickle.load(f)
    f.close()
    try:
        server = config['finger']['server']
    except KeyError:
        server = None
    try:
        username = config['finger']['user']
    except KeyError:
        username = None

    return username, server



class finger_user(object):
    def __init__(self):

        username, server = get_finger_configuration()
        if server and server != 'localhost':
            self.command_name = 'ssh'
            if username:
                self.options = [username + '@' + server, 'finger', '-mp']
            else:
                self.options = [server, 'finger', '-mp']
        else:
            self.command_name = 'finger'
            self.options = ['-mp']

    def get_user_by_uid(self, uid):
        result = {}
        # build command
        command = [self.command_name]
        command.extend(self.options)
        command.append(uid)

        try:
            res = self._run(command)
        except FingerException:
            return {}
        name = []
        for line in res.splitlines():
            if line.startswith('Login'):
                p = re.compile("Login:\s*.*\s*Name:\s*(.*)")
                m = p.match(line)
                if m:
                    name = m.group(1)
                break
        if name:
            result = {'name': name, 'mail': '.'.join(name.split(' ')) + '@' + user.get_email_domain()}
        return result


    def _run(self, command):
        p = Popen(command, stdout=PIPE, stderr=PIPE)

        # Store the result as a single string. It will be splitted later
        stdout, stderr = p.communicate()

        if stderr:
            raise FingerException('Error while running the command: %s \nError message: %s' % (command, stderr))

        return stdout

class FingerException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
    
# register ourselves to the factory
factory.register_srv('FINGER', finger_user)