import sqlite3
from models import (
    UserRole,
    UserResponse,
    UserState,
    SafeResponse,
    SafeType,
    UserRecord,
    SafeMemberResponse,
    SafePermissionLevel,
)


DB_FILE = "mini_vault.db"


def clear_users_table() -> None:  # helper function for tests
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM users")

    connection.commit()
    connection.close()


def clear_safes_table() -> None:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        DELETE FROM safes
        """
    )
    connection.commit()
    connection.close()


def clear_safe_members_table() -> None:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM safe_members")

    connection.commit()
    connection.close()


def get_connection():
    connection = sqlite3.connect(DB_FILE)
    connection.execute(
        "PRAGMA foreign_keys = ON"
    )  # make sure foreign key is work  - תפעיל אכיפת מפתח זר בכל חיבור חדש למסד הנתונים
    return connection


def db_init():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL,
            state TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL

)
"""
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS safes(
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        safe_type TEXT NOT NULL,
        description TEXT 
        )


        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS safe_members(
        safe_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        permission_level TEXT NOT NULL,
        PRIMARY KEY (safe_id,user_id),
        FOREIGN KEY (safe_id) REFERENCES safes(id),
        FOREIGN KEY (user_id) REFERENCES users(id)


                    )
        """
    )
    connection.commit()
    connection.close()


def get_next_safe_id_from_db() -> int:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id
        FROM safes
        ORDER BY CAST(SUBSTR(id,3) AS INTEGER ) DESC
        LIMIT 1
        """
    )
    rows = cursor.fetchone()
    connection.close()
    if rows is None:
        return 1

    last_id = rows[0]
    last_number = int(last_id.split("_")[1])
    return last_number + 1


def get_next_user_id_from_db() -> int:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id
        FROM users
        ORDER BY CAST(SUBSTR(id,3) AS INTEGER) DESC
        LIMIT 1
        """
    )
    row = cursor.fetchone()
    connection.close()
    if row is None:
        return 1
    last_id = row[0]
    last_number = int(last_id.split("_")[1])

    return last_number + 1


def create_safe_member_in_db(safe_member: SafeMemberResponse) -> None:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO safe_members (safe_id , user_id,permission_level)
        VALUES(?,?,?)
        """,
        (safe_member.safe_id, safe_member.user_id, safe_member.permission_level.value),
    )
    connection.commit()
    connection.close()


def get_safe_member_from_db(safe_id: str, user_id: str) -> SafeMemberResponse | None:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT safe_id,user_id,permission_level
        FROM safe_members
        WHERE safe_id = ? AND user_id = ?
        """,
        (safe_id, user_id),
    )
    row = cursor.fetchone()
    connection.close()
    if row is None:
        return None
    return SafeMemberResponse(
        safe_id=row[0], user_id=row[1], permission_level=SafePermissionLevel(row[2])
    )


def get_all_safe_members_of_member_from_db(user_id: str) -> list[SafeMemberResponse]:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
                SELECT safe_id,user_id,permission_level
                FROM safe_members
                WHERE user_id = ?
                ORDER BY safe_id
                   """,
        (user_id,),
    )
    rows = cursor.fetchall()
    connection.close()
    safes_list = []
    for row in rows:
        safe_member_response = SafeMemberResponse(
            safe_id=row[0], user_id=row[1], permission_level=SafePermissionLevel(row[2])
        )
        safes_list.append(safe_member_response)

    return safes_list


def get_members_of_safe_from_db(safe_id: str) -> list[SafeMemberResponse]:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT safe_id, user_id, permission_level
        FROM safe_members
        WHERE safe_id = ?
        ORDER BY user_id
        """,
        (safe_id,),
    )

    rows = cursor.fetchall()
    connection.close()

    members = []

    for row in rows:
        members.append(
            SafeMemberResponse(
                safe_id=row[0],
                user_id=row[1],
                permission_level=SafePermissionLevel(row[2]),
            )
        )

    return members


def get_safes_of_user_from_db(user_id: str) -> list[SafeResponse]:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT safes.id,safes.name,safes.safe_type,safes.description
        FROM safes
        JOIN safe_members ON  safes.id =safe_members.safe_id 
        WHERE safe_members.user_id = ?
        ORDER BY safes.id
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    connection.close()
    safes = []
    for row in rows:
        safe = SafeResponse(
            id=row[0], name=row[1], safe_type=SafeType(row[2]), description=row[3]
        )
        safes.append(safe)
    return safes


def create_safe_in_db(safe: SafeResponse) -> None:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO safes (id,name,safe_type,description)
        VALUES(?,?,?,?)
        """,
        (safe.id, safe.name, safe.safe_type.value, safe.description),
    )
    connection.commit()
    connection.close()


def get_safe_from_db(safe_id: str) -> SafeResponse | None:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id,name,safe_type,description
        FROM safes
        WHERE id =?
        """,
        (safe_id,),
    )
    rows = cursor.fetchone()
    connection.close()  # no need to commit cause its no a db chagner action
    if rows is None:
        return None

    return SafeResponse(
        id=rows[0], name=rows[1], safe_type=SafeType(rows[2]), description=rows[3]
    )


def get_all_safes_from_db() -> list[SafeResponse]:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id,name,safe_type,description
        FROM safes
        ORDER BY id
        """
    )
    rows = cursor.fetchall()
    connection.close()
    safes = []

    for row in rows:
        safes.append(
            SafeResponse(
                id=row[0], name=row[1], safe_type=SafeType(row[2]), description=row[3]
            )
        )

    return safes


def create_user_in_db(user: UserRecord) -> None:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO users (id,username,role,state,password_hash,password_salt)
        VALUES(?,?,?,?,?,?)
        """,
        (
            user.id,
            user.username,
            user.role.value,
            user.state.value,
            user.password_hash,
            user.password_salt,
        ),
    )
    connection.commit()
    connection.close()


def get_user_from_db(user_id: str) -> UserResponse | None:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id,username,role,state 
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    )
    row = cursor.fetchone()
    connection.close()
    if row is None:
        return None
    return UserResponse(
        id=row[0],
        username=row[1],
        role=UserRole(row[2]),
        state=UserState(row[3]),
    )


def get_all_users_from_db() -> list[UserResponse]:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id,username,role,state 
        FROM users
        ORDER BY id
        """
    )
    rows = cursor.fetchall()
    connection.close()
    users = []
    for row in rows:
        users.append(
            UserResponse(
                id=row[0],
                username=row[1],
                role=UserRole(row[2]),
                state=UserState(row[3]),
            )
        )
    return users


def get_user_by_username_from_db(username: str) -> UserRecord | None:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, username, role, state, password_hash, password_salt
        FROM users
        WHERE username = ? 
        """,
        (username,),
    )

    row = cursor.fetchone()
    connection.close()
    if row is None:
        return None
    return UserRecord(
        id=row[0],
        username=row[1],
        role=UserRole(row[2]),
        state=UserState(row[3]),
        password_hash=row[4],
        password_salt=row[5],
    )
