#!/usr/bin/env sh
set -e

sleep 15
python setup/orchestrate-logs.py --mode normal
