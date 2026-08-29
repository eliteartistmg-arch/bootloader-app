#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
PYTHONPATH=. python3 -m bootloader_app
