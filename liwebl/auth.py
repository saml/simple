from functools import wraps
import re

from flask import request, Response, current_app
from werkzeug.security import check_password_hash

PASSWORD_HASH = re.compile(r'[^$]+\$[^$]+\$[^$]+')

def is_password_hash(password):
    return True


def is_admin():
    authorization = request.authorization
    admin_username = current_app.config['ADMIN_USERNAME']
    admin_password = current_app.config['ADMIN_PASSWORD']
    if authorization and authorization.username == admin_username:
        if PASSWORD_HASH.match(admin_password):
            return check_password_hash(admin_password, authorization.password)
        return admin_password == authorization.password
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

