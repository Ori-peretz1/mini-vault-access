# Mini Vault Access Project

Mini Vault is a learning backend project inspired by privileged access management concepts.

The project demonstrates backend API development, authentication, authorization, SQLite persistence, password hashing, audit logging, and automated testing.

## Current Features

- FastAPI backend
- Pydantic request and response models
- SQLite persistence for users and safes
- User registration
- Login with password hashing using scrypt and salt
- Role-based authorization
- Safes and safe members
- Account metadata and secret retrieval flow
- Audit logs for secret retrieval attempts
- Swagger/OpenAPI documentation
- Pytest tests
- Ruff formatting/linting

## Tech Stack

- Python
- FastAPI
- Pydantic
- SQLite
- Pytest
- Ruff

## Run the Project

```bash
python -m uvicorn main:app --reload
```

Then open:

```text
http://localhost:8000/docs
```

## Run Tests

```bash
python -m pytest -v
```

## Project Status

This is an educational project and is not production-ready.

Planned next steps:

- Replace `x-user-id` mock authentication with bearer token authentication
- Persist safe members, accounts, and audit logs in SQLite
- Add foreign keys and JOIN queries
- Add a PSM-like connection simulation
- Add Docker support
- Add a frontend demo