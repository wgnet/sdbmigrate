Feature: Generate Action
  @postgres
  Scenario: Simple config for PostgreSQL + generate initial migration
    Given migration dir
    And postgres_simple.yaml config
    And generate migration using template "trx_plain_sql"
    And generate migration using template "notrx_plain_py"
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And sdbmigrate state has correct env
  @postgres
  Scenario: Sharded config for PostgreSQL + generate
    Given migration dir
    And postgres_auto.yaml config
    And migrations
      | file                       | code      |
      | V0000__TRX_PLAIN__base.sql | CREATE TABLE base_test (id int); |
      | V0001__TRX_PLAIN__base.sql | SELECT * FROM base_test; |
    And generate migration using template "trx_plain_sql"
    And generate migration using template "notrx_plain_py"
    And generate migration using template "trx_shard_py"
    And generate migration using template "notrx_shard_sql"
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And sdbmigrate state has correct env
  @mysql
  Scenario: Simple config for MySQL + generate initial migration
    Given migration dir
    And mysql_simple.yaml config
    And generate migration using template "trx_plain_sql"
    And generate migration using template "notrx_plain_py"
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And sdbmigrate state has correct env
  @mysql
  Scenario: Sharded config for MySQL + generate
    Given migration dir
    And mysql_auto.yaml config
    And add migration V0000__TRX_SHARD__test.sql
      """
      CREATE TABLE IF NOT EXISTS test_base_<shard_id>
      (
        id bigint PRIMARY KEY,
        trx_id bigint not null,
        meta json not null
      );
      """
    And generate migration using template "trx_plain_sql"
    And generate migration using template "notrx_plain_py"
    And generate migration using template "trx_shard_py"
    And generate migration using template "notrx_shard_sql"
    And init databases
    And successful sdbmigrate.py run with defaults
    Then sdbmigrate.py "succeeded"
    And database has initialized sdbmigrate state schema
    And sdbmigrate state has correct migrations
    And sdbmigrate state has correct env
    And sdbmigrate state has correct auto sharding
