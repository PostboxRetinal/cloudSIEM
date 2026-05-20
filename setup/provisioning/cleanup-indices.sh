#!/usr/bin/env sh
set -e

pip install -q requests urllib3
python cleanup-indices.py --docker
