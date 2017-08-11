#!/usr/bin/env python

'''
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
'''
import sys
import urllib2
import json
import base64
import optparse

HTTP_PROTOCOL = 'http'
HTTPS_PROTOCOL = 'https'

SOLR_SERVICE_NAME = 'SOLR'

SOLR_COMPONENT_NAME ='SOLR'

CLUSTERS_URL = '/api/v1/clusters/{0}'

CONFIG_BACKUP_FILE = '/SOLR-backup-configs.json'
HOST_BACKUP_FILE = '/SOLR-backup-hosts.json'
STACK_DEFAULTS_FILE = '/SOLR-HDP-2.6-defaults.json'

SOLR_CONFIG_FILE = '/config-SOLR-{0}.json'

BACKUP_CONFIGS_URL = '/configurations/service_config_versions?service_name={0}&is_current=true'
BACKUP_HOSTS_URL = '/services/{0}/components/{1}?fields=host_components'

ADD_SERVICE_URL = '/services/{0}'
ADD_COMPONENT_URL = '/services/{0}/components/{1}'

ADD_HOST_COMPONENT_URL = '/hosts/{0}/host_components/{1}'

STACK_CONFIG_DEFAULTS_URL = '/api/v1/stacks/HDP/versions/2.6/services/{0}/configurations?fields=StackConfigurations/type,StackConfigurations/property_value'

CREATE_CONFIGURATIONS_URL = '/configurations'

def api_accessor(host, username, password, protocol, port):
  def do_request(api_url, request_type, request_body=''):
    try:
      url = '{0}://{1}:{2}{3}'.format(protocol, host, port, api_url)
      print 'Execute {0} {1}'.format(request_type, url)
      if request_body:
        print 'Request body: {0}'.format(request_body)
      admin_auth = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
      request = urllib2.Request(url)
      request.add_header('Authorization', 'Basic %s' % admin_auth)
      request.add_header('X-Requested-By', 'ambari')
      request.add_data(request_body)
      request.get_method = lambda: request_type
      response = urllib2.urlopen(request)
      response_body = response.read()
    except Exception as exc:
      raise Exception('Problem with accessing api. Reason: {0}'.format(exc))
    return response_body
  return do_request

def format_json(dictionary, tab_level=0):
  output = ''
  tab = ' ' * 2 * tab_level
  for key, value in dictionary.iteritems():
    output += ',\n{0}"{1}": '.format(tab, key)
    if isinstance(value, dict):
      output += '{\n' + format_json(value, tab_level + 1) + tab + '}'
    else:
      output += '"{0}"'.format(value)
  output += '\n'
  return output[2:]

def output_to_file(filename, jsonStr):
  with open(filename, 'w') as out_file:
    out_file.write(json.dumps(jsonStr, sort_keys=True, indent=2, separators=(',', ': ')))

def read_json(json_file):
  with open(json_file) as data_file:
    data = json.load(data_file)
  return data

def get_json(accessor, url):
  response = accessor(url, 'GET')
  json_resp = json.loads(response)
  return json_resp

def process_to_file(options, accessor, url, filename):
  jsons_to_store = get_json(accessor, url)
  output_to_file(options.backup_location + filename, jsons_to_store)

def add_secrets(merged_properties, ranger_solr_secrets):
  for secret_config_type in ranger_solr_secrets:
    if secret_config_type in merged_properties:
      for secret_property in ranger_solr_secrets[secret_config_type]:
        if secret_property in merged_properties[secret_config_type]:
          print 'Applying secret property {0}/{1}.'.format(secret_config_type, secret_property)
          merged_properties[secret_config_type][secret_property] = ranger_solr_secrets[secret_config_type][secret_property]
  return merged_properties

def apply_solr_site_configs(merged_properties, old_properties):
  '''
  Apply old solr-site properties (from IOP 4.2.5 and HDP 2.6 solr-site does not exist)
  '''
  if 'solr-site' in old_properties:
    if 'solr.hdfs.security.kerberos.keytabfile' in old_properties['solr-site']:
      merged_properties['solr-env']['solr_kerberos_keytab'] = \
        old_properties['solr-site']['solr.hdfs.security.kerberos.keytabfile']
      print 'Transfer old solr-site/solr.hdfs.security.kerberos.keytabfile proeprty to solr-env/solr_kerberos_keytab.'
    if 'solr.hdfs.security.kerberos.principal' in old_properties['solr-site']:
      merged_properties['solr-env']['solr_kerberos_principal'] = \
        old_properties['solr-site']['solr.hdfs.security.kerberos.principal']
      print 'Transfer old solr-site/solr.hdfs.security.kerberos.principal proeprty to solr-env/solr_kerberos_principal.'
  return merged_properties

