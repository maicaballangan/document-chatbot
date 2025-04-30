# Document Chatbot FastAPI - Backend

```
.
├── app
│   ├── core                        - core classes
│   ├── email-templates             - email templates
│   ├── models                      - tortoise models
│   │   ├── user.py
│   │   └── ...
│   ├── routes                      - api routers
│   │   ├── app_router.py
│   │   ├── auth_router.py
│   │   ├── user_routes.py
│   │   └── ...
│   ├── schemas                     - pydantic schema
│   │   ├── user_schemas.py
│   │   └── ...
│   ├── utils                       - utilities
│   └── main.py
├── tests
│   ├── models                      - model unit tests
│   ├── routes                      - integration tests
│   └── conftest.py
├── Dockerfile          
├── Makefile                        - build automation
└── README.md
```

## Requirements
* [brew](https://brew.sh/) - Package Manager for macOS and Linux
* [uv](https://docs.astral.sh/uv/) - Package Manager for python
* [postgres](https://www.postgresql.org/download/)
* [make](https://formulae.brew.sh/formula/make) - Build automation tool for macOS and Linux

Installing using brew:
```sh
brew install uv
brew install make
brew install postgresql
```

## Development

### Local Setup

Note: See [makefile](Makefile) for build automation commands

Create and activate virtual env:
```sh
make venv
source .venv/bin/activate
```

Copy env and add necessary variables:
```sh
cp .env.local .env
```

Install/sync dependencies:
```sh
make install
```

### Database Setup
 
Start postgresql:
```sh
brew services start postgresql
```

Seed local database:
```sh
aerich upgrade
createuser -s postgres
psql -U postgres -f data/create_superuser.sql
```

### Docker Database Setup
```sh
docker compose exec api-new aerich upgrade
docker cp data/create_superuser.sql db:/create_superuser.sql
docker compose exec db psql -U postgres -d lawyersdb -f ./create_superuser.sql
```

## Running the server

Run dev server with live reload:
```sh
make dev
```

Run service on docker:
```sh
make docker
```

Access: http://localhost:8001/docs
```
username: admin@example.ai
password: Admin12#
```

## Testing

Run pytest:
```sh
make test
```

## Coverage HTML

Run coverage report:
```sh
make coverage
```
Note: Make sure coverage is at least 90%

## Lint Fix

Check and fix issues before you commit or else pre-commit hook will fail:
```sh
make lint
```

## Other useful commands
To see for any dependency mismatch:
```sh
make dep-check
```

To add a missing dependency:
```sh
uv add <dependency-name>
```
