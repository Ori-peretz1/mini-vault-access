import pytest
from fastapi.testclient import TestClient
import main
from database import (
    clear_users_table,
    clear_safes_table,
    clear_safe_members_table,
    clear_account_secrets_table,
    clear_accounts_table,
    clear_audit_logs,
)


client = TestClient(main.app)


@pytest.fixture(
    autouse=True
)  # autouse means that between every test , this reset ode will run again
def reset_state():
    clear_audit_logs()
    clear_account_secrets_table()
    clear_accounts_table()
    clear_safe_members_table()
    clear_users_table()
    clear_safes_table()

    main.token_store.clear()

    yield  # means till here the reset test code


# helper function:
def create_user(username: str, role: str, password: str):
    return client.post(
        "/users",
        json={"username": username, "role": role, "password": password},
    )


def create_admin():
    return create_user("Ori", "admin", "123456")


def create_operator():
    return create_user("Bob", "operator", "123456")


def create_auditor():
    return create_user("Dana", "auditor", "123456")


def auth_header_for_admin() -> dict[str, str]:
    login_response = login(username="Ori", password="123456")
    token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


def auth_header(username: str, password: str = "123456") -> dict[str, str]:
    login_response = login(username=username, password=password)
    token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }


def create_safe_as_admin(
    name: str = "Production Linux Servers",
    safe_type: str = "linux_accounts",
    description: str = "Privileged Linux accounts",
):
    return client.post(
        "/safes",
        headers=auth_header_for_admin(),
        json={
            "name": name,
            "safe_type": safe_type,
            "description": description,
        },
    )


def login(username: str = "Ori", password: str = "123456"):
    return client.post(
        "/login",
        json={
            "username": username,
            "password": password,
        },
    )


def add_member_as_admin(
    safe_id: str = "s_1", user_id: str = "u_2", permission_level: str = "use"
):
    return client.post(
        f"/safes/{safe_id}/members",
        headers={"x-user-id": "u_1"},
        json={"user_id": user_id, "permission_level": permission_level},
    )


def create_account_as_admin(
    safe_id: str,
    target: str = "prod-linux-01",
    platform: str = "linux_ssh",
    secret_value: str = "fake-root-secret",
    username: str = "root",
):
    return client.post(
        f"/safes/{safe_id}/accounts",
        headers={"x-user-id": "u_1"},
        json={
            "username": username,
            "target": target,
            "platform": platform,
            "secret_value": secret_value,
        },
    )


def test_get_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_admin_user():
    response = client.post(
        "/users",
        json={"username": "ori", "role": "admin", "password": "123456"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": "u_1",
        "username": "ori",
        "role": "admin",
        "state": "active",
    }


def test_create_safe_without_header():
    create_admin()
    response = client.post(
        "/safes",
        json={
            "name": "Production Linux Servers",
            "safe_type": "linux_accounts",
            "description": "Privileged Linux accounts",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authorization header"


def test_admin_can_create_safe():
    create_admin()
    response = create_safe_as_admin()
    assert response.status_code == 200
    assert response.json() == {
        "id": "s_1",
        "name": "Production Linux Servers",
        "safe_type": "linux_accounts",
        "description": "Privileged Linux accounts",
    }


def test_operator_cant_create_safe():
    create_operator()
    response = client.post(
        "/safes",
        headers=auth_header(username="Bob"),
        json={
            "id": "s_1",
            "name": "Production Linux Servers",
            "safe_type": "linux_accounts",
            "description": "Privileged Linux accounts",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Only admin can create safe"


def test_operator_with_read_cant_retrieve_secret():
    create_admin()
    create_operator()
    create_safe_as_admin()
    create_account_as_admin(safe_id="s_1")
    add_member_as_admin(permission_level="read")
    response = client.post(
        "/safes/s_1/accounts/a_1/retrieve",
        headers={"x-user-id": "u_2"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized"

    logs_response = client.get(
        "/audit-logs",
        headers={"x-user-id": "u_1"},
    )

    assert logs_response.status_code == 200
    logs = logs_response.json()
    assert len(logs) == 1
    assert logs[0]["actor_user_id"] == "u_2"
    assert logs[0]["id"] == "log_1"
    assert logs[0]["action"] == "retrieve_secret"
    assert logs[0]["safe_id"] == "s_1"
    assert logs[0]["account_id"] == "a_1"
    assert logs[0]["success"] is False
    assert (
        logs[0]["message"]
        == "Unauthorized u_2 tried to retrieved secret for account a_1"
    )


def test_admin_can_retrieve_secret():
    create_admin()
    create_operator()
    create_safe_as_admin()
    create_account_as_admin(safe_id="s_1")
    response = client.post(
        "/safes/s_1/accounts/a_1/retrieve",
        headers={"x-user-id": "u_1"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "account_id": "a_1",
        "secret_value": "fake-root-secret",
        "secret_version": 1,
    }
    logs_response = client.get(
        "/audit-logs",
        headers={"x-user-id": "u_1"},
    )
    assert logs_response.status_code == 200

    logs = logs_response.json()
    assert len(logs) == 1
    assert logs[0]["actor_user_id"] == "u_1"
    assert logs[0]["id"] == "log_1"
    assert logs[0]["action"] == "retrieve_secret"
    assert logs[0]["safe_id"] == "s_1"
    assert logs[0]["account_id"] == "a_1"
    assert logs[0]["success"] is True
    assert logs[0]["message"] == "u_1 retrieved secret for account a_1 from safe s_1"


def test_operator_with_use_permission_can_retrieve_secret():
    create_admin()
    create_operator()
    create_safe_as_admin()
    create_account_as_admin(safe_id="s_1")
    add_member_as_admin(permission_level="use")

    response = client.post(
        "/safes/s_1/accounts/a_1/retrieve",
        headers={"x-user-id": "u_2"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "account_id": "a_1",
        "secret_value": "fake-root-secret",
        "secret_version": 1,
    }

    logs_response = client.get(
        "/audit-logs",
        headers={"x-user-id": "u_1"},
    )

    assert logs_response.json()[0]["success"] is True
    assert (
        logs_response.json()[0]["message"]
        == "u_2 retrieved secret for account a_1 from safe s_1"
    )
    assert logs_response.json()[0]["action"] == "retrieve_secret"


def test_login_return_token():
    create_admin()
    response = login()
    assert response.status_code == 200
    assert response.json() == {"access_token": "token_u_1", "token_type": "bearer"}


def test_me_with_valid_token():
    create_admin()
    login_request = login()
    login_data = login_request.json()
    token = login_data["access_token"]
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {
        "id": "u_1",
        "username": "Ori",
        "role": "admin",
        "state": "active",
    }


def test_me_without_token_return_401():
    response = client.get("/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authorization header"


def test_admin_can_get_safes_with_token():
    create_admin()
    login_request = login()
    login_token = login_request.json()["access_token"]
    create_safe_as_admin()
    response = client.get(
        "/safes",
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "s_1",
            "name": "Production Linux Servers",
            "safe_type": "linux_accounts",
            "description": "Privileged Linux accounts",
        }
    ]


def test_me_invalid_token_get_401():
    response = client.get(
        "/me",
        headers={"Authorization": "Bearer Bad_token"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong or expired token"
