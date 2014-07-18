BDKD Datastore samples
======================

Sample scripts and utilities for BDKD Datastore are provided here.


datastore-add-tdrs
------------------

Add a GPlates time-dependent raster sequence to a Repository.

This utility is modeled after ``datastore-add``.  It takes the same parameters,
except that the one file argument is a GPML file.  This file is parsed for the
paths of a set of time-dependent rasters.  The GPML file and all raster files
are used as the files of the created Resource.

This script can be used with the `GPlates sample data 
<http://sourceforge.net/projects/gplates/files/gplates/1.3/gplates-1.3-sample-data.zip/download>`_.

The Agegrids time-dependent raster sequence in that set could be loaded as 
follows::

        datastore-add-tdrs 'my-repository' 'SampleData/Rasters/Time-dependent raster sequences/Agegrids' gplates/1.3/SampleData/Rasters/Time-dependent\ raster\ sequences/Agegrids/jpg/agegrid.gpml
