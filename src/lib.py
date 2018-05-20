from flask import Flask, request, Response
from flask_mysqldb import MySQL
import hashlib
import json
import datetime
import secrets
import api_localization as loc

PERMS = [
        "cp", "ep", "dp", # Post (create/edit/delete)
        "cc", "ec", "dc", # Comment (create/edit/delete)
        "bu", "du", # User (ban/delete)
        "af", "rf", "uf", # Friends (add/revoke request/unfriend)
        "ss", # colour Scheme (set)
        ]

DEFAULT_PERMS = [
        "cp,cc,af,rf,uf,ss"
        ]

lang = loc.langs["gb"]

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

def create_test_database(name="molurus_test"):
    cur = mysql.connection.cursor()
    cur.execute('''CREATE DATABASE %s''', (name,))
    print("Database created: {}".format(name))

# True if user exists else false
def user_id_exists(user_id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM users WHERE user_id = %s''', (user_id,))
    return int(cur.fetchone()[0]) > 0

# True if a user has the given username else false
def username_exists(username):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM users WHERE username = %s''', (username,))
    return int(cur.fetchone()[0]) > 0

# True if an api token exists else false
def token_exists(token):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM api_tokens WHERE token = %s''', (token,))
    return int(cur.fetchone()[0]) > 0

# True if user has already generated a token
def user_id_has_token(user_id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM api_tokens WHERE user_id = %s''', (user_id,))
    return int(cur.fetchone()[0]) > 0

# Retrieve the user id from an api token
def user_id_from_token(token):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT user_id FROM api_tokens WHERE token = %s''', (token,))
    return int(cur.fetchone()[0])

# Gets the api token from http args, and returns the user id of the token
def user_id_from_request_args(args):
    if "api_token" not in args:
        return False, lang["arg_not_given"]

    tok = args["api_token"]

    if not token_exists(tok):
        return False, lang["tok_noexist"]

    user_id = user_id_from_token(tok)

    if not user_id_exists(user_id):
        return False, lang["user_id_noexist"]

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
    user_id, info = user_id_from_request_args(args)

    if not user_id:
        return False, info

    user_perms = get_user_permissions(user_id)
    client_perms = get_api_token_permissions(args["api_token"])

    if len(perms) == 0:
        return True, lang["authenticated"]

    for perm in perms:
        if perm not in user_perms or perm not in client_perms:
            return False, lang["insufficient_perms"]

    return True, lang["authenticated"]

# almost identical to authenticate(...), except you don't
# need the permission to delete the component if you're the
# owner of it
def authenticate_delete(args, component_owner, perms):
    user_id, info = user_id_from_request_args(args)

    if not user_id:
        return False, info

    user_perms = get_user_permissions(user_id)
    client_perms = get_api_token_permissions(args["api_token"])

    if len(perms) == 0 or user_id == component_owner:
        return True, lang["authenticated"]

    for perm in perms:
        if perm not in user_perms or perm not in client_perms:
            return False, lang["insufficient_perms"]

    return True, lang["authenticated"]

# remove an api token (e.g. for logging out)
def delete_user_id_token(user_id):
    if not user_id_has_token(user_id):
        return

    cur = mysql.connection.cursor()

    try:
        cur.execute('''DELETE FROM api_tokens WHERE user_id = %s''', (user_id,))
        mysql.connection.commit()
        return True, lang["tok_deleted"]
    except:
        mysql.connection.rollback()
        return False, lang["database_failure"]

# Generate a new api token for a user
def new_api_token(user_id, permissions):
    if not user_id_exists(user_id):
        return False, lang["user_id_noexist"]

    if user_id_has_token(user_id): # this user already has a token.
        delete_user_id_token(user_id)

    tok = secrets.token_hex(64)

    while (token_exists(tok)): # make sure to get a unique token
        tok = secrets.token_hex(64)

    cur = mysql.connection.cursor()
    try:
        cur.execute('''INSERT INTO `api_tokens`(`token_id`, `token`, `user_id`, `client_permissions`) 
                        VALUES (NULL, %s, %s, %s)''',
                (tok, user_id, permissions))
        mysql.connection.commit()
        return True, tok
    except:
        mysql.connection.rollback()
        return False, lang["database_failure"]

# Check if a post exists with this id
def post_id_exists(post_id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM posts WHERE post_id = %s''', (post_id,))
    return int(cur.fetchone()[0]) > 0

