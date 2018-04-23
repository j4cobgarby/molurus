from flask import Flask, request, Response, session
from flask_mysqldb import MySQL
from lib import *

import hashlib
import json
import importlib

@app.route("/api/user", methods=["PUT", "DELETE", "GET"])
def api_user():
    if request.method == "PUT":
        if ("username" not in request.args or 
            "email" not in request.args or
            "password" not in request.args):
            return return_simple("failure", "Required arguments were not all given.")

        username    = request.args["username"]
        email       = request.args["email"]
        password    = request.args["password"]

        if create_user(username, email, password, "cp,cc"):
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
    if request.method == "PUT":
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
    elif request.method == "DELETE":
        if "post_id" not in request.args:
            return return_simple("failure", "Required arguments were not all given.")

        post_id = int(request.args["post_id"])

        if not is_logged_in():
            return return_simple("failure", "Failed to delete post because you're not logged in.")

        if "dp" not in get_user_permissions(int(session["user_id"])) and user_id != int(session["user_id"]):
            return return_simple("failure", "Lack of permissions to delete this post.")

        if not post_id_exists(post_id):
            return return_simple("failure", "This post doesn't exist, actually.")

        if delete_post(post_id):
            return return_simple("success", "Successfully deleted post.")
        else:
            return return_simple("failure", "Failed to delete post.")
    else: # GET
        if "post_id" not in request.args:
            return return_simple("failure", "Required arguments were not all given.")

        post_id = int(request.args["post_id"])

        if not post_id_exists(post_id):
            return return_simple("failure", "Post does not exist.")

        return_format = "json"

        if "format" in request.args:
            return_format = request.args["format"]

        if return_format not in ["json", "python"]:
            return_format = "json"

        ret = get_post(post_id)

        if return_format == "python":
            return str(ret)

        return Response(json.dumps(ret), mimetype="application/json")

@app.route("/api/comment", methods=["PUT", "DELETE", "GET"])
def api_comment():
    pass

@app.route("/api/users", methods=["GET"])
def api_users():
    return_format = "json"

    if "format" in request.args:
        return_format = request.args["format"]

    if return_format not in ["json", "python"]:
        return_format = "json"

    ret = get_all_users()

    if return_format == "python":
        return str(ret)

    return Response(json.dumps(ret), mimetype="application/json")

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
