from flask import Flask, request, Response, session
from flask_mysqldb import MySQL
from lib import *

import hashlib
import json
import importlib

@app.route("/api/user/<int:user_id>", methods=["GET", "DELETE"])
def api_user_user_id(user_id):
    if request.method == "DELETE": 
        succ, info = authenticate_delete(request.args, user_id, ["du"])
        if not succ:
            return return_simple("failure", info)

        succ, info = user_id_exists(user_id)
        if not succ:
            return return_simple("failure", info)

        succ, info = delete_user(user_id)
        if not succ:
            return return_simple("success", info)
        else:
            return return_simple("failure", info)

    if request.method == "GET":
        succ, info = get_user(user_id)
        if not succ:
            return return_simple("failure", info)

        return return_json("success", "User got successfully", "user", info)

@app.route("/api/user", methods=["POST"])
def api_user():
    if request.method == "POST":
        if ("username" not in request.args or 
            "email" not in request.args or
            "password" not in request.args):
            return return_simple("failure", lang["arg_not_given"])

        username    = request.args["username"]
        email       = request.args["email"]
        password    = request.args["password"]

        succ, info = create_user(username, email, password, DEFAULT_PERMS)
        if succ:
            return return_simple("success", info)
        else:
            return return_simple("failure", info)

@app.route("/api/post/<int:post_id>", methods=["GET", "DELETE"])
def api_post_post_id(post_id):
    if request.method == "DELETE":
        succ, info = get_post(post_id)
        if not succ:
            return return_simple("failure", info)
        post_owner = int(info["user_id"])
        
        succ, info = authenticate_delete(request.args, post_owner, ["dp"])
        if not succ:
            return return_simple("failure", info)

        succ, info = delete_post(post_id)
        if not succ:
            return return_simple("success", info)
        else:
            return return_simple("failure", info)
    if request.method == "GET":
        succ, info = get_post(post_id)
        if not succ:
            return return_simple("failure", info)

        return return_json("success", "Post got successfully", "post", info)

@app.route("/api/post", methods=["POST"])
def api_post():
    if request.method == "POST":
        succ, info = authenticate(request.args, ["cp"])
        if not succ:
            return return_simple("failure", info)

        user_id = user_id_from_token(request.args["api_token"])
        body = request.args["body"]
        tags = request.args["tags"]

        succ, info = create_post(user_id, body, tags)
        if succ:
            return return_simple("success", info)
        else:
            return return_simple("failure", info)

@app.route("/api/comment/<int:comment_id>", methods=["DELETE", "GET"])
def api_comment_comment_id(comment_id):
    if request.method == "DELETE":
        succ, info = get_comment(comment_id)
        if not succ:
            return return_simple("failure", info)
        comment_owner = int(info["user_id"])
        
        succ, info = authenticate_delete(request.args, comment_owner, ["dc"])
        if not succ:
            return return_simple("failure", info)

        succ, info = delete_comment(comment_id)
        if not succ:
            return return_simple("success", info)
        else:
            return return_simple("failure", info)

    if request.method == "GET":
        succ, info = get_comment(comment_id)
        if not succ:
            return return_simple("failure", info)

        return return_json("success", "Comment successfully got", "comment", info)

@app.route("/api/comment", methods=["POST", "GET"])
def api_comment():
    if request.method == "POST":
        succ, info = authenticate(request.args, ["cc"])
        if not succ:
            return return_simple("failure", info)

        user_id = user_id_from_token(request.args["api_token"])

        post_id = request.args["post_id"]
        body    = request.args["body"]

        succ, info = create_comment(user_id, post_id, body)
        if succ:
            return return_simple("success", info)
        else:
            return return_simple("failure", info)

@app.route("/api/friend/<int:receiver_id>", methods=["POST", "DELETE"])
def api_friend(receiver_id):
    if request.method == "POST":
        if not authenticate(request.args, ["af"]):
            return return_simple("failure", "Failed to authenticate")

        sender_id = user_id_from_token(request.args["api_token"])

        success, info = send_friend_request(sender_id, receiver_id)

        if success:
            return return_simple("success", info)
        else:
            return return_simple("failure", info)
    if request.method == "DELETE":
        # remove friend
        succ, info = authenticate(request.args, ["uf"])
        if not succ:
            return return_simple("failure", info)

        sender_id = user_id_from_token(request.args["api_token"])

        succ, info = unfriend(sender_id, receiver_id)

        if succ:
            return return_simple("success", info)
        else:
            return return_simple("failure", info)

@app.route("/api/friend/request_revoke/<int:receiver_id>", methods=["POST"])
def api_friend_request_revoke(receiver_id):
    succ, info = authenticate(request.args, ["rf"])
    if not succ:
        return return_simple("failure", info)

    sender_id = user_id_from_token(request.args["api_token"])

    succ, info = revoke_friend_request(sender_id, receiver_id)

    if succ:
        return return_simple("success", info)
    else:
        return return_simple("failure", info)

@app.route("/api/users", methods=["GET"])
def api_users():
    succ, info = get_all_users()
    if not succ:
        return return_simple("failure", info)

    return return_json("success", "Users returned successfully", "users", info)

@app.route("/api/posts", methods=["GET"])
def api_posts():
    since_year = None
    skip = 0
    limit = 30

    if "since" in request.args:
        try:
            since_year = datetime.datetime.strptime(request.args["since"], "%Y-%M-%d")
        except:
            return return_simple("failure", lang["arg_not_given"])

    if "skip" in request.args:
        try:
            skip = int(request.args["skip"])
        except:
            return return_simple("failure", lang["arg_not_given"])

    if "limit" in request.args:
        try:
            limit = int(request.args["limit"])
        except:
            return return_simple("failure", lang["arg_not_given"])

    succ, info = get_conditional_posts(since_year, skip, limit)
    if not succ:
        return return_failure("failure", info)

    return return_json("success", "Posts returned Successfully", "posts", info)

@app.route("/api/comments", methods=["GET"])
def api_comments():
    succ, info = get_all_comments()
    if not succ:
        return return_failure("failure", info)

    return return_json("success", "Comments returned successfully", "comments", info)

@app.route("/api/login", methods=["POST"])
def api_login():
    if "username" not in request.args or "password" not in request.args:
        return return_simple("failure", "Required arguments were not all given")

    username = request.args["username"]
    password = request.args["password"]

    if login_validate(username, password):
        ret, token = new_api_token(userid_from_username(username), "*")
        if ret:
            return return_json("success", "Successfully authenticated", "info", {"token" : token})
            #return Response(json.dumps({"status" : "success", "token" : token}),
            #        mimetype="application/json")
        else:
            return return_simple("failure", token)
    else:
        return return_simple("failure", lang["invalid_creds"])

@app.route("/")
def api_main():
    return "Molurus"
