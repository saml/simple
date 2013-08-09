
import json
import mimetypes

from liwebl import app, db

from bs4 import BeautifulSoup

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
        text = markdown_to_html(self.text) if self.text_type == 'markdown' else self.text
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

