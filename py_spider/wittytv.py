from urllib.parse import quote
from urllib.parse import unquote
# -*- coding: utf-8 -*-
# Ported from videodl (PolyForm Noncommercial License 1.0.0)
# LIMITATION: WittyTV (Mediaset Play) streams are DASH + Widevine DRM protected
# (commonEncryption), the CDM can not be emulated in a pure python TVBox spider.
# Only metadata (title/cover) is fetched over plain HTTP, playback is delegated to
# TVBox with parse=1 (page url).
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

def safe_extract(d, keys, default=None):
    try:
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
    except Exception:
        return default

class Spider:
    # ---------- inlined TVBox base helpers (self-contained, no sibling imports) ----------
    def __init__(self):
        self.extend = ''
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        try:
            from http.cookiejar import CookieJar
            from urllib.request import HTTPCookieProcessor, build_opener
            self.cookie_jar = CookieJar()
            self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))
        except Exception:
            self.cookie_jar = None
            self.opener = None

    def get(self, url, headers=None, timeout=10):
        if not getattr(self, 'opener', None):
            return ''
        req_headers = dict(getattr(self, 'headers', {}))
        if headers:
            req_headers.update(headers)
        try:
            from urllib.request import Request
            req = Request(url, headers=req_headers)
            resp = self.opener.open(req, timeout=timeout)
            content = resp.read()
            for enc in ('utf-8', 'gbk', 'latin-1'):
                try:
                    return content.decode(enc)
                except Exception:
                    continue
            return ''
        except Exception:
            return ''

    def post(self, url, data=None, headers=None, timeout=10):
        if not getattr(self, 'opener', None):
            return ''
        req_headers = dict(getattr(self, 'headers', {}))
        if headers:
            req_headers.update(headers)
        try:
            from urllib.request import Request
            from urllib.parse import urlencode
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
        except Exception:
            return ''

    def fetch_json(self, url, headers=None, timeout=10):
        try:
            import json
            return json.loads(self.get(url, headers=headers, timeout=timeout))
        except Exception:
            return {}

    def legalize(self, s):
        try:
            import re
            if not s:
                return ''
            s = re.sub(r'[\\/:*?"<>|]', '', str(s))
            return re.sub(r'\s+', ' ', s).strip()
        except Exception:
            return str(s or '')

    def match_domain(self, url, domains):
        try:
            from urllib.parse import urlparse
            host = urlparse(url).netloc.lower()
            for d in domains or []:
                d = (d or '').lower()
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

    def getName(self):
        try:
            return self.__class__.__name__
        except Exception:
            return 'Spider'

    def getDependence(self):
        return []

    def homeContent(self, filter=True):
        try:
            name = self.getName()
        except Exception:
            name = self.__class__.__name__
        return {
            "class": [{"type_id": "link", "type_name": "链接解析"}],
            "filters": {},
            "list": [{"vod_id": "usage", "vod_name": "【使用说明】", "vod_pic": "", "vod_remarks": "粘贴分享链接到搜索框解析", "vod_content": "支持直接把 %s 平台的分享链接粘贴到搜索框，即可解析并播放。" % name}]
        }

    def homeVideoContent(self):
        try:
            name = self.getName()
        except Exception:
            name = self.__class__.__name__
        return {"list": [{"vod_id": "usage", "vod_name": "【%s】粘贴分享链接到搜索框解析" % name, "vod_pic": "", "vod_remarks": "链接解析", "vod_content": "把平台分享链接粘贴到搜索栏即可"}]}

    def categoryContent(self, tid, pg, filter=None, extend=None):
        try:
            name = self.getName()
        except Exception:
            name = self.__class__.__name__
        if tid == 'link' or not tid:
            return {"page": int(pg) if pg else 1, "pagecount": 1, "limit": 20, "total": 1, "list": [{"vod_id": "usage", "vod_name": "【%s】把分享链接粘贴到搜索框" % name, "vod_pic": "", "vod_remarks": "使用说明", "vod_content": "在搜索页粘贴 http(s) 链接即可自动解析。"}]}
        return {"page": int(pg) if pg else 1, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def searchContent(self, key, quick=False, pg="1"):
        try:
            import json, re
            key = str(key or '').strip()
            m = re.search(r'(https?://[^\s]+)', key)
            if not m:
                return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
            url = m.group(1)
            try:
                res = self.detailContent([url])
                lst = (res or {}).get('list') or []
                out = []
                for v in lst:
                    try:
                        v2 = dict(v)
                        v2['vod_id'] = url
                        out.append(v2)
                    except Exception:
                        out.append(v)
                return {"page": pg, "pagecount": 1, "limit": 20, "total": len(out), "list": out}
            except Exception:
                return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
        except Exception:
            return {"page": str(pg) if pg is not None else "1", "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def detailContent(self, ids):
        return {"list": []}

    def playerContent(self, flag, id, vipFlags=None):
        try:
            if vipFlags is None:
                vipFlags = []
            import json
            return {"parse": 1, "url": str(id or ""), "header": json.dumps(getattr(self, 'headers', {}))}
        except Exception:
            return {"parse": 1, "url": str(id or "")}

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

    DOMAINS = ["wittytv.it"]
    MEDIASET_URL = 'https://mediasetinfinity.mediaset.it'
    LOGIN_URL = "https://api-ott-prod-fe.mediaset.net/PROD/play/idm/anonymous/login/v2.0"
    PLAYBACK_URL = 'https://api-ott-prod-fe.mediaset.net/PROD/play/playback/check/v2.0'
    PROGRAM_URL = 'https://feed.entertainment.tv.theplatform.eu/f/-/mediaset-prod-ext-programs-v2/guid/-/{guid}'
    def getName(self):
        return "WittyTV"
    
    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
        })
        self.token = ''
    
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, self.DOMAINS):
                return result
            html = ''
            try:
                html = self.get(url)
            except Exception:
                html = ''
            guid = self._extract_guid(html)
            program = {}
            if guid:
                try:
                    program = self.fetch_json(self.PROGRAM_URL.format(guid=guid), timeout=15) or {}
                except Exception:
                    program = {}
            title = self._parse_title(program) or self._page_title(html) or guid or url
            cover = self._parse_cover(program) or self._page_cover(html)
            media = self._extract_media(guid)
            title = title.replace('$', '').replace('#', '')
            play_id = f'{media}|{url}'
            result['list'] = [self.build_vod(guid or url, title, cover, '', title, 'WittyTV', f'{title}${play_id}')]
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
                return {"parse": 0, "url": media, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': page})}
            return {"parse": 1, "url": page or media, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': page})}
        except Exception:
            return {"parse": 1, "url": id}
    
    def _extract_guid(self, html):
        try:
            found = re.findall(r'guIDcurrentGlobal\s*=\s*"([^"]+)"', html or '')
            if found:
                return found[0]
        except Exception:
            pass
        try:
            found = re.findall(r'["\']?contentId["\']?\s*[:=]\s*["\']([A-Za-z0-9\-]{8,40})', html or '')
            if found:
                return found[0]
        except Exception:
            pass
        return ''
    
    def _parse_title(self, program):
        try:
            if not isinstance(program, dict):
                return ''
            brand = program.get('mediasetprogram$brandTitle') or program.get('mediasetprogram$auditelBrandName') or program.get('mediasetprogram$tvLinearSeasonTitle') or ''
            title = program.get('title') or ''
            if brand and title:
                return self.legalize(f'{brand}-{title}')
            return self.legalize(title or brand)
        except Exception:
            return ''
    
    def _parse_cover(self, program):
        try:
            thumbs = program.get('thumbnails') if isinstance(program, dict) else None
            if not isinstance(thumbs, dict):
                return ''
            best, best_size = '', 0
            for _, item in thumbs.items():
                if not isinstance(item, dict):
                    continue
                u = item.get('url') or ''
                size = int(item.get('width') or 0) * int(item.get('height') or 0)
                if u.startswith('http') and size > best_size:
                    best, best_size = u, size
            if best:
                return best
            for _, item in thumbs.items():
                if isinstance(item, dict):
                    u = item.get('url') or ''
                    if u.startswith('http'):
                        return u
        except Exception:
            pass
        return ''
    
    def _extract_media(self, guid):
        try:
            if not guid:
                return ''
            token = self._login()
            if not token:
                return ''
            raw = self.post(self.PLAYBACK_URL, data=json.dumps({'contentId': guid, 'streamType': 'VOD'}), headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}, timeout=15)
            selector = safe_extract(json.loads(raw), ['response', 'mediaSelector'], {}) or {}
            manifest = selector.get('url')
            if not manifest:
                return ''
            query = {k: v for k, v in selector.items() if k != 'url' and v is not None}
            query['auth'] = token
            smil = self.get(f'{manifest}?{urlencode(query)}', headers={'Accept': 'application/json, text/plain, */*', 'Origin': self.MEDIASET_URL, 'Referer': self.MEDIASET_URL}, timeout=15)
            if 'commonEncryption' in smil:
                return ''
            found = re.findall(r'<video\s+src="([^"]+)"', smil)
            for u in found:
                if u and '.m3u8' in u:
                    return u
        except Exception:
            pass
        return ''
    
    def _login(self):
        try:
            if getattr(self, 'token', ''):
                return self.token
            raw = self.post(self.LOGIN_URL, data=json.dumps({'client_id': 'client_id', 'appName': 'embed//mediasetplay-embed'}), headers={'Content-Type': 'application/json'}, timeout=15)
            token = safe_extract(json.loads(raw), ['response', 'beToken'], '') or ''
            self.token = token
            return token
        except Exception:
            return ''
    
    def _page_title(self, html):
        try:
            found = re.findall(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html or '')
            if found:
                return self.legalize(found[0])
        except Exception:
            pass
        try:
            found = re.findall(r'<title>(.*?)</title>', html or '', re.S)
            if found:
                return self.legalize(found[0])
        except Exception:
            pass
        return ''
    
    def _page_cover(self, html):
        try:
            found = re.findall(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html or '')
            if found:
                return found[0]
        except Exception:
            pass
        try:
            found = re.findall(r'(https?://[^\s"\'<>]*mediaset[^\s"\'<>]*\.(?:jpg|jpeg|png))', html or '')
            if found:
                return found[0]
        except Exception:
            pass
        return ''
