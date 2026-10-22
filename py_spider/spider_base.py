"""
TVBox Spider base template/helpers for videodl ports
PolyForm Noncommercial License 1.0.0 - see LICENSE-videodl
"""
import json
import re
import os
import sys
from urllib.parse import urlparse, parse_qs, quote, unquote, urlencode
from urllib.request import Request, urlopen, build_opener, HTTPCookieProcessor
from http.cookiejar import CookieJar
from html import unescape

try:
    from base.spider import Spider
except ImportError:
    try:
        from spider import Spider
    except ImportError:
        class Spider:
            def __init__(self):
                self.extend = ''
            def init(self, extend=""):
                self.extend = extend
            def homeContent(self, filter):
                return {"class": [], "list": []}
            def homeVideoContent(self):
                return {"list": []}
            def categoryContent(self, tid, pg, filter, extend):
                return {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}
            def detailContent(self, ids):
                return {"list": []}
            def searchContent(self, key, quick, pg="1"):
                return {"list": [], "page": pg}
            def playerContent(self, flag, id, vipFlags):
                return {"parse": 0, "url": id}
            def localProxy(self, param):
                return None

class BaseSpider(Spider):
    def __init__(self):
        super().__init__()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        self.cookie_jar = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))
    
    def get(self, url, headers=None, timeout=10):
        req_headers = dict(self.headers)
        if headers:
            req_headers.update(headers)
        req = Request(url, headers=req_headers)
        resp = self.opener.open(req, timeout=timeout)
        content = resp.read()
        try:
            return content.decode('utf-8')
        except:
            try:
                return content.decode('gbk')
            except:
                return content.decode('latin-1', errors='ignore')
    
    def post(self, url, data=None, headers=None, timeout=10):
        req_headers = dict(self.headers)
        if headers:
            req_headers.update(headers)
        if isinstance(data, dict):
            data = urlencode(data).encode('utf-8')
            req_headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
        elif isinstance(data, str):
            data = data.encode('utf-8')
        req = Request(url, data=data, headers=req_headers)
        resp = self.opener.open(req, timeout=timeout)
        content = resp.read()
        try:
            return content.decode('utf-8')
        except:
            try:
                return content.decode('gbk')
            except:
                return content.decode('latin-1', errors='ignore')
    
    def fetch_json(self, url, headers=None, timeout=10):
        text = self.get(url, headers=headers, timeout=timeout)
        return json.loads(text)
    
    def legalize(self, s):
        if not s:
            return ''
        s = re.sub(r'[\\/:*?"<>|]', '', str(s))
        s = re.sub(r'\s+', ' ', s).strip()
        return s
    
    def match_domain(self, url, domains):
        try:
            host = urlparse(url).netloc.lower()
            for d in domains:
                if host == d or host.endswith('.' + d):
                    return True
        except:
            pass
        return False
    
    def build_vod(self, vod_id, name, pic='', remarks='', content='', play_from='', play_url=''):
        return {
            'vod_id': vod_id,
            'vod_name': name,
            'vod_pic': pic,
            'vod_remarks': remarks,
            'vod_content': content,
            'vod_play_from': play_from,
            'vod_play_url': play_url
        }

def safe_extract(d, keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k)
        elif isinstance(cur, list) and isinstance(k, int):
            try:
                cur = cur[k]
            except:
                return default
        else:
            return default
        if cur is None:
            return default
    return cur
