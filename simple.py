""" simple """

# python imports
import re
import datetime
import os
from functools import wraps
from unicodedata import normalize
from os import urandom
from base64 import b32encode
import mimetypes
import subprocess
import shlex
import dateutil.parser

# web stuff and markdown imports
import markdown
from flask.ext.paginate import Pagination
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from flask import render_template, request, Flask, flash, redirect, url_for, \
    abort, jsonify, Response, make_response
from werkzeug.contrib.cache import FileSystemCache, NullCache
from werkzeug.utils import secure_filename
import json
from flask import send_from_directory
from unidecode import unidecode
from bs4 import BeautifulSoup
import pytz

try:
    import pygments
    from pygments.formatters import HtmlFormatter
except ImportError:
    pygments = None


app = Flask(__name__)
app.config.from_object('settings')
app.secret_key = app.config["SECRET_KEY"]

UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp3', 'ogg'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
CACHE_FLUSH_COMMAND = app.config['CACHE_FLUSH_COMMAND'].strip()
BEGINNING_SLASH = re.compile(r'^/+')

db = SQLAlchemy(app)
cache_directory = os.path.dirname(__file__)
try:
    cache = FileSystemCache(os.path.join(cache_directory, "cache"))
except Exception, e:
    print "Could not create cache folder, caching will be disabled."
    print "Error: %s" % e
    cache = NullCache()

_punct_re = re.compile(r'\W+')

extensions = ['fenced_code', 'toc']
if pygments is not None:
    extensions.append('codehilite')

MARKDOWN_PARSER = markdown.Markdown(extensions=extensions, safe_mode=False,
                                    output_format="html5")

def current_datetime():
    return datetime.datetime.utcnow()

def format_datetime(date, format='%Y-%m-%d %I:%m %p %Z'):
    if not date:
        return ''
    return pytz.utc.localize(date).strftime(format)

def format_iso8601_notz(date):
    return format_datetime(date, '%Y-%m-%dT%H:%M:%S')

def format_iso8601(date):
    if not date:
        return ''
    return pytz.utc.localize(date).isoformat()
    

if not app.jinja_env.filters.has_key('datetimeformat'):
    app.jinja_env.filters['datetimeformat'] = format_datetime
    app.jinja_env.filters['iso8601notz'] = format_iso8601_notz
    app.jinja_env.filters['iso8601'] = format_iso8601

class Post(db.Model):
    def __init__(self, title):
        self.title = title

    __tablename__ = "posts"
    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String())
    readable_id = db.Column(db.String(), index=True, unique=True, nullable=True)
    text = db.Column(db.String(), default="")
    draft = db.Column(db.Boolean(), index=True, default=True)
    text_type = db.Column(db.String(), default='markdown')
    links = db.Column(db.String(), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), index=True)
    updated_at = db.Column(db.DateTime(timezone=True))

    def links_as_dict(self):
        if self.links:
            return json.loads(self.links)
        return {}


    def has_audio(self):
        for link in self.links_as_dict():
            if link.get('mimetype', '').startswith('audio/'):
                return True
        return False

    def render_content(self):
        _cached = cache.get("post_%s"%self.id)
        if _cached is not None:
            return _cached
        text = MARKDOWN_PARSER.convert(self.text) if self.text_type == 'markdown' else self.text
        cache.set("post_%s"%self.id, text)
        return text

    def set_content(self, content):
        cache.delete("post_%s"%self.id)
        self.text = content
        post_links = self._parse_post_links()
        self.links = json.dumps(post_links) if len(post_links) > 0 else None

    def get_content(self): return self.text

    def _parse_post_links(self):
        soup = BeautifulSoup(self.render_content())
        links = []
        for link in soup.find_all('a'):
            href = link.get('href')
            if href:
                mimetype,_ = mimetypes.guess_type(href.lower())
                if mimetype:
                    links.append({'href': href, 'mimetype': mimetype})
        return links


try:
    db.create_all()
except Exception:
    pass


def is_admin():
    auth = request.authorization
    if not auth or not (auth.username == app.config["ADMIN_USERNAME"]
                        and check_password_hash(app.config["ADMIN_PASSWORD"], 
                                                auth.password)):
        return False
    return True


