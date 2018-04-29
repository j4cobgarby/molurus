from flask import Flask, request, Response, session
from flask_mysqldb import MySQL
import hashlib
import json
import datetime
import secrets

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

def token_exists(token):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM api_tokens WHERE token = %s''', (token,))
    return int(cur.fetchone()[0]) > 0

def user_id_has_token(user_id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM api_tokens WHERE user_id = %s''', (user_id,))
    return int(cur.fetchone()[0]) > 0

def user_id_from_token(token):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT user_id FROM api_tokens WHERE token = %s''', (token,))
    return int(cur.fetchone()[0])

def user_id_from_request_args(args):
    if "api_token" not in args:
        return False

    tok = args["api_token"]

    if not token_exists(tok):
        return False

    user_id = user_id_from_token(tok)

    if not user_id_exists(user_id):
        return False

    return user_id

# Checks if both the user and the client both have permission
#  to do something specified by perms.
#
# args is a request.args dictionary
#
# perms is a list of permissions to be checked, or empty for
#  no permissions needed.
#
# returns True if authenticated, otherwise False
# False is also returned in the case of errors
def authenticate(args, perms):
    user_id = user_id_from_request_args(args)

    if not user_id:
        return False

    user_perms = get_user_permissions(user_id)
    client_perms = get_api_token_permissions(args["api_token"])

    print(user_perms, client_perms)

    if len(perms) == 0:
        return True

    for perm in perms:
        if perm not in user_perms or perm not in client_perms:
            return False

    return True

# almost identical to authenticate(...), except you don't
# need the permission to delete the component if you're the
# owner of it
def authenticate_delete(args, component_owner, perms):
    user_id = user_id_from_request_args(args)

    if not user_id:
        return False

    user_perms = get_user_permissions(user_id)
    client_perms = get_api_token_permissions(args["api_token"])

    if len(perms) == 0 or user_id == component_owner:
        return True

    for perm in perms:
        if perm not in user_perms or perm not in client_perms:
            return False

    return True

def delete_user_id_token(user_id):
    if not user_id_has_token(user_id):
        return

    cur = mysql.connection.cursor()

    try:
        cur.execute('''DELETE FROM api_tokens WHERE user_id = %s''', (user_id,))
        mysql.connection.commit()
        return True
    except:
        mysql.connection.rollback()
        return False

def new_api_token(user_id, permissions):
    if not user_id_exists(user_id):
        return False

    if user_id_has_token(user_id): # this user already has a token.
        delete_user_id_token(user_id)

    tok = secrets.token_hex(64)

    while (token_exists(tok)): # make sure to get a unique token
        tok = secrets.token_hex(64)

    print(tok)

    cur = mysql.connection.cursor()
    try:
        cur.execute('''INSERT INTO `api_tokens`(`token_id`, `token`, `user_id`, `client_permissions`) 
                        VALUES (NULL, %s, %s, %s)''',
                (tok, user_id, permissions))
        mysql.connection.commit()
        return True, tok
    except:
        mysql.connection.rollback()
        return False, ""

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
            '''INSERT INTO `users`
                (`user_id`, `username`, `email_address`, `pass_hash`, `permissions`, `preferred_colour_scheme`) 
                VALUES (NULL, %s, %s, %s, %s, %s)''',
                (username, email, pass_hash, permissions, 1))
        mysql.connection.commit()
        return True
    except:
        mysql.connection.rollback()
        return False

def login_validate(username, password):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM users WHERE username = %s AND pass_hash = %s''', 
                (username, hash_password(password, username)))
    return int(cur.fetchone()[0]) > 0
    
def create_post(user_id, body, tags):
    now = datetime.datetime.now()

    cur = mysql.connection.cursor()

    try:
        cur.execute(
            '''INSERT INTO `posts`(`post_id`, `user_id`, `body`, `tags`, `date_posted`, `date_edited`, `amount_edits`) 
                VALUES (NULL, %s, %s, %s, %s, %s, %s)''',
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
            '''INSERT INTO `comments`(`comment_id`, `user_id`, `post_id`, `body`, `date_posted`) 
                VALUES (NULL, %s, %s, %s, %s)''',
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

def get_api_token_permissions(token):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT client_permissions FROM api_tokens WHERE token = %s''', (token,))

    result = cur.fetchone()[0]
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
