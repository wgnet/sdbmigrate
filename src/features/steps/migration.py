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

from behave import given


@given("migrations")  # noqa
def step_impl(context):
    for row in context.table:
        path = os.path.join(context.migration_dir, row["file"])
        code = row["code"]
        if context.text:
            code = row["code"].replace("%context.text%", context.text.strip())

        with open(path, "w") as f:
            f.write(code.replace("\\n", "\n"))


@given("add migration {name}")  # noqa
def step_impl(context, name):
    path = os.path.join(context.migration_dir, name)
    code = context.text.strip()
    with open(path, "w") as f:
        f.write(code.replace("\\n", "\n"))