# Check if a comment with this id exists
def comment_id_exists(comment_id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM comments WHERE comment_id = %s''', (comment_id,))
    return int(cur.fetchone()[0]) > 0

# Check if sender_id has sent a friend request to receiver_id
def friend_request_exists(sender_id, receiver_id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM friend_requests WHERE sender_id = %s AND receiver_id = %s''',
            (sender_id, receiver_id))
    return int(cur.fetchone()[0]) > 0

def are_friends(friend_1, friend_2):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM friends WHERE (user_id_1 = %s AND user_id_2 = %s) OR (user_id_1 = %s AND user_id_2 = %s)''',
            (friend_1, friend_2, friend_2, friend_1))
    return int(cur.fetchone()[0]) > 0

def username_from_userid(user_id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT username FROM users WHERE user_id = %s''', (user_id,))
    return cur.fetchone()[0]

def userid_from_username(username):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT user_id FROM users WHERE username = %s''', (username,))
    return int(cur.fetchone()[0])

# returns a json response object with a status and info, useful for quick
# and nice returns from api calls
def return_simple(status, info):
    json_string = json.dumps({"status" : status, "info" : info})
    return Response(json_string, mimetype="application/json")

# returns the hash of a password + the salt
# the salt should be the username
def hash_password(password, salt):
    pass_bytes = str.encode(salt + password)
    pass_hash = hashlib.sha512(pass_bytes).hexdigest()
    return pass_hash

def unfriend(friend_1, friend_2):
    if not are_friends(friend_1, friend_2):
        return False, lang["not_friends"]

    cur = mysql.connection.cursor()
    try:
        cur.execute('''DELETE FROM friends WHERE (user_id_1 = %s AND user_id_2 = %s) OR (user_id_1 = %s AND user_id_2 = %s)''',
                (friend_1, friend_2, friend_2, friend_1))
        mysql.connection.commit()
        return True, lang["unfriended"]
    except:
        mysql.connection.rollback()
        return False, lang["database_failure"]

# befriends two users
def create_friendship(friend_1, friend_2):
    if are_friends(friend_1, friend_2):
        return False, lang["already_friends"]

    cur = mysql.connection.cursor()

    try:
        cur.execute(
                '''INSERT INTO `friends`(`friendship_id`, `user_id_1`, `user_id_2`, `friendship_strength`) 
                    VALUES (NULL, %s, %s, 0)''',
                    (int(friend_1), int(friend_2))
                )
        mysql.connection.commit()

        # Make sure to delete any relevant friend requests
        delete_friend_request(friend_1, friend_2)
        delete_friend_request(friend_2, friend_1)

        return True, lang["friended"]
    except:
        mysql.connection.rollback()
        return False, lang["database_failure"]

# if sender_id has previously sent a friend request to receiver_id, this function undoes that
def revoke_friend_request(sender_id, receiver_id):
    if not friend_request_exists(sender_id, receiver_id):
        return False, lang["friend_request_noexist"]

    cur = mysql.connection.cursor()
    try:
        cur.execute(
                '''DELETE FROM friend_requests WHERE sender_id = %s AND receiver_id = %s''',
                (sender_id, receiver_id)
                )
        mysql.connection.commit()
        return True, lang["friend_request_revoked"]
    except:
        mysql.connection.rollback()
        return False, lang["database_failure"]

# this is obvious what it does but i don't want to write nothing about it because it's a really
# long function
def send_friend_request(sender_id, receiver_id):
    if friend_request_exists(receiver_id, sender_id):
        # The would-be receiver already has asked the sender to be
        # his friend
        success, info = create_friendship(sender_id, receiver_id)
        if success:
            return True, lang["friended"]
        else:
            return False, info

    if friend_request_exists(sender_id, receiver_id):
        return False, lang["friend_request_exists"]

    cur = mysql.connection.cursor()
    try:
        cur.execute(
                '''INSERT INTO `friend_requests`(`request_id`, `sender_id`, `receiver_id`)
                    VALUES (NULL, %s, %s)''',
                    (sender_id, receiver_id)
                )
        mysql.connection.commit()
        return True, lang["friend_requested"]
    except:
        mysql.connection.rollback()
        return False, lang["database_failure"]

# permissions should be a comma seperated string of permissions, as documented
# in docs.txt and in a list at the top of this file. for normal users, DEFAULT_PERMS
# should be used.
def create_user(username, email, password, permissions):
    if username_exists(username):
        return False, lang["username_exists"]

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
        return True, lang["user_created"]
    except:
        mysql.connection.rollback()
        return False, lang["database_failure"]

# verify that the username/password combination supplied is valid and correct
def login_validate(username, password):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM users WHERE username = %s AND pass_hash = %s''', 
                (username, hash_password(password, username)))
    return int(cur.fetchone()[0]) > 0

