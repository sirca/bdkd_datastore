import pytest
from mock import Mock, patch, MagicMock, call, ANY
from bdkdportal.databuild import PortalBuilder
from bdkdportal.databuild import RepositoryBuilder
import yaml
import datetime


def check_calls_with(call_mock, param, value):
    """ Given a mocked object, check if it was called with a given parameter and/or value.
    :param call_mock: the mock object to check
    :type  call_mock: mock.call
    :param param    : check if it was called with this given 'param'
    :type  param    : string
    :param value    : check if it was called with this given value for the 'param'
                      If the value is not important, call this with mock.ANY
    """
    for cm in call_mock.call_args_list:
        if param in cm[1]:
            if cm[1][param] == value:
                return True
    return False


class PortalResourceMocker:
    """ For patching all external resources used by a PortalBuilder object.
    The PortalBuilder is a busy class that interactives with lots of
    external resources such as CKAN, BDKD datastore, local files and jinja2
    engine. As the tests require lots of repetitive mocking of the same
    resources, this class is created to help reduce the amount of duplicated
    code required for mocking the portal resources.

    """
    def __init__(self):
        self._patches = {}

    # A list of all the modules that can be patched.
    PatchList = [
        'ckan.lib.cli.DatasetCmd',
        'jinja2.FileSystemLoader',
        'jinja2.Environment',
        'jinja2.PackageLoader',
        'ckanapi.RemoteCKAN',
        'bdkd.datastore.Repository',
        'bdkd.datastore.Host',
        'bdkdportal.databuild.prepare_lock_file',
        'bdkdportal.databuild.purge_ckan_dataset',
        'logging.getLogger',
        'os.path.exists',
        '__builtin__.open',
    ]

    def start_patching(self, exclude_modules=None):
        self._patches = {}
        for mod in PortalResourceMocker.PatchList:
            if exclude_modules and mod in exclude_modules:
                continue
            p = patch(mod)
            m = p.start()
            self._patches[mod] = { 'patch':p, 'mock':m }

    def get_patch(self, patch_name):
        patch_data = self._patches.get(patch_name)
        if patch_data:
            return patch_data['patch']
        return None

    def get_mock(self, patch_name):
        patch_data = self._patches.get(patch_name)
        if patch_data:
            return patch_data['mock']
        return None

    def stop_patching(self):
        for mod in self._patches:
            self._patches[mod]['patch'].stop()


@pytest.fixture
def mocked_resources():
    return PortalResourceMocker()


@pytest.fixture
def good_cfg_string():
    """ Provides a good configuration string.
    Keep updating this string as more config is added.
    """
    return """
api_key: test-key
ckan_cfg: test_ckan_cfg_file
ckan_url: test_ckan_url
download_template: test_template
repos:
    - bucket: test_bucket
      org_name: test_org_name
      org_title: test_org_title
      ds_host: test_ds_host
      download_url_format: https://{datastore_host}/{repository_name}/{resource_id}
visual-sites:
    - data_type: ocean data
      url: http://ocean.site/{repository_name}/{resource_name}
    - data_type: rotation model
      url: http://gplate.site/repo={repository_name}&ds={resource_name}
           """


@pytest.fixture
def good_portal_cfg(good_cfg_string):
    cfg = yaml.load(good_cfg_string)
    return cfg


@pytest.fixture
def good_portal_builder(good_cfg_string):
    # Provide a portal builder that has a good configuration.
    builder = PortalBuilder(logger=MagicMock())
    builder.load_config(from_string=good_cfg_string)
    return builder


def mock_getmeta(key, default=None):
    mock_meta = {
        'author':'test author',
        'author_email':'test_author@test.email',
        'maintainer':'test maintainer',
        'maintainer_email':'test_maintainer@test.email',
        'version':'1.0',
        'description':'test desc',
        'data_type':'ocean data',
        }

    return mock_meta.get(key, default)


@pytest.fixture
@patch('bdkd.datastore.Host')
def single_dataset_repo(mock_ds_host):
    """ Returns a mock datastore repository that gives the caller:
    - repository called 'test_bucket'
    - some meta data about the dataset, as per mock_metadata()
    - a single dataset in that repository called 'groupA/groupAA/dataset1'
    - the dataset has 2 resources:
      - a local file called 'groupA/groupAA/dataset1/files1'
      - a remote file called 'http://remotefile.internet/file2'
    """
    ds_resource_list = [ 'groupA/groupAA/dataset1' ]
    mock_ds_repo = MagicMock()
    mock_ds_repo.name = 'test_bucket'
    mock_ds_repo.host = mock_ds_host.return_value
    mock_ds_repo.list.return_value = ds_resource_list
    def mock_repo_get(ds_resource_name):
        if ds_resource_name == 'groupA/groupAA/dataset1':
            mock_ds_resource_file1 = MagicMock()
            mock_ds_resource_file1.location.return_value = 'groupA/groupAA/dataset1/file1'
            mock_ds_resource_file2 = MagicMock()
            mock_ds_resource_file2.location.return_value = None
            mock_ds_resource_file2.remote.return_value = 'http://remotefile.internet/file2'
            mock_ds_resource = MagicMock()
            mock_ds_resource.files = [mock_ds_resource_file1, mock_ds_resource_file2]
            mock_ds_resource.name = ds_resource_name
            mock_ds_resource.metadata.get = MagicMock(side_effect=mock_getmeta)
            return mock_ds_resource
        return None
    mock_ds_repo.get = MagicMock(side_effect=mock_repo_get)
    return mock_ds_repo


