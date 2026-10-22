#!/usr/bin/env bash
# 用低 Android API level 重新构建 OpenSSL 的 libcrypto.so，并安装到 jniLibs。
#
# 背景（修复 32 位老设备启动失败）：
#   jniLibs 里预置的 libcrypto.so 是用旧 NDK GCC 编译的，它引用了
#   __register_atfork —— 那是 Android 4.x libc 的私有符号，Android 5.0 起被删除。
#   又因为该库带 DF_1_NOW（加载时立即解析全部符号），
#   于是 Android 5.0 及以上的设备 dlopen("libcrypto.so") 直接失败，
#   依赖它的 edge_v2 / edge_v3 / edge_jni 全部抛 UnsatisfiedLinkError，
#   而不依赖 crypto 的其余 6 个库加载正常。
#
# 修复要点（缺一不可）：
#   1. 用 NDK 25.2（r26+ 已删除 API 19 支持）的 clang，按低 API 编译：
#      32 位 19 / 64 位 21；链接时用的是该 API 的 libc stub，
#      所以未定义符号必然存在于对应版本的系统里。
#   2. 屏蔽 OpenSSL 的 pthread_atfork 调用：
#      crypto/threads_pthread.c 在 OPENSSL_SYS_UNIX（Android 也定义）下会调用
#      pthread_atfork。API 19 的 NDK 头文件把它映射成 __register_atfork，
#      API 21+ 则直接引用 pthread_atfork —— 两者都会让产物在部分 Android 版本上
#      dlopen 失败（前者 Android 5.0+ 失败，后者 Android 4.4 失败）。
#      这里直接删掉该调用，使产物不再依赖任何 fork 相关符号。
#   3. 产物用 check-libcrypto.sh 校验：核心导出符号齐全 + 无危险未定义符号。
#
# 用法（需已安装 NDK 25.2.9519653）：
#   ANDROID_NDK_HOME=/path/to/ndk/25.2.9519653 bash hin2n/scripts/build-openssl-android.sh
set -euo pipefail

die() { echo "ERROR: $*" >&2; exit 1; }

OPENSSL_VERSION="${OPENSSL_VERSION:-1.1.1w}"
# 构建配方版本：改动构建步骤时递增，用来让旧的缓存产物失效
BUILD_RECIPE="3"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
JNI_LIBS="$ROOT/hin2n/Hin2n_android/app/src/main/jniLibs"
WORK="${WORK:-$ROOT/hin2n/.openssl-build}"
CHECKER="$SCRIPT_DIR/check-libcrypto.sh"

# NDK 选择：优先用 SDK 里显式安装的 25.2（与 app 的 ndkVersion 一致）。
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
    if [ -n "${ANDROID_NDK_HOME:-}" ]; then
        NDK="$ANDROID_NDK_HOME"
    elif [ -n "${ANDROID_NDK_ROOT:-}" ]; then
        NDK="$ANDROID_NDK_ROOT"
    else
        NDK="${HOME:-/root}/Android/Sdk/ndk/$NDK_VER"
    fi
fi
# 必须显式导出给 OpenSSL 的 Configure：它靠 ANDROID_NDK_HOME/ANDROID_NDK_ROOT
# 判断使用新版 NDK 布局；两者都未设置时会退回早已移除的 gcc 式工具链路径，
# 直接报 “no NDK arm-linux-androideabi-gcc on $PATH”。
export ANDROID_NDK_HOME="$NDK"
export ANDROID_NDK_ROOT="$NDK"
echo "使用 NDK: $NDK"
# NDK r26+ 已移除 API 19/20 支持（最低 API 21），无法为 32 位老设备产出可加载的库
if [ -f "$NDK/source.properties" ]; then
    _rev="$(sed -n 's/^Pkg\.Revision[[:space:]]*=[[:space:]]*//p' "$NDK/source.properties")"
    echo "NDK Pkg.Revision: $_rev"
    case "$_rev" in
        25.*|24.*|23.*|22.*|21.*) ;;
        *) die "NDK $_rev 不支持 API 19（r26+ 最低 API 21），请改用 25.2.9519653" ;;
    esac
fi
HOST_TAG="${HOST_TAG:-linux-x86_64}"
TOOLCHAIN="$NDK/toolchains/llvm/prebuilt/$HOST_TAG"
JOBS="$(nproc 2>/dev/null || echo 4)"
TARBALL="$WORK/openssl-$OPENSSL_VERSION.tar.gz"
TAG="OpenSSL_$(echo "$OPENSSL_VERSION" | tr . _)"
URLS=(
    "https://www.openssl.org/source/openssl-$OPENSSL_VERSION.tar.gz"
    "https://www.openssl.org/source/old/1.1.1/openssl-$OPENSSL_VERSION.tar.gz"
    "https://github.com/openssl/openssl/releases/download/$TAG/openssl-$OPENSSL_VERSION.tar.gz"
)

[ -d "$TOOLCHAIN" ] || die "未找到 NDK 工具链：$TOOLCHAIN（请设置 ANDROID_NDK_HOME）"
NM="$TOOLCHAIN/bin/llvm-nm"
READELF="$TOOLCHAIN/bin/llvm-readelf"
[ -x "$NM" ] || die "未找到 $NM"
[ -f "$CHECKER" ] || die "缺少校验脚本：$CHECKER"

