#!/usr/bin/env bash
# 校验一个 libcrypto.so 是否能在低版本 Android（API 19 ~ 当前）设备上 dlopen。
#
# 检查项：
#   1) 必须导出 n2n 直接引用的 OpenSSL 符号（缺失 → 运行期 undefined symbol）
#   2) 不得存在落在禁用名单里的“强”未定义符号：
#      这些符号要么老系统 libc 里没有，要么在新系统里已被删除
#      （典型：__register_atfork —— Android 4.x 的 libc 私有符号，Android 5.0 起被移除）
#   3) 弱未定义符号（如 getentropy）不算失败：弱符号解析不到时取 NULL，不影响加载
#
# 用法: bash check-libcrypto.sh <libcrypto.so> [llvm-nm] [llvm-readelf]
#
# 环境变量：
#   CHECK_MODE=undef  只检查“危险未定义符号”，不检查必需导出符号。
#                      用于校验 APK 里那些“使用”而不是“提供”OpenSSL 的库
#                      （edge_v2 / edge_v3 / edge_jni 等）。
set -uo pipefail

LIB="${1:-}"
NM="${2:-}"
READELF="${3:-}"
CHECK_MODE="${CHECK_MODE:-full}"

if [ -z "$LIB" ] || [ ! -f "$LIB" ]; then
    echo "用法: $0 <libcrypto.so> [llvm-nm] [llvm-readelf]" >&2
    exit 2
fi

if [ -z "$NM" ]; then
    NM="$(command -v llvm-nm 2>/dev/null || command -v nm 2>/dev/null || true)"
fi
if [ -z "$READELF" ]; then
    READELF="$(command -v llvm-readelf 2>/dev/null || command -v readelf 2>/dev/null || true)"
fi
if [ -z "$NM" ]; then
    echo "ERROR: 找不到 llvm-nm / nm" >&2
    exit 2
fi

# n2n(edge_v2/edge_v3) 直接引用的 OpenSSL 符号
REQUIRED_SYMBOLS=(
    EVP_CIPHER_CTX_new
    EVP_CIPHER_CTX_free
    EVP_CIPHER_CTX_reset
    EVP_CIPHER_CTX_set_padding
    EVP_EncryptInit_ex
    EVP_EncryptUpdate
    EVP_EncryptFinal_ex
    EVP_DecryptInit_ex
    EVP_DecryptUpdate
    EVP_DecryptFinal_ex
    EVP_aes_128_cbc
    EVP_aes_192_cbc
    EVP_aes_256_cbc
    EVP_chacha20
    BIO_new
    BIO_s_mem
    BIO_free
    BIO_ctrl
)

# 强未定义符号禁用名单：出现在这里就说明产物在某些 Android 版本上 dlopen 会失败
FORBIDDEN_UNDEF=(
    __register_atfork
    pthread_atfork
    getentropy
    getrandom
    arc4random_buf
    arc4random_uniform
    pthread_getname_np
    closefrom
)

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
DEF="$TMP/defined.txt"
UNDEF="$TMP/undefined.txt"
WEAK="$TMP/weak.txt"
RAW="$TMP/raw.txt"
: > "$DEF"
: > "$UNDEF"
: > "$WEAK"

if ! "$NM" -D "$LIB" > "$RAW" 2>"$TMP/nm.err"; then
    echo "ERROR: $NM -D $LIB 执行失败" >&2
    cat "$TMP/nm.err" >&2
    exit 2
fi

# 解析动态符号表：
#   "<addr> <type> <name>"  → 已定义
#   "         U <name>"    → 强未定义
#   "         w <name>"    → 弱未定义
# 符号名可能带版本后缀（name@@VER），统一去掉。
awk -v def="$DEF" -v undef="$UNDEF" -v weak="$WEAK" '
    NF < 2 { next }
    {
        t = $(NF-1); n = $NF;
        sub(/@.*/, "", n);
        if (t == "U")      { print n >> undef; next }
        if (t == "w")      { print n >> weak;  next }
        print n >> def
    }
' "$RAW"

def_count="$(wc -l < "$DEF" | tr -d ' ')"
undef_count="$(wc -l < "$UNDEF" | tr -d ' ')"
weak_count="$(wc -l < "$WEAK" | tr -d ' ')"

echo "[check-libcrypto] $LIB"
echo "[check-libcrypto] 已导出符号: $def_count  强未定义: $undef_count  弱未定义: $weak_count"

rc=0

# 1) 必需导出符号
missing=""
if [ "$CHECK_MODE" != "undef" ]; then
    for sym in "${REQUIRED_SYMBOLS[@]}"; do
        if ! grep -qxF -- "$sym" "$DEF"; then
            missing="$missing $sym"
        fi
    done
    if [ -n "$missing" ]; then
        echo "[check-libcrypto] 缺少必需导出符号：$missing" >&2
        rc=1
    else
        echo "[check-libcrypto] 必需导出符号齐全（${#REQUIRED_SYMBOLS[@]} 个）"
    fi
fi

# 2) 危险的强未定义符号
printf '%s\n' "${FORBIDDEN_UNDEF[@]}" > "$TMP/forbidden.txt"

# 用 readelf 复核绑定：llvm-nm 理论上已区分强/弱未定义，这里只是兜底，
# 避免把 WEAK（弱符号，解析不到时取 NULL，不影响加载）误判为致命问题。
is_weak_undef() {
    [ -n "$READELF" ] && [ -x "$READELF" ] || return 1
    "$READELF" --dyn-syms "$LIB" 2>/dev/null | awk -v s="$1" -v at="@" '
        $0 ~ /WEAK/ {
            m = split($NF, a, at)
            if (a[1] == s) { found = 1 }
        }
        END { exit(found ? 0 : 1) }
    '
}

hit=""
warn=""
while IFS= read -r sym; do
    [ -n "$sym" ] || continue
    if grep -qxF -- "$sym" "$UNDEF"; then
        if is_weak_undef "$sym"; then
            warn="$warn $sym(弱符号)"
        else
            hit="$hit $sym"
        fi
    fi
done < "$TMP/forbidden.txt"
if [ -n "$hit" ]; then
    echo "[check-libcrypto] 引用了老系统 libc 不存在 / 新系统已删除的符号：$hit" >&2
    rc=1
else
    echo "[check-libcrypto] 无危险未定义符号"
fi
if [ -n "$warn" ]; then
    echo "[check-libcrypto] 以下符号为弱引用，不影响 dlopen：$warn"
fi

# 3) 弱未定义符号只提示（解析不到时取 NULL，不影响 dlopen）
if [ "$weak_count" -gt 0 ]; then
    weak_list=$(tr '\n' ' ' < "$WEAK")
    echo "[check-libcrypto] 弱未定义符号（可忽略）：$weak_list"
fi

# 4) 依赖与标志位，方便排查
if [ -n "$READELF" ] && [ -x "$READELF" ]; then
    needed=""
    needed=$("$READELF" -d "$LIB" 2>/dev/null | grep NEEDED | cut -d'[' -f2 | cut -d']' -f1 | tr '\n' ' ' || true)
    echo "[check-libcrypto] NEEDED: $needed"
    "$READELF" -d "$LIB" 2>/dev/null | grep -E '^\s*0x[0-9a-f]+\s+\(FLAGS' | sed 's/^/[check-libcrypto] /' || true
fi

if [ "$rc" -eq 0 ]; then
    echo "[check-libcrypto] 校验通过"
else
    echo "[check-libcrypto] 校验失败" >&2
fi
exit "$rc"
