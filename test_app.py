import pytest  # type: ignore
import re

import app as hauki


@pytest.fixture
def client():
    hauki.app.testing = True
    client = hauki.app.test_client()

    with client:
        yield client
    # request context stays alive until the fixture is closed


def test_csrf_token_generate():
    with hauki.app.test_request_context():
        token = hauki.csrf_token()
        assert token != ''


def test_csrf_token_save():
    with hauki.app.test_request_context() as context:
        token = hauki.csrf_token()
        assert token == context.session['csrf_token']


def test_csrf_token_load():
    with hauki.app.test_request_context() as context:
        context.session['csrf_token'] = 'test token'
        assert hauki.csrf_token() == 'test token'
