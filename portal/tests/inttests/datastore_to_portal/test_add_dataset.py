import pytest
from bdkd import datastore as ds
from subprocess import call
import ckan.logic

def test_add_dataset(portal_builder, ckan_site, sample_data1):
    sample_data1.prepare() # make sure dataset1 is there
    portal_builder.run_update() # Build portal

    # Verify the dataset appears in the portal
    try:
        ds = ckan_site.action.package_show(id=sample_data1.get_dataset_id())
        assert ds['author'] == 'test author'
        # FIXME - email not set. assert ds['author_email'] == 'test@test.email'
        assert ds['notes'] == 'laser in ocean'
        assert ds['num_resources'] == 2
        assert ds['organization']['title'] == 'BDKD QA System'
        assert ds['organization']['name'] == 'bdkd-qa-org'
        assert any(rs.get('name') == 'download' for rs in ds['resources']), "Missing download resource"
        for rs_name in ['download','manifest']:
            assert any(rs.get('name') == rs_name for rs in ds['resources']), "Missing {0} resource".format(rs_name)

    except ckan.logic.NotFound:
        assert False, "Unable to find sample data in CKAN portal after data build"


def test_update_dataset_metadata(portal_builder, ckan_site, sample_data1):
    sample_data1.prepare() # make sure dataset1 is there
    portal_builder.run_update() # Build portal

    # Verify the dataset appears in the portal
    ds = ckan_site.action.package_show(id=sample_data1.get_dataset_id())
    assert ds['notes'] == 'laser in ocean'

    # Now update the notes of the dataset in datastore
    rs = sample_data1.get_ds_resource()
    rs.set_edit()
    rs.metadata['description'] = 'laser on trees'
    rs.save()

    portal_builder.run_update() # Update the portal and requery from portal
    ds = ckan_site.action.package_show(id=sample_data1.get_dataset_id())
    assert ds['notes'] == 'laser on trees'


# def test_update_dataset_add_file(portal_builder, ckan_site, sample_data1):
# Can't do this test yet because datastore library does not directly support that.


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


def test_auto_build():
    # TODO
    pass


def test_visualization():
    # TODO
    pass


def test_download():
    # TODO
    pass


def test_manifest():
    # TODO
    pass
