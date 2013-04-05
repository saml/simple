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


class Post(db.Model):
    def __init__(self, title, created_at):
        if title:
            self.title = title
            self.readable_id = get_readable_id(created_at, title)
        if created_at:
            self.created_at = created_at
            self.updated_at = created_at

    __tablename__ = "posts"
    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String())
    readable_id = db.Column(db.String(), index=True, unique=True)
    text = db.Column(db.String(), default="")
    draft = db.Column(db.Boolean(), index=True, default=True)
    text_type = db.Column(db.String(), default='markdown')
    links = db.Column(db.String(), nullable=True)
    created_at = db.Column(db.DateTime(), index=True)
    updated_at = db.Column(db.DateTime())

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
                mimetype,_ = mimetypes.guess_type(href)
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
                           now=datetime.datetime.now(),
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


@app.route("/<path:readable_id>")
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
    post = Post(title=request.form.get("title", "untitled"),
                created_at=datetime.datetime.now())

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
        post_content = request.form.get("post_content", "")

        post.set_content(post_content)
        post.updated_at = datetime.datetime.now()

        recalculate_readable_id = False
        if any(request.form.getlist("post_draft", type=int)):
            post.draft = True
        else:
            if post.draft:
                post.draft = False
                post.created_at = datetime.datetime.now()
                post.updated_at = datetime.datetime.now()
                recalculate_readable_id = True

        if post.title != request.form.get("post_title", ""):
            post.title = request.form.get("post_title", "")
            recalculate_readable_id = True

        if recalculate_readable_id:
            post.readable_id = get_readable_id(post.created_at, post.title)

        db.session.add(post)
        db.session.commit()
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
        post.readable_id = get_readable_id(post.created_at, post.title)
    content = request.form.get("content", "")
    content_changed = content != post.get_content()

    post.set_content(content)
    post.updated_at = datetime.datetime.now()
    db.session.add(post)
    db.session.commit()
    return jsonify(success=True, update=content_changed)


@app.route("/preview/<int:post_id>")
@requires_authentication
def preview(post_id):
    try:
        post = db.session.query(Post).filter_by(id=post_id).one()
    except Exception:
        # TODO: Better exception
        return abort(404)

    return render_template("view.html", post=post, preview=True)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
            extension = slugify(extension[1:] if extension.startswith('.') else extension)
            filename = '%s.%s' % (slugify(filename), extension)

            file_upload.save(os.path.join(dest_dir, filename))
            url = url_for('uploaded_file', filename=os.path.join(dest_prefix, filename))
            return json.dumps({'status': 'ok', 'url': url, 'name': filename})
    return 'ok'
            

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

def get_readable_id(publish_date, text):
    readable_id = '%s/%s' % (publish_date.strftime('%Y/%m/%d'), slugify(text))
    
    # This could have issues if a post is marked as draft, then live, then 
    # draft, then live and there are > 1 posts with the same slug. Oh well.
    count = db.session.query(Post).filter_by(readable_id=readable_id).count()
    if count > 0:
        return "%s-%d" % (readable_id, count)
    else:
        return readable_id

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
