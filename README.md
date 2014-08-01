# Getting Started

    virtualenv venv
    . venv/bin/activate
    pip install -r requirements.txt
    vim settings_local.cfg # and override some of settings.py values.
    python manage.py shell
    > db.create_all()
    ^D
    python manage.py runserver --debug

