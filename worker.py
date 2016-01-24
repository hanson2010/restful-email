# -*- coding: utf-8 -*-

import datetime, time
# todo
#import sqlite3
import threading

from flask_mail import Message

TASK_TIMEOUT = 3600
BULK_INTERVAL = 10
CHECK_TIMEOUT = 5

class Worker(threading.Thread):
    def __init__(self, app, mail, name = 'noname'):
        threading.Thread.__init__(self, name = name)
        self._app = app
        self._mail = mail
        self._stop = False
        self._task_id = 0
        self._tasks = []

    def _is_task_timeout(self, task):
        now = datetime.datetime.now()
        if (now - task['timestamp']).seconds > TASK_TIMEOUT:
            return True
        return False

    def _perform_task(self, task, conn):
        ret = {'done': False}
        self._app.logger.info(u'Sending email to %s' % (task['to'].replace(';', ', '),))
        # flask read utf-8 from config file
        # but assume it as unicode, wrong!
        prefix = ''.join([chr(ord(x)) for x in self._app.config['EMAIL_PREFIX']]).decode('utf-8')
        if prefix:
            subject = u'%s %s' % (prefix, task['subject'])
        else:
            subject = task['subject']
        recipients = task['to'].split(';')
        msg = Message(subject = subject, \
                recipients = recipients, \
                body = task['text'], \
                html = task['html'], \
                charset = 'UTF-8')
        conn.send(msg)
        return True

    def terminate(self):
        self._stop = True

    def add_task(self, task):
        self._task_id += 1
        self._tasks.append({'id': self._task_id, 'timestamp': datetime.datetime.now(), 'obj': task, 'done': False})
        self._app.logger.info(u'Task %d created' % (self._task_id,))
        return self._task_id

    def check_task(self, task_id):
        task = next((x for x in self._tasks if x['id'] == task_id), None)
        if not task:
            return {'error': u'Not found', 'done': False}
        # blocking operation
        for i in range(CHECK_TIMEOUT):
            if task['done']:
                return {'error': u'', 'done': True}
                break
            time.sleep(1)
        return {'error': u'', 'done': False}

    def run(self):
        self._app.logger.info(u'Worker started')
        delay = 0
        while True:
            if self._stop:
                break
            time.sleep(BULK_INTERVAL + delay)
            # clean items timed out
            while True:
                task = next((x for x in self._tasks if self._is_task_timeout(x)), None)
                if task:
                    self._app.logger.info(u'Task %d timed out' % (task['id'],))
                    self._tasks.remove(task)
                else:
                    break
            # working copy
            tasks = [x for x in self._tasks if x['done'] == False]
            if not tasks:
                continue
            self._app.logger.debug(u'Performing %d task(s)' % (len(tasks)))
            with self._app.app_context():
                try:
                    with self._mail.connect() as conn:
                        for task in tasks:
                            r = self._perform_task(task['obj'], conn)
                            if r == True:
                                task['done'] = r
                    delay = 0
                except Exception, e:
                    self._app.logger.error(u'Worker met exception: %s' % (e,))
                    delay += BULK_INTERVAL
