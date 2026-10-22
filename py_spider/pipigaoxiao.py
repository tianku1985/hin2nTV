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
from urllib.parse import urlparse

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

    API = "https://h5.ippzone.com/ppapi/share/fetch_content"
    DOMAINS = ["h5.ippzone.com", "share.ippzone.com"]
    URL_PATTERN = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', re.S)
    
    def getName(self):
        return "皮皮虾"
    
    def init(self, extend=""):
        self.extend = extend
    
    def homeContent(self, filter):
        return {"class": [], "list": []}
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            raw_id = ids[0] if isinstance(ids, list) else ids
            raw_id = str(raw_id or '').strip()
            url = self._first_url(raw_id)
            if not url or not self.match_domain(url, self.DOMAINS):
                return result
            mid, pid = self._ids(url)
            if not pid:
                return result
            data = self._fetch(mid, pid, url)
            post = safe_extract(data, ['data', 'post'], {}) or {}
            videos = post.get('videos') if isinstance(post.get('videos'), dict) else {}
            imgs = post.get('imgs') if isinstance(post.get('imgs'), list) else []
            img_id = ''
            if imgs and isinstance(imgs[0], dict):
                img_id = str(imgs[0].get('id') or '')
            entry = videos.get(img_id) if isinstance(videos, dict) else {}
            entry = entry if isinstance(entry, dict) else {}
            media = ''
            for key in ('url', 'urlwm', 'h5url'):
                if entry.get(key):
                    media = entry.get(key)
                    break
            cover = ''
            if videos:
                cover = 'http://file.ippzone.com/img/frame/id/%s' % list(videos.keys())[0]
            title = self._clean(post.get('content') or '') or '皮皮虾'
            play_id = '%s|%s|%s' % (pid, media, url)
            result['list'] = [self.build_vod(pid, title, cover, '', title, '皮皮虾', '%s$%s' % (title, play_id))]
        except Exception:
            pass
        return result
    
    def searchContent(self, key, quick, pg="1"):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def playerContent(self, flag, id, vipFlags):
        try:
            parts = str(id).split('|')
            media = parts[1] if len(parts) > 1 else ''
            page = parts[-1] if len(parts) > 2 else ''
            if media.startswith('http'):
                header = {'Referer': page or 'http://share.ippzone.com/', 'User-Agent': self.headers['User-Agent']}
                return {"parse": 0, "url": media, "header": json.dumps(header)}
            if page:
                header = {'Referer': page, 'User-Agent': self.headers['User-Agent']}
                return {"parse": 1, "url": page, "header": json.dumps(header)}
            return {"parse": 1, "url": id}
        except Exception:
            return {"parse": 1, "url": id}
    
    def _fetch(self, mid, pid, url):
        headers = {
            'Host': 'share.ippzone.com',
            'Origin': 'http://share.ippzone.com',
            'Referer': url,
            'Content-Type': 'application/json'
        }
        body = {'mid': int(mid) if mid else 'null', 'pid': int(pid), 'type': 'post'}
        text = self.post(self.API, data=json.dumps(body), headers=headers, timeout=10)
        return json.loads(text)
    
    def _first_url(self, text):
        found = self.URL_PATTERN.findall(text)
        if found:
            return found[0]
        if text.startswith('http'):
            return text
        return ''
    
    def _ids(self, url):
        mid = ''
        pid = ''
        try:
            mids = re.findall(r'mid=(\d+)', url, re.S)
            pids = re.findall(r'pid=(\d+)', url, re.S)
            mid = mids[0] if mids else ''
            pid = pids[0] if pids else ''
        except Exception:
            pass
        if not pid:
            pid = urlparse(url).path.replace('/pp/post/', '').strip('/')
        return mid, pid
    
    def _clean(self, s):
        s = self.legalize(s or '')
        return s.replace('#', '').replace('$', '').strip()
