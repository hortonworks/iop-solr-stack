#!/usr/bin/env python

"""
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import solr_cli

from resource_management.core.exceptions import Fail
from resource_management.core.logger import Logger
from resource_management.core.resources.system import Execute
from resource_management.libraries.functions.decorator import retry
from resource_management.libraries.functions.format import format

def create_solr_api_request_command(request_path, output=None):
  import params
  solr_protocol = 'https' if params.solr_ssl_enabled else 'http'
  solr_base_url = format("{solr_protocol}://{hostname_lowercase}:{solr_port}/solr")
  solr_url = format("{solr_base_url}/{request_path}")
  grep_cmd = " | grep 'solr_rs_status: 200'"
  api_cmd = format("kinit -kt {solr_kerberos_keytab} {solr_kerberos_principal} && curl -w'solr_rs_status: %{{http_code}}' -k --negotiate -u : '{solr_url}'") \
    if params.security_enabled else format("curl -w'solr_rs_status: %{{http_code}}' -k '{solr_url}'")
  if output is not None:
    api_cmd+=format(" -o {output}")
  api_cmd+=grep_cmd
  return api_cmd

@retry(times=30, sleep_time=10, err_class=Fail)
def create_collection(collection_name, config_name, shards=2, replicas=2, required_nodes=0):
  import params
  if solr_cli.is_node_exists(format("/collections/{collection_name}")):
    Logger.info(format("Collection '{collection_name}' already exists."))
  else:
    solr_cli.wait_for_live_nodes_before_collection_creation(required_nodes)
    maxShardsPerNode = int(shards) * int(replicas)
    collection_request = format('admin/collections?action=CREATE&name={collection_name}&collection.configName={config_name}&numShards={shards}&replicationFactor={replicas}&maxShardsPerNode={maxShardsPerNode}&wt=json')
    solr_api_cmd = create_solr_api_request_command(collection_request)
    Execute(solr_api_cmd, user=params.solr_user)