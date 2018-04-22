from flask import Flask, request, Response, session
from flask_mysqldb import MySQL
from lib import *

import hashlib
import json
import importlib

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

POST /api/login
    Sets the users cookies to be logged in, if the credentials are valid. Arguments:
    
     username:  The username to log in as
     password:  The password to log in as
'''

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
        return return_simple("success", "Validated.")
    else:
        return return_simple("failure", "Incorrect creds.")

@app.route("/")
def main():
    cur = mysql.connection.cursor()
    cur.execute('''SELECT * FROM users''')
    return str(cur.fetchall())

# Below this point, everything's just for testing

@app.route("/set")
def set_session():
    param = request.args["to"]
    session["s"] = param
    session.modified = True
    return return_simple("success", "Updated session")
