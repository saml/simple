from liwebl import app, db
from models import Post

def query_posts_paginated(page=1, draft=False, per_page=app.config['POSTS_PER_PAGE']):
    all_posts = db.session.query(Post).filter_by(draft=draft).order_by(Post.created_at.desc())
    total = all_posts.count()
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

def new_post(title):
    post = Post(title=title)
    db.session.add(post)
    db.session.commit()
    return post
