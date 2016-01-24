# restful-email
A flask application exposes RESTful API for backend SMTP server.

## Features
* Text and HTML
* Async processing and task queues
* Bulk sending and connection reuse

## Setup
* Install libs:
  * pip install flask
  * pip install flask-mail
* Define parameters:
  * Change the content in config.py
  * Create an envvar *RE_SETTINGS* pointing at the config file
* Start up application by python restful-email/app.py
* Post data to http://127.0.0.1:5000/api/mail.send.json
