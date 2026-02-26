import pytest
import warnings
import agentci


def pytest_configure(config):
    warnings.filterwarnings(
        "ignore",
        message="Pydantic serializer warnings",
        category=UserWarning,
    )

