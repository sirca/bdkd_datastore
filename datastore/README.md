BDKD DATASTORE
==============

The BDKD Datastore provides for the storage of file-like objects to a 
S3-compatible repository (Amazon or OpenStack Swift) including local caching.


Dependencies
------------

 * python-nose
 * python-sphinx


Testing
-------

The unit tests assume no services external to the host are available.  Run the 
unit tests as follows:

	nosetests -w tests/unit/

Integration tests may make use of external services (e.g. S3 connection).  Run 
the integration tests as follows:

	nosetests -w tests/integration/


Installation
------------

1. Build the documentation

	pushd doc/
	make html
	popd

2. Prepare the files for RPM packaging

	package/prepare.sh

3. Build a RPM

	rpmbuild -bb ~/rpmbuild/SPECS/bdkd-datastore.spec

Then as root install the RPM.


Further information
-------------------

Full documentation is available in HTML format in /usr/share/doc after
installation.
