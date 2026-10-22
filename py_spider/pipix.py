# -*- coding: utf-8 -*-
# Ported from videodl (PolyForm Noncommercial License 1.0.0)
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor
from urllib.request import Request
from urllib.request import build_opener
from urllib.parse import urlparse
from urllib.parse import urlencode
from html import unescape
import json
import re
from urllib.parse import unquote

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

    RENDER_PATTERN = re.compile(r'<script id="RENDER_DATA" type="application/json">(.*?)</script>', re.S)
    COMMENT_API = "https://api.pipix.com/bds/cell/cell_comment/?offset=0&cell_type=1&api_version=1&cell_id={vid}&ac=wifi&channel=huawei_1319_64&aid=1319&app_name=super"
    DOMAINS = ["pipix.com"]
    
    def getName(self):
        return "PIPIX"
    
    def init(self, extend=""):
        self.extend = extend
    
    def homeContent(self, filter):
        return {"class": [], "list": []}
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            url = str(url or '').strip()
            if not self.match_domain(url, self.DOMAINS):
                return result
            html_text = self.get(url, timeout=10)
            title, cover, media, ident = '', '', '', ''
            m = self.RENDER_PATTERN.search(html_text)
            if m:
                raw = self._loads(unquote(m.group(1)))
                media = safe_extract(raw, ['ppxItemDetail', 'item', 'video', 'video_download', 'url_list', 0, 'url'], '') or ''
                title = safe_extract(raw, ['ppxItemDetail', 'item', 'video', 'title'], '') or safe_extract(raw, ['ppxItemDetail', 'item', 'share', 'title'], '') or ''
                cover = safe_extract(raw, ['ppxItemDetail', 'item', 'cover', 'url_list', 0, 'url'], '') or ''
                ident = str(safe_extract(raw, ['ppxItemDetail', 'item', 'item_id'], '') or '')
            else:
                vid = self._item_id(url)
                if not vid:
                    return result
                raw = self._comment(vid)
                item = safe_extract(raw, ['data', 'cell_comments', 0, 'comment_info', 'item'], {}) or {}
                author_id = safe_extract(item, ['author', 'id'], '')
                media = ''
                try:
                    for c in item.get('comments', []) or []:
                        if safe_extract(c, ['item', 'author', 'id'], None) == author_id:
                            media = safe_extract(c, ['item', 'video', 'video_high', 'url_list', 0, 'url'], '') or ''
                            if media:
                                break
                except Exception:
                    media = ''
                if not media:
                    media = safe_extract(item, ['video', 'video_high', 'url_list', 0, 'url'], '') or ''
                title = item.get('content') or ''
                cover = safe_extract(item, ['cover', 'url_list', 0, 'url'], '') or ''
                ident = vid
            if not media:
                return result
            title = self._clean(title) or 'PIPIX'
            play_id = '%s|%s|%s' % (ident, media, url)
            result['list'] = [self.build_vod(ident or url, title, cover, '', title, 'PIPIX', '%s$%s' % (title, play_id))]
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
                header = {'Referer': page or 'https://www.pipix.com/', 'User-Agent': self.headers['User-Agent']}
                return {"parse": 0, "url": media, "header": json.dumps(header)}
            if page:
                header = {'Referer': page, 'User-Agent': self.headers['User-Agent']}
                return {"parse": 1, "url": page, "header": json.dumps(header)}
            return {"parse": 1, "url": id}
        except Exception:
            return {"parse": 1, "url": id}
    
    def _comment(self, vid):
        text = self.get(self.COMMENT_API.format(vid=vid), timeout=10)
        return json.loads(text)
    
    def _item_id(self, url):
        found = re.findall(r'item/(\d+)', url)
        if found:
            return found[0]
        try:
            final = self.opener.open(url, timeout=10).geturl()
            found = re.findall(r'item/(\d+)', final)
            if found:
                return found[0]
        except Exception:
            pass
        return ''
    
    def _loads(self, text):
        try:
            return json.loads(text)
        except Exception:
            pass
        try:
            return json.loads(re.sub(r',\s*([\]}])', r'\1', text))
        except Exception:
            pass
        try:
            obj, _ = json.JSONDecoder().raw_decode(text.lstrip())
            return obj
        except Exception:
            return {}
    
    def _clean(self, s):
        s = self.legalize(s or '')
        return s.replace('#', '').replace('$', '').strip()
