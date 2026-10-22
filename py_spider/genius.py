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

    UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
    DEFAULT_ACCOUNT_ID = '4863540648001'
    DEFAULT_PLAYER_ID = 'S1ZcmcOC1x'
    PLAYER_KEYS = [
        'brightcove_standard_web_player_id',
        'brightcove_standard_no_autoplay_web_player_id',
        'brightcove_modal_web_player_id',
        'brightcove_song_story_web_player_id'
    ]

    def getName(self):
        return "Genius"

    def init(self, extend=""):
        self.extend = extend
        self.headers.update({'User-Agent': self.UA})


    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def _searchdictbykey(self, obj, target_key):
        results = []
        try:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    results += ([v] if k == target_key else []) + self._searchdictbykey(v, target_key)
            elif isinstance(obj, list):
                for item in obj:
                    results.extend(self._searchdictbykey(item, target_key))
        except Exception:
            pass
        return results

    def _unescapestring(self, text):
        try:
            text = text.replace("\\'", "'").replace('\\"', '"').replace('\\/', '/').replace('\\\\', '\\')
            return text
        except Exception:
            return text

    def _extractappconfig(self, html):
        try:
            m = re.search(r"var\s+APP_CONFIG\s*=\s*JSON\.parse\('(?P<json>.*?)'\);", html, re.S)
            if not m:
                return {}
            return json.loads(self._unescapestring(m.group('json')))
        except Exception:
            return {}

    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["genius.com"]):
                return result
            m = re.compile(r'https?://(?:www\.)?genius\.com/(?:videos|(?P<article>a))/(?P<id>[^?/#]+)').match(url)
            if not m:
                return result
            title = m.group('id')
            html = self.get(url, timeout=15)
            video_id = ''
            for p in [r'["\']brightcove_video_id["\']\s*[:,]\s*(?:\[\s*)?["\'](\d{6,})["\']',
                      r'"provider"\s*:\s*"brightcove"[^}]*?"provider_id"\s*:\s*"(\d{6,})"',
                      r'brightcove_video_id[^0-9]+(\d{6,})']:
                mm = re.search(p, html, re.S)
                if mm:
                    video_id = mm.group(1)
                    break
            if not video_id:
                return result
            app_config = self._extractappconfig(html)
            account_id = app_config.get('brightcove_account_id') or self.DEFAULT_ACCOUNT_ID
            player_id = ''
            for key in self.PLAYER_KEYS:
                found = self._searchdictbykey(app_config, key)
                if found:
                    player_id = found[0]
                    break
            if not player_id:
                player_id = self.DEFAULT_PLAYER_ID
            cover = ''
            mm = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
            if mm:
                cover = mm.group(1)
            play_id = '%s|%s|%s|%s' % (video_id, account_id, player_id, url)
            title = self.legalize(title).replace('$', '')
            result['list'] = [self.build_vod(video_id, title, cover, '', title, 'Genius', '%s$%s' % (title, play_id))]
        except Exception:
            pass
        return result

    def searchContent(self, key, quick, pg="1"):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    def _fetchpolicykey(self, player_url):
        try:
            html = self.get(player_url, timeout=15)
            m = re.search(r'"policyKey"\s*:\s*"([^"]+)"', html) or re.search(r'policyKey\s*:\s*"([^"]+)"', html)
            if m:
                return m.group(1)
            m = re.search(r'<script[^>]+src="([^"]*index(?:\.min)?\.js[^"]*)"[^>]*>', html, re.I)
            if not m:
                return ''
            js = self.get(urljoin(player_url, self._unescapestring(m.group(1))), timeout=15)
            m = re.search(r'"policyKey"\s*:\s*"([^"]+)"', js) or re.search(r'policyKey\s*:\s*"([^"]+)"', js)
            return m.group(1) if m else ''
        except Exception:
            return ''

    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split('|')
            video_id = parts[0] if parts else ''
            account_id = parts[1] if len(parts) > 1 else self.DEFAULT_ACCOUNT_ID
            player_id = parts[2] if len(parts) > 2 else self.DEFAULT_PLAYER_ID
            page_url = parts[-1]
            if not video_id:
                return {"parse": 1, "url": page_url}
            player_url = 'https://players.brightcove.net/%s/%s_default/index.html?videoId=%s' % (account_id, player_id, video_id)
            policy_key = self._fetchpolicykey(player_url)
            if not policy_key:
                return {"parse": 1, "url": page_url}
            api_url = 'https://edge.api.brightcove.com/playback/v1/accounts/%s/videos/%s' % (account_id, video_id)
            headers = {
                'User-Agent': self.UA,
                'Accept': 'application/json;pk=%s' % policy_key,
                'BCOV-Policy': policy_key,
                'Origin': 'https://players.brightcove.net',
                'Referer': player_url
            }
            raw_data = json.loads(self.get(api_url, headers=headers, timeout=15))
            formats = []
            for s in safe_extract(raw_data, ['sources'], []) or []:
                if not isinstance(s, dict) or not s.get('src'):
                    continue
                formats.append({'url': s.get('src'), 'height': s.get('height') or 0, 'bitrate': s.get('avg_bitrate') or s.get('bitrate') or 0})
            formats.sort(key=lambda f: (f.get('height') or 0, f.get('bitrate') or 0), reverse=True)
            if formats:
                return {"parse": 0, "url": formats[0]['url'], "header": json.dumps(headers)}
            return {"parse": 1, "url": page_url}
        except Exception:
            return {"parse": 1, "url": id}
