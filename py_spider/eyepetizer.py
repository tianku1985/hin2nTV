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

    DETAIL_API = 'https://proxy.eyepetizer.net/v1/content/item/get_item_detail_v2'

    def getName(self):
        return "Eyepetizer"

    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
            'x-thefair-appid': 'xfpa44crf2p70lk8',
            'x-thefair-forward-host': 'https://api.eyepetizer.net',
            'x-thefair-ua': 'EYEPETIZER_UNIAPP_H5/100000 (android;android;OS_VERSION_UNKNOWN;zh-Hans-CN;h5;2.0.0;cn-bj;SOURCE_UNKNOWN;PHPSESSID;2560*1440;NETWORK_UNKNOWN) cardsystem/2.0',
            'x-thefair-cid': '',
            'x-thefair-auth': ''
        })

    def homeContent(self, filter):
        return {"class": [], "list": []}

    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["eyepetizer.net"]):
                return result
            parsed_url_qs = parse_qs(urlparse(url).query, keep_blank_values=True)
            vid = next((parsed_url_qs[k][0] for k in ('resource_id', 'vid', 'video_id') if k in parsed_url_qs), None)
            if not vid:
                m = re.search(r'/(\d+)', urlparse(url).path)
                vid = m.group(1) if m else ''
            if not vid:
                return result
            raw_data = json.loads(self.post(self.DETAIL_API, data={'resource_type': 'pgc_video', 'resource_id': vid}, timeout=15))
            video = safe_extract(raw_data, ['result', 'video'], {}) or {}
            title = safe_extract(video, ['title'], '') or vid
            cover = safe_extract(video, ['cover', 'url'], '') or ''
            download_url = safe_extract(video, ['play_url'], '') or ''
            play_info = safe_extract(video, ['play_info'], []) or []
            candidates = [i for i in play_info if isinstance(i, dict) and i.get('url')]
            candidates.sort(key=lambda x: (int(x.get('height', 0) or 0), int(x.get('width', 0) or 0)), reverse=True)
            if candidates:
                download_url = candidates[0]['url']
            if not download_url:
                return result
            play_id = '%s|%s' % (download_url, url)
            title = self.legalize(title).replace('$', '')
            result['list'] = [self.build_vod(vid, title, cover, '', title, 'Eyepetizer', '%s$%s' % (title, play_id))]
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
                return {"parse": 0, "url": playurl, "header": json.dumps({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'})}
            return {"parse": 1, "url": page_url}
        except Exception:
            return {"parse": 1, "url": id}
