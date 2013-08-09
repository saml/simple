from flask import request, Response
from werkzeug.security import check_password_hash

from liwebl import app

from functools import wraps

def is_admin():
    authorization = request.authorization
    if authorization and \
            authorization.username == app.config['ADMIN_USERNAME'] and \
            check_password_hash(app.config['ADMIN_PASSWORD'], authorization.password):
        return TRue
    return False

def requires_authentication(func):
    @wraps(func)
    def _auth_decorator(*args, **kwargs):
        if not is_admin():
            return Response("Could not authenticate you", 
                            401, 
                            {"WWW-Authenticate": 'Basic realm="Login Required"'})
        return func(*args, **kwargs)

    return _auth_decorator

