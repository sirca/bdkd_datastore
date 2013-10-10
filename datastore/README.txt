BDKD DATASTORE
==============

The BDKD Datastore provides for the storage of file-like objects to a 
S3-compatible repository (Amazon or OpenStack Swift) including local caching.


Configuration
-------------

Configuration is searched in the following locations:

 - /etc/bdkd/datastore.conf (global configuration)
 - ~/.bdkd_datastore.conf (user configuration)

The user configuration location can be overridden via the environment variable 
"BDKD_DATASTORE_CONFIG".  This may point to a readable configuration file.

The configuration files should be YAML.  They should contain the following 
variables:

- "settings": various settings that affect the way the datastore works.  The 
  following variables under settings are recognised:
	- "cache_root": Path to a directory where all cache files will be 
	  stored
	- "working_root": Path to a directory where working files will be 
	  stored for Resources that are currently being edited
- "hosts": recognised S3 hosts.
	- (name): Each entry under "hosts" is the name of a S3 host.  The 
	  following options are supported:
		- "host": hostname (required)
		- "port": (optional: port 80)
		- "secure": use HTTPS (optional: True)
		- "access_key": S3 access key
		- "secret_key": S3 secret key
- "repositories": S3 buckets for containing documents.
	- (name): Each entry under "repositories" is the name of a repository.  
	  The following options are supported:
		- "cache_path": where to store cached documents (default: 
		  settings.cache_root, above)
		- "host": The host of the bucket, as defined above 

Settings in the user configuration take precedence over those in the global 
configuration.  Therefore if settings are defined globally that do not need to 
be changed, they can be omitted from the user configuration.  For example you 
may define the "cache_root" and "working_root" at a global level along with 
some standard read-only repositories, and at the user level only define 
repositories that are specific to that user.

For example a configuration file may be similar to the following:

	settings:
	    cache_root: /var/tmp/cache/bdkd
	    working_root: /var/tmp/working
	hosts:
	    s3-sydney-2:
		host: s3-ap-southeast-2.amazonaws.com
		access_key: MyAccessKey123
		secret_key: MySecretKey123
	repositories:
	    bdkd-gplates:
		host: s3-sydney-2


Usage
-----

If BDKD Datastore is in the Python path it can be imported like so:

	import bdkd.datastore

For examples of usage see the unit tests.


Testing
-------

It is assumed that you have a test runner such as Nose 
<https://pypi.python.org/pypi/nose> installed.

The unit tests assume no services external to the host are available.  Run the 
unit tests as follows:

	nosetests -w tests/unit/

Integration tests may make use of external services (e.g. S3 connection).  Run 
the integration tests as follows:

	nosetests -w tests/integration/
