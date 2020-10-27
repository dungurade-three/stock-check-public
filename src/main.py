# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup as bs
import requests
import json
import sys
import time
from threading import Thread
from flask import Flask, request, redirect
from utils import get_token, renew_token, send_talk_msg, send_talk_msg_to_me, read_token_info
from secret_utils import get_product_info, get_rest_api_key, get_redirect_url_map, get_owner_user_id

app = Flask(__name__)

HOST_MAP = {
    'dev': '127.0.0.1',
    'prod': '0.0.0.0',
}


def get_stock_status(url, product_name, shop):
    retry_count = 5
    for i in range(retry_count):
        try:
            doc = requests.get(url)
            break
        except requests.exceptions.RequestException as e:
            msg = 'requests error: {}'.format(e)
            print('{}\nretrying...{}({})'.format(msg, i, retry_count))
            if i == retry_count:
                return False, msg
            time.sleep(60)

    doc_text = doc.text
    try:
        soup = bs(doc_text, 'html.parser')
    except Exception as e:
        return False, 'soup parsing error {}'.format(e)

    if shop == '11st':
        # 현재 판매중인 상품이 아닙니다. 구매하기 비활성화 대응
        no_sale_list = list(filter(lambda x: 'class' in x.attrs and x.attrs['class'] == ['no_sale'], soup.find_all('p')))
        if len(no_sale_list) > 0:
            print(no_sale_list)
            stock_info = {
                'status': False,
                'text': no_sale_list[0].string
            }
            return True, stock_info

        optlst_list = list(filter(lambda x: 'class' in x.attrs and x.attrs['class'] == ['optlst'], soup.find_all('ul')))

        if len(optlst_list) > 0:
            options = {
                'data-optnm': product_name
            }

            target_opt = optlst_list[0].find('a', options)
            # stock status check
            if 'data-stckqty' in target_opt.attrs:
                stock_info = {
                    'status': int(target_opt.attrs['data-stckqty']) > 0,
                    'unknown_key': []
                }

                for span_tag in target_opt.find_all('span'):
                    if 'class' in span_tag.attrs:
                        key = span_tag.attrs['class'][0]
                        value = span_tag.string
                        stock_info[key] = value
                    else:
                        value = span_tag.string
                        stock_info['unknown_key'].append(value)

                return True, stock_info
            else:
                return False, 'data-stckqty key error'

        return False, 'optlst error'
    elif shop == 'ssg':
        # 일시품절 상태인지 확인
        option = {
            'class': 'cdtl_disabled cdtl_btn_soldout'
        }
        disabled_tag = soup.find('a', option)
        if disabled_tag:
            stock_info = {
                    'status': False,
                    'text': disabled_tag.string
                }
            print(disabled_tag.string)
            return True, stock_info
        
        # 버튼 활성되었는지 확인
        option = {
            'class': 'cdtl_btn_black cdtl_btn_buy clickable'
        }
        buy_tag = soup.find('a', option)
        if buy_tag:
            stock_info = {
                    'status': True,
                    'text': buy_tag.string
                }
            return True, stock_info

    return False, 'error'


@app.route('/')
def root_test():
    return '^~^'


@app.route("/auth/callback")
def auth_code_callback():
    auth_code = request.args.get('code')
    redirect_url_map = get_redirect_url_map()
    get_token(auth_code, redirect_url_map[ENV])
    return 'done'


@app.route("/auth")
def auth_code():
    url_template = 'https://kauth.kakao.com/oauth/authorize?client_id={}&redirect_uri={}&response_type=code'
    rest_api_key = get_rest_api_key()
    redirect_url_map = get_redirect_url_map()
    url = url_template.format(rest_api_key, redirect_url_map[ENV])
    print(url)
    return redirect(url)


@app.route('/friends')
def get_friends_info():
    owner_user_id = get_owner_user_id()
    token_info = read_token_info(owner_user_id)
    access_token = token_info.get('access_token')
    refresh_token = token_info.get('refresh_token')
    host = 'kapi.kakao.com'
    path = '/v1/api/talk/friends'
    url = 'https://{host}{path}'.format(host=host, path=path)
    headers = {
        'Authorization': 'Bearer {}'.format(access_token),
        'Content-Type': "application/x-www-form-urlencoded",
    }
    r = requests.get(url, headers=headers)
    print(r.text)
    if r.status_code != 200:
        renew_token(refresh_token)
        return 'renewed access_token. please retry again'
    else:
        return r.text


