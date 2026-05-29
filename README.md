# Mini Vault Access Project

Mini Vault is a learning backend and fullstack project inspired by privileged access management concepts.

The project demonstrates backend API development, authentication, authorization, SQLite persistence, password hashing, audit logging, automated testing, privileged session management simulation, and a browser-based frontend demo.

## Current Features

- FastAPI backend
- Pydantic request and response models
- SQLite persistence for users, safes, safe members, accounts, account secrets, audit logs, authentication sessions, and connection sessions
- User registration
- Login with password hashing using scrypt and salt
- Bearer token authentication
- Secure random access token generation
- SQLite-backed bearer sessions
- Session revocation through logout
- Token expiration with `expires_at`
- Role-based authorization
- Safes and safe members
- Foreign keys and JOIN queries
- Account metadata and secret retrieval flow
- PSM-like managed connection simulation without exposing secrets
- Connection session persistence in SQLite
- Audit logs for secret retrieval and connection attempts, including timestamps
- Swagger/OpenAPI documentation
- React/Vite frontend demo
- Frontend handling for expired or revoked tokens
- Frontend support for PSM-like connect flow
- Pytest tests
- Ruff formatting/linting

## Tech Stack

### Backend

- Python
- FastAPI
- Pydantic
- SQLite
- Pytest
- Ruff

### Frontend

- React
- Vite
- JavaScript
- CSS-in-JS styling

## Project Structure

```text
Mini-Vault/
├── main.py
├── database.py
├── models.py
├── tests/
│   └── test_main.py
├── mini-vault-frontend/
│   ├── src/
│   │   └── App.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── index.html
└── README.md
```

## Run the Backend

From the project root:

```bash
python -m uvicorn main:app --reload
```

Then open the Swagger/OpenAPI documentation:

```text
http://localhost:8000/docs
```

The backend API runs at:

```text
http://127.0.0.1:8000
```

## Run the Frontend

From the project root:

```bash
cd mini-vault-frontend
npm install
npm run dev
```

Then open:

```text
http://localhost:5173
```

Make sure the FastAPI backend is also running at:

```text
http://127.0.0.1:8000
```

## Run Tests

From the project root:

```bash
python -m pytest -v
```

## Code Formatting and Linting

```bash
python -m ruff format .
python -m ruff check .
```

## Frontend Note

The React frontend was generated and iteratively adapted with AI assistance.

The main focus of this project is the backend implementation: FastAPI APIs, authentication, authorization, SQLite persistence, password hashing, audit logging, PSM-like connection simulation, and automated tests.

The frontend is included as a visual fullstack demo for testing the backend flow through a browser interface.

## Authentication Flow

```text
1. User registers with username, role, and password.
2. Password is hashed with scrypt and salt before being stored.
3. User logs in with username and password.
4. Backend validates the password hash.
5. Backend creates a secure random bearer token.
6. Backend stores the token as a session in SQLite.
7. The session includes created_at, expires_at, and is_revoked.
8. Frontend stores the token locally after login.
9. Frontend sends the token in the Authorization header.
10. Backend looks up the session by token.
11. Backend rejects missing, revoked, expired, or malformed sessions.
12. Backend identifies the current user from the session user_id.
13. Backend verifies the user exists and is active.
```

Example protected request:

```text
Authorization: Bearer <access_token>
```

## PSM-like Connection Flow

```text
1. User logs in and receives a bearer token.
2. User selects an account inside a safe.
3. User requests a managed connection session.
4. Backend authenticates the user from the bearer token.
5. Backend checks that the safe exists.
6. Backend checks that the account exists and belongs to the safe.
7. Backend checks that the account secret exists internally.
8. Backend verifies that the user is allowed to connect.
9. Backend creates a connection session in SQLite.
10. Backend writes an audit log.
11. Backend returns connection metadata without exposing the secret value.
```

Example connection request:

```text
POST /safes/{safe_id}/accounts/{account_id}/connect
Authorization: Bearer <access_token>
```

Example concept:

```text
The user receives a managed connection session.
The secret remains stored inside the backend and is not returned to the frontend.
```

## Authorization Rules

- Admin can create safes.
- Admin can add safe members.
- Admin can read audit logs.
- Admin can retrieve secrets.
- Admin can start managed connection sessions.
- Operator can see safes where he is a member.
- Operator with `use` or `manage` permission can retrieve secrets.
- Operator with `use` or `manage` permission can start managed connection sessions.
- Operator with `read` permission cannot retrieve secrets.
- Operator with `read` permission cannot start managed connection sessions.
- Auditor currently receives an empty safes list, cannot retrieve secrets, and cannot start managed connection sessions.

## Database Persistence

The project uses SQLite for learning and local development.

Persisted entities:

- Users
- Safes
- Safe members
- Accounts
- Account secrets
- Audit logs
- Authentication sessions
- Connection sessions

The project includes examples of:

- Primary keys
- Foreign keys
- JOIN queries
- Test cleanup order
- Mapping database rows to Pydantic response models
- SQLite-backed authentication sessions
- Session revocation
- Token expiration checks
- PSM-like connection session persistence

## Project Status

This is an educational project and is not production-ready.

Completed learning milestones:

- Replaced `x-user-id` mock authentication with bearer token authentication
- Persisted users, safes, safe members, accounts, account secrets, audit logs, and sessions in SQLite
- Added foreign keys and JOIN queries
- Added password hashing with scrypt and salt
- Added secure random bearer tokens
- Persisted bearer sessions in SQLite instead of using an in-memory `token_store`
- Added additional tests for bearer-protected safe, member, audit log, and secret retrieval endpoints
- Added audit log timestamps
- Added a React/Vite frontend demo
- Added logout and token revocation
- Added tests for logout and revoked sessions
- Added token expiration with `expires_at`
- Added tests for expired sessions
- Added frontend handling for expired or revoked tokens
- Added PSM-like connection simulation
- Added SQLite persistence for managed connection sessions
- Added tests for successful and unauthorized connection attempts
- Added audit logging for managed connection attempts
- Added frontend support for starting managed connection sessions without exposing secrets

Planned next steps:

- Add Docker support
- Optionally migrate from SQLite to PostgreSQL or MySQL
- Optionally re-implement selected concepts in Java

## Disclaimer

This project is built for learning purposes. It is not production-ready and should not be used to store real secrets.
