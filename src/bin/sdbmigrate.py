#!/usr/bin/env python
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

"""Cool database migration tool both for sharded and simple databases.

Available actions(specified by --action or -a):
apply    -- run set of migration on target databases according to config;
generate -- create next basic migration from the template and
            put to directory with migrations.

"""
import sys
import argparse
import logging
import pprint
import os
import re
import copy
import json
from contextlib import contextmanager

import yaml

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import SafeLoader as Loader

import sqlparse


LOG_LEVELS = {
    "info": logging.INFO,
    "debug": logging.DEBUG,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

MIGRATION_LANG_SQL = "sql"
MIGRATION_LANG_PYTHON = "py"

DB_TYPE_POSTGRES = "postgres"
DB_TYPE_MYSQL = "mysql"


class SdbMigrateError(Exception):
    """Base class for migration errors"""


class SdbInvalidConfig(SdbMigrateError):
    """Migration error because of wrong config"""


class SdbInvalidShardingConfig(SdbInvalidConfig):
    """Migration error because of wrong sharding configuration"""


class SdbInvalidEnv(SdbInvalidConfig):
    """Migration error because of invalid sdbmigrate env"""


class DbSession:  # pylint: disable=too-many-instance-attributes
    """Class for encapsulating all about sharded DB
    and its settings.
    """

    def __init__(
        self,
        db_config,
        db_index,
        trx_conn=None,
        notrx_conn=None,
        schema_version=None,
        shard_ids=None,
        migrations=None,
        migrate_state_schema=None,
        env=None
    ):
        self.config = db_config
        self.host = self.config["host"]
        self.name = self.config["name"]
        self.port = self.config["port"]
        self.user = self.config["user"]
        self.password = self.config["password"]
        self.type = self.config["type"]
        self.shards = self.config.get("shards", [])
        self.index = db_index
        self.trx_conn = trx_conn
        self.notrx_conn = notrx_conn
        self.schema_version = schema_version
        self.shard_ids = shard_ids
        self.migrations = migrations
        self.migrate_state_schema = migrate_state_schema
        self.env = env

    @property
    def schema(self):
        if self.migrate_state_schema and self.type == DB_TYPE_POSTGRES:
            return self.migrate_state_schema

        if self.type == DB_TYPE_POSTGRES:
            return "public"

        # For MySQL Schema===Database and can't be created and used as flexible
        # as in PostgreSQL, see https://dev.mysql.com/doc/refman/8.0/en/create-database.html
        return self.name

    def __str__(self):
        return "DB[host={}, name={}, type={}]".format(self.host, self.name, self.type)

    def __repr__(self):
        return self.__str__()


class Sql:
    """
    Class that allows to encapsulate differences of SQL for different database types
    """

    def __init__(self, default=None, postgres=None, mysql=None):
        self.postgres = postgres or default
        self.mysql = mysql or default

    def get_for(self, db):
        sql_str = None
        if db.type == DB_TYPE_POSTGRES:
            sql_str = self.postgres
        elif db.type == DB_TYPE_MYSQL:
            sql_str = self.mysql
        return sql_str

    def resolve_for(self, db):
        return env_query(self.get_for(db), {"db_schema": {"value": db.schema}})


def connect(db_info, log=None, autocommit=False):
    """
    Setup and return connection to single database.
    """
    if db_info["type"] == DB_TYPE_POSTGRES:
        import psycopg2  # pylint: disable=import-outside-toplevel,import-error

        # https://www.psycopg.org/docs/module.html
        connection = psycopg2.connect(
            host=db_info["host"],
            port=db_info["port"],
            dbname=db_info["name"],
            user=db_info["user"],
            password=db_info["password"],
        )
        connection.autocommit = autocommit
        return PostgresConnectionWrapper(connection, log)
    if db_info["type"] == DB_TYPE_MYSQL:
        from MySQLdb import Connection  # pylint: disable=import-outside-toplevel,import-error

        # https://mysqlclient.readthedocs.io/user_guide.html
        connection = Connection(
            host=db_info["host"],
            port=db_info["port"],
            user=db_info["user"],
            passwd=db_info["password"],
            db=db_info["name"],
            autocommit=autocommit,
        )
        return MysqlConnectionWrapper(connection, log, autocommit)
    raise ValueError("Invalid db type %s" % db_info["type"])


class PostgresConnectionWrapper:
    """
    Returns CursorWrapper instance in cursor() response.
    In other cases this class just redirects calls to the native connection.
    """

    def __init__(self, connection, log=None):
        self.log = log
        self._connection = connection

    def rollback(self):
        return self._connection.rollback()

    def __enter__(self):
        return self._connection.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        return self._connection.__exit__(exc_type, exc_value, traceback)

    @contextmanager
    def cursor(self):
        with self._connection.cursor():
            yield CursorWrapper(self._connection.cursor(), self.log)


class MysqlConnectionWrapper:
    """
    - Returns CursorWrapper instance in cursor() response.
    - Adds behavior of context manager the same way as it is done in psycopg2
    In other cases this class just redirects calls to the native connection.
    """

    def __init__(self, connection, log=None, autocommit=False):
        self.log = log
        self._connection = connection
        self._autocommit = autocommit
        self._is_in_trx = False

    def rollback(self):
        assert self._is_in_trx
        return self._connection.rollback()

    def __enter__(self):
        assert not self._is_in_trx
        if not self._autocommit:
            self._connection.begin()
            self._is_in_trx = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        assert self._is_in_trx
        self._is_in_trx = False
        if not self._autocommit:
            if exc_type is None:
                self._connection.commit()
            else:
                self._connection.rollback()

    @contextmanager
    def cursor(self):
        with self._connection.cursor():
            yield CursorWrapper(
                cursor=self._connection.cursor(), log=self.log, name=str(self._connection)
            )


class CursorWrapper:
    """
    Wrapper for DB API V2.0 cursors that just adds debug logging.
    """

    def __init__(self, cursor, log, name=None):
        self.cursor = cursor
        self.log = log
        self.name = name or str(cursor)

    def execute(self, query, args=()):
        self.log.debug("execute SQL %s with args: %s on %s", query, args, self.name)
        self.cursor.execute(query, args)

    def fetchone(self):
        result = self.cursor.fetchone()
        self.log.debug("fetchone: %s", result)
        return result

    def fetchall(self):
        result = self.cursor.fetchall()
        self.log.debug("fetchall %s rows: %s", self.rowcount, result)
        return result

    def __getattr__(self, name):
        # For other available attributes and methods see
        # https://www.python.org/dev/peps/pep-0249/#cursor-objects
        return getattr(self.cursor, name)


class DbWrapper:
    """Class for encapsulating all DB-specific code.
    Supported databases:
        PostgreSQL 9.6 .. 11
        MySQL 5.7
    """

    SDB_STATE_TABLES = {
        "_sdbmigrate_migrations": Sql(
            postgres="""
                CREATE TABLE IF NOT EXISTS <db_schema>._sdbmigrate_migrations (
                    version BIGINT NOT NULL PRIMARY KEY,
                    migration_name TEXT NOT NULL,
                    applied TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                );
            """,
            mysql="""
                CREATE TABLE IF NOT EXISTS <db_schema>._sdbmigrate_migrations (
                    version BIGINT NOT NULL PRIMARY KEY,
                    migration_name TEXT NOT NULL,
                    applied TIMESTAMP DEFAULT NOW()
                );
            """,
        ),
        "_sdbmigrate_sharding_state": Sql(
            postgres="""
                CREATE TABLE IF NOT EXISTS <db_schema>._sdbmigrate_sharding_state (
                    id INTEGER NOT NULL PRIMARY KEY,
                    shard_count INTEGER NOT NULL,
                    shard_ids JSON NOT NULL,
                    created TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                    updated TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                );
            """,
            mysql="""
                CREATE TABLE IF NOT EXISTS <db_schema>._sdbmigrate_sharding_state (
                    id INTEGER NOT NULL PRIMARY KEY,
                    shard_count INTEGER NOT NULL,
                    shard_ids JSON NOT NULL,
                    created TIMESTAMP DEFAULT NOW(),
                    updated TIMESTAMP DEFAULT NOW()
                );
            """,
        ),
        "_sdbmigrate_env": Sql(
            postgres="""
                CREATE TABLE IF NOT EXISTS <db_schema>._sdbmigrate_env (
                    key varchar(128) PRIMARY KEY,
                    value TEXT NOT NULL,
                    type varchar(128) NOT NULL DEFAULT 'str',
                    created TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                    updated TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
                );
            """,
            mysql="""
                CREATE TABLE IF NOT EXISTS <db_schema>._sdbmigrate_env (
                    `key` varchar(128) PRIMARY KEY,
                    `value` TEXT NOT NULL,
                    `type` varchar(128) NOT NULL DEFAULT 'str',
                    `created` TIMESTAMP DEFAULT NOW(),
                    `updated` TIMESTAMP DEFAULT NOW()
                );
            """,
        ),
    }
    SDB_ENV_TYPES = {"int", "str", "float"}

    def __init__(self, args, sdbmigrate_config):
        self.log = logging.getLogger(self.__class__.__name__)
        self.args = args
        self.sdbmigrate_config = sdbmigrate_config
        self.migrate_state_schema = None

        self.db_sessions = []
        for db_index, db in enumerate(sdbmigrate_config["databases"]):
            db_config = copy.copy(db)
            trx_conn = self.get_db_connection(db)
            notrx_conn = self.get_db_connection(db, autocommit=True)
            if self.args.migrate_state_schema:
                self.migrate_state_schema = self.args.migrate_state_schema

            db_session = DbSession(
                db_config, db_index, trx_conn, notrx_conn,
                migrate_state_schema=self.migrate_state_schema
            )
            self.db_sessions.append(db_session)

    def get_db_connection(self, db_info, autocommit=False):
        return connect(db_info, self.log, autocommit)

    def get_shards_for_db_auto(self, db_index, shard_count, shard_on_db):
        if shard_count % shard_on_db != 0:
            raise SdbInvalidShardingConfig("Cant distribute shards on dbs fairly")

        min_shard = db_index * shard_on_db
        max_shard = (db_index + 1) * shard_on_db - 1
        self.log.debug(
            "db_index is %s, shard_on_db is %s, min_shard is %s, max_shard is %s",
            db_index,
            shard_on_db,
            min_shard,
            max_shard,
        )

        return list(range(min_shard, max_shard + 1))

    @staticmethod
    def get_shards_for_db_manual(db):
        shard_ids = []
        for shard_info in db.shards:
            shard_range = range(shard_info["min"], shard_info["max"] + 1)
            shard_ids.extend(shard_range)

        return shard_ids

    @staticmethod
    def is_shard_state_initialized(cursor, db):
        sql_cmd = Sql("SELECT count(*) FROM <db_schema>._sdbmigrate_sharding_state WHERE id=0")
        cursor.execute(sql_cmd.resolve_for(db))
        res = cursor.fetchone()
        return res[0] > 0

    def init_sdbmigrate_shard_state(self, cursor, db):
        if self.is_shard_state_initialized(cursor, db):
            logging.debug("Sdb shard state is already initialized in db `%s`", db)
            return False

        shard_count = self.sdbmigrate_config["shard_count"]
        shard_distribution_mode = self.sdbmigrate_config.get("shard_distribution_mode", None)
        if shard_distribution_mode is None:
            # It's a basic config without sharding.
            shard_ids = []
        elif shard_distribution_mode == "auto":
            shard_on_db = self.sdbmigrate_config["shard_on_db"]
            shard_ids = self.get_shards_for_db_auto(db.index, shard_count, shard_on_db)
        elif shard_distribution_mode == "manual":
            shard_ids = self.get_shards_for_db_manual(db)
        else:
            raise SdbInvalidConfig(
                "Invalid shard_distribution_mode `{}` in config".format(shard_distribution_mode)
            )

        sql_cmd = Sql(
            """
            INSERT INTO
                <db_schema>._sdbmigrate_sharding_state (id, shard_count, shard_ids)
            VALUES
                (0, %(shard_count)s, %(shard_ids)s)
            """,
        )
        cursor.execute(
            sql_cmd.resolve_for(db),
            {"shard_ids": json.dumps(shard_ids), "shard_count": shard_count},
        )
        return True

    @staticmethod
    def is_env_initialized(cursor, db):
        sql_cmd = Sql("SELECT count(*) FROM <db_schema>._sdbmigrate_env")
        cursor.execute(sql_cmd.resolve_for(db))
        res = cursor.fetchone()
        return res[0] > 0

    def verify_env_type(self, key, env_type, db):
        if env_type not in self.SDB_ENV_TYPES:
            raise SdbInvalidEnv(
                "Unsupported sdbmigrate env type `{}` for key `{}` in `{}`".format(env_type, key, db)
            )

    def init_sdbmigrate_env(self, cursor, db):
        sdbmigrate_env = self.sdbmigrate_config.get("env", {})
        # by default sdbmigrate environment is frozen and may be reloaded only
        # if you specified --force-update-env option
        if self.is_env_initialized(cursor, db) and not self.args.force_update_env:
            logging.debug("Sdb env is already initialized in db `%s`", db)
            return

        if self.args.force_update_env:
            logging.info("Force set sdbmigrate env into `%s` for `%s`", sdbmigrate_env, db)

        sql_cmd = Sql(
            postgres="""
                INSERT INTO
                    <db_schema>._sdbmigrate_env (key, value, type)
                VALUES
                    (%(key)s, %(value)s, %(type)s)
                ON CONFLICT (key) DO UPDATE
                    SET value=%(value)s, type=%(type)s, updated=now()
                WHERE
                    <db_schema>._sdbmigrate_env.key=%(key)s
            """,
            mysql="""
                INSERT INTO
                    <db_schema>._sdbmigrate_env (`key`, value, type)
                VALUES
                    (%(key)s, %(value)s, %(type)s)
                ON DUPLICATE KEY UPDATE
                    value=%(value)s, type=%(type)s, updated=now()
            """,
        )
        for key, var in sdbmigrate_env.items():
            sql_args = {"key": key, "value": var["value"], "type": "str"}
            if "type" in var:
                self.verify_env_type(key, var["type"], db)
                sql_args["type"] = var["type"]

            cursor.execute(sql_cmd.resolve_for(db), sql_args)

    def load_sdbmigrate_state(self, db):  # pylint: disable=too-many-locals
        config_sdbmigrate_env = self.sdbmigrate_config.get("env", {})
        with db.trx_conn as db_conn:
            with db_conn.cursor() as cursor:
                self.load_sdbmigrate_sharding_state(cursor, db)
                self.load_sdbmigrate_migrations_state(cursor, db)
                db_config_env = self.load_sdbmigrate_env(cursor, db, config_sdbmigrate_env)

                for row in db_config_env:
                    key = row[0]
                    db_value_raw = row[1]
                    db_type = row[2]
                    self.verify_env_type(key, db_type, db)

                    try:
                        python_type = eval(db_type)
                        db_value = python_type(db_value_raw)
                    except ValueError:
                        raise SdbInvalidEnv(
                            "Sdb env in `{}` has wrong value `{}` for key `{}` and type `{}`".format(
                                db, key, db_value_raw, db_type
                            )
                        )

                    if key not in config_sdbmigrate_env:
                        raise SdbInvalidEnv(
                            "Sdb env in `{}` has no key `{}` in config env".format(db, key)
                        )
                    config_value = config_sdbmigrate_env[key]["value"]
                    if config_value != db_value:
                        logging.info(
                            "env: key is `%s`, db_value is `%s`, config_value is `%s`",
                            key,
                            db_value,
                            config_value,
                        )
                        raise SdbInvalidEnv(
                            "Sdb env in `{}` has different values for key `{}`".format(db, key)
                        )
                    config_type = config_sdbmigrate_env[key].get("type", "str")
                    if config_type != db_type:
                        logging.info(
                            "env: key is `%s`, db_type is `%s`, config_type is `%s`",
                            key,
                            db_type,
                            config_type,
                        )
                        raise SdbInvalidEnv(
                            "Sdb env in `{}` has different types for key `{}``".format(db, key)
                        )
                db.env = config_sdbmigrate_env

    def load_sdbmigrate_sharding_state(self, cursor, db):
        sql_cmd_sharding_state = Sql(
            """
            SELECT
                shard_count, shard_ids
            FROM
                <db_schema>._sdbmigrate_sharding_state
            WHERE
                id=0
        """
        )
        config_shard_count = self.sdbmigrate_config["shard_count"]

        cursor.execute(sql_cmd_sharding_state.resolve_for(db))
        db_state = cursor.fetchone()
        db_shard_count = db_state[0]
        if db_shard_count != config_shard_count:
            raise SdbInvalidShardingConfig(
                "Different number of shards in `{}` - `{}` and config - `{}`".format(
                    db, db_shard_count, config_shard_count
                )
            )
        db_shard_ids = db_state[1]
        if db.type == DB_TYPE_MYSQL:
            db_shard_ids = json.loads(db_shard_ids)

        db.shard_ids = db_shard_ids
        self.log.debug("Load sdbmigrate state for %s. shard_ids: %s.", db, db.shard_ids)

    @staticmethod
    def load_sdbmigrate_migrations_state(cursor, db):
        sql_cmd_migrations = Sql(
            """
            SELECT
                version, migration_name
            FROM
                <db_schema>._sdbmigrate_migrations
            ORDER BY
                version
        """
        )
        cursor.execute(sql_cmd_migrations.resolve_for(db))
        res = cursor.fetchall()
        db_migrations = []
        last_version = -1
        for row in res:
            migration = Migration(version=row[0], full_name=row[1])
            last_version = row[0]
            db_migrations.append(migration)

        db.migrations = db_migrations
        db.schema_version = last_version

    @staticmethod
    def load_sdbmigrate_env(cursor, db, config_sdbmigrate_env):
        sql_cmd_env = Sql(
            postgres="""
                SELECT
                    key, value, type
                FROM
                    <db_schema>._sdbmigrate_env
                ORDER BY
                    key
            """,
            mysql="""
                SELECT
                    `key`, value, type
                FROM
                    <db_schema>._sdbmigrate_env
                ORDER BY
                    `key`
            """,
        )

        cursor.execute(sql_cmd_env.resolve_for(db))
        db_config_env = cursor.fetchall()
        if len(db_config_env) != len(config_sdbmigrate_env):
            logging.info(
                "env: config_sdbmigrate_env is `%s`, db_sdbmigrate_env is `%s`",
                config_sdbmigrate_env,
                db_config_env,
            )
            raise SdbInvalidEnv(
                "Sdb env in `{}` is not equal to config env: record count mismatch".format(db)
            )
        return db_config_env

    def init_sdbmigrate_state(self):
        for db in self.db_sessions:
            # init sdbmigrate state
            with db.trx_conn as db_conn:
                with db_conn.cursor() as cursor:
                    if self.migrate_state_schema:
                        self.init_schema(cursor)
                    self.init_sdbmigrate_state_tables(cursor, db)
                    self.init_sdbmigrate_shard_state(cursor, db)
                    self.init_sdbmigrate_env(cursor, db)

            self.load_sdbmigrate_state(db)

    def init_schema(self, cursor):
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.migrate_state_schema}")

    def init_sdbmigrate_state_tables(self, cursor, db):
        for table_name, sql in self.SDB_STATE_TABLES.items():
            if not self.is_table_exists(cursor, db, table_name):
                self.log.info("Create new sdbmigrate state table `%s` on `%s`", table_name, db)
                cursor.execute(sql.resolve_for(db))

    @staticmethod
    def set_migration_applied(cursor, db, migration):
        sql_cmd = Sql(
            """
            INSERT INTO
                <db_schema>._sdbmigrate_migrations (version, migration_name)
            VALUES
                (%(version)s, %(migration_name)s)
        """
        )
        cursor.execute(
            sql_cmd.resolve_for(db),
            {"version": migration.version, "migration_name": migration.full_name},
        )

    @staticmethod
    def is_table_exists(cursor, db, table_name):
        sql = Sql(
            """
            SELECT EXISTS(SELECT 1 FROM
            information_schema.tables
            WHERE table_schema = %(table_schema)s
            AND table_name = %(table_name)s)
        """
        )
        cursor.execute(sql.resolve_for(db), {"table_name": table_name, "table_schema": db.schema})
        is_exists = cursor.fetchone()[0]
        return is_exists


