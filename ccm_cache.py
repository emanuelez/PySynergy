#!/usr/bin/env python
# encoding: utf-8
"""
ccm_cache.py

Created by Aske Olsson on 2011-05-04.
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
from datetime import datetime
import sys
from DirectoryObject import DirectoryObject

from SynergyObject import SynergyObject
from ProjectObject import ProjectObject
from FileObject import FileObject
from SynergySession import SynergySession
from TaskObject import TaskObject

import string
import cPickle
import hashlib
import os
import os.path

def get_object(obj, ccm=None):
    """Get the object's meta data from either the cache or directly from ccm"""
    if obj is None:
        return None
    ccm_cache_path = load_ccm_cache_path()
    #try the object cache first
    try:
        object_data = get_object_data_from_cache(obj, ccm_cache_path)
    except ObjectCacheException:
        if not ccm:
            ccm = create_ccm_session_from_config()
        try:
            object_data = get_object_from_ccm(obj, ccm, ccm_cache_path)
        except ObjectCacheException:
            raise ObjectCacheException("Couldn't extract %s from Synergy" % obj)
    return object_data

def get_source(obj, ccm=None):
    """Get the object source from either the cache or directly from ccm"""
    if obj is None:
        return None
    ccm_cache_path = load_ccm_cache_path()
    #try the object cache first
    try:
        object = get_object_source_from_cache(obj, ccm_cache_path)
    except ObjectCacheException:
        if not ccm:
            ccm = create_ccm_session_from_config()
        try:
            get_object_from_ccm(obj, ccm, ccm_cache_path)
        except ObjectCacheException:
            raise ObjectCacheException("Couldn't extract %s from Synergy" % obj)
        object = get_object_source_from_cache(obj, ccm_cache_path)

    return object

def reload_object(obj, ccm=None):
    ccm_cache_path = load_ccm_cache_path()
    # delete it:
    delete_object(obj)
    # load it
    if not ccm:
        ccm = create_ccm_session_from_config()
    object = get_object_from_ccm(obj, ccm, ccm_cache_path)
    return object

def delete_object(obj):
    """Get the object's meta data from either the cache or directly from ccm"""
    if obj is None:
        return None
    ccm_cache_path = load_ccm_cache_path()
    dir, filename = get_path_for_object(obj, ccm_cache_path)
    datafile = filename + '_data'
    if os.path.exists(datafile):
        #delete it
        os.remove(datafile)
    if os.path.exists(filename):
        os.remove(filename)

def get_path_for_object(obj, ccm_cache_path):
    m = hashlib.sha1()
    m.update(obj)
    sha = m.hexdigest()
    dir = ccm_cache_path + sha[0:2]
    filename = dir + '/' + sha[2:-1]
    return dir, filename

def get_object_data_from_cache(obj, ccm_cache_path):
    """Try to get the object's meta data from the cache"""
    #sha1 the object name:
    dir, filename = get_path_for_object(obj, ccm_cache_path)
    datafile = filename + '_data'
    # check if object exists
    if os.path.exists(datafile):
        # load the data file
#        print 'Loading object %s from cache' %obj
        f = open(datafile, 'rb')
        object_data = cPickle.load(f)
        f.close()
        return object_data
    else:
        raise ObjectCacheException("Object %s not in cache" %obj)

def get_object_source_from_cache(obj, ccm_cache_path):
    """Try to get the object from the cache"""
    dir, filename = get_path_for_object(obj, ccm_cache_path)
    # check if object exists
    if os.path.exists(filename):
        # load the file
        f = open(filename, 'rb')
        content = f.read()
        f.close()
        return content
    else:
        raise ObjectCacheException("Object %s not in cache" %obj)


def force_cache_update_for_object(object, ccm=None, ccm_cache_path=None):
    if ccm_cache_path is None:
        ccm_cache_path = load_ccm_cache_path()
    dir, filename = get_path_for_object(object.get_object_name(), ccm_cache_path)
    datafile = filename + '_data'
    # check if object exists
    if os.path.exists(datafile):
        #delete it
        os.remove(datafile)
    if not os.path.exists(dir):
        try:
           os.makedirs(dir)
        except OSError:
            # just continue if it is already there
            pass
    f = open(datafile, 'wb')
    cPickle.dump(object, f)
    f.close()

    type = object.get_type()
    if type != 'project' and type != 'task' and type != 'dir':
        # Store the content of the object
        if not os.path.exists(filename):
            if ccm is None:
                ccm = create_ccm_session_from_config()
            content = ccm.cat(object.get_object_name()).run()
            f = open(filename, 'wb')
            f.write(content)
            f.close()


