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
import json


class DbType:
    postgres = "postgres"
    mysql = "mysql"


def get_sdbmigrate_sharding_state(db_info, cur, schema_name=None):
    if schema_name:
        sql = f"SELECT shard_count, shard_ids from {schema_name}._sdbmigrate_sharding_state WHERE id=0"
    else:
        sql = "SELECT shard_count, shard_ids from _sdbmigrate_sharding_state WHERE id=0"

    cur.execute(sql)
    res = cur.fetchone()
    shard_ids = res[1]
    if db_info["type"] == DbType.mysql:
        shard_ids = json.loads(shard_ids)
    state = {
        "shard_count": res[0],
        "shard_ids": shard_ids,
    }
    return state
