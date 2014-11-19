import pytest
from bdkd import datastore as ds
from subprocess import call
import ckan.logic

def get_dataset_from_ckan(ckan_site, dataset_id):
    # Common function to allow tests to get a CKAN dataset and
    # if the dataset cannot be found, do an assert instead of
    # an exception does not really tell what the failure was.
    try:
        ds = ckan_site.action.package_show(id=dataset_id)
        return ds

    except ckan.logic.NotFound:
        assert False, "Unable to find test dataset {0} in the CKAN portal".format(dataset_id)


def get_resource_from_ckan(ckan_site, dataset_id, resource_name):
    ds = get_dataset_from_ckan(ckan_site, dataset_id)
    rss = filter(lambda x: x.get('name')==resource_name, ds['resources'])
    assert len(rss) > 0, "Unable to find resource {0} in the dataset {1}".format(resource_name, dataset_id)
    return rss[0]


def test_add_dataset(portal_builder, ckan_site, sample_data1):
    sample_data1.prepare() # make sure dataset1 is there
    portal_builder.run_update() # Build portal
    ds = get_dataset_from_ckan(ckan_site, sample_data1.get_dataset_id())
    assert ds['author'] == 'test author'
    assert ds['author_email'] == 'test@test.email'
    assert ds['maintainer'] == 'test maintain'
    assert ds['maintainer_email'] == 'testmain@test.email'
    assert ds['notes'] == 'laser in ocean'
    assert ds['num_resources'] == 3 # download, manifest, metadata
    assert ds['organization']['title'] == 'BDKD QA System'
    assert ds['organization']['name'] == 'bdkd-qa-org'
    for rs_name in ['download','manifest']:
        assert any(rs.get('name') == rs_name for rs in ds['resources']), "Missing {0} resource".format(rs_name)


def test_update_dataset_metadata(portal_builder, ckan_site, sample_data1):
    sample_data1.prepare() # make sure dataset1 is there
    portal_builder.run_update() # Build portal

    # Verify the dataset appears in the portal
    ds = get_dataset_from_ckan(ckan_site, dataset_id=sample_data1.get_dataset_id())
    assert ds['notes'] == 'laser in ocean'

    # Now update the notes of the dataset in datastore
    rs = sample_data1.get_ds_resource()
    rs.set_edit()
    rs.metadata['description'] = 'laser on trees'
    rs.save()

    portal_builder.run_update() # Update the portal and requery from portal
    ds = get_dataset_from_ckan(ckan_site, dataset_id=sample_data1.get_dataset_id())
    assert ds['notes'] == 'laser on trees'


# def test_update_dataset_add_file(portal_builder, ckan_site, sample_data1):
# Can't do this test yet because datastore library does not directly support that.

def test_purge_and_reprime_dataset(portal_builder, ckan_site, sample_data1, sample_data2):
    # make sure the datasets are there in datastore
    sample_data1.prepare()
    sample_data2.prepare()
    portal_builder.run_update()
    # double check that the datasets were explorable in the portal
    dss = ckan_site.action.package_list()
    assert sample_data1.get_dataset_id() in dss, "Failed to see sample data 1"
    assert sample_data2.get_dataset_id() in dss, "Failed to see sample data 2"
    # now run the purge command
    portal_builder.run(cmd='purge')
    # check that the datasets are no longer there after purge
    dss = ckan_site.action.package_list()
    assert len(dss) == 0, "no dataset should be there after purge"
    portal_builder.run(cmd='reprime')
    dss = ckan_site.action.package_list()
    assert len(dss) == 2, "dataset should have been rebuilt after the reprime"


