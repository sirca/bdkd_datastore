:
if [ $# -lt 1 ]
then
  echo "Usage: $0 <dataset_name>"
  exit 1
fi

cd /usr/lib/ckan/default/src
paster dataset purge $1 -c /etc/ckan/default/production.ini
