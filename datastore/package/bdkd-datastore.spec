# EL6-compatible Python macros (see /usr/lib/rpm/macros.python)
%define py_ver         %(echo `python -c "import sys; sys.stdout.write(sys.version[:3])"`)
%define py_prefix      %(echo `python -c "import sys; sys.stdout.write(sys.prefix)"`)
%define py_libdir      %{py_prefix}/lib/python%{py_ver}
%define py_sitedir     %{py_libdir}/site-packages

%define name		bdkd-datastore
%define version		0.0.1
%define release		<<BUILD_NUMBER>>%{?dist}

Name:		%{name}
Version:	%{version}
Release:	%{release}
Summary: 	Storage of file-like objects to a S3-compatible repository

Group:		Development/Libraries
License: 	Python
URL:		https://github.com/sirca/bdkd/archive/master.zip

Source0: 	https://github.com/sirca/bdkd.git
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root
BuildArch:      noarch

Requires:	python-boto, python-yaml

%description
The BDKD Datastore provides for the storage of file-like objects to a 
S3-compatible repository (Amazon or OpenStack Swift) including local caching.


%prep
mkdir -p $RPM_BUILD_DIR/%{name}
rm -rf $RPM_BUILD_DIR/%{name}/*
cp -a $RPM_SOURCE_DIR/%{name}/files/* $RPM_BUILD_DIR/%{name}


%build


%install
cp -a $RPM_BUILD_DIR/%{name}/ $RPM_BUILD_ROOT


%clean
rm -rf $RPM_BUILD_ROOT


%post
touch %{py_sitedir}/bdkd/__init__.py


%files
%defattr(-,root,root,-)
%doc $RPM_SOURCE_DIR/%{name}/doc/*
%{py_sitedir}/bdkd/datastore.py*
/usr/bin/datastore-*


%changelog
* Fri Oct 18 2013 David Nelson <david.nelson@sirca.org.au> - 0.0.1
- Initial configuration
