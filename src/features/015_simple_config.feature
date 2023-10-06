Feature: Simple config
  @postgres
  Scenario: Simple config for PostgreSQL
    Given migration dir
    And migrations
      | file                       | code      |
      | V0000__TRX_PLAIN__base.sql | CREATE TABLE test (id int); |
      | V0001__TRX_PLAIN__base.sql | SELECT * FROM test; |
    And postgres_simple.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And sdbmigrate state has correct env
  @mysql
  Scenario: Simple config for MySQL
    Given migration dir
    And migrations
      | file                       | code      |
      | V0000__TRX_PLAIN__base.sql | CREATE TABLE test (id int); |
      | V0001__TRX_PLAIN__base.sql | SELECT * FROM test; |
    And mysql_simple.yaml config
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And sdbmigrate state has correct env