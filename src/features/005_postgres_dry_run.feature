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
@postgres
Feature: Dry-run feature
  Scenario: Test migration via using --dry-run option
    Given migration dir
    And add migration V0000__NOTRX_PLAIN__base.sql
      """
      CREATE TABLE IF NOT EXISTS test (id bigint);
      """
    And postgres_auto.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And plain table was created with name "test"
    Given add migration V0001__TRX_SHARD__test.sql
      """
      CREATE TABLE IF NOT EXISTS test_<shard_id>
      (
        id bigint,
        trx_id bigint not null,
        meta jsonb not null,
        CONSTRAINT test_pkey_<shard_id> PRIMARY KEY(id)
      );
      """
    And add migration V0003__TRX_PLAIN__base.sql
      """
      CREATE TABLE IF NOT EXISTS test_trx (id bigint);
      """
    And successful sdbmigrate.py run with dry-run
    Then sdbmigrate.py "succeeded"
    And plain table was NOT created with name "test_trx"
    And sharded table was NOT created with name "test_<shard_id>"
    Given successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And plain table was created with name "test_trx"
    And sharded table was created with name "test_<shard_id>"
