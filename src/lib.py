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

def user_id_exists(user_id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM users WHERE user_id = %s''', (user_id,))
    return int(cur.fetchone()[0]) > 0

def username_exists(username):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM users WHERE username = %s''', (username,))
    return int(cur.fetchone()[0]) > 0

def post_id_exists(post_id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM posts WHERE post_id = %s''', (post_id,))
    return int(cur.fetchone()[0]) > 0

def comment_id_exists(comment_id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM comments WHERE comment_id = %s''', (comment_id,))
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
        mysql.connection.rollback()
        return False

def create_comment(user_id, post_id, body):
    now = datetime.datetime.now()
    cur = mysql.connection.cursor()

    try:
        cur.execute(
            '''INSERT INTO `comments`(`comment_id`, `user_id`, `post_id`, `body`, `date_posted`) VALUES (NULL, %s, %s, %s, %s)''',
                (
                    user_id,
                    post_id,
                    body,
                    now
                )
            )
        mysql.connection.commit()
        return True
    except:
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

def get_all_comments():
    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM comments''')
    results = cur.fetchall()
    ret = []

    for result in results:
        ret.append({
            "comment_id" : result[0],
            "user_id" : result[1],
            "post_id" : result[2],
            "body" : result[3],
            "date_posted" : result[4]
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

    return {"user_id" : user[0], "username" : user[1]}

def delete_post(post_id):
    cur = mysql.connection.cursor()

    try:
        cur.execute('''DELETE FROM posts WHERE post_id = %s''', (post_id,))
        mysql.connection.commit()
        return True
    except:
        print("SQL Error")
        mysql.connection.rollback()
        return False

def get_post(post_id):
    if not post_id_exists(post_id):
        return False

    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM posts WHERE post_id = %s''', (post_id,))
    post = cur.fetchone()

    return {"post_id" : post[0], "user_id" : post[1], "body" : post[2], 
            "tags" : post[3], "date_posted" : str(post[4]), "date_edited" : str(post[5]), "amount_edits" : post[6]}

def delete_comment(comment_id):
    cur = mysql.connection.cursor()

    try:
        cur.execute('''DELETE FROM comments WHERE comment_id = %s''', (comment_id,))
        mysql.connection.commit()
        return True
    except:
        mysql.connection.rollback()
        return False

def get_comment(comment_id):
    if not comment_id_exists(comment_id):
        return False

    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM comments WHERE comment_id = %s''', (comment_id,))
    com = cur.fetchone()

    return {"comment_id" : com[0], "user_id" : com[1], "post_id" : com[2], "body" : com[3], "date_posted" : str(com[4])}