class Migration:
    """Class for representing one migration loading logic"""

    NAME_PATTERN = "^V([0-9]{4})__([A-Z]+)_([A-Z]+)__([a-z0-9_]+).([a-z]+)$"
    MIGRATION_TYPE1_TRX = "TRX"
    MIGRATION_TYPE1_NOTRX = "NOTRX"

    MIGRATION_TYPE2_PLAIN = "PLAIN"
    MIGRATION_TYPE2_SHARD = "SHARD"

    def __init__(
        self,
        version=None,
        type1=None,
        type2=None,
        short_name=None,
        full_name=None,
        path=None,
        lang=None,
        code=None
    ):
        self.version = int(version)
        self.type1 = type1
        self.type2 = type2
        self.short_name = short_name
        self.full_name = full_name
        self.code = code
        self.path = path
        self.lang = lang

    def __str__(self):
        return 'Migration(version="{}", full_name="{}")'.format(self.version, self.full_name)

    def __repr__(self):
        return self.__str__()

    def read(self):
        """ Read migration code from file.
        """
        migration_path = os.path.join(self.path, self.full_name)
        with open(migration_path, mode='r', encoding='utf8') as migration_file:
            self.code = migration_file.read()

    def write(self):
        """ Write migration code to file.
        """
        migration_path = os.path.join(self.path, self.full_name)
        with open(migration_path, mode='w', encoding='utf8') as migration_file:
            migration_file.write(self.code)


