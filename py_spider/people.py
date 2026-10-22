from urllib.parse import quote
from urllib.parse import unquote
# -*- coding: utf-8 -*-
# Ported from videodl (PolyForm Noncommercial License 1.0.0)
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor
from urllib.request import Request
from urllib.request import build_opener
from urllib.parse import urlencode
import json
import re
from html import unescape
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

    DOMAINS = ["people.cn", "people.com.cn"]
    PLAYER_API = "http://tvplayer.people.com.cn/getXML.php?path={path}&callback=playForMobile&ios=0"
    
    def getName(self):
        return "人民网"
    
    def init(self, extend=""):
        self.extend = extend
    
    
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
            parsed = urlparse(url)
            base_url = '%s://%s' % (parsed.scheme or 'http', parsed.netloc)
            info = self._extract(html_text, base_url)
            title = self._clean(info.get('title') or '') or '人民网视频'
            cover = info.get('cover_url') or ''
            media = info.get('video_url') or ''
            play_id = '%s|%s' % (media, url)
            result['list'] = [self.build_vod(url, title, cover, '', title, '人民网', '%s$%s' % (title, play_id))]
        except Exception:
            pass
        return result
    
    def searchContent(self, key, quick, pg="1"):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def playerContent(self, flag, id, vipFlags):
        try:
            parts = str(id).split('|')
            media = parts[0] if len(parts) > 0 else ''
            page = parts[-1] if len(parts) > 1 else ''
            if media.startswith('http'):
                header = {'Referer': page, 'User-Agent': self.headers['User-Agent']}
                return {"parse": 0, "url": media, "header": json.dumps(header)}
            if page:
                header = {'Referer': page, 'User-Agent': self.headers['User-Agent']}
                return {"parse": 1, "url": page, "header": json.dumps(header)}
            return {"parse": 1, "url": id}
        except Exception:
            return {"parse": 1, "url": id}
    
    def _extract(self, html_text, base_url):
        scripts = "\n".join(re.findall(r'<script\b[^>]*>(.*?)</script>', html_text, re.I | re.S))
        title = self._first(self._meta(html_text, 'og:title'), self._meta(html_text, 'twitter:title'), self._heading(html_text), self._meta(html_text, 'description'), self._title_tag(html_text))
        poster = self._first(self._meta(html_text, 'og:image'), self._meta(html_text, 'twitter:image'), self._video_attr(html_text, 'poster'))
        video = self._first(self._meta(html_text, 'og:video'), self._meta(html_text, 'og:video:url'), self._source_attr(html_text), self._video_attr(html_text, 'src'))
        if not video:
            m = re.search(r"""src\s*:\s*['"]([^'"]+\.(?:mp4|m3u8)(?:\?[^'"]*)?)['"]""", scripts, re.I)
            if m:
                video = m.group(1)
        if not poster:
            m = re.search(r"""poster(?:Url)?\s*:\s*['"]([^'"]+\.(?:jpg|jpeg|png|webp)(?:\?[^'"]*)?)['"]""", scripts, re.I)
            if m:
                poster = m.group(1)
        if not video:
            m = re.search(r"""https?://[^\s"'<>]+?\.(?:mp4|m3u8)(?:\?[^\s"'<>]*)?""", html_text, re.I)
            if m:
                video = m.group(0)
        if not poster:
            m = re.search(r"""https?://[^\s"'<>]+?\.(?:jpg|jpeg|png|webp)(?:\?[^\s"'<>]*)?""", html_text, re.I)
            if m:
                poster = m.group(0)
        if not video:
            m = re.search(r'showPlayer\s*\(\s*\{\s*id\s*:\s*["\']([^"\']+\.xml)["\']', html_text)
            if m:
                video = m.group(1)
        if video and str(video).endswith('.xml'):
            video = self._player_xml(video)
        return {"title": title, "video_url": self._join(base_url, video), "cover_url": self._join(base_url, poster)}
    
    def _player_xml(self, path):
        try:
            text = self.get(self.PLAYER_API.format(path=path), timeout=10)
            m = re.search(r"""\b[\w$.]+\s*\(\s*(['"])((?:https?:)?//[^'"]+|/[^'"]+)\1""", text)
            if m:
                return m.group(2)
        except Exception:
            pass
        return ''
    
    def _meta(self, html_text, name):
        for tag in re.findall(r'<meta\b[^>]*>', html_text, re.I):
            if re.search(r'(?:property|name|itemprop)\s*=\s*["\']%s["\']' % re.escape(name), tag, re.I):
                content = self._attr(tag, 'content')
                if content:
                    return content
        return ''
    
    def _attr(self, tag, name):
        m = re.search(r'\b%s\s*=\s*["\']([^"\']*)["\']' % re.escape(name), tag, re.I)
        if m:
            return m.group(1)
        m = re.search(r'\b%s\s*=\s*([^\s"\'>]+)' % re.escape(name), tag, re.I)
        return m.group(1) if m else ''
    
    def _video_attr(self, html_text, name):
        for tag in re.findall(r'<video\b[^>]*>', html_text, re.I):
            value = self._attr(tag, name)
            if value:
                return value
        return ''
    
    def _source_attr(self, html_text):
        for tag in re.findall(r'<source\b[^>]*>', html_text, re.I):
            value = self._attr(tag, 'src') or self._attr(tag, 'data-src')
            if value:
                return value
        return ''
    
    def _heading(self, html_text):
        for name in ('h1', 'h2'):
            m = re.search(r'<%s\b[^>]*>(.*?)</%s>' % (name, name), html_text, re.I | re.S)
            if m:
                text = self._text(m.group(1))
                if text:
                    return text
        return ''
    
    def _title_tag(self, html_text):
        m = re.search(r'<title\b[^>]*>(.*?)</title>', html_text, re.I | re.S)
        return self._text(m.group(1)) if m else ''
    
    def _text(self, s):
        if s is None:
            return ''
        s = re.sub(r'<[^>]+>', ' ', str(s))
        s = unescape(s)
        return re.sub(r'\s+', ' ', s).strip()
    
    def _join(self, base_url, u):
        u = self._text(u)
        if not u:
            return ''
        try:
            return urljoin(base_url, u)
        except Exception:
            return u
    
    def _first(self, *xs):
        for x in xs:
            if x and str(x).strip():
                return x
        return ''
    
    def _clean(self, s):
        s = self.legalize(s or '')
        return s.replace('#', '').replace('$', '').strip()
