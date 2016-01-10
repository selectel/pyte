%define debug_package %{nil}

Summary:    	Simple VTXXX-compatible terminal emulator
Name:	    	python26-pyte
Version:    	0.5.1
Release:    	1.selectel%{?dist}
Vendor:	    	Selectel
License:    	LGPL
Group:	    	Development/Libraries/Python
URL:            https://github.com/selectel/pyte
Source0:        http://pypi.python.org/packages/source/p/pyte/pyte-%{version}.tar.gz
Requires:       python26 python26-wcwidth
BuildRequires:  python26-setuptools
BuildRoot:      %{_tmppath}/pyte-%{version}-%{release}-root-%(%{__id_u} -n)

%description
What is pyte? It's an in memory VTXXX-compatible terminal emulator.
*XXX* stands for a series video terminals, developed by
DEC between 1970 and 1995. The first, and probably the most
famous one, was VT100 terminal, which is now a de-facto standard
for all virtual terminal emulators. Pyte follows the suit.

%prep
%setup -q -n pyte-%{version}

%build
/usr/bin/python2.6 setup.py build

%install
/usr/bin/python2.6 setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf %{buildroot}

%files -f INSTALLED_FILES
%doc AUTHORS
%doc CHANGES
%doc LICENSE
%doc README
%defattr(-,root,root,-)

%changelog
* Sun Jan 10 2015 Sergei Leebdev <superbobry@gmail.com>
- Added wcwidth to requirements
* Thu Sep 1 2011  Fedor Gogolev <knsd@knsd.net>
- Initial packaging for CentOS
