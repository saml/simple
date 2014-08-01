import os

_curdir = os.path.dirname(__file__)

POSTS_PER_PAGE=20
BLOG_URL='http://localhost:5000'
CACHE_FLUSH_COMMAND='./recache.bash'
UPLOAD_FOLDER='./uploads'
ADMIN_USERNAME='admin'
ADMIN_PASSWORD='admin'
LOG_PATH='./logs/app.log'
LOG_LEVEL='DEBUG'
SECRET_KEY='abc'
SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/simple.db' % _curdir
