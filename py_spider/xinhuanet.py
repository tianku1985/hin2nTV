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
import html as htmlmod
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
        return "新华网"

    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
        })


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

    def _meta(self, page, key, value):
        try:
            pat = r'<meta[^>]*\b' + key + r'\s*=\s*["\']' + re.escape(value) + r'["\'][^>]*>'
            for tag in re.findall(pat, page, re.I):
                m = re.search(r'\bcontent\s*=\s*["\']([^"\']*)["\']', tag, re.I)
                if m:
                    return htmlmod.unescape(m.group(1)).strip()
        except Exception:
            pass
        return None

    def _tagtext(self, page, tag):
        try:
            m = re.search(r'<' + tag + r'\b[^>]*>(.*?)</' + tag + r'>', page, re.I | re.S)
            if m:
                return htmlmod.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()
        except Exception:
            pass
        return None

    def _classtext(self, page, cls):
        try:
            pat = r'<[^>]*class\s*=\s*["\'][^"\']*\b' + re.escape(cls) + r'\b[^"\']*["\'][^>]*>(.*?)</'
            m = re.search(pat, page, re.I | re.S)
            if m:
                return htmlmod.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()
        except Exception:
            pass
        return None

    def _idtext(self, page, iid):
        try:
            pat = r'<[^>]*id\s*=\s*["\']' + re.escape(iid) + r'["\'][^>]*>(.*?)</'
            m = re.search(pat, page, re.I | re.S)
            if m:
                return htmlmod.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()
        except Exception:
            pass
        return None

    def _anyattr(self, page, attr):
        try:
            for seg in re.findall(r'<[^>]+>', page):
                m = re.search(r'\b' + re.escape(attr) + r'\s*=\s*["\']([^"\']*)["\']', seg, re.I)
                if m and m.group(1):
                    return htmlmod.unescape(m.group(1)).strip()
        except Exception:
            pass
        return None

    def _tagattr(self, page, tag, attr):
        try:
            for seg in re.findall(r'<' + tag + r'\b[^>]*>', page, re.I):
                m = re.search(r'\b' + re.escape(attr) + r'\s*=\s*["\']([^"\']*)["\']', seg, re.I)
                if m and m.group(1):
                    return htmlmod.unescape(m.group(1)).strip()
        except Exception:
            pass
        return None

    def _extractmedia(self, base_url, page):
        title = self._meta(page, 'property', 'og:title')
        if not title:
            title = self._meta(page, 'name', 'title')
        if not title:
            title = self._tagtext(page, 'h1')
        if not title:
            title = self._classtext(page, 'title')
        if not title:
            title = self._tagtext(page, 'title')
        if title:
            doctitle = self._tagtext(page, 'title')
            if doctitle and title == doctitle:
                title = re.sub(r'[-_｜|].*$', '', title).strip()
        video_url = self._tagattr(page, 'source', 'src')
        if not video_url:
            video_url = self._tagattr(page, 'video', 'src')
        if not video_url:
            video_url = self._meta(page, 'property', 'og:video')
        if not video_url:
            video_url = self._meta(page, 'property', 'og:video:url')
        if not video_url:
            video_url = self._anyattr(page, 'video_src')
        if not video_url:
            fs = self._idtext(page, 'fontsize')
            if fs and fs.startswith(('http://', 'https://')):
                video_url = fs
        if video_url:
            video_url = urljoin(base_url, video_url)
        cover = self._meta(page, 'property', 'og:image')
        if not cover:
            cover = self._meta(page, 'name', 'twitter:image')
        if not cover:
            cover = self._anyattr(page, 'poster')
        if not cover:
            cover = self._tagattr(page, 'img', 'src')
        if cover:
            cover = urljoin(base_url, cover)
        video_id = self._meta(page, 'name', 'contentid')
        if not video_id:
            for k in ('data-video-id', 'data-id', 'vid'):
                video_id = self._anyattr(page, k)
                if video_id:
                    break
        if not video_id and video_url:
            m = re.search(r"/([A-Za-z0-9_-]{10,})\.(mp4|m3u8)", video_url)
            if m:
                video_id = m.group(1)
        return {'title': title, 'video_url': video_url, 'cover_url': cover, 'video_id': video_id}

    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["news.cn", "xinhuanet.com"]):
                return result
            page = self.get(url, timeout=15)
            raw = self._extractmedia(urljoin(url, '/'), page)
            media = raw.get('video_url') or ''
            title = raw.get('title') or raw.get('video_id') or urlparse(url).path.strip('/').split('/')[-1]
            cover = raw.get('cover_url') or ''
            title = self.legalize(title).replace('$', '').replace('#', '')
            play_id = '%s|%s|%s' % ('1' if media else '0', self._enc(media), self._enc(url))
            vid = raw.get('video_id') or title
            result['list'] = [self.build_vod(vid, title, cover, '', title, 'XinhuaNet', '%s$%s' % (title, play_id))]
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
                    'Referer': page})}
            return {"parse": 1, "url": page or id}
        except Exception:
            return {"parse": 1, "url": id}
