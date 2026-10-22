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

    UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
    ROUTER_DATA_RE = re.compile(r"window\._ROUTER_DATA\s*=\s*(.*?)</script>", re.S | re.I)

    def getName(self):
        return "抖音"

    def init(self, extend=""):
        self.extend = extend
        self.headers.update({'User-Agent': self.UA})

    def homeContent(self, filter):
        return {"class": [], "list": []}

    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def _loads(self, text):
        try:
            return json.loads(text)
        except Exception:
            pass
        try:
            fixed = re.sub(r',\s*([}\]])', r'\1', text)
            fixed = fixed.replace('\\/', '/')
            return json.loads(fixed)
        except Exception:
            return {}

    def _extractjson(self, text, marker='window._ROUTER_DATA'):
        try:
            start = text.find('{', text.find(marker))
            if start < 0:
                return None
            depth, in_string, escape = 0, False, False
            for i in range(start, len(text)):
                ch = text[i]
                if in_string:
                    escape, in_string = (False, in_string) if escape else (ch == '\\', ch != '"')
                    continue
                if ch == '"':
                    in_string = True
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return self._loads(text[start:i + 1])
            return None
        except Exception:
            return None

    def _resolvevid(self, url):
        try:
            host = urlparse(url).netloc.lower()
            if 'v.douyin.com' in host:
                try:
                    resp = self.opener.open(url, timeout=10)
                    url = resp.geturl()
                except Exception:
                    pass
            m = re.search(r'/video/(\d{5,})', url) or re.search(r'modal_id=(\d{5,})', url) or re.search(r'(\d{15,})', url)
            return (m.group(1) if m else ''), url
        except Exception:
            return '', url

    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["douyin.com"]):
                return result
            vid, url = self._resolvevid(url)
            if not vid:
                return result
            html = self.get('https://www.iesdouyin.com/share/video/%s' % vid, timeout=15)
            raw_data = self._extractjson(html)
            video_detail = safe_extract(raw_data or {}, ['loaderData', 'video_(id)/page', 'videoInfoRes', 'item_list', 0], {}) or {}
            title = safe_extract(video_detail, ['desc'], '') or ''
            cover = safe_extract(video_detail, ['video', 'cover', 'url_list', 0], '') or ''
            uri = safe_extract(video_detail, ['video', 'play_addr', 'uri'], '') or ''
            if not title:
                m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]*)"', html, re.I)
                title = m.group(1) if m else vid
            play_id = '%s|%s|%s' % (vid, uri, url)
            title = self.legalize(title).replace('$', '')
            result['list'] = [self.build_vod(vid, title, cover, '', title, 'Douyin', '%s$%s' % (title, play_id))]
        except Exception:
            pass
        return result

    def searchContent(self, key, quick, pg="1"):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split('|')
            uri = parts[1] if len(parts) > 2 else ''
            page_url = parts[-1]
            if uri:
                playurl = 'http://www.iesdouyin.com/aweme/v1/play/?video_id=%s&ratio=1080p&line=0' % uri
                return {"parse": 0, "url": playurl, "header": json.dumps({'User-Agent': self.UA, 'Referer': 'https://www.douyin.com/'})}
            return {"parse": 1, "url": page_url}
        except Exception:
            return {"parse": 1, "url": id}
