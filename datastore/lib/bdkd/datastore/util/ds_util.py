#!/usr/bin/env python

"""
Utility for adding, removing, listing, etc resources
in a datastore.
"""

import argparse
import os
import posixpath

import yaml
import pprint
import bdkd.datastore
import bdkd.datastore.util.common as util_common

known_metadata_fields = ['description', 'author', 'author_email', 'data_type', 'version',
                         'maintainer', 'maintainer_email']

def _optional_files_parser():
    """
    Parser that handles an optional list of files provided on the command line
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('filenames', nargs='*', action=util_common.FilesAction,
            help='List of local file names or URLs of remote files (HTTP, FTP)')
    return parser

def _files_parser():
    """
    Parser that handles the list of files provided on the command line
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('filenames', nargs='+', action=util_common.FilesAction,
            help='List of local file names or URLs of remote files (HTTP, FTP)')
    return parser


def _metadata_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--metadata-file',
            action=util_common.SingleFileAction,
            help="A YAML file containing metadata and optionally tags")
    return parser


def _create_options_parser():
    """
    Parser for various options related to adding
    """
    parser = argparse.ArgumentParser(add_help=False)
    publish_group = parser.add_mutually_exclusive_group()
    publish_group.add_argument('--publish', action='store_true', dest='publish',
                        help='Publish the resource (default action). Must provide Metadata')
    publish_group.add_argument('--no-publish', action='store_false', dest='publish',
                        help='Resource not published. Metadata is optional')
    parser.set_defaults(publish=True)
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
    mandatory_fields = parser.add_argument_group('Mandatory metadata',
                                                 'Must specify if publishing. If using --no-publish, these may be'
                                                 ' omitted. Either specify on command line or via --metadata-file')
    # Mandatory arguments (not actually mandatory in the argparse sense)
    mandatory_fields.add_argument('--description', dest='description',
            help='Human-readable description of the resource')
    mandatory_fields.add_argument('--author', help='Name of the author/creator')
    mandatory_fields.add_argument('--author-email', help='Email address of the author/creator')

    # Optional arguments
    optional_fields = parser.add_argument_group('Optional metadata',
                                                'Below fields are optional and can also be specified via metadata file')
    optional_fields.add_argument('--data-type',
            help='String describing the kind of data provided by the Resource')
    optional_fields.add_argument('--version',
            help='Version string for the Resource')
    optional_fields.add_argument('--maintainer',
            help='Name of the person responsible for maintaining the Resource')
    optional_fields.add_argument('--maintainer-email',
            help='Email address of the maintainer')


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
    subparser.add_parser('create', help='Create a new Resource',
                         description='Create new Resource, optionally with files and metadata',
                         parents=[
                             util_common._repository_resource_parser(),
                             _metadata_parser(),
                             _bdkd_metadata_parser(),
                             _create_options_parser(),
                             _optional_files_parser(),
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
    subparser.add_parser('get', help='Get details of a Resource as JSON text',
                         description='Get details of a Resource as JSON text. The meta-data and list '
                         'of Files for a Resource will be printed to STDOUT as JSON text',
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

    subparser.add_parser('rebuild-file-list', help='Rebuild Resource\'s file list',
                         description='Rebuild metadata file list of Resource by scanning all files',
                         parents=[
                             util_common._repository_resource_parser()
                         ])

    return subparser

def _parse_metadata_file(filename):
    """
    Opens filename, parses YAML, and returns a tuple consisting of a dictionary of fields, and a list of tags
    """
    if not filename:
        return None, None
    meta_file = open(filename, 'r')
    raw = yaml.load(meta_file)
    tags = []
    if 'tags' in raw:
        tags = raw['tags']
        del raw['tags']

    for key in raw:
        if type(raw[key]) == dict or type(raw[key]) == list:
            raise ValueError("Metadata file cannot contain nested fields: {0}".format(raw[key]))

    return raw, tags

def _check_bdkd_metadata(resource_args):

    def known_fields_present(field):
        return field[1] is not None and field[0] in known_metadata_fields

    metadata = {}
    tags = []
    args_metadata = dict(filter(known_fields_present, vars(resource_args).items()))

    if resource_args.metadata_file:
        file_metadata, tags = _parse_metadata_file(resource_args.metadata_file)
        if file_metadata:
            # Fields in args_metadata should override any identically named ones in file_metadata
            metadata = dict(file_metadata.items() + args_metadata.items())
    else:
        metadata = args_metadata

    return metadata, tags


def create_new_resource(resource_args):
    """
    Creates a new unsaved Resource object by parsing the provided arguments.
    Validates all provided metadata, and returns a datastore Resource.
    """
    metadata, tags = _check_bdkd_metadata(resource_args)

    resource_items = []
    for item in resource_args.filenames:
        item = item.replace("\\","/")
        if os.path.exists(item) and os.path.isdir(item):
            # item is a dir, so recursively expands directories into files
            for root, dir, files in os.walk(item):
                for f in files:
                    resource_items.append(posixpath.join(root, f))
        else:
            resource_items.append(item)

    try:
        resource = bdkd.datastore.Resource.new(resource_args.resource_name,
                files_data=resource_items,
                metadata=metadata,
                do_bundle=resource_args.bundle,
                publish=resource_args.publish)
    except bdkd.datastore.MetadataException, e:
        bad_fields_string = ', '.join(e.missing_fields)
        raise ValueError("Must specify the following fields either on command "
                         "line or via metadata file: {0}".format(bad_fields_string))

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
        existing.metadata.update(metadata)
        existing.metadata = dict((k, v) for k, v in existing.metadata.items()
                if v != None)
        repository.save(existing, overwrite=True)
    else:
        raise ValueError("Resource '{0}' does not exist!".format(resource_name))


def _update_with_parser(resource_args):
    metadata = _check_bdkd_metadata(resource_args)[0]
    _update_metadata(resource_args.repository, resource_args.resource_name, metadata)

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
    

def _build_file_list(repository, resource_name):
    resource = repository.get(resource_name)
    if not resource:
        raise ValueError("Resource '{0} does not exist!".format(resource_name))
    if repository.rebuild_file_list(resource):
        repository.save(resource, overwrite=True)
    else:
        print "Nothing to rebuild"



def ds_util(argv=None):
    """
    Main entry point for datastore-util
    """
    parser = argparse.ArgumentParser(prog='datastore-util', description='Perform actions on a datastore')
    
    subparser = parser.add_subparsers(description='The following datastore commands are available', dest='subcmd')
    _create_subparsers(subparser)

    args = parser.parse_args(argv)

    if args.subcmd == 'create':
        resource = create_new_resource(args)
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
        _update_with_parser(args)
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
    elif args.subcmd == 'rebuild-file-list':
        _build_file_list(args.repository, args.resource_name)

