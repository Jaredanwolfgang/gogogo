"""执行真实命令，保存逐帧终端输出，可选生成小于五分钟的 MP4。"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gogogo.cli import ConsoleClient


def scenario():
    steps = [
        ("new go 7", "棋盘边长校验", "仅接受 8 至 19 的整数。非法指令不创建或修改对局。"),
        ("new gomoku 8", "开始五子棋", "X 为黑棋，O 为白棋。坐标从 1 开始，先行后列。"),
        ("play 1 1", "黑白交替落子", "落子成功后自动切换行棋方。"),
        ("play 1 1", "拒绝占用位置", "落子失败不会改变轮次、棋盘或历史。"),
        ("play 0 1", "拒绝越界坐标", "语法由客户端解析，棋盘边界由后端验证。"),
        ("play 3 1", "白方落子", "客户端通过统一接口调用游戏后端。"),
    ]
    for col in range(2, 5):
        steps.extend([(f"play 1 {col}", "五子棋双人对战", "水平、竖直和两条斜线均可连五获胜。"),
                      (f"play 3 {col}", "五子棋双人对战", "自由五子棋：无禁手，五子或长连获胜。")])
    steps += [
        ("play 1 5", "自动判断胜负", "黑方连成五子，系统结束对局并显示胜者。"),
        ("play 8 8", "终局后禁止落子", "结束状态不能继续行棋。可悔棋、重开或创建新局。"),
        ("undo", "终局也能悔棋", "撤销最后一手，同时恢复棋盘、轮次和未结束状态。"),
        ("resign", "投子认负", "当前行棋方认负，对方立即获胜。"),
        ("new go 8", "切换到围棋", "同一客户端与命令格式，后端更换规则策略。"),
        ("play 1 2", "准备提子演示", "围棋只按上下左右计算连接和气。"),
        ("play 1 1", "白棋位于角部", "角上的棋子最多只有两口气。"),
        ("play 8 8", "继续交替落子", "黑方在远处落子。"),
        ("play 7 7", "继续交替落子", "白方在远处落子。"),
        ("play 2 1", "自动提子", "封住最后一口气，白棋 (1,1) 被提走。"),
        ("play 1 1", "禁止自杀", "白方落子后无气且不能提子，操作被拒绝。"),
        ("undo", "悔棋恢复提子", "被提走的白棋复原，黑方提子数也恢复。"),
        ("play 2 1", "撤销后的分支", "撤销掉的未来局面不参与全局同形检查。"),
        ('save "results/demo-save.json"', "保存完整对局", "JSON 保存历史、局面和剩余悔棋次数；写入使用原子替换。"),
        ("restart", "重新开始", "保持游戏类型和棋盘大小，清空棋子和历史。"),
        ('load "results/demo-save.json"', "读取覆盖当前对局", "重放历史并验证结果，成功后一次性替换当前对局。"),
        ('load "results/not-found.json"', "文件错误反馈", "文件不存在时保留当前对局，不崩溃。"),
        ("pass", "围棋虚着", "不落子并交给对方；连续虚着计数加一。"),
        ("pass", "双方虚着后计分", "面积计分：棋子 + 单方围住的空域；白方贴 7.5 点。"),
        ("new go 8", "准备劫争演示", "全局同形规则阻止重复历史棋盘；虚着不受此限制。"),
    ]
    for command in ("play 1 2", "play 2 2", "play 2 1", "play 1 3", "play 3 2",
                    "play 3 3", "play 8 8", "play 2 4"):
        steps.append((command, "构造合法劫形", "双方按真实落子顺序形成劫争局面。"))
    steps += [
        ("play 2 3", "黑方提劫", "白棋 (2,2) 被提走，新下黑棋也只有一口气。"),
        ("play 2 2", "禁止立即回提", "如果立即回提，棋盘将重复历史局面，因此被拒绝。"),
        ("hints off", "隐藏操作提示", "隐藏帮助组件，仍保留状态、棋盘和操作反馈。"),
        ("help", "重新显示提示", "随时查看可用指令和围棋计分约定。"),
        ("oops", "未知指令处理", "每条输入都会得到反馈。"),
        ("restart", "检查悔棋限制", "每局双方合计最多悔棋三次，重开时重置。"),
        ("undo", "无历史可撤销", "空棋盘上的悔棋操作得到明确错误提示。"),
    ]
    for _ in range(3):
        steps.extend([("play 1 1", "检查悔棋限制", "落子后再撤销一步。"),
                      ("undo", "悔棋次数递减", "悔棋计数独立于棋盘快照，不会被悔棋恢复。")])
    steps += [("play 1 1", "达到悔棋限制", "三次额度已经全部使用。"),
              ("undo", "超过次数被拒绝", "读档会恢复原额度，不能通过保存读取重置额度。"),
              ("quit", "演示完成", "代码、设计文档、自动测试与本演示均可在仓库中复现。")]
    return steps


def video(frames, output, font_path):
    from PIL import Image, ImageDraw, ImageFont
    font_path = font_path or "/System/Library/Fonts/STHeiti Medium.ttc"
    body = ImageFont.truetype(font_path, 26)
    title = ImageFont.truetype(font_path, 40)
    small = ImageFont.truetype(font_path, 21)
    mono = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc" if sys.platform == "darwin" else font_path, 26)
    with tempfile.TemporaryDirectory(prefix="gogogo-video-") as directory:
        root = Path(directory)
        for number, frame in enumerate(frames):
            canvas = Image.new("RGB", (1600, 1000), "#eef1e9")
            draw = ImageDraw.Draw(canvas)
            draw.text((54, 32), "GOGOGO  /  第一阶段功能演示", font=title, fill="#183b31")
            draw.text((56, 92), "由实际程序输出生成的命令回放 · Python 3.9+ · 黑棋 X / 白棋 O", font=small, fill="#536258")
            draw.rounded_rectangle((40, 145, 1095, 925), radius=14, fill="#19231e")
            draw.text((65, 166), "> " + frame["command"], font=mono, fill="#b9deb0")
            y = 220
            for line in frame["screen"].splitlines():
                # 棋盘字符使用等宽字体；中文状态使用 CJK 字体。
                face = mono if line and all(ord(char) < 128 for char in line) else body
                for wrapped in textwrap.wrap(line, width=63 if face == mono else 38) or [""]:
                    draw.text((65, y), wrapped, font=face, fill="#f0f4eb")
                    y += 32
            draw.text((1130, 180), f"{number + 1:02d} / {len(frames):02d}", font=small, fill="#5d7161")
            y = 238
            for line in textwrap.wrap(frame["title"], width=10):
                draw.text((1130, y), line, font=title, fill="#183b31")
                y += 55
            y += 28
            for line in textwrap.wrap(frame["note"], width=13):
                draw.text((1130, y), line, font=body, fill="#41594a")
                y += 40
            draw.rectangle((40, 955, 40 + int(1520 * (number + 1) / len(frames)), 961), fill="#527b56")
            canvas.save(root / f"frame-{number:03d}.png")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", "1/4",
                        "-i", str(root / "frame-%03d.png"), "-vf", "fps=24,format=yuv420p",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "24", "-movflags", "+faststart",
                        str(output)], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", action="store_true", help="使用 Pillow 和 FFmpeg 生成 MP4")
    parser.add_argument("--font", help="CJK 字体路径，非 macOS 环境需要提供")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    results = root / "results"
    results.mkdir(exist_ok=True)
    client, frames, transcript = ConsoleClient(), [], []
    for command, title, note in scenario():
        client.execute(command)
        # 视频仅展示真实输出；隐藏长帮助正文，帮助状态仍记录在完整日志中。
        screen = "\n\n".join(component.render(client) for component in client.view.components[:3])
        frames.append({"command": command, "title": title, "note": note, "screen": screen})
        transcript.append(f"> {command}\n{client.view.render(client)}\n")
    (results / "demo-transcript.txt").write_text("\n".join(transcript), encoding="utf-8")
    (results / "demo-frames.json").write_text(json.dumps(frames, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.video:
        video(frames, results / "demo.mp4", args.font)
    print(f"已生成 {len(frames)} 步真实命令记录；视频时长 {len(frames) * 4} 秒。")


if __name__ == "__main__":
    main()
