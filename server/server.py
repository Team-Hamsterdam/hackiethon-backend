from flask import Flask, request, make_response
from flask_cors import CORS
import sqlite3,sys
from werkzeug.exceptions import HTTPException
import hashlib
import jwt
from flask_cors import CORS, cross_origin
app = Flask(__name__)
CORS(app)


class ConflictError(HTTPException):
    code = 409
    message = 'No message specified'

class NotFound(HTTPException):
    code = 404
    message = 'No message specified'

class AccessError(HTTPException):
    code = 403
    message = 'No message specified'

class InputError(HTTPException):
    code = 400
    message = 'No message specified'

def hasher(string):
    return hashlib.sha256(string.encode()).hexdigest()

# Generates a token for a registered user
def generate_token(username):
    '''
    Generates a JSON Web Token (JWT) encoded token for a given username
    Input: username (str)
    Output: JWT-encoded token (str)
    '''
    private_key = 'HamsterHealthIsTheBestWebsite'
    return jwt.encode({'username': username}, private_key, algorithm='HS256')

# @app.after_request
# def after_request_func(response):
#     response = make_response()
#     response.headers.add("Access-Control-Allow-Origin", "*")
#     response.headers.add("Access-Control-Allow-Headers", "*")
#     response.headers.add("Access-Control-Allow-Methods", "*")
#     return response


@app.route('/auth/login', methods=['POST'])
@cross_origin()
def auth_login():
    con = sqlite3.connect('../database/hackiethon.db')
    cur = con.cursor()
    data = request.get_json()
    if data['username'] is None or data['password'] is None:
        raise InputError ('Please enter your username and password')
    query = '''select u.token, u.password from user u where u.username = "{}"; '''.format(data['username'])
    cur.execute(query)
    x = cur.fetchone()
    if x is None:
        raise AccessError ('Invalid username')
    token,password = x
    hashed_password = hasher(data['password'])
    if hashed_password != password:
        raise AccessError ('Incorrect password')

    cur.execute('BEGIN TRANSACTION;')
    cur.execute('''UPDATE user set logged_in = 1 where user.token = "{}";'''.format(token))
    cur.execute('COMMIT;')

    return {'token': token}

@app.route('/auth/register', methods=['POST'])
@cross_origin()
def auth_register():
    con = sqlite3.connect('../database/hackiethon.db')
    cur = con.cursor()
    data = request.get_json()
    if data['username'] is None or data['password'] is None or data['name'] is None or data['email'] is None:
        raise InputError ('Please fill in all details')
    print(data)
    # Checks if username is unique
    query = '''select u.username from user u where u.username = "{}"; '''.format(data['username'])
    cur.execute(query)
    x = cur.fetchone()
    if x is not None:
        raise ConflictError ('Username already taken')

    # Checks if email is unique
    query = '''select u.email from user u where u.email = "{}"; '''.format(data['email'])
    cur.execute(query)
    x = cur.fetchone()
    if x is not None:
        raise ConflictError ('Email already in use')

    hashed_password = hasher(data['password'])
    token = generate_token(data['username'])
    cur.execute('BEGIN TRANSACTION;')
    query = '''
                INSERT INTO user (token, username, password, email, name, level, xp) VALUES ("{}", "{}", "{}", "{}", "{}", 0, 0);

            '''.format(token, data['username'], hashed_password, data['email'], data['name'])
    cur.execute(query)
    cur.execute('COMMIT;')
    return {'token': token}

@app.route('/auth/check', methods=['GET'])
@cross_origin()
def auth_check():
    con = sqlite3.connect('../database/hackiethon.db')
    cur = con.cursor()
    data = request.get_json()
    if data['token'] is None:
        raise AccessError ("Invalid Token")
    query = '''select u.logged_in from user.u where u.token = "{}";'''.format(data['token'])
    cur.execute(query)
    x = cur.fetchone()
    if x is None:
        raise AccessError ("Invalid Token")
    if x is False:
        raise AccessError ("User not logged in")
    return {'token': data['token']}

