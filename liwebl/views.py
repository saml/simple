import os
import json

from liwebl import app, db
from auth import requires_authentication, is_admin
import contents
from utils import current_datetime, refresh_cache, slugify
from forms import parse_form_for_post
from renderers import markdown_to_html

from flask import render_template, \
        request, flash, redirect, url_for, \
        abort, jsonify, Response, make_response, send_from_directory
from flask.ext.paginate import Pagination


@app.route("/")
def index():
    """ Index Page. Here is where the magic starts """
    page = request.args.get("page", 1, type=int)
    posts,count,total = contents.query_posts_paginated(page, draft=False)
    pagination = Pagination(count, page=page, total=total, 
            record_name='posts', search=False, per_page=app.config['POSTS_PER_PAGE'])

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


@app.route("/admin/posts", methods=["GET", "POST"])
@requires_authentication
def new_post():
    if request.method == 'GET':
        page = request.args.get("page", 1, type=int)
        posts,count,total = contents.query_posts_paginated(page)
        pagination = Pagination(count, page=page, total=total, 
                record_name='posts', search=False, per_page=app.config['POSTS_PER_PAGE'])
        return render_template("admin.html", posts=posts, pagination=pagination)

    title = request.form.get('title', 'untitled')
    post = contents.new_post(title)
    return redirect(url_for("edit", post_id=post.id))


@app.route("/admin/posts/<int:post_id>", methods=["GET", "POST"])
@requires_authentication
def edit(post_id):
    post = contents.get_post_by_id(post_id)
    if post is None:
        return abort(404)

    if request.method == "GET":
        return render_template("edit.html", post=post)
    
    form = request.form
    old_url = parse_form_for_post(form, post)
    contents.save_post(post)
    if old_url:
        refresh_cache([old_url])

    return redirect(url_for("edit", post_id=post_id))


@app.route("/admin/posts/<int:post_id>/delete", methods=["POST"])
@requires_authentication
def delete(post_id):
    post = contents.get_post_by_id(post_id)
    if post is None:
        return flash("Cannot find post id: %d for deletion" % post_id, category="error")

    old_url = contents.delete_post(post)
    if old_url:
        refresh_cache([old_url])

    return redirect(request.args.get("next", "")
                    or request.referrer or url_for('index'))



@app.route("/admin/posts/<int:post_id>/json", methods=["POST"])
@requires_authentication
def save_post(post_id):
    post = contents.get_post_by_id(post_id)
    if post is None:
        return abort(404)

    form = request.form
    old_url = parse_form_for_post(form, post)
    contents.save_post(post)
    return jsonify(success=True)


@app.route("/admin/posts/<int:post_id>/preview")
@requires_authentication
def preview(post_id):
    post = contents.get_post_by_id(post_id)
    if post is None:
        return abort(404)
    return render_template("view.html", post=post, preview=True)


@app.route("/admin/cache-refresh", methods=["POST"])
@requires_authentication
def cache_refresh():
    if request.json is None:
        response = make_response(jsonify(status = 'err', message = 'request entity is not application/json'))
        response.status = 400
        return response
    urls = requeset.json.get('urls', [])
    results = refresh_cache(urls)
    return json.dumps({'status': 'ok', 'results': results})

@app.route("/admin/upload", methods=["POST"])
@requires_authentication
def upload_file():
    file_upload = request.files['file']
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
        

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

