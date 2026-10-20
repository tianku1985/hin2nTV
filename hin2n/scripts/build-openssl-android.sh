#!/usr/bin/env bash
# 用低 Android API level 重新构建 OpenSSL 的 libcrypto.so，并安装到 jniLibs。
#
# 背景（修复 32 位老设备启动失败）：
#   jniLibs 里预置的 libcrypto.so 是用较新的 API level 编译的，其动态符号表
#   引用了 getentropy（API 29+）、__register_atfork（API 23+）等老系统 libc
#   没有的符号，并且带 DF_1_NOW（加载时立即全量解析所有符号）。
#   于是 Android 9 及以下设备 dlopen("libcrypto.so") 直接失败，
#   依赖它的 edge_v2 / edge_v3 / edge_jni 全部抛 UnsatisfiedLinkError，
#   而不依赖 crypto 的其余 6 个库加载正常。
#   以 minSdk 对应的 API level（32 位 19 / 64 位 21）重新编译即可在老设备上加载。
#
# 用法（需已安装 NDK 25.2.9519653）：
#   ANDROID_NDK_HOME=/path/to/ndk/25.2.9519653 bash hin2n/scripts/build-openssl-android.sh
set -euo pipefail

OPENSSL_VERSION="${OPENSSL_VERSION:-1.1.1w}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
JNI_LIBS="$ROOT/hin2n/Hin2n_android/app/src/main/jniLibs"
WORK="${WORK:-$ROOT/hin2n/.openssl-build}"
# NDK 选择：优先用 SDK 里显式安装的 25.2（与 app 的 ndkVersion 一致，最高 API=33）。
# CI runner 镜像会把 ANDROID_NDK_HOME 指向预装的最新 NDK（r27+，默认 API 35，
# 已移除 API 19 支持），必须忽略它，否则编出来的库依旧无法在老设备加载。
NDK_VER="25.2.9519653"
NDK=""
for _ndk_root in "${ANDROID_SDK_ROOT:-}" "${ANDROID_HOME:-}"; do
    if [ -n "$_ndk_root" ] && [ -d "$_ndk_root/ndk/$NDK_VER" ]; then
        NDK="$_ndk_root/ndk/$NDK_VER"
        break
    fi
done
if [ -z "$NDK" ]; then
    NDK="${ANDROID_NDK_HOME:-${ANDROID_NDK_ROOT:-$HOME/Android/Sdk/ndk/$NDK_VER}}"
fi
HOST_TAG="${HOST_TAG:-linux-x86_64}"
TOOLCHAIN="$NDK/toolchains/llvm/prebuilt/$HOST_TAG"
JOBS="$(nproc 2>/dev/null || echo 4)"
TARBALL="$WORK/openssl-$OPENSSL_VERSION.tar.gz"
TAG="OpenSSL_$(echo "$OPENSSL_VERSION" | tr . _)"
URLS=(
    "https://www.openssl.org/source/openssl-$OPENSSL_VERSION.tar.gz"
    "https://github.com/openssl/openssl/releases/download/$TAG/openssl-$OPENSSL_VERSION.tar.gz"
)
# 这些符号只在较新的 Android 版本的 libc 中存在，出现任意一个即判定为不可用于老设备
NEW_API_SYMBOLS='^(getentropy|getrandom|__register_atfork|pthread_getname_np|arc4random_buf|closefrom)$'

die() { echo "ERROR: $*" >&2; exit 1; }

[ -d "$TOOLCHAIN" ] || die "未找到 NDK 工具链：$TOOLCHAIN（请设置 ANDROID_NDK_HOME）"
NM="$TOOLCHAIN/bin/llvm-nm"
READELF="$TOOLCHAIN/bin/llvm-readelf"
[ -x "$NM" ] || die "未找到 $NM"

# 校验 libcrypto.so 是否只引用老设备上存在的 libc 符号；返回 0 表示可用
libcrypto_ok() {
    local lib="$1" bad
    [ -s "$lib" ] || return 1
    # llvm-nm -D 输出形如“<addr> U symbol”或“ U symbol”，符号名在最后一列
    bad="$("$NM" -D "$lib" 2>/dev/null \
        | awk '$(NF-1) == "U" { sub(/@.*/, "", $NF); print $NF }' \
        | grep -E "$NEW_API_SYMBOLS" || true)"
    [ -z "$bad" ]
}

fetch_tarball() {
    [ -s "$TARBALL" ] && return 0
    mkdir -p "$WORK"
    local u
    for u in "${URLS[@]}"; do
        echo "下载 $u ..."
        if curl -fsSL --retry 3 -o "$TARBALL.tmp" "$u"; then
            mv "$TARBALL.tmp" "$TARBALL"
            return 0
        fi
    done
    die "下载 OpenSSL $OPENSSL_VERSION 失败"
}

