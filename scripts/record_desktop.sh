#!/bin/sh
# 仅录制指定窗口；请先打开游戏并取得当前窗口 ID。
# 用法：sh scripts/record_desktop.sh 窗口ID /tmp/gogogo-desktop.mov [秒数]
# macOS 需要为启动此命令的宿主 App 授予录屏权限。
set -eu
if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo "用法：sh scripts/record_desktop.sh 窗口ID 输出.mov [秒数，默认140]" >&2
    exit 2
fi
window_id="$1"
output="$2"
duration="${3:-140}"
case "$window_id" in
    ''|*[!0-9]*) echo "窗口 ID 必须为正整数。" >&2; exit 2 ;;
esac
case "$duration" in
    ''|*[!0-9]*) echo "时长必须为 1–300 秒的整数。" >&2; exit 2 ;;
esac
if [ "$window_id" -le 0 ] || [ "$duration" -lt 1 ] || [ "$duration" -gt 300 ]; then
    echo "窗口 ID 须大于零，时长须为 1–300 秒。" >&2
    exit 2
fi
case "$output" in
    *.mov) ;;
    *) echo "原始录制文件请使用 .mov 后缀。" >&2; exit 2 ;;
esac
if [ -e "$output" ]; then
    echo "输出文件已存在，拒绝覆盖：$output" >&2
    exit 2
fi
printf '仅录制窗口 %s；%s 秒后自动保存。请勿按 Ctrl-C，否则可能无法保存。\n' "$window_id" "$duration"
exec /usr/sbin/screencapture -v "-l$window_id" "-V$duration" -k -x "$output"
