# coding: utf-8
import logging
logging.basicConfig(level=logging.INFO)
import os
from urlparse import urlparse
import pickle
import json

import redis
from requests import Session
from lxml import etree

from examples.topitem import top_item as top_item_rules
from ibdparser.parser import Parser, AjaxParser
from ibdparser.baserules import *

redis_svr_conf = {'host': '115.29.174.125'}
re_conn = redis.StrictRedis(**redis_svr_conf)
parser = etree.HTMLParser()
_default_encoding = 'GBK'

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'GBK,utf-8;q=0.7,*;q=0.3',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Accept-Language': 'zh-CN,zh;q=0.8',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Host': 'item.taobao.com',
    'Referer': 'http://taobao.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.11 TaoBrowser/3.5 Safari/536.11',
}

cookies = None
session = None
session_file = None


def _fmt_encoding(encoding):
    if not encoding:
        return _default_encoding
    if encoding.lower() in ('gbk', 'gb2312'):
        return 'GB18030'
    return encoding


def _pty_json(j, indent=None):
    if not isinstance(j, (dict, list)):
        return j
    if indent is None:
        return json.dumps(j, ensure_ascii=False)
    else:
        return json.dumps(j, ensure_ascii=False, indent=indent)


def url_get(url, force=False, allow_empty=False, **kwargs):
    global headers, cookies, session
    resp = re_conn.hget('requests.get', url)
    if resp and not force:
        return resp.decode('utf-8')
    while 1:
        headers['Host'] = urlparse(url).netloc
        resp = session.get(url, headers=headers, cookies=cookies, allow_redirects=False, **kwargs)
        if cookies is None:
            cookies = resp.cookies
        else:
            cookies.update(resp.cookies)
        if resp.status_code in range(300, 400):
            headers['Host'] = urlparse(resp.headers['location']).netloc
            headers['Referer'] = url
            url = resp.headers['location']
            continue
        html = resp.content.decode(_fmt_encoding(resp.encoding)).encode('utf-8')
        re_conn.hset('requests.get', url, html)
        if not allow_empty and not html:
            raise Exception('url_get of %s is empty' % url)
        return html.decode('utf-8')


def test_topitem():
    global session, session_file
    iid = 18878183440
    # iid = 23938544082
    iid = 13070844167
    # iid = 37467127858
    url = 'http://detail.tmall.com/item.htm?id=%s' % iid
    url = 'http://item.taobao.com/item.htm?id=%s' % iid
    session_file = '/home/cooper/session_taobao_%s' % iid
    if os.path.exists(session_file):
        session = pickle.load(open(session_file, 'r'))
    else:
        session = Session()

    html = url_get(url)
    results = dict(Parser(html, top_item_rules, 'GBK').parse())

    html_ajax = {}
    for key in (
        'rateList',
        'reviewCount',
        'confirmGoodsItems',
        'confirmGoods',
        'quanity',
        'location',
        'tradeList',
        'favNum',
        'monthlyTrade',
        'paySuccess',
        'paySuccessItems',
    ):
        if results.get(key) is None:
            continue
        if not isinstance(results[key], dict):
            continue
        url, rule = results[key]['url'], results[key]['rules']
        if html_ajax.get(url):
            html = html_ajax.get(url)
        else:
            html = url_get(url)
            html_ajax[url] = html
        results.update({key: AjaxParser(html, rule).parse()})

    for key, result in results.items():
        print '{} : {}'.format(
            key,
            result if not isinstance(result, (dict, list))
            else _pty_json(result).encode('utf-8'))


def test_jd():
    global session, session_file
    from examples.jdrules import jdrules
    url = 'http://www.jd.com'
    session_file = '/home/cooper/session_jd'
    if os.path.exists(session_file):
        session = pickle.load(open(session_file, 'r'))
    else:
        session = Session()

    html = url_get(url)
    pickle.dump(session, open(session_file, 'w'))
    for key, result in Parser(html, jdrules, 'GBK').parse():
        print '{} : {}'.format(
            key,
            result if not isinstance(result, (dict, list))
            else _pty_json(result).encode('utf-8'))


def test_etao():
    global session, session_file
    from examples.etaorules import rules
    url = 'http://www.etao.com'
    session_file = '/home/cooper/session_etao'
    if os.path.exists(session_file):
        session = pickle.load(open(session_file, 'r'))
    else:
        session = Session()

    html = url_get(url)
    pickle.dump(session, open(session_file, 'w'))
    for key, result in Parser(html, rules, 'GBK').parse():
        print '{} : {}'.format(
            key,
            result if not isinstance(result, (dict, list))
            else _pty_json(result).encode('utf-8'))


def test_appso():
    global session, session_file
    from examples.appsorules import appsorules
    url = 'http://www.ifanr.com/special/appso-xianmian'
    session_file = '/home/cooper/session_appso'
    if os.path.exists(session_file):
        session = pickle.load(open(session_file, 'r'))
    else:
        session = Session()

    html = url_get(url)
    pickle.dump(session, open(session_file, 'w'))
    items = dict(Parser(html, appsorules, 'utf-8').parse())
    for i in range(len(items['tsmp'])):
        print (items['tsmp'][i] and items['tsmp'][i][0] or '').encode('utf-8')
        print (items['title'][i] and items['title'][i][0] or '').encode('utf-8')
        print (items['desc'][i] and items['desc'][i][0] or '').encode('utf-8')
        print (items['intro'][i] and items['intro'][i][0] or '').encode('utf-8')
        print

if __name__ == '__main__':
    test_topitem()
    # test_jd()
    # test_etao()
    # test_appso()