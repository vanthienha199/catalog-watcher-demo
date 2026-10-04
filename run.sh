#!/usr/bin/env bash
set -e
python3 -m pip install -q -r requirements.txt
python3 -m watcher.cli run "$@"
