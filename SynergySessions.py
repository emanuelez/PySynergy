#!/usr/bin/env python
# encoding: utf-8
"""
SynergySessions.py

Copyright (c) 2011, Nokia
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the 
distribution.
Neither the name of the Nokia nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND 
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES 
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys
import os
import re
import random
from datetime import datetime, timedelta
from subprocess import Popen, PIPE
import SynergySession
from Queue import Queue

sys.stdout =  os.fdopen(sys.stdout.fileno(), 'w', 0);
sys.stderr =  os.fdopen(sys.stderr.fileno(), 'w', 0);

class SynergySessions(object):
    """This class is a wrapper around a pool of cm synergy sessions"""

    def __init__(self, database, engine=None, command_name='ccm', ccm_ui_path='/dev/null', ccm_eng_path='/dev/null', nr_sessions=2):
        self.database = database
        self.command_name = command_name
        self.ccm_ui_path = ccm_ui_path
        self.ccm_eng_path = ccm_eng_path
        self.engine = engine
        self.nr_sessions = nr_sessions
        self.max_session_index = nr_sessions-1
        
        """populate and array with synergy sessions"""
        self.sessionArray = {}
        self.threadarrau = {}
        for i in range (self.nr_sessions):
            print "starting session [" + str(i) + "]"
            self.sessionArray[i] = SynergySession.SynergySession(self.database, self.engine, self.command_name, self.ccm_ui_path, self.ccm_eng_path)
            self.sessionArray[i].setSessionID(i)
            


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

 


def main():
    """Test: start a bunch of sessions in parallel, start commands on each, wait for them all to return and print the result in execution order"""
    ccmpool = SynergySessions(database='/nokia/co_nmp/groups/gscm/dbs/co1asset', nr_sessions=2)

    print "ccmpool:"
    print ccmpool

    nr_ops_in_test = 11

    print "asking for info on " + str(nr_ops_in_test) + " random tasks in parallel"
    tstart = datetime.now()

    nr_full_parallel_run_groups = nr_ops_in_test/ccmpool.nr_sessions
    partial_parallel_run_nr = nr_ops_in_test-(nr_full_parallel_run_groups*ccmpool.nr_sessions)
    ops_count = 0

    for i in range(nr_full_parallel_run_groups):
        for j in range(ccmpool.nr_sessions):
            ops_count+=1
            querytask = random.randint(1000, 100000)
            print "[" + str(j) + "] ops_count=" + str(ops_count) + ", task=" + str(querytask)
            ccmpool[j].query("is_associated_cv_of(task('co1asset#%i'))" % querytask).format("%objectname").start()
        for j in range(ccmpool.nr_sessions):
            print "DEBUG: .join() waiting for [" + str(j) + "]" 
            results = ccmpool[j].join()
            print results

    for j in range(partial_parallel_run_nr):
        ops_count+=1
        querytask = random.randint(1000, 100000)
        print "[" + str(j) + "] ops_count=" + str(ops_count) + ", task=" + str(querytask)
        ccmpool[j].query("is_associated_cv_of(task('co1asset#%i'))" % querytask).format("%objectname").start()
    for j in range(partial_parallel_run_nr):
        print "DEBUG: .join() waiting for [" + str(j) + "]"
        results = ccmpool[j].join()
        print results
    
    tparallel = datetime.now()-tstart
    print str(nr_ops_in_test) + " operations, in parallel, on " + str(ccmpool.nr_sessions) + " ccm sessions, it took: " + str(tparallel.seconds) + " seconds"
    
if __name__ == '__main__':
    main()


