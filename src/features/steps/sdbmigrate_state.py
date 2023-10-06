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
import os

from behave import then
from features.steps.common import DbType, get_sdbmigrate_sharding_state


@then("database has initialized sdbmigrate state schema")
def step_impl(context):
    verify_sdbmigrate_state_schema(context)


@then('database has initialized sdbmigrate state schema in schema "{schema_name}"')
def step_impl(context, schema_name):
    verify_sdbmigrate_state_schema(context, schema_name)


def verify_sdbmigrate_state_schema(context, schema_name=None):
    expected_sdbmigrate_state_tables = [
        "_sdbmigrate_migrations",
        "_sdbmigrate_sharding_state",
        "_sdbmigrate_env",
    ]
    for db_info in context.databases.values():
        with db_info["conn"] as conn:
            with conn.cursor() as cur:
                for table in expected_sdbmigrate_state_tables:
                    if schema_name:
                        sql = f"SELECT 1 from {schema_name}.{table}"
                    else:
                        sql = f"SELECT 1 from {table}"

                    cur.execute(sql)


@then("sdbmigrate state has correct migrations")
def step_impl(context):
    verify_sdbmigrate_state_migrations(context)


@then('sdbmigrate state has correct migrations in schema "{schema_name}"')
def step_impl(context, schema_name):
    verify_sdbmigrate_state_migrations(context, schema_name)


def verify_sdbmigrate_state_migrations(context, schema_name=None):
    migrations = os.listdir(context.migration_dir)
    for db_info in context.databases.values():
        with db_info["conn"] as conn:
            with conn.cursor() as cur:
                for migration_name in migrations:
                    if schema_name:
                        sql = f"""
                            SELECT count(1) from
                            {schema_name}._sdbmigrate_migrations WHERE
                            migration_name=%(migration_name)s
                        """
                    else:
                        sql = "SELECT count(1) from _sdbmigrate_migrations WHERE migration_name=%(migration_name)s"
                    cur.execute(sql, {"migration_name": migration_name})
                    migration_in_db = cur.fetchone()[0]
                    assert migration_in_db == 1, "Migration {} was not applied".format(
                        migration_name
                    )


def cast_value(raw_value, type_as_str):
    t = eval(type_as_str)
    value = t(raw_value)
    return value


@then("sdbmigrate state has correct env")
def step_impl(context):
    verify_migration_env(context)


@then('sdbmigrate state has correct env in schema "{schema_name}"')
def step_impl(context, schema_name):
    verify_migration_env(context, schema_name)


def verify_migration_env(context, schema_name=None):
    env = context.sdbmigrate_config.get("env", {})
    for db in context.databases.values():
        with db["conn"] as conn:
            with conn.cursor() as cur:
                for key, param in env.items():
                    if db["db_info"]["type"] == DbType.mysql:
                        sql = "SELECT value, type from _sdbmigrate_env WHERE `key`=%(key)s"
                    else:
                        if schema_name is None:
                            schema_name = 'public'
                        sql = f"SELECT value, type from {schema_name}._sdbmigrate_env WHERE key=%(key)s"
                    cur.execute(sql, {"key": key})
                    res = cur.fetchone()
                    assert res, "Unable to find in DB env param {key}:{param}".format(
                        key=key, param=param
                    )

                    db_value = res[0]
                    db_type = res[1]

                    config_type = param.get("type", "str")
                    msg = (
                        "Param with key={key} has different types in config: `{config_type}` "
                        "and db: `{db_type}`"
                    ).format(key=key, db_type=db_type, config_type=config_type)
                    assert db_type == config_type, msg

                    msg = (
                        "Param with key={key} has different values in config: `{config_value}` "
                        "and db: `{db_value}`"
                    ).format(key=key, db_value=db_value, config_value=param["value"])
                    assert cast_value(db_value, db_type) == param["value"], msg


@then('sdbmigrate state has correct auto sharding in schema "{schema_name}"')
def step_impl(context, schema_name):
    verify_migration_sharding_state(context, schema_name)


def verify_migration_sharding_state(context, schema_name=None):
    shard_count = context.sdbmigrate_config["shard_count"]
    shard_on_db = context.sdbmigrate_config["shard_on_db"]
    all_shard_ids = []

    for db in context.databases.values():
        with db["conn"] as conn:
            with conn.cursor() as cur:
                sharding_state = get_sdbmigrate_sharding_state(db["db_info"], cur, schema_name)
                db_shard_count = sharding_state["shard_count"]
                db_shard_ids = sharding_state["shard_ids"]
                assert db_shard_count == shard_count, "shard_count mismatch in config and db"
                assert isinstance(db_shard_ids, list), "shard_ids must be list"
                assert len(db_shard_ids) == shard_on_db, "shard_on_db mismatch in config and db"
                all_shard_ids.extend(db_shard_ids)

    assert (
            len(all_shard_ids) == shard_count
    ), "total shard_count in DB shard_ids should be equal to config shard_count"


@then("sdbmigrate state has correct auto sharding")
def step_impl(context):
    verify_migration_sharding_state(context)


def compare_manual_shard_info(db_shard_ids, config_shard_ids):
    for shard_range in config_shard_ids:
        for shard_id in range(shard_range["min"], shard_range["max"] + 1):
            assert (
                shard_id in db_shard_ids
            ), "shard_id={shard_id} is not in DB range `{db_shard_ids}`".format(
                shard_id=shard_id, db_shard_ids=db_shard_ids
            )


@then("sdbmigrate state has correct manual sharding")
def step_impl(context):
    verify_migration_state_manual_sharding(context)


@then('sdbmigrate state has correct manual sharding in schema "{schema_name}"')
def step_impl(context, schema_name):
    verify_migration_state_manual_sharding(context, schema_name)


def verify_migration_state_manual_sharding(context, schema_name=None):
    shard_count = context.sdbmigrate_config["shard_count"]
    all_shard_ids = []

    for db in context.databases.values():
        with db["conn"] as conn:
            with conn.cursor() as cur:
                sharding_state = get_sdbmigrate_sharding_state(db["db_info"], cur, schema_name)
                db_shard_count = sharding_state["shard_count"]
                db_shard_ids = sharding_state["shard_ids"]
                compare_manual_shard_info(db_shard_ids, db["db_info"]["shards"])

                assert db_shard_count == shard_count, "shard_count mismatch in config and db"
                all_shard_ids.extend(db_shard_ids)

    assert (
        len(all_shard_ids) == shard_count
    ), "total shard_count in DB shard_ids should be equal to config shard_count"
