# py_spider

TVBox Python spiders ported from [videodl](https://github.com/CharlesPikachu/videodl). All spiders follow the standard TVBox Python spider interface (FongMi/Chaquopy style).

## Usage

Add to your TVBox config (sites array):

`json
{
  "key": "py_haokan",
  "name": "∫√ø¥ ”∆µ",
  "type": 3,
  "api": "clan://localhost/py_spider/haokan.py",
  "searchable": 1,
  "quickSearch": 1,
  "filterable": 0
}
`

Or use ile:// paths depending on your TVBox variant.

## Interface

Each spider implements:
- init(self, extend="")
- homeContent(self, filter) 
- categoryContent(self, tid, pg, filter, extend)
- detailContent(self, ids)
- searchContent(self, key, quick, pg="1")
- playerContent(self, flag, id, vipFlags)

## Notes

- Some platforms require Node.js (e.g. Tencent QQ Video) - won't work in pure Chaquopy without node
- Some use browser automation (DrissionPage) - not available in mobile runtime
- YouTube may have limitations
- All code is stdlib-only where possible

## License

Ported code is based on videodl under [PolyForm Noncommercial License 1.0.0](LICENSE-videodl). See LICENSE-videodl for details.
