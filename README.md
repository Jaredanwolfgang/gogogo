# GOGOGO 棋类对战平台

面向对象技术与应用大作业第一阶段。Python 实现五子棋、围棋本地双人对战，包含控制台、可选 Tkinter 图形界面、JSON 存档、自动测试、设计报告与演示视频。

[观看桌面操作录屏（1 分 50 秒）](results/desktop-demo.mp4) · [设计报告](docs/design.pdf)

## 运行

控制台和测试仅依赖 Python 3.9+ 标准库，无须安装 pip 包。在本地课程目录中执行：

```sh
cd project
python3 main.py
```

从 GitHub 单独克隆时，仓库根目录就对应本地的 `project`：

```sh
git clone git@github.com:Jaredanwolfgang/gogogo.git
cd gogogo
python3 main.py
python3 -m unittest discover -s tests -v
```

图形模式需要带 Tk 的 Python：

```sh
python3 main.py --gui
# macOS Homebrew 的 Python 3.12 可使用：
brew install python-tk@3.12
python3.12 main.py --gui
```

macOS 系统 Python 自带的旧 Tk 8.5 可能显示空白窗口，请使用更新的 Tk。没有图形环境时使用控制台。GUI 提供游戏类型与棋盘大小选择、点击交叉点落子、重开、悔棋、虚着、认负、存取文件和提示开关，也支持底部输入命令。

## 命令

| 指令 | 功能 |
| --- | --- |
| `new gomoku 15` / `new go 9` | 未开始或终局后创建对局；边长为 8–19 |
| `restart` | 按原游戏类型和边长重开，重置历史与悔棋额度 |
| `play 3 4` | 在第 3 行第 4 列落子；坐标均从 1 开始 |
| `pass` | 围棋虚着；五子棋拒绝此指令 |
| `undo` | 撤销最近一次落子、虚着或认负；全局合计限 3 次 |
| `resign` | 当前行棋方认负 |
| `save "my game.json"` | 保存棋盘、历史、轮次、提子、终局与悔棋额度 |
| `load "my game.json"` | 校验成功后覆盖当前对局；失败时保留原局面 |
| `hints off` / `hints on` / `help` | 隐藏或重新显示操作提示 |
| `show` / `quit` | 刷新局面 / 退出 |

所有指令均有反馈。路径相对于启动程序的工作目录，父目录须已存在；含空格的路径请加引号。退出不自动保存。

## 规则约定

- 两个游戏均黑先白后，方形棋盘大小为 8–19。
- 五子棋采用自由规则：横、竖、两斜线的五子或长连获胜，无禁手。满盘且无人连五为平局。
- 围棋支持整块提子、同时提多块、禁自杀、全局同形禁入（positional superko）。先提敌方无气棋块，再判断己方气；虚着不受同形限制。
- 围棋采用面积计分：盘上己方棋子数 + 仅与己方相邻的连通空域；双方共同接触的空域及无边界空域均为中立，白贴 7.5 点。提子数只显示，不重复加入面积分。
- 双方连续虚着或双方均无合法落点时自动计分。只有一方无合法落点时可以虚着，不自动终局。
- 为避免自动误判复杂死活，双方应先实际提净死子，再连续虚着。系统不实现赛制中的死活协商、争议恢复、让子和自动死子标记；直接双虚着表示接受当前盘面计分。这是课程平台明确采用的简化终局流程，不能替代完整赛事裁判。
- 悔棋每局双方合计 3 次，每次撤销一个动作；允许撤销终局动作。已撤销的未来棋盘从同形历史中移除。存档重放保留已经消耗的额度。
- 单局记录上限 5000 个成功动作（含悔棋）；存档读取上限 2 MiB。版本 1 固定上述规则参数。

规则依据与实现边界详见[设计文档](docs/design.md)。

## 文件

```text
gogogo/             领域模型、规则、应用门面、存档与两个客户端
tests/              unittest 单元测试与命令行集成测试
docs/design.md      设计说明与 Mermaid UML 源码
docs/design.typ     可编辑报告源文件
docs/design.pdf     可提交的设计报告
docs/architecture.svg  UML 类图
results/tests.txt   实际自动测试记录
results/desktop-demo.mp4  1 分 50 秒的游戏窗口实际录屏
results/desktop-demo.srt  桌面演示中文字幕
results/desktop-save.json 桌面操作保存的局面
results/demo.mp4    3 分 44 秒的真实命令回放视频
results/demo-transcript.txt  完整输入与输出
results/demo-save.json       提子后存档样例
scripts/demo.py     演示记录与视频生成脚本
scripts/record_desktop.sh macOS 指定窗口录屏脚本
```

## 重现验证与演示

```sh
python3 -m unittest discover -s tests -v
python3 scripts/demo.py
# 只有重新生成视频时需要 Pillow、FFmpeg 和中文字体：
python3 scripts/demo.py --video
# 非 macOS：指定本机 CJK 字体
python3 scripts/demo.py --video --font /path/to/CJK-font.ttf
# 重新生成设计报告需要 Typst
typst compile docs/design.typ docs/design.pdf
```

`results/desktop-demo.mp4` 是真实 Tkinter 游戏窗口录屏，通过桌面键盘输入和确认对话框操作，覆盖五子棋、围棋提子、禁自杀、悔棋、存档恢复、提示开关、计分及认负。仅捕获游戏窗口，无音轨；裁掉窗口外围黑边与结尾空等时段，未重绘游戏画面。录制方法及章节见[桌面录屏说明](docs/gui-recording.md)。

原 `results/demo.mp4` 继续作为补充：脚本执行真实 `ConsoleClient` 命令，将输出生成带说明文字的自动回放，包含劫争和悔棋额度等额外场景。完整日志包含提示开关后的实际界面。

## 提交材料

仓库：[Jaredanwolfgang/gogogo](https://github.com/Jaredanwolfgang/gogogo)。演示视频：[桌面操作录屏](results/desktop-demo.mp4)。提交前请将视频上传至清华网盘，把分享链接填写到 `docs/submission.json`，然后重新编译报告；按课程要求将报告提交网络学堂。网盘分享和学堂提交尚未执行，报告不会虚构这两个步骤的完成状态。
