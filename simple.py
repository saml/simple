""" simple """

# python imports
import re
import datetime
import os
from unicodedata import normalize
from os import urandom
from base64 import b32encode
import subprocess
import shlex
import dateutil.parser

# web stuff and markdown imports
from werkzeug.contrib.cache import FileSystemCache, NullCache
from werkzeug.utils import secure_filename
import json
from flask import send_from_directory
import pytz




UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CACHE_FLUSH_COMMAND = app.config['CACHE_FLUSH_COMMAND'].strip()

cache_directory = os.path.dirname(__file__)
try:
    cache = FileSystemCache(os.path.join(cache_directory, "cache"))
except Exception, e:
    print "Could not create cache folder, caching will be disabled."
    print "Error: %s" % e
    cache = NullCache()






def allowed_file(filename):
    return True



if not app.debug:
    import logging
    from logging.handlers import RotatingFileHandler
    handler = RotatingFileHandler(app.config['LOG_PATH'], maxBytes=100*1024*1024, backupCount=5)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'
        '[in %(filename)s:%(lineno)d]'
        ))
    handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    app.logger.addHandler(handler)
    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))



if __name__ == "__main__":
    if pygments is not None:
        to_write_path = os.path.join(app.static_folder, "css", "code_styles.css")
        if not os.path.exists(to_write_path):
            to_write = HtmlFormatter().get_style_defs(".codehilite")
            try:
                with open(to_write_path, "w") as fd:
                    fd.write(to_write)
            except IOError:
                pass

    app.run(host="0.0.0.0")