def load_sdbmigrate_config(path_to_config):
    try:
        with open(path_to_config, encoding='utf8') as config_file:
            sdbmigrate_config = yaml.load(config_file, Loader=Loader)
            logging.debug("sdbmigrate config:\n %s", pprint.pformat(sdbmigrate_config))

    except OSError as e:
        logging.error("Unable to open config %s. Error: %s", path_to_config, e)
        sys.exit(1)

    assert sdbmigrate_config is not None, "sdbmigrate_config should be loaded"

    database_count = len(sdbmigrate_config["databases"])
    shard_mode = sdbmigrate_config.get("shard_distribution_mode", None)
    # Initialize sharding config for the basic config without sharding.
    if "shard_count" not in sdbmigrate_config:
        sdbmigrate_config["shard_count"] = 0

    if (
        shard_mode == "auto"
        and sdbmigrate_config["shard_on_db"] * database_count != sdbmigrate_config["shard_count"]
    ):
        msg = "shard_count: {}  does not match to shard_on_db*database_count: {} * {}".format(
            sdbmigrate_config["shard_count"], sdbmigrate_config["shard_on_db"], database_count
        )
        raise SdbInvalidConfig(msg)

    return sdbmigrate_config


def load_migrations(path_to_migrations):
    migration_list = os.listdir(path_to_migrations)
    migration_name_re = re.compile(Migration.NAME_PATTERN)
    clean_migration_list = []
    for migration_name in migration_list:
        match_result = re.match(migration_name_re, migration_name)
        if match_result is None:
            logging.error(
                "Wrong migration name: %s. Expected pattern: %s",
                migration_name,
                Migration.NAME_PATTERN,
            )
            sys.exit(1)

        migration = Migration(
            version=match_result.group(1),
            type1=match_result.group(2),
            type2=match_result.group(3),
            short_name=match_result.group(4),
            full_name=match_result.group(0),
            path=path_to_migrations,
            lang=match_result.group(5),
        )
        migration.read()
        clean_migration_list.append(migration)

    # sort migration by version
    clean_migration_list.sort(key=lambda m: m.version)
    logging.debug("clean_migration_list:\n %s", pprint.pformat(clean_migration_list))

    return clean_migration_list


