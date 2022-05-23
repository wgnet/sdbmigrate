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
import sys

import yaml
import subprocess32 as subprocess   # backport of py3 subprocess for py27

from behave import given, then

SDB_MIGRATE_RUN_TIMEOUT = 10


def run_sdbmigrate(context, args=""):
    cmd = [
        "coverage",
        "run",
        "-p",
        "--include=bin/sdbmigrate.py",
        "./bin/sdbmigrate.py",
        "-d",
        context.migration_dir,
        "-c",
        context.sdbmigrate_config_path,
    ]
    if args:
        cmd += str(args).split(" ")

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stdout, stderr = p.communicate(timeout=SDB_MIGRATE_RUN_TIMEOUT)
    return p.returncode, str(stdout), str(stderr)


@given("successful sdbmigrate.py run with defaults")
def step_impl(context):
    res = run_sdbmigrate(context)

    if res[0] != 0:
        sys.stdout.write(res[1])
        sys.stderr.write(res[2])
        raise Exception("Expected success got retcode=%d" % res[0])

    context.last_migrate_res = {"ret": res[0], "out": res[1], "err": res[2]}


@given("successful sdbmigrate.py run with dry-run")
def step_impl(context):
    res = run_sdbmigrate(context, args="--dry-run")

    if res[0] != 0:
        sys.stdout.write(res[1])
        sys.stderr.write(res[2])
        raise Exception("Expected success got retcode=%d" % res[0])

    context.last_migrate_res = {"ret": res[0], "out": res[1], "err": res[2]}


@given("successful sdbmigrate.py run with args {args}")
def step_impl(context, args):
    res = run_sdbmigrate(context, args=args)

    if res[0] != 0:
        sys.stdout.write(res[1])
        sys.stderr.write(res[2])
        raise Exception("Expected success got retcode=%d" % res[0])

    context.last_migrate_res = {"ret": res[0], "out": res[1], "err": res[2]}


@given("failed sdbmigrate.py run with defaults")
def step_impl(context):
    res = run_sdbmigrate(context)
    context.last_migrate_res = {"ret": res[0], "out": res[1], "err": res[2]}


@then('sdbmigrate.py "{result}"')  # noqa
def step_impl(context, result):
    if not context.last_migrate_res:
        raise Exception("No sdbmigrate run detected in current context")

    if result == "failed" and context.last_migrate_res["ret"] == 0:
        sys.stdout.write(str(context.last_migrate_res["out"]))
        sys.stderr.write(str(context.last_migrate_res["err"]))
        raise Exception("Expected failure got success")
    elif result == "succeeded" and context.last_migrate_res["ret"] != 0:
        sys.stdout.write(str(context.last_migrate_res["out"]))
        sys.stderr.write(str(context.last_migrate_res["err"]))
        raise Exception("Expected success got retcode=" "%d" % context.last_migrate_res["ret"])
    elif result not in ["failed", "succeeded"]:
        raise Exception("Incorrect step arguments")


@then("sdbmigrate.py failed with {error}")
def step_impl(context, error):
    if context.last_migrate_res["ret"] == 0:
        sys.stdout.write(str(context.last_migrate_res["out"]))
        sys.stderr.write(str(context.last_migrate_res["err"]))
        raise Exception("sdbmigrate.py is not failed")
    actual_error = context.last_migrate_res["err"]
    if error not in actual_error:
        sys.stdout.write(str(context.last_migrate_res["out"]))
        sys.stderr.write(str(context.last_migrate_res["err"]))
        raise Exception("sdbmigrate.py is failed with other error, expected `{}`".format(error))
