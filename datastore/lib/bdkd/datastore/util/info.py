#!/usr/bin/env python
"""
Module providing utilities for listing resource information.
"""

import bdkd.datastore.util.common as util_common
import argparse
import pprint


def info_parser(prog, desc):
    """
    Parser for info utilities
    """
    parser = argparse.ArgumentParser(prog=prog, description=desc, 
            parents=[
                util_common._repository_resource_parser(),
            ])
    return parser


def getkey_parser():
    return info_parser(prog='datastore-getkey', 
            desc='To get the information about the key of a resource')


def lastmod_parser():
    return info_parser(prog='datastore-lastmod', 
            desc='To get the last modified date of a resource')


def getkey_util(argv=None):
    """ Entry point for the datastore-getkey utility.
    """
    parser = getkey_parser()
    args = parser.parse_args(argv)
    resource_key = args.repository.get_resource_key(args.resource_name)
    pprint.pprint(resource_key.__dict__)


def lastmod_util(argv=None):
    """ Entry point for the datastore-lastmod utility.
    """
    parser = lastmod_parser()
    args = parser.parse_args(argv)
    last_mod = args.repository.get_resource_last_modified(args.resource_name)
    print "Last modified: %s" % (last_mod)
