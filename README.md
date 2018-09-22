# IOP Solr service for Ambari

## IOP Solr - Ambari MPack Matrix

MPack version | Solr version | Ambari version
--- | --- | --- 
1.0.0.0 | 6.3.0 | 2.5.x - 2.6.x 
1.0.0.1 | 6.6.5 | 2.5.x - 2.6.x 
1.0.1.0 | 6.3.0 | 2.7.x 
1.0.1.1 | 6.6.5 | 2.7.x 

## Generate IOP Solr mpack from source code
Download iop-solr-stack repository from git then run:
```bash
cd iop-solr-stack
./gradlew clean buildTar -Pversion=1.0.0 # addition option: -PpackageName=...
```

## Install IOP Solr mpack

Stop Ambari Server:
```bash
ambari-server stop
```

Install Solr mpack:
```bash
ambari-server install-mpack --mpack=/my-path/iop-solr-mpack-1.0.0.tar.gz --verbose
```

Start Ambari Server
```bash
ambari-server start
```

## Build Solr 6.3.0 RPM/DEB package
```bash
cd iop-solr-stack
# rpm build:
# note: generated rpm file: build/distributions/iop-solr-6.3.0.2.6.0.0-15.noarch.rpm, package name: iop-solr
./gradlew clean rpm -PstackVersion=2.6.0.0 -PstackBuildNumber=15
# deb build:
# note: generated deb file: build/distributions/iop-solr_6.3.0-2.6.0.0-15_all.deb, package name: iop-solr
./gradlew clean deb -PstackVersion=2.6.0.0 -PstackBuildNumber=15

# Example of install:
# note: files will be extracted to /usr/hdp/2.6.0.0-15/iop-solr folder
yum install -y iop-solr-6.3.0.2.6.0.0-15.noarch.rpm
```

## Notes about properties
```bash
-Pversion=.. # mpack version
-PsolrVersion=.. # solr version
-PsolrTar=.. # solr tar.gz location (can be local with file:// prefix)
-PrepoCentos6BaseUrl=.. -PrepoCentos7BaseUrl=.. # repo url for solr rpm, it will be used in repoinfo.xml file
-Prepoid=.. # that is placed to repoinfo.xml as a repoid
-PstackFolder=.. # package will be unpackaged into that location
```

## Upgrade from an earlier version (e.g. 1.0.0.0 to 1.0.1.0)

Stop ambari-server
```bash
ambari-server stop
```

Upgrade mpack:
```bash
# centos7
ambari-server upgrade-mpack \
--mpack=http://s3.amazonaws.com/dev.hortonworks.com/IOPSOLR/centos7/1.x/BUILDS/1.0.1.0-5/tars/iopsolr/iop-solr-mpack-6.3.0.1.0.1.0-5.tar.gz

# centos 6
ambari-server upgrade-mpack \
--mpack=http://s3.amazonaws.com/dev.hortonworks.com/IOPSOLR/centos6/1.x/BUILDS/1.0.1.0-5/tars/iopsolr/iop-solr-mpack-6.3.0.1.0.1.0-5.tar.gz
```

Start ambari-server
```bash
ambari-server start
```

Run the following on Solr server hosts:
```bash
# centos 7
wget -O /etc/yum.repos.d/iopsolr.repo http://s3.amazonaws.com/dev.hortonworks.com/IOPSOLR/centos7/1.x/BUILDS/1.0.1.0-5/iopsolr_public.repo # if the old repo name was iopsolr.repo
# centos 6
wget -O /etc/yum.repos.d/iopsolr.repo http://s3.amazonaws.com/dev.hortonworks.com/IOPSOLR/centos6/1.x/BUILDS/1.0.1.0-5/iopsolr_public.repo # if the old repo name was iopsolr.repo
yum clean all
yum upgrade iop-solr
```

Then restart IOP Solr instances
