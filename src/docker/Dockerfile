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
# vim:set ft=dockerfile:
###### Base image
FROM ubuntu:focal AS base

# make the "en_US.UTF-8" locale so postgres will be utf-8 enabled by default
RUN apt-get update && apt-get install -y software-properties-common locales && \
    rm -rf /var/lib/apt/lists/* && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
ENV LANG en_US.utf8
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -o Acquire::AllowInsecureRepositories=true \
        -o Acquire::AllowDowngradeToInsecureRepositories=true update \
    && apt-get install -y \
        sudo \
        wget \
        libssl-dev \
        python3-pip \
        python2.7-dev \
        python3.8-dev \
    && pip3 install tox


###### MySQL image
FROM base AS sdbmigrate_mysql
ARG MYSQL_VERSION=5.7
ARG MYSQL_ATPCONF=mysql-apt-config_0.8.18-1_all.deb
RUN wget http://repo.mysql.com/$MYSQL_ATPCONF \
    && echo mysql-apt-config    mysql-apt-config/repo-codename  select  bionic | debconf-set-selections \
    && echo mysql-apt-config    mysql-apt-config/repo-distro    select  ubuntu | debconf-set-selections \
    && echo mysql-apt-config    mysql-apt-config/select-server  select  mysql-$MYSQL_VERSION | debconf-set-selections \
    && echo mysql-apt-config    mysql-apt-config/select-product select  Ok | debconf-set-selections \
    && dpkg -i $MYSQL_ATPCONF \
    && rm $MYSQL_ATPCONF \
    && apt-get update -q && apt-get install -y \
        default-libmysqlclient-dev \
        mysql-client=$MYSQL_VERSION.*-1ubuntu18.04 \
        mysql-community-server=$MYSQL_VERSION.*-1ubuntu18.04 \
        mysql-server=$MYSQL_VERSION.*-1ubuntu18.04
COPY ./ /sdbmigrate
CMD ["/sdbmigrate/docker/run_tests_mysql.sh"]


###### Postgres image
# explicitly set user/group IDs
FROM base AS sdbmigrate_postgres
ARG PG_MAJOR=13
RUN groupadd -r postgres --gid=1100 && useradd -r -d /var/lib/postgresql -g postgres --uid=1100 postgres
RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ focal-pgdg main' $PG_MAJOR > /etc/apt/sources.list.d/pgdg.list
RUN apt-get -o Acquire::AllowInsecureRepositories=true \
        -o Acquire::AllowDowngradeToInsecureRepositories=true update \
    && apt-get \
        -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold" \
        -o APT::Get::AllowUnauthenticated=true \
        install -y postgresql-common \
        libpq-dev \
        postgresql-$PG_MAJOR \
        postgresql-contrib-$PG_MAJOR
COPY ./ /sdbmigrate
ENV PG_MAJOR=$PG_MAJOR
CMD ["/sdbmigrate/docker/run_tests_postgres.sh"]
