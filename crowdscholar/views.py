import json

from flask import request, session, g, redirect, url_for, \
        abort, render_template, flash, make_response, jsonify, Response
from helpers.raw_endpoint import get_id, store_json_to_file
from json_controller import JSONController
from main import app
from pymongo import MongoClient


# setup database connection
def connect_client():
    """Connects to Mongo client"""
    return  MongoClient(app.config['DATABASE_IP'], app.config['DATABASE_PORT'])

def get_db():
    """Connects to Mongo database"""
    if not hasattr(g, 'mongo_client'):
        g.mongo_client = connect_client()
        g.mongo_db = getattr(g.mongo_client, app.config['DATABASE_NAME'])
    return g.mongo_db

@app.teardown_appcontext
def close_db(error):
    """Closes connection with Mongo client"""
    if hasattr(g, 'mongo_client'):
        g.mongo_client.close()

# Begin view routes
@app.route('/')
@app.route('/index')
def index():
    """Landing pgae for Crowdscholar API"""
    return render_template("index.html")

@app.route('/ping', methods=['POST'])
def ping_endpoint():
    """API endpoint determines potential article hash exists in db

    :return: status code 204 -- hash not present, continue submissio
    :return: status code 201 -- hash already exists, drop submission
    """
    db = get_db()
    target_hash = request.form.get('hash')
    if db.raw.find({'hash': target_hash}).count():
        return Response(status=201)
    else:
        return Response(status=204)

@app.route('/raw', methods=['POST'])
def raw_endpoint():
    """API endpoint for submitting raw article data

    :return: status code 405 - invalid JSON or invalid request type
    :return: status code 400 - unsupported content-type or invalid publisher
    :return: status code 201 - successful submission
    """
    # Ensure post's content-type is supported
    if request.headers['content-type'] == 'application/json':
        # Ensure data is a valid JSON
        try:
            user_submission = json.loads(request.data)
        except ValueError:
            return Response(status=405)
        # generate UID for new entry
        uid = get_id()
        # store incoming JSON in raw storage
        store_json_to_file(user_submission, uid)
        # hand submission to controller and return Resposne
        db = get_db()
        controller_response = JSONController(user_submission, db=db, raw_file_pointer=uid).submit()
        return controller_response

    # User submitted an unsupported content-type
    else:
        return Response(status=400)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Page Not Found' } ), 404)

@app.errorhandler(405)
def method_not_allowed(error):
    return make_response(jsonify( { 'error': 'Method Not Allowed' } ), 405)