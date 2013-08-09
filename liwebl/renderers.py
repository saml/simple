import misaka
import pygments
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from liwebl import app

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
        app.logger.info(lang)
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


