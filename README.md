![Python Versions][python version badge]
![PostgreSQL Versions][postgresql version badge]
![MySQL Versions][mysql version badge]

# SdbMigrate tool

sdbmigrate - easy-peasy tool for applying set of SQL migration on PostgreSQL or MySQL. Supports sharding out of the box.


Supported Python versions:

    - 3.8.X
    - 3.9.X
    - 3.10.X

Deprecated Python versions(should work fine, buy support will be dropped soon):

    - 2.7.X

Supported PostgreSQL versions:

    - 10.X
    - 11.X
    - 12.X
    - 13.X
    - 14.X
    - 15.X

Supported MySQL versions:

    - 5.7.X
    - 8.0.X

## Main features

- work both for PostgreSQL and MySQL
- schema versions out of the box
- transactional and non-transactional steps
- sharded migration steps
- dry-run for transactional steps
- ability to apply stored procedures/functions

## Installation

To install sdbmigrate migrate you also need to install proper database connection library.
For Postgres it is "psycopg2", for MySQL it is "mysqlclient".

Use one of the following recepies.

1. Install for Postgres:
```
pip install sdbmigrate[postgres]
```
2. Install for Mysql:
```
pip install sdbmigrate[mysql]
```
3. Install for both Postgres and MySQL:
```
pip install sdbmigrate[postgres,mysql]
```

## Getting started guide with sdbmigrate and PostgreSQL

0. Install sdbmigrate

```
pip install sdbmigrate[postgres]
```

or clone this repo.

1. Install PostgreSQL on your system, see https://www.postgresql.org/download/

2. Create PostgreSQL user, e.g. test/test:

```
sudo -u postgres createuser -p 5432 test --pwprompt
```

3. Create database for applying migrations, e.g. :

```
for i in `seq 1 3` ; do echo $i ; sudo -u postgres createdb -p 5432 test_db$i ; done
```

4. Create YAML-config for sdbmigrate :

```
# a total number of shards for sharded tables
shard_count: 16

# shard distribution mode:
# "auto" - sdbmigrate migrate distribute shard across DB servers before initial
#          migration and then continue to use this distribution for all
#          sharded migrations. shard_on_db/shard_count and databases info
#          is used for such process.
# "manual" - shard distribution is specified by shards params inside databases
#            section
shard_distribution_mode: auto

# amount of shard perf DB master, used with shard_distribution_mode: "auto"
shard_on_db: 8

# information about database masters and their connection info
databases:
    - name: test_db1
      host: 127.0.0.1
      port: 5432
      # supported DB types: ["postgres", "mysql"]
      type: postgres
      user: test
      password: test

    - name: test_db2
      host: 127.0.0.1
      port: 5436
      # supported DB types: ["postgres", "mysql"]
      type: postgres
      user: test
      password: test

```

5. Run sdbmigrate with test DB :

```
sdbmigrate.py -c sdbmigrate.yaml -d demo/test_migrations
```

6. See migrations on disk

```
$ ls -l demo/test_migrations
total 24
-rw-rw-r-- 1 dr dr  244 Jul 18 09:46 V0000__TRX_PLAIN__initial_types.sql
-rw-rw-r-- 1 dr dr  902 Jul 18 09:42 V0001__TRX_PLAIN__initial_tables.sql
-rw-rw-r-- 1 dr dr 3781 Jul 18 09:48 V0002__TRX_SHARD__initial_tables.sql
-rw-rw-r-- 1 dr dr 1257 Jul 18 09:50 V0003__TRX_PLAIN__initial_procedures.sql
-rw-rw-r-- 1 dr dr  133 Jul 23 08:08 V0004__NOTRX_SHARD__extra_indices.sql
-rw-rw-r-- 1 dr dr   76 Jul 23 08:15 V0005__NOTRX_SHARD__drop_indices.sql

$ cat demo/test_migrations/V0000__TRX_PLAIN__initial_types.sql
CREATE TYPE item_type AS ENUM ('ownership', 'access');
CREATE TYPE item_value_type AS ENUM ('durable', 'consumable');
CREATE TYPE item_amount_unit AS ENUM ('number', 'time_seconds');
CREATE TYPE operation_type AS ENUM ('deposit','withdrawal');

```

7. Inspect DB using psql or other tool:

```
$ sudo -u postgres psql -p 5432 test_db2
=# \d+
...
```

See more info about sdbmigrate internals in docs/internals.md

## Running tests locally using Docker

```
cd src
make test
```


## Running tests locally

1. Setup Postgres

    Mac OS:
    ```
    brew install postgres
    brew services start postgres
    createuser -s postgres
    psql -U postgres
    ```

    Create user and databases
    ```
    CREATE USER test_behave WITH SUPERUSER PASSWORD 'test_behave';
    CREATE DATABASE sdbmigrate1_behave OWNER test_behave;
    CREATE DATABASE sdbmigrate2_behave OWNER test_behave;
    ```

2. Setup MySQL

    Mac OS:
    ```
    brew install mysql
    brew services start mysql
    mysql -h 127.0.0.1 -u root -p
    <enter>
    ```

    Create user and databases
    ```
    CREATE DATABASE IF NOT EXISTS sdbmigrate1_behave;
    CREATE DATABASE IF NOT EXISTS sdbmigrate2_behave;
    CREATE USER IF NOT EXISTS 'test_behave'@'%' IDENTIFIED BY 'test_behave';
    GRANT ALL PRIVILEGES ON sdbmigrate1_behave.* TO 'test_behave'@'%';
    GRANT ALL PRIVILEGES ON sdbmigrate2_behave.* TO 'test_behave'@'%';
    FLUSH PRIVILEGES;
    ```

3. Setup python 2.7 and python 3.8 on your local machine.

    Mac OS:
    ```
    brew install python@2.7 python@3.8
    ```

4. Install dev requirements.
    ```
    pip install -r src/requirements_dev.txt
    ```

5. Run tests
    ```
    make -C src test_local
   ```

<!-- Badges -->
[python version badge]: https://img.shields.io/badge/python-3.8%20to%203.10-green.svg?style=plastic```
[postgresql version badge]: https://img.shields.io/badge/postgresql-10%20to%2015-darkgreen.svg?style=plastic```
[mysql version badge]: https://img.shields.io/badge/mysql-5.7%20to%208.0-darkgreen.svg?style=plastic```
