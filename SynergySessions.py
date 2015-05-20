#!/usr/bin/env python
# encoding: utf-8
"""
SynergySessions.py

Created by Knud Poulsen Aske Olsson on 2011-03-08.
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

import sys
import os
import re
import random
from datetime import datetime, timedelta
from subprocess import Popen, PIPE
from SynergySession import SynergySession
import time
from multiprocessing import Pool, Process, Queue

sys.stdout =  os.fdopen(sys.stdout.fileno(), 'w', 0);
sys.stderr =  os.fdopen(sys.stderr.fileno(), 'w', 0);

class SynergySessions(object):
    """This class is a wrapper around a pool of cm synergy sessions"""

    def __init__(self, database, engine=None, command_name='ccm', ccm_ui_path='/dev/null', ccm_eng_path='/dev/null', nr_sessions=2, offline=False):
        self.database = database
        self.command_name = command_name
        self.ccm_ui_path = ccm_ui_path
        self.ccm_eng_path = ccm_eng_path
        self.engine = engine
        self.nr_sessions = nr_sessions
        self.max_session_index = nr_sessions-1
        self.sessionArray = {}
        self.offline = offline
        """populate and array with synergy sessions"""
        create_sessions_pool(self.nr_sessions, self.database, self.engine, self.command_name, self.ccm_ui_path, self.ccm_eng_path, self.offline, self)

        for k, v in self.sessionArray.iteritems():
            print "session %d: %s" %(k, v.getCCM_ADDR())
            v.keep_session_alive = False

    def put_session(self, res):
        idx, ccm = res
        self.sessionArray[idx] = ccm


    def __getitem__(self, index):
        if ((index > self.max_session_index) or (index < 0)):
            raise IndexError()
        session = self.sessionArray[index];
        return session

    def __str__(self):
        retstring = ''
        for i in range (self.nr_sessions):
            retstring = retstring + "[" + str(i) + "] " + self.sessionArray[i].getCCM_ADDR() + "\n"
        return retstring

def create_sessions_pool(nr_sessions, database, engine, command_name, ccm_ui_path, ccm_eng_path, offline, session_cls):
    session_array = {}
    pool = Pool(nr_sessions)
    for i in range(nr_sessions):
        pool.apply_async(create_session, (database, engine, command_name, ccm_ui_path, ccm_eng_path, offline, i), callback=session_cls.put_session )
        if offline:
            print "Offline mode, just using cache"
        else:
            print "starting session [" + str(i) + "]"

    pool.close()

    pool.join()

def create_session(database, engine, command_name, ccm_ui_path, ccm_eng_path, offline, i):
    ccm = SynergySession(database, engine, command_name, ccm_ui_path, ccm_eng_path, offline)
    ccm.keep_session_alive = True
    ccm.sessionID = i
    return (i,ccm)


def do_query(task, ccm, queue):
    result = ccm.query("is_associated_cv_of(task('%s'))" % task).format("%objectname").run()
    queue.put(result)
    queue.close()

def main():
    pass
if __name__ == '__main__':
    main()
