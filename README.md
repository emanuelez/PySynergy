PySynergy
=========

ccm -> git converter


HOWTO
-----

Create a `configuration.conf` file with the info needed for your setup, 
look in the `configuration.conf.sample`.


Run `get_synergy_history.py` and the converter will start quering the 
Synergy database for project info. Data will be stored in two places:
`ccm_cache_path` from the config will store all Synergy objects as so 
they can easily and fast be be loaded again. The release and task structure
and how everything is linked together is stored in the PySynergy folder.

To do the actual conversion run `do_convert_history.py` and pipe this to 
`git fast-import` or a file for later import through `git fast-import`

Done!

For the conversion of synergy data to git data you'll need to have `pygraph` 
installed.

NOTE
----
If you need assistance or help in migrating from Synergy to git, don't hesitate 
to contact me at aske.olsson@switch-gears.dk

I'm currently not having access to any Synergy servers, so development on 
PySynergy is slow, if not stopped.


