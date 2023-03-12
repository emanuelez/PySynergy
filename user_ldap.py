#!/usr/bin/env python
# encoding: utf-8
"""
User_ldap.py

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
import ldap
import logging as logger
import user
import user_srv_factory as factory

class ldap_user(object):
    """LDAP connection for user oject"""

    def __init__(self):
        self.ldap = self.ldap_setup()

    def __del__(self):
        # Close the ldap session
        self.ldap.unbind_s()
        
    def get_typeName(self):
        return 'LDAP'
    
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
                    if 'displayName' in d:
                        result['name'] = d['displayName'][0]
                    elif 'cn' in d:
                        result['name'] = d['cn'][0]
                    elif 'gecos' in d:
                        result['name'] = d['gecos'][0]

                    if 'mail' in d:
                        result['mail'] = d['mail'][0]
                    else:
                        if 'displayName' in d:
                            result['mail'] = result['name'].split(' ')[1] + '.' + result['name'].split(' ')[0] + '@' + user.get_email_domain()

        except ldap.LDAPError as error_message:
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
        config = pickle.load(f)
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

factory.register_srv('LDAP', ldap_user)