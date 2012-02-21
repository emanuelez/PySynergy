#!/usr/bin/env python
# encoding: utf-8
"""
ccm_objects_in_project.py

Get object hierarchy for project as a dict:
    object_name : [path(s)]

Created by Aske Olsson 2011-03-11
Copyright (c) 2011, Nokia
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

Neither the name of the Nokia nor the names of its contributors may be used
to endorse or promote products derived from this software without specific
prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED.    IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import Queue
from SynergySession import SynergySession, SynergyException
from SynergyObject import SynergyObject
from collections import deque
import logging
from multiprocessing import Pool, Manager, Process
import time
import ccm_cache

logger = logging.getLogger("objects in project")

def get_objects_in_project(project, ccm=None, database=None, ccmpool=None, use_cache=False):
    """ Get all objects and paths in project
        If use_cache is enabled all objects will stored in cache area
    """
    start = time.time()
    if ccmpool:
        if ccmpool.nr_sessions == 1:
            result = get_objects_in_project_serial(project, ccm=ccmpool[0], database=database, use_cache=use_cache)
        else:
            result = get_objects_in_project_parallel(project, ccmpool=ccmpool, use_cache=use_cache)
    else:
        result = get_objects_in_project_serial(project, ccm=ccm, database=database, use_cache=use_cache)
    logger.debug("Time used fetching all objects and paths in %s: %d s.",
                project, time.time() - start)
    if use_cache:
        ccm_object = ccm_cache.get_object(project)
        ccm_object.set_members(result)
        ccm_cache.force_cache_update_for_object(ccm_object)
    return result


def get_objects_in_project_serial(project, ccm=None, database=None, use_cache=False):
    """ Get all objects and paths of a project """
    if not ccm:
        if not database:
            raise SynergyException("No ccm instance nor database given\n" +
                                   "Cannot start ccm session!\n")
        ccm = SynergySession(database)
    else:
        logger.debug("ccm instance: %s" % ccm.environment['CCM_ADDR'])

    delim = ccm.delim()
    if use_cache:
        start_object = ccm_cache.get_object(project, ccm)
    else:
        start_object = SynergyObject(project, delim)
    queue = deque([start_object])

    hierarchy = {}
    dir_structure = {}
    proj_lookup = {}
    cwd = ''
    count = 1
    hierarchy[start_object.get_object_name()] = [start_object.name]
    dir_structure[start_object.get_object_name()] = ''
    while queue:
        obj = queue.popleft()
        #logger.debug('Processing: %s' % obj.get_object_name())
        parent_proj = None

        if obj.get_type() == 'dir' or obj.get_type() == 'project':
            # Processing a dir set 'working dir'
            cwd = dir_structure[obj.get_object_name()]
            if obj.get_type() == 'dir':
                parent_proj = proj_lookup[obj.get_object_name()]

        result = get_members(obj, ccm, parent_proj)
        if use_cache:
            objects = []
            na_obj = []
            for item in result:
                try:
                    objects.append(ccm_cache.get_object(item['objectname'], ccm))
                except ccm_cache.ObjectCacheException:
                    objects.append(SynergyObject(item['objectname'], ccm.delim()))
                    na_obj.append(item['objectname'])
            if na_obj:
                logger.warning("Objects not avaliable in this db:")
                logger.warning(', '.join(na_obj))
        else:
            objects = [SynergyObject(item['objectname'], delim) for item in result]

        # if a project is being queried it might have more than one dir with the
        # same name as the project associated, find the directory that has the
        # project associated as the directory's parent
        if obj.get_type() == 'project':
            if len(objects) > 1:
                objects = find_root_project(obj, objects, ccm)

        for synergy_object in objects:
            count += 1
            if synergy_object.get_type() == 'dir':
                # add the directory to the queue and record its parent project
                queue.append(synergy_object)
                #logger.debug("object: %s child %s cwd %s" % (obj
                # .get_object_name(), o.get_object_name(), cwd))
                dir_structure[synergy_object.get_object_name()] = \
                '%s%s/' % (cwd, synergy_object.get_name())
                if obj.get_type() == 'project':
                    proj_lookup[synergy_object.get_object_name()] = \
                    obj.get_object_name()
                elif obj.get_type() == 'dir':
                    proj_lookup[synergy_object.get_object_name()] = \
                    proj_lookup[obj.get_object_name()]
                    # Also add the directory to the Hierachy to get empty dirs
                if synergy_object.get_object_name() in hierarchy.keys():
                    hierarchy[synergy_object.get_object_name()].append(
                        '%s%s' % (cwd, synergy_object.get_name()))
                else:
                    hierarchy[synergy_object.get_object_name()] = \
                    ['%s%s' % (cwd, synergy_object.get_name())]
            elif synergy_object.get_type() == 'project':
                dir_structure[synergy_object.get_object_name()] = cwd
                # Add the project to the queue
                queue.append(synergy_object)
                #logger.debug("object: %s child %s cwd %s" % (obj
                # .get_object_name(), o.get_object_name(), cwd))
                # Add the project to the hierarchy,
                # so the subprojects for the release/project is known
                if synergy_object.get_object_name() in hierarchy.keys():
                    hierarchy[synergy_object.get_object_name()].append(
                        '%s%s' % (cwd, synergy_object.get_name()))
                else:
                    hierarchy[synergy_object.get_object_name()] = \
                    ['%s%s' % (cwd, synergy_object.get_name())]
            else:
                # Add the object to the hierarchy
                if obj.get_type() == 'dir':
                    if synergy_object.get_object_name() in hierarchy.keys():
                        hierarchy[synergy_object.get_object_name()].append(
                            '%s%s' % (cwd, synergy_object.get_name()))
                    else:
                        hierarchy[synergy_object.get_object_name()] = \
                        ['%s%s' % (cwd, synergy_object.get_name())]
                        #logger.debug("Object: %s has path %s%s" % (o.get_object_name(), cwd, o.get_name()))
        logger.debug("Object count: %6d" % count)
    return hierarchy


def find_root_project(project, objects, ccm):
    """ If a project is being queried it might have more than one dir with the
        same name as the project associated, find the directory that has the
        project associated as the directory's parent """
    for synergy_object in objects:
        result = ccm.query("has_child('{0}', '{1}')".format(
            synergy_object.get_object_name(), project.get_object_name())).format('%objectname').run()
        for item in result:
            if item['objectname'] == project.get_object_name():
                return [synergy_object]