# 校验 libcrypto.so（导出符号齐全 + 无危险未定义符号）
check_libcrypto() {
    bash "$CHECKER" "$1" "$NM" "$READELF"
}

fetch_tarball() {
    if [ -s "$TARBALL" ]; then
        return 0
    fi
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

# 删除 OpenSSL 的 pthread_atfork 调用。
# crypto/threads_pthread.c 的 fork_once_func() 里调用 pthread_atfork：
#   - API 19 头文件把 pthread_atfork 映射成 __register_atfork（Android 5.0 起被删除）
#   - API 21+ 直接引用 pthread_atfork（Android 4.4 没有）
# 两种情况都会让 libcrypto.so 在部分 Android 版本上 dlopen 失败。
# Android 应用基本不会 fork，去掉 fork 处理器没有实际影响。
patch_no_atfork() {
    local src="$1"
    local f="$src/crypto/threads_pthread.c"
    [ -f "$f" ] || die "找不到 $f"
    sed -i '/pthread_atfork(OPENSSL_fork_prepare,/d' "$f"
    sed -i '/OPENSSL_fork_parent, OPENSSL_fork_child);/d' "$f"
    if grep -q 'pthread_atfork' "$f"; then
        die "pthread_atfork 补丁失败，$f 仍引用 pthread_atfork"
    fi
    echo "[patch] 已移除 pthread_atfork 引用：crypto/threads_pthread.c"
}

build_abi() {
    local abi="$1" target="$2" triple="$3" api="$4"
    local out="$WORK/out/$abi"
    local src="$WORK/src-$abi"
    local stamp="$out/.built-api"
    local need_build=1

    # 缓存可复用条件：配方版本一致 + 产物校验通过。
    # 历史上 job 失败时 cache 也保存过残缺 so，那种产物必须强制重编。
    if [ -f "$stamp" ] && [ "$(cat "$stamp")" = "$api $BUILD_RECIPE" ]; then
        if check_libcrypto "$out/libcrypto.so"; then
            echo "[$abi] 使用缓存的构建结果：$out/libcrypto.so"
            need_build=0
        else
            echo "[$abi] 缓存产物校验不通过，重新编译"
        fi
    fi

    if [ "$need_build" = "1" ]; then
        echo "[$abi] 以 API $api 重新编译 OpenSSL $OPENSSL_VERSION ..."
        # 清掉可能被污染的旧产物，避免残留文件进入下一轮 cache
        rm -rf "$out" "$src"
        fetch_tarball
        # 快速失败：确认该 API 的 clang wrapper 在 NDK 里存在
        [ -x "$TOOLCHAIN/bin/${triple}${api}-clang" ] \
            || die "[$abi] NDK 中不存在 ${triple}${api}-clang（检查 NDK 版本/三元组拼写，32 位 ARM 是 armv7a-linux-androideabi）"
        mkdir -p "$src"
        tar -xf "$TARBALL" -C "$src" --strip-components=1
        patch_no_atfork "$src"
        (
            cd "$src"
            export PATH="$TOOLCHAIN/bin:$PATH"
            # ANDROID_API + 带 API 后缀的 clang wrapper 双保险，
            # 确保 bionic 头文件按低 API 做可用性裁剪
            export ANDROID_API="$api"
            # -D__ANDROID_API__ 会被 OpenSSL 的 android-* 配置读到，
            # 从而把编译器选成 <triple><api>-clang（否则会用 NDK 最高 API 的 clang）。
            # 注意：OpenSSL 的 android-* target 会忽略 CC 环境变量，自行选择编译器，
            # 所以 Configure 之后还要改写 Makefile 强制低 API，见下方 patch。
            CC="${triple}${api}-clang" ./Configure "android-$target" \
                -D__ANDROID_API__="$api" \
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

        # 校验产物；不通过时退回到“去掉版本脚本”的全量导出再链接一次
        if ! check_libcrypto "$src/libcrypto.so"; then
            echo "[$abi] 首次产物校验未通过，去掉版本脚本后全量导出并重新链接 ..." >&2
            (
                cd "$src"
                sed -i -E 's|-Wl,--version-script=[^ ]*||g' Makefile
                rm -f libcrypto.so libssl.so
                make -j"$JOBS" SHLIB_VERSION_NUMBER= SHLIB_EXT=.so build_libs
            )
        fi
        check_libcrypto "$src/libcrypto.so" \
            || die "[$abi] libcrypto.so 无法在老设备上加载，请检查 Configure 是否按 API $api 编译"

        rm -rf "$out"
        mkdir -p "$out/include"
        cp -a "$src/libcrypto.so" "$out/libcrypto.so"
        # opensslconf.h 等由 Configure 按 ABI 生成在源码树里，必须按 ABI 分别安装
        cp -a "$src/include/openssl" "$out/include/openssl"
        echo "$api $BUILD_RECIPE" > "$stamp"
    fi

    [ -s "$out/libcrypto.so" ] || die "[$abi] 未生成 libcrypto.so"

    needed=""
    if [ -x "$READELF" ]; then
        needed=$("$READELF" -d "$out/libcrypto.so" 2>/dev/null | grep NEEDED | tr '\n' ' ' || true)
    fi
    echo "[$abi] NEEDED: $needed"

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
