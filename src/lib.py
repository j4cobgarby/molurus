from flask import Flask, request, Response
from flask_mysqldb import MySQL
import hashlib
import json

def return_simple(status, info):
    json_string = json.dumps({"status" : status, "info" : info})
    return Response(json_string, mimetype="application/json")

def hash_password(password, salt):
    pass_bytes = str.encode(salt + password)
    pass_hash = hashlib.sha512(pass_bytes).hexdigest()

def create_user(db, username, email, password, permissions):
    print("Creating user {}".format(username))

    pass_hash = hash_password(password, username) 
    
    # Insert the new user into the database
    cur = db.connection.cursor()

    try:
        cur.execute(
            '''INSERT INTO `users`(`user_id`, `username`, `email_address`, `pass_hash`, `permissions`, `preferred_colour_scheme`) 
                VALUES (NULL, %s, %s, %s, %s, %s)''',
                (username, email, pass_hash, permissions, 1))
        db.connection.commit()
        return True
    except:
        print("SQL Error.")
        db.connection.rollback()
        return False

def login_validate(db, username, password):
    cur = db.connection.cursor()

    cur.execute('''SELECT COUNT(*) FROM users WHERE username = %s AND pass_hash = %s''', (username, hash_password(password, username)))
    return int(cur.fetchone()[0]) > 0
    

def create_post(db, user_id, body, tags):
    try:
        auth_token = session["auth_token"]
    except KeyError:
        return return_simple("failure", "Authentication token not set. No post was created.")

    cur = db.connection.cursor()