def update_cache(object, ccm, ccm_cache_path):
    dir, filename = get_path_for_object(object.get_object_name(), ccm_cache_path)
    datafile = filename + '_data'
    # check if object exists
    if os.path.exists(datafile):
        raise ObjectCacheException("Object %s is already in cache" %object)
    else:
        if not os.path.exists(dir):
            try:
               os.makedirs(dir)
            except OSError:
                # just continue if it is already there
                pass
        f = open(datafile, 'wb')
        cPickle.dump(object, f)
        f.close()

    type = object.get_type()
    if type != 'project' and type != 'task' and type != 'dir':
        # Store the content of the object
        content = ccm.cat(object.get_object_name()).run()
        f = open(filename, 'wb')
        f.write(content)
        f.close()

def create_project_object(synergy_object, ccm):
    object = ProjectObject(synergy_object.get_object_name(), synergy_object.get_separator(), synergy_object.get_author(), synergy_object.get_status(), synergy_object.get_created_time(), synergy_object.get_tasks())
    # baseline info
    res = ccm.query("is_baseline_project_of('{0}')".format(synergy_object.get_object_name())).format("%objectname").run()
    if res:
        baseline_predecessor = res[0]['objectname']
    else:
        baseline_predecessor = None
    object.baseline_predecessor = baseline_predecessor

    res = ccm.query("has_baseline_project('{0}') and status='released'".format(synergy_object.get_object_name())).format("%objectname").run()
    if res:
        baseline_successor = [baseline['objectname'] for baseline in res]
    else:
        baseline_successor = []
    object.baseline_successor = baseline_successor

    # Get task in reconfigure prop
    tasks = []
    res = ccm.rp(synergy_object.get_object_name()).option('-show').option('all_tasks').run()
    for t in res:
        tasks.append(t['objectname'].strip())
    object.tasks_in_rp = tasks

    # get baselines
    baselines = []
    res = ccm.query("has_project_in_baseline('{0}')".format(synergy_object.get_object_name())).format('%objectname').run()
    for b in res:
        baselines.append(b['objectname'])
    object.baselines = baselines

    return object

def create_task_object(synergy_object, ccm):
    object = TaskObject(synergy_object.get_object_name(), synergy_object.get_separator(), synergy_object.get_author(), synergy_object.get_status(), synergy_object.get_created_time(), synergy_object.get_tasks())
    # Get the projects this task is used in
    projects = []
    result = ccm.finduse(synergy_object.get_object_name()).option('-task').option('-released_proj').run().splitlines()
    for p in result[1:]: # aviod [0], the task synopsis
        projects.append(p.strip())
    object.released_projects = projects

    # get baselines which the task is used in
    baselines = []
    res = ccm.query("has_task_in_baseline('{0}')".format(synergy_object.get_object_name())).format('%objectname').run()
    for b in res:
        baselines.append(b['objectname'])
    object.baselines = baselines

    return object


def create_file_or_dir_object(synergy_object, ccm):
    if synergy_object.get_type() == 'dir':
        object = DirectoryObject(synergy_object.get_object_name(), synergy_object.get_separator(), synergy_object.get_author(), synergy_object.get_status(), synergy_object.get_created_time(), synergy_object.get_tasks())
    else:
        object = FileObject(synergy_object.get_object_name(), synergy_object.get_separator(), synergy_object.get_author(), synergy_object.get_status(), synergy_object.get_created_time(), synergy_object.get_tasks())
    # releases
    releases = []
    res = ccm.query("has_member('{0}') and status='released'".format(synergy_object.get_object_name())).format('%objectname').run()
    for r in res:
        releases.append(r['objectname'])
    object.releases = releases

    return object

def fill_changed_entries(object, ccm):
    deleted = []
    new = []
    for p in object.get_predecessors():
        diff = ccm.diff(object.get_object_name(), p).run().splitlines()
        for line in diff:
            if line.startswith('<'):
                deleted.append(line.split()[1])
            if line.startswith('>'):
                new.append(line.split()[1])
    object.set_new_objects(set(new))
    object.set_deleted_objects(set(deleted))
    return object

def get_object_from_ccm(four_part_name, ccm, ccm_cache_path):
    """Try to get the object's meta data from Synergy"""