@app.route('/task/create', methods=['POST'])
@cross_origin()
def task_create():
    con = sqlite3.connect('../database/hackiethon.db')
    cur = con.cursor()
    data = request.get_json()
    if data['title'] is None:
        raise InputError ("Please enter a title")
    # Generate task_id
    task_id = 0
    query = '''select max(t.task_id) from task t;'''
    cur.execute(query)
    x = cur.fetchone()
    task_id_tuple = x
    if x is None:
        task_id_tuple[0] = 1
    task_id = task_id_tuple[0]
    task_id += 1
    task_xp = 5
    # Insert task into database
    cur.execute('BEGIN TRANSACTION;')
    query = '''INSERT INTO task (token, task_id, title, description, task_xp, is_custom)
                VALUES ("{}", {}, "{}", "{}", {}, {});'''.format(data['token'], task_id, data['title'], data['description'], task_xp, 1)
    cur.execute(query)
    cur.execute('COMMIT;')
    # Insert task into user task list
    # query = '''BEGIN TRANSACTION;
    #             INSERT INTO active_task (token, task_id, title, description, is_completed) VALUES ("{}", {}, "{}", "{}", 0);
    #            COMMIT;
    #         '''.format(data['token'], task_id, data['title'], data['description'])
    # cur.execute(query)
    return {'task_id': task_id}

@app.route('/task/edit', methods=['PUT'])
@cross_origin()
def task_edit():
    con = sqlite3.connect('../database/hackiethon.db')
    cur = con.cursor()
    data = request.get_json()
    if data['title'] is None:
        raise InputError ("Please enter a title")
    cur.execute('BEGIN TRANSACTION;')
    query = '''UPDATE active_task t
                SET  t.title = "{}",
                     t.description = "{}"
                WHERE t.task_id = {};'''.format(data['title'], data['description'], data['task_id'])
    cur.execute(query)
    cur.execute('COMMIT;')
    return {}

@app.route('/task/remove', methods=['DELETE'])
@cross_origin()
def task_remove():
    con = sqlite3.connect('../database/hackiethon.db')
    cur = con.cursor()
    data = request.get_json()
    if data['token'] is None:
        raise AccessError ("Invalid Token")
    query = '''select u.token from user u where u.token = "{}";'''.format(data['token'])
    cur.execute(query)
    x = cur.fetchone()
    if x is None:
        raise AccessError ("Invalid Token")
    if data['task_id'] is None:
        raise NotFound ("Task not found")
    cur.execute('BEGIN TRANSACTION;')
    query = '''DELETE FROM task
                WHERE task.task_id = {} and task.token = "{}";'''.format(data['task_id'], data['token'])
    cur.execute(query)
    cur.execute('COMMIT;')
    return {}

@app.route('/task/removeactivetask', methods=['DELETE'])
@cross_origin()
def task_removepersonal():
    con = sqlite3.connect('../database/hackiethon.db')
    cur = con.cursor()
    data = request.get_json()
    if data['token'] is None:
        raise AccessError ("Invalid Token")
    query = '''select u.token from user u where u.token = "{}";'''.format(data['token'])
    cur.execute(query)
    x = cur.fetchone()
    if x is None:
        raise AccessError ("Invalid Token")
    if data['task_id'] is None:
        raise NotFound ("Task not found")
    cur.execute('BEGIN TRANSACTION;')
    query = '''DELETE FROM active_task
                WHERE active_task.task_id = {} and active_task.token = "{}";'''.format(data['task_id'], data['token'])
    cur.execute(query)
    cur.execute('COMMIT;')
    return {}

