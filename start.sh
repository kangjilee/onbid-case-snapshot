#!/usr/bin/env bash
set -e
echo "== git sync =="
git fetch origin || true
git reset --hard origin/main || true
echo "== install deps =="
python3 -m pip install -U pip
python3 -m pip install -r requirements.txt
echo "== start =="
exec python3 -m uvicorn KomaCore.main:app --host 0.0.0.0 --port 8000