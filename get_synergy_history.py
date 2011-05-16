#!/usr/bin/env python
# encoding: utf-8
"""
get_synergy_data.py

Loads configuration from config file and starts the data extraction from Synergy

Created by Aske Olsson on 2011-05-09.
Copyright (c) 2011, Nokia
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the
distribution.
Neither the name of the Nokia nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.    IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
from ConfigParser import ConfigParser
import cPickle
import os
from CCMHistory import CCMHistory
from SynergySession import SynergySession
from SynergySessions import SynergySessions
from CCMHistory import CCMHistory


def save_config(config):
    f = open('config.p', 'wb')
    cPickle.dump(config, f)
    f.close()

def load_config_file():

    config_parser = ConfigParser()
    config_parser.read('configuration.conf')
    config = {}
    for k, v in config_parser.items('synergy'):
        if k == 'ccm_cache_path' and not v.endswith('/'):
            v += '/'
        if k == 'max_sessions':
            v = int(v)
        if k == 'max_recursion_depth':
            v = int(v)
        config[k]=v
    for k, v in config_parser.items('history conversion'):
        config[k]=v
    save_config(config)

    return config


def start_sessions(config):
    ccm = SynergySession(config['database'])
    ccm_pool = SynergySessions(database=config['database'], nr_sessions=config['max_sessions'])

    return ccm, ccm_pool

def load_history(config):
    history = {}
    filename = config['data_file'] + '.p'
    if os.path.isfile(filename):
        print "Loading", filename, "..."
        fh = open(filename, 'rb')
        history = cPickle.load(fh)
        fh.close()
    else:
        cwd = os.getcwd()
        content = os.listdir(cwd)
        for f in content:
            if not os.path.isdir(f):
                if config['data_file'] in f:
                    if f.endswith('.p'):
                        print "Loading file", f
                        # Try to pickle it
                        fh = open(f, 'rb')
                        hist = cPickle.load(fh)
                        fh.close()
                        if 'name' in hist.keys():
                            history[hist['name']] = hist

    print "history contains:", sorted(history.keys())

    return history


def main():

    config = load_config_file()
    ccm, ccm_pool = start_sessions(config)
    history = load_history(config)

    ccm_hist = CCMHistory(ccm, ccm_pool, history, config['data_file'])
    history = ccm_hist.get_project_history(config['end_project'], config['base_project'])

    fh = open(config['data_file'] + '.p', 'wb')
    cPickle.dump(history, fh, cPickle.HIGHEST_PROTOCOL)
    fh.close()

if __name__ == '__main__':
    main()

    