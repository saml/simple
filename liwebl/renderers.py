import misaka
import pygments
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

import pytz

markdown_extensions = (
    misaka.EXT_NO_INTRA_EMPHASIS |
    misaka.EXT_AUTOLINK |
    misaka.EXT_TABLES |
    misaka.EXT_FENCED_CODE |
    misaka.EXT_LAX_HTML_BLOCKS |
    misaka.EXT_SPACE_HEADERS |
    misaka.EXT_SUPERSCRIPT
)
markdown_flags = (
    misaka.HTML_TOC
)

class CodeHtmlFormatter(HtmlFormatter):
    def wrap(self, source, outfile):
        return self._wrap_code(source)
    def _wrap_code(self, source):
        yield 0, '<code class="%s">' % self.cssclass
        for i, t in source:
            if i == 1:
                # it's a line of formatted code
                t += '<br>'
            yield i, t
        yield 0, '</code>'

pygments_formatter = HtmlFormatter(cssclass='codehilite')

# Create a custom renderer
class BleepRenderer(misaka.HtmlRenderer, misaka.SmartyPants):
    def block_code(self, text, lang):
        if not lang:
            lang = 'text'
        lexer = get_lexer_by_name(lang, stripall=True)
        return pygments.highlight(text, lexer, pygments_formatter)

markdown_renderer = BleepRenderer(markdown_flags)
markdown = misaka.Markdown(markdown_renderer, extensions=markdown_extensions)

def markdown_to_html(s):
    return markdown.render(s)



def format_datetime(date, format='%Y-%m-%d %I:%m %p %Z'):
    if not date:
        return ''
    if not date.tzinfo:
        date = date.replace(tzinfo=pytz.utc)
    return date.strftime(format)

def format_iso8601_notz(date):
    return format_datetime(date, '%Y-%m-%dT%H:%M:%S')

def format_iso8601(date):
    if not date:
        return ''
    if not date.tzinfo:
        date = date.replace(tzinfo=pytz.utc)
    return date.isoformat()
    
def render_post(post):
    if post.text_type == 'markdown':
        return markdown_to_html(post.text)
    return post.text


