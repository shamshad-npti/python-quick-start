#!/usr/bin/env python
import json
import ConfigParser
from collections import defaultdict

_STRING_TYPES = (str, unicode)


class Config(defaultdict):
    """
    A configuration dictionary, but it has additional methods to populate
    dict from files or other objects.
    """

    _error = []

    def __init__(self):
        defaultdict.__init__(self)

    def from_cfgfile(self, filename, sections=[]):
        """
        reads a config.cfg file and parses it using the ConfigParser
        module, adds each section as a key to the configuration dict
        and any subsequent items as key values to a an imbdeded default
        dict
        """
        config = ConfigParser.ConfigParser()
        if isinstance(filename, file):
            config.readfp(filename)
        else:
            config.read(filename)

        if sections == []:
            sections = config.sections()

        for sec in sections:

            try:
                if sec not in self:
                    self[sec] = {}

                for key, value in config.items(sec):
                    self[sec][key] = value
            except Exception as e:
                self._error.append(str(e))

    def from_object(self, obj):
        """
        updates the config dict from the values in the given
        object
        """
        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)

    def from_json(self, jsonfile):
        """
        loads configuration from a json file
        """
        with open(jsonfile) as js:
            a = json.load(js)
            self.update(a)

    def __repr__(self):
        return '<%s:%s>' % (self.__class__.__name__,
                            defaultdict.__repr__(self))
