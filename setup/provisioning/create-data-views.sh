#!/usr/bin/env sh
set -e

pip install -q requests urllib3
python setup/create-data-views.py
