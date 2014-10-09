BDKD Portal Integration Tests
-----------------------------

The portal integration tests carries out end to end tests using:
- datastore library and utilities
- datastore
- CKAN portal
- CKAN search via solr

The integration tests requires the following python packages to be installed:
- pytest
- requests
- psutil

To run the integration test, from the ./bdkd/portal/tests/inttests directory
(which should be the current directory), type: `pytest`

Make sure your instance have access to AWS S3. The bucket that the tests uses
is called "bdkd-qa-bucket". This bucket is configured in the /etc/bdkd/Current/datastore.conf
and /etc/bdkd/portal/builder.cfg files

Note that the test bucket can be heavily written and modified, so don't use
production buckets for testing.
