#!/bin/bash

git pull --rebase || exit 1
. venv/bin/activate
pip install -r requirements.txt

