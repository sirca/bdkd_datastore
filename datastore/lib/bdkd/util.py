#!/usr/bin/env python

import bdkd.datastore
import argparse
import pprint

def _repo_resource_op(prog, desc):
    """ A common function that can be used by a typical repo-resource utility
    as they all have something in common.
    :param prog: the name of the utility
    :param desc: the description of the utility
    :returns (repo,resource_name)
    """
    parser = argparse.ArgumentParser(prog=prog, description=desc)
    parser.add_argument("repository", help="The repository that the resource is under")
    parser.add_argument("resource", help="The resource to get the key from")
    args = parser.parse_args()

    repo = bdkd.datastore.repository(args.repository)
    if not repo:
        ArgumentParser.error("The repository {0} is not valid or not configured".format(args.repository))
    return (repo, args.resource)


def getkey_util():
    """ Entry point for the datastore-getkey utility.
    """
    (repo, resource_name) = _repo_resource_op(prog='datastore-getkey', desc='To get the information about the key of a resource')
    resource_key = repo.get_resource_key(resource_name)
    pprint.pprint(resource_key.__dict__)


def lastmod_util():
    """ Entry point for the datastore-lastmod utility.
    """
    (repo, resource_name) = _repo_resource_op(prog='datastore-lastmod', desc='To get the last modified date of a resource')
    last_mod = repo.get_resource_last_modified(resource_name)
    print "Last modified: %s" % (last_mod)
