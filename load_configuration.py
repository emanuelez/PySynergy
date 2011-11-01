#!/usr/bin/env python
# encoding: utf-8
"""
load_configuration.py

Loads configuration from config file

Created by Aske Olsson on 2011-09-19.
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
from ConfigParser import ConfigParser
import cPickle


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
        if k == 'heads':
            v = v.split(',')
            v = [i.strip() for i in v]
        if k == 'skip_binary_files':
            v = config_parser.getboolean('synergy', 'skip_binary_files')
        config[k]=v
    for k, v in config_parser.items('history conversion'):
        if k == 'print_graphs':
            v = config_parser.getboolean('history conversion', 'print_graphs')
        config[k]=v
    if config_parser.has_section('ldap'):
        for k,v in config_parser.items('ldap'):
            config[k]=v
    if config_parser.has_section('finger'):
        config['finger'] = {}
        for k,v in config_parser.items('finger'):
            config['finger'][k] = v

    if config.has_key('heads'):
        if config['master'] in config['heads']:
            config['heads'].remove(config['master'])

    save_config(config)

    return config
