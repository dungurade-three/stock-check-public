# -*- coding: utf-8 -*-
import json
import os.path
from os import path

PROJ_DIR = os.path.realpath(os.path.dirname(__file__) + "/..")


def get_secret(filename):
    data = dict()
    print(PROJ_DIR)
    p = "{}/stock-check-secret/{}.json".format(PROJ_DIR, filename)
    if os.path.isfile(p):
        try:
            with open(p, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print("get_secret load error : {}, ".format(p), e)
    
    return data


def get_owner_user_id():
    return get_secret('app').get('owner_user_id')


def get_rest_api_key():
    return get_secret('app').get('rest_api_key')


def get_uuid_map():
    return get_secret('app').get('uuid_map')


def get_redirect_url_map():
    return get_secret('app').get('redirect_url_map')


def get_product_info():
    return get_secret('app').get('product_info')


def read_token_info(user_id):
    return get_secret('token').get(str(user_id))


def write_token_info(access_token, refresh_token, user_id):
    filename = 'token'
    data = get_secret(filename)
    data[str(user_id)] = {
        'access_token': access_token,
        'refresh_token': refresh_token,
    }
    p = "{}/stock-check-secret/{}.json".format(PROJ_DIR, filename)
    with open(p, 'w+') as f:
        json.dump(data, f)
    f.close()
