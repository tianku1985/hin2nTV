# -*- coding: utf-8 -*-
# Ported from videodl (PolyForm Noncommercial License 1.0.0)
# LIMITATION: YouTube stream extraction needs the botguard/PO-token + js-interpreter
# stack of videodl (node), which is not available in a pure python TVBox spider.
# Best effort: the watch page / innertube player response and the public third party
# resolvers are tried, otherwise playback is delegated to TVBox with parse=1.
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

    DOMAINS = ["youtube.com", "youtu.be", "youtube-nocookie.com"]
    INNERTUBE_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
    def getName(self):
        return "YouTube"
    
    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        })
    
    def homeContent(self, filter):
        return {"class": [], "list": []}
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, self.DOMAINS):
                return result
            vid = self._extract_vid(url)
            title = ''
            cover = ''
            content = ''
            media = ''
            player = {}
            html = ''
            if vid:
                try:
                    html = self.get(f'https://www.youtube.com/watch?v={vid}', timeout=15)
                except Exception:
                    html = ''
                player = self._extract_player(html)
                title = self._parse_title(player)
                cover = self._parse_cover(player)
                content = self._parse_description(player)
                media = self._pick_stream(player)
            if not media and vid:
                media = self._innertube_stream(vid)
            if not media:
                media = self._ytdown_stream(url)
            if not media:
                media = self._downr_stream(url)
            if not title:
                title = self._page_title(html) or vid or url
            if not cover and vid:
                cover = f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg'
            title = title.replace('$', '').replace('#', '')
            play_id = f'{media}|{url}'
            result['list'] = [self.build_vod(vid or url, title, cover, '', content or title, 'YouTube', f'{title}${play_id}')]
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
                return {"parse": 0, "url": media, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': 'https://www.youtube.com/'})}
            return {"parse": 1, "url": page or media, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': 'https://www.youtube.com/'})}
        except Exception:
            return {"parse": 1, "url": id}
    
    def _extract_vid(self, url):
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            q = parse_qs(parsed.query, keep_blank_values=True).get('v')
            if q and q[0]:
                return q[0]
            path = parsed.path.strip('/')
            if host.endswith('youtu.be') and path:
                return path.split('/')[0]
            for prefix in ('embed', 'shorts', 'live', 'v'):
                if path.startswith(prefix + '/'):
                    return path.split('/')[1]
        except Exception:
            pass
        return ''
    
    def _extract_player(self, html):
        try:
            if not html:
                return {}
            idx = html.find('ytInitialPlayerResponse')
            if idx < 0:
                return {}
            start = html.find('{', idx)
            if start < 0:
                return {}
            depth, in_str, esc, quote = 0, False, False, ''
            for i in range(start, len(html)):
                ch = html[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == '\\':
                        esc = True
                    elif ch == quote:
                        in_str = False
                    continue
                if ch in '"\'':
                    in_str, quote = True, ch
                    continue
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return json.loads(html[start:i + 1])
        except Exception:
            pass
        return {}
    
    def _parse_title(self, player):
        try:
            details = player.get('videoDetails') if isinstance(player, dict) else None
            if isinstance(details, dict):
                title = details.get('title')
                if title:
                    return self.legalize(title)
        except Exception:
            pass
        return ''
    
    def _parse_cover(self, player):
        try:
            details = player.get('videoDetails') if isinstance(player, dict) else None
            if isinstance(details, dict):
                thumbs = safe_extract(details, ['thumbnail', 'thumbnails'], []) or []
                best = ''
                for item in thumbs:
                    if isinstance(item, dict) and str(item.get('url') or '').startswith('http'):
                        best = item['url']
                if best:
                    return best
        except Exception:
            pass
        return ''
    
    def _parse_description(self, player):
        try:
            details = player.get('videoDetails') if isinstance(player, dict) else None
            if isinstance(details, dict):
                desc = details.get('shortDescription')
                if desc:
                    return self.legalize(desc)
        except Exception:
            pass
        return ''
    
    def _pick_stream(self, player):
        try:
            sd = player.get('streamingData') if isinstance(player, dict) else None
            if not isinstance(sd, dict):
                return ''
            best, best_score = '', -1
            for group, bonus in (('formats', 1000000000), ('adaptiveFormats', 0)):
                for fmt in (sd.get(group) or []):
                    if not isinstance(fmt, dict):
                        continue
                    u = fmt.get('url') or ''
                    if not str(u).startswith('http'):
                        continue
                    mime = str(fmt.get('mimeType') or '')
                    if 'audio' in mime and 'video' not in mime:
                        continue
                    score = bonus + int(fmt.get('bitrate') or 0)
                    try:
                        score += int(fmt.get('width') or 0) * int(fmt.get('height') or 0)
                    except Exception:
                        pass
                    if score > best_score:
                        best, best_score = str(u), score
            return best
        except Exception:
            return ''
    
    def _innertube_stream(self, vid):
        try:
            body = {
                'videoId': vid,
                'contentCheckOk': True,
                'racyCheckOk': True,
                'context': {'client': {'clientName': 'ANDROID', 'clientVersion': '19.09.37', 'androidSdkVersion': 30, 'hl': 'en', 'gl': 'US'}}
            }
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip',
                'X-YouTube-Client-Name': '3',
                'X-YouTube-Client-Version': '19.09.37'
            }
            raw = self.post(f'https://www.youtube.com/youtubei/v1/player?key={self.INNERTUBE_KEY}', data=json.dumps(body), headers=headers, timeout=15)
            player = json.loads(raw)
            return self._pick_stream(player)
        except Exception:
            return ''
    
    def _ytdown_stream(self, url):
        try:
            headers = {'origin': 'https://app.ytdown.to', 'referer': 'https://app.ytdown.to/en27/', 'Content-Type': 'application/x-www-form-urlencoded'}
            raw = self.post('https://app.ytdown.to/proxy.php', data={'url': url}, headers=headers, timeout=20)
            items = safe_extract(json.loads(raw), ['api', 'mediaItems'], []) or []
            videos = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                if str(item.get('type') or '').lower() != 'video':
                    continue
                media_url = str(item.get('mediaUrl') or '')
                if not media_url.startswith('http'):
                    continue
                size = 0
                try:
                    size = int(float(str(item.get('mediaFileSize') or '0').split(' ')[0]))
                except Exception:
                    size = 0
                videos.append((size, media_url))
            videos.sort(key=lambda x: x[0], reverse=True)
            for _, media_url in videos[:3]:
                try:
                    raw2 = self.post('https://app.ytdown.to/proxy.php', data={'url': media_url}, headers=headers, timeout=20)
                    file_url = safe_extract(json.loads(raw2), ['api', 'fileUrl'], '') or ''
                    if str(file_url).startswith('http'):
                        return str(file_url)
                except Exception:
                    continue
        except Exception:
            pass
        return ''
    
    def _downr_stream(self, url):
        try:
            headers = {'referer': 'https://downr.org/', 'Content-Type': 'application/json'}
            try:
                self.get('https://downr.org/.netlify/functions/analytics', headers={'referer': 'https://downr.org/'}, timeout=15)
            except Exception:
                pass
            raw = self.post('https://downr.org/.netlify/functions/nyt', data=json.dumps({'url': url}), headers=headers, timeout=20)
            data = json.loads(raw)
            medias = []
            for item in (data.get('medias') or []):
                if not isinstance(item, dict):
                    continue
                if str(item.get('type') or '') != 'video':
                    continue
                media_url = str(item.get('url') or '')
                if not media_url.startswith('http'):
                    continue
                try:
                    size = int(item.get('height') or 0) * int(item.get('width') or 0) + int(item.get('bitrate') or 0)
                except Exception:
                    size = 0
                medias.append((size, media_url))
            medias.sort(key=lambda x: x[0], reverse=True)
            if medias:
                return medias[0][1]
        except Exception:
            pass
        return ''
    
    def _page_title(self, html):
        try:
            found = re.findall(r'<title>(.*?)</title>', html or '', re.S)
            if found:
                return self.legalize(found[0])
        except Exception:
            pass
        return ''