def requires_authentication(func):
    """ function decorator for handling authentication """
    @wraps(func)
    def _auth_decorator(*args, **kwargs):
        """ does the wrapping """
        if not is_admin():
            return Response("Could not authenticate you", 
                            401, 
                            {"WWW-Authenticate": 'Basic realm="Login Required"'})
        return func(*args, **kwargs)

    return _auth_decorator




@app.route("/")
def index():
    """ Index Page. Here is where the magic starts """

    page = request.args.get("page", 1, type=int)
    posts_result,total = query_posts_paginated(page, draft=False)
    posts = posts_result.all()

    pagination = Pagination(posts_result.count(), page=page, total=total, record_name='posts', search=False, per_page=app.config['POSTS_PER_PAGE'])

    return render_template("index.html", 
                           posts=posts,
                           pagination=pagination,
                           now=current_datetime(),
                           is_admin=is_admin())


@app.route("/style.css")
def render_font_style():
    t = render_template("font_style.css", font_name=app.config["FONT_NAME"])
    return Response(t, mimetype="text/css")



@app.route("/<int:post_id>")
def view_post(post_id):
    """ view_post renders a post and returns the Response object """
    try:
        post = db.session.query(Post).filter_by(id=post_id, draft=False).one()
    except Exception:
        return abort(404)

    return render_template("view.html", post=post, has_audio=post.has_audio(), is_admin=is_admin())


@app.route("/<path:readable_id>.html")
def view_post_slug(readable_id):
    try:
        post = db.session.query(Post).filter_by(readable_id=readable_id, draft=False).one()
    except Exception:
        #TODO: Better exception
        return abort(404)

    return render_template("view.html", post=post, has_audio=post.has_audio(), is_admin=is_admin())


@app.route("/new", methods=["POST", "GET"])
@requires_authentication
def new_post():
    post = Post(title=request.form.get("title", "untitled"))

    db.session.add(post)
    db.session.commit()

    return redirect(url_for("edit", post_id=post.id))


@app.route("/edit/<int:post_id>", methods=["GET", "POST"])
@requires_authentication
def edit(post_id):
    try:
        post = db.session.query(Post).filter_by(id=post_id).one()
    except Exception:
        #TODO: better exception
        return abort(404)

    if request.method == "GET":
        return render_template("edit.html", post=post)
    else:
        was_initially_published = not post.draft

        urls_to_flush = []
        post_content = request.form.get("post_content", "")

        post.set_content(post_content)
        post.updated_at = current_datetime()

        publish_date = request.form.get('post_publish_date', '').strip()
        if len(publish_date) > 0:
            publish_date = dateutil.parser.parse(publish_date + 'Z') #UTC everywhere
            if publish_date.tzinfo:
                publish_date = publish_date.astimezone(pytz.utc).replace(tzinfo = None)
        else:
            publish_date = None


        recalculate_readable_id = False

        if publish_date and post.created_at != publish_date:
            post.created_at = publish_date
            recalculate_readable_id = True

        if any(request.form.getlist("post_draft", type=int)):
            post.draft = True
        else:
            #user wants to publish
            if post.draft:
                post.draft = False
                if not post.created_at:
                    post.created_at = current_datetime()
                    post.updated_at = post.created_at
                    recalculate_readable_id = True

        if post.title != request.form.get("post_title", ""):
            post.title = request.form.get("post_title", "")
            recalculate_readable_id = True

        if was_initially_published:
            urls_to_flush.append(full_url_of(post))

        readable_id = request.form.get("post_readable_id", "")

        if post.readable_id and (post.readable_id != readable_id):
            post.readable_id = readable_id
        elif recalculate_readable_id:
            post.readable_id = get_readable_id(post.created_at, post.title, post_id)

        db.session.add(post)
        db.session.commit()

        if was_initially_published:
            refresh_cache(urls_to_flush)

        return redirect(url_for("edit", post_id=post_id))


