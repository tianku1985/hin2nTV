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
from urllib.parse import urlparse, quote

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
        return "Bilibili"
    
    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'Referer': 'https://www.bilibili.com/',
            'Origin': 'https://www.bilibili.com'
        })
    
    def homeContent(self, filter):
        return {"class": [], "list": []}
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if 'bilibili.com' not in url and 'b23.tv' not in url:
                return result
            if 'b23.tv' in url:
                try:
                    resp = self.opener.open(url, timeout=10)
                    url = resp.geturl()
                except:
                    pass
            bv_match = re.search(r'BV[0-9A-Za-z]+', url)
            if not bv_match:
                return result
            bvid = bv_match.group(0)
            html = self.get(f'https://www.bilibili.com/video/{bvid}')
            aid_match = re.search(r'"aid"\s*:\s*(\d+)', html)
            cid_match = re.search(r'"cid"\s*:\s*(\d+)', html)
            title_match = re.search(r'"title"\s*:\s*"([^"]+)"', html)
            title = title_match.group(1) if title_match else bvid
            title = self.legalize(title)
            play_url = f'{bvid}||{aid_match.group(1) if aid_match else ""}||{cid_match.group(1) if cid_match else ""}'
            vod = {
                'vod_id': bvid,
                'vod_name': title,
                'vod_pic': '',
                'vod_remarks': '',
                'vod_content': title,
                'vod_play_from': 'Bilibili',
                'vod_play_url': f'{title}${play_url}'
            }
            result['list'] = [vod]
        except Exception as e:
            pass
        return result
    
    def searchContent(self, key, quick, pg="1"):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def playerContent(self, flag, id, vipFlags):
        try:
            parts = id.split('||')
            bvid = parts[0]
            aid = parts[1] if len(parts) > 1 else ''
            cid = parts[2] if len(parts) > 2 else ''
            if not cid and aid:
                try:
                    api = f'https://api.bilibili.com/x/web-interface/view?aid={aid}'
                    data = self.fetch_json(api, headers={'Referer': 'https://www.bilibili.com/'})
                    cid = str(safe_extract(data, ['data', 'cid'], ''))
                    if not cid:
                        for page in safe_extract(data, ['data', 'pages'], []):
                            cid = str(page.get('cid', ''))
                            if cid:
                                break
                except:
                    pass
            if not cid:
                html = self.get(f'https://www.bilibili.com/video/{bvid}')
                cid_match = re.search(r'"cid"\s*:\s*(\d+)', html)
                if cid_match:
                    cid = cid_match.group(1)
            if cid:
                playurl = f'https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=80&fnval=16&fourk=1'
                data = self.fetch_json(playurl, headers={'Referer': 'https://www.bilibili.com/'})
                durl = safe_extract(data, ['data', 'durl'], [])
                if durl and durl[0].get('url'):
                    return {"parse": 0, "url": durl[0]['url'], "header": json.dumps({'Referer': 'https://www.bilibili.com/', 'User-Agent': self.headers['User-Agent']})}
            return {"parse": 1, "url": id}
        except:
            return {"parse": 1, "url": id}
