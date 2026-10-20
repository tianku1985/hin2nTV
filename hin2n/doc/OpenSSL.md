hin2n 需要 OpenSSL 的 `libcrypto.so` 来启用 ntop n2n 的 AES 加密。
APK 内 4 个 ABI 各带一份 `libcrypto.so` 与对应头文件，位于
`Hin2n_android/app/src/main/jniLibs/<abi>/`。

## 重要：必须以低 API level 编译

`libcrypto.so` 必须用 app minSdk 对应的 Android API level 编译
（armeabi-v7a / x86 用 19，arm64-v8a / x86_64 用 21）。

如果用较新的 API level 编译（比如直接用 NDK 里最高版本的 clang 默认值），
产物会引用 `getentropy`（API 29+）、`__register_atfork`（API 23+）
等老系统 libc 里不存在的符号；而 OpenSSL 的 so 带 `DF_1_NOW`，
加载时立即全量解析所有符号，于是 **Android 9 及以下设备**
（多为 32 位盒子）`dlopen("libcrypto.so")` 直接失败：
`edge_v2` / `edge_v3` / `edge_jni`（仅这三个依赖 crypto）
抛 `UnsatisfiedLinkError`，界面报“启动失败”。

## 构建方法（推荐，CI 也用它）

```bash
# 需已安装 NDK 25.2.9519653（与 app 的 ndkVersion 一致）
export ANDROID_NDK_HOME=/path/to/android-sdk/ndk/25.2.9519653
bash hin2n/scripts/build-openssl-android.sh
```

脚本会下载 OpenSSL 源码（默认 1.1.1w，可用 `OPENSSL_VERSION` 覆盖），
按 ABI 分别以 API 19/21 编译 `libcrypto.so`，校验产物不再引用新 API 符号，
然后覆盖安装到 `Hin2n_android/app/src/main/jniLibs/<abi>/`
（`libcrypto.so` + `include/openssl/`，`opensslconf.h` 等按 ABI 生成，不可混用）。
构建中间产物缓存在 `hin2n/.openssl-build/`（已 gitignore）。

GitHub Actions（`.github/workflows/hin2n.yml`）在 Gradle 构建前自动执行此脚本，
因此发布产物始终是低 API 的 libcrypto。

## 手动构建方法（参考）

```bash
# 参考
# https://wiki.openssl.org/index.php/Android
export ANDROID_NDK_HOME=/path/to/android-sdk/ndk/25.2.9519653
export PATH="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin:$PATH"
tar -xf openssl-1.1.1w.tar.gz && cd openssl-1.1.1w

# 32 位必须指定 API 19，64 位指定 API 21；SHLIB_* 覆盖用于得到不带版本号的 libcrypto.so
make clean
CC=armv7a-linux-androideabi19-clang ANDROID_API=19 \
  ./Configure android-arm no-ssl3 no-comp no-hw no-engine
make -j`nproc` SHLIB_VERSION_NUMBER= SHLIB_EXT=.so build_libs

# 其余 ABI 同理：
#   arm64 : CC=aarch64-linux-android21-clang     ANDROID_API=21 ./Configure android-arm64
#   x86   : CC=i686-linux-android19-clang        ANDROID_API=19 ./Configure android-x86
#   x86_64: CC=x86_64-linux-android21-clang      ANDROID_API=21 ./Configure android-x86_64
```

产物校验（确认能在老设备上加载）：

```bash
$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-nm -D libcrypto.so \
  | awk '$2=="U"{print $3}' | grep -E 'getentropy|__register_atfork'
# 期望：无输出
```
