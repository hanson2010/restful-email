# -*- coding: utf-8 -*-

import json

from flask import Flask, request, abort, g
from flask_mail import Mail

from worker import Worker

# configuration
DEBUG = True

API_USERS = [
        ('user1', 'key1'),
        ('user2', 'key2'),
    ]
EMAIL_PREFIX = u'[prefix]'

MAIL_SERVER = 'smtp.server.com'
MAIL_PORT = 465
MAIL_USE_TLS = False
MAIL_USE_SSL = True
MAIL_USERNAME  = 'user@server.com'
MAIL_PASSWORD = 'pass'
MAIL_DEFAULT_SENDER  = 'user@server.com'
MAIL_MAX_EMAILS = 10

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('RE_SETTINGS', silent=True)

# global variables
mail = Mail()
workers = []

def init_workers():
    global mail
    global workers
    with app.app_context():
        mail.init_app(app)
        worker = Worker(app, mail)
        # start the thread
        worker.start()
        workers.append(worker)

@app.before_request
def before_request():
    global workers
    g.wks = workers

@app.route('/api/mail.send.json', methods=['POST'])
def mail_send_json():
    api_user = request.form.get('api_user')
    api_key = request.form.get('api_key')
    if (api_user, api_key) not in app.config['API_USERS']:
        return json.dumps({'error': u'Invalid API user: %s' % (api_user,), 'task_id': 0})
    if not request.form.has_key('to'):
        return json.dumps({'error': u'Form field [to] is required', 'task_id': 0})
    if not request.form.has_key('subject'):
        return json.dumps({'error': u'Form field [subject] is required', 'task_id': 0})
    # find an available worker
    if not g.wks:
        app.logger.error(u'No worker available')
        abort(500)
    worker = g.wks[0]
    task_id = worker.add_task({
            'to': request.form.get('to'),
            'subject': request.form.get('subject'),
            'text': request.form.get('text'),
            'html': request.form.get('html')
        })
    return json.dumps({'error': u'', 'task_id': task_id})

@app.route('/api/mail.task.json', methods=['GET'])
def mail_task_json():
    task_id = int(request.args.get('id', '0'))
    if not task_id:
        return json.dumps({'error': u'No task ID provided', 'done': False})
    # find an available worker
    if not g.wks:
        app.logger.error(u'No worker available')
        abort(500)
    worker = g.wks[0]
    result = worker.check_task(task_id)
    return json.dumps(result)

if __name__ == '__main__':
    init_workers()
    app.run()
