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
from behave import given


@given("init databases")
def step_impl(context):
    context.databases = {}
    if "postgres" in context.tags:
        init_postgres_databases(context)
    if "mysql" in context.tags:
        init_mysql_databases(context)


def init_postgres_databases(context):
    import psycopg2

    # drop/init database, terminate backends
    for db_info in context.sdbmigrate_config["databases"]:
        conn = psycopg2.connect(
            host=db_info["host"],
            port=db_info["port"],
            dbname="postgres",
            user=db_info["user"],
            password=db_info["password"],
        )
        conn.autocommit = True
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity WHERE datname='{}'".format(db_info["name"])
                )
                cur.execute("DROP DATABASE IF EXISTS {}".format(db_info["name"]))
                cur.execute("CREATE DATABASE {}".format(db_info["name"]))

    # init connections for tests
    databases = {}
    for db_num, db_info in enumerate(context.sdbmigrate_config["databases"]):
        conn = psycopg2.connect(
            host=db_info["host"],
            port=db_info["port"],
            dbname=db_info["name"],
            user=db_info["user"],
            password=db_info["password"],
        )
        databases[db_num] = {"db_info": db_info, "conn": conn}

    context.databases.update(databases)


def init_mysql_databases(context):
    from MySQLdb import Connection

    # drop/init database, terminate backends
    for db_info in context.sdbmigrate_config["databases"]:
        connection = Connection(
            host=db_info["host"],
            port=db_info["port"],
            user=db_info["user"],
            passwd=db_info["password"],
            db=db_info["name"],
            autocommit=True,
        )
        with connection.cursor() as cur:
            cur.execute("DROP DATABASE IF EXISTS {}".format(db_info["name"]))
            cur.execute("CREATE DATABASE {}".format(db_info["name"]))

    # init connections for tests
    databases = {}
    for db_num, db_info in enumerate(context.sdbmigrate_config["databases"]):
        connection = Connection(
            host=db_info["host"],
            port=db_info["port"],
            user=db_info["user"],
            passwd=db_info["password"],
            db=db_info["name"],
        )
        conn = MysqlConnectionWrapper(connection)
        databases[db_num] = {"db_info": db_info, "conn": conn}

    context.databases.update(databases)


class MysqlConnectionWrapper:
    def __init__(self, connection, autocommit=False):
        self._connection = connection
        self._autocommit = autocommit

    def __enter__(self):
        if not self._autocommit:
            self._connection.begin()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self._autocommit:
            if exc_type is None:
                self._connection.commit()
            else:
                self._connection.rollback()

    def cursor(self):
        return self._connection.cursor()
