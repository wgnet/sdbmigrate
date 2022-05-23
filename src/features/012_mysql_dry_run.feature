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
Feature: Dry-run feature
  Scenario: Test migration via using --dry-run option
    Given migration dir
    And add migration V0000__NOTRX_PLAIN__base.sql
      """
      CREATE TABLE IF NOT EXISTS test (id bigint);
      """
    And add migration V0001__NOTRX_SHARD__test.sql
      """
      CREATE TABLE IF NOT EXISTS test_<shard_id> (id bigint, name text not null);
      """
    And mysql_auto.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And plain table was created with name "test"
    And sharded table was created with name "test_<shard_id>"
    # MySQL doesn't support transactional schema changes, so we test dry-run with INSERT statements
    Given add migration V0002__TRX_SHARD__test.sql
      """
      INSERT INTO test_<shard_id> VALUES
      (0, "Dart"),
      (1, "Vader");
      """
    And add migration V0003__TRX_PLAIN__base.sql
      """
      INSERT INTO test VALUES (42);
      """
    And successful sdbmigrate.py run with dry-run
    Then sdbmigrate.py "succeeded"
    And plain table with name "test" is empty
    And sharded table with name "test_<shard_id>" is empty
    Given successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And plain table with name "test" is NOT empty
    And sharded table with name "test_<shard_id>" is NOT empty
