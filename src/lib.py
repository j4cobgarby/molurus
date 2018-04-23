from flask import Flask, request, Response, session
from flask_mysqldb import MySQL
import hashlib
import json
import datetime

PERMS = [
        "cp", "ep", "dp", # post
        "cc", "ec", "dc", # comment
        "bu", "du" # user
        ]

config_file = open("config", "r")
config_lines = config_file.readlines()
config = {}
for ln in config_lines:
    pieces = ln.split("=")
    config[pieces[0]] = pieces[1].rstrip()

app = Flask(__name__)

for k, v in config.items():
    app.config[k] = v

app.secret_key = config["SECRET_KEY"]

mysql = MySQL(app)

'''
Helper functions to be used in the api functions.
'''

def user_id_exists(user_id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM users WHERE user_id = %s''', (user_id,))
    return int(cur.fetchone()[0]) > 0

def username_exists(username):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM users WHERE username = %s''', (username,))
    return int(cur.fetchone()[0]) > 0

def is_logged_in():
    return ("user_id" in session)

def username_from_userid(user_id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT username FROM users WHERE user_id = %s''', (user_id,))
    return cur.fetchone()[0]

def userid_from_username(username):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT user_id FROM users WHERE username = %s''', (username,))
    return int(cur.fetchone()[0])

def return_simple(status, info):
    json_string = json.dumps({"status" : status, "info" : info})
    return Response(json_string, mimetype="application/json")

def hash_password(password, salt):
    pass_bytes = str.encode(salt + password)
    pass_hash = hashlib.sha512(pass_bytes).hexdigest()
    return pass_hash

def create_user(username, email, password, permissions):
    print("Creating user {}".format(username))

    pass_hash = hash_password(password, username) 
    
    # Insert the new user into the database
    cur = mysql.connection.cursor()

    try:
        cur.execute(
            '''INSERT INTO `users`(`user_id`, `username`, `email_address`, `pass_hash`, `permissions`, `preferred_colour_scheme`) 
                VALUES (NULL, %s, %s, %s, %s, %s)''',
                (username, email, pass_hash, permissions, 1))
        mysql.connection.commit()
        return True
    except:
        print("SQL Error.")
        mysql.connection.rollback()
        return False

def login_validate(username, password):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM users WHERE username = %s AND pass_hash = %s''', (username, hash_password(password, username)))
    return int(cur.fetchone()[0]) > 0
    
def create_post(user_id, body, tags):
    now = datetime.datetime.now()

    cur = mysql.connection.cursor()

    try:
        cur.execute(
            '''INSERT INTO `posts`(`post_id`, `user_id`, `body`, `tags`, `date_posted`, `date_edited`, `amount_edits`) VALUES (NULL, %s, %s, %s, %s, %s, %s)''',
                (
                    user_id,
                    body,
                    tags,
                    now,
                    now,
                    0
                )
            )
        mysql.connection.commit()
        return True
    except:
        print("SQL Error.")
        mysql.connection.rollback()
        return False

def get_all_posts():
    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM posts''')
    results = cur.fetchall()
    ret = []

    for result in results:
        d = {
            "post_id" : result[0],
            "user_id" : result[1],
            "body" : result[2],
            "tags" : result[3],
            "date_posted" : result[4].strftime("%Y-%M-%d"),
            "date_edited" : result[5].strftime("%Y-%M-%d"),
            "amount_edits" : result[6]
        }

        ret.append(d)

    return ret


def get_all_users():
    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM users''')
    results = cur.fetchall()
    ret = []

    for result in results:
        ret.append({
            "user_id" : result[0],
            "username" : result[1]
            })

    return ret

def get_user_permissions(user_id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT permissions FROM users WHERE user_id = %s''', (user_id,))
    
    result = cur.fetchone()[0]
    print(result)

    if result == '*':
        return PERMS

    return result.split(",")
   
def delete_user(user_id):
    cur = mysql.connection.cursor()
   
    try:
        cur.execute('''DELETE FROM users WHERE user_id = %s''', (user_id,))
        mysql.connection.commit()
        return True
    except:
        print("SQL Error")
        mysql.connection.rollback()
        return False

def get_user(user_id):
    if not user_id_exists(user_id):
        return False

    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM users WHERE user_id = %s''', (user_id,))
    user = cur.fetchone()

    print("User: " + str(user))

    return {"user_id" : user[0], "username" : user[1]}