def get_members(obj, ccm, parent_proj):
    """ Get directory members of a project
    Get all members of a directory object """
    if obj.get_type() == 'dir':
        objects = ccm.query("is_child_of('{0}', '{1}')".format(
            obj.get_object_name(), parent_proj)).format('%objectname').run()
    else:
        # For projects only get the directory of the project
        objects = ccm.query(
            "is_member_of('{0}') and type='dir' and name='{1}'".format(
                obj.get_object_name(), obj.get_name())).format(
                    '%objectname').run()
    return objects


def do_query(next_in_queue, free_ccm, semaphore, delim, p_queue, use_cache):
    (project, parent_proj) = next_in_queue
    ccm_addr, database = get_and_lock_free_ccm_addr(free_ccm)
    ccm = SynergySession(database, ccm_addr=ccm_addr)
    ccm.keep_session_alive = True
#    logger.debug('Querying: %s' % project.get_object_name())

    result = get_members(project, ccm, parent_proj)
    if use_cache:
        objects = []
        na_obj = []
        for item in result:
            try:
                objects.append(ccm_cache.get_object(item['objectname'], ccm))
            except ccm_cache.ObjectCacheException:
                objects.append(SynergyObject(item['objectname'], delim))
                na_obj.append(item['objectname'])
        if na_obj:
            logger.warning("Objects not avaliable in this db:")
            logger.warning(', '.join(na_obj))
    else:
        objects = [SynergyObject(item['objectname'], delim)
                   for item in result]

    # if a project is being queried it might have more than one dir with the
    # same name as the project associated, find the directory that has the
    # project associated as the directory's parent
    if project.get_type() == 'project':
        if len(objects) > 1:
            objects = find_root_project(project, objects, ccm)

    p_queue.put((project, objects))
    entry = free_ccm[ccm_addr]
    entry['free'] = True
    free_ccm[ccm_addr] = entry
    semaphore.release()


