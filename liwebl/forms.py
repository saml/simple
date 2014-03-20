import dateutil.parser
import pytz

from utils import current_datetime, full_url_of


def parse_form_for_post(form, post):
    
    title = form.get('title')
    readable_id = form.get('readable_id')
    text_type = form.get('text_type')
    created_at = form.get('created_at')
    if created_at is not None:
        created_at = dateutil.parser.parse(created_at)
        if created_at.tzinfo:
            created_at = created_at.astimezone(pytz.utc)

    updated_at = current_datetime()
    text = form.get('text', '')
    is_draft = any(form.getlist("draft", type=int))

    old_url = full_url_of(post)
    was_draft = post.draft

    post.text = text
    post.text_type = text_type
    post.draft = is_draft
    post.updated_at = updated_at
    post.created_at = created_at
    post.readable_id = readable_id
    post.title = title

    if not was_draft:
        return old_url
    return None

    
    
