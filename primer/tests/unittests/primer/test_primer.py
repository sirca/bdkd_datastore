import pytest
from mock import Mock, patch, MagicMock, call
from primer.primer import Primer
import yaml

@pytest.fixture
def good_cfg():
    """ Provides a good configuration string.
    Keep updating this string as more config is added.
    """
    return """
        api_key: test-key
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

def create_primer_using_string_as_config(cfg_yaml_str):
    """ An easy way to create a Primer object and patch the
    loading of a config file by providing it a YAML string instead.
    """
    primer = Primer()
    cfg = yaml.load(cfg_yaml_str)
    with patch('os.path.exists', return_value=True):
        with patch('__builtin__.open'):
            with patch('yaml.load') as mock_yaml_load:
                mock_yaml_load.return_value = cfg
                primer.load_config('ignored')
    return primer


@pytest.fixture
def good_primer(good_cfg):
    # Provides a primer object that has a good configuration from good_cfg.
    return create_primer_using_string_as_config(good_cfg)


class TestPrimer:

    @patch('os.path.exists', return_value=True)
    def test_load_config_ok(self, mock_os_path_exists, good_cfg):
        """ Test the loading of a good primer configuration file.
        """
        primer = Primer()
        cfg_from_yaml = yaml.load(good_cfg) # For intercepting the loading
        with patch('yaml.load') as mock_yaml_load:
            mock_yaml_load.return_value = cfg_from_yaml

            # Test that load_config will attempt to open up the file
            with patch('__builtin__.open') as mock_open:
                primer.load_config('cfgfile_to_load')
                mock_open.assert_called_once_with('cfgfile_to_load')

        # Check that the good settings made it to the primer's configuration.
        mock_open.assert_called_once_with('cfgfile_to_load')
        assert primer._cfg['api_key'] == 'test-key'
        assert len(primer._cfg['repos']) == 1
        repo_cfg = primer._cfg['repos'][0]
        assert repo_cfg["bucket"]=='test_bucket'
        assert repo_cfg["org_name"]=='test_org_name'
        assert repo_cfg["org_title"]=='test_org_title'
        assert repo_cfg["ckan_url"]=='test_ckan_url'
        assert repo_cfg["ds_host"]=='test_ds_host'


    def test_load_config_bad(self):
        """ Test when the primer throws if config file is bad.
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
            primer = create_primer_using_string_as_config("""
                repos:
                    - bucket: test_bucket
                      org_name: test_org_name
                      org_title: test_org_title
                      ckan_url: test_ckan_url
                      ds_host: test_ds_host
                """)
            primer.prime_portal()

        with pytest.raises(Exception):
            primer = create_primer_using_string_as_config("""
                api_key: test-key
                """)
            primer.prime_portal()


    @patch('bdkd.datastore.Host')
    @patch('bdkd.datastore.Repository')
    @patch('ckanapi.RemoteCKAN')
    def test_prime_repository_ok(self, mock_ckanapi, mock_dsrepo, mock_dshost, good_primer):
        """ Test that given the good configuration, the primer is connected to the right things.
        """
        mock_dsrepo.list.return_value = ('repo1',)
        # Do the mock priming
        from mock import mock_open
        open_name = '%s.open' % '__builtin__'
        with patch(open_name, create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=file)
            good_primer.prime_portal(repo_name='test_bucket')
            # Check that it connects to the datastore at the right host using the right bucket.
            mock_dshost.assert_called_once_with(host='test_ds_host')
            assert mock_dsrepo.call_args[0][1] == 'test_bucket' # last call, 2nd param is bucket name
            # Check that connects to the correct CKAN with the right key
            mock_ckanapi.assert_called_once_with('test_ckan_url', apikey='test-key')


    @patch('bdkd.datastore.Host')
    @patch('bdkd.datastore.Repository')
    @patch('ckanapi.RemoteCKAN')
    def test_resource_write(self, mock_ckanapi, mock_Repository, mock_dshost, good_primer):
        # Mock a repository that contains a single dataset.
        # The dataset has 2 resources: 1 is a local file and other a remote file.
        datasets = [ 'groupA/groupAA/dataset1' ]
        mock_dsrepo = mock_Repository.return_value
        mock_dsrepo.list.return_value = datasets
        mock_resource = MagicMock()
        mock_resource_file1 = MagicMock()
        mock_resource_file1.location.return_value = 'groupA/groupAA/dataset1/file1'
        mock_resource_file2 = MagicMock()
        mock_resource_file2.location.return_value = None
        mock_resource_file2.remote.return_value = 'http://remotefile.internet/file2'
        mock_resource.files = [mock_resource_file1, mock_resource_file2]
        mock_dsrepo.get.return_value = mock_resource

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

    def mock_getmeta(self, key, default=None):
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


    @patch('bdkd.datastore.Host')
    @patch('bdkd.datastore.Repository')
    @patch('ckanapi.RemoteCKAN')
    def test_visualization(self, mock_ckanapi, mock_Repository, mock_dshost, good_primer):
        # Mock a repository that contains a single dataset of a 'ocean data'
        # and check that given that was configured to use site 'http://ocean.site'
        # an exploration link should be created for that dataset.
        datasets = [ 'oceanData/dataset1' ]
        mock_dsrepo = mock_Repository.return_value
        mock_dsrepo.list.return_value = datasets
        mock_resource = MagicMock()
        mock_dsrepo.get.return_value = mock_resource
        mock_resource.metadata.get = MagicMock(side_effect=self.mock_getmeta)

        with patch('__builtin__.open', create=True) as mock_open:
            # Execute the priming using the mocks.
            good_primer.prime_portal(repo_name='test_bucket')
            mock_site = mock_ckanapi.return_value
            mock_create = mock_site.action.resource_create
            mock_create.assert_has_calls([
                call(url='http://ocean.site/test_bucket/oceanData%2Fdataset1',
                     package_id='oceandata-dataset1',
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
