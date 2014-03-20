from flask_script import Shell, Manager, Server

from liwebl import create_app
from liwebl.extensions import db

app = create_app()
manager = Manager(app)

def _make_context():
    return dict(app=app, db=db)
    
if __name__ == '__main__':
    manager.add_command('runserver', Server())
    manager.add_command('shell', Shell(make_context=_make_context))
    manager.run()