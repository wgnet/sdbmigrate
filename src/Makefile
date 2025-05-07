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
POSTGRES_MAJOR_VERSIONS = 11 13 14 15
MYSQL_VERSIONS = 8.0 8.4-lts

.PHONY: test

test: test_postgres test_mysql test_linters

test_postgres: build_image_postgres
	@- $(foreach PG_MAJOR,$(POSTGRES_MAJOR_VERSIONS), \
		echo "Run sdbmigrate test for PostgreSQL $(PG_MAJOR)"; \
		docker run -t sdbmigrate_postgres_$(PG_MAJOR) ;\
	)

build_image_postgres:
	@- $(foreach PG_MAJOR,$(POSTGRES_MAJOR_VERSIONS), \
		echo "Build image for PostgreSQL $(PG_MAJOR)"; \
		docker build \
			-f docker/Dockerfile.postgres \
			--target sdbmigrate_postgres \
			-t "sdbmigrate_postgres_$(PG_MAJOR)" \
			--build-arg PG_MAJOR=$(PG_MAJOR) . ;\
	)

test_mysql: build_image_mysql
	@- $(foreach MYSQL_VERSION,$(MYSQL_VERSIONS), \
		echo "Run sdbmigrate test for MySQL $(MYSQL_VERSION)"; \
		docker run -t "sdbmigrate_mysql_$(MYSQL_VERSION)" ;\
	)


build_image_linters: build_image_linters
	echo "Build image for running static checkers(pylint, etc)"; 
	docker build \
		-f docker/Dockerfile.linters \
		-t "sdbmigrate_linters" . ;\

build_image_mysql:
	@- $(foreach MYSQL_VERSION,$(MYSQL_VERSIONS), \
		echo "Build image for MySQL $(MYSQL_VERSION)"; \
		docker build \
			-f docker/Dockerfile.mysql \
			--target sdbmigrate_mysql \
			-t "sdbmigrate_mysql_$(MYSQL_VERSION)" \
			--build-arg MYSQL_VERSION=$(MYSQL_VERSION) . ;\
	)

test_linters: build_image_linters
	echo "Run sdbmigrate linters";
	docker run -t "sdbmigrate_linters" ;


lint:
	tox -e pylint,flake8 $(TOX_ARGS)

black:
	black --line-length=100 bin features setup.py

clean:
	-rm -rf tmp/*
	-rm .coverage.*
