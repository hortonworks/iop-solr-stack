# IOP Solr service for Ambari

## Generate IOP Solr mpack from source code
Download iop-solr-stack repository from git then run:
```bash
cd iop-solr-stack
./gradlew clean buildTar -Pversion=1.0.0 # addition options: -PpackageName=... and -Prepoid=...
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
