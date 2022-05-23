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
Feature: Real world migration cases
  Scenario: Mix plain and shard migration with second run
    Given migration dir
    And add migration V0000__NOTRX_PLAIN__base.sql
      """
      CREATE TABLE IF NOT EXISTS test (id bigint);
      """
    And add migration V0001__TRX_SHARD__test.sql
      """
      CREATE SEQUENCE test_uniq_seq_<shard_id>;
      CREATE TABLE IF NOT EXISTS test_<shard_id>
      (
        id bigint,
        trx_id bigint not null,
        meta jsonb not null,
        CONSTRAINT test_pkey_<shard_id> PRIMARY KEY(id)
      );
      """
    And postgres_auto.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And plain table was created with name "test"
    And sharded table was created with name "test_<shard_id>"
    And sharded sequence was created with name "test_uniq_seq_<shard_id>"
    # run sdbmigrate.py again
    Given successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"

    Scenario: Add migrations one by one
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
        CREATE SEQUENCE test_uniq_seq_<shard_id>;
        CREATE TABLE IF NOT EXISTS test_<shard_id>
        (
            id bigint,
            trx_id bigint not null,
            meta jsonb not null,
            CONSTRAINT test_pkey_<shard_id> PRIMARY KEY(id)
        );
        """
      And successful sdbmigrate.py run with defaults
      Then sdbmigrate.py "succeeded"
      And sdbmigrate state has correct migrations
      And sharded table was created with name "test_<shard_id>"
      And sharded sequence was created with name "test_uniq_seq_<shard_id>"
      Given migrations
        | file                         | code                                             |
        | V0002__TRX_PLAIN__base.sql   | CREATE TABLE IF NOT EXISTS test_trx (id bigint); |
      And successful sdbmigrate.py run with defaults
      Then sdbmigrate.py "succeeded"
      And sdbmigrate state has correct migrations
      And plain table was created with name "test_trx"
