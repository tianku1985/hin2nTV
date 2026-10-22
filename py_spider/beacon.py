from urllib.parse import quote
from urllib.parse import unquote
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
from urllib.parse import urlparse, urljoin

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

    def getName(self):
        return "Beacon"

    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
        })


    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def _loads(self, text):
        try:
            return json.loads(text)
        except Exception:
            pass
        try:
            obj, _ = json.JSONDecoder().raw_decode(text.lstrip())
            return obj
        except Exception:
            pass
        try:
            fixed = re.sub(r',\s*([}\]])', r'\1', text)
            fixed = fixed.replace('\\/', '/')
            obj, _ = json.JSONDecoder().raw_decode(fixed.lstrip())
            return obj
        except Exception:
            return None

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

    def _searchbykey(self, obj, target_key, results=None):
        try:
            if results is None:
                results = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == target_key:
                        results.append(v)
                    self._searchbykey(v, target_key, results)
            elif isinstance(obj, list):
                for item in obj:
                    self._searchbykey(item, target_key, results)
            return results
        except Exception:
            return results or []

    def _sourcekey(self, item):
        try:
            return (item.get('filesize', 0) or 0,
                    item.get('bitrate', 0) or 0,
                    (item.get('width', 0) or 0) * (item.get('height', 0) or 0))
        except Exception:
            return (0, 0, 0)

    def detailContent(self, ids):
        result = {"list": []}
        url = ''
        vid = ''
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["beacon.tv"]):
                return result
            vid = urlparse(url).path.strip('/').split('/')[-1]
            page = self.get(url, timeout=15)
            m = re.search(r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', page, re.S | re.I)
            if not m:
                raise ValueError('no data')
            raw_data = self._loads(m.group(1).strip())
            if not isinstance(raw_data, dict):
                raise ValueError('no data')
            content_data = safe_extract(raw_data, ['props', 'pageProps', '__APOLLO_STATE__'], {}) or {}
            videos = self._searchbykey(content_data, 'contentVideo')
            video_data = videos[0] if videos else {}
            plists = self._searchbykey(video_data, 'playlistUrl')
            playlist_url = plists[0] if plists else ''
            title, cover, media = '', '', ''
            if playlist_url:
                if not str(playlist_url).startswith('http'):
                    playlist_url = urljoin(url, str(playlist_url))
                playlist_raw = self.fetch_json(playlist_url, headers={'Referer': url}, timeout=15)
                sources = safe_extract(playlist_raw, ['playlist', 0, 'sources'], []) or []
                sources = [s for s in sources if isinstance(s, dict)]
                sources = sorted(sources, key=self._sourcekey, reverse=True)
                if sources:
                    media = sources[0].get('file') or ''
                title = safe_extract(playlist_raw, ['playlist', 0, 'title'], '') or ''
                cover = safe_extract(playlist_raw, ['playlist', 0, 'images', -1, 'src'], '') or ''
                vid = safe_extract(playlist_raw, ['playlist', 0, 'mediaid'], '') or vid
            if not title:
                title = vid
            title = self.legalize(title).replace('$', '').replace('#', '')
            play_id = '%s|%s|%s' % ('1' if media else '0', self._enc(media), self._enc(url))
            result['list'] = [self.build_vod(vid, title, cover, '', title, 'Beacon', '%s$%s' % (title, play_id))]
        except Exception:
            pass
        if not result['list']:
            try:
                title = self.legalize(vid or 'Beacon').replace('$', '').replace('#', '')
                play_id = '0||%s' % self._enc(url)
                result['list'] = [self.build_vod(vid or url, title, '', '', title, 'Beacon', '%s$%s' % (title, play_id))]
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
                    'Referer': page or 'https://www.beacon.tv/'})}
            return {"parse": 1, "url": page or id}
        except Exception:
            return {"parse": 1, "url": id}
