from enum import Enum

from pydantic import BaseModel


class UserRole(str, Enum):
    admin = "admin"
    operator = "operator"
    auditor = "auditor"


class UserCreate(BaseModel):
    username: str
    role: UserRole
    password: str  # stage 9


class LoginRequest(BaseModel):  # step 9
    username: str
    password: str


class LoginResponse(BaseModel):  # step 9
    access_token: str
    token_type: str


class UserState(str, Enum):
    active = "active"
    suspended = "suspended"
    locked = "locked"
    disabled = "disabled"


class UserRecord(BaseModel):  # step 9
    id: str
    username: str
    role: UserRole
    state: UserState
    password_hash: str
    password_salt: str


class SafePermissionLevel(str, Enum):
    read = "read"  # can see the Meta data of the safe
    use = "use"  # can use accounts and secrets from the safe
    manage = "manage"  # can manage - adding members and change stuff


class SafeMemberResponse(BaseModel):
    user_id: str
    safe_id: str
    permission_level: SafePermissionLevel


class UserResponse(BaseModel):
    id: str
    username: str
    role: UserRole
    state: UserState


class SafeType(str, Enum):
    production = "production"
    linux_accounts = "linux_accounts"
    database = "database"


class SafeCreate(BaseModel):
    name: str
    safe_type: SafeType
    description: str | None = None


class SafeResponse(BaseModel):
    id: str
    name: str
    safe_type: SafeType
    description: str | None = None


class SafeMemberCreate(BaseModel):
    user_id: str
    permission_level: SafePermissionLevel


class AccountPlatform(str, Enum):  # step 5
    linux_ssh = "linux_ssh"
    database = "database"
    windows_rdp = "windows_rdp"
    ci_cd = "ci_cd"


class AccountCreate(BaseModel):  # step 5
    username: str
    target: str
    platform: AccountPlatform
    secret_value: str


class AccountResponse(BaseModel):  # step 5
    id: str
    safe_id: str
    username: str
    target: str
    platform: AccountPlatform
    secret_version: int


class AuditAction(str, Enum):
    retrieve_secret = "retrieve_secret"


class AuditLogResponse(BaseModel):
    id: str
    actor_user_id: str
    action: AuditAction
    safe_id: str | None = (
        None  # if in the future i will add actions with no safe connection
    )
    account_id: str | None = None
    success: bool
    message: str
    time: str


class SecretRetrieveResponse(BaseModel):
    account_id: str
    secret_value: str
    secret_version: int


class SessionResponse(BaseModel):
    token: str
    user_id: str
    created_at: str
    expires_at: str | None = None
    is_revoked: bool


class LogoutResponse(BaseModel):
    user_id: str
    logout_msg: str
