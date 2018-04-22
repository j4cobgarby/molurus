from flask import Flask, request, Response, session
from flask_mysqldb import MySQL
from lib import *

import hashlib
import json
import importlib

@app.route("/api/user", methods=["PUT", "DELETE", "GET"])
def api_user():
    if request.method == "PUT":
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

    elif request.method == "DELETE":
        if "user_id" not in request.args:
            return return_simple("failure", "Required arguments were not all given.")

        user_id = int(request.args["user_id"])

        if not is_logged_in():
            return return_simple("failure", "Failed to delete user because you're not logged in.")

        if "du" not in get_user_permissions(int(session["user_id"])) and user_id != int(session["user_id"]):
            return return_simple("failure", "Failed to delete user because of lack of permissions.")

        if not user_id_exists(user_id):
            return return_simple("failure", "Failed to delete user because the user doesn't exist.")

        if delete_user(user_id):
            return return_simple("success", "Successfully deleted user.")
        else:
            return return_simple("failure", "Failed to delete user.")

    else: # GET
        if "user_id" not in request.args:
            return return_simple("failure", "Required arguments were not all given")

        user_id = int(request.args["user_id"])

        if not user_id_exists(user_id):
            return return_simple("failure", "User does not exist.")

        return_format = "json"

        if "format" in request.args:
            return_format = request.args["format"] 

        if return_format not in ["json", "python"]:
            return_format = "json"

        ret = get_user(user_id)
        
        if return_format == "python":
            return str(ret)

        return Response(json.dumps(ret), mimetype="application/json")

@app.route("/api/post", methods=["PUT", "DELETE", "GET"])
def api_post():
    if not is_logged_in():
        return return_simple("failure", "Not logged in as anyone.")

    user_id = int(session["user_id"])

    if not user_id_exists(user_id):
        return return_simple("failure", "User id isn't a real user.")

    body = request.args["body"]
    tags = request.args["tags"]

    if create_post(user_id, body, tags):
        return return_simple("success", "Inserted new post.")
    else:
        return return_simple("failure", "Failed to create post.")

@app.route("/api/comment", methods=["PUT", "DELETE", "GET"])
def api_comment():
    pass

@app.route("/api/users", methods=["GET"])
def api_users():
    pass

@app.route("/api/posts", methods=["GET"])
def api_posts():
    return_format = "json"

    if "format" in request.args:
        return_format = request.args["format"]

    if return_format not in ["json", "python"]:
        return_format = "json"

    ret = get_all_posts()

    if return_format == "python":
        return str(ret)

    return Response(json.dumps(ret), mimetype="application/json")

@app.route("/api/comments", methods=["GET"])
def api_comments():
    pass

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
        session["user_id"] = user_id
        return return_simple("success", "Validated.")
    else:
        return return_simple("failure", "Incorrect creds.")

@app.route("/")
def api_main():
    return "Main"
