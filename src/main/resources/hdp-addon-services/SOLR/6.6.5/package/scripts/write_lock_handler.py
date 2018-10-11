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

def check_hdfs_files_exist(write_locks_pattern):
  """
  Check that hdfs folders are exist or not
  """
  cmd=create_command(format("hdfs dfs -ls {write_locks_pattern}"))
  returncode, stdout = execute_commad(cmd)
  if returncode:
    return False
  return True

def remove_write_locks():
  """
  Removes write lock files from base solr hdfs dir based on a pattern (<solr_hdfs_home>/*/core_node*/data/index/write.lock)
  """
  import params
  write_locks_pattern = format("{solr_hdfs_home_dir}/*/core_node*/data/index/write.lock")
  if check_hdfs_files_exist(write_locks_pattern):
    delete_cmd=create_command(format("hdfs dfs -rm -f {write_locks_pattern}"))
    returncode, stdout = execute_commad(delete_cmd)
    if stdout:
      Logger.info(format("Output of hdfs command (skip errors): {stdout}"))
  else:
    Logger.info(format("Not found any write.lock files by pattern: {write_locks_pattern}"))
