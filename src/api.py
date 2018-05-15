from flask import Flask, request, Response, session
from flask_mysqldb import MySQL
from lib import *

import hashlib
import json
import importlib

@app.route("/api/user/<int:user_id>", methods=["GET", "DELETE"])
def api_user_user_id(user_id):
    if request.method == "DELETE": 
        if not authenticate_delete(request.args, user_id, ["du"]):
            return return_simple("failure", "Failed to authenticate the user")

        if not user_id_exists(user_id):
            return return_simple("failure", "Failed to delete user because the user doesn't exist.")

        if delete_user(user_id):
            return return_simple("success", "Successfully deleted user.")
        else:
            return return_simple("failure", "Failed to delete user.")

    if request.method == "GET":
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

@app.route("/api/user", methods=["POST"])
def api_user():
    if request.method == "POST":
        if ("username" not in request.args or 
            "email" not in request.args or
            "password" not in request.args):
            return return_simple("failure", "Required arguments were not all given.")

        username    = request.args["username"]
        email       = request.args["email"]
        password    = request.args["password"]

        if create_user(username, email, password, DEFAULT_PERMS):
            return return_simple("success", "Inserted new user.")
        else:
            return return_simple("failure", "Failed to insert new user.")

@app.route("/api/post/<int:post_id>", methods=["GET", "DELETE"])
def api_post_post_id(post_id):
    if request.method == "DELETE":
        if not post_id_exists(post_id):
            return return_simple("failure", "This post doesn't exist, actually.")

        post_owner = int(get_post(post_id)["user_id"])
        
        if not authenticate_delete(request.args, post_owner, ["dp"]):
            return return_simple("failure", "Failed to authenticate")

        if delete_post(post_id):
            return return_simple("success", "Successfully deleted post.")
        else:
            return return_simple("failure", "Failed to delete post.")
    if request.method == "GET":
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

@app.route("/api/post", methods=["POST"])
def api_post():
    if request.method == "POST":
        if not authenticate(request.args, ["cp"]):
            return return_simple("failure", "Failed to authenticate user")

        user_id = user_id_from_token(request.args["api_token"])
        body = request.args["body"]
        tags = request.args["tags"]

        if create_post(user_id, body, tags):
            return return_simple("success", "Inserted new post.")
        else:
            return return_simple("failure", "Failed to create post.")

@app.route("/api/comment/<int:comment_id>", methods=["DELETE", "POST"])
def api_comment_comment_id(comment_id):
    if request.method == "DELETE":
        if not comment_id_exists(comment_id):
            return return_simple("failure", "This comment doesn't exist.")

        comment_owner = int(get_comment(comment_id)["user_id"])
        
        if not authenticate_delete(request.args, comment_owner, ["dc"]):
            return return_simple("failure", "Failed to authenticate")

        if delete_comment(comment_id):
            return return_simple("success", "Comment successfully deleted.")
        else:
            return return_simple("failure", "Failed to delete the post.")

@app.route("/api/comment", methods=["POST", "DELETE", "GET"])
def api_comment():
    if request.method == "POST":
        if not authenticate(request.args, ["cc"]):
            return return_simple("failure", "Failed to authenticate")

        user_id = user_id_from_token(request.args["api_token"])

        post_id = request.args["post_id"]
        body    = request.args["body"]

        if create_comment(user_id, post_id, body):
            return return_simple("success", "Successfully created comment.")
        else:
            return return_simple("failure", "Failed to create comment.")

    if request.method == "GET":
        if "comment_id" not in request.args:
            return return_simple("failure", "Required arguments were not all given")

        comment_id = int(request.args["comment_id"])

        if not comment_id_exists(comment_id):
            return return_simple("failure", "This comment does not exist.")

        return_format = "json"

        if "format" in request.args:
            return_format = request.args["format"]

        if return_format not in ["json", "python"]:
            return_format = "json"

        ret = get_comment(comment_id)

        if return_format == "python":
            return str(ret)

        return Response(json.dumps(ret), mimetype="application/json")

@app.route("/api/friend/request/<int:receiver_id>", methods=["POST"])
def api_friend_request(receiver_id):
    if not authenticate(request.args, ["af"]):
        return return_simple("failure", "Failed to authenticate")

    sender_id = user_id_from_token(request.args["api_token"])

    success, info = send_friend_request(sender_id, receiver_id)

    if success:
        return return_simple("success", info)
    else:
        return return_simple("failure", info)

@app.route("/api/friend/request/revoke/<int:receiver_id>", methods=["POST"])
def api_friend_request_revoke(receiver_id):
    if not authenticate(request.args, ["rf"]):
        return return_simple("failure", "Failed to authenticate")

    sender_id = user_id_from_token(request.args["api_token"])

    success, info = revoke_friend_request(sender_id, receiver_id)

    if success:
        return return_simple("success", info)
    else:
        return return_simple("failure", info)

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
    return_format = "json"

    if "format" in request.args:
        return_format = request.args["format"]

    if return_format not in ["json", "python"]:
        return_format = "json"

    ret = get_all_comments()

    if return_format == "python":
        return str(ret)

    return Response(json.dumps(ret), mimetype="application/json")

@app.route("/api/login", methods=["POST"])
def api_login():
    if "username" not in request.args or "password" not in request.args:
        return return_simple("failure", "Required arguments were not all given")

    username = request.args["username"]
    password = request.args["password"]

    if login_validate(username, password):
        ret, token = new_api_token(userid_from_username(username), "*")
        if ret:
            return Response(json.dumps({"success" : "Validated user.", "token" : token}),
                    mimetype="application/json")
        else:
            return return_simple("failure", "Failed to create api token.")
    else:
        return return_simple("failure", "Incorrect creds.")

@app.route("/")
def api_main():
    return "Molurus"
