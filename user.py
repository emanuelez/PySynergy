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

from  user_srv_factory import factory

class user(object):
    """ User object that contains user detailed info retreived from remote service
    """
    def __init__(self, srv: str = 'DFT'):
        """ Init with Sevice selection
        """
        # to reproduce 'past behavior" we'll call default getter whenever the selected service fails.
        self.user_srv_dft = factory.get_user_srv('DFT')
        if srv != 'DFT':
            self.user_srv = factory.get_user_srv(srv)

    def get_user_by_uid(self, username):
        """ Call external method configured, but if it fails will fall back to default method """
        result = {}
        try:
            result =  self.user_srv.get_user_by_uid(username)
        except Exception as e:
             if self.user_srv != self.user_srv_dft:
                result = self.user_srv.user_srv_dft(username)
        return result
        

def get_email_domain():
    f = open('config.p', 'rb')
    config = pickle.load(f)
    f.close()
    try:
        domain = config['email_domain']
    except KeyError:
        domain = 'none.com'
    return domain
