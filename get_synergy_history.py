#!/usr/bin/env python
# encoding: utf-8
"""
get_synergy_data.py

Starts the data extraction from Synergy

Created by Aske Olsson on 2011-05-09.
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
import os
import logging as logger

from SynergySession import SynergySession
from SynergySessions import SynergySessions
from CCMHistory import CCMHistory
from load_configuration import load_config_file

def start_sessions(config):
    ccm = SynergySession(config['database'], offline=config['offline'])
    ccm_pool = SynergySessions(database=config['database'], nr_sessions=config['max_sessions'], offline=config['offline'])

    return ccm, ccm_pool

def load_history(config):
    history = {}
    filename = config['data_file'] + '.p'
    if os.path.isfile(filename):
        logger.info("Loading %s" %filename)
        fh = open(filename, 'rb')
        history = pickle.load(fh)
        fh.close()
    else:
        cwd = os.getcwd()
        content = os.listdir(cwd)
        for f in content:
            if not os.path.isdir(f):
                if config['data_file'] in f:
                    if f.endswith('.p'):
                        logger.info("Loading file %s" % str(f))
                        # Try to pickle it
                        fh = open(f, 'rb')
                        hist = pickle.load(fh)
                        fh.close()
                        if 'name' in hist.keys():
                            history[hist['name']] = hist

    logger.info("history contains: %s" % str(sorted(history.keys())))

    return history


def main():

    config = load_config_file()
    # Set up logger
    log_file = config['log_file']
    if not log_file.endswith('.log'):
        log_file += '.log'
    logger.basicConfig(filename=log_file, level=logger.DEBUG)

    ccm, ccm_pool = start_sessions(config)
    history = load_history(config)

    ccm_hist = CCMHistory(ccm, ccm_pool, history, config['data_file'])
    history = ccm_hist.get_project_history(config['master'], config['base_project'])

    if config.has_key('heads'):
        for head in config['heads']:
            history = ccm_hist.get_project_history(head, config['base_project'])
        
    fh = open(config['data_file'] + '.p', 'wb')
    pickle.dump(history, fh, pickle.HIGHEST_PROTOCOL)
    fh.close()

    logger.shutdown()
if __name__ == '__main__':
    main()

