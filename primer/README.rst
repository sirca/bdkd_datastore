Big Data Knowledge Discovery Data Portal Primer
-----------------------------------------------
The BDKD Data Portal Primer uses the meta-data information stored in the BDKD Datastore component
to populate a CKAN portal so that the data in the Datastore can be explore and discovered by
public users via a web portal.

Instructions
------------
Install the primer from source by checking out the code and type:

  python setup.py install

Alternatively you can create a source distribution using the command:

  `python setup.py sdist`

And copy the sdist file (should be in ./dist/bdkd-portal-primer-x.x.tar.gz) to your destination
and type:

  `pip install bdkd-portal-primer-x.x.tar.gz`

Once installed, you should be able to run the `portal_primer` command from the prompt.

Upload/store your data using the BDKD Datastore package into an object storage system
such as 'S3'. For example:

  `datastore-add bdkd-sirca-public 'Test Group/Test Data' tests/testdata/*`

Create a primer config file either in /etc/bdkd/primer.conf or anywhere that you have access to.
If you don't specify the configuration file when you perform priming, it will default to
/etc/bdkd/primer.conf.

The configuration file should contain the following entries:

    - bucket: bdkd-sirca-public
      org_name: sirca
      org_title: Sirca BDKD Group
      ckan_url: http://localhost
      ds_host: s3-ap-southeast-2.amazonaws.com

where
  "bucket" is the object storage (or S3 bucket name if you are in AWS).
  "org_name" is the unique organization name that data from this object storage will be owned by.
  "org_title" is the title of the organization if you use the primer to create/setup.
  "ckan_url" is the CKAN URL and is generally on the machine that the primer is executed.
  "ds_host" is the region where you will find the object storage (or S3 bucket)

Run the primer to prime a single bucket:

    `portal_primer -b bdkd-sirca-public prime`                 ### use /etc/bdkd/primer.conf
    `portal_primer -b bdkd-sirca-public -c primer.cfg prime`   ### use alt config

To prime all buckets configured, run it without the '-b' switch:

    `portal_primer prime`
