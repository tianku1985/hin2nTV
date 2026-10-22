# -*- coding: utf-8 -*-
# Ported from videodl (PolyForm Noncommercial License 1.0.0)
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor
from urllib.request import Request
from urllib.request import build_opener
from html import unescape
import json
import re
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

    def getName(self):
        return "56网"
    
    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
        })
    
    def homeContent(self, filter):
        return {"class": [], "list": []}
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["56.com"]):
                return result
            vid = self._vid(url)
            html = self.get(url)
            raw_data = self._loads(self._extract_object(html, 'var videoInfo'))
            if not isinstance(raw_data, dict):
                return result
            sohu_url = safe_extract(raw_data, ['sohu', 'video_url'], '') or ''
            title = self.legalize(raw_data.get('Subject') or vid).replace('$', '').replace('#', '')
            cover = raw_data.get('img') or ''
            if sohu_url and sohu_url.startswith('//'):
                sohu_url = 'https:' + sohu_url
            if not sohu_url:
                return result
            play_id = f'{sohu_url}|{url}'
            result['list'] = [self.build_vod(vid, title, cover, '', title, 'C56', f'{title}${play_id}')]
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
                direct = self._resolve_sohu(media)
                if direct:
                    return {"parse": 0, "url": direct, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': media})}
            return {"parse": 1, "url": page or media}
        except Exception:
            return {"parse": 1, "url": id}
    
    def _vid(self, url):
        m = re.search(r'https?://(?:(?:www|player)\.)?56\.com/(?:.+?/)?(?:v_|(?:play_album.+-))(.+?)\.(?:html|swf)', url)
        if m:
            return m.group(1)
        return urlparse(url).path.strip('/').split('/')[-1].split('.')[0]
    
    def _resolve_sohu(self, url):
        try:
            html = self.get(url)
            m = re.search(r'var\s+vid\s*=\s*["\'](\d+)["\']', html) or re.search(r'data-vid\s*=\s*["\']?(\d+)', html)
            if not m:
                return ''
            vid = m.group(1)
            urls = self._sohu_hot(vid) or self._sohu_mytv(vid)
            return self._finalize(urls)
        except Exception:
            return ''
    
    def _sohu_hot(self, vid):
        try:
            params = {'vid': vid, 'ver': '1', 'ssl': '1', 'uid': '17636986544987061902', 'pflag': 'pch5', 'prod': 'h5n', 'platform_source': 'pc'}
            raw = json.loads(self.get(f'https://hot.vrs.sohu.com/vrs_pc_play.action?{urlencode(params)}'))
            data = raw.get('data')
            if not isinstance(data, dict):
                return []
            priority = ["relativeId", "norVid", "highVid", "superVid", "oriVid", "h2644kVid", "h265norVid", "h265highVid", "h265superVid", "h265oriVid", "h2654mVid", "h2654kVid", "norVid_ns", "highVid_ns", "superVid_ns", "oriVid_ns", "p1080HdrVid", "p1080Hdr265Vid", "p1080HdrVid_ns", "p1080Hdr265Vid_ns", "tvVer35_vid", "tvVer36_vid", "tvVer34_vid", "tvVer284_vid", "tvVer285_vid", "tvVer260_vid", "tvVer262_vid", "tvVer264_vid", "tvVer266_vid", "tvVer301_vid", "tvVer302_vid", "tvVer303_vid", "tvVer304_vid", "tvVer306_vid", "tvVer307_vid", "tvVer321_vid", "tvVer322_vid", "tvVer323_vid", "tvVer324_vid", "tvVer326_vid", "tvVer327_vid"][::-1]
            def to_int0(x):
                if isinstance(x, str) and x.strip().lstrip('+-').isdigit():
                    return int(x)
                if isinstance(x, str):
                    return 0
                return x
            vid2 = 0
            for k in priority:
                v = to_int0(data.get(k, 0))
                if v and v != 0:
                    vid2 = v
                    break
            if not vid2:
                return []
            params['vid'] = vid2
            raw2 = json.loads(self.get(f'https://hot.vrs.sohu.com/vrs_pc_play.action?{urlencode(params)}'))
            urls = safe_extract(raw2, ['data', 'mp4PlayUrl'], []) or []
            return [u for u in urls if isinstance(u, str) and u]
        except Exception:
            return []
    
    def _sohu_mytv(self, vid):
        try:
            raw = json.loads(self.get(f'http://my.tv.sohu.com/play/videonew.do?vid={vid}&referer=http://my.tv.sohu.com'))
            qualities = ['norVid', 'highVid', 'superVid', 'oriVid'][::-1]
            vid2 = ''
            for q in qualities:
                v = safe_extract(raw, ['data', q], '') or ''
                if v:
                    vid2 = v
                    break
            if not vid2:
                return []
            raw2 = json.loads(self.get(f'http://my.tv.sohu.com/play/videonew.do?vid={vid2}&referer=http://my.tv.sohu.com'))
            urls = safe_extract(raw2, ['data', 'mp4PlayUrl'], []) or []
            return [u for u in urls if isinstance(u, str) and u]
        except Exception:
            return []
    
    def _finalize(self, urls):
        try:
            out = []
            for u in urls:
                if u.startswith('//'):
                    u = 'https:' + u
                if not u.startswith('http'):
                    continue
                out.append(u)
            parsed = []
            for u in out:
                try:
                    data = json.loads(self.get(u))
                    real = safe_extract(data, ['servers', 0, 'url'], '')
                    if real and str(real).startswith('http'):
                        parsed.append(real)
                except Exception:
                    parsed.append(u)
            if parsed:
                return parsed[0]
        except Exception:
            pass
        return ''
    
    def _extract_object(self, text, marker):
        try:
            idx = text.find(marker)
            if idx < 0:
                return ''
            start = text.find('{', idx)
            if start < 0:
                return ''
            depth, in_str, esc, quote = 0, False, False, ''
            for i in range(start, len(text)):
                ch = text[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == '\\':
                        esc = True
                    elif ch == quote:
                        in_str = False
                    continue
                if ch in '"\'':
                    in_str, quote = True, ch
                    continue
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return text[start:i + 1]
        except Exception:
            pass
        return ''
    
    def _loads(self, text):
        try:
            if not text:
                return None
            return json.loads(text)
        except Exception:
            pass
        try:
            return json.loads(re.sub(r',\s*([}\]])', r'\1', text))
        except Exception:
            return None
