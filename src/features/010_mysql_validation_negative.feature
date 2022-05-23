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
Feature: Various validation & checks
  Scenario: Unsupported language prefix
    Given migration dir
    And migrations
      | file                      | code                   |
      | V0000__TRX_PLAIN__base.sh | echo "Bash migration"  |
    And mysql_auto.yaml config
    And init databases
    And failed sdbmigrate.py run with defaults
    Then sdbmigrate.py "failed"
    And sdbmigrate.py failed with __main__.SdbMigrateError: Unsupported migration code language: `sh`

  Scenario: Unsupported language prefix for shard migration
    Given migration dir
    And migrations
      | file                      | code                   |
      | V0000__TRX_SHARD__base.sh | echo "Bash migration"  |
    And mysql_auto.yaml config
    And init databases
    And failed sdbmigrate.py run with defaults
    Then sdbmigrate.py "failed"
    And sdbmigrate.py failed with __main__.SdbMigrateError: Unsupported migration code language: `sh`

  Scenario: Wrong migration version
    Given migration dir
    And migrations
      | file                       | code       |
      | V0__TRX_PLAIN__base.sql    | SELECT 1;  |
    And mysql_auto.yaml config
    And init databases
    And failed sdbmigrate.py run with defaults
    Then sdbmigrate.py "failed"
    And sdbmigrate.py failed with Wrong migration name

  Scenario: Wrong migration type1 - TRX/NOTRX
    Given migration dir
    And migrations
      | file                             | code       |
      | V0000__NONTRX_PLAIN__base.sql    | SELECT 1;  |
    And mysql_auto.yaml config
    And init databases
    And failed sdbmigrate.py run with defaults
    Then sdbmigrate.py "failed"
    And sdbmigrate.py failed with __main__.SdbInvalidConfig: unsupported migration type1

  Scenario: Wrong migration type2 - PLAIN/SHARD
    Given migration dir
    And migrations
      | file                             | code       |
      | V0000__NOTRX_FUCK__base.sql      | SELECT 1;  |
    And mysql_auto.yaml config
    And init databases
    And failed sdbmigrate.py run with defaults
    Then sdbmigrate.py "failed"
    And sdbmigrate.py failed with __main__.SdbInvalidConfig: unsupported migration type2

  Scenario: Wrong migration name
    Given migration dir
    And migrations
      | file                                    | code       |
      | V0__NOTRX_FUCK__BASE_MIGRATION.sql      | SELECT 1;  |
    And mysql_auto.yaml config
    And init databases
    And failed sdbmigrate.py run with defaults
    Then sdbmigrate.py "failed"
    And sdbmigrate.py failed with Wrong migration name
