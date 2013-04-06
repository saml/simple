#!/bin/bash

export PROJ="$(pwd)"

echo "vim nginx.conf 
=8<=
location / {
    include uwsgi_params;
    uwsgi_pass unix:$PROJ/uwsgi.sock;
}
=8<="

uwsgi -s "$PROJ/uwsgi.sock" --wsgi-file "$PROJ/simple.py" --callable app --chdir "$PROJ"


