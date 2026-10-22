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

    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
    BOT_COOKIE = '__tst_status=4192826146#; EO_Bot_Ssid=2980118528'

    def getName(self):
        return "环球网"

    def init(self, extend=""):
        self.extend = extend
        self.headers.update({'User-Agent': self.UA})

    def homeContent(self, filter):
        return {"class": [], "list": []}

    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def _textarea(self, html_text, cls):
        try:
            m = re.search(r'<textarea[^>]*class=["\'][^"\']*%s[^"\']*["\'][^>]*>(.*?)</textarea>' % cls, html_text, re.S | re.I)
            return m.group(1) if m else ''
        except Exception:
            return ''

    def _metatag(self, html_text, prop):
        try:
            m = re.search(r'<meta[^>]+property=["\']%s["\'][^>]+content=["\']([^"\']*)["\']' % prop, html_text, re.I)
            if not m:
                m = re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+property=["\']%s["\']' % prop, html_text, re.I)
            return m.group(1) if m else ''
        except Exception:
            return ''

    def _normurl(self, url, base_url):
        try:
            url = (url or '').strip()
            if not url:
                return ''
            if url.startswith('//'):
                return 'https:' + url
            return urljoin(base_url, url)
        except Exception:
            return url

    def _extractvideoinfo(self, base_url, html_text):
        try:
            content = html.unescape(self._textarea(html_text, 'article-content'))
            title = self._textarea(html_text, 'article-title').strip() or self._metatag(html_text, 'og:title')
            m = re.search(r'<title>(.*?)</title>', html_text, re.S | re.I)
            if not title and m:
                title = m.group(1).strip()
            video_url, poster = '', ''
            mm = re.search(r'<video[^>]*>', content, re.S | re.I)
            if not mm:
                mm = re.search(r'<video[^>]*>', html_text, re.S | re.I)
            if mm:
                tag = mm.group(0)
                src = re.search(r'src=["\']([^"\']+)["\']', tag, re.I)
                video_url = self._normurl(src.group(1) if src else '', base_url)
                pos = re.search(r'poster=["\']([^"\']+)["\']', tag, re.I)
                poster = self._normurl(pos.group(1) if pos else '', base_url)
            if not video_url:
                mm = re.search(r'<source[^>]*src=["\']([^"\']+)["\']', content, re.S | re.I)
                if mm:
                    video_url = self._normurl(mm.group(1), base_url)
            cover = poster or self._textarea(html_text, 'article-cover').strip() or self._metatag(html_text, 'og:image')
            cover = self._normurl(cover, base_url)
            return {'title': title, 'video_url': video_url, 'cover_url': cover}
        except Exception:
            return {'title': '', 'video_url': '', 'cover_url': ''}

    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["huanqiu.com"]):
                return result
            vid = urlparse(url).path.strip('/').split('/')[-1].removesuffix('.html').removesuffix('.htm')
            html_text = self.get(url, timeout=15)
            base_url = '%s://%s' % (urlparse(url).scheme, urlparse(url).netloc)
            raw_data = self._extractvideoinfo(base_url, html_text)
            if not raw_data.get('title') and not raw_data.get('video_url'):
                html_text = self.get(url, headers={'Cookie': self.BOT_COOKIE}, timeout=15)
                raw_data = self._extractvideoinfo(base_url, html_text)
            title = raw_data.get('title') or vid
            cover = raw_data.get('cover_url') or ''
            play_id = '%s|%s' % (raw_data.get('video_url') or '', url)
            title = self.legalize(title).replace('$', '')
            result['list'] = [self.build_vod(vid, title, cover, '', title, 'HuanQiu', '%s$%s' % (title, play_id))]
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
                return {"parse": 0, "url": playurl, "header": json.dumps({'User-Agent': self.UA, 'Referer': 'https://www.huanqiu.com/'})}
            return {"parse": 1, "url": page_url}
        except Exception:
            return {"parse": 1, "url": id}
