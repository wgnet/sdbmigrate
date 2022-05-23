#!/bin/sh
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

set -e

# Start MySQL
mysqld_safe &
sleep 3

echo "CREATE DATABASE IF NOT EXISTS sdbmigrate1_behave; \
    CREATE DATABASE IF NOT EXISTS sdbmigrate2_behave; \
    CREATE USER IF NOT EXISTS 'test_behave'@'%' IDENTIFIED BY 'test_behave'; \
    GRANT ALL PRIVILEGES ON *.* TO 'test_behave'@'%'; \
    FLUSH PRIVILEGES;" | mysql -u root

cd /sdbmigrate

# Exclude postgres tests to ensure that.
# If we run only "mysql" tests here, then we can accidentially skip some tests that we
# forget to mark as mysql or postgres tests.
TOXENV=`tox -c /sdbmigrate/tox.ini --listenvs | grep -Ev "\-(postgres|all)" | tr '\n' ','`
echo "Running tox envs: $TOXENV"
tox -c /sdbmigrate/tox.ini -e $TOXENV
