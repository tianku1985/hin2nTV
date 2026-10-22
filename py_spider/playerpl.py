from urllib.parse import quote
from urllib.parse import unquote
# -*- coding: utf-8 -*-
# Ported from videodl (PolyForm Noncommercial License 1.0.0)
# LIMITATION: Player.pl streams are protected with Widevine DRM (CDM), which can not
# be emulated in a pure python TVBox spider. Only metadata (title/cover) is fetched
# over plain HTTP, playback is delegated to TVBox with parse=1 (page url).
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

    PLATFORM = "BROWSER"
    TRANSLATE_URL = 'https://player.pl/playerapi/item/translate'
    PLAYLIST_URL = 'https://player.pl/playerapi/item/{item_id}/playlist'
    SERIAL_URL = 'https://player.pl/playerapi/product/vod/serial/{show_id}'
    SEASONS_URL = 'https://player.pl/playerapi/product/vod/serial/{show_id}/season/list'
    EPISODES_URL = 'https://player.pl/playerapi/product/vod/serial/{show_id}/season/{season_id}/episode/list'
    DOMAINS = ["player.pl"]
    def getName(self):
        return "Player.pl"
    
    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://player.pl',
            'Referer': 'https://player.pl/'
        })
    
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, self.DOMAINS):
                return result
            clean = url.split('?')[0].split('#')[0].rstrip('/')
            if ('/filmy-online' in clean) or re.findall(r',S\d+E\d+,\d+$', clean.split('/')[-1]):
                vods = self._single_vod(url)
            else:
                vods = self._series_vods(url)
            if not vods:
                vods = self._page_vod(url)
            result['list'] = vods
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
                return {"parse": 0, "url": media, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': 'https://player.pl/'})}
            return {"parse": 1, "url": page or media, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': 'https://player.pl/'})}
        except Exception:
            return {"parse": 1, "url": id}
    
    def _page_vod(self, url):
        vods = []
        try:
            html = self.get(url)
            title = self._page_title(html)
            cover = self._page_cover(html)
            title = (title or url).replace('$', '').replace('#', '')
            play_id = f'|{url}'
            vods.append(self.build_vod(url, title, cover, '', title, 'Player.pl', f'{title}${play_id}'))
        except Exception:
            pass
        return vods
    
    def _single_vod(self, url):
        vods = []
        try:
            clean = url.split('?')[0].split('#')[0].rstrip('/')
            vid = clean.split(',')[-1]
            item_id = self._translate(vid, 'articleId')
            details = self._playlist(item_id) if item_id else None
            title, cover, media = self._parse_details(details)
            html = ''
            try:
                html = self.get(url)
            except Exception:
                html = ''
            if not title:
                title = self._page_title(html)
            if not cover:
                cover = self._page_cover(html)
            title = (title or vid).replace('$', '').replace('#', '')
            play_id = f'{media}|{url}'
            vods.append(self.build_vod(vid, title, cover, '', title, 'Player.pl', f'{title}${play_id}'))
        except Exception:
            pass
        return vods
    
    def _series_vods(self, url):
        vods = []
        try:
            clean = url.split('?')[0].split('#')[0].rstrip('/')
            program_id = clean.split(',')[-1]
            show_id = self._translate(program_id, 'programId')
            if not show_id:
                return vods
            serial = self._get(self.SERIAL_URL.format(show_id=show_id))
            title = self._find_value(serial, 'title') or program_id
            cover = self._find_value(serial, 'image') or self._find_value(serial, 'thumbnail') or ''
            plays = []
            seasons = self._get(self.SEASONS_URL.format(show_id=show_id))
            if not isinstance(seasons, list):
                seasons = []
            seasons = sorted(seasons, key=lambda s: s.get('number') or 0 if isinstance(s, dict) else 0)
            for season in seasons:
                if not isinstance(season, dict) or not season.get('id'):
                    continue
                episodes = self._get(self.EPISODES_URL.format(show_id=show_id, season_id=season['id']))
                if not isinstance(episodes, list):
                    episodes = []
                episodes = sorted(episodes, key=lambda e: e.get('episode') or 0 if isinstance(e, dict) else 0)
                for episode in episodes:
                    if not isinstance(episode, dict):
                        continue
                    share = episode.get('shareUrl') or episode.get('share_url') or episode.get('url') or ''
                    if not share:
                        continue
                    ep_title = episode.get('title') or episode.get('name') or ''
                    ep_no = episode.get('episode') or episode.get('number') or ''
                    label = f'S{season.get("number") or "?"}E{ep_no} {ep_title}'.strip()
                    label = self.legalize(label).replace('$', '').replace('#', '')
                    plays.append(f'{label}$|{share}')
            if not plays:
                return vods
            title = self.legalize(title).replace('$', '').replace('#', '')
            vods.append(self.build_vod(program_id, title, cover, '', title, 'Player.pl', '#'.join(plays)))
        except Exception:
            pass
        return vods
    
    def _translate(self, vid, key):
        try:
            params = {key: vid, 'platform': self.PLATFORM}
            raw = self.fetch_json(f'{self.TRANSLATE_URL}?{urlencode(params)}', headers={'Origin': 'https://player.pl', 'Referer': 'https://player.pl/'})
            if isinstance(raw, dict):
                return str(raw.get('id') or '')
        except Exception:
            pass
        return ''
    
    def _playlist(self, item_id):
        try:
            params = {'type': 'MOVIE', 'platform': self.PLATFORM}
            raw = self.fetch_json(f'{self.PLAYLIST_URL.format(item_id=item_id)}?{urlencode(params)}', headers={'Origin': 'https://player.pl', 'Referer': 'https://player.pl/'})
            if isinstance(raw, dict):
                return raw
        except Exception:
            pass
        return None
    
    def _get(self, url):
        try:
            params = {'platform': self.PLATFORM}
            raw = self.fetch_json(f'{url}?{urlencode(params)}', headers={'Origin': 'https://player.pl', 'Referer': 'https://player.pl/'})
            return raw
        except Exception:
            return None
    
    def _parse_details(self, details):
        title, cover, media = '', '', ''
        try:
            if not isinstance(details, dict):
                return title, cover, media
            content_info = safe_extract(details, ['movie', 'info'], {}) or {}
            nl_data = safe_extract(details, ['movie', 'stats', 'nl_data'], {}) or {}
            series_title = content_info.get('series_title') or nl_data.get('program')
            video_title = " - ".join(dict.fromkeys(filter(None, [series_title, nl_data.get('title')])))
            title = self.legalize(video_title)
            cover = safe_extract(details, ['movie', 'info', 'media', 'thumbnail_big'], '') or safe_extract(details, ['movie', 'info', 'media', 'poster'], '') or ''
            protections = safe_extract(details, ['movie', 'video', 'protections'], {}) or {}
            sources = safe_extract(details, ['movie', 'video', 'sources'], {}) or {}
            if not protections:
                for name in ('smooth', 'dash', 'hls'):
                    u = sources.get(name, {}).get('url') if isinstance(sources.get(name), dict) else None
                    if u and str(u).startswith('http'):
                        media = str(u)
                        break
                if not media:
                    for _, value in sources.items():
                        u = value.get('url') if isinstance(value, dict) else None
                        if u and str(u).startswith('http'):
                            media = str(u)
                            break
        except Exception:
            pass
        return title, cover, media
    
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
        return ''
    
    def _find_value(self, obj, key):
        try:
            if isinstance(obj, dict):
                if key in obj:
                    return obj[key]
                for v in obj.values():
                    r = self._find_value(v, key)
                    if r is not None:
                        return r
            elif isinstance(obj, list):
                for v in obj:
                    r = self._find_value(v, key)
                    if r is not None:
                        return r
        except Exception:
            pass
        return None
