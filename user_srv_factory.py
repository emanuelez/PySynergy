#!/usr/bin/env python
# encoding: utf-8
"""
user_srv_factory.py

Created by Selso LIBERADO on 2023-03-08.
Copyright (c) 2023, Guerbet
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

import user

class dft_user_srv():
    def __init__(self):
        pass      
    def get_user_by_uid(self, username):
        """ Default method creating username from synergy username and configured domain """
        user = {'name': username, 'mail': username + '@' + user.get_email_domain()}
        return user
    
class user_srv_factory():
    """ Serializer factory to provide dynamic abstraction above product method,
        and runtime dependency addition.
    """
    def __init__(self):
        self._creators = {}
    def register_srv(self, srv: str, creator):
        self._creators[srv] = creator
    def get_user_srv(self, srv : str):
        creator = self._creators.get(srv)
        if not creator:
            raise ValueError(srv)
        return creator()
    
factory = user_srv_factory()
# register default only
factory.register_srv('DFT', dft_user_srv)
# Let other services register themselves if appropriate
#factory.register_srv('LDAP', ldap_user)
#factory.register_srv('FINGER', finger_user)