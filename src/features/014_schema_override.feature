Feature: Default schema override
    @postgres
    Scenario: Apply the plain migration with default schema override in PostgreSQL
        Given migration dir
        And migrations
          | file                       | code      |
          | V0000__TRX_PLAIN__base.sql | CREATE TABLE test1(id integer); |
          | V0001__TRX_PLAIN__base.sql | CREATE SCHEMA other_schema; CREATE TABLE other_schema.test2(id integer); |
        And postgres_auto.yaml config
        And init databases
        And successful sdbmigrate.py run with args --migrate-state-schema=non_default
        Then sdbmigrate.py "succeeded"
        And database has initialized sdbmigrate state schema in schema "non_default"
        And sdbmigrate state has correct migrations in schema "non_default"
        And sdbmigrate state has correct env in schema "non_default"
        And sdbmigrate state has correct auto sharding in schema "non_default"
        And plain table was created with name "test1" in schema "public"
        And plain table was created with name "test2" in schema "other_schema"

    @mysql
    Scenario: Apply the plain migration with default schema override in MySQL
        # MySQL doesn't has rich schema support, so you should be careful with such scenarios
        # e.g. here I have to put IF NOT EXISTS in each migration, because migration is applied for
        # two databases on the one host, attempt to create other_schema twice and failed.
        Given migration dir
        And migrations
          | file                       | code      |
          | V0000__TRX_PLAIN__base.sql | CREATE TABLE test1(id integer); |
          | V0001__TRX_PLAIN__base.sql | CREATE SCHEMA IF NOT EXISTS other_schema; |
          | V0002__TRX_PLAIN__base.sql | CREATE TABLE IF NOT EXISTS other_schema.test2(id integer); |
        And mysql_auto.yaml config
        And init databases
        And successful sdbmigrate.py run with args --migrate-state-schema=non_default
        Then sdbmigrate.py "succeeded"
        And sdbmigrate state has correct auto sharding
        And database has initialized sdbmigrate state schema
        And sdbmigrate state has correct migrations
        And sdbmigrate state has correct env
        And plain table was created with name "test1"
        And plain table was created with name "test2" in schema "other_schema"
