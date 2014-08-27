import bdkd.datastore
import h5py


class Dataset(object):
    META_MAPS='maps'
    META_RAW_ALL='raw_all'
    META_SHARD_SIZE='shard_size'
    META_README='readme'

    META_X_NAME='x_name'
    META_X_SIZE='x_size'
    META_X_VARIABLES='x_variables'

    META_Y_NAME='y_name'
    META_Y_SIZE='y_size'
    META_Y_VARIABLES='y_variables'

    META_Z_NAME='z_name'
    META_Z_SIZE='z_size'
    META_Z_INTERVAL_BASE='z_interval_base'
    META_Z_INTERVAL_EXPONENT='z_interval_exponent'

    META_Z_PEAK_VOLTAGE='z_peak_voltage'

    META_REQUIRED_FIELDS=[
            META_MAPS,
            META_RAW_ALL,
            META_SHARD_SIZE,
            META_README,
            META_X_NAME,
            META_X_SIZE,
            META_X_VARIABLES,
            META_Y_NAME,
            META_Y_SIZE,
            META_Y_VARIABLES,
            META_Z_NAME,
            META_Z_SIZE,
            META_Z_INTERVAL_BASE,
            META_Z_INTERVAL_EXPONENT,
            META_Z_PEAK_VOLTAGE,
            ]


    @classmethod
    def validate(cls, resource):
        """
        Verifies that the given resource is valid for use as a laser dataset.

        Not any old resource can be used as a source of laser data: a number of 
        meta-data fields in particular need to be provided.  This method will 
        throw ValueError if something's wrong.
        """
        # Required meta-data fields
        for required_field in cls.META_REQUIRED_FIELDS:
            if not resource.meta(required_field):
                raise ValueError("Required meta-data field '{0}' absent"
                        .format(required_field))

        # Check the README file
        readme_filename = resource.meta(Dataset.META_README)
        readme_file = resource.file_ending(readme_filename)
        if not readme_file:
            raise ValueError("README file name '{0}' doesn't refer to a file"
                    .format(readme_filename))

        # Check the maps file, including its contents (X and Y variables)
        maps_filename = resource.meta(Dataset.META_MAPS)
        maps_file = resource.file_ending(maps_filename)
        if not maps_file:
            raise ValueError("Maps file name '{0}' doesn't refer to a file"
                    .format(maps_filename))
        else:
            # Check that the X and Y variables are available in the maps file
            maps = h5py.File(maps_file.local_path(), 'r')
            if not maps.get(resource.meta(Dataset.META_X_VARIABLES)):
                raise ValueError("Maps file does not contain X variables '{0}'"
                        .format(resource.meta(Dataset.META_X_VARIABLES)))
            if not maps.get(resource.meta(Dataset.META_Y_VARIABLES)):
                raise ValueError("Maps file does not contain Y variables '{0}'"
                        .format(resource.meta(Dataset.META_Y_VARIABLES)))
            maps.close()


    @classmethod
    def list(cls, repo_name, prefix=''):
        repository = bdkd.datastore.repository(repo_name)
        if repository:
            return repository.list(prefix)
        else:
            return None


    @classmethod
    def open(cls, repo_name, resource_name):
        repository = bdkd.datastore.repository(repo_name)
        if repository:
            resource = repository.get(resource_name)
            if resource:
                return cls(resource_name, resource)
        return None


    def _map_shard_files(self):
        """
        Map the raw shard files by (X,Y) to facilitate lookup.
        """
        self.shards = dict()
        for shard_file in self.resource.files_matching(r'shard'):
            x = shard_file.metadata.get('x_index_min', None)
            y = shard_file.metadata.get('y_index_min', None)
            if x != None and y != None:
                self.shards[(x, y)] = shard_file


    def __init__(self, name, resource):
        type(self).validate(resource)
        # Expose all mandatory fields as attributes
        for attr_name in type(self).META_REQUIRED_FIELDS:
            setattr(self, attr_name, resource.metadata.get(attr_name))
        # Other convenience
        setattr(self, 'z_interval', 
                self.z_interval_base * self.z_interval_exponent)
        self.name = name
        self.resource = resource
        self._map_shard_files()


    def get_map_names(self, include_variables=True):
        """
        Get the names of all available maps from the maps file.

        If there is no maps file, returns None.
        """
        if not self.maps:
            return None
        maps_file = self.resource.file_ending(self.maps)
        maps = h5py.File(maps_file.local_path(), 'r')
        map_names = []
        for name, data in maps.iteritems():
            map_type = data.attrs.get('type', None)
            if map_type:
                if map_type.endswith('variables') and not include_variables:
                    pass
                else:
                    map_names.append(name)
            else:
                map_names.append(name)
        maps.close()
        return map_names


    def get_map_data(self, map_name):
        """
        Get the map (array of floats) for the given map name.

        If the map doesn't exist, return None.
        """
        if not self.maps:
            return None
        maps_file = self.resource.file_ending(self.maps)
        maps = h5py.File(maps_file.local_path(), 'r')
        data = None
        if map_name in maps:
            data = maps[map_name][()]
        maps.close()
        return data
        

    def get_x_variables(self):
        return self.get_map_data(self.x_variables)


    def get_y_variables(self):
        return self.get_map_data(self.y_variables)


    def get_map_and_variables_data(self, map_name):
        map_data = self.get_map_data(map_name)
        x_variables = self.get_x_variables()
        y_variables = self.get_y_variables()
        if map_data != None and x_variables != None and y_variables != None:
            print map_data
            data = []
            for x in range(len(map_data)):
                row = map_data[x]
                for y in range(len(row)):
                    value = row[y]
                    data.append(dict(
                        x_index=x,
                        y_index=y,
                        x_variable=x_variables[x][y],
                        y_variable=y_variables[x][y],
                        value=value
                        ))
            return data
        else:
            return None


    def get_time_series(self, x, y):
        x_shard = int(x / self.shard_size) * self.shard_size
        y_shard = int(y / self.shard_size) * self.shard_size
        data = None
        if (x_shard, y_shard) in self.shards:
            shard_file = self.shards[(x_shard,y_shard)]
            shard = h5py.File(shard_file.local_path(), 'r')
            for (name, dataset) in shard.iteritems():
                x_index = dataset.attrs.get('x_index', None)
                y_index = dataset.attrs.get('y_index', None)
                if (x_index == x and y_index == y):
                    data = dataset[()]
                    break
            shard.close()
        return data


    def get_readme(self):
        """
        Gets the README text for the dataset.

        If no README file is available, returns None.
        """
        readme_text = None
        if not self.readme:
            return None
        readme_file = self.resource.file_ending(self.readme)
        if readme_file:
            with open (readme_file.local_path(), 'r') as fh:
                readme_text = fh.read()
        return readme_text
