## Migration naming magic


All migrations should have proper names to be properly processed by sdbmigrate:

V{SCHEMA_VERSION}__{TYPE1}_{TYPE2}__{NAME}.sql

{SCHEMA_VERSION} - integer between 0 and 2**63, should be monotonically incremented for each next migration.
{TYPE1} - type of migration - TRX or NOTRX.
          TRX - migration will be applied transactionally, NOTRX - transaction will be applied without transaction block.
          NOTRX should used for DDL like VACUUM, CREATE INDEX CONCURRENTLY etc.

{TYPE2} - type of migration - PLAIN or SHARD. PLAIN migrations contains plain SQL code.
          SHARD migrations contains SQL code templates, which have <shard_id> inside. Actual tables
          will be created on target DB master in depends on current shard distribution according to
          sdbmigrate YAML config.

{NAME} - human-readable name of migration.


For example:

V0000__TRX_PLAIN__initial_types.sql - migration with version 0, applied transactionally,
                                      contains plain SQL code.
V0002__TRX_SHARD__initial_tables.sql - migration with version 2, applied transactionally,
                                       contains SQL code template with sharded entities.
V0004__NOTRX_SHARD__extra_indices.sql - migration with version 4, applied non-transactionally,
                                        contains SQL code template with sharded entities.
                                        Do CREATE INDEX CONCURRENTLY.




## State of sdbmigrate

sdbmigrate stores its state in database using 2 tables - public._sdbmigrate_migrations and _sdbmigrate_sharding_state.

Here is example of _sdbmigrate_migrations in PostgreSQL:

**version** column has integer version which should monotonically incremented for
each next migrations. max(version) is current DB schema version.

**migration_name** contains migration file name.

**applied** has datetime of migration.


```
test_db2=# \d _sdbmigrate_migrations
                       Table "public._sdbmigrate_migrations"
     Column     |            Type             | Collation | Nullable | Default
----------------+-----------------------------+-----------+----------+---------
 version        | bigint                      |           | not null |
 migration_name | text                        |           | not null |
 applied        | timestamp without time zone |           |          | now()
Indexes:
    "_sdbmigrate_migrations_pkey" PRIMARY KEY, btree (version)


test_db2=# select * from _sdbmigrate_migrations ;
 version |              migration_name              |          applied
---------+------------------------------------------+----------------------------
       0 | V0000__TRX_PLAIN__initial_types.sql      | 2019-07-23 09:11:05.552868
       1 | V0001__TRX_PLAIN__initial_tables.sql     | 2019-07-23 09:11:05.558
       2 | V0002__TRX_SHARD__initial_tables.sql     | 2019-07-23 09:11:29.699978
       3 | V0003__TRX_PLAIN__initial_procedures.sql | 2019-07-23 09:11:51.42165
       4 | V0004__NOTRX_SHARD__extra_indices.sql    | 2019-07-23 09:11:51.490624
       5 | V0005__NOTRX_SHARD__drop_indices.sql     | 2019-07-23 09:11:51.518978
(6 rows)
```


Here is example of _sdbmigrate_sharding_state in PostgreSQL:

**shard_count** - the total of shards for sharded entities.
**shard_ids** - a list of shards on current DB master, serialized to JSON.

```
test_db2=# \d _sdbmigrate_sharding_state
                    Table "public._sdbmigrate_sharding_state"
   Column    |            Type             | Collation | Nullable | Default
-------------+-----------------------------+-----------+----------+---------
 id          | integer                     |           | not null |
 shard_count | integer                     |           | not null |
 shard_ids   | json                        |           | not null |
 created     | timestamp without time zone |           |          | now()
 updated     | timestamp without time zone |           |          | now()
Indexes:
    "_sdbmigrate_sharding_state_pkey" PRIMARY KEY, btree (id)

test_db2=# select * from _sdbmigrate_sharding_state ;
 id | shard_count |           shard_ids            |          created           |          updated
----+-------------+--------------------------------+----------------------------+----------------------------
  0 |          16 | [8, 9, 10, 11, 12, 13, 14, 15] | 2019-07-23 08:57:50.581911 | 2019-07-23 08:57:50.581911
```
