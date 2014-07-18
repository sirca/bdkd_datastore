.. BDKD Datastore documentation master file, created by
   sphinx-quickstart on Thu Oct 17 09:56:45 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to BDKD Datastore's documentation!
==========================================

BDKD Datastore is a system for storing and accessing file-like data in a cloud 
environment.  Files are stored in Repositories, grouped together as Resources.  
A Resource and its Files may have meta-data: key/value pairs.

Usage of BDKD is oriented around local caching of Resources.  A program 
acquires the Resources it needs and BDKD Datastore ensures that a reasonably 
up-to-date local cache of that Resource and its Files is maintained.  This 
allows one definitive version of a Resource to be kept (in the Repository) 
while possibly mutiple users can access the Resource from various hosts in the 
cloud.

Full functionality of the BDKD Datastore is exposed via a Python library.  
There is also a set of command-line tools that can be used to manipulate 
Resources easily.

Contents:

.. toctree::
   :maxdepth: 2

   intro
   tutorial
   reference


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

