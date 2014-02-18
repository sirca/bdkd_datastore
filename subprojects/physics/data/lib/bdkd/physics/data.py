import bdkd.datastore, h5py, re


class Dataset(object):

    def __init__(self, name, resource):
        self.name = name
        self.resource = resource
        self.shard_size = resource.metadata.get('shard-size', None)
        self.shards = {}
        self.maps = None
        shard_name_re = re.compile(r".*FB_(\d+)_INJ_(\d+)_(\d+)\.hdf5$")
        maps_name_re = re.compile(r".*maps.hdf5$")
        for rfile in resource.files:
            match = shard_name_re.match(rfile.location_or_remote())
            if match:
                fb = int(match.group(1))
                inj = int(match.group(2))
                if not self.shard_size:
                    self.shard_size = int(m.group(3))
                self.shards[(fb, inj)] = rfile
            elif maps_name_re.match(rfile.location_or_remote()):
                self.maps = rfile
    

    @classmethod
    def open(cls, repo_name, resource_name):
        repository = bdkd.datastore.repository(repo_name)
        if repository:
            resource = repository.get(resource_name)
            if resource:
                return cls(resource_name, resource)
        return None


    def get_map_names(self):
        """
        Get the names of all available maps from the maps file.

        If there is no maps file, returns None.
        """
        if not self.maps:
            return None
        map_file = h5py.File(self.maps.local_path(), 'r')
        names = map_file.keys()
        map_file.close()
        return names


    def get_map_data(self, map_name):
        """
        Get the map (array of floats) for the given map name.

        If the map doesn't exist, return None.
        """
        if not self.maps:
            return None
        map_file = h5py.File(self.maps.local_path(), 'r')
        data = None
        if map_name in map_file:
            data = map_file[map_name][()]
        map_file.close()
        return data

        filename = self.get_map_filename()
        if filename:
            pass
        else:
            return None
        
    def get_time_series(self, feedback, injection):
        """
        Get the time series (array of floats) for the given combination of feedback and injection.

        If the time series doesn't exist, return None.
        """
        fb_shard = int(feedback / self.shard_size) * self.shard_size
        inj_shard = int(injection / self.shard_size) * self.shard_size
        data = None
        if (fb_shard, inj_shard) in self.shards:
            shard_file = h5py.File(
                    self.shards[(fb_shard, inj_shard)].local_path(), 'r')
            time_series_name = "FB_{0:03d}_INJ_{1:03d}.csv".format(
                    feedback, injection)
            if time_series_name in shard_file:
                data = shard_file[time_series_name][()]
            shard_file.close()
        return data

