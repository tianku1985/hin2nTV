from urllib.parse import unquote
# -*- coding: utf-8 -*-
# Ported from videodl (PolyForm Noncommercial License 1.0.0)
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor
from urllib.request import Request
from urllib.request import build_opener
from html import unescape
import json
import re
import math
import time
import random
import hashlib
from urllib.parse import urlparse, quote, urlencode

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

    VIDEO_URL_PATS = [re.compile(r'^https?://www\.1905\.com/(?:vod|video)/play/(\d+)\.shtml', re.IGNORECASE),
                      re.compile(r'^https?://www\.1905\.com/mdb/film/(\d+)/?', re.IGNORECASE),
                      re.compile(r'^https?://vip\.1905\.com/play/(\d+)\.shtml', re.IGNORECASE)]
    M1905_DEFINITION = {'free': ['uhd', 'hd', 'sd'], 'vip': ['v1080pm3u8', 'ipad800kbm3u8', 'm3u8ipad', 'm3u8iphone']}
    M1905_DEFN_MAP_I2S = {'free': {'uhd': 'shd', 'hd': 'hd', 'sd': 'sd'}, 'vip': {'v1080pm3u8': 'fhd', 'ipad800kbm3u8': 'shd', 'm3u8ipad': 'hd', 'm3u8iphone': 'sd'}}
    M1905_DEFN_MAP_S2I = {'free': {'dolby': 'uhd', 'suhd': 'uhd', 'hdr10': 'uhd', 'uhd': 'uhd', 'fhd': 'uhd', 'shd': 'uhd', 'hd': 'hd', 'sd': 'sd'}, 'vip': {'dolby': 'v1080pm3u8', 'suhd': 'v1080pm3u8', 'hdr10': 'v1080pm3u8', 'uhd': 'v1080pm3u8', 'fhd': 'v1080pm3u8', 'shd': 'ipad800kbm3u8', 'hd': 'm3u8ipad', 'sd': 'm3u8iphone'}}
    SD_CONF_PAT_RE = re.compile(r"(?:VODCONFIG|VIDEOCONFIG).*vid\s*:\s*\"(?P<vid>\d+)\".*?(?<!vip)title\s*:\s*\"(?P<title>.*?)\".*?apikey\s*:\s*\"(?P<apikey>.*?)\"", re.MULTILINE | re.DOTALL | re.IGNORECASE)
    SD_YEAR_RE = re.compile(r"playerBox-info-year.*?\(\s*(\d+)\s*\)", re.MULTILINE | re.DOTALL | re.IGNORECASE)
    HD_MV_CONF_PAT_RE = re.compile(r"movie-title\s*\"\s*>(?P<title>[^<]+)</h1>.*?年份[^\d]+(?P<year>\d+).*?www\.1905\.com/mdb/film/(?P<cover_id>\d+)", re.MULTILINE | re.DOTALL | re.IGNORECASE)
    HD_TV_CONF_PAT_RE = re.compile(r"(?<!<!--)<h4\s+class=\"tv_title\">(?P<title>[^<]+)</h4>.*?年份[^\d]+(?P<year>\d+).+?CONFIG\['vipid'\][^\d]+(?P<cover_id>\d+)", re.MULTILINE | re.DOTALL | re.IGNORECASE)
    HD_TV_COVER_RE = re.compile(r"<div\s+id=\"dramaList\">.+?(?P<dramalist><ul\s+.*?</ul>)\s*</div>", re.MULTILINE | re.DOTALL | re.IGNORECASE)
    HD_TV_EPISODE_RE = re.compile(r"<li.+?is_free=\"(?P<free>\d)\".+?vip\.1905\.com/play/(?P<vid>\d+)\.shtml[^\d]+(?P<ep>\d+).+?</li>", re.MULTILINE | re.DOTALL | re.IGNORECASE)
    COVER_YEAR_RE = re.compile(r"header-wrapper-h1.*?\(\s*(\d+)\s*\)", re.MULTILINE | re.DOTALL | re.IGNORECASE)
    ONLINE_COVER_RE = re.compile(r"class\s*=\s*\"\s*watch-online.+?正片.+?(<ul\s+class\s*=\s*\"watch-online-list.*?</ul>)", re.MULTILINE | re.DOTALL | re.IGNORECASE)
    ONLINE_EPISODE_RE = re.compile(r"<a\s+href\s*=\s*\"([^\"]+)\"\s+.*?class=\"online-list-time\s*\">(.*?)</span>", re.MULTILINE | re.DOTALL | re.IGNORECASE)
    APP_ID = "dde3d61a0411511d"
    VIDEO_COVER_FORMAT = "https://www.1905.com/mdb/film/{}/video"
    PROFILE_CONFIG_URL = "https://profile.m1905.com/mvod/getVideoinfo.php"
    VIP_CONFIG_URL = "https://vip.1905.com/playerhtml5/formal"
    
    def getName(self):
        return "1905电影网"
    
    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Connection': 'keep-alive'
        })
    
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["1905.com"]):
                return result
            cover_info = self._getvideocoverinfo(url)
            if not cover_info:
                return result
            title = self.legalize(str(cover_info.get('title') or '')).removesuffix('.').replace('$', '').replace('#', '') or '1905'
            cover = cover_info.get('image_url') or ''
            normal_ids = cover_info.get('normal_ids') or []
            plays = []
            for idx, normal_id in enumerate(normal_ids):
                playlist = ''
                try:
                    self._updatevideodwnldinfo(normal_id)
                    defns = normal_id.get('defns') or []
                    if defns:
                        playlist = list(defns[0].values())[0]
                except:
                    playlist = ''
                if not isinstance(playlist, str):
                    playlist = ''
                ep = normal_id.get('E') or (idx + 1)
                name = f'EP{ep}' if len(normal_ids) > 1 else '播放'
                play_id = f"{normal_id.get('V', '')}|{ep}|{playlist}|{normal_id.get('url', '')}"
                plays.append(f'{name}${play_id}')
            if not plays:
                return result
            play_url = '#'.join(plays)
            vod = self.build_vod(str(cover_info.get('url') or url), title, cover, '', title, 'M1905', play_url)
            result['list'] = [vod]
        except Exception:
            pass
        return result
    
    def searchContent(self, key, quick, pg="1"):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split('|', 3)
            playlist = parts[2] if len(parts) > 2 else ''
            page_url = parts[3] if len(parts) > 3 else ''
            if playlist.startswith('http'):
                return {"parse": 0, "url": playlist, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': 'https://www.1905.com/'})}
            return {"parse": 1, "url": page_url or id}
        except Exception:
            return {"parse": 1, "url": id}
    
    def _randomstring(self):
        try:
            out = []
            for c in "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx":
                n = math.floor(16 * random.random())
                if c == "x":
                    out.append("{:x}".format(n))
                elif c == "y":
                    out.append("{:x}".format((3 & n) | 8))
                else:
                    out.append(c)
            return ''.join(out)
        except Exception:
            return '00000000-0000-4000-8000-000000000000'
    
    def _randomplayerid(self):
        try:
            return self._randomstring().replace('-', '')[5:20]
        except Exception:
            return ''
    
    def _signature(self, params, appid=None):
        try:
            appid = appid or self.APP_ID
            query = ""
            for k in sorted(params.keys()):
                if k != "signature":
                    q = k + "=" + quote(str(params[k]), safe="")
                    query += "&" + q if query else q
            return hashlib.sha1((query + "." + appid).encode("utf-8")).hexdigest()
        except Exception:
            return ''
    
    def _getcoverinfosd(self, epurl):
        try:
            text = self.get(epurl)
            year = ""
            image_url = ''
            m = re.search(r'thumb\s*:\s*"(.*?)"', text)
            if m:
                image_url = m.group(1)
            year_match = self.SD_YEAR_RE.search(text)
            if year_match:
                year = year_match.group(1)
                conf_match = self.SD_CONF_PAT_RE.search(text[year_match.end(0):])
            else:
                conf_match = self.SD_CONF_PAT_RE.search(text)
            if not conf_match:
                return None
            api_key = conf_match.group('apikey')
            cover_id = ''
            cover_id_match = re.search(r"mdbfilmid\s*:\s*\"(\d+)\"", conf_match.group(0), flags=re.MULTILINE | re.DOTALL | re.IGNORECASE)
            if cover_id_match:
                cover_id = cover_id_match.group(1)
            return {'image_url': image_url, 'title': conf_match.group('title'), 'year': year, 'cover_id': cover_id, 'type': 'MOV', 'api_key': api_key,
                    'normal_ids': [dict(V=conf_match.group('vid'), E=1, defns={}, free=True, vip=False, url=epurl)]}
        except Exception:
            return None
    
    def _getcoverinfohd(self, epurl):
        try:
            text = self.get(epurl)
            image_url = self._metacontent(text, 'og:image')
            conf_match = self.HD_MV_CONF_PAT_RE.search(text)
            if conf_match:
                return {'image_url': image_url, 'title': conf_match.group('title'), 'year': conf_match.group('year'), 'cover_id': conf_match.group('cover_id'), 'type': 'MOV', 'api_key': '',
                        'normal_ids': [dict(V=epurl.split('/')[-1].split('.')[0], E=1, defns={}, free=False, vip=True, url=epurl)]}
            cover_match = self.HD_TV_COVER_RE.search(text)
            if not cover_match:
                return None
            conf_match = self.HD_TV_CONF_PAT_RE.search(text[cover_match.end(0):])
            episodes_match = list(self.HD_TV_EPISODE_RE.finditer(cover_match.group('dramalist')))
            if not (conf_match and episodes_match):
                return None
            normal_ids = []
            for mo in episodes_match:
                try:
                    normal_ids.append(dict(V=mo.group('vid'), E=int(mo.group('ep')), defns={}, free=bool(int(mo.group('free'))), vip=True, url="https://vip.1905.com/play/%s.shtml" % mo.group('vid')))
                except:
                    continue
            return {'image_url': image_url, 'title': conf_match.group('title'), 'year': conf_match.group('year'), 'cover_id': conf_match.group('cover_id'), 'type': 'TV', 'api_key': '', 'normal_ids': normal_ids}
        except Exception:
            return None
    
    def _getcoverinfo(self, cvurl):
        try:
            text = self.get(cvurl)
            year = ''
            urls = None
            year_match = self.COVER_YEAR_RE.search(text)
            if year_match:
                year = year_match.group(1)
                cover_match = self.ONLINE_COVER_RE.search(text[year_match.end(0):])
            else:
                cover_match = self.ONLINE_COVER_RE.search(text)
            if cover_match:
                defns = {"VIP免广告": "hd", "免费": "sd"}
                urls = {}
                for mo in self.ONLINE_EPISODE_RE.finditer(cover_match.group(1)):
                    key = defns.get(mo.group(2).strip())
                    if key:
                        urls[key] = mo.group(1)
            return year, urls
        except Exception:
            return '', None
    
    def _getvideocoverinfo(self, url):
        try:
            for typ, pat in enumerate(self.VIDEO_URL_PATS, 1):
                match = pat.match(url)
                if not match:
                    continue
                if typ == 1:
                    cover_info = self._getcoverinfosd(url)
                elif typ == 2:
                    urls_dict = (self._getcoverinfo(self.VIDEO_COVER_FORMAT.format(match.group(1))) or ('', None))[-1]
                    if urls_dict and urls_dict.get("hd") and not urls_dict.get("sd"):
                        cover_info = self._getcoverinfohd(urls_dict["hd"])
                    elif urls_dict and urls_dict.get("sd"):
                        cover_info = self._getcoverinfosd(urls_dict["sd"])
                    else:
                        cover_info = None
                else:
                    cover_info = self._getcoverinfohd(url)
                    if cover_info and cover_info.get('type') == 'MOV':
                        urls_dict = (self._getcoverinfo(self.VIDEO_COVER_FORMAT.format(cover_info.get('cover_id', ''))) or ('', None))[-1]
                        if urls_dict and urls_dict.get("sd"):
                            sd_info = self._getcoverinfosd(urls_dict["sd"])
                            if sd_info:
                                cover_info = sd_info
                if not cover_info:
                    return cover_info
                cover_info['url'] = url
                cover_info['referrer'] = url
                cover_info['episode_all'] = len(cover_info.get('normal_ids') or [])
                if cover_info.get('type') == 'TV':
                    video_id = match.group(1)
                    cover_info['normal_ids'] = [dic for dic in (cover_info.get('normal_ids') or []) if dic.get('V') == video_id]
                return cover_info
            return None
        except Exception:
            return None
    
    def _updatevideodwnldinfosd(self, vi):
        try:
            nonce = math.floor(time.time())
            params = {'cid': vi['V'], 'expiretime': nonce + 600, 'nonce': nonce, 'page': vi['url'], 'playerid': self._randomplayerid(), 'type': "hls", 'uuid': self._randomstring()}
            params['signature'] = self._signature(params, self.APP_ID)
            text = self.get(self.PROFILE_CONFIG_URL + '?' + urlencode(params))
            data = self._loadjsonp(text, 'null(')
            data = data.get('data') if isinstance(data, dict) else None
            if not data or not isinstance(data, dict):
                return
            preferred_defn = self.M1905_DEFN_MAP_S2I['free']["uhd"]
            for defn in ([preferred_defn] + [d for d in self.M1905_DEFINITION['free'] if d != preferred_defn]):
                host = safe_extract(data, ['quality', defn, 'host'], None)
                sign = safe_extract(data, ['sign', defn, 'sign'], None)
                path = safe_extract(data, ['path', defn, 'path'], None)
                if not (host and path):
                    continue
                if sign:
                    playlist_m3u8 = str(host + sign + path).replace('\\', '')
                elif 'sign=' in path:
                    playlist_m3u8 = str(host + path).replace('\\', '')
                else:
                    continue
                vi["defns"] = [{self.M1905_DEFN_MAP_I2S['free'][defn]: playlist_m3u8}]
        except Exception:
            return
    
    def _updatevideodwnldinfohd(self, vi):
        try:
            params = {'vipid': vi['V'], 'playerid': self._randomplayerid(), 'uuid': self._randomstring(), 'callback': 'fnCallback0'}
            text = self.get(self.VIP_CONFIG_URL + '?' + urlencode(params))
            data = self._loadjsonp(text, 'fnCallback0(')
            data = data.get('data') if isinstance(data, dict) else None
            if not data or not isinstance(data, dict):
                return
            defn = self.M1905_DEFN_MAP_S2I['vip']["uhd"]
            order = ([defn] if safe_extract(data, ['path', defn], None) else self.M1905_DEFINITION['vip'])
            for defn in order:
                path = safe_extract(data, ['path', defn], None)
                if not path:
                    continue
                playlist_m3u8 = str(path).replace('\\', '')
                vi["defns"] = [{self.M1905_DEFN_MAP_I2S['vip'][defn]: playlist_m3u8}]
        except Exception:
            return
    
    def _updatevideodwnldinfo(self, vi):
        try:
            if not vi.get('vip'):
                self._updatevideodwnldinfosd(vi)
            elif vi.get('free'):
                self._updatevideodwnldinfohd(vi)
            else:
                raise RuntimeError("Couldn't download the VIP video, please configure 1905 VIP cookies first.")
        except Exception:
            return
    
    def _loadjsonp(self, text, prefix):
        try:
            t = (text or '').strip()
            if prefix and t.startswith(prefix):
                t = t[len(prefix):]
            if t.endswith(')'):
                t = t[:-1]
            t = t.strip()
            try:
                return json.loads(t)
            except:
                pass
            blob = self._extractjsonobj(t)
            if blob:
                try:
                    return json.loads(blob)
                except:
                    pass
            return self._repairjson(t)
        except Exception:
            return {}
    
    def _extractjsonobj(self, text):
        try:
            start = text.find('{')
            if start < 0:
                return ''
            depth = 0
            for i in range(start, len(text)):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        return text[start:i + 1]
            return ''
        except Exception:
            return ''
    
    def _repairjson(self, text):
        try:
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
