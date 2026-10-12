import os

# Settings are instantiated on import, so select the test environment first.
os.environ["MAN_ENV"] = "test"

pytest_plugins = (
    "tests.fixtures.base",
    "tests.fixtures.database",
    "tests.fixtures.random_objects",
)
