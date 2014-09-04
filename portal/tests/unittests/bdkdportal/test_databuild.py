import pytest
from mock import Mock, patch, MagicMock, call, ANY
from bdkdportal.databuild import PortalBuilder
import yaml
import datetime


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
        'jinja2.FileSystemLoader',
        'jinja2.Environment',
        'jinja2.PackageLoader',
        'ckanapi.RemoteCKAN',
        'bdkd.datastore.Repository',
        'bdkdportal.databuild.prepare_lock_file',
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
def good_builder(good_cfg_string):
    # Provide a portal builder that has a good configuration.
    builder = PortalBuilder()
    builder.load_config(from_string=good_cfg_string)
    return builder


def mock_getmeta(key, default=None):
    mock_meta = {
        'author':'dan',
        'author_email':'dan',
        'maintainer':'dan',
        'maintainer_email':'dan',
        'version':'1.0',
        'description':'test desc',
        'data_type':'ocean data',
    }
    if key in mock_meta.keys():
        return mock_meta[key]
    return default


@pytest.fixture
@patch('bdkd.datastore.Host')
def single_dataset_repo(mock_ds_host):
    """ Returns a mock datastore repository that gives the caller:
    - repository called 'test_bucket'
    - some meta data about the dataset, as per mock_getmeta()
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
        portal_builder_from_file = PortalBuilder()
        cfg_from_yaml = yaml.load(good_cfg_string) # For intercepting the loading
        with patch('yaml.load') as mock_yaml_load:
            mock_yaml_load.return_value = cfg_from_yaml

            # Test that load_config will attempt to open up the file
            with patch('__builtin__.open') as mock_open:
                portal_builder_from_file.load_config(from_file='cfgfile_to_load')
                mock_open.assert_called_once_with('cfgfile_to_load')

        portal_builder_from_string = PortalBuilder()
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
        builder = PortalBuilder()
        # If config file is missing or not openable, it should raise an exception.
        with patch('os.path.exists', return_value=False):
            with pytest.raises(Exception):
                builder.load_config("missing_cfg")

        with patch('os.path.exists', return_value=True):
            with patch('__builtin__.open', return_value=None):
                with pytest.raises(Exception):
                    builder.load_config("open_fail_cfg")


    def test_data_build_with_bad_config(self):
        """ Test that priming fails if config is bad.
        """
        # Config not loaded should fail
        with patch('bdkdportal.databuild.prepare_lock_file', return_value=MagicMock()):
            with pytest.raises(Exception):
                builder = PortalBuilder()
                builder.build_portal()

            # Missing key settings should fail
            with pytest.raises(Exception):
                builder = PortalBuilder()
                builder.load_config(from_string="""
                    repos:
                        - bucket: test_bucket
                          org_name: test_org_name
                          org_title: test_org_title
                          ckan_url: test_ckan_url
                          ds_host: test_ds_host
                    """)
                builder.build_portal()

            with pytest.raises(Exception):
                builder = PortalBuilder()
                builder.load_config(from_string="""
                    api_key: test-key
                    """)
                builder.build_portal()


    @patch('bdkd.datastore.Host')
    @patch('ckanapi.RemoteCKAN')
    def test_data_build_repo_connection(self, mock_ckanapi, mock_ds_host, single_dataset_repo, good_builder):
        """ Test that a builder with a good config, the builder will connect to the correct datastore
        host and repository to source data, and connect to the right CKAN portal to build the data.
        """
        with patch('bdkd.datastore.Repository', return_value=single_dataset_repo) as mock_repo:
            from mock import mock_open
            open_name = '%s.open' % '__builtin__'
            with patch(open_name, create=True):
                with patch('bdkdportal.databuild.prepare_lock_file', return_value=MagicMock()):
                    good_builder.build_portal(repo_name='test_bucket')
                mock_ds_host.assert_called_once_with(host='test_ds_host') # connects to the right host
                assert mock_repo.call_args[0][1] == 'test_bucket'         # connects to the right repo
                mock_ckanapi.assert_any_call('test_ckan_url', apikey='test-key') # connects to the right CKAN


    @patch('ckanapi.RemoteCKAN')
    def test_data_build_repo_manifest_write(self, mock_ckanapi, single_dataset_repo, good_builder):
        with patch('bdkd.datastore.Repository', return_value=single_dataset_repo):
            # Check that writes were done to the manifest.
            with patch('__builtin__.open', create=True) as mock_open:
                mock_open.return_value = MagicMock(spec=file)
                mock_write = mock_open.return_value.write
                # Execute the priming using the mocks.
                with patch('bdkdportal.databuild.prepare_lock_file', return_value=MagicMock()):
                    good_builder.build_portal(repo_name='test_bucket')
                mock_write.assert_has_calls([
                    call('s3://test_bucket/groupA/groupAA/dataset1/file1\n'),
                    call('http://remotefile.internet/file2\n'),
                    ])


    @patch('ckanapi.RemoteCKAN')
    @patch('bdkd.datastore.Repository')
    @patch('__builtin__.open', create=True)
    def test_visualization(self, mock_open, mock_repo, mock_ckanapi, single_dataset_repo, good_builder):
        # The single dataset repo provides a single dataset of data type 'ocean data'.
        # The configuration states that for ocean data, visualization should point to
        # 'http://ocean.site/{repo_name}/{dataset_name}
        mock_site = mock_ckanapi.return_value
        mock_repo.return_value = single_dataset_repo
        with patch('bdkdportal.databuild.prepare_lock_file', return_value=MagicMock()):
            good_builder.build_portal(repo_name='test_bucket')

        # Check that a visualization resource was created.
        mock_site.action.resource_create.assert_has_calls([
            call(url='http://ocean.site/test_bucket/groupA%2FgroupAA%2Fdataset1',
                 package_id='test_bucket-groupa-groupaa-dataset1',
                 description='Explore the dataset',
                 name='explore',
                 format='html')],
            any_order=True)


    def test_find_visual_site(self, good_builder):
        assert good_builder.find_visual_site_for_datatype('ocean data') == 'http://ocean.site/{repository_name}/{resource_name}'
        assert good_builder.find_visual_site_for_datatype('rotation model') == 'http://gplate.site/repo={repository_name}&ds={resource_name}'


    def test_download(self, single_dataset_repo, good_builder, mocked_resources):
        # The single dataset repo provides a single dataset of data type 'ocean data'.
        # The class creates a 'download resource' in CKAN for files of that dataset.
        mocked_resources.start_patching()
        mocked_resources.get_mock('os.path.exists').return_value = True
        mocked_resources.get_mock('bdkd.datastore.Repository').return_value = single_dataset_repo
        mock_site = mocked_resources.get_mock('ckanapi.RemoteCKAN').return_value

        good_builder.build_portal(repo_name='test_bucket')

        mocked_resources.stop_patching()

        # Check that a download resource was created.
        mock_site.action.resource_create.assert_has_calls(
            [
                call(package_id='test_bucket-groupa-groupaa-dataset1',
                     description = ANY,
                     name='download',
                     format='html',
                     upload=ANY)
            ],
            any_order=True)


    @patch('ckanapi.RemoteCKAN')
    @patch('bdkd.datastore.Repository')
    @patch('__builtin__.open', create=True)
    def test_dataset_create_if_new(self, mock_open, mock_repo, mock_ckanapi, single_dataset_repo, good_builder):
        # Scenario: New dataset in datastore, no dataset in CKAN portal.
        mock_site = mock_ckanapi.return_value
        mock_repo.return_value = single_dataset_repo

        with patch('bdkdportal.databuild.prepare_lock_file', return_value=MagicMock()):
            good_builder.build_portal(repo_name='test_bucket')
        mock_site.action.package_create.assert_called_once_with(
            name = 'test_bucket-groupa-groupaa-dataset1',
            owner_org = 'test_org_name',
            title = 'dataset1',
            version = '1.0',
            notes = 'test desc',
            author = 'dan',
            groups = [{'name': 'groupa'}, {'name': 'groupaa'}])


    @patch('ckan.lib.cli.DatasetCmd')
    @patch('ckanapi.RemoteCKAN')
    @patch('bdkd.datastore.Repository')
    @patch('__builtin__.open', create=True)
    def test_no_dataset_update_if_still_fresh(self, mock_open, mock_repo, mock_ckanapi, mock_dscmd, single_dataset_repo, good_builder):
        # Scenario: Dataset already exist in CKAN portal and has NOT been updated in datastore.
        # Expects the builder not to update anything.
        mock_site = mock_ckanapi.return_value
        mock_site.action.current_package_list_with_resources.return_value = [{
                'name':'test_bucket-groupa-groupaa-dataset1',
                'revision_timestamp' : '20131201T12:34:56',
                'groups' : [],
            }]
        single_dataset_repo.get_resource_last_modified = MagicMock(
            side_effect=lambda r: datetime.datetime(2013, 11, 01, 0, 0, 0))
        mock_repo.return_value = single_dataset_repo

        # Check that no new dataset creation took place.
        with patch('bdkdportal.databuild.prepare_lock_file', return_value=MagicMock()):
            good_builder.build_portal(repo_name='test_bucket')
        assert not mock_site.action.package_create.called, 'Package creation should not have been called'

     
    @patch('ckanapi.RemoteCKAN')
    @patch('bdkd.datastore.Repository')
    @patch('__builtin__.open', create=True)
    def test_dataset_update_if_stale(self, mock_open, mock_repo, mock_ckanapi, single_dataset_repo, good_builder):
        # Scenario: Dataset already exist in CKAN portal and HAS been updated in datastore.
        # Expects the builder not to delete the existing dataset and create a new one.
        mock_site = mock_ckanapi.return_value
        mock_site.action.current_package_list_with_resources.return_value = [{
                'name':'test_bucket-groupa-groupaa-dataset1',
                'revision_timestamp' : '20131201T12:34:56',
                'groups' : [],
            }]
        single_dataset_repo.get_resource_last_modified = MagicMock(
            side_effect=lambda r: datetime.datetime(2014, 11, 01, 0, 0, 0))
        mock_repo.return_value = single_dataset_repo

        # Check that the existing dataset was purged and a new dataset created.
        with patch('bdkdportal.databuild.purge_ckan_dataset') as mock_purge:
            with patch('bdkdportal.databuild.prepare_lock_file', return_value=MagicMock()):
                 good_builder.build_portal()

            assert mock_site.action.package_create.called, 'Package should have been updated'
            mock_purge.assert_called_once_with('test_bucket-groupa-groupaa-dataset1','test_ckan_cfg_file')


    @patch('bdkdportal.databuild.purge_ckan_dataset')
    @patch('ckanapi.RemoteCKAN')
    @patch('bdkd.datastore.Repository')
    @patch('__builtin__.open', create=True)
    def test_obsolete_dataset_are_purged(self, mock_open, mock_repo, mock_ckanapi, mock_purge, single_dataset_repo, good_builder):
        # Scenario: Dataset exists in CKAN portal but no longer exist in datastore.
        # Expects the builder to delete the dataset.
        mock_site = mock_ckanapi.return_value

        # CKAN returns 2 datasets, in which one of the dataset is no longer in the dataset.
        mock_site.action.current_package_list_with_resources.return_value = [
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
        single_dataset_repo.get_resource_last_modified = MagicMock(
            side_effect=lambda r: datetime.datetime(2013, 11, 01, 0, 0, 0))
        mock_repo.return_value = single_dataset_repo

        # Mock CKAN to return 0 dataset associated to the group 'groupbb'
        mock_site.action.group_show = MagicMock(
            side_effect=lambda id: {'package_count':{'groupbb':0}.get(id,1)})

        # Check that the obsolete dataset is purge.
        with patch('bdkdportal.databuild.prepare_lock_file', return_value=MagicMock()):
            good_builder.build_portal()
        mock_purge.assert_called_once_with('test_bucket-groupa-groupbb-dataset2','test_ckan_cfg_file')
        # This was disabled at the library as purging of group in CKAN has an issue.
        # mock_site.action.group_purge.assert_called_once_with(id='groupbb')


    @patch('ckan.lib.cli.DatasetCmd')
    def test_ckan_dataset_purge(self, mock_dsc):
        
        from bdkdportal.databuild import purge_ckan_dataset
        purge_ckan_dataset('dataset_to_delete', 'dummy_ini')
        dsc_call_args = mock_dsc.return_value.run.call_args
        print dsc_call_args[0][0]
        purge_cmd = (
            dsc_call_args and
            len(dsc_call_args) > 0 and 
            dsc_call_args[0][0] == ['purge','dataset_to_delete','-c','dummy_ini'])
        assert purge_cmd, 'Purge dataset should have triggered a paste purge command'

    """
    Other possible unit tests:
    def test_get_last_build_dataset_audit(self)
    def test_temp_dirs_cleaned_up(self):
    def test_data_build_repository_bad(self):
    def test_data_build_portal(self):
    def test_setup_organization_ok(self):
    def test_setup_organizations_bad(self):
    """
