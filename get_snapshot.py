#!/usr/bin/env python
# encoding: utf-8
"""
get_snapshot.py

Fetch project from synergy and store on disc

Created by Aske Olsson 2011-09-22.
Copyright (c) 2011 Aske Olsson. All rights reserved.
"""

from ccm_objects_in_project import get_objects_in_project
import os

def get_snapshot(project, ccm, outdir):
    if not outdir.endswith('/'):
        outdir += '/'
    # get all objects in the project
    objects = get_objects_in_project(project, ccm)

    # write the objects to outdir
    for object, paths in objects.iteritems():
#        print object, paths
        if not ':dir:' in object and not ':project:' in object:
            content = ccm.cat(object).run()
            for path in paths:
                p = outdir + path
                dir = os.path.split(p)[0]
                if not os.path.exists(dir):
                    os.makedirs(dir)
                print "Writing %s to %s" %(object, p)
                f = open(p, 'wb')
                f.write(content)
                f.close()

    # handle empty dirs by adding .gitignore to empty leaf dirs
    empty_dirs = get_empty_dirs(objects)
    write_empty_dirs(empty_dirs, outdir)

def write_empty_dirs(dirs, outdir):
    for dir in dirs:
        path = os.path.join(outdir, dir)
        filepath = os.path.join(path, '.gitignore')
        if not os.path.exists(path):
            os.makedirs(path)
        print "Writing empty .gitignore to %s" %filepath
        f = open(filepath, 'wb')
        f.write('')
        f.close()

def get_empty_dirs(objects):
    dirs = [d for o, paths in objects.iteritems() for d in paths if ':dir:' in o]
    file_dirs = [d.rsplit('/',1)[0] for o, paths in objects.iteritems() for d in paths if ':dir:' not in o and ':project:' not in o]
    leaf_dirs = get_leaf_dirs(dirs)
    empty_leaves = set(leaf_dirs) - set(file_dirs)
    return empty_leaves

def get_leaf_dirs(dirs):
    res = [sorted(dirs)[0]]
    previous = res[0]
    for dir in sorted(dirs):
        if previous in dir:
            res.remove(previous)
        res.append(dir)
        previous = dir
    return res

def main():
    pass

if __name__ == '__main__':
    main()
