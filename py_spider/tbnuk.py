# -*- coding: utf-8 -*-
# Ported from videodl (PolyForm Noncommercial License 1.0.0)
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor
from urllib.request import Request
from urllib.request import build_opener
from html import unescape
import json
import re
from urllib.parse import urlparse, urlencode, urljoin

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

    DOMAINS = ["tbn.uk"]
    BASE_URL = "https://watch.tbn.uk"
    STREAM_PATH = '/api/{stream_type}/stream/{stream_id}'
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    HEADERS = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "cache-control": "max-age=0",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "upgrade-insecure-requests": "1",
        "user-agent": UA,
    }

    def getName(self):
        return "TBN UK"

    def init(self, extend=""):
        self.extend = extend
        self.api_key = ''
        self.stream_url = ''
        self.headers.update({'User-Agent': self.UA})

    def homeContent(self, filter):
        return {"class": [], "list": []}

    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            url = str(url or '').strip()
            if not self.match_domain(url, self.DOMAINS):
                return result
            items = self._watch(url)
            if not items:
                items = self._shows(url)
            if not items:
                items = self._live(url)
            if not items:
                return result
            name = self._clean(items[0].get('name') or 'TBN UK')
            cover = items[0].get('cover') or ''
            plays = []
            for item in items:
                label = self._clean(item.get('title') or name)
                play_id = '%s||%s' % (self._enc(item.get('stream', '')), self._enc(item.get('page') or url))
                plays.append('%s$%s' % (label, play_id))
            vod_id = items[0].get('page') or url
            result['list'] = [self.build_vod(vod_id, name, cover, '', name, 'TBN UK', '#'.join(plays))]
        except Exception:
            pass
        return result

    def searchContent(self, key, quick, pg="1"):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def playerContent(self, flag, id, vipFlags):
        try:
            parts = str(id).split('||')
            stream = self._dec(parts[0]) if parts else ''
            page = self._dec(parts[1]) if len(parts) > 1 else ''
            if not stream.startswith('http') and page:
                try:
                    items = self._watch(page) or self._live(page)
                    if items:
                        stream = items[0].get('stream', '')
                except Exception:
                    pass
            if stream.startswith('http'):
                header = {'User-Agent': self.UA, 'Referer': page or self.BASE_URL + '/'}
                return {"parse": 0, "url": stream, "header": json.dumps(header)}
            if page:
                return {"parse": 1, "url": page, "header": json.dumps({'User-Agent': self.UA})}
            return {"parse": 1, "url": id}
        except Exception:
            return {"parse": 1, "url": id}

    def _setapiinfo(self):
        try:
            if self.api_key and self.stream_url:
                return
            html = self.get(self.BASE_URL, headers=self.HEADERS, timeout=15)
            m = re.search(r'config[^=]*=[^{]*({[^;]+});', html)
            if not m:
                return
            cfg = self._loads(m.group(1)) or {}
            api = cfg.get('api') or {}
            key = api.get('key') or ''
            endpoints = api.get('endpoints') or {}
            streams = endpoints.get('streams') or ''
            if key:
                self.api_key = key
            if streams:
                full = streams + self.STREAM_PATH
                if not full.startswith('http'):
                    full = self.BASE_URL + ('/' + full if not full.startswith('/') else full)
                self.stream_url = full
        except Exception:
            pass

    def _stream(self, stream_type, vid, url, with_url=False):
        try:
            self._setapiinfo()
            if not self.api_key or not self.stream_url:
                return ''
            params = {'key': self.api_key, 'platform': 'chrome'}
            if with_url and url:
                params['url'] = url
            api = '%s?%s' % (self.stream_url.format(stream_type=stream_type, stream_id=vid), urlencode(params))
            data = self._loads(self.post(api, timeout=15)) or {}
            resp = data.get('response')
            if isinstance(resp, str):
                resp = self._loads(resp) or {}
            if not isinstance(resp, dict):
                return ''
            if resp.get('drm'):
                return ''
            if 'not found' in str(resp.get('error', '')).lower():
                return ''
            stream = resp.get('stream') or ''
            if stream:
                return stream
            ads = resp.get('ads') or {}
            prefix = ads.get('prefix') or ''
            session = ads.get('session') or ''
            if prefix and session:
                adata = self._loads(self.post(prefix + session, timeout=15)) or {}
                manifest = adata.get('manifestUrl') or ''
                if manifest:
                    if manifest.startswith('http'):
                        return manifest
                    return prefix + manifest
        except Exception:
            pass
        return ''

    def _watch(self, url):
        try:
            base = url.split('?')[0].split('#')[0].rstrip('/')
            if '/watch/vod/' not in base and '/watch/replay/' not in base:
                return None
            item = self._watchitem(url)
            return [item] if item else None
        except Exception:
            return None

    def _live(self, url):
        try:
            base = url.split('?')[0].split('#')[0].rstrip('/')
            if '/live/' not in base:
                return None
            m = re.search(r'https?://[^/]+/live/(\d+)(?=[/?#]|$)', url)
            if not m:
                return None
            vid = m.group(1)
            html = self.get(url, headers=self.HEADERS, timeout=15)
            title = self._pagetitle(html) or 'TBN UK Live'
            cover = self._ogimage(html)
            stream = self._stream('live', vid, url, with_url=True)
            if not stream:
                return None
            return [{'name': title, 'title': title, 'stream': stream, 'page': url, 'cover': cover}]
        except Exception:
            return None

    def _watchitem(self, url, name=None, label=None, cover=None):
        try:
            m = re.search(r'https?://[^/]+/watch/(?:replay|vod)/(\d+)(?=[/?#]|$)', url)
            if not m:
                return None
            vid = m.group(1)
            html = self.get(url, headers=self.HEADERS, timeout=15)
            title = self._pagetitle(html) or 'TBN UK'
            pic = self._ogimage(html) or cover or ''
            stream = self._stream(self._streamtype(html), vid, url)
            if not stream:
                return None
            return {'name': name or title, 'title': label or title, 'stream': stream, 'page': url, 'cover': pic}
        except Exception:
            return None

    def _shows(self, url):
        try:
            base = url.split('?')[0].split('#')[0].rstrip('/')
            if '/shows/' not in base:
                return None
            html = self.get(url, headers=self.HEADERS, timeout=15)
            found = re.findall(r'"af_content"[^:]*:[^"]*"([^"]+)"', html)
            collection = found[0] if found and found[0] else urlparse(url).path.strip('/').split('/')[-1]
            items = []
            for chunk in html.split('card-body')[1:]:
                episode = self._episode(chunk)
                if not episode.get('url'):
                    continue
                ep_url = episode['url']
                if not ep_url.startswith('http'):
                    ep_url = urljoin(self.BASE_URL + '/', ep_url)
                ep_title = episode.get('title') or ep_url.split('/')[-1]
                if episode.get('episode'):
                    label = 'EP%d - %s' % (episode['episode'], ep_title)
                else:
                    label = ep_title
                item = self._watchitem(ep_url, name=collection, label=label, cover=self._ogimage(html))
                if item:
                    items.append(item)
            return items or None
        except Exception:
            return None

    def _episode(self, chunk):
        info = {'url': '', 'title': '', 'season': 0, 'episode': 0}
        try:
            anchors = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', chunk, re.S | re.I)
            for href, text in anchors:
                if '/watch/vod/' in href or '/watch/replay/' in href:
                    info['url'] = href
                    info['title'] = self._striptags(text)
                    break
            season = re.search(r'data-content-type=["\']season["\'][^>]*>(.*?)</span>', chunk, re.S | re.I)
            if season:
                m = re.search(r'season\s*(\d+)', self._striptags(season.group(1)), re.I)
                if m:
                    info['season'] = int(m.group(1))
            episode = re.search(r'data-content-type=["\']episode["\'][^>]*>(.*?)</span>', chunk, re.S | re.I)
            if episode:
                m = re.search(r'episode\s*(\d+)', self._striptags(episode.group(1)), re.I)
                if m:
                    info['episode'] = int(m.group(1))
        except Exception:
            pass
        return info

    def _streamtype(self, html):
        try:
            blocks = re.findall(r'this\.url\.params[^=]*=[^{]*({[^}]+})', html or '') or re.findall(r'programme[^{]*({[^}]+})', html or '')
            if blocks:
                found = re.findall(r"type[^:]*:[^']*'([^']+)'", blocks[0])
                if found:
                    return str(found[0]).lower()
        except Exception:
            pass
        return 'vod'

    def _pagetitle(self, html):
        try:
            m = re.search(r'<title[^>]*>(.*?)</title>', html or '', re.I | re.S)
            if m:
                return self._clean(m.group(1))
        except Exception:
            pass
        return ''

    def _ogimage(self, html):
        try:
            for m in re.finditer(r'<meta[^>]+property=["\']og:image["\'][^>]*>', html or '', re.I):
                c = re.search(r'content=["\']([^"\']*)["\']', m.group(0), re.I)
                if c and c.group(1):
                    return c.group(1)
        except Exception:
            pass
        return ''

    def _striptags(self, s):
        try:
            s = re.sub(r'<[^>]+>', '', s or '')
            return re.sub(r'\s+', ' ', s).strip()
        except Exception:
            return ''

    def _loads(self, text):
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            pass
        try:
            fixed = re.sub(r',\s*([}\]])', r'\1', text)
            fixed = fixed.replace('\\/', '/')
            return json.loads(fixed)
        except Exception:
            pass
        return None

    def _enc(self, s):
        try:
            return str(s or '').replace('|', '%7C').replace('$', '%24').replace('#', '%23')
        except Exception:
            return ''

    def _dec(self, s):
        try:
            return str(s or '').replace('%7C', '|').replace('%24', '$').replace('%23', '#')
        except Exception:
            return ''

    def _clean(self, s):
        s = self.legalize(s or '')
        return s.replace('$', '').replace('#', '').replace('|', '').strip()