@app.route('/task/addactivetask', methods=['POST'])
@cross_origin()
def task_add_active_task():
    con = sqlite3.connect('../database/hackiethon.db')
    cur = con.cursor()
    data = request.get_json()
    if data['token'] is None:
        raise AccessError ("Invalid Token")
    query = '''select u.token from user u where u.token = "{}";'''.format(data['token'])
    cur.execute(query)
    x = cur.fetchone()
    if x is None:
        raise AccessError ("Invalid Token")
    if data['task_id'] is None:
        raise NotFound ("Task not found")
    query = '''select task.title, task.description from task
                where task.task_id = {};'''.format(data['task_id'])
    cur.execute(query)
    x = cur.fetchone()
    title, description = x
    cur.execute('BEGIN TRANSACTION;')
    query = '''INSERT INTO active_task (token, task_id, title, description, is_completed)
                VALUES ("{}", {}, "{}", "{}", 0);'''.format(data['token'], data['task_id'], title, description)
    cur.execute(query)
    cur.execute('COMMIT;')
    return {}

@app.route('/task/finish', methods=['PUT'])
@cross_origin()
def task_finish():
    con = sqlite3.connect('../database/hackiethon.db')
    cur = con.cursor()
    xp_threshold = 3
    new_level = 0
    new_xp = 0
    data = request.get_json()
    if data['token'] is None:
        raise AccessError ("Invalid Token")
    if data['task_id'] is None:
        raise NotFound ("Task not found")
    query = '''select u.token from user u where u.token = "{}";'''.format(data['token'])
    cur.execute(query)
    x = cur.fetchone()
    if x is None:
        raise AccessError ("Invalid Token")
    cur.execute('BEGIN TRANSACTION;')
    query = '''UPDATE active_task
                SET  is_completed = True
                WHERE active_task.token = "{}";'''.format(data['token'])
    cur.execute(query)
    cur.execute('COMMIT;')
    cur.execute('''select task.task_xp from task where task.task_id = {};'''.format(data['task_id']))
    x = cur.fetchone()
    task_xp = x
    query = '''select u.level, u.xp from user u where u.token = "{}";'''.format(data['token'])
    cur.execute(query)
    x = cur.fetchone()
    level, user_xp = x
    if (user_xp + task_xp[0]) >= xp_threshold:
        new_xp = (user_xp + task_xp[0]) - xp_threshold
        new_level = level + 1
    else:
        new_xp = user_xp + task_xp[0]
        new_level = level
    cur.execute('BEGIN TRANSACTION;')
    query = ''' UPDATE user
                    SET level = {},
                        xp = {}
                WHERE token = "{}";'''.format(new_level, new_xp, data['token'])
    cur.execute(query)
    cur.execute('COMMIT;')

    return {}

@app.route('/task/gettasks', methods=['GET'])
@cross_origin()
def task_gettasks():
    tasks_list = []
    con = sqlite3.connect('../database/hackiethon.db')
    cur = con.cursor()
    data = request.headers.get('Authorization')
    if data is None:
        raise AccessError ("Invalid Token")
    query = '''select u.token from user u where u.token = "{}";'''.format(data)
    cur.execute(query)
    x = cur.fetchall()
    print(x)
    if x is None:
        raise AccessError ("Invalid Token")
    query = '''select task.task_id, task.title, task.description, task.task_xp, task.is_custom from task
                join active_task active on active.task_id = task.task_id
                where active.token = "{}";'''.format(data)
    cur.execute(query)
    while True:
        x = cur.fetchone()
        if x is None:
            break
        task_id, title, description, task_xp, is_custom = x
        task = {
            'task_id': task_id,
            'title': title,
            'description': description,
            'task_xp': task_xp,
            'is_custom': is_custom
        }
        tasks_list.append(task)


    return {"tasks": tasks_list}