def do_results(from_queue, hierarchy, dir_structure, proj_lookup):
    """ Process the query results from Synergy """
    (obj, objects) = from_queue

    next_on_queue = []
    cwd = ''

    if obj.get_type() == 'dir' or obj.get_type() == 'project':
        # Processing a dir set 'working dir'
        cwd = dir_structure[obj.get_object_name()]
        #logger.debug('setting cwd: %s' %cwd)

    for synergy_object in objects:
        #logger.debug("%s" %o.get_object_name())
        if synergy_object.get_type() == 'dir':
            # add the directory to the queue and record its parent project
            next_on_queue.append(synergy_object)
            #logger.debug("object: %s child %s cwd %s" % (obj.get_object_name
            # (), o.get_object_name(), cwd))
            dir_structure[synergy_object.get_object_name()] = \
            '%s%s/' % (cwd, synergy_object.get_name())
            if obj.get_type() == 'project':
                proj_lookup[synergy_object.get_object_name()] = \
                obj.get_object_name()
            elif obj.get_type() == 'dir':
                proj_lookup[synergy_object.get_object_name()] = \
                proj_lookup[obj.get_object_name()]

            # Also add the directory to the Hierarchy to get empty dirs
            if synergy_object.get_object_name() in hierarchy.keys():
                hierarchy[synergy_object.get_object_name()].append(
                    '%s%s' % (cwd, synergy_object.get_name()))
            else:
                hierarchy[synergy_object.get_object_name()] = \
                ['%s%s' % (cwd, synergy_object.get_name())]
        elif synergy_object.get_type() == 'project':
            dir_structure[synergy_object.get_object_name()] = cwd
            #logger.debug("object: %s child %s cwd %s" % (obj.get_object_name
            # (), o.get_object_name(), cwd))
            # Add the project to the queue
            next_on_queue.append(synergy_object)
            # Add the project to the hierarchy,
            # so the subprojects for the release/project is known
            if synergy_object.get_object_name() in hierarchy.keys():
                hierarchy[synergy_object.get_object_name()].append(
                    '%s%s' % (cwd, synergy_object.get_name()))
            else:
                hierarchy[synergy_object.get_object_name()] = \
                ['%s%s' % (cwd, synergy_object.get_name())]
        else:
            # Add the object to the hierarchy
            if synergy_object.get_object_name() in hierarchy.keys():
                hierarchy[synergy_object.get_object_name()].append(
                    '%s%s' % (cwd, synergy_object.get_name()))
            else:
                hierarchy[synergy_object.get_object_name()] = \
                ['%s%s' % (cwd, synergy_object.get_name())]

    return next_on_queue, hierarchy, dir_structure, proj_lookup


def get_and_lock_free_ccm_addr(free_ccm):
    """ Get a free ccm session and mark it as being in use """
    for k in free_ccm.keys():
        entry = free_ccm[k]
        if free_ccm[k]['free']:
            # Extract dict entry and write it back to dict to inform manager
            # of update
            entry['free'] = False
            free_ccm[k] = entry
            return k, free_ccm[k]['database']


