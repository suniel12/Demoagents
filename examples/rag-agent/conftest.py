import pytest
import warnings
import ciagent


def pytest_configure(config):
    warnings.filterwarnings(
        "ignore",
        message="Pydantic serializer warnings",
        category=UserWarning,
    )