@app.route("/delete/<int:post_id>", methods=["GET", "POST"])
@requires_authentication
def delete(post_id):
    try:
        post = db.session.query(Post).filter_by(id=post_id).one()
    except Exception:
        # TODO: define better exceptions for db failure.
        flash("Error deleting post ID %s" % post_id, category="error")
    else:
        db.session.delete(post)
        db.session.commit()
        if not post.draft:
            refresh_cache([full_url_of(post)])

    return redirect(request.args.get("next", "")
                    or request.referrer or url_for('index'))

def query_posts_paginated(page=1, draft=False, per_page=app.config['POSTS_PER_PAGE']):
    all_posts = db.session.query(Post)\
        .filter_by(draft=draft).order_by(Post.created_at.desc())
    
    total = all_posts.count()

    query = all_posts.limit(per_page).offset((page - 1) * int(per_page))

    return (query, total)

@app.route("/admin", methods=["GET", "POST"])
@requires_authentication
def admin():
    drafts = db.session.query(Post)\
        .filter_by(draft=True).order_by(Post.created_at.desc()).all()

    page = request.args.get("page", 1, type=int)
    posts_result,total = query_posts_paginated(page, draft=False)
    posts = posts_result.all()

    pagination = Pagination(posts_result.count(), page=page, total=total, record_name='posts', search=False, per_page=app.config['POSTS_PER_PAGE'])


    return render_template("admin.html", drafts=drafts, posts=posts, pagination = pagination)

def full_url_of(post):
    path = BEGINNING_SLASH.sub('', url_for('view_post_slug', readable_id=post.readable_id))
    return os.path.join(app.config['BLOG_URL'], path)

@app.route("/admin/save/<int:post_id>", methods=["POST"])
@requires_authentication
def save_post(post_id):
    try:
        post = db.session.query(Post).filter_by(id=post_id).one()
    except Exception:
        # TODO Better exception
        return abort(404)

    if post.title != request.form.get("title", ""):
        post.title = request.form.get("title", "")
        post.readable_id = get_readable_id(post.created_at, post.title, post_id)
    content = request.form.get("content", "")
    content_changed = content != post.get_content()

    post.set_content(content)
    post.updated_at = current_datetime()
    db.session.add(post)
    db.session.commit()
    if not post.draft:
        refresh_cache([full_url_of(post)])
    return jsonify(success=True, update=content_changed)


@app.route("/preview/<int:post_id>")
@requires_authentication
def preview(post_id):
    try:
        post = db.session.query(Post).filter_by(id=post_id).one()
    except Exception:
        # TODO: Better exception
        return abort(404)

    return render_template("view.html", post=post, has_audio=post.has_audio(), preview=True)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

@app.route("/cache-refresh", methods=["POST"])
@requires_authentication
def cache_refresh():
    if request.method == 'POST':
        if request.json is None:
            response = make_response(jsonify(status = 'err', message = 'request entity is not application/json'))
            response.status = 400
            return response
        urls = requeset.json.get('urls', [])
        results = refresh_cache(urls)
        return json.dumps({'status': 'ok', 'results': results})
    response = make_response(jsonify(status = 'err', message = 'use POST'))
    response.status = 405
    return response



@app.route("/upload", methods=["POST"])
@requires_authentication
def upload_file():
    if request.method == 'POST':
        file_upload = request.files['file']
        if file and allowed_file(file_upload.filename):
            dest_prefix = request.form.get('dest', '').strip('/')
            dest_dir = os.path.join(app.config['UPLOAD_FOLDER'], dest_prefix)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            filename, extension = os.path.splitext(file_upload.filename)
            extension = slugify(extension[1:] if extension.startswith('.') else extension).lower()
            filename = '%s.%s' % (slugify(filename), extension)

            file_upload.save(os.path.join(dest_dir, filename))
            url = url_for('uploaded_file', filename=os.path.join(dest_prefix, filename))
            return json.dumps({'status': 'ok', 'url': url, 'name': filename});
        return json.dumps({'status': 'err', 'message': 'file type is not supported'});
    return json.dumps({'status': 'err', 'message': 'only POST is supported'});
            

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


@app.route("/posts.rss")
def feed():
    posts = db.session.query(Post)\
        .filter_by(draft=False)\
        .order_by(Post.created_at.desc())\
        .limit(10).all()

    response = make_response(render_template('index.xml', posts=posts))
    response.mimetype = "application/xml"
    return response


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