class TestPortalBuilder:

    @patch('os.path.exists', return_value=True)
    def test_load_config_ok(self, mock_os_path_exists, good_cfg_string):
        """ Test the loading of a good configuration file.
        """
        portal_builder_from_file = PortalBuilder(logger=MagicMock())
        cfg_from_yaml = yaml.load(good_cfg_string) # For intercepting the loading
        with patch('yaml.load') as mock_yaml_load:
            mock_yaml_load.return_value = cfg_from_yaml

            # Test that load_config will attempt to open up the file
            with patch('__builtin__.open') as mock_open:
                portal_builder_from_file.load_config(from_file='cfgfile_to_load')
                mock_open.assert_called_once_with('cfgfile_to_load')

        portal_builder_from_string = PortalBuilder(logger=MagicMock())
        portal_builder_from_string.load_config(from_string=good_cfg_string)

        # Check that loading config from string and from a file should produce the same config.
        for builder in [portal_builder_from_file, portal_builder_from_string]:
            # Check that the good settings made it to the builder's configuration.
            assert builder._cfg['api_key'] == 'test-key'
            assert builder._cfg['ckan_cfg'] == 'test_ckan_cfg_file'
            assert builder._cfg['ckan_url']=='test_ckan_url'
            assert len(builder._cfg['repos']) == 1
            repo_cfg = builder._cfg['repos'][0]
            assert repo_cfg["bucket"]=='test_bucket'
            assert repo_cfg["org_name"]=='test_org_name'
            assert repo_cfg["org_title"]=='test_org_title'
            assert repo_cfg["ds_host"]=='test_ds_host'


    def test_load_config_file_failures(self):
        """ Test when the builder throws if loading config file fails
        """
        builder = PortalBuilder(logger=MagicMock())
        # If config file is missing or not openable, it should raise an exception.
        with patch('os.path.exists', return_value=False):
            with pytest.raises(Exception):
                builder.load_config("missing_cfg")

        with patch('os.path.exists', return_value=True):
            with patch('__builtin__.open', return_value=None):
                with pytest.raises(Exception):
                    builder.load_config("open_fail_cfg")


    def test_nap_config(self, good_cfg_string):
        builder = PortalBuilder(logger=MagicMock())
        builder.load_config(from_string=good_cfg_string)
        # if not specifed, there will be a default (which is every hour)
        assert builder.get_nap_duration() == 3600
        cfg_with_nap = "cycle_nap_in_mins: 5" + good_cfg_string
        builder.load_config(from_string=cfg_with_nap)
        # if specified, it will be returned in seconds
        assert builder.get_nap_duration() == 300


    def test_data_build_with_bad_config(self, mocked_resources):
        """ Test that priming fails if config is bad.
        """
        # Config not loaded should fail
        mocked_resources.start_patching()
        with pytest.raises(Exception):
            builder = PortalBuilder(logger=MagicMock())
            builder.build_portal()

        # Missing key settings should fail
        with pytest.raises(Exception):
            builder = PortalBuilder(logger=MagicMock())
            builder.load_config(from_string="""
                repos:
                    - bucket: test_bucket
                      org_name: test_org_name
                      org_title: test_org_title
                      ckan_url: test_ckan_url
                      ds_host: test_ds_host
                """)
            builder.build_portal()

        # Missing repo key settings should fail too
        with pytest.raises(Exception):
            builder = PortalBuilder(logger=MagicMock())
            builder.load_config(from_string="""
                    api_key: test-key
                    ckan_cfg: test_ckan_cfg_file
                    ckan_url: test_ckan_url
                    download_template: test_template
                    repos:
                        - bucket: test_bucket
                          org_title: test_org_title
                          ds_host: test_ds_host
                          download_url_format: https://{datastore_host}/{repository_name}/{resource_id}
                    """)
            builder.build_portal()

        with pytest.raises(Exception):
            builder = PortalBuilder(logger=MagicMock())
            builder.load_config(from_string="""
                api_key: test-key
                """)
            builder.build_portal()

        with pytest.raises(Exception):
            builder = PortalBuilder(logger=MagicMock())
            builder.load_config() # Need to specify where to load the config from

        mocked_resources.stop_patching()


    def test_find_visual_site(self, good_portal_builder):
        assert (good_portal_builder.find_visual_site_for_datatype('ocean data') ==
                'http://ocean.site/{repository_name}/{resource_name}')
        assert (good_portal_builder.find_visual_site_for_datatype('rotation model') == 
                'http://gplate.site/repo={repository_name}&ds={resource_name}')
        assert good_portal_builder.find_visual_site_for_datatype('unknown type') == None


    def test_build_portal_repo_build_failed(self, mocked_resources, good_portal_builder):
        """ Test that build_portal() can deal with repo building failures.  """
        with patch('bdkdportal.databuild.RepositoryBuilder') as mock_RepositoryBuilder:
            mock_RepositoryBuilder.return_value.build_portal_from_repo = MagicMock(side_effect=Exception("Test failure"))
            mocked_resources.start_patching()
            with pytest.raises(Exception):
                good_portal_builder.build_portal()
            mocked_resources.stop_patching()


    def test_build_portal_cleanup_failure(self, mocked_resources, good_portal_builder):
        """ Test that build_portal() can deal with dataset cleanup failures.
        """
        mocked_resources.start_patching()
        # One way to fail the cleanup is to fail the dataset delete process.
        mock_ckan_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        mock_ckan_site.action.package_delete = MagicMock(side_effect=Exception("Delete failure"))
        mock_ckan_site.action.current_package_list_with_resources.return_value = [
            {
                'name':'test_bucket-groupb-groupbb-dataset2',
                'revision_timestamp' : '20131201T12:34:56',
                'groups' : [{'name':'groupb'},{'name':'groupbb'}],
            }]
        success = good_portal_builder.build_portal()
        mocked_resources.stop_patching()

        # Clean up failures do not terminate the build, but it should at least log some kind of error.
        assert success == False, "An error should have been noted if cleanup failed"


    def test_build_portal_purge_obsolete_dataset(self, single_dataset_repo, good_portal_cfg, good_portal_builder, mocked_resources):
        """ If the dataset exists in CKAN portal but no longer exist in datastore, the dataset should be purged.
        This test needs to be done at PortalBuilder level instead of RepositoryBuilder as the checking of dataset
        usage has to be done after all repositories have been 'tounched' so that untouched dataset can be purged.
        """
        mocked_resources.start_patching()
        mock_ckan_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        # CKAN returns 2 datasets, in which one of the dataset is no longer in the dataset.
        mock_ckan_site.action.current_package_list_with_resources.return_value = [
            {
                'name':'test_bucket-groupa-groupaa-dataset1',
                'revision_timestamp' : '20131201T12:34:56',
                'groups' : [{'name':'groupa'},{'name':'groupaa'}],
            },{
                'name':'test_bucket-groupa-groupbb-dataset2',
                'revision_timestamp' : '20131201T12:34:56',
                'groups' : [{'name':'groupa'},{'name':'groupbb'}],
            }]
        # Datastore is only going to return 1 dataset (i.e. single_dataset_repo)
        mocked_resources.get_mock('bdkd.datastore.Repository').return_value = single_dataset_repo
        # CKAN returns no dataset associated to the group 'groupbb', and should result in the group
        # being purged. Note: however group purge is currently not working so the test is now disabled.
        mock_ckan_site.action.group_show = MagicMock(
                side_effect=lambda id: {'package_count':{'groupbb':0}.get(id,1)})
        good_portal_builder.build_portal()
        mocked_resources.stop_patching()

        mock_purge = mocked_resources.get_mock('bdkdportal.databuild.purge_ckan_dataset')
        mock_purge.assert_called_once_with('test_bucket-groupa-groupbb-dataset2','test_ckan_cfg_file')
        # This was disabled at the library as purging of group in CKAN has an issue.
        # mock_site.action.group_purge.assert_called_once_with(id='groupbb')


    @patch('ckan.lib.cli.DatasetCmd')
    def test_ckan_dataset_purge(self, mock_dsc):
        """ This is probably not a very good test, but there needs to be something that checks
        that if a dataset is purged, it actually makes a call to CKAN to purge the dataset.
        This needs to be updated if we can get dataset purged via the API instead of via paster.
        """
        from bdkdportal.databuild import purge_ckan_dataset
        purge_ckan_dataset('dataset_to_delete', 'dummy_ini')
        dsc_call_args = mock_dsc.return_value.run.call_args
        purge_cmd = (
            dsc_call_args and
            len(dsc_call_args) > 0 and 
            dsc_call_args[0][0] == ['purge','dataset_to_delete','-c','dummy_ini'])
        assert purge_cmd, 'Purge dataset should have triggered a paste purge command'


    def test_setup_organizations(self, mocked_resources):
        """ Test that setup organizations creates CKAN organization from repo config
        """
        mocked_resources.start_patching()
        portal_builder = PortalBuilder(logger=MagicMock())
        portal_builder.load_config(from_string="""
                api_key: test-key
                ckan_url: test_ckan_url
                repos:
                    - bucket: test_bucket1
                      org_name: test_org_name1
                      org_title: test_org_title1
                    - bucket: test_bucket2
                      org_name: test_org_name2
                      org_title: test_org_title2
                """)
        portal_builder.setup_organizations()
        mocked_resources.stop_patching()

        mock_ckan = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        assert mock_ckan.action.organization_create.call_count == 2, "setup_organizations() should only be called twice"
        mock_ckan.action.organization_create.assert_has_calls([
                call(name='test_org_name1',
                     title='test_org_title1',
                     description='test_org_title1'),
                call(name='test_org_name2',
                     title='test_org_title2',
                     description='test_org_title2')])

        # Now only after a particular repo
        mocked_resources.start_patching()
        portal_builder.setup_organizations(repo_name='test_bucket2')
        mocked_resources.stop_patching()
        mock_ckan = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        assert mock_ckan.action.organization_create.call_count == 1, "setup_organizations() should only be called once"
        mock_ckan.action.organization_create.assert_has_calls([
                call(name='test_org_name2',
                     title='test_org_title2',
                     description='test_org_title2')])

    def test_setup_organizations_no_duplication(self, mocked_resources):
        """ Test that setup organizations does not create a CKAN organization if it already exists
        """
        mocked_resources.start_patching()
        portal_builder = PortalBuilder(logger=MagicMock())
        portal_builder.load_config(from_string="""
                api_key: test-key
                ckan_url: test_ckan_url
                repos:
                    - bucket: test_bucket1
                      org_name: test_org_name1
                      org_title: test_org_title1
                """)
        mock_ckan = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        mock_ckan.action.organization_list.return_value = ['test_org_name1']
        portal_builder.setup_organizations()
        mocked_resources.stop_patching()

        assert mock_ckan.action.organization_create.call_count == 0, "setup_organizations() should not create organization if it already exists"


    def test_no_concurrent_build(self, good_portal_builder, mocked_resources):
        """ Test that if a portal_build is happening, then 2 second should not be allowed.
        """
        mocked_resources.start_patching()
        mock_locker = mocked_resources.get_mock('bdkdportal.databuild.prepare_lock_file')
        from lockfile import LockTimeout
        mock_locker.return_value.acquire = MagicMock(side_effect=LockTimeout())

        # If unable to acquire a lock, the build_portal() call should raise an exception.
        with pytest.raises(Exception):
            good_portal_builder.build_portal()

        mocked_resources.stop_patching()


    def test_remove_all_datasets(self, mocked_resources):
        """ Test that remove_all_datasets() removes all dataset for all configured repositories.  """
        with patch('bdkdportal.databuild.RepositoryBuilder') as repo_builder_patcher:
            mocked_resources.start_patching()
            mock_purge = mocked_resources.get_mock('bdkdportal.databuild.purge_ckan_dataset')
            mock_ckan_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
            mock_ckan_site.action.package_list.return_value = [
                'test_bucket-group1-group2-dataset1',
                'test_bucket-group1-group2-dataset2',
                'test_bucket-group3-dataset3']
            portal_builder = PortalBuilder(logger=MagicMock())
            portal_builder.load_config(from_string="""
                    api_key: test-key
                    ckan_cfg: test_ckan_cfg_file
                    ckan_url: test_ckan_url
                    repos:
                        - bucket: test_bucket1
                          org_name: test_org_name1
                          org_title: test_org_title1
                          ds_host: test_ds_host1
                          download_url_format: test_format1
                    """)
            portal_builder.remove_all_datasets()
            mocked_resources.stop_patching()

            mock_purge.assert_has_calls([
                call('test_bucket-group1-group2-dataset1', 'test_ckan_cfg_file'),
                call('test_bucket-group1-group2-dataset2', 'test_ckan_cfg_file'),
                call('test_bucket-group3-dataset3',        'test_ckan_cfg_file')])


