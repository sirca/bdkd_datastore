#!/usr/bin/env bash

# Prepare BDKD Datastore files for RPM packaging

set -x

PACKAGE_NAME='bdkd-datastore'
RPMBUILD_DIR=~/rpmbuild
SOURCES_DIR=${RPMBUILD_DIR}/SOURCES
PACKAGE_DIR=${SOURCES_DIR}/${PACKAGE_NAME}
FILES_DIR=${PACKAGE_DIR}/files
DOC_DIR=${PACKAGE_DIR}/doc
SPECS_DIR=${RPMBUILD_DIR}/SPECS

PYTHON_SITE_PACKAGES=`/usr/bin/env python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())"`

mkdir -p ${PACKAGE_DIR}
rm -rf ${PACKAGE_DIR}/*

mkdir -p ${FILES_DIR}/${PYTHON_SITE_PACKAGES}/bdkd
cp lib/bdkd/datastore.py ${FILES_DIR}/${PYTHON_SITE_PACKAGES}/bdkd 

mkdir -p ${FILES_DIR}/usr/bin
cp bin/datastore-* ${FILES_DIR}/usr/bin

mkdir -p ${DOC_DIR}
cp -a doc/build/html ${DOC_DIR}

mkdir -p ${SPECS_DIR}
cp package/*.spec ${SPECS_DIR}
