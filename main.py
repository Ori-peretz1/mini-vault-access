from fastapi import FastAPI, HTTPException, Header
import hashlib
import os
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
)


next_account_id = 1  # step 5
next_audit_log_id = 1  # step 6


safe_members: dict[tuple[str, str], SafeMemberResponse] = {}
# users: dict[str, UserResponse] = {}
# safes: dict[str, SafeResponse] = {}

accounts: dict[str, AccountResponse] = {}  # metadata - step 5 (of safe)
account_secrets: dict[str, str] = {}  # sensitive info - step 5

audit_logs: dict[str, AuditLogResponse] = {}


app = FastAPI(title="Mini vault access project")
db_init()


def check_current_user(x_user_id: str | None) -> UserResponse:
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    user_response = get_user_from_db(x_user_id)
    if user_response is None:
        raise HTTPException(status_code=401, detail="user id does not exist")
    if user_response.state != UserState.active:
        raise HTTPException(status_code=403, detail="user is not active")
    return user_response


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


def user_is_admin(x_user_id: str) -> None:
    if get_user_from_db(x_user_id).role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admin can create safe")


def audit_log_create(
    actor_id: str,
    action: AuditAction,
    success: bool,
    msg: str,
    safe_id: str | None = None,
    account_id: str | None = None,
) -> AuditLogResponse:  # helper for creating audit -step 6
    global next_audit_log_id
    curr_log_id = f"log_{next_audit_log_id}"
    next_audit_log_id += 1
    audit_response = AuditLogResponse(
        id=curr_log_id,
        actor_user_id=actor_id,
        action=action,
        safe_id=safe_id,
        account_id=account_id,
        success=success,
        message=msg,
    )
    audit_logs[curr_log_id] = audit_response
    return audit_response


def can_retrieve_secret(
    user: UserResponse, safe_id: str
) -> bool:  # helper function for checking if user can get sensitive info by set of rules of authorization - step 6
    if user.role == UserRole.admin:
        return True

    if user.role == UserRole.operator:
        safe_member = (safe_id, user.id)
        if safe_member not in safe_members:
            return False
        permission = safe_members[safe_member].permission_level
        if (
            permission == SafePermissionLevel.manage
            or permission == SafePermissionLevel.use
        ):  # by the set of rules i decided that operator with "use" permission level and auditor cant retrieve secret
            return True

    return False


@app.post(
    "/safes/{safe_id}/accounts/{account_id}/retrieve",
    summary="retrieving a secret from a safe",
)  # step 6
def retrieve_secret(
    safe_id: str, account_id: str, x_user_id: str | None = Header(default=None)
) -> SecretRetrieveResponse:
    actor_user = check_current_user(
        x_user_id
    )  # this case does not create audit log for now
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
    if account_id not in accounts:
        audit_log_create(
            actor_id=actor_user.id,
            action=AuditAction.retrieve_secret,
            success=False,
            msg="Account does not exist",
            safe_id=safe_id,
            account_id=account_id,
        )
        raise HTTPException(status_code=404, detail="Account does not exist")
    account = accounts[account_id]
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

    if can_retrieve_secret(actor_user, safe_id):
        audit_log_create(
            actor_id=actor_user.id,
            action=AuditAction.retrieve_secret,
            success=True,
            msg=f"{x_user_id} retrieved secret for account {account_id} from safe {safe_id}",
            safe_id=safe_id,
            account_id=account_id,
        )
        secret_retrieve_response = SecretRetrieveResponse(
            account_id=account_id,
            secret_value=account_secrets[account_id],
            secret_version=accounts[account_id].secret_version,
        )  # account can be in only one safe
        return secret_retrieve_response
    audit_log_create(
        actor_id=actor_user.id,
        action=AuditAction.retrieve_secret,
        success=False,
        msg=f"Unauthorized {x_user_id} tried to retrieved secret for account {account_id}",
        safe_id=safe_id,
        account_id=account_id,
    )
    raise HTTPException(status_code=403, detail="Unauthorized")


@app.get("/audit-logs")  # step 6
def get_audit_logs(
    x_user_id: str | None = Header(default=None),
) -> list[AuditLogResponse]:
    user = check_current_user(x_user_id)
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admin can get logs")
    return list(audit_logs.values())


@app.post(
    "/safes/{safe_id}/accounts", summary="adding account into specific safe"
)  # creating account in specific safe - step 5
def add_account_to_safe(
    safe_id: str,
    account_create: AccountCreate,
    x_user_id: str | None = Header(default=None),
) -> AccountResponse:
    x_user = check_current_user(x_user_id)
    global next_account_id
    if get_safe_from_db(safe_id) is None:
        raise HTTPException(status_code=404, detail="No such safe")
    if x_user.role == UserRole.admin:
        curr_id = f"a_{next_account_id}"
        next_account_id += 1
        account_secrets[curr_id] = account_create.secret_value
        account_response = AccountResponse(
            id=curr_id,
            safe_id=safe_id,
            username=account_create.username,
            target=account_create.target,
            platform=account_create.platform,
            secret_version=1,
        )
        accounts[curr_id] = account_response
        return account_response

    if (
        (x_user.role == UserRole.operator)
        and (safe_id, x_user_id) in safe_members
        and safe_members[(safe_id, x_user_id)].permission_level
        == SafePermissionLevel.manage
    ):
        curr_id = f"a_{next_account_id}"
        next_account_id += 1
        account_secrets[curr_id] = account_create.secret_value
        account_response = AccountResponse(
            id=curr_id,
            safe_id=safe_id,
            username=account_create.username,
            target=account_create.target,
            platform=account_create.platform,
            secret_version=1,
        )
        accounts[curr_id] = account_response
        return account_response

    raise HTTPException(status_code=403, detail="Unauthorized")


