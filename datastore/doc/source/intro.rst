Introduction
============

Introduction to BDKD Datastore.


Installation
------------

Installation is via RPM.


Configuration
-------------

BDKD configuration is provided via YAML files that define the settings, hosts 
and repositories for BDKD on the current host.

There are two sources of configuration for BDKD datastore:

1. System-wide configuration in ``/etc/bdkd/datastore.conf``
2. User-specific configuration in ``~/.bdkd_datastore.conf``

Any variables in the user-specific configuration take precedence over the 
system-wide ones.

The location of the user-specific configuration can be overridden by setting 
the environment variable ``BDKD_DATASTORE_CONFIG``.  This should be the path to 
a readable YAML file.

The configuration file has the following sections:

**settings**
        Various settings that affect the way the datastore works.  The 
        following variables under settings are recognised:

        **cache_root**
                Path to a directory where all cache files will be stored
        **working_root**
                Path to a directory where working files will be stored for 
                Resources that are currently being edited

**hosts**
        Recognised S3 hosts.

        *(name)*
                Each entry under "hosts" is the name of a S3 host.  The 
                following options are supported:
		
                **host**
                        hostname (required)
                **port**
                        (optional: port 80)
                **secure**
                        use HTTPS (optional: True)
                **access_key**
                        S3 access key
                **secret_key**
                        S3 secret key

**repositories**
        S3 buckets for containing documents.
	
        *(name)*
                Each entry under "repositories" is the name of a repository.  
                The following options are supported:

                **cache_path**
                        where to store cached documents (default: 
                        settings.cache_root, above)
                **host**
                        The host of the bucket, as defined above 


Configuration example
^^^^^^^^^^^^^^^^^^^^^

Typically the system-wide configuration in ``/etc/bdkd/datastore.conf`` might 
define the cache root, working root, and any standard repositories.

::

        settings:
            cache_root: /var/tmp/bdkd/cache
            working_root: /var/tmp/bdkd/working

        hosts:
            s3-sydney-readonly:
                host: s3-ap-southeast-2.amazonaws.com
                access_key: XXXXXXXXXXXXXXXXXXXX
                secret_key: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

        repositories:
            bdkd-gplates:
                host: s3-sydney-readonly

A user may define settings specific to himself or herself in 
``~/.bdkd_datastore.conf``.  For example the user may define hosts with 
different credentials to the standard ones.

::

        hosts:
            s3-sydney-readwrite:
                host: s3-ap-southeast-2.amazonaws.com
                access_key: yyyyyyyyyyyyyyyyyyyy
                secret_key: yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy

        repositories:
            bdkd-gplates:
                host: s3-sydney-readwrite
            result-data:
                host: s3-sydney-readwrite

In this case the default repository "bdkd-gplates" has been redefined with 
different host credentials, and an additional repository "result-data" has been 
added.

