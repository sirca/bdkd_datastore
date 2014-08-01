Big Data Knowledge Discovery Data Portal Primer
-----------------------------------------------


Testing
-------
Install the BDKD datastore package.

Add a test dataset to a test bucket using the datastore util:

  `datastore-add bdkd-sirca-public 'Test Group/Test Data' tests/testdata/*`

Make sure your bucket is configured in the primer config file:

    - bucket: bdkd-sirca-public
      org_name: sirca
      org_title: Sirca BDKD Group
      ckan_url: http://localhost
      ds_host: s3-ap-southeast-2.amazonaws.com

Run the primer:

    `portal_primer -b bdkd-sirca-public -c primer.cfg prime`