def create_host_components(options, accessor, old_solr_hosts):
  for old_solr_host in old_solr_hosts:
    accessor(CLUSTERS_URL.format(options.cluster) + ADD_HOST_COMPONENT_URL.format(old_solr_host, SOLR_COMPONENT_NAME), 'POST')

def get_component_hosts(backup_hosts):
  hosts = []
  if "host_components" in backup_hosts and len(backup_hosts['host_components']) > 0:
    for host_component in backup_hosts['host_components']:
      if 'HostRoles' in host_component:
        hosts.append(host_component['HostRoles']['host_name'])
  return hosts

def apply_configs(options, accessor, configs):
  for config in configs:
    configs[config].pop("properties", None)
    post_configs = {}
    post_configs[config] = configs[config]
    desired_configs_post_body = {}
    desired_configs_post_body["Clusters"] = {}
    desired_configs_post_body["Clusters"]["desired_configs"] = post_configs
    accessor(CLUSTERS_URL.format(options.cluster), 'PUT', json.dumps(desired_configs_post_body))


def create_configs(options, accessor, merged_properties, tag):
  configs_for_posts = {}
  for config_type in merged_properties:
    config = {}
    config['type'] = config_type
    config['tag'] = tag
    config['properties'] = merged_properties[config_type]
    configs_for_posts[config_type] = config
    output_to_file(options.backup_location + SOLR_CONFIG_FILE.format(config_type), config)
    accessor(CLUSTERS_URL.format(options.cluster) + CREATE_CONFIGURATIONS_URL, 'POST', json.dumps(config))
  return configs_for_posts

def merge_properties(old_properties, stack_default_properties):
  new_properties = {}
  print 'Processing new properties...'
  for new_properties_config_type in stack_default_properties:
    if new_properties_config_type in old_properties:
      for old_config in old_properties[new_properties_config_type]:
        if old_config in stack_default_properties[new_properties_config_type] \
          and stack_default_properties[new_properties_config_type][old_config] != \
          old_properties[new_properties_config_type][old_config]:
          print 'Override {0}/{1} property from the backup.'.format(new_properties_config_type, old_config)
          stack_default_properties[new_properties_config_type][old_config] = old_properties[new_properties_config_type][old_config]
    new_properties[new_properties_config_type] = stack_default_properties[new_properties_config_type]
  return new_properties

def get_old_properties(backup_configs):
  properties = {}
  if 'items' in backup_configs and len(backup_configs['items']) > 0:
    if 'configurations' in backup_configs['items'][0]:
      for config in backup_configs['items'][0]['configurations']:
        properties[config['type']] = config['properties']
  return properties

def get_stack_default_properties(stack_default_properties_json):
  stack_default_properties = {}
  if 'items' in stack_default_properties_json and len(stack_default_properties_json['items']) > 0:
    for stack_properties in stack_default_properties_json['items']:
      if 'StackConfigurations' in stack_properties:
        first_stack_props = stack_properties['StackConfigurations']
        config_type = first_stack_props['type'].replace('.xml','')
        if config_type not in stack_default_properties:
          stack_default_properties[config_type] = {}

        stack_default_properties[config_type][first_stack_props['property_name']] = first_stack_props['property_value']

  return stack_default_properties

def check_cluster_option(options, parser):
  if not options.cluster:
    parser.print_help()
    print 'cluster option is required'
    sys.exit(1)

def backup(options, accessor, parser):
  '''
  Backup old configs and hosts to a specific folder
  '''
  if not options.backup_location:
    parser.print_help()
    print 'backup-location option is required'
    sys.exit(1)

  check_cluster_option(options, parser)

  process_to_file(options, accessor, CLUSTERS_URL.format(options.cluster) + BACKUP_CONFIGS_URL.format(SOLR_SERVICE_NAME), CONFIG_BACKUP_FILE)
  process_to_file(options, accessor, CLUSTERS_URL.format(options.cluster) + BACKUP_HOSTS_URL.format(SOLR_SERVICE_NAME, SOLR_COMPONENT_NAME), HOST_BACKUP_FILE)

def start_solr_service(options, accessor, parser):
  '''
    Start Solr service
    '''
  check_cluster_option(options, parser)

  start_solr_body = '{"RequestInfo": {"context" :"Start IOP Solr"}, "Body": {"ServiceInfo": {"state": "STARTED"}}}'
  accessor(CLUSTERS_URL.format(options.cluster) + ADD_SERVICE_URL.format(SOLR_SERVICE_NAME), 'PUT', start_solr_body)

def stop_solr_service(options, accessor, parser):
  '''
  Stop Solr service
  '''
  check_cluster_option(options, parser)

  stop_solr_body = '{"RequestInfo": {"context" :"Stop IOP Solr"}, "Body": {"ServiceInfo": {"state": "INSTALLED"}}}'
  accessor(CLUSTERS_URL.format(options.cluster) + ADD_SERVICE_URL.format(SOLR_SERVICE_NAME), 'PUT', stop_solr_body)

