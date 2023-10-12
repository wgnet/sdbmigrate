"""Tool for applying DB schema changes on sharded databases"""

from setuptools import setup

setup(
    name="sdbmigrate",
    version="1.1.0",
    author="Aliaksei Ramanau",
    author_email="drednout.by@gmail.com",
    url="https://github.com/wgnet/sdbmigrate",
    include_package_data=True,
    install_requires=["pyyaml", "sqlparse >= 0.3.1"],
    packages=[''],
    extras_require={
        # psycopg2 from version 2.9 breaks sdbmigrate, see https://github.com/psycopg/psycopg2/issues/941
        "postgres": ["psycopg2 <= 2.8.6"],
        "mysql": ["mysqlclient"],
    },
    scripts=["bin/sdbmigrate.py"],
)
