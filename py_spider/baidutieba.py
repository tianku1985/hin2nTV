# -*- coding: utf-8 -*-
# Ported from videodl (PolyForm Noncommercial License 1.0.0)
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor
from urllib.request import Request
from urllib.request import build_opener
from html import unescape
import json
import re
import hashlib
from urllib.parse import urlparse, parse_qs, urlencode

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

    SALT = "36770b1f34c9bbf2e7d1a99d2b82fa9e"
    
    def getName(self):
        return "百度贴吧"
    
    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Host': 'tieba.baidu.com',
            'Referer': 'https://tieba.baidu.com/'
        })
    
    def homeContent(self, filter):
        return {"class": [], "list": []}
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["tieba.baidu.com"]):
                return result
            vid = urlparse(url).path.strip('/').split('/')[-1]
            raw_data = self._fetch_thread(vid)
            if not isinstance(raw_data, dict):
                return result
            items = self._extract_video_items(raw_data)
            if not items:
                return result
            vods = []
            for item in items:
                play = item.get('video_url') or ''
                if not play.startswith('http'):
                    continue
                title = self.legalize(item.get('title') or vid).replace('$', '').replace('#', '')
                play_id = f'{play}|{url}'
                vods.append(self.build_vod(vid, title, item.get('cover') or '', '', title, 'BaiduTieba', f'{title}${play_id}'))
            result['list'] = vods
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
                return {"parse": 0, "url": media, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': 'https://tieba.baidu.com/'})}
            return {"parse": 1, "url": page or media}
        except Exception:
            return {"parse": 1, "url": id}
    
    def _get_tbs(self):
        try:
            data = self.fetch_json("https://tieba.baidu.com/dc/common/tbs")
            return data.get('tbs', '')
        except Exception:
            return ''
    
    def _generate_sign(self, params):
        try:
            sign_params = {k: v for k, v in params.items() if k != 'sign'}
            sign_str = "".join(f"{k}={sign_params[k]}" for k in sorted(sign_params.keys())) + Spider.SALT
            return hashlib.md5(sign_str.encode('utf-8')).hexdigest()
        except Exception:
            return ''
    
    def _fetch_thread(self, vid):
        params = {"kz": str(vid), "pn": "1", "lz": "0", "r": "2", "mark_type": "0", "back": "0", "fr": "", "session_request_times": "1", "tbs": self._get_tbs(), "subapp_type": "pc", "_client_type": "20"}
        params["sign"] = self._generate_sign(params)
        api = "https://tieba.baidu.com/c/f/pb/page_pc"
        data = None
        try:
            data = json.loads(self.post(f'{api}?{urlencode(params)}', data=params, headers={'Content-Type': 'application/x-www-form-urlencoded'}))
        except Exception:
            data = None
        if not isinstance(data, dict) or not data.get('thread'):
            try:
                data = json.loads(self.post(api, data=params, headers={'Content-Type': 'application/x-www-form-urlencoded'}))
            except Exception:
                data = None
        return data
    
    def _extract_video_items(self, data):
        items = []
        try:
            title = safe_extract(data, ['thread', 'title'], '') or ''
            video_info = safe_extract(data, ['thread', 'video_info'], {}) or {}
            cover = video_info.get('thumbnail_url', '')
            main = video_info.get('video_url')
            if main and str(main).startswith('http'):
                items.append({"title": title, "cover": cover, "video_url": main})
            for v in (video_info.get('video_desc', []) or []):
                if not isinstance(v, dict):
                    continue
                v_url = v.get('video_url')
                if not v_url or not str(v_url).startswith('http'):
                    continue
                if any(i['video_url'] == v_url for i in items):
                    continue
                items.append({"title": title, "cover": cover, "video_url": v_url})
        except Exception:
            pass
        return items
