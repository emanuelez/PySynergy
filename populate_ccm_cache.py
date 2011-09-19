#!/usr/bin/env python
# encoding: utf-8
"""
populate_ccm_cache.py

Created by Aske Olsson on 2011-05-13.
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
from CCMHistory import get_project_chain
from SynergySession import SynergySession
from SynergySessions import SynergySessions
import ccm_cache
import ccm_objects_in_project
from load_configuration import load_config_file


def update_project_with_members(project, ccm, ccmpool):
    project_obj = ccm_cache.get_object(project)
    objects_in_project = ccm_objects_in_project.get_objects_in_project(project, ccm=ccm, ccmpool=ccmpool)
    project_obj.set_members(objects_in_project)
    ccm_cache.force_cache_update_for_object(project_obj)


def populate_cache_with_projects(config):
    heads = config['heads']
    heads.append(config['master'])
    base_project = config['base_project']
    ccm, ccmpool = start_sessions(config)

    projects = []
    for head in heads:
        projects.extend(get_project_chain(head, base_project, ccm))

    # Got all the project chains - now get the members for each
    for project in set(projects):
        update_project_with_members(project, ccm, ccmpool)


def get_project_chain_from_ccm(from_project, to_project, ccm):
    # Do it reverse:
    successor = ccm_cache.get_object(to_project, ccm)
    chain = [successor.get_object_name()]
    while successor.get_object_name() != from_project:
        successor = ccm_cache.get_object(successor.baseline_predecessor, ccm)
        if successor:
            chain.append(successor.get_object_name())
        else:
            break
    chain.reverse()
    return chain


def populate_cache_with_objects_from_project(project, ccm, ccmpool):
    objects_in_project = {}
    print "processing project %s" %project
    #first try to get the object from cache
    project_obj = ccm_cache.get_object(project, ccm)
    if not project_obj.members:
        update_project_with_members(project)

    if objects_in_project:
        num_o = len( objects_in_project.keys())
        for o in objects_in_project.keys():
            print "loading object: %s" % o
            obj = ccm_cache.get_object(o, ccm)
            num_o -=1
            print "objects left %d" %num_o

    print "%s done, members: %d" %(project, len(project_obj.members.keys()))
    populate_cache_with_objects_from_project(project_obj.baseline_predecessor, ccm, ccmpool)

def start_sessions(config):
    ccm = SynergySession(config['database'])
    ccm_pool = SynergySessions(database=config['database'], nr_sessions=config['max_sessions'])
    return ccm, ccm_pool

def main():

    config = load_config_file()
    populate_cache_with_projects(config)

if __name__ == '__main__':
    main()
