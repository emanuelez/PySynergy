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
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.    IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from SynergySession import SynergySession
from SynergySessions import SynergySessions
from SynergyObject import SynergyObject
from collections import deque
from multiprocessing import Pool, Manager, Process
import time

def get_objects_in_project(project, ccm=None, database=None, ccmpool=None):
    start = time.time()
    if ccmpool:
        if ccmpool.nr_sessions == 1:
            result = get_objects_in_project_serial(project, ccm=ccmpool[0], database=database)
        else:
            result = get_objects_in_project_parallel(project, ccmpool=ccmpool)
    else:
        result = get_objects_in_project_serial(project, ccm=ccm, database=database)
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
    so = SynergyObject(project, delim)
    queue = deque([so])

    hierarchy = {}
    dir_structure = {}
    proj_lookup = {}
    cwd = ''
    count = 1
    hierarchy[so.get_object_name()] = ''
    dir_structure[so.get_object_name()] = ''
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
                # Add the project to the hierarchy, so the subprojects for the release/project is known
                if o.get_object_name() in hierarchy.keys():
                    hierarchy[o.get_object_name()].append('%s%s' % (cwd, o.get_name()))
                else:
                    hierarchy[o.get_object_name()] = ['%s%s' % (cwd, o.get_name())]
            else:
                # Add the object to the hierarchy
                if obj.get_type() == 'dir':
                    if o.get_object_name() in hierarchy.keys():
                        hierarchy[o.get_object_name()].append('%s%s' % (cwd, o.get_name()))
                    else:
                        hierarchy[o.get_object_name()] = ['%s%s' % (cwd, o.get_name())]
                    #print "Object:", o.get_object_name(), 'has path:'
                    #print '%s%s' % (cwd, o.get_name())
        print "Object count: %6d" % count
    return hierarchy

def find_root_project(project, objects, ccm):
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


def do_query(next, free_ccm, semaphore, delim, p_queue):
    (project, parent_proj) = next
    #print 'Querying:', project.get_object_name()
    ccm_addr = get_and_lock_free_ccm_addr(free_ccm)
    ccm = SynergySession(None, ccm_addr=ccm_addr)
    ccm.keep_session_alive = True
    result = get_members(project, ccm, parent_proj)
    objects = [SynergyObject(o['objectname'], delim) for o in result]

    # if a project is being queried it might have more than one dir with the
    # same name as the project associated, find the directory that has the
    # project associated as the directory's parent
    if project.get_type() == 'project':
        if len(objects) > 1:
            objects = find_root_project(project, objects, ccm)

    p_queue.put((project, objects))
    free_ccm[ccm_addr] = True
    semaphore.release()

def do_results(next, hierarchy, dir_structure, proj_lookup):
    (obj, objects) = next

    q = []
    #print 'Processing:', obj.get_object_name()
    cwd = ''

    if obj.get_type() == 'dir' or obj.get_type() == 'project':
        # Processing a dir set 'working dir'
        cwd = dir_structure[obj.get_object_name()]
        #print 'setting cwd:', cwd

    for o in objects:
        #print o.get_object_name()
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
            # Add the project to the hierarchy, so the subprojects for the release/project is known
            if o.get_object_name() in hierarchy.keys():
                hierarchy[o.get_object_name()].append('%s%s' % (cwd, o.get_name()))
            else:
                hierarchy[o.get_object_name()] = ['%s%s' % (cwd, o.get_name())]
        else:
            # Add the object to the hierarchy
            if o.get_object_name() in hierarchy.keys():
                hierarchy[o.get_object_name()].append('%s%s' % (cwd, o.get_name()))
            else:
                hierarchy[o.get_object_name()] = ['%s%s' % (cwd, o.get_name())]
            #print "Object:", o.get_object_name(), 'has path:'
            #print '%s%s' % (cwd, o.get_name())

    return q, hierarchy, dir_structure, proj_lookup

def get_and_lock_free_ccm_addr(free_ccm):
    # get a free session
    for k in free_ccm.keys():
        if free_ccm[k]:
            free_ccm[k] = False
            return k

