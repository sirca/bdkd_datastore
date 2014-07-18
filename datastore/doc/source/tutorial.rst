Using BDKD Datastore
====================

This page describes how BDKD Datastore would be used by an end-user to access 
and modify information in Repositories.  This would be done either from a 
Python script or interactive console session, or the user might utilise the 
provided command-line tools.

Session
-------

In either a Python script/program or an interactive Python console, the 
:mod:`bdkd.datastore` module can be accessed by importing it.

::

        import bdkd.datastore


Repositories and Resources
--------------------------

Repositories can be accessed by name using :meth:`bdkd.datastore.repository`, 
e.g.::

        repository = bdkd.datastore.repository("bdkd-datastore-test")

Resources in a Repository can be listed using 
:meth:`bdkd.datastore.Repository.list`, optionally by a leading pseudopath::

        # All resource names:
        resource_names = repository.list()

        # Resource names in a pseudopath:
        resource_names = repository.list('FeatureCollections/')

This could be used to iterate over some Resources::

        for resource_name in repository.list('FeatureCollections/'):
            resource = repository.get(resource_name)
            # Do something with resource here...


Command-line
^^^^^^^^^^^^

A list of available Repositories can be obtained from the command line using 
:ref:`reference-datastore-repositories`.

``datastore-repositories``

This will list the names of all configured Repositories to STDOUT -- one per 
line.

The Resources provided by a repository can be listed using 
:ref:`reference-datastore-list`, for example:

``datastore-list 'bdkd-datastore-test'``


Resource details
----------------

The name of a Resource can be accessed via :attr:`bdkd.datastore.Resource.name` 
and its meta-data via the dictionary :attr:`bdkd.datastore.Resource.metadata`.  
The ResourceFile instances contained in the Resource can be accessed via 
:attr:`bdkd.datastore.Resource.files`.

Local cache files for a Resource can be accessed in two ways:

1. Either individually for each ResourceFile via 
   :meth:`bdkd.datastore.ResourceFile.local_path`.  This will trigger a local 
   cache refresh for the specific ResourceFile only.
2. For all ResourceFiles owned by the Resource via 
   :meth:`bdkd.datastore.Resource.local_paths`.  This will trigger local cache 
   refreshes for the Resource and all its files.

Consider the similarity between these operations::

        resource = repository.get('FeatureCollections/Coastlines/Seton')

        # This will refresh all the Resource's cached files and return their paths
        paths = resource.local_paths()

        # This will do the same, one at a time:
        paths = []
        for resource_file in resource.files:
            paths.append(resource_file.local_path())

The question may be asked: why use one approach rather than the other?

* If a Resource consists of many files that may be large (e.g. a time-dependent 
  raster sequence composed of hundreds of images), it would be inefficient to 
  get the local paths of all the Resource's files if only one is required.  In 
  that case, the best approach would be to find the ResourceFile of interest 
  and call :meth:`bdkd.datastore.ResourceFile.local_path` for that ResourceFile 
  alone.
* However if a Resource consists of a set of files that need to be taken 
  together (e.g. an ESRI shapefile) then it may be best to use 
  :meth:`bdkd.datastore.Resource.local_paths`.


Command-line
^^^^^^^^^^^^

Details on a Resource can be obtained from the command-line as JSON text using 
:ref:`reference-datastore-get`, for example:

``datastore-get 'bdkd-datastore-test' 'FeatureCollections/Coastlines/Seton'``

To get a list of all the local cache files for a Resource, use 
:ref:`reference-datastore-files`, for example:

``datastore-files 'bdkd-datastore-test' 'FeatureCollections/Coastlines/Seton'``


Creating and editing Resources
------------------------------

There is a helper method ``Resource.new`` to create Resources.  At the point of 
creation, a Resource exists only in memory.  To be made persistent it needs to 
be added to a Repository.  This is an example of creating a Resource from a 
local file::

        # Create a new, unsaved Resource
        resource = bdkd.datastore.Resource.new('FeatureCollections/Coastlines/Seton',
                'path/to/FeatureCollections/Coastlines/Seton_etal_ESR2012_Coastlines_2012.1.gpmlz')
        # Save the Resource to a Repository
        repository.save(resource)

Creating Resources with remote Files (i.e. some external HTTP or FTP file) is 
almost the same: simply provide the URL instead of a local file path::

        resource = bdkd.datastore.Resource.new('Caltech/Continuously Closing Plate Polygons',
                'http://www.gps.caltech.edu/~gurnis/GPlates/Caltech_Global_20101129.tar.gz')
        repository.save(resource)


Command-line
^^^^^^^^^^^^

Resources can be created from the command-line using 
:ref:`reference-datastore-add`, for example:

``datastore-add 'bdkd-datastore-test' 'SampleData/FeatureCollections/Isochrons/Seton_etal_ESR2012_Isochrons_2012.1' ~/path/to/SampleData/FeatureCollections/Isochrons/Seton_etal_ESR2012_Isochrons_2012.1.gpmlz``


Deleting Resources
------------------

Resources can be deleted using :meth:`bdkd.datastore.Repository.delete`.  A 
Resource can be deleted from a Repository directly, for example::

        resource = repository.get('FeatureCollections/Coastlines/Seton')
        repository.delete(resource)

Or it can be deleted by name.  This operation is the same as the above::

        repository.delete('FeatureCollections/Coastlines/Seton')

The difference is that in the second case we assume that the name identifies a 
Resource that exists in the Repository.

When a Resource is deleted, so are any files belonging to that Resource that 
are stored in the same Repository.  However if any ResourceFiles refer to 
remote resources (HTTP or FTP URLs from elsewhere on the Internet) naturally no 
attempt will be made to remove those.


Command-line
^^^^^^^^^^^^

Resources can be deleted from the command-line using 
:ref:`reference-datastore-delete`, for example:

``datastore-delete 'bdkd-datastore-test' 'SampleData/FeatureCollections/Isochrons/Seton_etal_ESR2012_Isochrons_2012.1'``


Further information
-------------------

The :doc:`reference` page contains full details on the Python API and 
command-line tools.  The source code of the command-line tools themselves, 
being written in Python using the ``bdkd.datastore`` library, could also be 
illustrative of how the library can be used in a script.  The unit and 
integration tests provided with the source distribution could also demonstrate 
how all the facilities of the library can be invoked.