@app.get(
    "/safes/{safe_id}/accounts", summary="get accounts of specific safe"
)  # get accounts of a specific safe - step 5
def get_accounts_of_safe(
    safe_id: str, x_user_id: str | None = Header(default=None)
) -> list[AccountResponse]:
    x_user = check_current_user(x_user_id)
    if get_safe_from_db(safe_id) is None:
        raise HTTPException(status_code=404, detail="There is no such safe")
    list_of_accounts = []
    if x_user.role == UserRole.admin:
        for account_id in accounts:
            acc = accounts[account_id]
            if acc.safe_id == safe_id:
                list_of_accounts.append(acc)

        return list_of_accounts

    if x_user.role == UserRole.operator:
        if (safe_id, x_user_id) not in safe_members:
            raise HTTPException(status_code=403, detail="Unauthorized")
        else:
            for account_id in accounts:
                acc = accounts[account_id]
                if acc.safe_id == safe_id:
                    list_of_accounts.append(acc)

        return list_of_accounts

    raise HTTPException(status_code=403, detail="Unauthorized")


@app.get(
    "/safes/{safe_id}/accounts/{account_id}"
)  # getting meta data of account by account id - step 5
def get_account_from_safe(
    safe_id: str, account_id: str, x_user_id: str | None = Header(default=None)
) -> AccountResponse:
    x_user = check_current_user(x_user_id)
    if get_safe_from_db(safe_id) is None:
        raise HTTPException(status_code=404, detail="There is no such safe")
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="There is no such account")
    acc = accounts[account_id]
    if x_user.role == UserRole.admin:
        if acc.safe_id == safe_id:
            return acc
        else:
            raise HTTPException(status_code=404, detail="Not found")
    if x_user.role == UserRole.operator:
        if (
            (safe_id, x_user_id) in safe_members
        ):  # he is authorized to give info about this safe by the convention
            if acc.safe_id == safe_id:
                return acc
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
    x_user_id: (str | None) = Header(default=None),
) -> SafeMemberResponse:
    check_current_user(x_user_id)
    user_is_admin(x_user_id)
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

    safe_to_user = (safe_id, member.user_id)
    if safe_to_user in safe_members:
        raise HTTPException(
            status_code=409,
            detail="Conflict - this user is already a member of this safe",
        )
    safe_member_response = SafeMemberResponse(
        user_id=member.user_id,
        safe_id=safe_id,
        permission_level=member.permission_level,
    )
    safe_members[safe_to_user] = safe_member_response
    return safe_member_response


@app.post("/safes")
def create_safe(
    safe: SafeCreate, x_user_id: str | None = Header(default=None)
) -> SafeResponse:
    check_current_user(x_user_id)
    user_is_admin(x_user_id)
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
    safe_id: str, x_user_id: str | None = Header(default=None)
) -> SafeResponse:
    safe = get_safe_from_db(safe_id)
    if safe is None:
        raise HTTPException(status_code=404, detail="no such safe")
    user = check_current_user(x_user_id)
    if user.role == UserRole.admin:
        return safe

    if user.role == UserRole.operator:
        if (safe_id, x_user_id) in safe_members:
            return safe
    raise HTTPException(status_code=403, detail="Unauthorized")


@app.get("/safes/{safe_id}/members")
def get_members_of_safe(
    safe_id: str, x_user_id: str | None = Header(default=None)
) -> list[SafeMemberResponse]:
    if get_safe_from_db(safe_id) is None:
        raise HTTPException(status_code=404, detail="There is no such safe")
    check_current_user(x_user_id)
    user_is_admin(x_user_id)
    members_list = []
    for (s_id, _), safe_member_response in safe_members.items():
        if s_id == safe_id:
            members_list.append(safe_member_response)
    return members_list


@app.get("/safes")
def get_safes(x_user_id: str | None = Header(default=None)) -> list[SafeResponse]:
    user = check_current_user(x_user_id)
    if user.role == UserRole.admin:
        return get_all_safes_from_db()
    operator_list = []
    if user.role == UserRole.operator:
        for safe_id, member_user_id in safe_members:
            if member_user_id == x_user_id:
                operator_list.append(get_safe_from_db(safe_id))

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
    token = f"token_{user.id}"
    login_response = LoginResponse(access_token=token, token_type="bearer")
    return login_response
