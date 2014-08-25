import pytest
from mock import Mock, patch, MagicMock, call
from primer.primer import Primer
import yaml

@pytest.fixture
def good_cfg_string():
    """ Provides a good configuration string.
    Keep updating this string as more config is added.
    """
    return """
        api_key: test-key
        ckan_cfg: test_ckan_cfg_file
        repos:
            - bucket: test_bucket
              org_name: test_org_name
              org_title: test_org_title
              ckan_url: test_ckan_url
              ds_host: test_ds_host
        visual-sites:
            - data_type: ocean data
              url: http://ocean.site/{0}/{1}
        """


@pytest.fixture
def good_primer(good_cfg_string):
    # Provide a primer that has a good configuration.
    primer = Primer()
    primer.load_config(from_string=good_cfg_string)
    return primer


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


class TestPrimer:

    @patch('os.path.exists', return_value=True)
    def test_load_config_ok(self, mock_os_path_exists, good_cfg_string):
        """ Test the loading of a good primer configuration file.
        """
        primer_from_file = Primer()
        cfg_from_yaml = yaml.load(good_cfg_string) # For intercepting the loading
        with patch('yaml.load') as mock_yaml_load:
            mock_yaml_load.return_value = cfg_from_yaml

            # Test that load_config will attempt to open up the file
            with patch('__builtin__.open') as mock_open:
                primer_from_file.load_config(from_file='cfgfile_to_load')
                mock_open.assert_called_once_with('cfgfile_to_load')

        primer_from_string = Primer()
        primer_from_string.load_config(from_string=good_cfg_string)

        # Check that loading config from string and from a file should produce the same config.
        for primer in [primer_from_file, primer_from_string]:
            # Check that the good settings made it to the primer's configuration.
            assert primer._cfg['api_key'] == 'test-key'
            assert primer._cfg['ckan_cfg'] == 'test_ckan_cfg_file'
            assert len(primer._cfg['repos']) == 1
            repo_cfg = primer._cfg['repos'][0]
            assert repo_cfg["bucket"]=='test_bucket'
            assert repo_cfg["org_name"]=='test_org_name'
            assert repo_cfg["org_title"]=='test_org_title'
            assert repo_cfg["ckan_url"]=='test_ckan_url'
            assert repo_cfg["ds_host"]=='test_ds_host'


    def test_load_config_file_failures(self):
        """ Test when the primer throws if loading config file fails
        """
        primer = Primer()
        # If config file is missing or not openable, it should raise an exception.
        with patch('os.path.exists', return_value=False):
            with pytest.raises(Exception):
                primer.load_config("missing_cfg")

        with patch('os.path.exists', return_value=True):
            with patch('__builtin__.open', return_value=None):
                with pytest.raises(Exception):
                    primer.load_config("open_fail_cfg")


    def test_prime_with_bad_config(self):
        """ Test that priming fails if config is bad.
        """
        # Config not loaded should fail
        with pytest.raises(Exception):
            primer = Primer()
            primer.prime_portal()

        # Missing key settings should fail
        with pytest.raises(Exception):
            primer = Primer()
            primer.load_config(from_string="""
                repos:
                    - bucket: test_bucket
                      org_name: test_org_name
                      org_title: test_org_title
                      ckan_url: test_ckan_url
                      ds_host: test_ds_host
                """)
            primer.prime_portal()

        with pytest.raises(Exception):
            primer = Primer()
            primer.load_config(from_string="""
                api_key: test-key
                """)
            primer.prime_portal()


    @patch('bdkd.datastore.Host')
    @patch('ckanapi.RemoteCKAN')
    def test_prime_repository_ok(self, mock_ckanapi, mock_ds_host, single_dataset_repo, good_primer):
        """ Test that a primer with a good config, the primer will connect to the correct datastore
        host and repository to source data, and connect to the right CKAN portal to prime the data.
        """
        with patch('bdkd.datastore.Repository', return_value=single_dataset_repo) as mock_repo:
            from mock import mock_open
            open_name = '%s.open' % '__builtin__'
            with patch(open_name, create=True):
                good_primer.prime_portal(repo_name='test_bucket')
                mock_ds_host.assert_called_once_with(host='test_ds_host') # connects to the right host
                assert mock_repo.call_args[0][1] == 'test_bucket'         # connects to the right repo
                mock_ckanapi.assert_called_once_with('test_ckan_url', apikey='test-key') # connects to the right CKAN


    @patch('ckanapi.RemoteCKAN')
    def test_resource_write(self, mock_ckanapi, single_dataset_repo, good_primer):
        with patch('bdkd.datastore.Repository', return_value=single_dataset_repo):
            # Check that writes were done to the manifest.
            with patch('__builtin__.open', create=True) as mock_open:
                mock_open.return_value = MagicMock(spec=file)
                mock_write = mock_open.return_value.write
                # Execute the priming using the mocks.
                good_primer.prime_portal(repo_name='test_bucket')
                mock_write.assert_has_calls([
                    call('s3://test_bucket/groupA/groupAA/dataset1/file1\n'),
                    call('http://remotefile.internet/file2\n'),
                    ])


    @patch('ckanapi.RemoteCKAN')
    @patch('bdkd.datastore.Repository')
    @patch('__builtin__.open', create=True)
    def test_visualization(self, mock_open, mock_repo, mock_ckanapi, single_dataset_repo, good_primer):
        # The single dataset repo provides a single dataset of data type 'ocean data'.
        # The configuration states that for ocean data, visualization should point to
        # 'http://ocean.site/{repo_name}/{dataset_name}
        mock_site = mock_ckanapi.return_value
        mock_repo.return_value = single_dataset_repo

        good_primer.prime_portal(repo_name='test_bucket')

        # Check that a visualization resource was created.
        mock_site.action.resource_create.assert_has_calls([
            call(url='http://ocean.site/test_bucket/groupA%2FgroupAA%2Fdataset1',
                 package_id='groupa-groupaa-dataset1',
                 description='Explore the dataset',
                 name='explore',
                 format='html')],
            any_order=True)


    """
    Other possible unit tests:
    def test_temp_dirs_cleaned_up(self):
    def test_prime_repository_bad(self):
    def test_prime_all_repositories_ok(self):
    def test_setup_organization_ok(self):
    def test_setup_organizations_bad(self):
    """
