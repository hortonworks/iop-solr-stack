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
import socket
from resource_management.core.exceptions import Fail
from resource_management.core.logger import Logger
from resource_management.core.resources.system import Execute
from resource_management.core.shell import call
from resource_management.libraries.functions.decorator import retry
from resource_management.libraries.functions.format import format

def get_node_data(node_to_check, root=False):
  import params
  cmd = format('{zkcli_root_prefix} get {solr_znode}{node_to_check}') if root else format('{zkcli_prefix} get {node_to_check}')
  code, output = call(
    cmd,
    user=params.solr_user,
    timeout=60,
    quiet=True
  )
  return code, output

def is_node_exists(node_to_check, root=False):
  import params
  code, output = get_node_data(node_to_check, root)
  if not ("NoNodeException" in output):
    return True
  return False

@retry(times=30, sleep_time=10, err_class=Fail)
def create_znode():
  import params

  clusterstate_json_exists = is_node_exists("/clusterstate.json", root=True)

  if clusterstate_json_exists:
    Logger.info(format("ZNode '{solr_znode}/clusterstate.json' already exists, skipping ..."))
    return

  Execute(format('{zkcli_root_prefix} makepath {solr_znode}'),
          user=params.solr_user,
          logoutput=True
          )

def set_url_scheme():
  import params
  url_scheme = 'https' if params.solr_ssl_enabled else 'http'
  Execute(format('{zkcli_prefix} clusterprop -name urlScheme -val {url_scheme}'),
          user=params.solr_user,
          logoutput=True
          )

def upload_configs(config_name, config_dir):
  import params
  solrconfig_xml_exists = is_node_exists(format("/configs/{config_name}/solrconfig.xml"))
  if solrconfig_xml_exists:
    Logger.info(format("Config '{config_name}' already exists, upgrades only the solrconfig.xml"))
    Execute(format('{zkcli_prefix} putfile /configs/{config_name}/solrconfig.xml {config_dir}/solrconfig.xml'),
            user=params.solr_user,
            logoutput=True
            )
  else:
    Logger.info(format("Config '{config_name}' does not exist, creating it ..."))
    Execute(format('{zkcli_prefix} upconfig -confdir {config_dir} -confname {config_name}'),
            user=params.solr_user,
            logoutput=True
            )

@retry(times=30, sleep_time=10, err_class=Fail)
def wait_for_live_nodes_before_collection_creation(required_nodes):
  import params
  if int(required_nodes) > 0:
    code, output = call(
      format('{zkcli_prefix} ls /live_nodes'),
      user=params.solr_user,
      timeout=60,
      quiet=True
    )
    if code == 0:
      if not ("NoNodeException" in output):
        line_splitted = output.split('\n')
        if len(line_splitted) > 1:
          live_nodes_number = len(line_splitted) - 1
          if live_nodes_number >= int(required_nodes):
            Logger.info(format("Number of live nodes {live_nodes_number}, required: {required_nodes}. passing ..."))
          else:
            raise Fail(format("Number of live nodes for creating a collection is {live_nodes_number}, required: {required_nodes} "))
        else:
          raise Fail('No live nodes yet.')
      else:
        raise Fail('Znode /live_nodes does not exist.')
    else:
      raise Fail(format("List /live_nodes failed: {output}"))
  else:
    Logger.info("It is not required to wait /live_nodes as 'solr-env/solr_wait_for_live_nodes' is less or equal 0.'")

def is_ip(addr):
  try:
    socket.inet_aton(addr)
    return True
  except socket.error:
    return False

def resolve_ip_to_hostname(ip):
  try:
    host_name = socket.gethostbyaddr(ip)[0].lower()
    Logger.info(format("Resolved {ip} to {host_name}"))
    fqdn_name = socket.getaddrinfo(host_name, 0, 0, 0, 0, socket.AI_CANONNAME)[0][3].lower()
    return host_name if host_name == fqdn_name else fqdn_name
  except socket.error:
    pass
  return ip

def get_local_cores(collection):
  import json
  import params

  cores = []
  if is_node_exists(format("/collections/{collection}/state.json")):
    code, state_json_content = get_node_data(format("/collections/{collection}/state.json"))
    state_json = json.loads(state_json_content)
    collection_data = state_json[collection]
    shards = collection_data['shards']
    for shard in shards:
      replicas = shards[shard]['replicas']
      for replica in replicas:
        core_data = replicas[replica]
        node_name = core_data['node_name']
        host = node_name.split(":")[0]
        hostname = host.lower()
        if is_ip(host):
          hostname = resolve_ip_to_hostname(host).lower()
        if hostname == params.hostname_lowercase:
          Logger.info(format("Found core '{replica}' for collection {collection} on host {hostname}"))
          cores.append(replica)
  return cores