def get_objects_in_project_parallel(project, ccmpool=None, use_cache=False):
    """ Get all the objects and paths of project with use of multiple ccm
    sessions """
    mgr = Manager()
    free_ccm = mgr.dict()

    for ccm in ccmpool.sessionArray.values():
        free_ccm[ccm.getCCM_ADDR()] = {'free': True, 'database': ccm.database}
    ccm_addr, database = get_and_lock_free_ccm_addr(free_ccm)
    ccm = SynergySession(database, ccm_addr=ccm_addr)
    ccm.keep_session_alive = True
    delim = ccm.delim()

    semaphore = mgr.Semaphore(ccmpool.nr_sessions)

    # Starting project
    if use_cache:
        start_object = ccm_cache.get_object(project, ccm)
    else:
        start_object = SynergyObject(project, delim)

    # unlock update dict entry to inform manager
    entry = free_ccm[ccm_addr]
    entry['free'] = True
    free_ccm[ccm_addr] = entry

    p_queue = mgr.Queue()
    c_queue = mgr.Queue()
    c_queue.put((start_object, None))
    p_queue.put(start_object)

    # start the produce and consumer thread
    prod = Process(target=producer, args=(c_queue, p_queue, free_ccm))
    cons = Process(target=consumer, args=(c_queue, p_queue, free_ccm,
                                          semaphore, delim, use_cache))

    prod.start()
    cons.start()
    logger.debug("Waiting to join")
    cons.join()
    hierarchy = p_queue.get()
    prod.join()

    return hierarchy


def consumer(c_queue, p_queue, free_ccm, semaphore, delim, use_cache):
    """ This thread handles queries to the ccm sessions by allpying them
    async to a process pool """
    done = False
    pool = Pool(len(free_ccm.keys()))

    while not done:
        #get item from queue
        #logger.debug("Object count ------ ... P queue length %6d ... C queue
        # length %6d" % (p_queue.qsize(), c_queue.qsize()))
        next_in_queue = c_queue.get()
        if next_in_queue == "DONE":
            #done = True
            break

        semaphore.acquire()
        pool.apply_async(do_query,
                         (next_in_queue, free_ccm, semaphore, delim, p_queue, use_cache))

    pool.close()
    pool.join()


def producer(c_queue, p_queue, free_ccm):
    """ Handle the query results from synergy and put new projects / dirs on
    the queue to be handled """
    project_hierarchy = {}
    dir_structure = {}
    proj_lookup = {}

    start_project = p_queue.get()
    dir_structure[start_project.get_object_name()] = ''
    project_hierarchy[start_project.get_object_name()] = [start_project.name]
    done = False
    while not done or p_queue.qsize() > 0:
        # check if all ccm's are free for 5 seconds if they are it's all done
        #if not p_queue.qsize():
        done = True
        for i in range(10):
            if [free_ccm[k]['free'] for k in free_ccm.keys() if
                free_ccm[k]['free'] == False]:
                done = False
                logger.debug("ccm busy...")
                break
            else:
                logger.debug("sleep...")
                if p_queue.qsize() > 0:
                    done = False
                    break
                time.sleep(0.1)

        if done:
            break
#        logger.debug("Thread: %s ", multiprocessing.current_process().name)

        # Get results from ccm query and put new objects on the queue
        try:
            next_in_queue = p_queue.get(timeout=1200) # 1200 secs,
            # to allow ccm_cache to populate if option is chosen
        except Queue.Empty:
            logger.warning("Synergy timeout")
            logger.debug("Free ccm: %s ",
                         [k['free'] for k in free_ccm.values()] )
            for k in free_ccm.keys():
                entry = free_ccm[k]
                if free_ccm[k]['free']:
                    entry['free'] = True
                    free_ccm[k] = entry
            break
        (objects, project_hierarchy, dir_structure, proj_lookup) = \
        do_results(next_in_queue, project_hierarchy, dir_structure, proj_lookup)

        # put on queue
        for synergy_object in objects:
            parent_proj = None
            if synergy_object.get_type() == 'dir':
                parent_proj = proj_lookup[synergy_object.get_object_name()]
            c_queue.put((synergy_object, parent_proj))

        logger.debug("Objects %6d ... P queue %6d ... C queue %6d" % (
        len(project_hierarchy.keys()), p_queue.qsize(), c_queue.qsize()))

    logger.debug("we're done...")
    if done:
        c_queue.put("DONE")
    p_queue.put(project_hierarchy)


def main():
    pass

if __name__ == '__main__':
    main()



