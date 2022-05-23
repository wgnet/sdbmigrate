# Copyright 2022 Wargaming Group Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
@mysql
Feature: Migrations in Python
  Scenario: Apply python migration with auto sharded table
    Given migration dir
    And add migration V0000__TRX_SHARD__test.py
    """
    global cursor
    global shard_id
    sql = 'CREATE TABLE IF NOT EXISTS test_py_{shard_id} (id integer, name text);'
    cursor.execute(sql.format(shard_id=shard_id))
    """
    And mysql_auto.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And sdbmigrate state has correct env
    And sdbmigrate state has correct auto sharding
    And sharded table was created with name "test_py_<shard_id>"

  Scenario: Apply NOTRX python migration with auto sharded index
    Given migration dir
    And add migration V0000__NOTRX_SHARD__test_idx.py
    """
    global cursor
    global shard_id
    sql = 'CREATE TABLE IF NOT EXISTS test_py_{shard_id} (id integer, name varchar(256));'
    cursor.execute(sql.format(shard_id=shard_id))
    sql_index = 'CREATE INDEX test_py_name_{shard_id}_idx ON test_py_{shard_id} (name)'
    cursor.execute(sql_index.format(shard_id=shard_id))
    """
    And mysql_auto.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And sdbmigrate state has correct auto sharding
    And sharded table was created with name "test_py_<shard_id>"
    And sharded index was created with name "test_py_name_<shard_id>_idx"

  Scenario: Apply NOTRX python plain migration
    Given migration dir
    And migrations
    | file                        | code          |
    | V0000__NOTRX_PLAIN__base.py | global cursor |
    And mysql_auto.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations

  Scenario: Apply TRX python plain migration
    Given migration dir
    And migrations
      | file                      | code          |
      | V0000__TRX_PLAIN__base.py | global cursor |
    And mysql_auto.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
