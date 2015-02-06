#!/usr/bin/env python

"""
Utility for adding, removing, listing, etc resources
in a datastore.
"""

import argparse
import os
import urlparse
import pprint
import bdkd.datastore
import bdkd.datastore.util.common as util_common

class FilesAction(argparse.Action):
    """
    Action to perform for file arguments: check that they are either files or 
    remote URIs.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        for filename in values:
            if not os.path.exists(filename):
                url = urlparse.urlparse(filename)
                if not url.netloc:
                    raise ValueError("The file '{0}' is neither a local filename nor a URL"
                            .format(filename))
        setattr(namespace, self.dest, values)


def _files_parser():
    """
    Parser that handles the list of files provided on the command line
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('filenames', nargs='+', action=FilesAction,
            help='List of local file names or URLs of remote files (HTTP, FTP)')
    return parser


def _metadata_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--metadata', 
            action=util_common.JsonDictionaryAction, 
            default=dict(),
            help="Meta-data for resource (JSON string dictionary: '{...}')")
    return parser


def _add_options_parser():
    """
    Parser for various options related to adding
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--force', action='store_true', default=False,
            help="Force overwriting any existing resource")
    parser.add_argument('--bundle', action='store_true', default=False,
            help="Bundle all files together")
    return parser

def _bdkd_metadata_parser(enforce=True):
    """
    Parser for BDKD-specific meta-data options.
    """
    parser = argparse.ArgumentParser(add_help=False)
    # Mandatory arguments
    parser.add_argument('--description', required=enforce,
            help='Human-readable description of the resource')
    parser.add_argument('--author', required=enforce,
            help='Name of the author/creator')
    parser.add_argument('--author-email', required=enforce,
            help='Email address of the author/creator')

    # Optional arguments
    parser.add_argument('--data-type',
            help='String describing the kind of data provided by the Resource')
    parser.add_argument('--tags', action=util_common.JsonArrayAction,
            help='JSON list of additional tags for the Resource')
    parser.add_argument('--version',
            help='Version string for the Resource')
    parser.add_argument('--maintainer',
            help='Name of the person responsible for maintaining the Resource')
    parser.add_argument('--maintainer-email',
            help='Email address of the maintainer')
    parser.add_argument('--custom-fields', action=util_common.JsonDictionaryAction,
            help="A JSON dictionary ('{...}') containing additional custom "
            "fields to be stored in the Resource's meta-data")

    return parser


def _repository_resource_from_to_parser():
    """
    Parser for various options related to adding
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('from_repository', action=util_common.RepositoryAction,
            help='Name of the source repository')
    parser.add_argument('from_resource_name',
            help='Name of the source Resource (exists)')
    parser.add_argument('to_repository', nargs='?', default=None,
            action=util_common.OptionalRepositoryAction,
            help='Name of the destination repository (default source)')
    parser.add_argument('to_resource_name',
            help='Name of the destination Resource')
    return parser


