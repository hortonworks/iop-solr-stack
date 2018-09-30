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

from resource_management.core.shell import call
from resource_management.core.logger import Logger
from resource_management.libraries.functions.format import format

def create_command(command):
  """
  Create hdfs command. Append kinit to the command if required.
  """
  import params
  kinit_cmd = "{0} -kt {1} {2};".format(params.kinit_path_local, params.solr_kerberos_keytab, params.solr_kerberos_principal) if params.security_enabled else ""
  return kinit_cmd + command

def execute_commad(command):
  """
  Run hdfs command by solr user
  """
  import params
  return call(command, user=params.solr_user, timeout=300)

def check_hdfs_file_exists(hdfs_file):
  """
  Check that hdfs folder exists or not
  """
  cmd=create_command(format("hdfs dfs -ls {hdfs_file}"))
  returncode, stdout = execute_commad(cmd)
  if returncode:
    return False
  return True

def delete_lock_files_from_cores(collection, cores=[]):
  import params
  if len(cores) > 0:
    for core in cores:
      lock_file = format("{solr_hdfs_home_dir}/{collection}/{core}/data/index/write.lock")
      if check_hdfs_file_exists(lock_file):
        delete_cmd=create_command("hdfs dfs -rm -f {lock_file}")
        returncode, stdout = execute_commad(delete_cmd)
        if returncode:
          Logger.warn(format("Lock file '{lock_file}' has not been deleted correctly"))
          Logger.warn(format("Output of hdfs command: {stdout}"))
        else:
          Logger.info(format("Lock file '{lock_file}' has been deleted successfully."))
      else:
        Logger.info(format("No write.lock file found at '{solr_hdfs_home_dir}/{collection}/{core}/data/index/'"))


def remove_write_locks():
  import params
  if params.has_ranger_admin:
    ranger_audit_cores = solr_cli.get_local_cores(params.ranger_solr_collection_name)
    delete_lock_files_from_cores(params.ranger_solr_collection_name, ranger_audit_cores)
  if params.has_atlas:
    vertex_cores = solr_cli.get_local_cores(params.atlas_vertex_index_name)
    delete_lock_files_from_cores(params.atlas_vertex_index_name, vertex_cores)

    edge_cores = solr_cli.get_local_cores(params.atlas_edge_index_name)
    delete_lock_files_from_cores(params.atlas_edge_index_name, edge_cores)

    fulltext_cores = solr_cli.get_local_cores(params.atlas_fulltext_index_name)
    delete_lock_files_from_cores(params.atlas_fulltext_index_name, fulltext_cores)