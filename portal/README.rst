Big Data Knowledge Discovery Portal Data Builder
-----------------------------------------------
The BDKD Portal Data Builder uses the meta-data information stored in the BDKD Datastore component
to populate a CKAN portal so that the data in the Datastore can be explore and discovered by
public users via a web portal.

Instructions
------------
Install the portal-data-builder from source by checking out the code and type:

`python setup.py install`

Alternatively you can create a source distribution using the command:

`python setup.py sdist`

And copy the sdist file (should be in ./dist/bdkd-portal-data-builder.x.tar.gz) to your destination
and type:

`pip install bdkd-portal-data-builder.x.tar.gz`

Once installed, you should be able to run the `portal-data-builder` command from the prompt.

Upload/store your data using the BDKD Datastore package into an object storage system
such as 'S3'. For example:

`datastore-add-bdkd --force --description "This is some sample data" --author "My Name" --author-email "myemail@domain.something" --data-type "geo data" bdkd-sirca-public 'MyDataSet' ./myfiles/*`

Create a primer config file either in /etc/bdkd/portal.cfg or anywhere that you have access to.
If you don't specify the configuration file when you perform portal data building, it will default to
/etc/bdkd/portal.cfg.
You can find a sample config file in data/portal.cfg

The configuration file should contain the following entries:

`
api_key: xxx-xxx                                  ## the CKAN API key to use when building
ckan_cfg: /etc/ckan/default/production.ini        ## the CKAN ini file
ckan_url: http://localhost                        ## the CKAN API URL (usually localhost)
cycle_nap_in_mins: 1                              ## how long to nap before scanning again (in daemon mode)
download_template: /etc/bdkd/portal/download.html ## template for the download page 
build_lock_file: /tmp/portal_building             ## the lock file to use when managing exclusive usage
visual-sites:                                     ## a list of websites that can help visualize the data
    - data_type: xxxx                             ## the type of dataset that the website knows how to visualize
      url: http://xxx.xxx.xxx{repository_name}/datasets/{resource_name} ## the format of the URL when creating a HTTP link

repos:                                            ## a list of repositories to build portal data from.
    - bucket: bdkd-sirca-public
      org_name: sirca
      org_title: Sirca BDKD Group
      ds_host: s3-ap-southeast-2.amazonaws.com
      download_url_format: https://{datastore_host}/{repository_name}/{resource_id}
`
where
  "bucket" is the object storage (or S3 bucket name if you are in AWS).
  "org_name" is the unique organization name that data from this object storage will be owned by.
  "org_title" is the title of the organization if you use the primer to create/setup.
  "ds_host" is the region where you will find the object storage (or S3 bucket)
  "download_url_format" is the format of the download link when constructing a HTTP link to download a file

To manually update the portal data for all configured repositories:

`portal-data-builder update`

To update a single repository, use the '-b' switch:

`portal-data-builder -b bdkd-sirca-public update`                ### use /etc/bdkd/primer.cfg
`portal-data-builder -b bdkd-sirca-public -c portal.cfg update`  ### use alternate configuration


To run the portal in a daemonized mode:

`portal-data-builder daemon`
