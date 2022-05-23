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
Feature: Sharded
  Scenario: Apply the migration with auto sharded table
    Given migration dir
    And add migration V0000__TRX_SHARD__test.sql
      """
      CREATE TABLE IF NOT EXISTS test_<shard_id>
      (
        id bigint PRIMARY KEY,
        trx_id bigint not null,
        meta json not null
      );
      """
    And mysql_auto.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And sdbmigrate state has correct env
    And sdbmigrate state has correct auto sharding
    And sharded table was created with name "test_<shard_id>"

  Scenario: Apply NOTRX migration with auto sharded index
    Given migration dir
    And add migration V0000__NOTRX_SHARD__test_idx.sql
      """
      CREATE TABLE IF NOT EXISTS test_<shard_id>
      (
        id bigint PRIMARY KEY,
        trx_id bigint not null
      );
      CREATE INDEX test_trx_id_<shard_id>_idx ON
         test_<shard_id> (trx_id);
      """
    And mysql_auto.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And sdbmigrate state has correct auto sharding
    And sharded table was created with name "test_<shard_id>"
    And sharded index was created with name "test_trx_id_<shard_id>_idx"

  Scenario: Apply the migration with manual sharded table
    Given migration dir
    And add migration V0000__NOTRX_SHARD__test_idx.sql
      """
      CREATE TABLE IF NOT EXISTS test_<shard_id> (id bigint);
      """
    And mysql_manual.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And sdbmigrate state has correct env
    And sdbmigrate state has correct manual sharding
    And sharded table was created with name "test_<shard_id>"
