""" simple """

from liwebl import app

if not app.debug:
    import logging
    from logging.handlers import RotatingFileHandler
    handler = RotatingFileHandler(app.config['LOG_PATH'], maxBytes=100*1024*1024, backupCount=5)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'
        '[in %(filename)s:%(lineno)d]'
        ))
    handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
    app.logger.addHandler(handler)
    app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))



if __name__ == "__main__":
    app.run(host="0.0.0.0")
