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
import html
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
        return "MyVideo"
    
    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Referer': 'https://www.myvideo.ge/'
        })
    
    def homeContent(self, filter):
        return {"class": [], "list": []}
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["myvideo.ge"]):
                return result
            m = re.compile(r"https?://(?:www\.)?myvideo\.ge/v/(?P<id>[0-9]+)").match(url)
            video_id = m.group('id') if m else (urlparse(url).path.strip('/').split('/')[-1] or url)
            webpage = self.get(url, timeout=20)
            title = self._searchmeta(webpage, 'og:title') or self._cleanhtml(self._elementbyclass('my_video_title', webpage)) or self._cleantext(self._titleof(webpage)) or video_id
            title = self.legalize(str(title)).removesuffix('.').replace('$', '').replace('#', '') or video_id
            sources = self._getsources(webpage)
            download_url = ''
            for item in sources:
                if not isinstance(item, dict):
                    continue
                cand = item.get('file') or item.get('src')
                if cand:
                    download_url = str(cand)
                    break
            if download_url:
                download_url = urljoin(url, download_url)
            cover = self._searchmeta(webpage, 'og:image') or ''
            play_id = f'{video_id}|{download_url}|{url}'
            vod = self.build_vod(video_id or url, title, cover, '', title, 'MyVideo', f'{title}${play_id}')
            result['list'] = [vod]
        except Exception:
            pass
        return result
    
    def searchContent(self, key, quick, pg="1"):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split('|', 2)
            download_url = parts[1] if len(parts) > 1 else ''
            page_url = parts[2] if len(parts) > 2 else id
            if download_url.startswith('http'):
                return {"parse": 0, "url": download_url, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': 'https://www.myvideo.ge/'})}
            return {"parse": 1, "url": page_url}
        except Exception:
            return {"parse": 1, "url": id}
    
    def _getsources(self, webpage):
        try:
            m = re.search(r"""(?s)jwplayer\s*\(\s*['"]mvplayer['"]\s*\)\s*\.\s*setup\s*\(.*?""" r"""\bsources\s*:\s*(\[.*?])\s*[,});]""", webpage)
            if not m:
                m = re.search(r"""(?s)["']?sources["']?\s*:\s*(\[.*?])""", webpage)
            if m:
                raw = m.group(1)
                parsed = self._jsarraytopython(raw)
                if isinstance(parsed, list):
                    formats = [x for x in parsed if isinstance(x, dict)]
                    if formats:
                        return formats
                return self._fallbackparsesources(raw)
            return self._fallbackparsesources(webpage)
        except Exception:
            return []
    
    def _jsarraytopython(self, raw):
        try:
            text = re.sub(r"(?s)/\*.*?\*/|(?<![:/])//[^\n\r]*", "", raw).strip()
            text = re.sub(r"([{,]\s*)([A-Za-z_$][\w$-]*)\s*:", r'\1"\2":', text)
            text = re.sub(r",\s*([}\]])", r"\1", text)
            try:
                return json.loads(text)
            except:
                pass
            py_text = re.sub(r"\btrue\b", "True", text)
            py_text = re.sub(r"\bfalse\b", "False", py_text)
            py_text = re.sub(r"\bnull\b", "None", py_text)
            try:
                return json.loads(py_text.replace("'", '"'))
            except:
                return None
        except Exception:
            return None
    
    def _fallbackparsesources(self, raw):
        try:
            sources = []
            for obj in re.findall(r"{(.*?)}", raw, flags=re.S):
                m_file = re.search(r"\b(?:file|src)\s*:\s*(['\"])(.*?)\1", obj, flags=re.S)
                if not m_file:
                    continue
                m_label = re.search(r"\b(?:label|format_id)\s*:\s*(['\"])(.*?)\1", obj, flags=re.S)
                m_type = re.search(r"\btype\s*:\s*(['\"])(.*?)\1", obj, flags=re.S)
                sources.append({"file": m_file.group(2), "label": m_label.group(2) if m_label else None, "type": m_type.group(2) if m_type else None})
            return sources
        except Exception:
            return []
    
    def _searchmeta(self, webpage, name):
        try:
            pattern = (r"<meta\b"
                       rf"(?=[^>]*(?:property|name)\s*=\s*['\"]{re.escape(name)}['\"])"
                       rf"(?=[^>]*content\s*=\s*['\"]([^'\"]+)['\"])"
                       r"[^>]*>")
            m = re.search(pattern, webpage, flags=re.I | re.S)
            if not m:
                return None
            return html.unescape(str(m.group(1))).strip()
        except Exception:
            return None
    
    def _elementbyclass(self, class_name, webpage):
        try:
            pattern = (r"<(?P<tag>[a-zA-Z0-9]+)\b"
                       rf"(?=[^>]*\bclass\s*=\s*(['\"])[^'\"]*\b{re.escape(class_name)}\b[^'\"]*\2)"
                       r"[^>]*>(?P<content>.*?)</(?P=tag)>")
            m = re.search(pattern, webpage, flags=re.I | re.S)
            return m.group('content') if m else None
        except Exception:
            return None
    
    def _titleof(self, webpage):
        try:
            m = re.search(r"<title\b[^>]*>([^<]+)</title\b", webpage, flags=re.I | re.S)
            return m.group(1) if m else None
        except Exception:
            return None
    
    def _cleanhtml(self, text):
        try:
            if not text:
                return None
            t = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", text)
            t = re.sub(r"<[^>]+>", " ", t)
            t = re.sub(r"\s+", " ", html.unescape(t)).strip()
            return t or None
        except Exception:
            return None
    
    def _cleantext(self, text):
        try:
            if not text:
                return None
            return re.sub(r"\s+", " ", html.unescape(str(text))).strip() or None
        except Exception:
            return None
