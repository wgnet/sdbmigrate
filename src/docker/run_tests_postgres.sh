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

chown -R postgres:postgres /sdbmigrate
mkdir -p /var/log/postgresql
chown postgres:postgres /var/log/postgresql
sudo -u postgres /usr/lib/postgresql/${PG_MAJOR}/bin/pg_ctl -D \
    /etc/postgresql/${PG_MAJOR}/main -l \
    /var/log/postgresql/postgresql-${PG_MAJOR}-main.log start
sudo -u postgres psql -c "create role test_behave with SUPERUSER login password 'test_behave';"
cd /sdbmigrate

# Exclude mysql tests
# If we run only "postgres" tests here, then we can accidentially skip some tests that we
# forget to mark as mysql or postgres tests.
TOXENV=`sudo -u postgres tox -c /sdbmigrate/tox.ini --listenvs | grep -Ev "\-(mysql|all)" | tr '\n' ','`
echo "Running tox envs: $TOXENV"
sudo -u postgres -i tox -c /sdbmigrate/tox.ini -e $TOXENV
