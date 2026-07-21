#!/bin/sh
set -eu

ruff check .
ruff format --check .
mypy app
pytest

