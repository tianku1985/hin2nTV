from urllib.parse import unquote
# -*- coding: utf-8 -*-
# Ported from videodl (PolyForm Noncommercial License 1.0.0)
# videodl uses Cryptodome for the AES-CBC sign/answer of the xiami/xmflv parse
# service, here a pure python AES is used instead (no third party dependency).
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor
from urllib.request import Request
from urllib.request import build_opener
from html import unescape
import json
import re
import hashlib
import base64
from urllib.parse import urlparse, parse_qs, quote, urlencode

SBOX = [
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16]
INV_SBOX = [0] * 256

def _build_inv_sbox():
    for i, v in enumerate(SBOX):
        INV_SBOX[v] = i

_build_inv_sbox()
RCON = [0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36, 0x6c, 0xd8, 0xab, 0x4d]

def _xtime(a):
    a <<= 1
    if a & 0x100:
        a = (a ^ 0x1b) & 0xff
    return a

def _mul(a, b):
    r = 0
    while b:
        if b & 1:
            r ^= a
        a = _xtime(a)
        b >>= 1
    return r

def _expand_key(key):
    nk = len(key) // 4
    nr = nk + 6
    words = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
    for i in range(nk, 4 * (nr + 1)):
        t = list(words[i - 1])
        if i % nk == 0:
            t = t[1:] + t[:1]
            t = [SBOX[b] for b in t]
            t[0] ^= RCON[i // nk]
        elif nk > 6 and i % nk == 4:
            t = [SBOX[b] for b in t]
        words.append([words[i - nk][j] ^ t[j] for j in range(4)])
    rks = []
    for r in range(nr + 1):
        rk = []
        for j in range(4):
            rk.extend(words[4 * r + j])
        rks.append(rk)
    return rks

def _add_rk(s, rk):
    return [s[i] ^ rk[i] for i in range(16)]

def _shift_rows(s):
    o = list(s)
    for r in range(1, 4):
        for c in range(4):
            o[r + 4 * c] = s[r + 4 * ((c + r) % 4)]
    return o

def _inv_shift_rows(s):
    o = list(s)
    for r in range(1, 4):
        for c in range(4):
            o[r + 4 * ((c + r) % 4)] = s[r + 4 * c]
    return o

def _mix_columns(s):
    o = [0] * 16
    for c in range(4):
        a = s[4 * c:4 * c + 4]
        o[4 * c + 0] = _mul(a[0], 2) ^ _mul(a[1], 3) ^ a[2] ^ a[3]
        o[4 * c + 1] = a[0] ^ _mul(a[1], 2) ^ _mul(a[2], 3) ^ a[3]
        o[4 * c + 2] = a[0] ^ a[1] ^ _mul(a[2], 2) ^ _mul(a[3], 3)
        o[4 * c + 3] = _mul(a[0], 3) ^ a[1] ^ a[2] ^ _mul(a[3], 2)
    return o

def _inv_mix_columns(s):
    o = [0] * 16
    for c in range(4):
        a = s[4 * c:4 * c + 4]
        o[4 * c + 0] = _mul(a[0], 14) ^ _mul(a[1], 11) ^ _mul(a[2], 13) ^ _mul(a[3], 9)
        o[4 * c + 1] = _mul(a[0], 9) ^ _mul(a[1], 14) ^ _mul(a[2], 11) ^ _mul(a[3], 13)
        o[4 * c + 2] = _mul(a[0], 13) ^ _mul(a[1], 9) ^ _mul(a[2], 14) ^ _mul(a[3], 11)
        o[4 * c + 3] = _mul(a[0], 11) ^ _mul(a[1], 13) ^ _mul(a[2], 9) ^ _mul(a[3], 14)
    return o

def _encrypt_block(rks, block):
    nr = len(rks) - 1
    s = _add_rk(list(block), rks[0])
    for r in range(1, nr):
        s = _shift_rows([SBOX[b] for b in s])
        s = _mix_columns(s)
        s = _add_rk(s, rks[r])
    s = _shift_rows([SBOX[b] for b in s])
    return _add_rk(s, rks[nr])

def _decrypt_block(rks, block):
    nr = len(rks) - 1
    s = _add_rk(list(block), rks[nr])
    for r in range(nr - 1, 0, -1):
        s = _inv_shift_rows([INV_SBOX[b] for b in s])
        s = _add_rk(s, rks[r])
        s = _inv_mix_columns(s)
    s = _inv_shift_rows([INV_SBOX[b] for b in s])
    return _add_rk(s, rks[0])

def aes_cbc_encrypt(key, iv, data):
    rks = _expand_key(key)
    out = bytearray()
    prev = bytes(iv)
    for i in range(0, len(data), 16):
        block = bytes(a ^ b for a, b in zip(data[i:i + 16], prev))
        enc = bytes(_encrypt_block(rks, block))
        out.extend(enc)
        prev = enc
    return bytes(out)

def aes_cbc_decrypt(key, iv, data):
    rks = _expand_key(key)
    out = bytearray()
    prev = bytes(iv)
    for i in range(0, len(data), 16):
        enc = data[i:i + 16]
        dec = bytes(_decrypt_block(rks, enc))
        out.extend(bytes(a ^ b for a, b in zip(dec, prev)))
        prev = enc
    return bytes(out)

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

    TIME_URL = 'https://data.video.iqiyi.com/v.f4v?src=iqiyi.com'
    API_URL = 'https://cache.0567890.xyz:4433/Api'
    AES_IV = b'fUU9eRmkYzsgbkEK'
    def getName(self):
        return "XMFlv"
    
    def init(self, extend=""):
        self.extend = extend
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Origin': 'https://jx.xmflv.com',
            'Referer': 'https://jx.xmflv.com/'
        })
    
    
    def categoryContent(self, tid, pg, filter, extend):
        return {"page": pg, "pagecount": 1, "limit": 20, "total": 0, "list": []}
    
    def detailContent(self, ids):
        result = {"list": []}
        try:
            url = ids[0] if isinstance(ids, list) else ids
            if not isinstance(url, str) or not url.startswith('http'):
                return result
            title = ''
            cover = ''
            media = ''
            parsed = self._parse_api(url)
            if parsed:
                title = self.legalize(parsed.get('name') or '')
                cover = parsed.get('pic') or ''
                media = str(parsed.get('url') or '')
                if not media.startswith('http'):
                    media = ''
                if title == '解析失败啦':
                    media = ''
            html = ''
            if not title or not cover:
                try:
                    html = self.get(url, timeout=15)
                except Exception:
                    html = ''
            if not title:
                title = self._page_title(html)
            if not cover:
                cover = self._page_cover(html)
            if not title:
                title = url
            title = title.replace('$', '').replace('#', '')
            play_id = f'{media}|{url}'
            result['list'] = [self.build_vod(url, title, cover, '', title, 'XMFlv', f'{title}${play_id}')]
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
                return {"parse": 0, "url": media, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': 'https://jx.xmflv.com/'})}
            return {"parse": 1, "url": page or media, "header": json.dumps({'User-Agent': self.headers['User-Agent'], 'Referer': 'https://jx.xmflv.com/'})}
        except Exception:
            return {"parse": 1, "url": id}
    
    def _parse_api(self, url):
        try:
            raw = self.fetch_json(self.TIME_URL, timeout=15)
            server_time = str(raw.get('time') or '')
            if not server_time:
                return None
            quoted = quote(url, safe='')
            key = hashlib.md5((server_time + quoted).encode('utf-8')).hexdigest()
            sign = self._sign(key)
            data = {'tm': server_time, 'url': quoted, 'key': key, 'sign': sign}
            resp = self.post(self.API_URL, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}, timeout=20)
            raw2 = json.loads(resp)
            if not isinstance(raw2, dict):
                return None
            encrypted = raw2.get('data')
            resp_key = str(raw2.get('key') or '')
            resp_iv = str(raw2.get('iv') or '')
            if not encrypted or not resp_key or not resp_iv:
                return None
            plain = aes_cbc_decrypt(resp_key.encode('utf-8'), resp_iv.encode('utf-8'), base64.b64decode(encrypted))
            plain = self._unpad(plain)
            text = plain.decode('utf-8', 'ignore')
            try:
                parsed = json.loads(text)
            except Exception:
                parsed = json.loads(re.sub(r',\s*([}\]])', r'\1', text))
            if not isinstance(parsed, dict):
                return None
            return {k: (v.replace('\\/', '/') if isinstance(v, str) else v) for k, v in parsed.items()}
        except Exception:
            return None
    
    def _sign(self, key):
        try:
            aes_key = hashlib.md5(key.encode('utf-8')).hexdigest().encode('utf-8')
            text = key.encode('utf-8')
            pad = 16 - (len(text) % 16)
            if pad != 16:
                text += b'\x00' * pad
            return base64.b64encode(aes_cbc_encrypt(aes_key, self.AES_IV, text)).decode('utf-8')
        except Exception:
            return ''
    
    def _unpad(self, data):
        try:
            if not data:
                return data
            pad = data[-1]
            if 0 < pad <= 16 and data[-pad:] == bytes([pad]) * pad:
                return data[:-pad]
        except Exception:
            pass
        return data
    
    def _page_title(self, html):
        try:
            found = re.findall(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html or '')
            if found:
                return self.legalize(found[0])
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
