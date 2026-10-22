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
import os
import re
import json
import html
from urllib.parse import urlparse, parse_qs, urljoin

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
        return "明报"
    
    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
        })
    
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["mingpao.com"]):
                return result
            text = self.get(url)
            base_url = self._baseurl(url)
            info = self._extractvideoinfo(text, base_url)
            if not info:
                return result
            video_url = info.get('video_url') or ''
            embed_url = info.get('embed_url') or ''
            title = self.legalize(str(info.get('title') or '')).removesuffix('.').replace('$', '').replace('#', '') or info.get('file_id') or 'mingpao'
            cover = info.get('cover') or ''
            file_id = info.get('file_id') or ''
            play_id = f'{file_id}|{video_url}|{embed_url}|{url}'
            vod = self.build_vod(file_id or url, title, cover, '', title, 'Mingpao', f'{title}${play_id}')
            result['list'] = [vod]
        except Exception:
            pass
        return result
    
    def searchContent(self, key, quick, pg="1"):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split('|', 3)
            video_url = parts[1] if len(parts) > 1 else ''
            page_url = parts[3] if len(parts) > 3 else id
            if video_url.startswith('http'):
                return {"parse": 0, "url": video_url, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': page_url if page_url.startswith('http') else 'https://www.mingpao.com/'})}
            return {"parse": 1, "url": page_url}
        except Exception:
            return {"parse": 1, "url": id}
    
    def _extractvideoinfo(self, text, base_url=''):
        try:
            videos = []
            for m in re.finditer(r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.IGNORECASE | re.DOTALL):
                data = self._loads(html.unescape(m.group(1)).strip())
                for item in self._walk(data):
                    if not isinstance(item, dict):
                        continue
                    typ = item.get('@type')
                    typ = typ if isinstance(typ, list) else [typ]
                    if 'VideoObject' not in typ:
                        continue
                    content_url = self._one(item.get('contentUrl'))
                    videos.append({
                        'file_id': self._fileid(content_url),
                        'title': self._one(item.get('name')),
                        'cover': self._absurl(self._one(item.get('thumbnailUrl')), base_url),
                        'video_url': self._absurl(content_url, base_url),
                        'embed_url': self._absurl(self._one(item.get('embedUrl')), base_url)
                    })
            if not videos:
                title = None
                hm = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.IGNORECASE | re.DOTALL)
                if hm:
                    title = self._cleantext(hm.group(1))
                cover = self._metacontent(text, 'og:image') or self._metacontent(text, 'twitter:image') or self._linkimage(text)
                for m in re.finditer(r'<iframe[^>]*src\s*=\s*["\']([^"\']+)["\']', text, re.IGNORECASE | re.DOTALL):
                    embed_url = self._absurl(html.unescape(m.group(1)), base_url)
                    file_list = parse_qs(urlparse(embed_url).query).get('file')
                    video_url = self._absurl(self._one(file_list) or embed_url, base_url)
                    videos.append({
                        'file_id': self._fileid(video_url),
                        'title': title,
                        'cover': self._absurl(cover, base_url),
                        'video_url': video_url,
                        'embed_url': embed_url
                    })
            picked = None
            for v in videos:
                if not (v.get('video_url') or v.get('embed_url')):
                    continue
                if picked is None:
                    picked = v
            return picked
        except Exception:
            return None
    
    def _walk(self, obj):
        items = []
        if isinstance(obj, dict):
            items.append(obj)
            for v in obj.values():
                items.extend(self._walk(v))
        elif isinstance(obj, list):
            for v in obj:
                items.extend(self._walk(v))
        return items
    
    def _one(self, value):
        if isinstance(value, list):
            return value[0] if value else None
        return value
    
    def _absurl(self, url, base_url):
        try:
            if not url:
                return None
            return urljoin(base_url, str(url))
        except Exception:
            return url
    
    def _fileid(self, url):
        try:
            if not url:
                return None
            return os.path.splitext(os.path.basename(urlparse(str(url)).path))[0]
        except Exception:
            return None
    
    def _baseurl(self, url):
        try:
            u = url.strip()
            if '://' not in u and not u.startswith('//'):
                u = 'https://' + u
            p = urlparse(u)
            return f'{p.scheme or "https"}://{p.netloc}/'
        except Exception:
            return 'https://www.mingpao.com/'
    
    def _cleantext(self, text):
        try:
            t = re.sub(r'(?is)<(script|style)\b.*?</\1>', '', text)
            t = re.sub(r'<[^>]+>', ' ', t)
            return re.sub(r'\s+', ' ', html.unescape(t)).strip()
        except Exception:
            return text
    
    def _metacontent(self, text, name):
        try:
            for m in re.finditer(r'<meta\b[^>]*>', text, re.IGNORECASE | re.DOTALL):
                tag = m.group(0)
                pm = re.search(r'(?:property|name)\s*=\s*["\']([^"\']+)["\']', tag, re.IGNORECASE)
                cm = re.search(r'content\s*=\s*["\']([^"\']+)["\']', tag, re.IGNORECASE)
                if pm and cm and pm.group(1).lower() == name.lower():
                    return cm.group(1)
            return None
        except Exception:
            return None
    
    def _linkimage(self, text):
        try:
            for m in re.finditer(r'<link\b[^>]*>', text, re.IGNORECASE | re.DOTALL):
                tag = m.group(0)
                rm = re.search(r'rel\s*=\s*["\']image_src["\']', tag, re.IGNORECASE)
                hm = re.search(r'href\s*=\s*["\']([^"\']+)["\']', tag, re.IGNORECASE)
                if rm and hm:
                    return hm.group(1)
            return None
        except Exception:
            return None
    
    def _loads(self, text):
        try:
            try:
                return json.loads(text)
            except:
                pass
            t = re.sub(r',(\s*[}\]])', r'\1', text)
            t = re.sub(r'([{,]\s*)([A-Za-z_$][\w$]*)\s*:', r'\1"\2":', t)
            t = re.sub(r'\bTrue\b', 'true', t)
            t = re.sub(r'\bFalse\b', 'false', t)
            t = re.sub(r'\bNone\b', 'null', t)
            try:
                return json.loads(t)
            except:
                return {}
        except Exception:
            return {}