class TestRepositoryBuilder:

    def test_build_portal_from_repo(self, single_dataset_repo, good_portal_cfg, mocked_resources):
        """ Test that a typical portal building process still works
        """
        mocked_resources.start_patching()

        # Mock a single dataset in datastore repository so that the builder attempts to connect to CKAN.
        mocked_resources.get_mock('bdkd.datastore.Repository').return_value = single_dataset_repo
        mock_portal_builder = MagicMock()
        repo_builder = RepositoryBuilder(mock_portal_builder, good_portal_cfg)
        repo_cfg = good_portal_cfg['repos'][0]
        repo_builder.build_portal_from_repo(repo_cfg)
        mocked_resources.stop_patching()

        mock_ckan_conn = mocked_resources.get_mock('ckanapi.RemoteCKAN')
        mock_ckan_site = mock_ckan_conn.return_value
        mock_ds_repo = mocked_resources.get_mock('bdkd.datastore.Repository')
        mock_ds_host = mocked_resources.get_mock('bdkd.datastore.Host')
        mock_write = mocked_resources.get_mock('__builtin__.open').return_value.write

        # Check that using the configs, it connects to the right hosts/repos.
        mock_ckan_conn.assert_has_calls(call('test_ckan_url', apikey='test-key'))
        mock_ds_host.assert_has_calls(call(host='test_ds_host'))
        mock_ds_repo.assert_has_calls(call(mock_ds_host.return_value, 'test_bucket'))

        # Check there was an attempt to write to a manifest file containing the right entries.
        mock_write.assert_has_calls([
            call('s3://test_bucket/groupA/groupAA/dataset1/file1\n'),
            call('http://remotefile.internet/file2\n'),
            ])

        # Check that there was a look up for its visual site and that a visualization resource was created.
        # Note: as the portal builder is a mock, we'll check the link to the visualization in a separate test.
        mock_portal_builder.find_visual_site_for_datatype.assert_called_once_with('ocean data')
        mock_ckan_site.action.resource_create.assert_has_calls([
                call(url=ANY,
                     package_id='test_bucket-groupa-groupaa-dataset1',
                     description='Explore/visualise the dataset',
                     name='explore',
                     format='html')],
                any_order=True)

        # Check that a download resource was created (content will be checked in a separate test)
        mock_ckan_site.action.resource_create.assert_has_calls([
                call(package_id='test_bucket-groupa-groupaa-dataset1',
                     description = ANY,
                     name='download',
                     format='html',
                     upload=ANY)],
                any_order=True)


    def test_build_portal_from_repo_bad_portal_config(self, single_dataset_repo, good_portal_cfg, mocked_resources):
        """ Test that bad config throws error
        """
        bad_cfg = good_portal_cfg
        del bad_cfg['api_key']
        mocked_resources.start_patching()
        repo_builder = RepositoryBuilder(MagicMock(), bad_cfg)
        with pytest.raises(Exception):
            repo_builder.build_portal_from_repo(bad_cfg['repos'][0])
        mocked_resources.stop_patching()


    def test_build_portal_from_repo_bad_repo_config(self, single_dataset_repo, good_portal_cfg, mocked_resources):
        """ Test that bad config throws error
        """
        bad_cfg = good_portal_cfg
        del bad_cfg['repos'][0]['org_name']
        mocked_resources.start_patching()
        repo_builder = RepositoryBuilder(MagicMock(), bad_cfg)
        with pytest.raises(Exception):
            repo_builder.build_portal_from_repo(bad_cfg['repos'][0])
        mocked_resources.stop_patching()


    def test_build_portal_from_repo_bad_resource_file(self, good_portal_cfg, good_portal_builder, mocked_resources):
        """ Test that if the datastore has a bad resource file, the build will log an error instead of quietly failing.
        """
        mocked_resources.start_patching()
        mock_repo = mocked_resources.get_mock('bdkd.datastore.Repository').return_value
        mock_repo.name = 'test_bucket'
        mock_repo.list.return_value = [ 'dataset1' ]
        mock_repo.get.return_value.name = 'dataset1'
        mock_repo.get.return_value.metadata = { 'author':'test author', 'description':'test desc' }
        # Mock a bad file that is neither local nor remote.
        bad_file = MagicMock()
        bad_file.location.return_value = None
        bad_file.remote.return_value = None
        mock_repo.get.return_value.files = [ bad_file ]

        repo_builder = RepositoryBuilder(good_portal_builder, good_portal_cfg)
        repo_cfg = good_portal_cfg['repos'][0]
        repo_builder.build_portal_from_repo(repo_cfg)
        mocked_resources.stop_patching()
        mock_logger = mocked_resources.get_mock('logging.getLogger')
        assert 'dataset1' in mock_logger.return_value.error.call_args[0][0], "Expected error to be logged when resource is invalid"


    def test_build_portal_from_repo_visualization(self, good_portal_cfg, good_portal_builder, mocked_resources):
        """ Test visual resource creation based on dataset type and visual configuration
        """
        mocked_resources.start_patching()
        mock_repo = mocked_resources.get_mock('bdkd.datastore.Repository').return_value
        mock_repo.name = 'test_bucket'
        mock_repo.list.return_value = [ 'dataset1' ]
        mock_repo.get.return_value.name = 'dataset1'
        mock_repo.get.return_value.metadata = {
            'author':'test author',
            'description':'test desc',
            'data_type':'ocean data' }

        repo_builder = RepositoryBuilder(good_portal_builder, good_portal_cfg)
        repo_cfg = good_portal_cfg['repos'][0]
        repo_builder.build_portal_from_repo(repo_cfg)
        mocked_resources.stop_patching()

        mock_ckan_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        mock_ckan_site.action.resource_create.assert_has_calls([
                call(url=ANY,
                     package_id='test_bucket-dataset1',
                     description='Explore/visualise the dataset',
                     name='explore',
                     format='html')],
                any_order=True)


    def test_build_portal_from_repo_no_type_no_visual(self, good_portal_cfg, good_portal_builder, mocked_resources):
        """ Test that if the dataset has no data type, it will have no visualization CKAN resource.
        """
        mocked_resources.start_patching()
        mock_repo = mocked_resources.get_mock('bdkd.datastore.Repository').return_value
        mock_repo.name = 'test_bucket'
        mock_repo.list.return_value = [ 'dataset1' ]
        mock_repo.get.return_value.name = 'dataset1'
        mock_repo.get.return_value.metadata = {
            'author':'test author',
            'description':'test desc' }

        repo_builder = RepositoryBuilder(good_portal_builder, good_portal_cfg)
        repo_cfg = good_portal_cfg['repos'][0]
        repo_builder.build_portal_from_repo(repo_cfg)
        mocked_resources.stop_patching()

        mock_ckan_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        for c in mock_ckan_site.action.resource_create.call_args_list:
            assert c[1].get('name') != 'explore', "Dataset without data_type should not have an explore link"


    def test_build_portal_from_repo_no_site_no_visual(self, good_portal_cfg, good_portal_builder, mocked_resources):
        """ Test that if the dataset that has a data type that is not configured as a visual site, will not
        have a visualization CKAN resource created.
        """
        mocked_resources.start_patching()
        mock_repo = mocked_resources.get_mock('bdkd.datastore.Repository').return_value
        mock_repo.name = 'test_bucket'
        mock_repo.list.return_value = [ 'dataset1' ]
        mock_repo.get.return_value.name = 'dataset1'
        mock_repo.get.return_value.metadata = {
            'author':'test author',
            'data_type':'unknown type',
            'description':'test desc' }

        repo_builder = RepositoryBuilder(good_portal_builder, good_portal_cfg)
        repo_cfg = good_portal_cfg['repos'][0]
        repo_builder.build_portal_from_repo(repo_cfg)
        mocked_resources.stop_patching()

        mock_ckan_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        for c in mock_ckan_site.action.resource_create.call_args_list:
            assert c[1].get('name') != 'explore', "Dataset without data_type should not have an explore link"


    def test_build_portal_from_repo_visualization(self, good_portal_cfg, good_portal_builder, mocked_resources):
        """ Test visual resource creation based on dataset type and visual configuration
        """
        mocked_resources.start_patching()
        mock_repo = mocked_resources.get_mock('bdkd.datastore.Repository').return_value
        mock_repo.name = 'test_bucket'
        mock_repo.list.return_value = [ 'dataset1' ]
        mock_repo.get.return_value.name = 'dataset1'
        mock_repo.get.return_value.metadata = {
            'author':'test author',
            'description':'test desc',
            'data_type':'ocean data' }

        repo_builder = RepositoryBuilder(good_portal_builder, good_portal_cfg)
        repo_cfg = good_portal_cfg['repos'][0]
        repo_builder.build_portal_from_repo(repo_cfg)
        mocked_resources.stop_patching()

        mock_ckan_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        mock_ckan_site.action.resource_create.assert_has_calls([
                call(url=ANY,
                     package_id='test_bucket-dataset1',
                     description='Explore/visualise the dataset',
                     name='explore',
                     format='html')],
                any_order=True)


    def test_build_portal_from_repo_creates_visual_link_via_portal_builder(
            self, single_dataset_repo, good_portal_cfg, 
            good_portal_builder, mocked_resources):
        """ This is more like an integration whereby the build_portal_from_repo() method is now executed
        against a real PortalBuilder object (but all other resources are still mocked). The test here
        checks that the visual links created are formatted as expected.
        """
        mocked_resources.start_patching()
        mocked_resources.get_mock('bdkd.datastore.Repository').return_value = single_dataset_repo
        repo_builder = RepositoryBuilder(good_portal_builder, good_portal_cfg)
        repo_builder.build_portal_from_repo(good_portal_cfg['repos'][0])
        mocked_resources.stop_patching()

        mock_ckan_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        mock_ckan_site.action.resource_create.assert_has_calls([
                call(url='http://ocean.site/test_bucket/groupA%2FgroupAA%2Fdataset1',
                     package_id='test_bucket-groupa-groupaa-dataset1',
                     description='Explore/visualise the dataset',
                     name='explore',
                     format='html')],
                any_order=True)


    def test_build_portal_from_repo_create_if_new(self, single_dataset_repo, good_portal_cfg, mocked_resources):
        """ Test that new CKAN dataset is created for dataset that is not yet in the portal.
        """
        mocked_resources.start_patching()
        mock_ckan_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        mocked_resources.get_mock('bdkd.datastore.Repository').return_value = single_dataset_repo
        repo_builder = RepositoryBuilder(MagicMock(), good_portal_cfg)
        repo_builder.build_portal_from_repo(good_portal_cfg['repos'][0])
        mocked_resources.stop_patching()

        mock_ckan_site.action.package_create.assert_called_once_with(
            name = 'test_bucket-groupa-groupaa-dataset1',
            owner_org = 'test_org_name',
            title = 'dataset1',
            version = '1.0',
            notes = 'test desc',
            author = 'test author',
            author_email='test_author@test.email',
            maintainer='test maintainer',
            maintainer_email='test_maintainer@test.email',
            groups = [{'name': 'groupa'}, {'name': 'groupaa'}])


    def test_build_portal_from_repo_no_update_if_still_fresh(self, single_dataset_repo, good_portal_cfg, mocked_resources):
        """ If dataset already exist in CKAN portal and has NOT been updated in datastore, the build will not do anything.
        """
        mocked_resources.start_patching()
        mock_ckan_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        single_dataset_repo.get_resource_last_modified = MagicMock(
                side_effect=lambda r: datetime.datetime(2013, 11, 01, 0, 0, 0))
        mocked_resources.get_mock('bdkd.datastore.Repository').return_value = single_dataset_repo
        mock_ckan_site.action.current_package_list_with_resources.return_value = [{
                'name':'test_bucket-groupa-groupaa-dataset1',
                'revision_timestamp' : '20131201T12:34:56',
                'groups' : [],
            }]

        repo_builder = RepositoryBuilder(MagicMock(), good_portal_cfg)
        repo_builder.build_portal_from_repo(good_portal_cfg['repos'][0])
        mocked_resources.stop_patching()

        # Check that no new dataset creation took place.
        assert not mock_ckan_site.action.package_create.called, 'Package creation should not have been called'


    def test_build_portal_from_repo_update_if_stale(self, single_dataset_repo, good_portal_cfg, mocked_resources):
        """ If dataset already exist in CKAN portal and HAS BEEN UPDATED in datastore, the dataset will be rebuilt.
        """
        mocked_resources.start_patching()
        mock_ckan_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        single_dataset_repo.get_resource_last_modified = MagicMock(
                side_effect=lambda r: datetime.datetime(2014, 11, 01, 0, 0, 0))
        mocked_resources.get_mock('bdkd.datastore.Repository').return_value = single_dataset_repo
        mock_ckan_site.action.current_package_list_with_resources.return_value = [{
                'name':'test_bucket-groupa-groupaa-dataset1',
                'revision_timestamp' : '20131201T12:34:56',
                'groups' : [],
            }]

        repo_builder = RepositoryBuilder(MagicMock(), good_portal_cfg)
        repo_builder.build_portal_from_repo(good_portal_cfg['repos'][0])
        mocked_resources.stop_patching()

        # Check that the existing dataset was purged and a new dataset created.
        assert mock_ckan_site.action.package_create.called, 'Package should have been updated'
        mock_purge = mocked_resources.get_mock('bdkdportal.databuild.purge_ckan_dataset')
        mock_purge.assert_called_once_with('test_bucket-groupa-groupaa-dataset1','test_ckan_cfg_file')


    def test_build_portal_from_repo_dataset_audit(self, single_dataset_repo, good_portal_cfg, mocked_resources):
        """ Test the dataset audit method whereby dataset touched by the build process are properly noted.
        """
        mocked_resources.start_patching()
        # Datastore returns 2 dataset.
        mock_repo = mocked_resources.get_mock('bdkd.datastore.Repository').return_value
        mock_repo.name = 'test_bucket'
        mock_repo.list.return_value = [ 'groupA/groupAA/dataset1', 'groupB/groupBB/dataset2' ]
        # CKAN returns 3 datasets.
        mock_ckan_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        mock_ckan_site.action.current_package_list_with_resources.return_value = [
                { 'name':'test_bucket-groupa-groupaa-dataset1', 'revision_timestamp' : '20131201T12:34:56', 'groups' : [] },
                { 'name':'test_bucket-groupb-groupbb-dataset2', 'revision_timestamp' : '20131201T12:34:56', 'groups' : [] },
                { 'name':'test_bucket-groupc-groupcc-dataset3', 'revision_timestamp' : '20131201T12:34:56', 'groups' : [] }]
        dataset_audit = {}
        repo_builder = RepositoryBuilder(MagicMock(), good_portal_cfg)
        repo_builder.set_dataset_audit(dataset_audit)
        repo_builder.build_portal_from_repo(good_portal_cfg['repos'][0])
        mocked_resources.stop_patching()
        # Audit should detect that there were 2 datasets that are still in both CKAN and datastore
        assert len(dataset_audit) == 2, "Incorrect number of dataset detected during audit"
        assert 'test_bucket-groupa-groupaa-dataset1' in dataset_audit
        assert 'test_bucket-groupb-groupbb-dataset2' in dataset_audit


    def test_build_portal_from_repo_no_download_if_not_configured1(self, single_dataset_repo, good_portal_cfg, mocked_resources):
        """ Test that if the download configuration is not set, then no download link is created.
        """
        mocked_resources.start_patching()
        mocked_resources.get_mock('bdkd.datastore.Repository').return_value = single_dataset_repo
        # Portal config has no 'download_template'
        del good_portal_cfg['download_template']
        repo_builder = RepositoryBuilder(MagicMock(), good_portal_cfg)
        repo_builder.build_portal_from_repo(good_portal_cfg['repos'][0])
        mocked_resources.stop_patching()
        mock_ckan_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        assert not check_calls_with(mock_ckan_site.action.resource_create, 'name', 'download'), "Should not have created a download"

    def test_build_portal_from_repo_no_download_if_not_configured2(self, single_dataset_repo, good_portal_cfg, mocked_resources):
        # Repository config has no 'download_url_format'
        mocked_resources.start_patching()
        mocked_resources.get_mock('bdkd.datastore.Repository').return_value = single_dataset_repo
        del good_portal_cfg['repos'][0]['download_url_format']
        repo_builder = RepositoryBuilder(MagicMock(), good_portal_cfg)
        repo_builder.build_portal_from_repo(good_portal_cfg['repos'][0])
        mocked_resources.stop_patching()
        mock_ckan_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        assert not check_calls_with(mock_ckan_site.action.resource_create, 'name', 'download'), "Should not have created a download"

    def test_build_portal_from_repo_no_download_if_not_configured3(self, single_dataset_repo, good_portal_cfg, mocked_resources):
        # The download template file does not exist.
        mocked_resources.start_patching()
        mocked_resources.get_mock('bdkd.datastore.Repository').return_value = single_dataset_repo
        mock_exists = mocked_resources.get_mock('os.path.exists')
        mock_exists.side_effect = lambda f: dict(test_template=False).get(f,True) # False if the file is 'test_template'
        repo_builder = RepositoryBuilder(MagicMock(), good_portal_cfg)
        repo_builder.build_portal_from_repo(good_portal_cfg['repos'][0])
        mocked_resources.stop_patching()
        mock_ckan_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value
        assert not check_calls_with(mock_ckan_site.action.resource_create, 'name', 'download'), "Should not have created a download"