def install_solr_service(options, accessor, parser):
  '''
    Install Solr service
    '''
  check_cluster_option(options, parser)

  install_solr_body = '{"RequestInfo": {"context" :"Install IOP Solr"}, "Body": {"ServiceInfo": {"state": "INSTALLED"}}}'
  accessor(CLUSTERS_URL.format(options.cluster) + ADD_SERVICE_URL.format(SOLR_SERVICE_NAME), 'PUT', install_solr_body)

def remove_solr_service(options, accessor, parser):
  '''
    Remove Solr service
    '''
  check_cluster_option(options, parser)

  accessor(CLUSTERS_URL.format(options.cluster) + ADD_SERVICE_URL.format(SOLR_SERVICE_NAME), 'DELETE')

def configure_solr_service(options, accessor, parser):
  '''
  Configure new Solr host components used by a backup location:
  1. Create the new Solr service
  2. Create the new Solr component
  3. Get old properties from backup configs
  4. Merge the last one with the new properties (apply secrets and old solr-site configs if there is any)
  5. Create host components based on the backed up hosts
  '''
  if not options.ranger_solr_secrets:
    parser.print_help()
    print('ranger-solr-secrets option is required')
    sys.exit(1)
  if not options.backup_location:
    parser.print_help()
    print('backup-location option is required')
    sys.exit(1)

  ranger_solr_secrets = read_json(options.ranger_solr_secrets)
  backup_configs = read_json(options.backup_location + CONFIG_BACKUP_FILE)
  backup_hosts = read_json(options.backup_location + HOST_BACKUP_FILE)

  accessor(CLUSTERS_URL.format(options.cluster) + ADD_SERVICE_URL.format(SOLR_SERVICE_NAME), 'POST')
  accessor(CLUSTERS_URL.format(options.cluster) + ADD_COMPONENT_URL.format(SOLR_SERVICE_NAME, SOLR_COMPONENT_NAME), 'POST')

  stack_default_properties_json = get_json(accessor, STACK_CONFIG_DEFAULTS_URL.format(SOLR_SERVICE_NAME))
  output_to_file(options.backup_location + STACK_DEFAULTS_FILE, stack_default_properties_json)
  old_properties = get_old_properties(backup_configs)
  stack_default_properties = get_stack_default_properties(stack_default_properties_json)
  merged_properties = merge_properties(old_properties, stack_default_properties)
  merged_properties_with_secrets = add_secrets(merged_properties, ranger_solr_secrets)
  final_properties = apply_solr_site_configs(merged_properties_with_secrets, old_properties)
  print 'Processing new properties finished.'

  configs = create_configs(options, accessor, final_properties, options.tag)
  apply_configs(options, accessor, configs)

  old_solr_hosts = get_component_hosts(backup_hosts)
  create_host_components(options, accessor, old_solr_hosts)

if __name__=="__main__":
  parser = optparse.OptionParser("usage: %prog [options]")
  parser.add_option("-a", "--action", dest="action", type="string", help="backup | configure | install | start | stop | remove")
  parser.add_option("-H", "--host", dest="host", default="localhost", type="string", help="hostname for ambari server")
  parser.add_option("-P", "--port", dest="port", default=8080, type="int", help="port number for ambari server")
  parser.add_option("-c", "--cluster", dest="cluster", type="string", help="name cluster")
  parser.add_option("-s", "--ssl", dest="ssl", action="store_true", help="use if ambari server using https")
  parser.add_option("-u", "--username", dest="username", default="admin", type="string", help="username for accessing ambari server")
  parser.add_option("-p", "--password", dest="password", default="admin", type="string", help="password for accessing ambari server")
  parser.add_option("-l", "--backup-location", dest="backup_location", default="/tmp", type="string", help="input/output location of the backups")
  parser.add_option("-r", "--ranger-solr-secrets", dest="ranger_solr_secrets", default="secret_defaults.json", type="string", help="json file which contains secrets for ranger")
  parser.add_option("-t", "--tag", dest="tag", default="version12345", type="string", help="config tag for the new configurations")
  (options, args) = parser.parse_args()

  protocol = 'https' if options.ssl else 'http'

  accessor = api_accessor(options.host, options.username, options.password, protocol, options.port)

  print 'Inputs: ' + str(options)
  if options.action == 'backup':
    backup(options, accessor, parser)
  elif options.action == 'configure':
    configure_solr_service(options, accessor, parser)
  elif options.action == 'install':
    install_solr_service(options, accessor, parser)
  elif options.action == 'start':
    start_solr_service(options, accessor, parser)
  elif options.action == 'stop':
    stop_solr_service(options, accessor, parser)
  elif options.action == 'remove':
    remove_solr_service(options, accessor, parser)
  else:
    parser.print_help()
    print 'action option is wrong or missing'
