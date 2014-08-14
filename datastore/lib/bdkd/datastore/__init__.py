from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)

# This maintains the established "import bdkd.datastore" behaviour
from datastore import *
