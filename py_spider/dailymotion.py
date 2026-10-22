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
import random
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

    CLIENT_ID = 'f1a362d288c1b98099c7'
    CLIENT_SECRET = 'eea605b96e01c796ff369935357eca920c5da4c5'
    ACCESS_TOKEN = None
    
    def getName(self):
        return "Dailymotion"
    
    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
            'Referer': 'https://www.dailymotion.com/',
            'Origin': 'https://www.dailymotion.com'
        })
    
    def homeContent(self, filter):
        return {"class": [], "list": []}
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["dailymotion.com"]):
                return result
            video_id = self._video_id(url)
            if not video_id:
                return result
            meta = self._metadata(video_id)
            if not meta:
                xid = self._graphql_xid(video_id)
                if xid:
                    meta = self._metadata(xid)
            if not meta:
                return result
            play = self._play_url(meta)
            if not play:
                return result
            title = self.legalize(meta.get('title') or video_id).replace('$', '').replace('#', '')
            cover = ''
            try:
                thumbs = meta.get('thumbnails') or {}
                cover = thumbs.get('1080') or thumbs.get('720') or meta.get('filmstrip_url') or ''
            except Exception:
                cover = ''
            play_id = f'{play}|{url}'
            result['list'] = [self.build_vod(video_id, title, cover, '', title, 'Dailymotion', f'{title}${play_id}')]
        except Exception:
            pass
        return result
    
    def searchContent(self, key, quick, pg="1"):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split('|')
            media = parts[0].strip()
            page = parts[-1].strip()
            if media.startswith('http'):
                header = dict(self.headers)
                header.update(self._blockbuster_headers())
                return {"parse": 0, "url": media, "header": json.dumps(header)}
            return {"parse": 1, "url": page or media}
        except Exception:
            return {"parse": 1, "url": id}
    
    def _video_id(self, url):
        try:
            m = re.search(r'(?:video/|dai\.ly/|player\.html\?video=)([a-zA-Z0-9]+)', url)
            if m:
                return m.group(1)
            m = re.search(r'([a-zA-Z0-9]{5,})', urlparse(url).path)
            return m.group(1) if m else ''
        except Exception:
            return ''
    
    def _play_url(self, meta):
        try:
            qualities = meta.get('qualities') or {}
            m3u8, progressive = '', ''
            for _, media_list in qualities.items():
                if not isinstance(media_list, list):
                    continue
                for m in media_list:
                    if not isinstance(m, dict):
                        continue
                    u = m.get('url') or ''
                    if not u:
                        continue
                    if m.get('type') == 'application/x-mpegURL' and not m3u8:
                        m3u8 = u
                    if m.get('type') in ('video/mp4', 'video/webm') and not progressive:
                        progressive = u
            play = m3u8 or progressive
            if play.startswith('//'):
                play = 'https:' + play
            return play.split('#')[0]
        except Exception:
            return ''
    
    def _metadata(self, xid):
        try:
            url = f"https://www.dailymotion.com/player/metadata/video/{xid}?app=com.dailymotion.neon"
            return self.fetch_json(url)
        except Exception:
            return None
    
    def _access_token(self):
        if Spider.ACCESS_TOKEN:
            return Spider.ACCESS_TOKEN
        try:
            data = {'client_id': Spider.CLIENT_ID, 'client_secret': Spider.CLIENT_SECRET, 'grant_type': 'client_credentials'}
            raw = json.loads(self.post('https://graphql.api.dailymotion.com/oauth/token', data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}))
            Spider.ACCESS_TOKEN = raw.get('access_token')
            return Spider.ACCESS_TOKEN
        except Exception:
            return None
    
    def _graphql_xid(self, video_id):
        try:
            token = self._access_token()
            if not token:
                return ''
            headers = dict(self.headers)
            headers['Authorization'] = f'Bearer {token}'
            headers['Content-Type'] = 'application/json'
            query = '{\n          media(xid: "%s") {\n            ... on Video {\n              xid\n              description\n              geoblockedCountries {\n                allowed\n              }\n            }\n            ... on Live {\n              xid\n              description\n              geoblockedCountries {\n                allowed\n              }\n            }\n          }\n        }' % video_id
            raw = json.loads(self.post('https://graphql.api.dailymotion.com/', data=json.dumps({'query': query}), headers=headers))
            media = safe_extract(raw, ['data', 'media'], {}) or {}
            return media.get('xid') or ''
        except Exception:
            return ''
    
    def _blockbuster_headers(self):
        try:
            def rnd(mn, mx):
                return ''.join(random.choices('bcdfghjklmnpqrstvwxz', k=random.randint(mn, mx)))
            return {rnd(8, 24): rnd(16, 32) for _ in range(random.randint(2, 8))}
        except Exception:
            return {}
