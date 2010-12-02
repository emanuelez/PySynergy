#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

Created by Emanuele Zattin on 2010-11-08.
Copyright (c) 2010 Emanuele Zattin. All rights reserved.
"""

import os
from subprocess import Popen, PIPE

class SynergySession:
    """This class is a wrapper around the Synergy command line client"""

    def __init__(self, database, engine = None, command_name = 'ccm', ccm_ui_path = '/dev/null', ccm_eng_path = '/dev/null'):
        self.command_name = command_name
        self.database     = database
        self.engine       = engine

        # This dictionary will contain the status of the next command and will be emptied by self.run()
        self.command = ''
        self.status  = {}

        # Store the warnings and errors that might be found along the preparation or execution of a command
        self.warnings = []
        self.errors   = []

        # Open the session
        args = [self.command_name]
        args.append('start')
        args.append('-nogui')
        args.append('-d')
        args.append(self.database) # database
        args.append('-m') # permit multiple sessions
        args.append('-q') #quiet
        if self.engine:
            args.append('-d')
            args.append(self.engine) # engine

        self.environment = os.environ
        self.environment['CCM_UILOG'] = ccm_ui_path
        self.environment['CCM_ENGLOG'] = ccm_eng_path

        # Open the session
        p = Popen(args, stdout=PIPE, stderr=PIPE, env=self.environment)
        # Store the session data
        p.wait()
        stdout, stderr = p.communicate()

        if stderr:
            raise SynergyException('Error while starting a synergy Session: ' + stderr)

        # Set the environment variable for the Synergy session
        self.environment['CCM_ADDR'] = stdout

        # Get the delimiter and store it
        self.delimiter = self.delim()

    def __del__(self):
        # Close the session
        self.stop()

    def _reset_status(self):
        """Reset the status of the object"""
        self.command  = ''
        self.status   = {}
        self.warnings = []
        self.errors   = []

    def _run(self, command):
        """Execute a Synergy command"""

        if not command[0] == self.command_name:
            command.insert(0, self.command_name)

        p = Popen(command, stdout=PIPE, stderr=PIPE, env=self.environment)

        # Store the result as a single string. It will be splitted later
        #p.wait()
        stdout, stderr = p.communicate()

        if stderr:
            raise SynergyException('Error while running the Synergy command: %s \nError message: %s' % (command, stderr))

        return stdout

    def delim(self):
        """Returns the delimiter defined in the Synergy DB"""
        self._reset_status()
        return self._run(['delim'])

    def stop(self):
        """Stops the current Synergy session"""
        if 'CCM_ADDR' in self.environment:
            self._run(['stop'])

    def query(self, query_string):
        """Set a query that will be executed"""
        self.command = 'query'
        self.status['arguments'] = query_string
        self.status['formattable'] = True
        if 'format' not in self.status:
            self.status['format'] = ['%objectname']
        return self

    def format(self, format):
        """Sets the output format for the command, if it supports formatting.

        The input can be an iterable or a string"""
        if isinstance(format, str):
            self.status['format'].append(format)
            return self

        if not hasattr(format, '__iter__'):
            self.warnings.append('The argument of format(format) must be something iterable or a string')
            return self

        if not self.status['format']:
            for element in format:
                self.status['format'].append(element)

        return self

    def run(self):
        """
        Run the Synergy command.

        At this point the command must be already set by i.e. query()
        """
        if not self.status:
            self.errors.append('before run() the status of the command must be already set')

        command = [self.command_name]

        command.append(self.command)

        if 'formattable' in self.status and self.status['formattable']:
            if 'format' not in self.status:
                raise SynergyException("status['format'] undefined")
            command.append('-u')
            command.append('-nf')
            command.append('-f')
            command.append('|SEPARATOR|'.join(self.status['format']) + '|ITEM_SEPARATOR|')

        if 'arguments' not in self.status:
            raise SynergyException("status['arguments'] undefined")

        command.append(self.status['arguments'])

        result = self._run(command)

        # Parse the result and return it
        if 'formattable' in self.status and self.status['formattable']:
            if not result:
                # Clean up
                self._reset_status()
                return []

            final_result = []
            for item in result.split('|ITEM_SEPARATOR|')[:-1]:
                splitted_item = item.split('|SEPARATOR|')
                if len(splitted_item) != len(self.status['format']):
                    raise SynergyException("the length of status['format'] and the splitted result is not the same")
                line = {}
                for k, v in zip(self.status['format'], splitted_item):
                    line[k[1:]] = v
                final_result.append(line)
            # Clean up
            self._reset_status()
            return final_result
        else:
            # Clean up
            self._reset_status()
            return result


class SynergyException(Exception):
    """User defined exception raised by SynergySession"""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)



def main():
    # Test
    ccm = SynergySession('/nokia/co_nmp/groups/gscm/dbs/co1asset')
    results = ccm.query("is_associated_cv_of(task('co1asset#113266'))").format("%objectname").run()
    print results


if __name__ == '__main__':
    main()

