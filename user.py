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
import pickle
import re
import logging as logger

from user_ldap import ldap_user
from user_finger import finger_user

class user(object):
    """ User object that containe user detailed info retreived from remote service
        srv : string "LDAP", "FINGER", "None"
    """
    def __init__(self, srv : str = None):
        self.str = srv
        self.lu = None
        pass

    def _get_user_by_uid_creator(self, srv : str):
        """ Will retreive the right method from implementation selected with srv
            srv : string "LDAP", "FINGER", ""
            if srv is "" Then default implementation is selected
        """
        if srv == "LDAP":
            self.lu = ldap_user()
            return ldap_user.get_user_by_uid
        elif srv == "FINGER":
            self.lu = finger_user()
            return finger_user.get_user_by_uid
        else:
             return self.get_user_by_uid_dft

    def get_user_by_uid(self, username):
        """ Call external method configured, but if it fails will fall back to default method """
        try:
            get_user_by_uid = self._get_user_by_uid_creator(self.srv)
            return get_user_by_uid(username)
        except Exception as e:
            return self.get_user_by_uid_dft(username)
            
    def get_user_by_uid_dft(self, username):
        """ Default method creating username from synergy username and configured domain """
            #create default
        user = {'name': username, 'mail': username + '@' + get_email_domain()}
        return user

def get_email_domain():
    f = open('config.p', 'rb')
    config = pickle.load(f)
    f.close()
    try:
        domain = config['email_domain']
    except KeyError:
        domain = 'none.com'
    return domain
