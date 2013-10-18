%define name		bdkd-datastore
%define version		0.0.1
%define release		1%{?dist}

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

BuildRequires:	python-nose
BuildRequires:	python-sphinx


%description
The BDKD Datastore provides for the storage of file-like objects to a 
S3-compatible repository (Amazon or OpenStack Swift) including local caching.


%prep
mkdir -p $RPM_BUILD_DIR/%{name}
rm -rf $RPM_BUILD_DIR/%{name}/*
cp -a $RPM_SOURCE_DIR/%{name}/files/* $RPM_BUILD_DIR/%{name}


%build


%install
cp -a $RPM_BUILD_DIR/%{name}/* $RPM_BUILD_ROOT


%clean
rm -rf $RPM_BUILD_ROOT


%post
touch %{_python_sitelib}/bdkd/__init__.py


%files
%defattr(-,root,root,-)
%doc $RPM_SOURCE_DIR/%{name}/doc/*
%{_python_sitelib}/bdkd/datastore.py*


%changelog
* Fri Oct 18 2013 David Nelson <david.nelson@sirca.org.au> - 0.0.1
- Initial configuration
