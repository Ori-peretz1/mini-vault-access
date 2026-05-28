from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import hashlib
import os
import secrets
from datetime import datetime, timezone, timedelta
from models import (
    AccountCreate,
    AccountResponse,
    AuditAction,
    AuditLogResponse,
    SafeCreate,
    SafeMemberCreate,
    SafeMemberResponse,
    SafePermissionLevel,
    SafeResponse,
    SecretRetrieveResponse,
    UserCreate,
    UserResponse,
    UserRole,
    UserState,
    UserRecord,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
)
from database import (
    db_init,
    get_all_users_from_db,
    get_user_from_db,
    create_user_in_db,
    get_next_user_id_from_db,
    create_safe_in_db,
    get_next_safe_id_from_db,
    get_safe_from_db,
    get_all_safes_from_db,
    get_user_by_username_from_db,
    get_safe_member_from_db,
    get_members_of_safe_from_db,
    get_safes_of_user_from_db,
    create_safe_member_in_db,
    get_account_from_db,
    get_accounts_of_safe_from_db,
    get_account_secret_from_db,
    get_next_account_id_from_db,
    create_account_in_db,
    create_account_secret_in_db,
    create_audit_log_in_db,
    get_next_audit_log_id,
    get_all_audit_logs_from_db,
    create_session_in_db,
    get_session_from_db,
    revoke_session_in_db,
)

TOKEN_SESSION_TIME_MINUTES = 30

# next_account_id = 1  # step 5
# next_audit_log_id = 1  # step 6


# safe_members: dict[tuple[str, str], SafeMemberResponse] = {} step 10-db with realtions


# accounts: dict[str, AccountResponse] = {}  # metadata - step 5 (of safe)
# account_secrets: dict[str, str] = {}  # sensitive info - step 5

# audit_logs: dict[str, AuditLogResponse] = {}
# Token = str
# UserId = str
# token_store: dict[Token, UserId] = {}  # step 9 tokens - from token to user id
bearer_scheme = HTTPBearer(auto_error=False)

app = FastAPI(title="Mini vault access project")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
db_init()


# def check_current_user(x_user_id: str | None) -> UserResponse:
#     if x_user_id is None:
#         raise HTTPException(status_code=401, detail="Missing X-User-Id header")
#     user_response = get_user_from_db(x_user_id)
#     if user_response is None:
#         raise HTTPException(status_code=401, detail="user id does not exist")
#     if user_response.state != UserState.active:
#         raise HTTPException(status_code=403, detail="user is not active")
#     return user_response


