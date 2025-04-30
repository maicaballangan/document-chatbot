# FastAPI Project - Deployment

## Requirements
* [Docker](https://www.docker.com/)

## Docker Deployment
```sh
sudo docker compose up
```

## Create superuser
```sh
psql -U postgres -f data/create_superuser.sql
```

## Access
http://localhost:8001/docs

```
username: admin@example.ai
password: Admin12#
```