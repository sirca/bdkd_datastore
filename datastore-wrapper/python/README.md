# Python wrapper for datastore

Note that this assumes that the bdkd-datastore package is installed and available.

This library uses the locally datastore-util command line tool to obtain data from Datastore.

Example code:

```python
import datastorewrapper

datastorewrapper.configure_datastore(my_config)
datastore = datastorewrapper.Datastore()

repos = datastore.list('my-repo')

print "\n".join(repos)

```
