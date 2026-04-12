from app import create_app
import pytest


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)

    with app.test_client() as test_client:
        yield test_client