def _create_subparsers(subparser):
    subparser.add_parser('add', help='Add a Resource to a datastore',
                         description='Add a Resource to a datastore, optionally '
                         'overwriting any other Resource of the same name.',
                         parents=[
                             util_common._repository_resource_parser(),
                             _files_parser(),
                             _metadata_parser(),
                             _add_options_parser(),
                         ])
    subparser.add_parser('add-bdkd', help='Add a Resource to a datastore (with BDKD options)',
                         description='Add a Resource to a datastore, including options '
                         'related to BDKD.',
                         parents=[
                             util_common._repository_resource_parser(),
                             _files_parser(),
                             _metadata_parser(),
                             _add_options_parser(),
                             _bdkd_metadata_parser(),
                         ])
    subparser.add_parser('copy', help='Copy a resource',
                         description='Copy a resource within datastore',
                         parents=[
                             _repository_resource_from_to_parser(),
                         ])
    subparser.add_parser('move', help='Move a resource',
                         description='Move a resource within datastore',
                         parents=[
                             _repository_resource_from_to_parser(),
                         ])
    subparser.add_parser('getkey', help='Get information about the key of a resource',
                         description='Get information about the key of a resource',
                         parents=[
                             util_common._repository_resource_parser(),
                         ])
    subparser.add_parser('lastmod', help='Get the last modified date of a resource',
                         description='Get the last modified date of a resource',
                         parents=[
                             util_common._repository_resource_parser(),
                         ])
    subparser.add_parser('update-metadata', help='Update a resource\'s metadata',
                         description='Update a resource\'s meta-data, including BDKD options',
                         parents=[
                             util_common._repository_resource_parser(),
                             _metadata_parser(),
                             _bdkd_metadata_parser(enforce=False)
                         ])
    subparser.add_parser('delete', help='Delete a resource from a repository',
                         description='Delete a resource from a repository', 
                         parents=[
                             util_common._repository_resource_parser(),
                         ])
    subparser.add_parser('get', help='Get details of a Resource as JSON text.',
                         description='Get details of a Resource as JSON text. The meta-data and list '
                         'of Files for a Resource will be printed to STDOUT as JSON text.',
                         parents=[
                             util_common._repository_resource_parser(),
                         ])
    subparser.add_parser('files', help='List of locally-cached filenames',
                         description='List of locally-cached filenames for the given Resource', 
                         parents=[
                             util_common._repository_resource_parser(),
                         ])
    list_parser = subparser.add_parser('list', help='Get a list of all Resources in a Repository',
                         description='Get a list of all Resources in a Repository (or optionally '
                         'those Resources underneath a leading path).',
                         parents=[
                             util_common._repository_parser()
                         ])
    list_parser.add_argument('--path', '-p', help='Email address of the maintainer')
    list_parser.add_argument('--verbose', '-v', action='store_true', default=False,
                             help='Verbose mode: all resource details (default names only)')
    
    repositories_parser = subparser.add_parser('repositories', help='Get a list of all configured Repositories',
                                               description='Get a list of all configured Repositories')
    repositories_parser.add_argument('--verbose', '-v', action='store_true', default=False,
                                     help='Verbose mode: all resource details (default names only)')
    return subparser



def create_parsed_resource(resource_args, meta_parser=None, argv=None):
    """
    Creates an unsaved Resource object by parsing the provided arguments 
    (default: sys.argv) using the given resource arguments and metadata parser.

    If a metadata parser is provided it will be used to parse arguments from 
    argv.  These arguments will be treated as meta-data: they will be merged 
    into the metadata dictionary and used when creating the resource.
    """
    metadata = dict(**resource_args.metadata)
    if meta_parser:
        meta_args = meta_parser.parse_known_args(argv)
        metadata.update(meta_args[0].__dict__)
    metadata = dict((k, v) for k, v in metadata.items() if v != None)
    resource_items = []
    for item in resource_args.filenames:
        if os.path.exists(item) and os.path.isdir(item):
            # item is a dir, so recursively expands directories into files
            for root, dir, files in os.walk(item):
                for f in files:
                    resource_items.append(os.path.join(root, f))
        else:
            resource_items.append(item)

    if len(resource_items) == 0:
        raise ValueError("Unable to create an empty resource")
    resource = bdkd.datastore.Resource.new(resource_args.resource_name, 
            files_data=resource_items,
            metadata=metadata,
            do_bundle=resource_args.bundle)
    return resource

def _save_resource(repository, resource, force=False):
    existing = repository.get(resource.name)
    if existing:
        if force:
            repository.delete(existing)
        else:
            raise ValueError("Resource '{0}' already exists (use '--force' to overwrite)"
                    .format(resource.name))
    repository.save(resource)


def _copy_or_move(copy_move_args, do_move=False):
    to_repository = copy_move_args.to_repository
    if not to_repository:
        to_repository = copy_move_args.from_repository
    from_resource = copy_move_args.from_repository.get(
            copy_move_args.from_resource_name)
    if not from_resource:
        raise ValueError("From resource '{0}' does not exist!"
                .format(copy_move_args.from_resource_name))
    if do_move:
        to_repository.move(from_resource, copy_move_args.to_resource_name)
    else:
        to_repository.copy(from_resource, copy_move_args.to_resource_name)

