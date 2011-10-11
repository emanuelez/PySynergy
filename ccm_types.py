#!/usr/bin/env python
# encoding: utf-8
"""
ccm_types.py

Get the ccm types from a database and the corresponding file permission
    type : permission

e.g.: ascii : 0644
      perl : 0755

Created by Aske Olsson 2011-04-14
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
from SynergyObject import SynergyObject

def get_types_and_permissions(ccm):
    type_dict = {}

    types = get_all_types(ccm)

    # Map each type to permission
    for t in types:
        lines = ccm.attr(t.get_object_name()).option("-s").option("file_acs").run().splitlines()
        for line in lines:
            if line.startswith("working"):
                mode = line.split(":")[-1]
                type_dict[t.get_name()] = '10' + mode.strip()
                break
    return type_dict

def get_all_types(ccm):
    delim = ccm.delim()

      # Query for all types
    result = ccm.query("type='attype'").format("%name").format("%version").format("%type").format("%instance").run()
    types = [SynergyObject(t["name"] + delim + t["version"] + ":" + t["type"] + ":" + t["instance"], delim) for t in result]

    return types

def get_super_types(ccm):
    type_dict = {}
    types = get_all_types(ccm)

    # Map each type to permission
    for t in types:
        line = ccm.attr(t.get_object_name()).option("-s").option("super_type").run().strip()
        if 'Attribute \'super_type\'' in line:
            # just skip
            continue
        else:
            type_dict[t.get_name()] = line

    return type_dict

def main():
    pass

if __name__ == '__main__':
    main()

