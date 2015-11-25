# BDKD Portal

BDKD Portal uses the [Open Source CKAN Portal](http://ckan.org/) which provides the ability to search, explore and download datasets.


# BDKD Portal Data Builder

Python Application that extracts metadata from [BDKD-datastore](../datastore/README.md) and populates the BDKD portal.

It assumes that the [BDKD-datastore](../../datastore/README.md) package is installed and available.

Requires Python 2.7.

The latest release is 0.1.7.

Currently under maintenance.


## About

BDKD Portal Data Builder has been developed by [SIRCA](http://www.sirca.org.au/) as part of the Big Data Knowledge Discovery (BDKD) project funded by [SIEF](http://www.sief.org.au).

## Install

Check out the BDKD Portal Data Builder source and install from source.

It is best done in a Python [virtualenv](https://virtualenv.pypa.io/en/latest/).


    git clone https://<username>@github.com/sirca/bdkd_datastore.git
    cd portal
    python setup.py install

Note that you will have to ensure that Python 2.7 is used.

## Verify

To verify that BDKD Portal Data Builder is installed, try:

    portal-data-builder --help
    
And you should see BDKD Portal Data Builder's help output.

## Configuring
BDKD Portal Data Builder needs to be configured before it can be used.

Create a primer config file either in /etc/bdkd/portal.cfg or anywhere that you have access to. 
If you don't specify the configuration file when you perform portal data building, it will default to /etc/bdkd/portal.cfg. 
You can find a sample config file in data/portal.cfg

Create the file `/etc/bdkd/portal.cfg` in your home directory.

For example, if you use `vi`, you would type:

    vi /etc/bdkd/portal.cfg

A template of the contents of the file is as follows:

```yaml
api_key: 11111111-2222-3333-4444-555555555555                        # CKAN API key to use when building
ckan_cfg: /etc/ckan/default/production.ini                           # CKAN ini file
ckan_url: http://localhost                                           # CKAN API URL (usually localhost)
cycle_nap_in_mins: 60                                                # How long to nap before scanning again (in daemon mode)
download_template: /etc/bdkd/portal/download.html                    # Template for the download page
bundled_download_template: /etc/bdkd/portal/download_bundled.html    # Template for the download bundle page
build_lock_file: /tmp/portal_building                                # Lock file to use when managing exclusive usage

repos:                                                               # List of repositories to build portal data from
    - bucket: bdkd-sirca-public                                      # Object storage (or S3 bucket name if you are in AWS)
      org_name: sirca                                                # Unique organization name that data from this object storage will be owned by
      org_title: Sirca BDKD Group                                    # Title of the organization if you use the primer to create/setup
      ds_host: s3-ap-southeast-2.amazonaws.com                       # Region where you will find the object storage (or S3 bucket) 
      download_url_format: https://{datastore_host}/{repository_name}/{resource_id} # Format of the download link

visual-sites:                                                        # List of websites that can help visualize the data
    - data_type: sirca data                                          # Type of dataset that the website knows how to visualize
      url: http://ec2-11-22-333-44.ap-southeast-2.compute.amazonaws.com/repositories/{repository_name}/datasets/{resource_name}   # URL format when creating HTTP link
```

## Running Manually

Manually update the portal data for all configured repositories
```
portal-data-builder update
```

Update a single repository, use the '-b' switch
```
portal-data-builder -b bdkd-sirca-public update
```

Using an alternative configuration file
```
portal-data-builder -b bdkd-sirca-public -c portal.cfg update
```

## Running as a Daemon
```
portal-data-builder daemon
```


## Further information

Full documentation is available in the [doc](doc/README.md) folder.

# Licensing
BDKD Datastore is available under the Apache License (2.0). See the [LICENSE.md](../LICENSE.md) file.

Copyright NICTA 2015.
