"""Tool for applying DB schema changes on sharded databases"""

from setuptools import setup

setup(
    name="sdbmigrate",
    version="1.1.1",
    author="Alex Ramanau",
    author_email="a.ramanau.pl@gmail.com",
    url="https://github.com/alex-ramanau/sdbmigrate",
    include_package_data=True,
    install_requires=["pyyaml", "sqlparse >= 0.3.1"],
    packages=[''],
    extras_require={
        "postgres": ["psycopg2 >= 2.9.3"],
        "mysql": ["mysqlclient"],
    },
    scripts=["bin/sdbmigrate.py"],
)
