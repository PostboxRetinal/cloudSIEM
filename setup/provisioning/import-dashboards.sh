#!/usr/bin/env sh
set -e

sleep 10
pip install -q requests urllib3
python setup/create-dashboards-complete.py
python setup/import-dashboards.py
