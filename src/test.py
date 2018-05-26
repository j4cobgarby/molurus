import requests
import MySQLdb
from getpass import getpass
import unittest

users = []

def empty_testdb(commands="testdb_empty.sql"):
    con = MySQLdb.connect(host="localhost", user="root", 
        passwd=getpass("Database password: "), db="molurus_test")
    cur = con.cursor()

    cmds_file = open(commands, "r")
    cmds = cmds_file.readlines()
    cmds = [s[:len(s)-1] for s in cmds]
    cmds_file.close()

    print("| Resetting database.")
    for cmd in cmds:
        print("|> EXECUTING {}".format(cmd))
        try:
            cur.execute(cmd)
            con.commit()
        except:
            print("SQL error")
            con.rollback()

    print("| Reset.")

def req_successful(req_func, url, http_params):
    r = req_func(url, params=http_params)
    ret = r.json()

    if "status" not in ret:
        return False

    if ret["status"] != "success":
        return False

    return True

def get_successful(url, http_params={}):
    return req_successful(requests.get, url, http_params)
    
def post_successful(url, http_params={}):
    return req_successful(requests.post, url, http_params)

def delete_successful(url, http_params={}):
    return req_successful(requests.delete, url, http_params)

class TestApiUsers(unittest.TestCase):
    # Test creating users
    def test_create_users(self):
        users.append({"username": "user1", "email": "blah@blahmail.co", "password": "7654321"})
        users.append({"username": "user2", "email": "foo@bar.baz", "password": "deadbeef"})
        users.append({"username": "user3", "email": "user3@some.email", "password": "cool"})

        for user in users:
            self.assertTrue(post_successful("http://localhost:5000/api/user", user))

    # Test getting all users
    def test_get_users(self):
        self.assertTrue(get_successful("http://localhost:5000/api/users"))

    # Test getting a specific user
    def test_get_user(self):
        for i in range(1, len(users)+1):
            self.assertTrue(get_successful("http://localhost:5000/api/user/{}".format(i)))

    # Test that logging in works
    def test_login(self):
        for index, user in enumerate(users):
            r = requests.post("http://localhost:5000/api/login", params={"username":user["username"], "password":user["password"]})
            ret = r.json()
            self.assertTrue("status" in ret)
            self.assertTrue(ret["status"] == "success")
            users[index]["api_token"] = ret["info"]["token"]

    # Test that a newly generated api token is different to the old one
    def test_newlogin(self):
        for index, user in enumerate(users):
            r = requests.post("http://localhost:5000/api/login", params={"username":user["username"], "password":user["password"]})
            ret = r.json()
            self.assertTrue("status" in ret)
            self.assertTrue(ret["status"] == "success")
            self.assertFalse(ret["info"]["token"] == user["api_token"])
            users[index]["api_token"] = ret["info"]["token"]

if __name__ == "__main__":
    empty_testdb()
    unittest.main()