def shard_query(sql_template, shard_id):
    return sql_template.replace("<shard_id>", str(shard_id))


def env_query(sql_template, env):
    for key, var in env.items():
        # use all all variables from env as SQL template variables
        sql_template = sql_template.replace("<{}>".format(key), str(var["value"]))

    return sql_template


def split_sql(sql):
    return [chunk for chunk in sqlparse.split(sql) if chunk != ""]


def _do_apply_one_migration(sdbmigrate_state, cursor, db, migration):
    db_wrapper = sdbmigrate_state["db_wrapper"]
    if migration.type2 == Migration.MIGRATION_TYPE2_PLAIN:
        if migration.lang == MIGRATION_LANG_SQL:
            migration_code_with_env = env_query(migration.code, db.env)
            for sql_chunk in split_sql(migration_code_with_env):
                logging.debug("sql_chunk is %s", sql_chunk)
                cursor.execute(Sql(sql_chunk).resolve_for(db))
        elif migration.lang == MIGRATION_LANG_PYTHON:
            exec(migration.code, {"cursor": cursor, "env": db.env})
        else:
            raise SdbMigrateError(
                "Unsupported migration code language: `{}`".format(migration.lang)
            )

    elif migration.type2 == Migration.MIGRATION_TYPE2_SHARD:
        for shard_id in db.shard_ids:
            migration_code_with_env = env_query(migration.code, db.env)
            if migration.lang == MIGRATION_LANG_SQL:
                for sql_chunk in split_sql(migration_code_with_env):
                    logging.debug("sharded sql_chunk is %s", sql_chunk)
                    cursor.execute(shard_query(Sql(sql_chunk).resolve_for(db), shard_id))
            elif migration.lang == MIGRATION_LANG_PYTHON:
                exec(
                    migration.code,
                    {"cursor": cursor, "shard_id": shard_id, "env": db.env},
                )
            else:
                raise SdbMigrateError(
                    "Unsupported migration code language: `{}`".format(migration.lang)
                )
    else:
        raise SdbInvalidConfig("unsupported migration type2 {}".format(migration.type2))

    db_wrapper.set_migration_applied(cursor, db, migration)
    db.schema_version = migration.version
    logging.info("Migration %s was applied on %s", migration.full_name, db)


