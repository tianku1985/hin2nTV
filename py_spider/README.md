# py_spider（TVBox Python 爬虫，链接解析）

本目录为从 videodl 移植的 **72 个** 平台 Python 爬虫，均为**自包含单文件**（已去除对 `spider_base.py` 的依赖，可直接放入 TVBox 的 Python 插件目录加载）。

## 适用分支
- **FongMi/TV**：支持 `file://`、本地路径、http(s) 链接加载 Python。也可通过 `api` 指定文件路径。
- **takagen99/Box**：通过 `PythonLoader` 加载 `.py`。需用 **http(s) 直链** 或 `file://` 指向插件文件。  
  注意：`pyLoader.getPyUrl` 在 `ext` 非空时会拼接 `?extend=...`，**若用 `file://` 本地路径请务必将站点配置中的 `ext` 留空**，否则会破坏本地文件路径导致无法加载。

## 部署方式
1. 将整个 `py_spider/` 下的 `.py` 文件复制到 Android 设备的插件目录：`/storage/emulated/0/plugin/`（takagen99/FongMi 常用目录，具体以你的分支为准）。
2. 在 TVBox 站点配置（`sites`）中添加条目，`type` 建议设为 `3`。

## 配置示例
参考 `tvbox_sites_sample.json`。要点：
- 本地加载（常用）：`"api": "file:///storage/emulated/0/plugin/douyin.py"`, `"ext": ""`
- 远程加载：http(s) 直链（如 GitHub Raw、自己的服务器），`"ext": ""`
- 搜索框直接粘贴分享链接即可解析播放（已注入通用 `searchContent`/`homeContent`/`categoryContent`，解析结果的 `vod_id` 会设为原始链接以保证后续流程正常）。

## 注意事项
- **单文件自包含**：每个 `.py` 都内置了必要的 HTTP/JSON/工具函数，不依赖同目录其他模块。
- **接口兼容**：实现 `Spider` 类，包含 `init/getName/getDependence/homeContent/homeVideoContent/categoryContent/detailContent/searchContent/playerContent` 等 TVBox Python 接口。`getDependence()` 返回 `[]`。
- **header 格式**：`playerContent` 返回的 `header` 为 **JSON 字符串**，以同时兼容不同分支解析方式。
- **受限平台**：部分平台（如 tencent/youtube/playerpl/wittytv/mgtv/kuaishou/xinpianchang/dongchedi/m1905 等）因反爬/加密/DRM 或原实现依赖已失效路径，可能无法正常解析，仅保留框架代码。
- **许可**：基于 PolyForm Noncommercial 1.0.0（见 `LICENSE-videodl`）。

## 测试建议
在 TVBox 中先用 **抖音/哔哩哔哩/西瓜/好看/快手** 等常用平台的**公开分享链接**测试：把链接粘贴到搜索框 → 应能出结果并可播放。