def test_search_dataset(portal_builder, ckan_site, sample_data1, sample_data2):
    # make sure the datasets are there in datastore
    sample_data1.prepare()
    sample_data2.prepare()
    portal_builder.run_update()

    # double check that the datasets were explorable in the portal
    dss = ckan_site.action.package_list()
    assert sample_data1.get_dataset_id() in dss, "Failed to see sample data 1"
    assert sample_data2.get_dataset_id() in dss, "Failed to see sample data 2"

    # now check that datasets can be discovered via the portal
    laser_results = ckan_site.action.package_search(q='laser')
    assert laser_results['count'] == 2, "should have found 2 laser datasets"
    assert any(ds.get('name') == sample_data1.get_dataset_id() for ds in laser_results['results']), 'dataset #1 not discovered'
    assert any(ds.get('name') == sample_data2.get_dataset_id() for ds in laser_results['results']), 'dataset #2 not discovered'

    # if we search for 'space', we should only find dataset #2
    laser_results = ckan_site.action.package_search(q='space')
    assert laser_results['count'] == 1, "should have found 1 space dataset"
    assert any(ds.get('name') == sample_data2.get_dataset_id() for ds in laser_results['results']), 'dataset #2 not discovered'


def test_del_dataset(portal_builder, ckan_site, sample_data1):
    sample_data1.prepare() # make sure dataset1 is there
    portal_builder.run_update() # Build portal
    dss = ckan_site.action.package_list()
    assert sample_data1.get_dataset_id() in dss, "Sample data should have been in CKAN after build"

    # Now delete the dataset from datastore, rebuild, and check in portal.
    sample_data1.delete_dataset()
    portal_builder.run_update()
    dss = ckan_site.action.package_list()
    assert not sample_data1.get_dataset_id() in dss, "Sample data should have been remove from CKAN after build"


def test_visualization(portal_builder, ckan_site, visual_data1):
    visual_data1.prepare()
    portal_builder.run_update()

    # Verify the dataset appears in the portal
    visual_resource = get_resource_from_ckan(ckan_site, dataset_id=visual_data1.get_dataset_id(), resource_name='explore')
    assert visual_resource.get('url') == 'http://localhost/visual?repo={0}&dataset={1}'.format(
        visual_data1.get_repo_name(),
        visual_data1.get_dataset_name())


def test_download(portal_builder, ckan_site, sample_data1):
    sample_data1.prepare()
    portal_builder.run_update()
    download_rs = get_resource_from_ckan(ckan_site, sample_data1.get_dataset_id(), "download")
    # Maybe parse the download.html to locate the URL link so that we can attempt to download the resource
    # and check it against the original file.


def test_manifest(portal_builder, ckan_site, sample_data1):
    sample_data1.prepare()
    portal_builder.run_update()
    manifest_rs = get_resource_from_ckan(ckan_site, sample_data1.get_dataset_id(), "manifest")
    manifest_url = manifest_rs['url']
    import requests
    rsp = requests.get(manifest_url)
    assert rsp.status_code == 200, "Unable to download manifest file"
    manifest = rsp.content.split('\n')
    assert manifest[0], 's3://bdkd-qa-bucket/files/visual_dataset1/sample001.csv'
    assert manifest[1], 's3://bdkd-qa-bucket/files/visual_dataset1/sample002.txt'


def test_auto_build(portal_builder, ckan_site, short_sample_data):
    # Test that when running in daemon mode, CKAN is updated without manual trigger.
    assert portal_builder.daemon_running() == None, "portal builder should not be running"
    portal_builder.start_daemon()
    assert portal_builder.daemon_running() != None, "portal builder should now be running"

    # Have the sample data ready in datastore
    short_sample_data.prepare()
    # add an extra 5 seconds buffer
    builder_nap = portal_builder.get_portal_config()['cycle_nap_in_mins'] * 60 + 5
    import time
    tm_start = time.time()
    while not short_sample_data.get_dataset_id() in ckan_site.action.package_list():
        assert (time.time() - tm_start) <= builder_nap, "dataset {0} still not found after waiting for {1} seconds".format(
            short_sample_data.get_dataset_id(),
            builder_nap)
        time.sleep(5)

    portal_builder.stop_daemon()
    assert portal_builder.daemon_running() == None, "portal builder should no longer be running"
