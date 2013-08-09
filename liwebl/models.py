
import json
import mimetypes

from liwebl import app, db

from bs4 import BeautifulSoup

class Post(db.Model):
    def __init__(self, title):
        self.title = title

    __tablename__ = "posts"
    id = db.Column(db.Integer(), primary_key=True)
    draft = db.Column(db.Boolean(), index=True, default=True)
    text_type = db.Column(db.String(), default='markdown')
    created_at = db.Column(db.DateTime(timezone=True), index=True)
    updated_at = db.Column(db.DateTime(timezone=True))
    readable_id = db.Column(db.String(), index=True, unique=True, nullable=True)
    title = db.Column(db.String())
    text = db.Column(db.String(), default="")
