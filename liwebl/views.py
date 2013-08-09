

from liwebl import app, db
from auth import requires_authentication, is_admin
import contents

from flask import render_template, \
        request, flash, redirect, url_for, \
        abort, jsonify, Response, make_response
from flask.ext.paginate import Pagination

import datetime

def current_datetime():
    return datetime.datetime.utcnow()

@app.route("/")
def index():
    """ Index Page. Here is where the magic starts """
    page = request.args.get("page", 1, type=int)
    posts,count,total = contents.query_posts_paginated(page, draft=False)
    pagination = Pagination(posts_result.count(), 
            page=page, total=total, record_name='posts', search=False, per_page=app.config['POSTS_PER_PAGE'])

    return render_template("index.html", 
                           posts=posts,
                           pagination=pagination,
                           now=current_datetime(),
                           is_admin=is_admin())

@app.route("/<path:readable_id>.html")
def view_post_slug(readable_id):
    post = contents.get_post(readable_id, draft=False)
    if post is None:
        return abort(404)
    return render_template("view.html", post=post, is_admin=is_admin())


@app.route("/new", methods=["POST"])
@requires_authentication
def new_post():
    title = request.form.get('title', 'untitled')
    post = contents.new_post(title)
    return redirect(url_for("edit", post_id=post.id))


@app.route("/edit/<int:post_id>", methods=["GET", "POST"])
@requires_authentication
def edit(post_id):
    post = contents.get_post_by_id(post_id)
    if post is None:
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

