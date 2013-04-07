#!/bin/bash

curl -H 'X-Recache: 1' "$1" > /dev/null 2>&1 &
disown
