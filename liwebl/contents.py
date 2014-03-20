from flask import current_app

from .models import Post
from .utils import current_datetime, get_readable_id, full_url_of
from .extensions import db

def query_posts_paginated(page=1, draft=None):
    post_query = db.session.query(Post)
    if draft is not None:
        post_query = post_query.filter_by(draft=draft)
    all_posts = post_query.order_by(Post.created_at.desc())
    total = all_posts.count()
    per_page = current_app.config['POSTS_PER_PAGE']
    query = all_posts.limit(per_page).offset((page - 1) * int(per_page))
    result = query.all()
    return (result, query.count(), total)

def get_post(readable_id, draft=False):
    try:
        return db.session.query(Post).filter_by(readable_id=readable_id, draft=False).one()
    except:
        return None

def get_post_by_id(numeric_id):
    try:
        return db.session.query(Post).filter_by(id=numeric_id).one()
    except:
        return None


def save_post(post):
    db.session.add(post)
    db.session.commit()
    return post

def new_post(title):
    post = Post(title=title)
    post.created_at = current_datetime()
    post.readable_id = get_readable_id(post.created_at, title)
    return save_post(post)

#def old_url_of(fn):
#    @wraps(fn)
#    def _old_url_of(post):
#        was_draft = post.draft
#        old_url = full_url_of(post)
#        return fn()
#    return _old_url_of

def delete_post(post):
    was_draft = post.draft
    old_url = full_url_of(post)
    db.session.delete(post)
    db.session.commit()
    if not was_draft:
        return old_url
    return None
