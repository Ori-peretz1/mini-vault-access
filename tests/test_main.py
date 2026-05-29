import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import main
from database import (
    clear_users_table,
    clear_safes_table,
    clear_safe_members_table,
    clear_account_secrets_table,
    clear_accounts_table,
    clear_audit_logs,
    clear_sessions_table,
    get_session_from_db,
    create_session_in_db,
    clear_connections_table,
    get_connection_from_db,
)


client = TestClient(main.app)


@pytest.fixture(
    autouse=True
)  # autouse means that between every test , this reset ode will run again
def reset_state():
    clear_audit_logs()
    clear_account_secrets_table()
    clear_connections_table()
    clear_accounts_table()
    clear_sessions_table()
    clear_safe_members_table()
    clear_users_table()
    clear_safes_table()

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
    login_request = login()
    login_token = login_request.json()["access_token"]
    return client.post(
        f"/safes/{safe_id}/members",
        headers={"Authorization": f"Bearer {login_token}"},
        json={"user_id": user_id, "permission_level": permission_level},
    )


def create_account_as_admin(
    safe_id: str,
    target: str = "prod-linux-01",
    platform: str = "linux_ssh",
    secret_value: str = "fake-root-secret",
    username: str = "root",
):
    login_request = login()
    login_token = login_request.json()["access_token"]
    return client.post(
        f"/safes/{safe_id}/accounts",
        headers={"Authorization": f"Bearer {login_token}"},
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
    assert response.json()["detail"] == "Admin permission required"


def test_operator_with_read_cant_retrieve_secret():
    create_admin()
    create_operator()
    create_safe_as_admin()
    create_account_as_admin(safe_id="s_1")
    add_member_as_admin(permission_level="read")
    login_response = login(username="Bob", password="123456")
    token = login_response.json()["access_token"]
    response = client.post(
        "/safes/s_1/accounts/a_1/retrieve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized"

    logs_response = client.get(
        "/audit-logs",
        headers=auth_header_for_admin(),
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
    login_response = login()
    token = login_response.json()["access_token"]
    response = client.post(
        "/safes/s_1/accounts/a_1/retrieve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "account_id": "a_1",
        "secret_value": "fake-root-secret",
        "secret_version": 1,
    }

    logs_response = client.get(
        "/audit-logs",
        headers={"Authorization": f"Bearer {token}"},
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
    login_response = login(username="Bob", password="123456")
    token = login_response.json()["access_token"]
    response = client.post(
        "/safes/s_1/accounts/a_1/retrieve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "account_id": "a_1",
        "secret_value": "fake-root-secret",
        "secret_version": 1,
    }

    logs_response = client.get(
        "/audit-logs",
        headers=auth_header_for_admin(),
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
    data = response.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 20

    session = get_session_from_db(data["access_token"])

    assert session is not None
    assert session.user_id == "u_1"
    assert session.is_revoked is False


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


def test_operator_member_can_get_safe_by_id():
    create_admin()
    create_operator()
    create_safe_as_admin()
    add_member_as_admin(permission_level="read")
    response = client.get(
        "/safes/s_1",
        headers=auth_header(username="Bob", password="123456"),
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": "s_1",
        "name": "Production Linux Servers",
        "safe_type": "linux_accounts",
        "description": "Privileged Linux accounts",
    }


def test_non_member_operator_cant_get_safe_by_id():
    create_admin()
    create_operator()
    create_safe_as_admin()
    response = client.get(
        "/safes/s_1",
        headers=auth_header(username="Bob", password="123456"),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized"


def test_auditor_can_retrieve_secret():
    create_admin()
    create_auditor()
    create_safe_as_admin()
    create_account_as_admin(safe_id="s_1")
    response = client.post(
        "/safes/s_1/accounts/a_1/retrieve",
        headers=auth_header(username="Dana", password="123456"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Unauthorized"

    logs_response = client.get(
        "/audit-logs",
        headers=auth_header_for_admin(),
    )

    assert logs_response.status_code == 200
    logs = logs_response.json()

    assert len(logs) == 1
    assert logs[0]["actor_user_id"] == "u_2"
    assert logs[0]["action"] == "retrieve_secret"
    assert logs[0]["safe_id"] == "s_1"
    assert logs[0]["account_id"] == "a_1"
    assert logs[0]["success"] is False
    assert (
        logs[0]["message"]
        == "Unauthorized u_2 tried to retrieved secret for account a_1"
    )


def test_operator_cannot_read_audit_logs():
    create_operator()

    response = client.get(
        "/audit-logs",
        headers=auth_header(username="Bob"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Only admin can get logs"


def test_safes_with_invalid_token_returns_401():
    response = client.get(
        "/safes",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong or expired token"


def test_admin_can_get_members_of_safe():
    create_admin()
    create_operator()
    create_safe_as_admin()
    add_member_as_admin(safe_id="s_1", user_id="u_2", permission_level="use")

    response = client.get(
        "/safes/s_1/members",
        headers=auth_header_for_admin(),
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "user_id": "u_2",
            "safe_id": "s_1",
            "permission_level": "use",
        }
    ]


def test_operator_cannot_get_members_of_safe():
    create_admin()
    create_operator()
    create_safe_as_admin()
    add_member_as_admin(safe_id="s_1", user_id="u_2", permission_level="use")

    response = client.get(
        "/safes/s_1/members",
        headers=auth_header(username="Bob"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin permission required"


def test_revoke_update_session():
    create_admin()
    login_response = login()
    assert login_response.status_code == 200
    data = login_response.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 20
    token = data["access_token"]
    logout_response = client.post(
        "/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert logout_response.status_code == 200
    assert logout_response.json()["user_id"] == "u_1"
    assert logout_response.json()["logout_msg"] == "u_1 logged out successfully"
    session = get_session_from_db(data["access_token"])

    assert session is not None
    assert session.is_revoked is True


def test_logged_out_token_cannot_access_me():
    create_admin()
    login_response = login()
    data = login_response.json()
    token = data["access_token"]
    assert login_response.status_code == 200
    log_out_response = client.post(
        "/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert log_out_response.status_code == 200
    assert log_out_response.json()["user_id"] == "u_1"
    assert log_out_response.json()["logout_msg"] == "u_1 logged out successfully"
    me_response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 401
    assert me_response.json()["detail"] == "Wrong or expired token"


def test_logout_without_token_returns_401():
    create_admin()
    login()
    logout_response = client.post(
        "/logout",
    )
    assert logout_response.status_code == 401
    assert logout_response.json()["detail"] == "Missing authorization header"


def test_logout_with_wrong_token_returns_401():
    create_admin()
    login()
    logout_response = client.post(
        "/logout", headers={"Authorization": "bearer invalid token"}
    )
    assert logout_response.status_code == 401
    assert logout_response.json()["detail"] == "Wrong or expired token"


def test_login_create_session_with_expires_at():
    create_admin()
    before_login = datetime.now(timezone.utc)

    login_response = login()

    after_login = datetime.now(timezone.utc)

    assert login_response.status_code == 200
    login_token = login_response.json()["access_token"]
    session = get_session_from_db(login_token)
    assert session is not None
    assert session.expires_at is not None
    assert session.is_revoked is False

    expires_at = datetime.fromisoformat(session.expires_at)

    expected_min_expires_at = before_login + timedelta(
        minutes=main.TOKEN_SESSION_TIME_MINUTES
    )
    expected_max_expires_at = after_login + timedelta(
        minutes=main.TOKEN_SESSION_TIME_MINUTES
    )

    assert expected_min_expires_at <= expires_at <= expected_max_expires_at


def test_check_non_expired_token_can_acess_me():
    create_admin()
    login_response = login()
    token = login_response.json()["access_token"]
    assert login_response.status_code == 200
    me_response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json() == {
        "id": "u_1",
        "username": "Ori",
        "role": "admin",
        "state": "active",
    }


def test_check_expired_token_cannot_access_me():
    create_admin()
    token = "expired test token"
    create_time = datetime.now(timezone.utc) - timedelta(minutes=31)
    expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    create_session_in_db(
        user_id="u_1",
        token=token,
        created_at=create_time.isoformat(),
        expires_at=expires_at.isoformat(),
    )

    me_response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 401
    assert me_response.json()["detail"] == "Wrong or expired token"


def test_admin_can_start_connection_session():
    create_admin()
    create_safe_as_admin()
    create_account_as_admin(safe_id="s_1")
    login_response = login()
    token = login_response.json()["access_token"]
    connection_response = client.post(
        "/safes/s_1/accounts/a_1/connect", headers={"Authorization": f"Bearer {token}"}
    )
    assert connection_response.status_code == 200
    assert connection_response.json()["safe_id"] == "s_1"
    assert connection_response.json()["status"] == "active"

    connection = get_connection_from_db("connection_1")

    assert connection is not None
    assert connection.connection_id == "connection_1"
    assert connection.safe_id == "s_1"
    assert connection.account_id == "a_1"
    assert connection.actor_user_id == "u_1"
    assert connection.status.value == "active"


def test_operator_with_use_permission_can_start_connection():
    create_admin()
    create_safe_as_admin()
    create_operator()
    create_account_as_admin(safe_id="s_1")
    add_member_as_admin()
    connection_response = client.post(
        "/safes/s_1/accounts/a_1/connect", headers=auth_header(username="Bob")
    )

    assert connection_response.status_code == 200
    assert connection_response.json()["safe_id"] == "s_1"
    assert connection_response.json()["status"] == "active"

    connection = get_connection_from_db("connection_1")
    assert connection is not None
    assert connection.connection_id == "connection_1"
    assert connection.account_id == "a_1"
    assert connection.actor_user_id == "u_2"
    assert connection.status.value == "active"


def test_operator_with_manage_permission_can_start_connection():
    create_admin()
    create_safe_as_admin()
    create_operator()
    create_account_as_admin(safe_id="s_1")
    add_member_as_admin(permission_level="manage")
    connection_response = client.post(
        "/safes/s_1/accounts/a_1/connect", headers=auth_header(username="Bob")
    )

    assert connection_response.status_code == 200
    assert connection_response.json()["safe_id"] == "s_1"
    assert connection_response.json()["status"] == "active"

    connection = get_connection_from_db("connection_1")
    assert connection is not None
    assert connection.connection_id == "connection_1"
    assert connection.account_id == "a_1"
    assert connection.actor_user_id == "u_2"
    assert connection.status.value == "active"


def test_successful_connect_creates_audit_log():
    create_admin()
    create_safe_as_admin()
    create_operator()
    create_account_as_admin(safe_id="s_1")
    add_member_as_admin(permission_level="manage")
    connection_response = client.post(
        "/safes/s_1/accounts/a_1/connect", headers=auth_header(username="Bob")
    )

    assert connection_response.status_code == 200
    assert connection_response.json()["safe_id"] == "s_1"
    assert connection_response.json()["status"] == "active"

    connection = get_connection_from_db("connection_1")
    assert connection is not None
    assert connection.connection_id == "connection_1"
    assert connection.account_id == "a_1"
    assert connection.actor_user_id == "u_2"
    assert connection.status.value == "active"

    audit_log_response = client.get("/audit-logs", headers=auth_header_for_admin())

    assert audit_log_response.status_code == 200
    logs = audit_log_response.json()
    assert len(logs) == 1
    assert logs[0]["actor_user_id"] == "u_2"
    assert logs[0]["action"] == "connect_account"
    assert logs[0]["safe_id"] == "s_1"
    assert logs[0]["account_id"] == "a_1"
    assert logs[0]["success"] is True
    assert (
        logs[0]["message"]
        == "u_2 started connection session connection_1 for account a_1 without exposing the secret"
    )


def test_unauthorized_connect_creates_failed_audit_log():
    create_admin()
    create_safe_as_admin()
    create_operator()
    create_account_as_admin(safe_id="s_1")
    add_member_as_admin(permission_level="read")

    connection_response = client.post(
        "/safes/s_1/accounts/a_1/connect", headers=auth_header(username="Bob")
    )

    assert connection_response.status_code == 403
    assert connection_response.json()["detail"] == "Unauthorized"

    log_response = client.get("/audit-logs", headers=auth_header(username="Bob"))

    assert log_response.status_code == 403
    assert log_response.json()["detail"] == "Only admin can get logs"

    logs_res = client.get("/audit-logs", headers=auth_header_for_admin())

    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) == 1
    assert logs[0]["actor_user_id"] == "u_2"
    assert logs[0]["action"] == "connect_account"
    assert logs[0]["success"] is False
    assert logs[0]["safe_id"] == "s_1"
    assert logs[0]["account_id"] == "a_1"
    assert logs[0]["message"] == "Unauthorized u_2 tried to connect to account a_1"
