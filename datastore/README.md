# BDKD Datastore

Storage solution that manage large amount of data (file-like objects) in the form of datasets.

For example the BDKD project uses Amazon Web Services’ (AWS) Simple Storage Solution (S3) as its datastore solution.

Requires Python 2.7.

The latest release is 0.1.7.

Currently under passive development.


## About

BDKD Datastore is being developed by [SIRCA](http://www.sirca.org.au/) as part of the Big Data Knowledge Discovery (BDKD) project funded by [SIEF](http://www.sief.org.au).

## Install

Check out the BDKD Datastore source and install from source.

It is best done in a Python [virtualenv](https://virtualenv.pypa.io/en/latest/).


    git clone https://<username>@github.com/sirca/bdkd_datastore.git
    cd bdkd_datastore
    python setup.py develop

Note that you will have to ensure that Python 2.7 is used.
    

### Configuring
BDKD Datastore needs to be configured before it can be used.

Create the file `.bdkd_datastore.conf` in your home directory.

For example, if you use `vi`, you would type:

    vi ~/.bdkd_datastore.conf

A template of the contents of the file is as follows:
```yaml
settings:
    cache_root: /var/tmp/bdkd-data/cache
    working_root: /var/tmp/bdkd-data/working

hosts:
  s3-sydney:
    host: s3-ap-southeast-2.amazonaws.com
    access_key: xxx
    secret_key: xxx

repositories:
  my-repo1:
    host: s3-sydney
```

## Verify

To verify that BDKD Datastore is installed, try:

    datastore-utils --help
    
And you should see BDKD Datastore's help output.


## Further information

Full documentation is available in the [doc](doc/README.md) folder.


# Licensing
BDKD Datastore is available under the Apache License (2.0). See the LICENSE.md file.

Copyright NICTA 2015.