def generate_next_migration(sdbmigrate_state, migrations):
    """
    :param sdbmigrate_state: dictionary with various sdbmigrate settings
    :param migrations: list of migrations to apply
    :return:
    """
    if len(migrations) > 0:
        last_migration = migrations[-1]
    else:
        # handle case with generating first migration in migration directory
        last_migration = Migration(version=-1)

    next_version = last_migration.version + 1
    new_migration_params = {
        "trx_plain_sql": (
            Migration.MIGRATION_TYPE1_TRX,
            Migration.MIGRATION_TYPE2_PLAIN,
            MIGRATION_LANG_SQL
        ),
        "trx_shard_py": (
            Migration.MIGRATION_TYPE1_TRX,
            Migration.MIGRATION_TYPE2_SHARD,
            MIGRATION_LANG_PYTHON
        ),
        "notrx_shard_sql": (
            Migration.MIGRATION_TYPE1_NOTRX,
            Migration.MIGRATION_TYPE2_SHARD,
            MIGRATION_LANG_SQL
        ),
        "notrx_plain_py": (
            Migration.MIGRATION_TYPE1_NOTRX,
            Migration.MIGRATION_TYPE2_PLAIN,
            MIGRATION_LANG_PYTHON
        ),
    }
    new_migration_code = {
        "trx_plain_sql": """CREATE TABLE test (id bigint);
        """,
        "trx_shard_py": """global cursor
            global shard_id
            sql = 'CREATE TABLE test_py_{shard_id} (id bigint);'
            cursor.execute(sql.format(shard_id=shard_id))
        """,
        "notrx_shard_sql": """CREATE TABLE test_<shard_id> (id bigint);
        """,
        "notrx_plain_py": """global cursor
            sql = 'CREATE TABLE test_py (id bigint);'
            cursor.execute(sql)
        """,
    }
    template = sdbmigrate_state["args"].generate_template
    type1, type2, lang = new_migration_params[template]
    short_name = "new_migration"
    full_name = f"V{next_version:04d}__{type1}_{type2}__{short_name}.{lang}"
    path = sdbmigrate_state["args"].migrations_dir
    code = "\n".join([line.strip() for line in new_migration_code[template].split("\n")])
    next_migration = Migration(
        version=next_version,
        type1=type1,
        type2=type2,
        full_name=full_name,
        short_name=short_name,
        path=path,
        lang=lang,
        code=code
    )
    next_migration.write()
    logging.info("Generated new migration %s/%s from template %s", next_migration.path,
                 next_migration.full_name, template)


