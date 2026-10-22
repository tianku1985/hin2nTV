# -*- coding: utf-8 -*-
# Ported from videodl (PolyForm Noncommercial License 1.0.0)
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor
from urllib.request import Request
from urllib.request import build_opener
from html import unescape
import json
import re
import time
import random
import hashlib
import html
from urllib.parse import urlparse, urlencode

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

    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
    DETAIL_API = 'https://kapi.kankanews.com/content/pc/news/detail'
    APP_VERSION = '2.45.1'
    SIGN_SECRET = '28c8edde3d61a0411511d3b1866f0636'

    def getName(self):
        return "看看新闻"

    def init(self, extend=""):
        self.extend = extend
        self.headers.update({'User-Agent': self.UA})

    def homeContent(self, filter):
        return {"class": [], "list": []}

    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def _decodejsstring(self, text):
        try:
            if text is None:
                return None
            return json.loads('"%s"' % html.unescape(text))
        except Exception:
            try:
                return html.unescape(text).replace('\\u002F', '/').replace('\\/', '/')
            except Exception:
                return text

    def _firstmatch(self, patterns, text):
        try:
            for p in patterns:
                m = re.search(p, str(text), re.S | re.I)
                if m:
                    return m.group(1).strip()
            return None
        except Exception:
            return None

    def _extractfields(self, text):
        player_url = self._firstmatch([
            r'video_info\s*:\s*\{.*?play_url\s*:\s*"((?:\\.|[^"\\])*)"',
            r'play_url\s*:\s*"((?:\\.|[^"\\])*)"',
            r'["\']play_url["\']\s*:\s*["\']((?:\\.|[^"\'])*)["\']'
        ], text)
        cover_url = self._firstmatch([
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'\bcover\s*:\s*"((?:\\.|[^"\\])*)"'
        ], text)
        title = self._firstmatch([
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']',
            r'<h1[^>]*class=["\'][^"\']*video-bt[^"\']*["\'][^>]*>(.*?)</h1>',
            r'<title>(.*?)</title>'
        ], text)
        if title:
            title = html.unescape(title).strip()
            if '_看呀STV_看看新闻网' in title:
                title = title.split('_')[0].strip()
        return {'player_url': self._decodejsstring(player_url), 'cover_url': self._decodejsstring(cover_url), 'title': title}

    def _signheaders(self, params):
        merged = dict(params)
        merged.update({
            'platform': 'pc',
            'version': self.APP_VERSION,
            'nonce': ''.join(random.choice('0123456789abcdefghijklmnopqrstuvwxyz') for _ in range(8)),
            'timestamp': str(int(time.time())),
            'Api-Version': 'v1'
        })
        raw = ''
        for k in sorted(merged.keys()):
            v = merged[k]
            if v is None:
                continue
            if isinstance(v, (list, dict)):
                v = json.dumps(v, separators=(',', ':')).replace('/', '\\/')
            raw += '%s=%s&' % (k, v)
        sign = hashlib.md5(hashlib.md5((raw + self.SIGN_SECRET).encode('utf-8')).hexdigest().encode('utf-8')).hexdigest()
        merged['sign'] = sign
        return merged

    def _apiresult(self, content_id):
        try:
            params = {'content_id': content_id}
            headers = self._signheaders(params)
            headers.update({'User-Agent': self.UA, 'Referer': 'https://www.kankanews.com/'})
            raw_data = json.loads(self.get('%s?%s' % (self.DETAIL_API, urlencode(params)), headers=headers, timeout=15))
            if str(raw_data.get('code')) not in ('1000', '200'):
                return {}
            return raw_data.get('result') or {}
        except Exception:
            return {}

    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["kankanews.com"]):
                return result
            vid = urlparse(url).path.strip('/').split('/')[-1]
            html_text = self.get(url, timeout=15)
            raw_data = self._extractfields(html_text)
            title = raw_data.get('title') or ''
            cover = raw_data.get('cover_url') or ''
            download_url = raw_data.get('player_url') or ''
            if not download_url and vid:
                api_result = self._apiresult(vid)
                if api_result:
                    video_info = safe_extract(api_result, ['video_info'], {}) or {}
                    download_url = video_info.get('play_url') or ''
                    title = title or api_result.get('title') or ''
                    cover = cover or video_info.get('cover') or api_result.get('cover') or ''
            if not title:
                title = vid
            play_id = '%s|%s|%s' % (download_url, vid, url)
            title = self.legalize(title).replace('$', '')
            result['list'] = [self.build_vod(vid, title, cover, '', title, 'KanKanNews', '%s$%s' % (title, play_id))]
        except Exception:
            pass
        return result

    def searchContent(self, key, quick, pg="1"):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split('|')
            playurl = parts[0] if len(parts) > 2 else ''
            content_id = parts[1] if len(parts) > 2 else ''
            page_url = parts[-1]
            if not playurl and content_id:
                api_result = self._apiresult(content_id)
                playurl = safe_extract(api_result, ['video_info', 'play_url'], '') or ''
            if playurl.startswith('http'):
                return {"parse": 0, "url": playurl, "header": json.dumps({'User-Agent': self.UA, 'Referer': 'https://www.kankanews.com/'})}
            return {"parse": 1, "url": page_url}
        except Exception:
            return {"parse": 1, "url": id}