def get_objects_in_project_parallel(project, ccmpool=None):
    mgr = Manager()
    free_ccm = mgr.dict()

    for ccm in ccmpool.sessionArray.values():
        free_ccm[ccm.getCCM_ADDR()] = True
    ccm_addr = get_and_lock_free_ccm_addr(free_ccm)
    ccm = SynergySession(None, ccm_addr=ccm_addr)
    ccm.keep_session_alive = True
    delim = ccm.delim()
    # unlock
    free_ccm[ccm_addr] = True

    semaphore = mgr.Semaphore(ccmpool.nr_sessions)
    so = SynergyObject(project, delim)
    p_queue = mgr.Queue()
    c_queue = mgr.Queue()
    c_queue.put((so, None))
    p_queue.put(so)

    # start the produce and consumer thread
    prod = Process(target=producer, args=(c_queue, p_queue, free_ccm))
    cons = Process(target=consumer, args=(c_queue, p_queue, free_ccm, semaphore, delim))

    prod.start()
    cons.start()
    print "Waiting to join"
    cons.join()
    hierarchy = p_queue.get()
    prod.join()

    return hierarchy


def consumer(c_queue, p_queue, free_ccm, semaphore, delim):
    done = False
    pool = Pool(len(free_ccm.keys()))

    while not done:
        #get item from queue
        #print "Object count ------ ... P queue length %6d ... C queue length %6d" % (p_queue.qsize(), c_queue.qsize())
        next = c_queue.get()
        if next == "DONE":
            #done = True
            break

        semaphore.acquire()
        pool.apply_async(do_query, (next, free_ccm, semaphore, delim, p_queue))

    pool.close()
    pool.join()

def producer(c_queue, p_queue, free_ccm):
    project_hierarchy = {}
    dir_structure = {}
    proj_lookup = {}

    start_project = p_queue.get()
    dir_structure[start_project.get_object_name()] = ''
    project_hierarchy[start_project.get_object_name()] = ''
    done = False
    while not done or p_queue.qsize() > 0:
        # check if all ccm's are free for half a'sec if they are it's all done
        if not p_queue.qsize():
            done = True
            for i in range(10):
                if [v for v in free_ccm.values() if v == False]:
                    done = False
                    break
                else:
                    print "sleep..."
                    time.sleep(0.1)

        if done:
            break

        print "Object count %6d ... P queue length %6d ... C queue length %6d" % (len(project_hierarchy.keys()), p_queue.qsize(), c_queue.qsize())

        # Get results from ccm query and put new objects on the queue
        next = p_queue.get()
        (objects, hierarchy, dir_structure, proj_lookup) = do_results(next, project_hierarchy, dir_structure, proj_lookup)

        # put on queue
        for o in objects:
            parent_proj = None
            if o.get_type() == 'dir':
                parent_proj = proj_lookup[o.get_object_name()]
            c_queue.put((o, parent_proj))


    print "we're done..."
    if done:
        c_queue.put("DONE")
    p_queue.put(project_hierarchy)


def main():
    # Test
    db = '/nokia/co_nmp/groups/gscm/dbs/co1s30pr'
    #ccm = SynergySession(db)
    #result = get_objects_in_project("sb9-11w03_sb9_fam:project:be1s30pr#1", database=db)
    #result = get_objects_in_project("sb9-11w03_sb9_fam:project:be1s30pr#1", ccm=ccm)

    ccmpool = SynergySessions(database=db, nr_sessions=20)
    start = time.time()

#    res = get_objects_in_project_parallel("sb9-11w05_sb9_fam:project:be1s30pr#1", ccmpool=ccmpool)
    project = "sb9-11w05_sb9_fam:project:be1s30pr#1"
    res = get_objects_in_project(project, ccmpool=ccmpool)
    end = time.time()

    result = dict(res)
    count = 0
    for k, v in result.iteritems():
        if len(v) > 1:
            count += 1
            print '%s\n\t\t%s' % (k, '\n\t\t'.join(v))


    paths = sum([len(p) for p in result.values()])
    projects = [o for o in result.keys() if ':project:' in o]
    for p in sorted(projects):
        print p, result[p]
#    print '\n'.join(projects)

    print 'num of projects %d' %len(projects)
    print "Number of objects used in several places:", count
    print "objs:", str(len(result.keys()))
    print "paths:", paths
    print "Running time: %d seconds" % (end - start)

    import cPickle
    f = open("sb9-11w05_sb9_fam_2.p", 'wb')
    cPickle.dump(result, f, 2)
    f.close()

if __name__ == '__main__':
    main()



