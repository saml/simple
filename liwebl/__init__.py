from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

from renderers import format_datetime, format_iso8601_notz, format_iso8601, render_post

app = Flask(__name__)
app.config.from_object('settings')
app.secret_key = app.config["SECRET_KEY"]

db = SQLAlchemy(app)


if not app.jinja_env.filters.has_key('datetimeformat'):
    app.jinja_env.filters['datetimeformat'] = format_datetime
    app.jinja_env.filters['iso8601notz'] = format_iso8601_notz
    app.jinja_env.filters['iso8601'] = format_iso8601
    app.jinja_env.filters['render_post'] = render_post



from liwebl.views import *
