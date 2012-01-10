#!/usr/bin/env python
# encoding: utf-8
"""
User.py

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
import cPickle
import ldap
import re
from subprocess import Popen, PIPE
import logging as logger

class user(object):
    def __init__(self):
        self.lu = ldap_user()
        self.fu = finger_user()

    def get_user_by_uid(self, username):
        #try ldap
        user = self.lu.get_user_by_uid(username)

        if not user:
            # try finger...
            user = self.fu.get_user_by_uid(username)
        if not user:
            #create default
            user = {'name': username, 'mail': username + '@' + get_email_domain()}
        return user

def get_email_domain():
    f = open('config.p', 'rb')
    config = cPickle.load(f)
    f.close()
    try:
        domain = config['email_domain']
    except KeyError:
        domain = 'none.com'
    return domain

class ldap_user(object):
    """LDAP connection """

    def __init__(self):
        self.ldap = self.ldap_setup()

    def __del__(self):
        # Close the ldap session
        self.ldap.unbind_s()

    def get_user_by_uid(self, uid):
        result = {}
        if not self.ldap:
            return result

        base = "o=nokia"
        scope = ldap.SCOPE_SUBTREE
        filter = "uid=" + uid
        retrieve_attributes = None
        timeout = 0
        try:
            result_id = self.ldap.search(base, scope, filter, retrieve_attributes)
            result_type, result_data = self.ldap.result(result_id, timeout)
            if result_data:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    d = result_data[0][1] # result dict
                    if d.has_key('displayName'):
                        result['name'] = d['displayName'][0]
                    elif d.has_key('cn'):
                        result['name'] = d['cn'][0]
                    elif d.has_key('gecos'):
                        result['name'] = d['gecos'][0]

                    if d.has_key('mail'):
                        result['mail'] = d['mail'][0]
                    else:
                        if d.has_key('displayName'):
                            result['mail'] = result['name'].split(' ')[1] + '.' + result['name'].split(' ')[0] + '@' + get_email_domain()

        except ldap.LDAPError, error_message:
            logger.warning(error_message)

        return result


    def ldap_setup(self):
        username, password, server = self.get_ldap_configuration()
        if username:
            l = ldap.open(server)
            l.simple_bind_s(username, password)
            return l
        else:
            return None


    def get_ldap_configuration(self):
        f = open('config.p', 'rb')
        config = cPickle.load(f)
        f.close()
        try:
            username = config['username']
            password = config['password']
            server = config['server']
        except KeyError:
            username = None
            password = None
            server = None
        return username, password, server


def get_finger_configuration():
    f = open('config.p', 'rb')
    config = cPickle.load(f)
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
            result = {'name': name, 'mail': '.'.join(name.split(' ')) + '@' + get_email_domain()}
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
    