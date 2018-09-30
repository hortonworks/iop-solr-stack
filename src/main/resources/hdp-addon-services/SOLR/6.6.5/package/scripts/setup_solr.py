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
import os
import solr_cli

from resource_management.core.exceptions import Fail
from resource_management.core.source import InlineTemplate, Template, StaticFile
from resource_management.core.resources.system import Directory, Execute, File
from resource_management.libraries.functions.format import format

def setup_solr(name = None):
  import params

  if name == 'server':
    params.HdfsResource(params.solr_hdfs_home_dir,
                         type="directory",
                         action="create_on_execute",
                         owner=params.solr_user,
                         mode=0755
                        )

    params.HdfsResource(None, action="execute")

    Directory([params.solr_log_dir, params.solr_piddir,
               params.solr_datadir, params.solr_data_resources_dir],
              mode=0755,
              cd_access='a',
              create_parents=True,
              owner=params.solr_user,
              group=params.user_group
              )

    Directory([params.solr_dir],
              mode=0755,
              cd_access='a',
              create_parents=True,
              recursive_ownership=True
              )

    Directory([params.solr_conf],
              mode=0755,
              cd_access='a',
              owner=params.solr_user,
              group=params.user_group,
              create_parents=True,
              recursive_ownership=True
              )

    File(params.solr_log,
         mode=0644,
         owner=params.solr_user,
         group=params.user_group,
         content=''
         )

    File(format("{solr_conf}/solr-env.sh"),
         content=InlineTemplate(params.solr_env_content),
         mode=0755,
         owner=params.solr_user,
         group=params.user_group
         )

    if params.solr_xml_content:
      File(format("{solr_datadir}/solr.xml"),
           content=InlineTemplate(params.solr_xml_content),
           owner=params.solr_user,
           group=params.user_group
           )

    File(format("{solr_conf}/log4j.properties"),
         content=InlineTemplate(params.solr_log4j_content),
         owner=params.solr_user,
         group=params.user_group
         )

    if params.security_enabled:
      File(format("{solr_jaas_file}"),
           content=Template("solr_jaas.conf.j2"),
           owner=params.solr_user)

    if os.path.exists(params.limits_conf_dir):
      File(os.path.join(params.limits_conf_dir, 'solr.conf'),
           owner='root',
           group='root',
           mode=0644,
           content=Template("solr.conf.j2")
           )

    if params.has_ranger_admin and params.atlas_solrconfig_content:
      File(format("{ranger_solr_conf}/solrconfig.xml"),
           content=InlineTemplate(params.ranger_solr_config_content),
           owner=params.solr_user,
           group=params.user_group,
           mode=0644
           )
    if params.has_atlas and params.atlas_solrconfig_content:
      File(format("{atlas_configs_dir}/solrconfig.xml"),
           content=InlineTemplate(params.atlas_solrconfig_content),
           owner=params.solr_user,
           group=params.user_group,
           mode=0644
           )

    solr_cli.create_znode()

  else :
    raise Fail('Neither client, nor server were selected to install.')