def apply_migration(sdbmigrate_state, db: DbSession, migration: Migration):
    is_dry_run = sdbmigrate_state["args"].dry_run
    if migration.type1 == Migration.MIGRATION_TYPE1_TRX:
        # apply migration step transactionally
        # using context manager
        with db.trx_conn as db_conn:
            with db_conn.cursor() as cursor:
                _do_apply_one_migration(sdbmigrate_state, cursor, db, migration)
            if is_dry_run:
                logging.info(
                    "Rollback migration %s on %s because of ---dry-run",
                    migration.full_name,
                    db,
                )
                db_conn.rollback()

    elif migration.type1 == Migration.MIGRATION_TYPE1_NOTRX:
        # apply migration step without transaction(autocommit=True)
        with db.notrx_conn.cursor() as cursor:
            if is_dry_run:
                logging.info(
                    "Skip notrx migration run %s on %s because of ---dry-run",
                    migration.full_name,
                    db,
                )
            else:
                _do_apply_one_migration(sdbmigrate_state, cursor, db, migration)
    else:
        raise SdbInvalidConfig("unsupported migration type1 {}".format(migration.type1))


def apply_migrations(sdbmigrate_state, migrations):
    """
    :param sdbmigrate_state: dictionary with various sdbmigrate settings
    :param migrations: list of migrations to apply
    :return:
    """
    db_wrapper = sdbmigrate_state["db_wrapper"]
    target_schema_version = sdbmigrate_state["args"].target_schema_version

    for db in db_wrapper.db_sessions:
        for migration in migrations:
            if target_schema_version is not None and db.schema_version >= target_schema_version:
                logging.info(
                    "Target schema version %s was reached on %s. Stop further migrations.",
                    migration.full_name,
                    db,
                )
                break

            if db.schema_version >= migration.version:
                logging.debug("Migration %s was already applied on %s", migration.full_name, db)
                continue
            try:
                apply_migration(sdbmigrate_state, db, migration)
            except Exception as e:
                logging.error('Unable to apply migration %s to %s. Please review migration code.',
                              migration.full_name, db)
                raise e


