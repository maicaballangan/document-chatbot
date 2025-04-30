#! /usr/bin/env bash

set -e
set -x

# Run migrations
aerich init-db
aerich upgrade
