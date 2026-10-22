# -*- coding: utf-8 -*-
# Ported from videodl (PolyForm Noncommercial License 1.0.0)
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor
from urllib.request import Request
from urllib.request import build_opener
from urllib.parse import urlencode
from html import unescape
import json
import re
import html
from urllib.parse import urlparse, parse_qs

def safe_extract(d, keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k)
        elif isinstance(cur, list) and isinstance(k, int):
            try:
                cur = cur[k]
            except Exception:
                return default
        else:
            return default
        if cur is None:
            return default
    return cur

class Spider:
    # ---------- inlined TVBox base helpers (self-contained, no sibling imports) ----------
    def __init__(self):
        self.extend = ''
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
        for enc in ('utf-8', 'gbk', 'latin-1'):
            try:
                return content.decode(enc)
            except Exception:
                continue
        return ''

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
        for enc in ('utf-8', 'gbk', 'latin-1'):
            try:
                return content.decode(enc)
            except Exception:
                continue
        return ''

    def fetch_json(self, url, headers=None, timeout=10):
        return json.loads(self.get(url, headers=headers, timeout=timeout))

    def legalize(self, s):
        if not s:
            return ''
        s = re.sub(r'[\\/:*?"<>|]', '', str(s))
        return re.sub(r'\s+', ' ', s).strip()

    def match_domain(self, url, domains):
        try:
            host = urlparse(url).netloc.lower()
            for d in domains:
                if host == d or host.endswith('.' + d):
                    return True
        except Exception:
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

    # ---------- standard TVBox spider interface defaults ----------
    def getDependence(self):
        return []

    def homeVideoContent(self):
        return {"list": []}

    def liveContent(self, url):
        return ""

    def localProxy(self, param):
        return None

    def isVideoFormat(self, url):
        return True

    def manualVideoCheck(self):
        return False

    def action(self, action):
        return {}

    def destroy(self):
        pass

    def getName(self):
        return "Oasis"
    
    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
        })
    
    def homeContent(self, filter):
        return {"class": [], "list": []}
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["m.oasis.weibo.cn"]):
                return result
            vid = parse_qs(urlparse(url).query, keep_blank_values=True).get('sid', [''])[0]
            raw = self.get(url)
            download_url = ''
            m = re.search(r'<video\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', raw, re.IGNORECASE | re.DOTALL)
            if m:
                download_url = m.group(1)
            if download_url.startswith('//'):
                download_url = 'https:' + download_url
            title = ''
            tm = re.search(r'<div\b[^>]*class\s*=\s*["\'][^"\']*status-title[^"\']*["\'][^>]*>(.*?)</div>', raw, re.IGNORECASE | re.DOTALL)
            if tm:
                title = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', tm.group(1)))).strip()
            title = self.legalize(title).removesuffix('.').replace('$', '').replace('#', '') or vid or 'oasis'
            cover = ''
            cm = re.search(r'<[^>]*class\s*=\s*["\'][^"\']*video-cover[^"\']*["\'][^>]*>', raw, re.IGNORECASE | re.DOTALL)
            if cm:
                sm = re.search(r'style\s*=\s*["\']([^"\']*)["\']', cm.group(0), re.IGNORECASE | re.DOTALL)
                if sm:
                    um = re.search(r'url\((.*?)\)', sm.group(1))
                    if um:
                        cover = um.group(1).strip('\'" ')
            play_id = f'{vid}|{download_url}|{url}'
            vod = self.build_vod(vid or url, title, cover, '', title, 'Oasis', f'{title}${play_id}')
            result['list'] = [vod]
        except Exception:
            pass
        return result
    
    def searchContent(self, key, quick, pg="1"):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split('|', 2)
            download_url = parts[1] if len(parts) > 1 else ''
            page_url = parts[2] if len(parts) > 2 else id
            if download_url.startswith('http'):
                return {"parse": 0, "url": download_url, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': 'https://m.oasis.weibo.cn/'})}
            return {"parse": 1, "url": page_url}
        except Exception:
            return {"parse": 1, "url": id}