def check_current_user_by_token(
    credentials: HTTPAuthorizationCredentials | None,
) -> UserResponse:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Token type not compatible")
    token = credentials.credentials
    session = get_session_from_db(token=token)
    if session is None:
        raise HTTPException(status_code=401, detail="Wrong or expired token")
    if session.is_revoked:
        raise HTTPException(
            status_code=401, detail="Wrong or expired token"
        )  # case when user logout already
    if session.expires_at is not None:
        try:
            expires_at = datetime.fromisoformat(session.expires_at)

        except ValueError:
            raise HTTPException(status_code=401, detail="Wrong or expired token")

        if expires_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=401,
                detail="Wrong or expired token",
            )
    else:
        raise HTTPException(
            status_code=401,
            detail="Wrong or expired token",
        )
    user_id = session.user_id
    user = get_user_from_db(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User does'nt exist")
    if user.state != UserState.active:
        raise HTTPException(status_code=403, detail="User is inactive")
    return user


def hash_password(password: str) -> tuple[str, str]:  # helper function step 9
    salt = os.urandom(16)

    password_hash = hashlib.scrypt(
        password=password.encode(),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        dklen=32,
    )

    return salt.hex(), password_hash.hex()


def verify_password(
    password: str, salt_hex: str, stored_hash_hex: str
) -> bool:  # helper function - step 9
    salt = bytes.fromhex(salt_hex)

    password_hash = hashlib.scrypt(
        password=password.encode(),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        dklen=32,
    )

    return password_hash.hex() == stored_hash_hex


def user_is_admin(user: UserResponse) -> None:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin permission required")


def audit_log_create(
    actor_id: str,
    action: AuditAction,
    success: bool,
    msg: str,
    safe_id: str | None = None,
    account_id: str | None = None,
) -> AuditLogResponse:  # helper for creating audit -step 6
    id = get_next_audit_log_id()
    curr_log_id = f"log_{id}"
    audit_response = AuditLogResponse(
        id=curr_log_id,
        actor_user_id=actor_id,
        action=action,
        safe_id=safe_id,
        account_id=account_id,
        success=success,
        message=msg,
        time=datetime.now(timezone.utc).isoformat(),
    )
    create_audit_log_in_db(audit_response)
    return audit_response


def can_retrieve_secret(
    user: UserResponse, safe_id: str
) -> bool:  # helper function for checking if user can get sensitive info by set of rules of authorization - step 6
    if user.role == UserRole.admin:
        return True

    if user.role == UserRole.operator:
        safe_member = get_safe_member_from_db(safe_id, user.id)
        if safe_member is None:
            return False
        permission = safe_member.permission_level
        if (
            permission == SafePermissionLevel.manage
            or permission == SafePermissionLevel.use
        ):  # by the set of rules i decided that operator with "use" permission level and auditor cant retrieve secret
            return True

    return False


@app.get("/me")
def get_user_by_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UserResponse:
    return check_current_user_by_token(credentials)


@app.post(
    "/safes/{safe_id}/accounts/{account_id}/retrieve",
    summary="retrieving a secret from a safe",
)  # step 6
def retrieve_secret(
    safe_id: str,
    account_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> SecretRetrieveResponse:
    actor_user = check_current_user_by_token(credentials)
    # this case does not create audit log for now
    if get_safe_from_db(safe_id) is None:
        audit_log_create(
            actor_id=actor_user.id,
            action=AuditAction.retrieve_secret,
            success=False,
            msg="Safe does not exist",
            safe_id=safe_id,
            account_id=account_id,
        )
        raise HTTPException(status_code=404, detail="Safe does not exist")
    account = get_account_from_db(account_id)
    if account is None:
        audit_log_create(
            actor_id=actor_user.id,
            action=AuditAction.retrieve_secret,
            success=False,
            msg="Account does not exist",
            safe_id=safe_id,
            account_id=account_id,
        )
        raise HTTPException(status_code=404, detail="Account does not exist")
    if account.safe_id != safe_id:
        audit_log_create(
            actor_id=actor_user.id,
            action=AuditAction.retrieve_secret,
            success=False,
            msg="This account is not connected to this safe",
            safe_id=safe_id,
            account_id=account_id,
        )
        raise HTTPException(
            status_code=404, detail="This account is not connected to this safe"
        )
    secret_val = get_account_secret_from_db(account_id)
    if secret_val is None:
        raise HTTPException(status_code=404, detail="Secret does not exist")
    if can_retrieve_secret(actor_user, safe_id):
        audit_log_create(
            actor_id=actor_user.id,
            action=AuditAction.retrieve_secret,
            success=True,
            msg=f"{actor_user.id} retrieved secret for account {account_id} from safe {safe_id}",
            safe_id=safe_id,
            account_id=account_id,
        )
        secret_retrieve_response = SecretRetrieveResponse(
            account_id=account_id,
            secret_value=secret_val,
            secret_version=account.secret_version,
        )  # account can be in only one safe
        return secret_retrieve_response
    audit_log_create(
        actor_id=actor_user.id,
        action=AuditAction.retrieve_secret,
        success=False,
        msg=f"Unauthorized {actor_user.id} tried to retrieved secret for account {account_id}",
        safe_id=safe_id,
        account_id=account_id,
    )
    raise HTTPException(status_code=403, detail="Unauthorized")


@app.get("/audit-logs")  # step 6
def get_audit_logs(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> list[AuditLogResponse]:
    user = check_current_user_by_token(credentials)
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admin can get logs")
    return get_all_audit_logs_from_db()


@app.post(
    "/safes/{safe_id}/accounts", summary="adding account into specific safe"
)  # creating account in specific safe - step 5
def add_account_to_safe(
    safe_id: str,
    account_create: AccountCreate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AccountResponse:
    x_user = check_current_user_by_token(credentials)

    if get_safe_from_db(safe_id) is None:
        raise HTTPException(status_code=404, detail="No such safe")
    if x_user.role == UserRole.admin:
        curr_id_number = get_next_account_id_from_db()
        curr_id = f"a_{curr_id_number}"
        account_response = AccountResponse(
            id=curr_id,
            safe_id=safe_id,
            username=account_create.username,
            target=account_create.target,
            platform=account_create.platform,
            secret_version=1,
        )
        create_account_in_db(account_response)
        create_account_secret_in_db(curr_id, account_create.secret_value, 1)
        return account_response

    if (
        (x_user.role == UserRole.operator)
        and get_safe_member_from_db(safe_id, x_user.id) is not None
        and get_safe_member_from_db(safe_id, x_user.id).permission_level
        == SafePermissionLevel.manage
    ):
        curr_id_number = get_next_account_id_from_db()
        curr_id = f"a_{curr_id_number}"
        account_response = AccountResponse(
            id=curr_id,
            safe_id=safe_id,
            username=account_create.username,
            target=account_create.target,
            platform=account_create.platform,
            secret_version=1,
        )
        create_account_in_db(account_response)
        create_account_secret_in_db(curr_id, account_create.secret_value, 1)
        return account_response

    raise HTTPException(status_code=403, detail="Unauthorized")


@app.get(
    "/safes/{safe_id}/accounts", summary="get accounts of specific safe"
)  # get accounts of a specific safe - step 5
def get_accounts_of_safe(
    safe_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> list[AccountResponse]:
    x_user = check_current_user_by_token(credentials)
    if get_safe_from_db(safe_id) is None:
        raise HTTPException(status_code=404, detail="There is no such safe")
    list_of_accounts = get_accounts_of_safe_from_db(safe_id)
    if x_user.role == UserRole.admin:
        return list_of_accounts

    if x_user.role == UserRole.operator:
        if get_safe_member_from_db(safe_id, x_user.id) is None:
            raise HTTPException(status_code=403, detail="Unauthorized")
        else:
            return list_of_accounts

    raise HTTPException(status_code=403, detail="Unauthorized")


@app.get(
    "/safes/{safe_id}/accounts/{account_id}"
)  # getting meta data of account by account id - step 5
def get_account_from_safe(
    safe_id: str,
    account_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AccountResponse:
    x_user = check_current_user_by_token(credentials)
    if get_safe_from_db(safe_id) is None:
        raise HTTPException(status_code=404, detail="There is no such safe")
    account = get_account_from_db(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="There is no such account")
    if x_user.role == UserRole.admin:
        if account.safe_id == safe_id:
            return account
        else:
            raise HTTPException(status_code=404, detail="Not found")
    if x_user.role == UserRole.operator:
        if (
            get_safe_member_from_db(safe_id, x_user.id) is not None
        ):  # he is authorized to get info about this safe by the convention
            if account.safe_id == safe_id:
                return account
            else:
                raise HTTPException(status_code=404, detail="Not found")

    raise HTTPException(status_code=403, detail="Unauthorized")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/safes/{safe_id}/members")
def add_member_to_safe(
    safe_id: str,
    member: SafeMemberCreate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> SafeMemberResponse:
    user = check_current_user_by_token(credentials)
    user_is_admin(user)
    if get_safe_from_db(safe_id) is None:
        raise HTTPException(
            status_code=404,  # the resource doesnt exist
            detail="safe does not exist ",
        )

    if get_user_from_db(member.user_id) is None:
        raise HTTPException(
            status_code=404,  # the resource doesnt exist
            detail="cant add this member , user does not exist",
        )

    safe_to_user = get_safe_member_from_db(safe_id, member.user_id)
    if safe_to_user is not None:
        raise HTTPException(
            status_code=409,
            detail="Conflict - this user is already a member of this safe",
        )
    safe_member_response = SafeMemberResponse(
        user_id=member.user_id,
        safe_id=safe_id,
        permission_level=member.permission_level,
    )
    create_safe_member_in_db(safe_member_response)
    return safe_member_response


@app.post("/safes")
def create_safe(
    safe: SafeCreate,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> SafeResponse:
    user = check_current_user_by_token(credentials=credentials)
    user_is_admin(user)
    curr_id_number = get_next_safe_id_from_db()
    curr_sid = f"s_{curr_id_number}"

    safe_response = SafeResponse(
        name=safe.name,
        safe_type=safe.safe_type,
        description=safe.description,
        id=curr_sid,
    )
    create_safe_in_db(safe_response)
    return safe_response


@app.get("/safes/{safe_id}")
def get_safe_by_id(
    safe_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> SafeResponse:
    safe = get_safe_from_db(safe_id)
    if safe is None:
        raise HTTPException(status_code=404, detail="no such safe")
    user = check_current_user_by_token(credentials)
    if user.role == UserRole.admin:
        return safe

    if user.role == UserRole.operator:
        if get_safe_member_from_db(safe_id, user.id) is not None:
            return safe
    raise HTTPException(status_code=403, detail="Unauthorized")


@app.get("/safes/{safe_id}/members")
def get_members_of_safe(
    safe_id: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> list[SafeMemberResponse]:
    if get_safe_from_db(safe_id) is None:
        raise HTTPException(status_code=404, detail="There is no such safe")
    user = check_current_user_by_token(credentials)
    user_is_admin(user)
    members_list = get_members_of_safe_from_db(safe_id)
    return members_list


@app.get("/safes")
def get_safes(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> list[SafeResponse]:
    user = check_current_user_by_token(credentials=credentials)
    if user.role == UserRole.admin:
        return get_all_safes_from_db()
    operator_list = []
    if user.role == UserRole.operator:
        operator_list = get_safes_of_user_from_db(user.id)
        return operator_list

    if user.role == UserRole.auditor:
        return []

    return []


@app.get("/users")
def get_users() -> list[UserResponse]:
    return get_all_users_from_db()


@app.get("/users/{user_id}")
def get_by_user_id(user_id: str) -> UserResponse:
    user = get_user_from_db(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@app.post("/users")
def post_user(user: UserCreate) -> UserResponse:
    next_id = get_next_user_id_from_db()
    curr_id = f"u_{next_id}"
    u_r = UserResponse(
        id=curr_id, username=user.username, role=user.role, state=UserState.active
    )
    password_salt, password_hash = hash_password(user.password)
    create_user_in_db(
        UserRecord(
            id=curr_id,
            username=user.username,
            role=user.role,
            state=UserState.active,
            password_hash=password_hash,
            password_salt=password_salt,
        )
    )
    return u_r


@app.post("/login")
def login(login_req: LoginRequest) -> LoginResponse:
    username = login_req.username
    user = get_user_by_username_from_db(username)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not verify_password(
        password=login_req.password,
        salt_hex=user.password_salt,
        stored_hash_hex=user.password_hash,
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = secrets.token_urlsafe(32)
    created_at = datetime.now(timezone.utc)
    expires_at = created_at + timedelta(minutes=TOKEN_SESSION_TIME_MINUTES)
    create_session_in_db(
        user_id=user.id,
        token=token,
        created_at=created_at.isoformat(),
        expires_at=expires_at.isoformat(),
    )
    login_response = LoginResponse(access_token=token, token_type="bearer")
    return login_response


@app.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> LogoutResponse:
    user = get_user_by_token(credentials=credentials)
    token = credentials.credentials
    revoked = revoke_session_in_db(token=token)
    if not revoked:
        raise HTTPException(status_code=401, detail="Wrong or expired token")
    return LogoutResponse(
        user_id=user.id, logout_msg=f"{user.id} logged out successfully"
    )
