import requests
import unittest

def get_successful(url, http_params={}):
    if type(url) is not str or type(http_params) is not dict

    r = requests.get(url, params=http_params)
    ret = r.json()


def post_successful(url, params={}):
    pass

def delete_successful(url, params={}):
    pass

class TestMolurusApi(unittest.TestCase):