# tags should be a comma-seperated string of whatever, really
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
        return True, lang["post_created"]
    except:
        mysql.connection.rollback()
        return False, lang["database_failure"]

# body is the text of the comment
# post_id is the post which this is commenting on
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
        return True, lang["comment_created"]
    except:
        mysql.connection.rollback()
        return False, lang["database_failure"]

# returns a dictionary of all the posts
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

def get_conditional_posts(since=None, skip=0, limit=30):
    cur = mysql.connection.cursor()

    if since:
        cur.execute('''SELECT * FROM posts WHERE date_posted > %s LIMIT %s OFFSET %s''',
                (since, limit, skip))
    else:
        cur.execute('''SELECT * FROM posts LIMIT %s OFFSET %s''',
                (limit, skip))

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

# returns a dictionary of all users
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

# dictionary of all comments on a specific post
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
            "date_posted" : result[4].strftime("%Y-%M-%d")
            })

    return ret

# returns permissions as an array of strings
def get_user_permissions(user_id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT permissions FROM users WHERE user_id = %s''', (user_id,))
    
    result = cur.fetchone()[0]
    print(result)

    if result == '*':
        return PERMS

    return result.split(",")

# permissions of api token as array of strings
def get_api_token_permissions(token):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT client_permissions FROM api_tokens WHERE token = %s''', (token,))

    result = cur.fetchone()[0]
    if result == '*':
        return PERMS

    return result.split(",")

# completely remove a user from the database
# TODO: when profile pictures and uploaded assets are a thing, this should remove those
#       too.
def delete_user(user_id):
    cur = mysql.connection.cursor()
   
    try:
        cur.execute('''DELETE FROM users WHERE user_id = %s''', (user_id,))
        mysql.connection.commit()
        return True, lang["user_deleted"]
    except:
        print("SQL Error")
        mysql.connection.rollback()
        return False, lang["database_failure"]

# returns a dict of info about a user with the id
def get_user(user_id):
    if not user_id_exists(user_id):
        return False, lang["user_id_noexist"]

    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM users WHERE user_id = %s''', (user_id,))
    user = cur.fetchone()

    return {"user_id" : user[0], "username" : user[1]}

def delete_post(post_id):
    if not post_id_exists(post_id):
        return False, lang["post_noexist"]

    cur = mysql.connection.cursor()

    try:
        cur.execute('''DELETE FROM posts WHERE post_id = %s''', (post_id,))
        mysql.connection.commit()
        return True, lang["post_deleted"]
    except:
        print("SQL Error")
        mysql.connection.rollback()
        return False, lang["database_failure"]

# returns a dict of info about a post
def get_post(post_id):
    if not post_id_exists(post_id):
        return False, lang["post_noexist"]

    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM posts WHERE post_id = %s''', (post_id,))
    post = cur.fetchone()

    return {"post_id" : post[0], "user_id" : post[1], "body" : post[2], 
            "tags" : post[3], "date_posted" : str(post[4]), "date_edited" : str(post[5]), "amount_edits" : post[6]}

def delete_comment(comment_id):
    if not comment_id_exists(comment_id):
        return False, lang["comment_noexist"]

    cur = mysql.connection.cursor()

    try:
        cur.execute('''DELETE FROM comments WHERE comment_id = %s''', (comment_id,))
        mysql.connection.commit()
        return True, lang["comment_deleted"]
    except:
        mysql.connection.rollback()
        return False, lang["database_failure"]

# returns a dict of info about a comment
def get_comment(comment_id):
    if not comment_id_exists(comment_id):
        return False, lang["comment_noexist"]

    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM comments WHERE comment_id = %s''', (comment_id,))
    com = cur.fetchone()

    return {"comment_id" : com[0], "user_id" : com[1], "post_id" : com[2], "body" : com[3], "date_posted" : str(com[4])}