build_abi() {
    local abi="$1" target="$2" triple="$3" api="$4"
    local out="$WORK/out/$abi"
    local src="$WORK/src-$abi"

    if libcrypto_ok "$out/libcrypto.so"; then
        echo "[$abi] 使用缓存的构建结果：$out/libcrypto.so"
    else
        echo "[$abi] 以 API $api 重新编译 OpenSSL $OPENSSL_VERSION ..."
        fetch_tarball
        # 快速失败：确认该 API 的 clang wrapper 在 NDK 里存在
        [ -x "$TOOLCHAIN/bin/${triple}${api}-clang" ] \
            || die "[$abi] NDK 中不存在 ${triple}${api}-clang（检查 NDK 版本/三元组拼写，32 位 ARM 是 armv7a-linux-androideabi）"
        rm -rf "$src"
        mkdir -p "$src"
        tar -xf "$TARBALL" -C "$src" --strip-components=1
        (
            cd "$src"
            export PATH="$TOOLCHAIN/bin:$PATH"
            # ANDROID_API + 带 API 后缀的 clang wrapper 双保险，
            # 确保 bionic 头文件按低 API 做可用性裁剪
            export ANDROID_API="$api"
            # 注意：OpenSSL 的 android-* target 会忽略 CC 环境变量，自行选择
            # “clang + NDK 最高 API”（上一次 CI 实测编译器是 ...-35-clang），
            # 所以 Configure 完必须改写 Makefile 强制低 API，见下方 patch。
            CC="${triple}${api}-clang" ./Configure "android-$target" \
                no-ssl3 no-comp no-hw no-engine \
                --prefix="$out"

            # 强制编译器为指定 API 的 clang wrapper（OpenSSL android target 不认 CC env）
            sed -i -E "s|^CC[[:space:]]*=.*|CC = ${triple}${api}-clang|" Makefile
            # 清掉配置可能自带的高 API --target / __ANDROID_API__（后出现者优先，防止覆盖 wrapper 的低 API）
            sed -i -E "s|--target=[A-Za-z0-9_.-]+|--target=${triple}${api}|g" Makefile
            sed -i -E "s|-D__ANDROID_API__=[0-9]+|-D__ANDROID_API__=${api}|g" Makefile

            echo "[$abi] Makefile 编译器: $(grep -E '^CC[[:space:]]*=' Makefile | head -n1)"
            grep -qE "^CC[[:space:]]*=.*${triple}${api}-clang" Makefile \
                || die "[$abi] Makefile CC 未指向 ${triple}${api}-clang，无法保证产物可在 API $api 设备加载"

            make -j"$JOBS" SHLIB_VERSION_NUMBER= SHLIB_EXT=.so build_libs
        )
        rm -rf "$out"
        mkdir -p "$out/include"
        cp -a "$src/libcrypto.so" "$out/libcrypto.so"
        # opensslconf.h 等由 Configure 按 ABI 生成在源码树里，必须按 ABI 分别安装
        cp -a "$src/include/openssl" "$out/include/openssl"
    fi

    if ! libcrypto_ok "$out/libcrypto.so"; then
        echo "[$abi] 构建结果仍引用了新 API 符号：" >&2
        "$NM" -D "$out/libcrypto.so" | awk '$(NF-1) == "U" { sub(/@.*/, "", $NF); print $NF }' \
            | grep -E "$NEW_API_SYMBOLS" >&2 || true
        die "[$abi] libcrypto.so 仍无法在老设备上加载，请检查 Configure 是否按 API $api 编译"
    fi

    echo "[$abi] NEEDED: $("$READELF" -d "$out/libcrypto.so" | grep NEEDED | sed 's/.*\[\(.*\)\].*/\1/' | tr '\n' ' ')"

    mkdir -p "$JNI_LIBS/$abi/include"
    cp -f "$out/libcrypto.so" "$JNI_LIBS/$abi/libcrypto.so"
    rm -rf "$JNI_LIBS/$abi/include/openssl"
    cp -a "$out/include/openssl" "$JNI_LIBS/$abi/include/openssl"
    echo "[$abi] 已安装到 $JNI_LIBS/$abi"
}

build_abi armeabi-v7a arm    armv7a-linux-androideabi 19
build_abi arm64-v8a    arm64  aarch64-linux-android   21
build_abi x86          x86    i686-linux-android      19
build_abi x86_64       x86_64 x86_64-linux-android    21
echo "全部 ABI 的 libcrypto.so 已更新：$JNI_LIBS"