@app.route('/task/getourtasks', methods=['GET'])
@cross_origin()
def task_get_our_tasks():
    tasks_list = []
    con = sqlite3.connect('../database/hackiethon.db')
    cur = con.cursor()
    data = request.headers.get('Authorization')
    if data is None:
        raise AccessError ("Invalid Token")
    query = '''select u.token from user u where u.token = "{}";'''.format(data)
    cur.execute(query)
    x = cur.fetchall()
    print(x)
    if x is None:
        raise AccessError ("Invalid Token")
    query = '''select task.task_id, task.title, task.description, task.task_xp, task.is_custom from task
                where task.is_custom = 0;'''
    cur.execute(query)
    while True:
        x = cur.fetchone()
        if x is None:
            break
        task_id, title, description, task_xp, is_custom = x
        task = {
            'task_id': task_id,
            'title': title,
            'description': description,
            'task_xp': task_xp,
            'is_custom': is_custom
        }
        tasks_list.append(task)


    return {"tasks": tasks_list}

@app.route('/task/getcustomtasks', methods=['GET'])
@cross_origin()
def task_get_custom_tasks():
    tasks_list = []
    con = sqlite3.connect('../database/hackiethon.db')
    cur = con.cursor()
    data = request.headers.get('Authorization')
    if data is None:
        raise AccessError ("Invalid Token")
    query = '''select u.token from user u where u.token = "{}";'''.format(data)
    cur.execute(query)
    x = cur.fetchall()
    print(x)
    if x is None:
        raise AccessError ("Invalid Token")
    query = '''select task.task_id, task.title, task.description, task.task_xp, task.is_custom from task
                where task.is_custom = 1;'''
    cur.execute(query)
    while True:
        x = cur.fetchone()
        if x is None:
            break
        task_id, title, description, task_xp, is_custom = x
        task = {
            'task_id': task_id,
            'title': title,
            'description': description,
            'task_xp': task_xp,
            'is_custom': is_custom
        }
        tasks_list.append(task)


    return {"tasks": tasks_list}

@app.route('/user/list', methods=['GET'])
@cross_origin()
def user_list():
    num_users = 50
    con = sqlite3.connect('../database/hackiethon.db')
    cur = con.cursor()
    users_list = []
    data = request.get_json()
    if data['token'] is None:
        raise AccessError ("Invalid Token")
    query = '''select u.token from user.u where u.token = "{}";'''.format(data['token'])
    cur.execute(query)
    x = cur.fetchone()
    if x is None:
        raise AccessError ("Invalid Token")
    query = '''SELECT u.username, u.level, u.xp
                FROM user u
                LIMIT {}
                ORDER BY u.level DESC, u.xp DESC;'''.format(num_users)
    cur.execute(query)
    while True:
        x = cur.fetchone()
        if x is None:
            break
        username, level, xp = x
        user = {
            'username': username,
            'level': level,
            'xp': xp,
        }
        user_list.append(user)
    return {'users': users_list}

@app.route('/user/details', methods=['GET'])
@cross_origin()
def user_details():
    con = sqlite3.connect('../database/hackiethon.db')
    cur = con.cursor()
    data = request.get_json()
    if data['token'] is None:
        raise AccessError ("Invalid Token")
    query = '''select u.token from user.u where u.token = "{}";'''.format(data['token'])
    cur.execute(query)
    x = cur.fetchone()
    if x is None:
        raise AccessError ("Invalid Token")
    cur.execute('select u.username, u.level, u.xp from user u where u.token = "{}";').format(data['token'])
    x = cur.fetchone()
    username, level, xp = x
    user = {
        'username': username,
        'level': level,
        'xp': xp,
    }
    return {'users': user}

# @app.route('/user/details', methods=['GET'])
# @cross_origin()
# def user_details():
#     con = sqlite3.connect('../database/hackiethon.db')
#     cur = con.cursor()
#     data = request.get_json()
#     if data['token'] is None:
#         raise AccessError ("Invalid Token")
#     query = '''select u.token from user.u where u.token = "{}";'''.format(data['token'])
#     cur.execute(query)
#     x = cur.fetchone()
#     if x is None:
#         raise AccessError ("Invalid Token")

if __name__ == '__main__':
    app.run(debug=True, port=4500)