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
from urllib.parse import urlparse, parse_qs, urlencode, quote

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
    PLAY_VIDEO_API = 'https://m10.iyf.tv/v3/video/play'
    WATCH_VIDEO_API = 'https://upload.iyf.tv/api/video/play'

    def getName(self):
        return "爱奇艺电影"

    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': self.UA,
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://www.iyf.tv/'
        })

    def homeContent(self, filter):
        return {"class": [], "list": []}

    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def _extractvideoid(self, page_url):
        try:
            m = re.search(r'/play/([^/?#]+)', page_url)
            if m:
                return m.group(1), 'play'
            qs = parse_qs(urlparse(page_url).query)
            if 'v' in qs and qs['v']:
                return qs['v'][0], 'watch'
        except Exception:
            pass
        return '', ''

    def _extractbalancedjson(self, text, marker='var injectJson ='):
        try:
            brace_start = text.find('{', text.find(marker))
            if brace_start < 0:
                return None
            depth, in_string, escape = 0, False, False
            for i in range(brace_start, len(text)):
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
                        return json.loads(text[brace_start:i + 1])
        except Exception:
            return None
        return None

    def _extractpconfig(self, html_text):
        try:
            data = self._extractbalancedjson(html_text)
            pconfig = data['config'][0]['pConfig']
            return pconfig['publicKey'], pconfig['privateKey'][0]
        except Exception:
            return '', ''

    def _buildsignedquery(self, video_id, public_key, private_key):
        params = [('cinema', '1'), ('id', video_id), ('a', '1'), ('lang', 'none'), ('usersign', '1'), ('region', 'US'), ('device', '1'), ('isMasterSupport', '1')]
        base_query = urlencode(params)
        raw = '%s&%s&%s' % (public_key, base_query.lower(), private_key)
        vv = hashlib.md5(raw.encode('utf-8')).hexdigest()
        return base_query + '&vv=' + vv + '&pub=' + quote(public_key, safe='')

    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["iyf.tv"]):
                return result
            vid, mode = self._extractvideoid(url)
            if not vid:
                return result
            html_text = self.get(url, timeout=15)
            public_key, private_key = self._extractpconfig(html_text)
            if not public_key or not private_key:
                return result
            signed_query = self._buildsignedquery(vid, public_key, private_key)
            play_url = (self.PLAY_VIDEO_API if mode == 'play' else self.WATCH_VIDEO_API) + '?' + signed_query
            raw_data = json.loads(self.get(play_url, timeout=15))
            info = safe_extract(raw_data, ['data', 'info', 0], {}) or {}
            flv_path_list = info.get('flvPathList') or []
            if not flv_path_list:
                return result
            items = sorted(flv_path_list, key=lambda x: x.get('bitrate', 0) or 0, reverse=True)
            download_url = items[0].get('result') or items[0].get('dashResult') or items[0].get('rtmp') or ''
            if not download_url:
                return result
            title = info.get('title') or info.get('contxt') or vid
            cover = info.get('image') or ''
            play_id = '%s|%s' % (download_url, url)
            title = self.legalize(title).replace('$', '')
            result['list'] = [self.build_vod(vid, title, cover, '', title, 'IYF', '%s$%s' % (title, play_id))]
        except Exception:
            pass
        return result

    def searchContent(self, key, quick, pg="1"):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split('|')
            playurl = parts[0] if len(parts) > 1 else ''
            page_url = parts[-1]
            if playurl.startswith('http'):
                return {"parse": 0, "url": playurl, "header": json.dumps({'User-Agent': self.UA, 'Referer': 'https://www.iyf.tv/'})}
            return {"parse": 1, "url": page_url}
        except Exception:
            return {"parse": 1, "url": id}
