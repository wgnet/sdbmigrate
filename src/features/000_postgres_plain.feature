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
Feature: Plain
  Scenario: Apply the simplest plain migration
    Given migration dir
    And migrations
      | file                       | code      |
      | V0000__TRX_PLAIN__base.sql | SELECT 1; |
    And postgres_auto.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And sdbmigrate state has correct env
    And sdbmigrate state has correct auto sharding

  Scenario: Apply non-transactitonal plain migration
    Given migration dir
    And migrations
      | file                         | code                |
      | V0000__NOTRX_PLAIN__base.sql | CREATE TABLE IF NOT EXISTS test (id bigint); |
    And postgres_auto.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And plain table was created with name "test"
