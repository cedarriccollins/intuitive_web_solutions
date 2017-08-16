from flask import Flask, jsonify, abort, request, make_response, url_for, Response
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, MetaData, Table, update
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
import json
import decimal, datetime
from flask_cors import CORS, cross_origin

#app = Flask(__name__, static_url_path = "")
app = Flask(__name__)
CORS(app , resources=r'/api/*')
auth = HTTPBasicAuth()

#-- move to config file
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://terrell-mac:beer@localhost/iws_ticket'
#-- flasktest.cvpsfhju0zho.us-east-2.rds.amazonaws.com:5432 

PRODUCT_AREAS  = ('Policies', 'Billing', 'Claims', 'Reports')

engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
metadata = MetaData(engine,reflect=True)

client_issue_table = Table('client_issue', metadata, autoload=True)
iws_user_table = Table('iws_user', metadata, autoload=True)

@auth.get_password
def get_password(username):
    if username == 'cedarric':
        return 'python_rocks'
    return None

@auth.error_handler
def unauthorized():
    return make_response(jsonify( { 'error': 'Unauthorized access' } ), 403)
    # return 403 instead of 401 to prevent browsers from displaying the default auth dialog
    
@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify( { 'error': 'Bad request' } ), 400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)

@app.errorhandler(405)
def not_found(error):
    return make_response(jsonify( { 'error': 'Method Not Allowed' } ), 405)


def alchemyencoder(obj):
    """ handle dates and decimals """
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, decimal.Decimal):
        return float(obj)

def make_public_issue(issue):
    new_issue = {}
    for field in issue:
        if field == 'id':
            new_issue['uri'] = url_for('get_issue', issue_id = issue['issue_id'], _external = True)
        else:
            new_issue[field] = issue[field]
    return new_issue
    
@app.route('/api/v1.0/issues', methods = ['GET'])
@auth.login_required
def get_issues():
    res = engine.execute(select([client_issue_table]))
    data = json.dumps([dict(r) for r in res],default=alchemyencoder)
    return Response({data}, mimetype='application/json')
    
@app.route('/api/v1.0/issues/<int:issue_id>', methods = ['GET'])
@auth.login_required
def get_issue(issue_id):

    res = engine.execute(select([client_issue_table], client_issue_table.c.issue_id == issue_id))
    data = json.dumps([dict(r) for r in res],default=alchemyencoder)

    return Response(data, mimetype='application/json')

@app.route('/api/v1.0/issues/client/<string:client_name>', methods = ['GET'])
@auth.login_required
def get_issue_per_company(client_name):

    res = engine.execute(select([client_issue_table], client_issue_table.c.client_name == client_name))
    data = json.dumps([dict(r) for r in res],default=alchemyencoder)
    return Response(data, mimetype='application/json')

@app.route('/api/v1.0/issues', methods = ['GET','POST'])
@cross_origin()
@auth.login_required
def create_issue():

    if not request.json or not 'title' in request.json:
        abort(400)

    insert = client_issue_table.insert().values(request.json, \
        product_area=PRODUCT_AREAS[request.json['product_area']],
        client_name =request.json['client_name'].upper())
    insert.execute()
    return jsonify( [make_public_issue(request.get_json())] ), 201

@app.route('/api/v1.0/issues/<int:issue_id>', methods = ['PUT'])
@auth.login_required
def update_issue(issue_id):

    if not request.json:
        abort(400)

    issue = {}
    
    if 'title' in request.json:
        issue['title']=request.json['title']
    
    if 'description' in request.json:
        issue['description']=request.json['description' ]
    
    if 'client_priority' in request.json:
        issue['client_priority']=request.json['client_priority']
    
    if 'target_date' in request.json:
        issue['target_date']=request.json['target_date']

    if 'product_area' in request.json:
        issue['product_area']=PRODUCT_AREAS[request.json['product_area']]

    if 'client_name' in request.json:
        issue['client_name']=request.json['client_name'].upper()
    
    if 'done' in request.json:
        issue['done']= request.json['done']
 
    update = client_issue_table.update().where(client_issue_table.c.issue_id==issue_id).values(issue)
    update.execute()
    return jsonify( [make_public_issue(issue)] ), 201

@app.route('/api/v1.0/issues/<int:issue_id>', methods = ['DELETE'])
@auth.login_required
def delete_issue(issue_id):
    result = engine.execute(client_issue_table.delete().where(client_issue_table.c.issue_id==issue_id))
    print result
    return jsonify( { 'deleted':issue_id,'result': True } )
    
if __name__ == '__main__':
    app.run(debug = True)



