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
import yaml

from behave import given


def load_config(filename):
    with open("features/configs/%s" % filename) as f:
        return f.read()


@given("{config_name}.yaml config")
def step_migrations_dir(context, config_name):
    context.sdbmigrate_config_text = load_config("{}.yaml".format(config_name))
    context.sdbmigrate_config = yaml.safe_load(context.sdbmigrate_config_text)
    context.sdbmigrate_config_path = os.path.join(context.working_dir, "sdbmigrate.yaml")
    with open(context.sdbmigrate_config_path, "w") as f:
        f.write(context.sdbmigrate_config_text)


@given("{config_name}.yaml config with updated region_id={region_id}")
def step_migrations_dir(context, config_name, region_id):
    context.sdbmigrate_config_text = load_config("{}.yaml".format(config_name))
    context.sdbmigrate_config = yaml.safe_load(context.sdbmigrate_config_text)
    context.sdbmigrate_config["env"]["region_id"]["value"] = int(region_id)
    context.sdbmigrate_config_path = os.path.join(context.working_dir, "sdbmigrate.yaml")
    with open(context.sdbmigrate_config_path, "w") as f:
        yaml.dump(context.sdbmigrate_config, f)