from bdkdportal.databuild import portal_data_builder_entry as call_main
import argparse

class TestMain:

    def test_prepare_lock_file(self):
        """ Test that prepare_lock_file() claims what it does. Note that FileLock cannot be
        mocked so this will be using a real lock file.
        """
        from bdkdportal.databuild import prepare_lock_file
        from lockfile import LockTimeout
        lock_filename = '/tmp/__TEST_LOCK_FILE__'
        build_lock1 = prepare_lock_file(lock_filename)
        build_lock1.acquire(1)
        assert build_lock1.is_locked(), "Lock file did not appear to work"
        build_lock1.release()
        assert not build_lock1.is_locked(), "Release lock file did not appear to work"


    def test_main_no_arg_prints_help(self):
        """ Test that mainline prints help if no arg was provided. """
        with pytest.raises(SystemExit) as e:
            with patch.object(argparse.ArgumentParser, 'print_help') as mock_help:
                call_main(['prog'])
        assert mock_help.called, "Help was expected but wasn't there"


    def test_main_run_unknown_command(self):
        with pytest.raises(SystemExit) as e:
            call_main(['prog','unknown'])


    def test_main_run_update_no_config(self):
        with pytest.raises(SystemExit) as e:
            call_main(['prog','update'])


    @patch('logging.config')
    @patch('bdkdportal.databuild.PortalBuilder')
    def test_main_run_update_with_logging(self, mock_PortalBuilder, mock_logging_config):
        import logging
        mock_portal_builder = mock_PortalBuilder.return_value

        # Test various logging levels
        with patch('logging.basicConfig') as mock_basicConfig:
            call_main(['prog', '-c', 'my_config', 'update'])
            mock_basicConfig.assert_called_once_with(level=logging.WARN)

        with patch('logging.basicConfig') as mock_basicConfig:
            call_main(['prog', '-c', 'my_config', 'update', '--verbose'])
            mock_basicConfig.assert_called_once_with(level=logging.INFO)

        with patch('logging.basicConfig') as mock_basicConfig:
            call_main(['prog', '-c', 'my_config', 'update', '--debug'])
            mock_basicConfig.assert_called_once_with(level=logging.DEBUG)

        with patch('logging.config.fileConfig') as mock_fileConfig:
            call_main(['prog', '-c', 'my_config', 'update', '--log-ini', 'test_log.ini'])
            mock_fileConfig.assert_called_once_with('test_log.ini')


    @patch('bdkdportal.databuild.PortalBuilder')
    @patch('logging.basicConfig')
    def test_main_run_update(self, mock_basicConfig, mock_PortalBuilder):
        mock_portal_builder = mock_PortalBuilder.return_value

        call_main(['prog', '-c','my_config','update'])

        mock_portal_builder.load_config.assert_called_once_with(from_file='my_config')
        mock_portal_builder.build_portal.assert_called_once_with(repo_name=None)


    @patch('bdkdportal.databuild.PortalBuilder')
    @patch('logging.basicConfig')
    def test_main_run_setup(self, mock_basicConfig, mock_PortalBuilder):
        mock_portal_builder = mock_PortalBuilder.return_value
        call_main(['prog', '-c','my_config','setup'])
        mock_portal_builder.load_config.assert_called_once_with(from_file='my_config')
        mock_portal_builder.setup_organizations.assert_called_once_with(repo_name=None)


    @patch('bdkdportal.databuild.PortalBuilder')
    @patch('logging.basicConfig')
    def test_main_run_purge(self, mock_basicConfig, mock_PortalBuilder):
        mock_portal_builder = mock_PortalBuilder.return_value
        call_main(['prog', '-c','my_config','purge'])
        mock_portal_builder.load_config.assert_called_once_with(from_file='my_config')
        mock_portal_builder.remove_all_datasets.assert_called_once_with()


    @patch('bdkdportal.databuild.PortalBuilder')
    @patch('logging.basicConfig')
    def test_main_run_reprime(self, mock_basicConfig, mock_PortalBuilder):
        mock_portal_builder = mock_PortalBuilder.return_value
        call_main(['prog', '-c','my_config','reprime'])
        mock_portal_builder.load_config.assert_called_once_with(from_file='my_config')
        mock_portal_builder.remove_all_datasets.assert_called_once_with()
        mock_portal_builder.build_portal.assert_called_once_with()


    @patch('time.sleep')
    @patch('daemon.DaemonContext')
    @patch('bdkdportal.databuild.PortalBuilder')
    @patch('logging.basicConfig')
    @patch('logging.getLogger')
    def test_main_run_daemon(self, mock_getLogger, mock_basicConfig, mock_PortalBuilder, mock_DaemonContext, mock_sleep):
        mock_portal_builder = mock_PortalBuilder.return_value
        mock_portal_builder.get_nap_duration.return_value = 123
        with patch('bdkdportal.databuild.is_running', side_effect=[True, True, False]):
            # Side effect: 1st and 2nd cycles do the build, but 3rd cycle will terminates.
            call_main(['prog', '-c','my_config','daemon'])

        mock_portal_builder.load_config.assert_called_once_with(from_file='my_config')
        # Called twice because it was setup to do 2 cycles then terminates.
        mock_portal_builder.build_portal.assert_has_calls([call(), call()])
        mock_sleep.assert_called_with(123)

        # When running in daemon mode, by default is_running() is always True until it has been stopped.
        import bdkdportal.databuild
        assert bdkdportal.databuild.is_running(), "Default builder state should be 'running'"
        bdkdportal.databuild.stop_running()
        assert not bdkdportal.databuild.is_running(), "Builder state should have changed to 'stopped'"

        # Now that the mode is set to stop, executing in daemon mode should not trigger a 'build'
        count_before = mock_portal_builder.build_portal.call_count
        call_main(['prog', '-c','my_config','daemon'])
        assert mock_portal_builder.build_portal.call_count == count_before, "Should not build after it has been stopped"


    @patch('time.sleep')
    @patch('daemon.DaemonContext')
    @patch('bdkdportal.databuild.PortalBuilder')
    @patch('logging.basicConfig')
    @patch('logging.getLogger')
    def test_main_run_daemon_with_failure(self, mock_getLogger, mock_basicConfig, mock_PortalBuilder,
                                          mock_DaemonContext, mock_sleep):
        mock_portal_builder = mock_PortalBuilder.return_value
        mock_portal_builder.get_nap_duration.return_value = 1
        mock_portal_builder.build_portal.side_effect = Exception("Simulated build failure")
        with patch('bdkdportal.databuild.is_running', side_effect=[True, True, False]):
            call_main(['prog', '-c','my_config','daemon'])

        # Test that 2 build attempts even though the build threw errors.
        mock_portal_builder.load_config.assert_called_once_with(from_file='my_config')
        mock_portal_builder.build_portal.call_count == 2
