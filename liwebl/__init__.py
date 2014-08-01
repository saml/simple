import logging
from logging.handlers import RotatingFileHandler
import os

from flask import Flask

from .utils import ensure_dir
from .extensions import db
from .views import bp
from .renderers import format_datetime, format_iso8601_notz, format_iso8601, render_post

def create_app(config=None):
    app = Flask(__name__)

    configure_app(app, config)
    configure_logging(app)
    configure_blueprints(app)
    configure_extensions(app)
    configure_templates(app)

    return app


def configure_logging(app):
    log_path = app.config['LOG_PATH']
    ensure_dir(os.path.dirname(log_path))

    handler = RotatingFileHandler(log_path, maxBytes=100*1024*1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    handler.setFormatter(formatter)
    level = getattr(logging, app.config['LOG_LEVEL'])
    handler.setLevel(level)
    app.logger.addHandler(handler)
    app.logger.setLevel(level)


def configure_templates(app):
    if not app.jinja_env.filters.has_key('datetimeformat'):
        app.jinja_env.filters['datetimeformat'] = format_datetime
        app.jinja_env.filters['iso8601notz'] = format_iso8601_notz
        app.jinja_env.filters['iso8601'] = format_iso8601
        app.jinja_env.filters['render_post'] = render_post


def configure_app(app, config=None):
    app.config.from_object('settings')
    app.config.from_pyfile('settings_local.cfg', silent=True)
    app.config.from_envvar('LIWEBL_SETTINGS', silent=True)
    if config:
        app.config.from_object(config)

    app.secret_key = app.config["SECRET_KEY"]

def configure_blueprints(app):
    app.register_blueprint(bp)

def configure_extensions(app):
    db.init_app(app)
