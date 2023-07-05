

from flask import Flask
from flask_script import Server, Manager

from models import db
from webui import webui
from api import api
from config import config


app = Flask(__name__)
app.config.from_object(config['dev'])
app.register_blueprint(webui)
app.register_blueprint(api, url_prefix="/api")
db.init_app(app)
manager = Manager(app)
manager.add_command("runserver", Server(host="0.0.0.0", port=8080, use_debugger=True, threaded=True,ssl_crt = 'ca.crt', ssl_key = 'ca.key'))

@app.after_request
def headers(response):
    #response.headers["Server"] = "Ares"
    return response


@manager.command
def initdb():
    db.drop_all()
    db.create_all()
    db.session.commit()

    
if __name__ == '__main__':
    manager.run()
