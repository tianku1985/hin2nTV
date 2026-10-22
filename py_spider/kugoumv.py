# -*- coding: utf-8 -*-
# Ported from videodl (PolyForm Noncommercial License 1.0.0)
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor
from urllib.request import Request
from urllib.request import build_opener
from html import unescape
import json
import os
import re
import time
import hashlib
from urllib.parse import urlparse, urlencode

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

    SALT = "NVPh5oo715z5DIWAeQlhMDsWXXQV4hwt"
    
    def getName(self):
        return "酷狗音乐"
    
    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
        })
        self.mid = hashlib.md5(os.urandom(16)).hexdigest()
    
    def homeContent(self, filter):
        return {"class": [], "list": []}
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not self.match_domain(url, ["kugou.com"]):
                return result
            vid = urlparse(url).path.strip('/').split('/')[-1]
            params = {'srcappid': '2919', 'clientver': '1000', 'clienttime': str(int(time.time() * 1000)), 'mid': self.mid, 'uuid': self.mid, 'dfid': '1u0Qpt0FTdFC2BtwCF2hRvQ1', 'appid': '1014', 'id': vid}
            params['signature'] = self._calcsignature(params)
            api_url = 'https://wwwapi.kugou.com/play/mv?' + urlencode(params)
            raw_data = self.fetch_json(api_url)
            play = safe_extract(raw_data, ['data', 'play'], {})
            if not isinstance(play, dict):
                play = {}
            play_info = []
            for k, v in play.items():
                try:
                    downurl = v.get('downurl')
                    backup = v.get('backupdownurl') or []
                    if isinstance(backup, str):
                        backup = [backup]
                    first_backup = backup[0] if backup else ''
                    if not (downurl or first_backup):
                        continue
                    if not (str(downurl).startswith('http') or str(first_backup).startswith('http')):
                        continue
                    play_info.append((k, v))
                except:
                    continue
            if not play_info:
                return result
            try:
                play_info.sort(key=lambda item: int(float(item[1].get('filesize', 0) or 0)), reverse=True)
            except:
                pass
            best = play_info[0][1]
            download_url = best.get('downurl')
            if not download_url:
                backup = best.get('backupdownurl') or []
                download_url = backup[0] if isinstance(backup, list) and backup else backup
            if not isinstance(download_url, str):
                download_url = ''
            title = self.legalize(str(safe_extract(raw_data, ['data', 'info', 'base', 'mv_name'], '') or '')).removesuffix('.').replace('$', '').replace('#', '') or vid or 'kugou'
            cover = safe_extract(raw_data, ['data', 'info', 'base', 'hdpic'], '') or ''
            if isinstance(cover, str) and '{size}' in cover:
                cover = cover.replace('{size}', '480')
            play_id = f'{vid}|{download_url}|{url}'
            vod = self.build_vod(vid or url, title, cover, '', title, 'KugouMV', f'{title}${play_id}')
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
                return {"parse": 0, "url": download_url, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': 'https://www.kugou.com/'})}
            return {"parse": 1, "url": page_url}
        except Exception:
            return {"parse": 1, "url": id}
    
    def _calcsignature(self, params):
        try:
            kv_pairs = []
            for k in sorted(params.keys()):
                kv_pairs.append(f"{k}={params[k]}")
            sign_content = self.SALT + "".join(kv_pairs) + self.SALT
            return hashlib.md5(sign_content.encode('utf-8')).hexdigest()
        except Exception:
            return ''
