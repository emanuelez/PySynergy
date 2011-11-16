#!/usr/bin/env python
# encoding: utf-8
"""
add_project_snapshot_to_git.py

Fetch project from synergy and add to git repo

Created by Aske Olsson 2011-09-22.
Copyright (c) 2011 Aske Olsson. All rights reserved.
"""
from optparse import OptionParser
import os
from subprocess import Popen, PIPE
import sys
from SynergySession import SynergySession, SynergyException
from get_snapshot import get_snapshot

COLOR = {'WHITE':'\033[97m',
    'CYAN':'\033[96m',
    'PURPLE':'\033[95m',
    'BLUE':'\033[94m',
    'YELLOW':'\033[93m',
    'GREEN':'\033[92m',
    'RED':'\033[91m',
    'GRAY':'\033[90m',
    'ENDC':'\033[0m'}

def run_command(command):
    """Execute a command"""
    p = Popen(command, stdout=PIPE, stderr=PIPE)

    # Store the result as a single string.
    stdout, stderr = p.communicate()

    if stderr:
        raise GitException('Error: ' + stderr)
    return stdout

def add_project(project, db, commit_msg, parent=None, branch_name=None, path=None):
    print "Starting Synergy..."
    ccm = SynergySession(db)
    if not project_ok(project, ccm):
        raise Exception("Error no such Synergy project")
    if not git_project_ok():
        raise Exception("Git project not ok, cwd needs to be git project root")

    cwd = os.getcwd()
    if parent:
        # if not on the branch already check it out
        if not parent == get_current_branch():
            command = ['git', 'checkout', '-q', parent]
            run_command(command)
    else:
        #check out first commit and create branch from here
        first_commit = run_command(['git', 'log', '--format=%H']).splitlines()[-1]
        command = ['git', 'checkout', '-q', first_commit]
        run_command(command)

    # setup new branch
    if branch_name:
        if branch_name != get_current_branch():
            run_command(['git', 'checkout', '-q', '-b', branch_name])

    # setup path to import project into
    if path:
        if not os.path.exists(path):
            os.makedirs(path)
            os.chdir(path)
            cwd = os.getcwd()
        else:
            os.chdir(path)
            cwd = os.getcwd()
            try:
                run_command(['git', 'rm', '-q', '-rf', cwd])
            except GitException as ex:
                if not 'did not match any files' in ex.value:
                    raise Exception("Error deleting files in {0}".format(cwd))
    else:
        # delete everything
        try:
            run_command(['git', 'rm', '-q', '-rf', cwd])
        except GitException as ex:
            if not 'did not match any files' in ex.value:
                raise Exception("Error deleting files in {0}".format(cwd))

    print "Creating snapshot of project"
    get_snapshot(project, ccm, cwd)
    # add everything to git
    print "Adding project to git"
    run_command(['git', 'add', '.'])
    print "Committing..."
    out = run_command(['git', 'commit', '-m', '\n'.join(commit_msg)])
    print out
    if '(no branch)' in get_current_branch():
        # detached head state
        current_commit = get_current_commit()
        #find which branch contains parent commit
        if not parent:
            parent = get_parent_commit(current_commit)
        branches = run_command(['git', 'branch', '--contains', parent]).splitlines()
        branch = None
        for branch in branches:
            if not '(no branch)' in branch:
                break
        # Checkout branch and fast-forward
        out = run_command(['git', 'checkout', '-q', branch.strip()])
        print out
        out = run_command(['git', 'merge', current_commit])
        print out
    print "Done"


def get_parent_commit(commit):
    info = run_command(['git', 'cat-file', '-p', commit]).splitlines()
    for line in info:
        splitted = line.split()
        if splitted[0] == 'parent':
            return splitted[1]

def get_current_commit():
    return run_command(['git', 'rev-parse', 'HEAD']).strip()

def get_current_branch():
    branches = run_command(['git', 'branch'])
    branch = [b.split(' ', 1)[1] for b in branches.splitlines() if b.startswith('*')][0]
    return branch

class GitException(Exception):
    """User defined exception"""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

def project_ok(project, ccm):
    # Check if project exists
    try:
        ccm.query("is_successor_of('{0}')".format(project)).run()
    except SynergyException:
        return False
    return True

def git_project_ok():
    entries = os.listdir(os.getcwd())
    if '.git' in entries:
        return True
    return False

def get_input(db, project, parent, branch, commit_msg, path):
    done = False
    if not project:
        project = raw_input("Please enter project to import to git: ")
    if not db:
        db = raw_input("Please enter database: ")
    if not parent:
        parent = raw_input("Please enter parent (SHA or branch) \nif none the first commit will be selected as parent: ")
    if not branch:
        branch = raw_input("Please enter branch name if new branch should be created: ")
    if commit_msg == [None]:
        print "Please enter commit message, when done enter %s on its own line:" % color_string('yellow', "'.'")
        commit_msg = []
        while not done:
            line = raw_input()
            if line == '.':
                done = True
            else:
                commit_msg.append(line)
    if not path:
        path = raw_input("Please enter path if different from project root: ")
    return db, project, parent, branch, commit_msg, path

def input_ok(db, project, parent, branch, commit_msg, path):
    # Confirm that input is ok
    print color_string('purple', "Please confirm information")
    print "Database: " + color_string('green', db)
    print "Project: %s will be imported" % color_string('green', project)
    if parent:
        print "Parent: " + color_string('green',parent)
    else:
        print "No parent given, first commit will be used:"
        commit = run_command(['git', 'log', '--oneline', '--format="%H %s"']).splitlines()[-1]
        print color_string('red', commit)
    if branch:
        print "Branch %s will be created" % color_string('green', branch)
    print "Commit message:\n" + color_string('green', '\n'.join(commit_msg))
    if path:
        print "Path: " + color_string("green", path)
    print ""

    ok = raw_input(color_string('yellow', "Input ok (Y/n)?"))
    if not ok:
        # defaults to Y
        return True
    if 'y' in ok or 'Y' in ok:
            return True
    return False

def color_string(color, string):
    if COLOR.has_key(color.upper()):
        return COLOR[color.upper()] + string + COLOR['ENDC']
    else:
        return string

def check_input(argv):
    usage = "usage: %prog"
    parser = OptionParser(usage=usage)
    parser.add_option("-p", "--project", action="store", type="string", dest="project", help="Project to import to git")
    parser.add_option("-d", "--database", action="store", type="string", dest="database", help="Synergy database")
    parser.add_option("-b", "--branch", action="store", type="string", dest="branch", help="Branch to create (optional)")
    parser.add_option("-c", "--commit-message", action="store", type="string", dest="commit_msg", help="Commit message for project")
    parser.add_option("--parent", action="store", type="string", dest="parent", help="Set SHA/branch as parent for commit (optional)")
    parser.add_option("--path", action="store", type="string", dest="path", help="Path where project should be imported")
    (options, args) = parser.parse_args(argv)
    db = options.database
    project = options.project
    parent = options.parent
    branch = options.branch
    commit_msg = [options.commit_msg]
    path = options.path

    return db, project, parent, branch, commit_msg, path

def main():

    db, project, parent, branch, commit_msg, path = check_input(sys.argv[1:])
    if not project or not db or commit_msg == [None] or (not branch and not parent):
        ok = False
        while not ok:
            db, project, parent, branch, commit_msg, path = get_input(db, project, parent, branch, commit_msg, path)
            ok = input_ok(db, project, parent, branch, commit_msg, path)

    add_project(project, db, commit_msg, branch_name=branch, parent=parent, path=path)

if __name__ == '__main__':
    main()