@app.route('/auth/<scope>')
def get_additional_auth(scope):
    url_template = "https://kauth.kakao.com/oauth/authorize?client_id={}&redirect_uri={}&response_type=code&scope={}"
    rest_api_key = get_rest_api_key()
    redirect_url_map = get_redirect_url_map()
    url = url_template.format(rest_api_key, redirect_url_map[ENV], scope)
    return redirect(url)


@app.route('/unlink/<user_id>')
def unlink(user_id):
    token_info = read_token_info(user_id)
    if not token_info:
        return 'invalid user_id'
    
    access_token = token_info.get('access_token')
    refresh_token = token_info.get('refresh_token')

    host = 'kapi.kakao.com'
    path = '/v1/user/unlink'
    url = 'https://{host}{path}'.format(host=host, path=path)
    headers = {
        'Authorization': 'Bearer {}'.format(access_token),
    }
    r = requests.get(url, headers=headers)
    print(r.text)
    if r.status_code != 200:
        renew_token(refresh_token)
        return 'renewed access_token. please retry again'
    else:
        return r.text


def stock_check():
    product_info = get_product_info()
    noti_no_stock = False
    count = 0
    check_status = {
        '11st': True,
        'ssg': True,
    }
    while True:
        # 11번가
        if check_status['11st']:
            result, data = get_stock_status(**product_info['11st'])
            print(data)
            if result:
                if data.get('status'):
                    msg_template = (
                        "11번가 재고있음!!!\n"
                        "{}\n"
                        "{}"
                    )
                    infos = []
                    for key in ['prc', 'deadline']:
                        if data.get(key):
                            infos.append(data.get(key))
                    msg = msg_template.format(product_info['11st']['product_name'],
                                            "\n".join(infos))
                    url = product_info['iphone']['url']
                    send_talk_msg_to_me(msg, url, url)
                    send_talk_msg(msg, url, url, 'suk')
                    check_status['11st'] = False
                else:
                    if noti_no_stock:
                        msg = '11번가 재고없음ㅠㅠ\n{}\n(한시간에 한번만 알림)'.format(data['text'])
                        url = product_info['11st']['url']
                        send_talk_msg_to_me(msg, url, url)
                        send_talk_msg(msg, url, url, 'suk')
            else:
                msg = '에러발생 {}'.format(data)
                url = product_info['11st']['url']
                send_talk_msg_to_me(msg, url, url)
                return
        # ssg
        if check_status['ssg']:
            result, data = get_stock_status(**product_info['ssg'])
            print(data)
            if result:
                if data.get('status'):
                    msg_template = (
                        "SSG 재고있음!!!\n"
                        "{}\n"
                        "{}"
                    )
                    msg = msg_template.format(product_info['ssg']['product_name'],
                                            data['text'])
                    url = product_info['ssg']['url']
                    
                    send_talk_msg_to_me(msg, url, url)
                    send_talk_msg(msg, url, url, 'suk')
                    check_status['ssg'] = False

                else:
                    if noti_no_stock:
                        msg = 'SSG 재고없음ㅠㅠ\n{}\n(한시간에 한번만 알림)'.format(data['text'])
                        url = product_info['ssg']['url']
                        send_talk_msg_to_me(msg, url, url)
                        send_talk_msg(msg, url, url, 'suk')
            else:
                msg = '에러발생 {}'.format(data)
                url = product_info['ssg']['url']
                send_talk_msg_to_me(msg, url, url)
                return

        period = 10
        print('sleep for a while.. ({})'.format(period))
        time.sleep(period)
        count += 1
        if count%(60*60/period) == 0:
            noti_no_stock = True
        else:
            noti_no_stock = False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('argv error')
        sys.exit()
    
    global ENV
    ENV = sys.argv[1]
    app.run(host=HOST_MAP[ENV], port="8000")
    