#    print 'Loading object %s from ccm' %four_part_name
    # convert the four-part-name to a synergy object:
    delim = ccm.delim()
    synergy_object = SynergyObject(four_part_name, delim)
    res = ccm.query("name='{0}' and version='{1}' and type='{2}' and instance='{3}'".format(synergy_object.get_name(), synergy_object.get_version(), synergy_object.get_type(), synergy_object.get_instance())).format("%objectname").format("%owner").format("%status").format("%create_time").format("%task").run()
    if res:
        synergy_object.status = res[0]['status']
        synergy_object.author =  res[0]['owner']
        synergy_object.created_time = datetime.strptime(res[0]['create_time'], "%a %b %d %H:%M:%S %Y")
        tasks = []
        for t in res[0]['task'].split(','):
            if t != '<void>':
                if ':task:' not in t:
                    tasks.append(task_to_four_part(t, delim))
                else:
                    tasks.append(t)
        synergy_object.tasks = tasks
    else:
        raise ObjectCacheException("Couldn't extract %s from Synergy" % four_part_name)

    if synergy_object.get_type() == 'project':
        object = create_project_object(synergy_object, ccm)
    elif synergy_object.get_type() == 'task':
        object = create_task_object(synergy_object, ccm)
    else:
        object = create_file_or_dir_object(synergy_object, ccm)

    # Common among all objects
    # fill meta data for object:
    predecessors = []
    res = ccm.query("is_predecessor_of('{0}')".format(object.get_object_name())).format("%objectname").run()
    for p in res:
        predecessors.append(p['objectname'])
    object.predecessors = predecessors

    successors = []
    res = ccm.query("is_successor_of('{0}')".format(object.get_object_name())).format("%objectname").run()
    for s in res:
        successors.append(s['objectname'])
    object.successors = successors

    attributes = get_non_blacklisted_attributes(object, ccm)
    object.set_attributes(attributes)

    if object.get_type() == 'dir':
        object = fill_changed_entries(object, ccm)

    # write the file to the cache and return it
    update_cache(object, ccm, ccm_cache_path)

    return object

def task_to_four_part(task, delim):
    split = task.split('#')
    four_part = ['task', split[1], delim, '1:task:', split[0]]
    return ''.join(four_part)

def get_non_blacklisted_attributes(obj, ccm):
    attribute_blacklist = ['_archive_info', '_modify_time', 'binary_scan_file_time',
        'cluster_id', 'comment',  'create_time', 'created_in', 'cvtype', 'dcm_receive_time',
        'handle_source_as', 'is_asm', 'is_model', 'local_to', 'modify_time', 'name',
        'owner', 'project', 'release', 'source_create_time', 'source_modify_time',
        'status', 'subsystem', 'version', 'wa_type', '_relations', 'est_duration',
        'groups' , 'platform', 'priority', 'task_subsys', 'assigner', 'assignment_date',
        'completed_id', 'completed_in', 'completion_date', 'creator', 'modifiable_in',
        'registration_date', 'source']

    attr_list = ccm.attr(obj.get_object_name()).option('-l').run().splitlines()
    attributes = {}
    for attr in attr_list:
        attr = attr.partition(' ')[0]
        if attr not in attribute_blacklist:
            attributes[attr] = ccm.attr(obj.get_object_name()).option('-s').option(attr).run()
    return attributes

def get_all_attributes(obj, ccm):
    attr_list = ccm.attr(obj.get_object_name()).option('-l').run().splitlines()
    attributes = {}
    for attr in attr_list:
        attr = attr.partition(' ')[0]
        attributes[attr] = strip_non_ascii(ccm.attr(obj.get_object_name()).option('-s').option(attr).run())
    return attributes

def strip_non_ascii(str):
    return ''.join([c for c in str if c in string.printable])


def load_ccm_cache_path():
    f = open('config.p', 'rb')
    config = cPickle.load(f)
    f.close()

    return config['ccm_cache_path']

def create_ccm_session_from_config():
    f = open('config.p', 'rb')
    config = cPickle.load(f)
    f.close()

    ccm = SynergySession(config['database'])
    return ccm



class ObjectCacheException(Exception):
    """User defined exception raised by SynergySession"""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def main():
    """Test"""
    object = sys.argv[1]

    #create a fake config file:
    config = {'ccm_cache_path': '/nokia/co_nmp/groups/git_wip/users/asolsson/ccm_cache/',
              'database': '/nokia/co_nmp/groups/gscm/dbs/co1s30pr'}

    f = open('config.p', 'wb')
    cPickle.dump(config, f)
    f.close()

    obj = get_object(object)

    if os.path.isfile('config.p'):
        os.remove('config.p')

if __name__ == '__main__':
    main()
