Reference documentation
=======================

Command-line utilities
----------------------

.. _reference-datastore-add:

``datastore-add``
^^^^^^^^^^^^^^^^^

Add a Resource to a Repository, optionally overwriting any other Resource of 
the same name.

Usage:
        ``datastore-add [options] 'repository' 'resource name' file...``

'repository'
        Name of a defined Repository

'resource name'
        Name of the Resource to create (or overwrite: see --force below)

file...
        One or more local file paths or URLs of remote files (HTTP, FTP)
       
Options:

``--metadata, -m``
        A JSON string containing meta-data for the Resource
        
``--force, -f``
        If a Resource of the given name already exists in the Repository, 
        overwrite it.  Default: do not overwrite (returns an error)

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


Python API
----------

.. automodule:: bdkd.datastore
   :members:
   :show-inheritance:
