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
import shutil
import tempfile

from behave import given


@given("migration dir")
def step_migrations_dir(context):
    try:
        shutil.rmtree(context.migration_dir)
    except Exception:
        pass
    relative_tmp_dir = "./tmp"
    if not os.path.exists(relative_tmp_dir):
        os.mkdir(relative_tmp_dir)

    context.working_dir = tempfile.mkdtemp(prefix="test_sdbmigrate_", dir=relative_tmp_dir)
    context.migration_dir = os.path.join(context.working_dir, "migrations")
    os.mkdir(context.migration_dir)
