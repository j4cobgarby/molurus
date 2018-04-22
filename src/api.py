from flask import Flask, request, Response, session
from flask_mysqldb import MySQL
from lib import *

import hashlib
import json
import importlib

app = Flask(__name__)
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "Jacobg01"
app.config["MYSQL_DB"] = "molurus"

app.secret_key = "really cool secret key"

mysql = MySQL(app)

'''
API documentation

PUT /api/user
    Creates a user. The following arguments must be given:

     username:      The username of the user
     email:         The email of the user
     password:      The password (non-hashed - the api hashes it)
     permissions:   The permissions, a comma seperated list of any amount of these:

                        *:      Equivalent to a list of every other permission

                        cp:     Can create a post
                        ep:     Can edit any post
                        dp:     Can delete any post

                        cc:     Can comment on posts
                        ec:     Can edit any comment
                        dc:     Can delete any comment

PUT /api/post
    Creates a new post. The logged-in user is taken from the session cookie. Arguments:

     body:          The text content of the post. Max 2500 characters.
     tags:          Comma seperated tags, e.g. "foo,bar,baz"

GET /api/posts
    Returns a json of all the posts. Look at the json yourself to see how it works.
'''

def user_id_exists(id):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM users WHERE user_id = %s''', (id,))
    return int(cur.fetchone()[0]) > 0

def username_exists(username):
    cur = mysql.connection.cursor()
    cur.execute('''SELECT COUNT(*) FROM users WHERE username = %s''', (username,))
    return int(cur.fetchone()[0]) > 0

@app.route("/api/user", methods=["PUT"])
def new_user():
    username =    request.args["username"]
    email    =    request.args["email"]
    password =    request.args["password"]
    permissions = request.args["permissions"]

    if (username is None or email is None or password is None or permissions is None):
        return return_simple("failure", "Required arguments were not all given.")

    if create_user(username, email, password, permissions):
        return return_simple("success", "Inserted new user.")
    else:
        return return_simple("failure", "Failed to insert new user.")

@app.route("/api/login", methods=["POST"])
def api_login():
    username = request.args["username"]
    password = request.args["password"]

    logged_in = False

    if (username is None or password is None):
        return return_simple("failure", "Required arguments were not all given.")

    if login_validate(username, password):
        cur = mysql.connection.cursor()
        cur.execute('''SELECT user_id FROM users WHERE username = %s''', (username,))
        user_id = int(str(cur.fetchone()[0]))
        

@app.route("/")
def main():
    cur = mysql.connection.cursor()
    cur.execute('''SELECT user_id FROM users WHERE username = %s''', ("j4cobgarby",))
    return str(cur.fetchone()[0])

@app.route("/set")
def set_session():
    param = request.args["to"]
    session["s"] = param
    session.modified = True
    return return_simple("success", "Updated session")

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
    try:
        auth_token = session["auth_token"]
    except KeyError:
        return return_simple("failure", "Authentication token not set. No post was created.")

    cur = mysql.connection.cursor()
