# Mini Vault Access Project

Mini Vault is a learning backend and fullstack project inspired by privileged access management concepts.

The project demonstrates backend API development, authentication, authorization, SQLite persistence, password hashing, audit logging, automated testing, and a browser-based frontend demo.

## Current Features

- FastAPI backend
- Pydantic request and response models
- SQLite persistence for users, safes, safe members, accounts, account secrets, and audit logs
- User registration
- Login with password hashing using scrypt and salt
- Bearer token authentication
- Secure random access token generation
- Role-based authorization
- Safes and safe members
- Foreign keys and JOIN queries
- Account metadata and secret retrieval flow
- Audit logs for secret retrieval attempts, including timestamps
- Swagger/OpenAPI documentation
- React/Vite frontend demo
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

The main focus of this project is the backend implementation: FastAPI APIs, authentication, authorization, SQLite persistence, password hashing, audit logging, and automated tests.

The frontend is included as a visual fullstack demo for testing the backend flow through a browser interface.

## Authentication Flow

```text
1. User registers with username, role, and password.
2. Password is hashed with scrypt and salt before being stored.
3. User logs in with username and password.
4. Backend validates the password hash.
5. Backend creates a secure random bearer token.
6. Frontend sends the token in the Authorization header.
7. Backend identifies the current user from the bearer token.
```

Example protected request:

```text
Authorization: Bearer <access_token>
```

## Authorization Rules

- Admin can create safes.
- Admin can add safe members.
- Admin can read audit logs.
- Operator can see safes where he is a member.
- Operator with `use` or `manage` permission can retrieve secrets.
- Operator with `read` permission cannot retrieve secrets.
- Auditor currently receives an empty safes list and cannot retrieve secrets.

## Database Persistence

The project uses SQLite for learning and local development.

Persisted entities:

- Users
- Safes
- Safe members
- Accounts
- Account secrets
- Audit logs

The project includes examples of:

- Primary keys
- Foreign keys
- JOIN queries
- Test cleanup order
- Mapping database rows to Pydantic response models

## Project Status

This is an educational project and is not production-ready.

Completed learning milestones:

- Replaced `x-user-id` mock authentication with bearer token authentication
- Persisted users, safes, safe members, accounts, account secrets, and audit logs in SQLite
- Added foreign keys and JOIN queries
- Added password hashing with scrypt and salt
- Added secure random bearer tokens
- Added audit log timestamps
- Added a React/Vite frontend demo

Planned next steps:

- Persist sessions/tokens in SQLite
- Add logout and token revocation
- Add token expiration
- Add more tests for bearer-protected endpoints
- Add a PSM-like connection simulation
- Add Docker support
- Optionally migrate from SQLite to PostgreSQL or MySQL

## Disclaimer

This project is built for learning purposes. It is not production-ready and should not be used to store real secrets.