def main():
    """Entry point for sdbmigrate"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-c",
        "--config-file",
        type=str,
        required=True,
        help="Path to sdbmigrate configuration file",
    )
    parser.add_argument(
        "--action",
        "-a",
        default="apply",
        choices=("apply", "generate"),
        help="Specify action which will be performed during script run.",
    )
    parser.add_argument(
        "--generate-template",
        "-g",
        default="trx_plain_sql",
        choices=("trx_plain_sql", "trx_shard_py", "notrx_plain_py", "notrx_shard_sql"),
        help="Specify template to generate new empty migration.",
    )
    parser.add_argument(
        "-d",
        "--migrations-dir",
        type=str,
        required=True,
        help="Path to directory with migrations",
    )
    parser.add_argument(
        "--log-level",
        "-l",
        default="info",
        choices=("info", "debug", "error", "warning"),
        help="Specify logging level for sdbmigrate output",
    )
    parser.add_argument(
        "-t",
        "--target-schema-version",
        type=int,
        help="Specify target schema version to apply(for testing migrations)",
    )
    parser.add_argument(
        "--dry-run",
        default=False,
        action="store_true",
        help=(
            "Do not apply migrations on DB. "
            "For trx migrations do rollback, for notrx - print SQL to console and continue"
        ),
    )
    parser.add_argument(
        "--force-update-env",
        default=False,
        action="store_true",
        help="For update sdbmigrate env variables(by default they are frozen)",
    )
    parser.add_argument(
        "--migrate-state-schema",
        type=str,
        help=("Specify custom schema name for migration state. "
              "This option is supported only for PostgreSQL.")
    )

    # parse command line arguments
    args = parser.parse_args()

    # configure python logging using level from command line
    logging.basicConfig(
        level=LOG_LEVELS[args.log_level],
        format="%(levelname)s, %(asctime)s, %(filename)s +%(lineno)s, %(message)s",
    )

    sdbmigrate_config = load_sdbmigrate_config(args.config_file)
    migrations = load_migrations(args.migrations_dir)
    sdbmigrate_state = {"args": args}

    if args.action in ("apply", ):
        db_wrapper = DbWrapper(args, sdbmigrate_config)
        db_wrapper.init_sdbmigrate_state()
        sdbmigrate_state["db_wrapper"] = db_wrapper

    # run specified action
    action_map = {
        'apply': apply_migrations,
        'generate': generate_next_migration,
    }
    action_map[args.action](sdbmigrate_state, migrations)


if __name__ == "__main__":
    main()
