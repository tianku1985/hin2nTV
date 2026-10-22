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
import time
import base64
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

    def getName(self):
        return "乐视"
    
    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Referer': 'http://www.le.com/'
        })
    
    def homeContent(self, filter):
        return {"class": [], "list": []}
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["le.com"]):
                return result
            vid = self._getvid(url)
            api_url = (f'http://player-pc.le.com/mms/out/video/playJson?id={vid}&platid=1&splatid=105&format=1'
                       f'&source=1000&tkey={self._calctimekey(int(time.time()))}&domain=www.le.com&region=cn')
            raw_data = self.fetch_json(api_url)
            title = self.legalize(str(safe_extract(raw_data, ['msgs', 'playurl', 'title'], '') or '')).removesuffix('.').replace('$', '').replace('#', '') or vid or 'leshi'
            cover = safe_extract(raw_data, ['msgs', 'playurl', 'picAll', '640*320'], '') or ''
            play_domain = safe_extract(raw_data, ['msgs', 'playurl', 'domain', 0], '') or 'http://play.g3proxy.lecloud.com'
            dispatch = safe_extract(raw_data, ['msgs', 'playurl', 'dispatch'], {}) or {}
            media_url = ''
            try:
                items = sorted(dispatch.items(), key=lambda x: int(''.join(filter(str.isdigit, x[0])) or 0), reverse=True)
            except:
                items = list(dispatch.items())
            for _, format_data in items:
                try:
                    value = format_data
                    if isinstance(value, (list, tuple)):
                        value = value[0] if value else ''
                    if not value:
                        continue
                    media_url = play_domain + str(value)
                    media_url = self._fixflashurl(media_url)
                    break
                except:
                    continue
            location_url = ''
            if media_url:
                try:
                    location_url = self._getlocation(media_url)
                except:
                    location_url = ''
            play_id = f'{vid}|{location_url}|{media_url}|{url}'
            vod = self.build_vod(vid or url, title, cover, '', title, 'Leshi', f'{title}${play_id}')
            result['list'] = [vod]
        except Exception:
            pass
        return result
    
    def searchContent(self, key, quick, pg="1"):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split('|', 3)
            location_url = parts[1] if len(parts) > 1 else ''
            media_url = parts[2] if len(parts) > 2 else ''
            page_url = parts[3] if len(parts) > 3 else id
            if not location_url and media_url:
                try:
                    location_url = self._getlocation(media_url)
                except:
                    location_url = ''
            if location_url:
                body = self.get(location_url, headers={'User-Agent': self.headers['User-Agent'], 'Referer': 'https://www.le.com/'})
                if body[:5].lower() != 'vc_01':
                    return {"parse": 0, "url": location_url, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': 'https://www.le.com/'})}
                playlist = self._decryptfromtext(body)
                if playlist:
                    data_uri = 'data:application/vnd.apple.mpegurl;base64,' + base64.b64encode(playlist.encode('utf-8', errors='ignore')).decode('utf-8')
                    return {"parse": 0, "url": data_uri, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': 'https://www.le.com/'})}
            return {"parse": 1, "url": page_url}
        except Exception:
            return {"parse": 1, "url": id}
    
    def _getvid(self, url):
        try:
            m = re.search(r'https?://(?:www\.le\.com/ptv/vplay|(?:sports\.le|(?:www\.)?lesports)\.com/(?:match|video))/(?P<id>\d+)\.html', url)
            if m:
                return m.group('id')
            return urlparse(url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm')
        except Exception:
            return ''
    
    def _calctimekey(self, timestamp):
        try:
            x = timestamp & 0xFFFFFFFF
            for _ in range(185025305 % 17):
                x = ((x & 0xFFFFFFFF) >> 1) + ((x & 1) << 31)
            return x ^ 185025305
        except Exception:
            return 185025305
    
    def _fixflashurl(self, media_url):
        try:
            for k, v in {'m3v': '1', 'format': '1', 'expect': '3', 'tss': 'ios'}.items():
                if re.search(r'([?&])' + k + r'=[^&]*', media_url):
                    media_url = re.sub(r'([?&])' + k + r'=[^&]*', r'\g<1>' + k + '=' + v, media_url)
                else:
                    media_url = media_url + f'&{k}={v}'
            return media_url
        except Exception:
            return media_url
    
    def _getlocation(self, media_url):
        try:
            data = self.fetch_json(media_url, headers={'User-Agent': self.headers['User-Agent'], 'Referer': 'http://www.le.com/'})
            location = safe_extract(data, ['nodelist', 0, 'location'], '')
            return location if isinstance(location, str) else ''
        except Exception:
            return ''
    
    def _decryptm3u8(self, data):
        try:
            if data[:5].decode('utf-8', errors='ignore').lower() != 'vc_01':
                return data
            body = data[5:]
            loc4 = bytearray(2 * len(body))
            for idx, val in enumerate(body):
                loc4[2 * idx] = val // 16
                loc4[2 * idx + 1] = val % 16
            idx = len(loc4) - 11
            loc4 = loc4[idx:] + loc4[:idx]
            out = bytearray(len(body))
            for i in range(len(body)):
                out[i] = loc4[2 * i] * 16 + loc4[2 * i + 1]
            return bytes(out)
        except Exception:
            return b''
    
    def _decryptfromtext(self, text):
        try:
            candidates = []
            for enc in ('utf-8', 'gbk', 'latin-1'):
                try:
                    candidates.append(text.encode(enc))
                except:
                    continue
            for raw in candidates:
                decrypted = self._decryptm3u8(raw)
                try:
                    content = decrypted.decode('utf-8')
                except:
                    continue
                if content.lstrip().startswith('#EXTM3U'):
                    return content
            return ''
        except Exception:
            return ''
