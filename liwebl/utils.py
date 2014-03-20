import datetime
import re
import os
import subprocess

from flask import url_for, current_app
from unidecode import unidecode


BEGINNING_SLASH = re.compile(r'^/+')
NON_WORD = re.compile(r'\W+')

def current_datetime():
    return datetime.datetime.utcnow()

def full_url_of(post):
    if post.readable_id is None:
        return None
    path = BEGINNING_SLASH.sub('', url_for('.view_post_slug', readable_id=post.readable_id))
    return os.path.join(current_app.config['BLOG_URL'], path)

def slugify(text, delim=u'-', encoding='utf-8'):
    if type(text) != type(u''):
        text = unicode(text, encoding=encoding)
    return NON_WORD.sub(delim, unidecode(text).lower())

def get_readable_id(publish_date, title):
    readable_id = '%s/%s' % (publish_date.strftime('%Y/%m'), slugify(title))
    return readable_id

def refresh_cache(urls):
    results = []
    dryrun = current_app.config['CACHE_FLUSH_COMMAND']
    if not dryrun:
        for url in urls:
            command = [current_app.config['CACHE_FLUSH_COMMAND'], url]
            current_app.logger.debug(command)
            p = subprocess.Popen(command, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            out,err = p.communicate()
            results.append({'pid': p.pid, 'returncode': p.returncode, 'out': out, 'err': err, 'url': url})
    current_app.logger.debug(results)
    return results


