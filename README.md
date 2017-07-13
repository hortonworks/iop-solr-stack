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
ambari-server install-mpack --mpack=/my-path/iop-solr-service-mpack-1.0.0.tar.gz --verbose
```

Start Ambari Server
```bash
ambari-server start
```