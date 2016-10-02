#!/usr/bin/env python
# -*- coding: utf-8 -*-
from glob import glob
import os
import sys
import json

base_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.dirname(base_dir))
static_dir = os.path.join(base_dir, 'static')


def parse_json(file_content):
    return json.loads(file_content)


def load_static_files(path):
    data = []
    for i in glob(static_dir + '/*.json'):
        file_content = read_file(i)
        try:
            js = parse_json(file_content)
            data.append(js)
        except ValueError:
            print >> sys.stderr, '%s invalid json' % i
    # print data,
    return data


def read_file(file_path):
    with open(file_path, 'rb') as f:
        return f.read()


def add_static_attr(cls):
    static_data = load_static_files(static_dir)
    for jsn in static_data:
        for k in jsn.keys():
            setattr(cls, k.upper(), jsn.get(k))
    return cls


@add_static_attr
class BaseConfig(object):
    """
    All common settings that do not change
    across
    """
    BQ_JOB_TIMEOUT = 3600
    GC_COMPRESSION = "GZIP"
    GC_DEST_FORMAT = "NEWLINE_DELIMITED_JSON"
    GC_FILE_EXT = "_*.json.gz"


class DevelopmentConfig(BaseConfig):
    """
    Development only configuration
    environment should be set in this class
    """


class TestingConfig(BaseConfig):
    """
    Testing configration should be set in
    this class
    """


class ProductionConfig(BaseConfig):
    """
    Production only configuration should
    be set in this class only
    """


settings = {
    'development': DevelopmentConfig,
    'test': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
