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
Feature: Sdb env variables
  Scenario: Apply the plain migration & check env
    Given migration dir
    And migrations
      | file                       | code      |
      | V0000__TRX_PLAIN__base.sql | SELECT 1; |
    And mysql_auto.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And sdbmigrate state has correct env
    And sdbmigrate state has correct auto sharding
    Given mysql_auto.yaml config with updated region_id=100500
    And failed sdbmigrate.py run with defaults
    Then sdbmigrate.py "failed"
    Then sdbmigrate.py failed with __main__.SdbInvalidEnv
    Given mysql_auto.yaml config with updated region_id=2
    Then sdbmigrate state has correct env
  
  Scenario: Apply the plain migration with force update of region_id
    Given migration dir
    And migrations
      | file                       | code      |
      | V0000__TRX_PLAIN__base.sql | SELECT 1; |
    And mysql_auto.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And sdbmigrate state has correct env
    And sdbmigrate state has correct auto sharding
    Given mysql_auto.yaml config with updated region_id=100500
    And successful sdbmigrate.py run with args --force-update-env
    Then sdbmigrate.py "succeeded"
    Then sdbmigrate state has correct env
