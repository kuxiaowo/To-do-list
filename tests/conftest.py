import pytest


@pytest.fixture(autouse=True)
def central_account_service(monkeypatch):
    monkeypatch.setattr("nethub_status.read_account_status", lambda *args: {"active": True, "emailVerified": True})
