Reference documentation
=======================

Command-line utilities
----------------------

.. _reference-datastore-add:

``datastore-add``
^^^^^^^^^^^^^^^^^

.. argparse::
  :module: bdkd.datastore.util.add
  :func: add_parser
  :prog: datastore-add



.. _reference-datastore-add-bdkd:

``datastore-add-bdkd``
^^^^^^^^^^^^^^^^^^^^^^

.. argparse::
  :module: bdkd.datastore.util.add
  :func: add_bdkd_parser
  :prog: datastore-add-bdkd



.. _reference-datastore-delete:

``datastore-delete``
^^^^^^^^^^^^^^^^^^^^

Delete a Resource from a Repository.

If the Resource has any Files stored in the same Repository, these will be 
deleted too.  (Remote HTTP or FTP Files are of course not deleted.)

Usage:
        ``datastore-delete 'repository' 'resource name'``

'repository'
        Name of a defined Repository

'resource name'
        Name of the Resource to delete



.. _reference-datastore-files:

``datastore-files``
^^^^^^^^^^^^^^^^^^^

Obtain a list of locally-cached filenames for the given Resource.

This utility will trigger a local cache refresh: the Refresh itself will be 
checked, along with each File associated with the Resource.  If the 
locally-cached file is out of date it will be downloaded.

Usage:
        ``datastore-files 'repository' 'resource name'``

'repository'
        Name of a defined Repository

'resource name'
        Name of the Resource for which a list of cached files is required



.. _reference-datastore-get:

``datastore-get``
^^^^^^^^^^^^^^^^^

Get details of a Resource as JSON text.

The meta-data and list of Files for a Resource will be printed to STDOUT as 
JSON text.

Usage:
        ``datastore-get 'repository' 'resource name'``

'repository'
        Name of a defined Repository

'resource name'
        Name of the Resource for which details are required



.. _reference-datastore-getkey:

``datastore-getkey``
^^^^^^^^^^^^^^^^^^^^

.. argparse::
  :module: bdkd.datastore.util.info
  :func: getkey_parser
  :prog: datastore-getkey



.. _reference-datastore-lastmod:

``datastore-lastmod``
^^^^^^^^^^^^^^^^^^^^^

.. argparse::
  :module: bdkd.datastore.util.info
  :func: lastmod_parser
  :prog: datastore-lastmod



.. _reference-datastore-list:

``datastore-list``
^^^^^^^^^^^^^^^^^^

Get a list of all Resources in a Repository (or optionally those Resources 
underneath a leading path).

Usage:
        ``datastore-list 'repository'``

'repository'
        Name of a defined Repository

Options:

``--path, -p``
        A leading path under which Resources will be found

``--verbose, -v``
        Show full details of each Resource as JSON text.  Default: no details, 
        just the name of each resource -- one per line.

.. _reference-datastore-repositories:

``datastore-repositories``
^^^^^^^^^^^^^^^^^^^^^^^^^^

Get a list of all configured Repositories.

Usage:
        ``datastore-repositories``



.. _reference-datastore-update-metadata:

``datastore-update-metadata``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. argparse::
  :module: bdkd.datastore.util.metadata
  :func: update_metadata_bdkd_parser
  :prog: datastore-update-metadata



Python API
----------

.. automodule:: bdkd.datastore.datastore
   :members:
   :undoc-members:
   :show-inheritance:
