hin2n 需要 OpenSSL 的 `libcrypto.so` 来启用 ntop n2n 的 AES 加密。
APK 内 4 个 ABI 各带一份 `libcrypto.so` 与对应头文件，位于
`Hin2n_android/app/src/main/jniLibs/<abi>/`。

## 根因：老设备 dlopen 失败

32 位盒子（Android 5.0 ~ 9）上 `edge_v2` / `edge_v3` / `edge_jni` 抛
`UnsatisfiedLinkError`、界面报“启动失败”，而不依赖 crypto 的其余 6 个库加载正常。
原因是仓库预置的 `libcrypto.so`（旧 NDK GCC 编译）引用了老系统 libc 里
**不存在**的符号，而它带 `DF_1_NOW`（加载时立即全量解析所有符号），
于是 `dlopen("libcrypto.so")` 直接失败。

这类符号有两个来源，**两个都必须处理**：

| 符号 | 来源 | 影响范围 |
| --- | --- | --- |
| `__register_atfork` | OpenSSL `crypto/threads_pthread.c` 调用 `pthread_atfork`；API 19 的 NDK 头文件把它映射成 `__register_atfork`（Android 4.x 的 libc 私有符号，**Android 5.0 起被删除**） | Android 5.0+ 全部 dlopen 失败 |
| `pthread_atfork` | 同上，API 21+ 直接引用该符号（**Android 4.4 没有**） | Android 4.4 dlopen 失败 |
| `getentropy` | `crypto/rand/rand_unix.c` 弱符号引用（`__attribute__((weak))`） | 弱符号解析不到时取 NULL，**不影响加载** |

因此仅仅“用低 API level 重新编译”是不够的：API 19 的产物照样会引用
`__register_atfork`，在 Android 5.0+ 上照样加载失败。
构建脚本额外把 OpenSSL 的 `pthread_atfork` 调用删掉了
（见 `hin2n/scripts/build-openssl-android.sh` 的 `patch_no_atfork`），
使产物不再依赖任何 fork 相关符号，在 API 19 ~ 当前所有版本上都能加载。
Android 应用基本不会 fork，去掉 fork 处理器没有实际影响。

同时 `libcrypto.so` 必须用 app minSdk 对应的 API level 编译
（armeabi-v7a / x86 用 19，arm64-v8a / x86_64 用 21），
这样其余 libc 符号也保证存在于对应版本的系统里。

## 构建方法（推荐，CI 也用它）

```bash
# 需已安装 NDK 25.2.9519653（与 app 的 ndkVersion 一致）
export ANDROID_NDK_HOME=/path/to/android-sdk/ndk/25.2.9519653
bash hin2n/scripts/build-openssl-android.sh
```

脚本会：

1. 下载 OpenSSL 源码（默认 1.1.1w，可用 `OPENSSL_VERSION` 覆盖）；
2. 删除 `crypto/threads_pthread.c` 里的 `pthread_atfork` 调用；
3. 按 ABI 分别以 API 19/21 编译 `libcrypto.so`
   （NDK 必须是 25.x：r26+ 已移除 API 19 支持）；
4. 用 `hin2n/scripts/check-libcrypto.sh` 校验产物：
   必需导出符号齐全 + 没有 `__register_atfork` / `pthread_atfork` 等危险未定义符号；
5. 覆盖安装到 `Hin2n_android/app/src/main/jniLibs/<abi>/`
   （`libcrypto.so` + `include/openssl/`，`opensslconf.h` 等按 ABI 生成，不可混用）。

构建中间产物缓存在 `hin2n/.openssl-build/`（已 gitignore）。
GitHub Actions（`.github/workflows/hin2n.yml`）在 Gradle 构建前自动执行此脚本，
打包后还会再校验一次 APK 内 4 个 ABI 的 `libcrypto.so`
以及 `edge_v2` / `edge_v3` / `edge_jni`，因此发布产物始终是老设备可加载的。

## 产物校验（可单独执行）

```bash
NM=$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-nm
READELF=$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf
bash hin2n/scripts/check-libcrypto.sh libcrypto.so "$NM" "$READELF"
# CHECK_MODE=undef 可只检查“危险未定义符号”（用于 edge_v2/edge_v3/edge_jni 这类使用方）
```

手工核对时注意：**不要把上千个符号塞进管道**（`printf | grep` 会因 grep 提前退出
触发 SIGPIPE，误判成“符号缺失”）。正确写法是落到文件再比对：

```bash
# 1) 危险未定义符号（期望：无输出）
$NM -D libcrypto.so | awk '$(NF-1)=="U"{sub(/@.*/,"",$NF);print $NF}' \
  | grep -E '^(__register_atfork|pthread_atfork|getentropy|getrandom)$'
# 2) 必需导出符号（期望：每个都出现）
$NM -D --defined-only libcrypto.so | awk '{sub(/@.*/,"",$NF);print $NF}' \
  > /tmp/def.txt
grep -xE 'EVP_CIPHER_CTX_reset|EVP_CIPHER_CTX_new|EVP_aes_256_cbc|EVP_chacha20' /tmp/def.txt
```

## 手动构建方法（参考）

```bash
# 参考
# https://wiki.openssl.org/index.php/Android
# 注意：NDK r26+ 已移除 API 19 支持，必须用 25.x（与 app 的 ndkVersion 一致）
export ANDROID_NDK_HOME=/path/to/android-sdk/ndk/25.2.9519653
export PATH="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin:$PATH"
tar -xf openssl-1.1.1w.tar.gz && cd openssl-1.1.1w

# 1) 去掉 pthread_atfork 调用（否则 Android 5.0+ 加载失败）
sed -i '/pthread_atfork(OPENSSL_fork_prepare,/d' crypto/threads_pthread.c
sed -i '/OPENSSL_fork_parent, OPENSSL_fork_child);/d' crypto/threads_pthread.c
grep -n pthread_atfork crypto/threads_pthread.c   # 期望：无输出

# 2) OpenSSL 的 android-* target 会忽略 CC 环境变量，自行选择“clang + NDK 最高 API”，
#    所以要用 -D__ANDROID_API__ 告诉它用哪个 API，Configure 后再改写 Makefile 兜底。
./Configure android-arm -D__ANDROID_API__=19 \
    no-ssl3 no-comp no-hw no-engine --prefix="$PWD/out-arm"
sed -i -E "s|^CC[[:space:]]*=.*|CC = armv7a-linux-androideabi19-clang|" Makefile
sed -i -E "s|--target=[A-Za-z0-9_.-]+|--target=armv7a-linux-androideabi19|g" Makefile
sed -i -E "s|-D__ANDROID_API__=[0-9]+|-D__ANDROID_API__=19|g" Makefile
grep -E '^CC[[:space:]]*=' Makefile   # 确认是 armv7a-linux-androideabi19-clang
make -j`nproc` SHLIB_VERSION_NUMBER= SHLIB_EXT=.so build_libs

# 其余 ABI 同理（把上面的 triple/API 换成）：
#   arm64 : aarch64-linux-android21-clang     API 21  ./Configure android-arm64
#   x86   : i686-linux-android19-clang        API 19  ./Configure android-x86
#   x86_64: x86_64-linux-android21-clang      API 21  ./Configure android-x86_64
```