def _update_metadata(repository, resource_name, metadata):
    existing = repository.get(resource_name)
    if existing:
        repository.edit_resource(existing)
        existing.metadata.update(metadata)
        existing.metadata = dict((k, v) for k, v in existing.metadata.items()
                if v != None)
        repository.save(existing, overwrite=True)
    else:
        raise ValueError("Resource '{0}' does not exist!".format(resource_name))


def _update_with_parser(args, meta_parser, argv):
    metadata = dict()
    if meta_parser:
        meta_args = meta_parser.parse_known_args(argv)
        metadata = dict((k, v) for k, v in meta_args[0].__dict__.items() 
                if v != None)
    metadata.update(args.metadata)
    _update_metadata(args.repository, args.resource_name, metadata)

def _delete_resource(repository, resource_name):
    resource = repository.get(resource_name)
    if resource:
        repository.delete(resource)
    else:
        raise ValueError("Resource '{0}' does not exist!".format(resource_name))

def _get_resource_details(repository, resource_name):
    resource = repository.get(resource_name)
    if resource:
        print resource.to_json(indent=4, separators=(',', ': '))
    else:
        raise ValueError("Resource '{0}' does not exist!".format(resource_name))

def _list_resource_files(repository, resource_name):
    resource = repository.get(resource_name)
    if resource:
        paths = resource.local_paths()
        for path in paths:
            print path
    else:
        raise ValueError("Resource '{0}' does not exist!".format(resource_name))

def _list_resources(repository, path, verbose):
    resource_names = repository.list(path or '')
    for resource_name in resource_names:
        print resource_name
        if verbose:
            resource = repository.get(resource_name)
            print resource.to_json(indent=4, separators=(',', ': ')) + '\n'

def _list_repositories(verbose):
    repositories = bdkd.datastore.repositories()
    for name, repository in repositories.items():
        print name
        if verbose:
            print "\tCache path:\t{0}".format(repository.local_cache)
            print "\tWorking path:\t{0}".format(repository.working)
            print "\tStale time:\t{0}".format(repository.stale_time)
    


def ds_util(argv=None):
    """
    Main entry point for datastore-util
    """
    parser = argparse.ArgumentParser(prog='datastore-util', description='Perform actions on a datastore')
    
    subparser = parser.add_subparsers(description='The following datastore commands are avilable', dest='subcmd')
    _create_subparsers(subparser)

    args = parser.parse_args(argv)

    if args.subcmd == 'add':
        resource = create_parsed_resource(args)
        _save_resource(args.repository, resource, args.force)
    elif args.subcmd == 'add-bdkd':
        resource = create_parsed_resource(args, meta_parser=_bdkd_metadata_parser(), argv=argv)
        _save_resource(args.repository, resource, args.force)
    elif args.subcmd == 'copy':
        _copy_or_move(args, do_move=False)
    elif args.subcmd == 'move':
        _copy_or_move(args, do_move=True)
    elif args.subcmd == 'getkey':
        resource_key = args.repository.get_resource_key(args.resource_name)
        pprint.pprint(resource_key.__dict__)
    elif args.subcmd == 'lastmod':
        last_mod = args.repository.get_resource_last_modified(args.resource_name)
        print "Last modified: %s" % (last_mod)
    elif args.subcmd == 'update-metadata':
        _update_with_parser(args, _bdkd_metadata_parser(enforce=False), argv)
    elif args.subcmd == 'delete':
        _delete_resource(args.repository, args.resource_name)
    elif args.subcmd == 'get':
        _get_resource_details(args.repository, args.resource_name)
    elif args.subcmd == 'files':
        _list_resource_files(args.repository, args.resource_name)
    elif args.subcmd == 'list':
        _list_resources(args.repository, args.path, args.verbose)
    elif args.subcmd == 'repositories':
        _list_repositories(args.verbose)

