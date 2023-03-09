## DRAFT

# install synergy
# Launch once the tool CLI, through the tool menu to let it create com.user.properties in %USERPROFILE% directory.
# Append to it the content of com.user.properties.sample.

# Install git (git bash for windows is right).

# python interpreter: Download & install
# https://www.python.org/downloads/release/python-31010/
# Or use any prefered way to get it (direct install, store, chocolatey, vcpkg, visual studio code)

# Microsoft Visual C++ 14.0 
# https://visualstudio.microsoft.com/visual-cpp-build-tools/
# Install build tools for C/C+ for desktop from installer
# if install need CMD relaunch

# install vcpkg
# cancelled for non supported service ldap and finger, and install a lot of dependencies.

# create venv
Use batch file


# Manual python package pygraphviz
# https://pygraphviz.github.io/documentation/stable/install.html
# Use windows section, manual download
# 	Install graphviz
# 	Then call pip install in the venvironment.


# pip packages
# 	! need to be disconnected from Guerbet Network (but can be Guerbet Machine)
pickle
# pygraph pypi package is not the one -> python-graph
# Pypi package seems correct, otherwise project home is here : https://github.com/Shoobx/python-graph/tree/master/core
python-graph-core
networkx
configparser


# Code changes : 
# cPickle is not available.
cPickle -> pickle
