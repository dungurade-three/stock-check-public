# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup as bs
import requests
import json
import sys
from datetime import datetime
from secret_utils import get_owner_user_id, get_uuid_map, get_rest_api_key, read_token_info, write_token_info


def get_token(auth_code, redirect_uri):
    host = 'kauth.kakao.com'
    path = '/oauth/token'
    headers = {
        'Content-type': 'application/x-www-form-urlencoded;charset=utf-8'
    }
    url = 'https://{host}{path}'.format(host=host, path=path)
    payload_template = 'grant_type=authorization_code&' + \
                       'client_id={}&' + \
                       'redirect_uri={}&'.format(redirect_uri) + \
                       'code={}'

    rest_api_key = get_rest_api_key()
    payload = payload_template.format(rest_api_key, auth_code)
    print(payload)
    r = requests.post(url=url, headers=headers, data=payload)
    r_json = r.json()
    print(r_json)
    access_token =r_json.get('access_token')
    refresh_token = r_json.get('refresh_token')

    token_info = get_token_info(access_token)
    user_id = token_info.get('id')
    write_token_info(access_token, refresh_token, user_id)


def renew_token(refresh_token):
    host = 'kauth.kakao.com'
    path = '/oauth/token'
    url = 'https://{host}{path}'.format(host=host, path=path)
    headers = {
        'Content-Type': "application/x-www-form-urlencoded;charset=utf-8",
    }
    rest_api_key = get_rest_api_key()
    payload = {
        "grant_type": "refresh_token",
        "client_id": rest_api_key,
        "refresh_token": refresh_token,
    }
    r = requests.post(url, headers=headers, data=payload)
    
    if r.status_code == 200:
        r_json = r.json()
        print(r_json)
        access_token =r_json.get('access_token')
        token_info = get_token_info(access_token)
        user_id = token_info.get('id')
        write_token_info(access_token, refresh_token, user_id)


def get_token_info(access_token):
    host = 'kapi.kakao.com'
    path = '/v1/user/access_token_info'
    url = 'https://{host}{path}'.format(host=host, path=path)
    headers = {
        'Authorization': 'Bearer {}'.format(access_token),
        'Content-Type': "application/x-www-form-urlencoded;charset=utf-8",
    }
    
    r = requests.get(url, headers=headers)
    r_json = r.json()
    print(r_json)
    return r_json


def send_talk_msg(msg, web_url, mobile_web_url, receiver):
    host = 'kapi.kakao.com'
    path = '/v1/api/talk/friends/message/default/send'
    url = 'https://{host}{path}'.format(host=host, path=path)
    owner_user_id = get_owner_user_id()
    token_info = read_token_info(owner_user_id)
    access_token = token_info.get('access_token')
    refresh_token = token_info.get('refresh_token')
    print(access_token, refresh_token)
    headers = {
        'Authorization': 'Bearer {}'.format(access_token),
        'Content-Type': "application/x-www-form-urlencoded",
    }
    template_object = {
        "object_type": "text",
        "text": msg,
        "link": {
            "web_url": web_url,
            "mobile_web_url": mobile_web_url
        },
        "button_title": "이동"
    }
    uuid_map = get_uuid_map()
    payload = {
        "template_object": str(json.dumps(template_object)),
        "receiver_uuids": "[\"{}\"]".format(uuid_map[receiver])
    }
    r = requests.post(url, headers=headers, data=payload)
    if r.status_code != 200:
        print(r.text)
        renew_token(refresh_token)


def send_talk_msg_to_me(msg, web_url, mobile_web_url):
    host = 'kapi.kakao.com'
    path = '/v2/api/talk/memo/default/send'
    url = 'https://{host}{path}'.format(host=host, path=path)
    owner_user_id = get_owner_user_id()
    token_info = read_token_info(owner_user_id)
    access_token = token_info.get('access_token')
    refresh_token = token_info.get('refresh_token')
    print(access_token, refresh_token)
    headers = {
        'Authorization': 'Bearer {}'.format(access_token),
        'Content-Type': "application/x-www-form-urlencoded",
    }
    template_object = {
        "object_type": "text",
        "text": msg,
        "link": {
            "web_url": web_url,
            "mobile_web_url": mobile_web_url
        },
        "button_title": "이동"
    }
    payload = {
        "template_object": str(json.dumps(template_object)),
    }
    r = requests.post(url, headers=headers, data=payload)
    if r.status_code != 200:
        print(r.text)
        renew_token(refresh_token)


def write_text(text, p):
    with open(p, 'w') as f:
        f.write(text)


def get_current_datetime():
    now = datetime.now()
    return now.strftime("%Y-%m-%d-%H:%M:%S")
