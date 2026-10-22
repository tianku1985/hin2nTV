# -*- coding: utf-8 -*-
# Ported from videodl (PolyForm Noncommercial License 1.0.0)
import re
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor
from urllib.request import Request
from urllib.request import build_opener
from urllib.parse import urlencode
from html import unescape
import json
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
        return "最右"

    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
        })

    def homeContent(self, filter):
        return {"class": [], "list": []}

    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def _enc(self, s):
        try:
            return str(s).replace('$', '%24').replace('#', '%23').replace('|', '%7C')
        except Exception:
            return ''

    def _dec(self, s):
        try:
            return str(s).replace('%24', '$').replace('%23', '#').replace('%7C', '|')
        except Exception:
            return ''

    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["share.xiaochuankeji.cn"]):
                return result
            vid = parse_qs(urlparse(url).query, keep_blank_values=True).get('pid', [''])[0]
            if not vid:
                return result
            body = json.dumps({"h_av": "5.2.13.011", "pid": int(vid)})
            headers = {
                'Content-Type': 'application/json',
                'Referer': 'https://share.xiaochuankeji.cn/',
                'User-Agent': self.headers['User-Agent']
            }
            text = self.post('https://share.xiaochuankeji.cn/planck/share/post/detail_h5',
                             data=body, headers=headers, timeout=15)
            raw_data = json.loads(text)
            post = safe_extract(raw_data, ['data', 'post'], {}) or {}
            imgs = post.get('imgs') or []
            img_id = str(imgs[0].get('id')) if imgs and isinstance(imgs[0], dict) else ''
            videos = post.get('videos') or {}
            media = safe_extract(videos, [img_id, 'url'], '') or ''
            title = post.get('content') or vid
            cover = safe_extract(post, ['imgs', 0, 'urls', '540', 'urls', 0], '') or ''
            title = self.legalize(title).replace('$', '').replace('#', '')
            play_id = '%s|%s|%s' % ('1' if media else '0', self._enc(media), self._enc(url))
            result['list'] = [self.build_vod(vid, title, cover, '', title, 'Zuiyou', '%s$%s' % (title, play_id))]
        except Exception:
            pass
        return result

    def searchContent(self, key, quick, pg="1"):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split('|')
            media = self._dec(parts[1]).strip() if len(parts) > 2 else ''
            page = self._dec(parts[-1]).strip() if len(parts) > 2 else id
            if len(parts) > 2 and parts[0] == '1' and media.startswith('http'):
                return {"parse": 0, "url": media, "header": json.dumps({
                    'User-Agent': self.headers['User-Agent'],
                    'Referer': 'https://share.xiaochuankeji.cn/'})}
            return {"parse": 1, "url": page or id}
        except Exception:
            return {"parse": 1, "url": id}
