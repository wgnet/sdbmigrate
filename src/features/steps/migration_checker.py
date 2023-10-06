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
from behave import then
from features.steps.common import DbType, get_sdbmigrate_sharding_state


@then('sharded table was created with name "{table_name}"')
def step_impl(context, table_name):
    sql = "SELECT 1 from {table_name}".format(table_name=table_name)
    for_each_shard(context, sql)


@then('sharded sequence was created with name "{seq_name}"')
def step_impl(context, seq_name):
    sql = """SELECT nextval('{seq_name}')""".format(seq_name=seq_name)
    for_each_shard(context, sql)


@then('plain table was created with name "{table_name}" in schema "{schema}"')
def step_impl(context, table_name, schema):
    def f(_context, db_info, cur):
        is_created = check_table_exist_generic(cur, db_info, table_name, schema)
        assert is_created, "Table {table_name} is not exist".format(table_name=table_name)

    for_each_database(context, f)


@then('plain table was created with name "{table_name}"')
def step_impl(context, table_name):
    def f(_context, db_info, cur):
        sql = "SELECT 1 from {table_name}".format(table_name=table_name)
        cur.execute(sql)

        is_created = check_table_exist_generic(cur, db_info, table_name)
        assert is_created, "Table {table_name} is not exist".format(table_name=table_name)

    for_each_database(context, f)


@then('plain table was NOT created with name "{table_name}"')
def step_impl(context, table_name):
    def f(_context, db_info, cur):
        is_created = check_table_exist_generic(cur, db_info, table_name)
        assert not is_created, "Table {table_name} is exist!".format(table_name=table_name)

    for_each_database(context, f)


@then('sharded index was created with name "{name}"')
def step_impl(context, name):
    def f(_context, db_info, cur):
        sharding_state = get_sdbmigrate_sharding_state(db_info, cur)
        for shard_id in sharding_state["shard_ids"]:
            sharded_name = shard_query(name, shard_id)
            is_created = check_index_exist_generic(cur, db_info, sharded_name)
            assert is_created, "DB index `{name}` does not exist".format(name=sharded_name)

    for_each_database(context, f)


@then('sharded index was NOT created with name "{name}"')
def step_impl(context, name):
    def f(_context, db_info, cur):
        sharding_state = get_sdbmigrate_sharding_state(db_info, cur)
        for shard_id in sharding_state["shard_ids"]:
            sharded_name = shard_query(name, shard_id)
            is_created = check_index_exist_generic(cur, db_info, sharded_name)
            assert not is_created, "DB index `{name}` exists".format(name=sharded_name)

    for_each_database(context, f)


@then('sharded table was NOT created with name "{name}"')
def step_impl(context, name):
    def f(_context, db_info, cur):
        sharding_state = get_sdbmigrate_sharding_state(db_info, cur)
        for shard_id in sharding_state["shard_ids"]:
            sharded_name = shard_query(name, shard_id)
            is_created = check_table_exist_generic(cur, db_info, sharded_name)
            assert not is_created, "DB table `{name}` exists".format(name=sharded_name)

    for_each_database(context, f)


@then('plain table with name "{table_name}" is empty')
def step_impl(context, table_name):
    def f(_context, _db_info, cur):
        is_empty = check_if_table_is_empty(cur, table_name)
        assert is_empty, "Table {table_name} is not empty".format(table_name=table_name)

    for_each_database(context, f)


@then('plain table with name "{table_name}" is NOT empty')
def step_impl(context, table_name):
    def f(context, db_info, cur):
        is_empty = check_if_table_is_empty(cur, table_name)
        assert not is_empty, "Table {table_name} is empty".format(table_name=table_name)

    for_each_database(context, f)


@then('sharded table with name "{table_name}" is empty')
def step_impl(context, table_name):
    def f(shard_id, cur):
        sql = "SELECT count(*) from {table_name}".format(table_name=table_name)
        cur.execute(shard_query(sql, shard_id))
        res = cur.fetchone()
        assert res[0] == 0, "Table {table_name} is not empty".format(table_name=table_name)

    for_each_shard(context, f)


@then('sharded table with name "{table_name}" is NOT empty')
def step_impl(context, table_name):
    def f(shard_id, cur):
        sql = "SELECT count(*) from {table_name}".format(table_name=table_name)
        cur.execute(shard_query(sql, shard_id))
        res = cur.fetchone()
        assert res[0] > 0, "Table {table_name} is empty".format(table_name=table_name)

    for_each_shard(context, f)


def check_if_postgres_relation_exists(cursor, name, schema):
    """
    See http://dba.stackexchange.com/questions/35616/create-index-if-it-does-not-exist
    """
    sql = """
        SELECT 1
        FROM   pg_class c
        JOIN   pg_namespace n ON n.oid = c.relnamespace
        WHERE  c.relname = %(name)s  AND n.nspname=%(schema)s
    """
    cursor.execute(sql, {"name": name, "schema": schema})
    res = cursor.fetchall()
    return len(res) > 0


def check_if_mysql_table_exists(cursor, name, schema):
    sql = """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = %(schema)s AND table_name = %(name)s;
    """
    cursor.execute(sql, {"name": name, "schema": schema})
    res = cursor.fetchall()
    return len(res) == 1


def check_if_mysql_index_exists(cursor, name, schema):
    sql = """
    SELECT 1 FROM information_schema.statistics
    WHERE table_schema = %(schema)s AND index_name = %(name)s;
    """
    cursor.execute(sql, {"name": name, "schema": schema})
    res = cursor.fetchall()
    return len(res) == 1


def check_if_table_is_empty(cursor, name):
    sql = "SELECT count(*) FROM {name}".format(name=name)
    cursor.execute(sql)
    res = cursor.fetchone()
    return res[0] == 0


def shard_query(sql, shard_id):
    return sql.replace("<shard_id>", str(shard_id))


def for_each_shard(context, sql_or_func):
    """Run a piece of SQL code for each database and shard"""
    for db in context.databases.values():
        with db["conn"] as conn:
            with conn.cursor() as cur:
                sharding_state = get_sdbmigrate_sharding_state(db["db_info"], cur)
                for shard_id in sharding_state["shard_ids"]:
                    if isinstance(sql_or_func, str):
                        cur.execute(shard_query(sql_or_func, shard_id))
                    else:
                        sql_or_func(shard_id, cur)


def check_table_exist_generic(cur, db_info, name, schema=None):
    if db_info["type"] == DbType.postgres:
        if schema is None:
            schema = "public"
        is_created = check_if_postgres_relation_exists(cur, name, schema)
    elif db_info["type"] == DbType.mysql:
        if schema is None:
            schema = db_info["name"]
        is_created = check_if_mysql_table_exists(cur, name, schema)
    else:
        raise NotImplemented(f"Database type `{db_info['type']}` is not supported")

    return is_created


def check_index_exist_generic(cur, db_info, name, schema=None):
    if db_info["type"] == DbType.postgres:
        if schema is None:
            schema = "public"
        is_created = check_if_postgres_relation_exists(cur, name, schema)
    elif db_info["type"] == DbType.mysql:
        if schema is None:
            schema = db_info["name"]
        is_created = check_if_mysql_index_exists(cur, name, schema)
    else:
        raise NotImplemented(f"Database type `{db_info['type']}` is not supported")

    return is_created


def for_each_database(context, callback):
    """Run function callback for each dataase"""
    for db in context.databases.values():
        with db["conn"] as conn:
            with conn.cursor() as cur:
                callback(context, db["db_info"], cur)
