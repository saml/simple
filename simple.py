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
from unidecode import unidecode
import pytz




UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CACHE_FLUSH_COMMAND = app.config['CACHE_FLUSH_COMMAND'].strip()
BEGINNING_SLASH = re.compile(r'^/+')

cache_directory = os.path.dirname(__file__)
try:
    cache = FileSystemCache(os.path.join(cache_directory, "cache"))
except Exception, e:
    print "Could not create cache folder, caching will be disabled."
    print "Error: %s" % e
    cache = NullCache()

_punct_re = re.compile(r'\W+')



def full_url_of(post):
    path = BEGINNING_SLASH.sub('', url_for('view_post_slug', readable_id=post.readable_id))
    return os.path.join(app.config['BLOG_URL'], path)


def allowed_file(filename):
    return True

def refresh_cache(urls, dryrun=not CACHE_FLUSH_COMMAND):
    app.logger.debug('flush: %s' % urls)
    results = []
    if not dryrun:
        for url in urls:
            command = [CACHE_FLUSH_COMMAND, url]
            app.logger.debug(command)
            p = subprocess.Popen(command, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            out,err = p.communicate()
            results.append({'pid': p.pid, 'returncode': p.returncode, 'out': out, 'err': err, 'url': url})
    app.logger.debug(results)
    return results


def slugify(text, delim=u'-', encoding='utf-8'):
    """Generates an slightly worse ASCII-only slug.
    text should be unicode
    """
    if type(text) != type(u''):
        text = unicode(text, encoding=encoding)
    return _punct_re.sub(delim, unidecode(text).lower())

def get_readable_id(publish_date, text, post_id):
    readable_id = '%s/%s' % (publish_date.strftime('%Y/%m'), slugify(text))
    
    # This could have issues if a post is marked as draft, then live, then 
    # draft, then live and there are > 1 posts with the same slug. Oh well.
    post = db.session.query(Post).filter_by(readable_id=readable_id).first()
    if post is None or post.id == post_id:
        return readable_id
    return "%s-1" % readable_id


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
