#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

Created by Emanuele Zattin on 2010-11-08.
Copyright (c) 2010 Emanuele Zattin. All rights reserved.
"""

import sys
import os

class SynergySession:
	"""This class is a wrapper around the Synergy command line client"""
	
	def __init__(self, database, engine = None, command_name = 'ccm', ccm_ui_path = '/dev/null', ccm_eng_path = '/dev/null'):
		self.command_name = command_name
		self.database     = database
		self.engine       = engine
		self.ccm_ui_path  = ccm_ui_path
		self.ccm_eng_path = ccm_eng_path
		
		# This dictionary will contain the status of the next command and will be emptied by self.run()
		self.command = ''
		self.status  = {}
		
		# Store the warnings and errors that might be found along the preparation or execution of a command
		self.warnings = []
		self.errors   = []
		
		# TODO: Open the session
		# TODO: Store the session data
		# Get the delimiter and store it
		self.delimiter = self.delim()
		
	def __del__(self):
		# TODO: Close the session
		pass
		
	def _reset_status(self):
		"""Reset the status of the object"""
		self.command  = ''
		self.status   = {}
		self.warnings = []
		self.errors   = []
	
	def _run(self, command):
		"""Execute a Synergy command"""
		# TODO: Set the environment variables
		
		if command.startswith(self.command_name):
			# TODO: Run the command as it is
			pass
		else:
			# TODO: Prepend self.command_name to command and run
			pass
			
		# TODO: Store the result as a single string. It will be splitted later 
		pass
		
	def delim(self):
		"""Returns the delimiter defined in the Synergy DB"""
		self._reset_status()
		return self._run('delim')
		
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
			return
			
		if not hasattr(format, '__iter__'):
			self.warnings.append('The argument of format(format) must be something iterable or a string')
			return
			
		for element in format:
			self.status['format'].append(element)
			
	def run(self):
		"""
		Run the Synergy command.
		
		At this point the command must be already set by i.e. query() 
		"""
		if not self.status:
			self.errors.append('before run() the status of the command must be already set')
		
		command += ' ' + self.command
		
		if 'formattable' in self.status and self.status['formattable']:
			if 'format' not in self.status:
				raise SynergyException("status['format'] undefined")
			command += ' -u -nf -f "'
			command += '|SEPARATOR|'.join(self.status['format'])	
			command += '|ITEM_SEPARATOR|"'
			
		if 'arguments' not in self.status:
			raise SynergyException("status['arguments'] undefined")
			
		command += ' "%s"' % self.status['arguments']
		
		result = self._run(command)
		
		# Parse the result and return it
		if 'formattable' in self.status and self.status['formattable']:
			if not result:
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
			return final_result
		else:
			return result
				

class SynergyException(Exception):
	"""User defined exception raised by SynergySession"""
	def __init__(self, value):
		self.value = value
		
	def __str__(self):
		return repr(self.value)
				


def main():
	pass


if __name__ == '__main__':
	main()

