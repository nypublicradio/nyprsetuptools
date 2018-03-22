import os
import pytest


@pytest.fixture
def settings():
    return {
        'env': 'demo',
        'repository': 'nyprsetuptools-test',
        'cluster': 'utilities',
        'test_dir': os.path.dirname(__file__),
        'execution_role': 'ecsTaskExecutionRole',
    }
