#!/usr/bin/env python
# encoding: utf-8
"""
ccm_objects_in_project.py

Get object hierarchy for project as a dict:
    object_name : [path(s)]

Created by Aske Olsson 2011-03-11

Copyright (c) 2011, Nokia
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

Neither the name of the Nokia nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""

from SynergySession import SynergySession
from SynergySessions import SynergySessions
from SynergyObject import SynergyObject
from collections import deque
from multiprocessing import Process, Queue
import time

def get_objects_in_project(project, ccm=None, database=None, ccmpool=None):
    start = time.time()
    if ccmpool:
        result = get_objects_in_project_parallel(project, ccmpool=ccmpool)
    else:
        result = get_objects_in_project_parallel(project, ccm=ccm, database=database)
    print "Time used fetching all objects and paths in %s: %d s." %(project, time.time()-start)
    return result

def get_objects_in_project_serial(project, ccm=None, database=None):
    if not ccm:
        if not database:
            raise SynergyException('No ccm instance nor database given\nCannot start ccm session!\n')
        ccm = SynergySession(database)
    else:
        print "ccm instance:", ccm.environment['CCM_ADDR']

    delim = ccm.delim()
    queue = deque([SynergyObject(project, delim)])

    hierarchy = {}
    dir_structure = {}
    proj_lookup = {}
    cwd = ''
    count = 0

    while queue:
        obj = queue.popleft()
        #print 'Processing:', obj.get_object_name()
        parent_proj = None

        if obj.get_type() == 'dir':
            # Processing a dir set 'working dir'
            cwd = dir_structure[obj.get_object_name()]
            parent_proj = proj_lookup[obj.get_object_name()]

        result = get_members(obj, ccm, parent_proj)
        objects = [SynergyObject(o['objectname'], delim) for o in result]

        # if a project is being queried it might have more than one dir with the
        # same name as the project associated, find the directory that has the
        # project associated as the directory's parent
        if obj.get_type() == 'project':
            if len(objects) > 1:
                objects = find_root_project(obj, objects, ccm)

        for o in objects:
            count +=1
            if count % 100 == 0:
                print count, "objects done, currently in:", obj.get_object_name()
            if o.get_type() == 'dir':
                # add the directory to the queue and record its parent project
                queue.append(o)
                dir_structure[o.get_object_name()] = '%s%s/' % (cwd, o.get_name())
                if obj.get_type() == 'project':
                    proj_lookup[o.get_object_name()] = obj.get_object_name()
                elif obj.get_type() == 'dir':
                    proj_lookup[o.get_object_name()] = proj_lookup[obj.get_object_name()]
                    # Also add the directory to the Hierachy to get empty dirs
                    if o.get_object_name() in hierarchy.keys():
                        hierarchy[o.get_object_name()].append('%s%s' % (cwd, o.get_name()))
                    else:
                        hierarchy[o.get_object_name()] = ['%s%s' % (cwd, o.get_name())]
            elif o.get_type() == 'project':
                # Add the project to the queue
                queue.append(o)
            else:
                # Add the object to the hierarchy
                if obj.get_type() == 'dir':
                    if o.get_object_name() in hierarchy.keys():
                        hierarchy[o.get_object_name()].append('%s%s' % (cwd, o.get_name()))
                    else:
                        hierarchy[o.get_object_name()] = ['%s%s' % (cwd, o.get_name())]
                    #print "Object:", o.get_object_name(), 'has path:'
                    #print '%s%s' % (cwd, o.get_name())

    return hierarchy

def find_root_project(project, objects, ccm):
    delim = ccm.delim()
    for o in objects:
        result = ccm.query("has_child('{0}', '{1}')".format(o.get_object_name(), project.get_object_name())).format('%objectname').run()
        for r in result:
            if r['objectname'] == project.get_object_name():
                return [o]

def get_members(obj, ccm, parent_proj):
    if obj.get_type() == 'dir':
        objects = ccm.query("is_child_of('{0}', '{1}')".format(obj.get_object_name(), parent_proj)).format('%objectname').run()
    else:
        # For projects only get the directory of the project
        objects = ccm.query("is_member_of('{0}') and type='dir' and name='{1}'".format(obj.get_object_name(), obj.get_name())).format('%objectname').run()
    return objects


class SynergyException(Exception):
    """User defined exception raised by SynergySession"""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

def do_project(obj, proj_lookup, delim, ccm, queue):
    res = {}
    #print 'Querying:', obj.get_object_name()
    parent_proj = None

    if obj.get_type() == 'dir':
        parent_proj = proj_lookup[obj.get_object_name()]

    result = get_members(obj, ccm, parent_proj)
    objects = [SynergyObject(o['objectname'], delim) for o in result]

    # if a project is being queried it might have more than one dir with the
    # same name as the project associated, find the directory that has the
    # project associated as the directory's parent
    if obj.get_type() == 'project':
        if len(objects) > 1:
            objects = find_root_project(obj, objects, ccm)
    res[obj] = objects

    queue.put(res)
    queue.close()


def do_results(res, hierarchy, dir_structure, proj_lookup):
    #start = time.time()
    q = []
    obj = res.keys()[0]
    #print 'Processing:', obj.get_object_name()
    cwd = ''

    if obj.get_type() == 'dir' or obj.get_type() == 'project':
        # Processing a dir set 'working dir'
        cwd = dir_structure[obj.get_object_name()]
        #print 'setting cwd:', cwd

    objects = res.values()[0]

    for o in objects:
        if o.get_type() == 'dir':
            # add the directory to the queue and record its parent project
            q.append(o)
            #print "object:", obj.get_object_name(), 'child', o.get_object_name(), 'cwd', cwd
            dir_structure[o.get_object_name()] = '%s%s/' % (cwd, o.get_name())
            if obj.get_type() == 'project':
                proj_lookup[o.get_object_name()] = obj.get_object_name()
            elif obj.get_type() == 'dir':
                proj_lookup[o.get_object_name()] = proj_lookup[obj.get_object_name()]
                # Also add the directory to the Hierachy to get empty dirs
                if o.get_object_name() in hierarchy.keys():
                    hierarchy[o.get_object_name()].append('%s%s' % (cwd, o.get_name()))
                else:
                    hierarchy[o.get_object_name()] = ['%s%s' % (cwd, o.get_name())]
        elif o.get_type() == 'project':
            #print "object:", obj.get_object_name(), 'child', o.get_object_name(), 'cwd', cwd
            dir_structure[o.get_object_name()] = cwd
            # Add the project to the queue
            q.append(o)
        else:
            # Add the object to the hierarchy
            if o.get_object_name() in hierarchy.keys():
                hierarchy[o.get_object_name()].append('%s%s' % (cwd, o.get_name()))
            else:
                hierarchy[o.get_object_name()] = ['%s%s' % (cwd, o.get_name())]
            #print "Object:", o.get_object_name(), 'has path:'
            #print '%s%s' % (cwd, o.get_name())

    #print "time used %5d ms, no of objects: %4d for %s" % ((time.time()-start)*1000, len(objects), obj.get_object_name())
    return (q, hierarchy, dir_structure, proj_lookup)


def get_objects_in_project_parallel(project, ccmpool=None):

    ccm = ccmpool.sessionArray[0]
    delim = ccm.delim()
    so = SynergyObject(project, delim)
    queue = deque([so])

    hierarchy = dict()
    proj_lookup = dict()
    dir_structure = dict()

    dir_structure[so.get_object_name()] = ''
    done = False

    while queue:
        start = time.time()
        print "queue size:", len(queue)
        processes = []
        queues = []
        for i in range(ccmpool.nr_sessions):
            # Break if queue is empty
            if not queue:
                break
            # make processes
            proj = queue.popleft()
            ccm = ccmpool[i]
            queues.append(Queue())
            processes.append(Process(target=do_project, args=(proj, proj_lookup, delim, ccm, queues[i])))

        for p in processes:
            p.start()

        for i in range(len(processes)):
            res = queues[i].get()
            (q, hierarchy, dir_structure, proj_lookup) = do_results(res, hierarchy, dir_structure, proj_lookup)
            queue.extend(q)
            processes[i].join()

        print "No of objects so far: %d for project %s. Time used: %8d ms" % (len(hierarchy.keys()), project, (time.time()-start)*1000)

    return hierarchy



def main():
    # Test
    db = '/nokia/co_nmp/groups/gscm/dbs/co1s30pr'
    #ccm = SynergySession(db)
    #result = get_objects_in_project("sb9-11w03_sb9_fam:project:be1s30pr#1", database=db)
    #result = get_objects_in_project("sb9-11w03_sb9_fam:project:be1s30pr#1", ccm=ccm)

    ccmpool = SynergySessions(database=db, nr_sessions=10)
    start = time.time()

    res = get_objects_in_project_parallel("sb9-11w03_sb9_fam:project:be1s30pr#1", ccmpool=ccmpool)

    end = time.time()

    result = dict(res)
    count = 0
    for k, v in result.iteritems():
        if len(v) > 1:
            count += 1
            print '%s\n\t\t%s' % (k, '\n\t\t'.join(v))

    print "Number of objects used in several places:", count
    print "objs:", str(len(result.keys()))

    paths = sum([len(p) for p in result.values()])

    print "paths:", paths
    print "Running time:", end - start


if __name__ == '__main__':
    main()



