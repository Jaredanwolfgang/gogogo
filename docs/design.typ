#set document(title: "棋类对战平台第一阶段设计报告")
#set page(paper: "a4", margin: (top: 19mm, bottom: 18mm, left: 21mm, right: 21mm), numbering: "1",
  header: align(right, text(size: 8pt, fill: luma(45%))[GOGOGO · 面向对象技术与应用]))
#set text(font: ("New Computer Modern", "Songti SC"), size: 10.5pt, lang: "zh")
#set par(justify: true, leading: 0.65em, spacing: 0.65em)
#set heading(numbering: "1.1")
#show heading.where(level: 1): set text(size: 14pt, weight: "bold")
#show heading.where(level: 2): set text(size: 11.5pt, weight: "bold")
#show raw: set text(font: ("Menlo", "Songti SC"), size: 8.3pt)
#let tab(..items) = table(columns: (1.1fr, 2.5fr), inset: 7pt, stroke: 0.5pt + luma(80%),
  fill: (x, y) => if y == 0 { luma(92%) } else { none }, ..items)
#let submission = json("submission.json")
#align(center)[
  #v(7mm)
  #text(size: 22pt, weight: "bold")[棋类对战平台]
  #v(3mm)
  #text(size: 16pt)[第一阶段设计报告]
  #v(4mm)
  Python 3.9+ · 五子棋与围棋 · 本地双人对战
]
#v(5mm)
本项目完成五子棋与围棋的控制台对战、局面管理、终局判断、悔棋和存档，并提供可选 Tkinter 图形界面。后端以规则策略和不可变状态组织逻辑，两个客户端共用同一应用接口。自动测试包含 33 项，1 分 50 秒桌面录屏及补充命令回放随仓库提供。

= 需求范围与规则约定
#tab([需求], [实现],
  [两种棋类与黑白交替], [`GameFactory` 创建策略会话，黑先白后],
  [开始与重开], [棋盘边长 8–19；未开始或终局后 new，进行中 restart],
  [提子与终局], [整块提子、禁自杀、全局同形、虚着计分、连五、满盘平局、认负],
  [悔棋与存档], [一步快照恢复，双方合计每局 3 次；JSON 重放验证后覆盖局面],
  [界面和异常反馈], [状态、棋盘、反馈、帮助四组件；可隐藏和显示提示],
  [可选 GUI], [Canvas 棋盘、鼠标落子、按钮操作和文件对话框],
)

五子棋采用自由规则：横、竖、两斜线五子或长连获胜，无禁手，先判胜再判满盘平局。围棋采用面积计分，棋子与单方围住的空域各计 1 点，白贴 7.5；被提子数仅显示，不重复加分。双方连续虚着或双方均无合法落点时结算，一方无合法落点可以虚着。

围棋先提敌子、再判自杀，落子不得重复未撤销历史中的棋盘；虚着豁免同形检查。双虚着前应实际提净死子；本阶段没有自动死活识别、死子协商、让子及争议裁定。直接双虚着表示接受当前盘面。采用现行面积计分原理，但终局流程是课程范围内的简化实现。

#pagebreak()
= 架构与设计模式
#figure(image("architecture.svg", width: 100%), caption: [核心 UML 类图。空心三角表示继承，实心菱形表示组合，箭头表示关联。])

*策略与简单工厂。* `RuleStrategy` 抽象落子和终局算法；`GomokuRules`、`GoRules` 实现不同规则。`GameFactory` 的注册表统一创建会话并复用规则对象。这是注册式简单工厂，不是基于工厂方法继承层次的实现。

*备忘录。* `GameState` 和 `Board` 不可变，会话保存状态历史。撤销末状态即可同时恢复棋盘、提子数、轮次、虚着与终局结果；悔棋计数在快照外独立维护，防止额度被一并回退。

*门面。* `GameService` 统一提供 new、restart、play、undo、save、load 等接口。控制台负责解析与反馈；GUI 复用控制台的命令控制器，不自行判断提子和胜负。

*对象复用。* `Stone` 枚举共享棋子值；规则实例不含对局状态，由工厂复用。虚着、认负快照共享棋盘，界面组件只构建一次。没有可变全局对局，也不为本地双人游戏引入单例。

#pagebreak()
= 界面建造与面向对象原则
`ViewDirector` 先决定布局顺序，`ViewBuilder` 记录组件类型，最后 build 实例化组件并组成 `ConsoleView`。状态、棋盘、反馈、帮助均实现 `Component.render(client)`；组合本身也实现同一接口。隐藏提示由帮助组件输出状态决定，不重建整个界面。

#align(center)[
  ViewDirector → ViewBuilder → ConsoleView\
  #v(2mm)
  ConsoleView ◆── Component «abstract»\
  #v(2mm)
  △ StatusComponent / BoardComponent / FeedbackComponent / HelpComponent
]

单一职责落实为模型、规则、会话、仓库和客户端分离。开闭原则落实为规则注册和显示组件组合。里氏替换要求规则策略使用相同参数与返回类型，拒绝操作统一抛出 `GameError`。会话依赖抽象策略，服务允许注入工厂和仓库；仓库通过鸭子类型协议替换。增加需要“移动棋子”的新棋种仍须扩展命令接口，不假定后续需求全部能够零修改实现。

== 关键类与函数
#tab([类与函数], [职责],
  [`Board`], [`empty/index` 校验棋盘与坐标；`group/neighbors` 搜索棋块及气],
  [`GomokuRules.outcome`], [从最后落点向四方向双向延伸，检查连五和满盘],
  [`GoRules.place`], [暂放棋子、邻块提子、检查自杀与同形，返回新棋盘和提子数],
  [`GoRules.score/outcome`], [搜索空域计分，检查连续虚着和双方可落点],
  [`GameSession`], [`play/pass_turn/resign` 生成快照；`undo` 恢复；`seen` 给出有效历史],
  [`GameService`], [检查生命周期；读档成功后一次性替换当前会话],
  [`JsonGameRepository`], [原子保存，有界读取，严格解析并重放动作],
  [`ConsoleClient`], [`shlex` 解析路径与参数，循环输入，统一异常反馈],
  [`GuiClient`], [`click` 转换坐标；`dispatch` 发送命令；`draw` 绘图],
)

GUI 先声明按钮及命令映射，再创建控件和绑定回调。`gui_view.py` 只读生成棋局摘要及居中坐标；右侧分为当前棋局、最近操作和可折叠提示。最后落子标记随悔棋和读档恢复；新建和读档同步类型与尺寸，较小窗口支持右侧滚动。图形模式依赖可用的 Tk；macOS 系统 Tk 8.5 的空白窗口问题通过 Python 3.12 配套 Tk 解决。控制台与自动测试无需图形环境。

#pagebreak()
= 算法与持久化一致性
== 围棋提子与面积计分
棋块采用迭代栈进行四邻接搜索，同时收集相邻空点作为气。暂放棋子后先找出邻接的所有无气敌方棋块，统一删除，再检查己方气，允许通过提子获得气。对比整个棋盘元组实现 positional superko，不包含轮次；悔棋后的未来分支不再参与对比。

计分时每个空域仅访问一次，收集与其接触的颜色。只有一种邻接颜色时归该方，双颜色或无颜色空域为中立。双方都无合法落点才自动结束，不能用“当前方不能落子”代替“双方面临终局”。

设棋盘边长 n，交叉点 B=n²，历史长度 H。连五检查 O(n)，棋块搜索与计分 O(B)，最坏合法落点枚举 O(B²)。当前实现每次动作构造同形集合 O(HB)，历史快照空间 O(HB)。最大棋盘为 19×19，事件日志上限 5000。虚着和认负复用原棋盘，悔棋不复制历史。

== JSON 格式与读档事务
版本 1 含 version、game、size、events、position。events 保存 play、pass、resign、undo 的实际成功顺序，position 保存声明的最终棋盘、轮次、提子、连续虚着、结果、手数及悔棋额度。规则参数在版本 1 固定。

读取在独立新会话中重放全部历史，以正常规则验证每个动作，然后用规范 JSON 对比最终局面。布尔值不能冒充整数，非法动作、未知字段、重复键、NaN、非法编码、深层嵌套及超过 2 MiB 的文件均被拒绝。重放成功才覆盖当前局面，失败时原会话保留。该检查验证合法性和一致性，不是来源签名。

保存先在目标同目录写临时文件，flush 与 fsync 后原子替换；失败保留原文件并清理临时文件。父目录必须存在；不使用 pickle 或可执行对象反序列化。

== 异常由哪一层处理
#tab([层次], [典型异常与行为],
  [客户端], [未知指令、参数数量、整数格式、引号不匹配；输出提示],
  [会话与规则后端], [越界、占点、自杀、同形、终局落子、无子可悔、次数超限；状态不变],
  [服务], [进行中创建新局、未开始操作；维护生命周期],
  [文件仓库], [读写失败、损坏和非法存档；不替换当前会话],
)

#pagebreak()
= 测试输入与实际输出
33 项自动测试在 Python 3.9 和 Python 3.12 中通过，包含子进程完整五子棋对局。完整输出保存在 `results/tests.txt` 与 `tests-python312.txt`。下表坐标为一基；直接构造盘面的测试为隔离规则测试。

#tab([测试输入], [实际输出或断言],
  [`new go 7`], [拒绝：棋盘边长必须是 8 到 19 的整数],
  [已落点再次 play], [拒绝占用位置，棋盘、轮次、历史保持不变],
  [黑 (1,1..5)，白 (3,1..4)], [黑方 X 获胜；连成五子],
  [四方向连续五子、白长连六子], [全部返回对应颜色获胜],
  [无五连的 8×8 满盘], [棋盘已满，平局],
  [围棋 (1,2),(1,1),(8,8), (7,7),(2,1)], [黑提 1 子，白 (1,1) 消失],
  [接上例白 play 1 1], [拒绝自杀，不改变局面],
  [接上例 undo], [白 (1,1) 复原，黑提子恢复为 0，轮到黑],
  [劫形立即回提], [拒绝全局同形；其他处应劫后可合法回提],
  [提子后 save → restart → load], [棋盘、轮次、历史与剩余悔棋额度一致],
  [示例提子局面 pass、pass], [白胜；面积得分黑 4，白 8.5],
  [超过三次悔棋], [悔棋次数超过限制；局面不变],
  [损坏 JSON、重复键、伪造盘面], [读取失败；原会话对象不变],
  [模拟磁盘替换失败], [保存失败；旧文件字节不变，无残留临时文件],
)

还覆盖整块与多块同时提子、提子先于自杀判断、较早历史同形、双方无合法落点终局、单方无合法落点继续、虚着恢复、认负恢复、中文空格路径和 EOF 正常退出。自动测试无需桌面。

新增 4 项测试覆盖展示状态的悔棋、读档、终局和棋盘缩放坐标。GUI 补充验证结果记录在 `results/gui-check.txt`。实现没有 AI 对手、网络联机或计时赛制；它们不属于当前第一阶段需求。

#pagebreak()
= 运行 演示与提交
在本地课程目录中执行 `cd project`；独立克隆时进入 `gogogo`，它对应本地 project 目录。
```sh
python3 main.py
python3.12 main.py --gui
python3 -m unittest discover -s tests -v
python3 scripts/demo.py
```

new gomoku 15 或 new go 9 开始新局；play 行 列 落子；pass 虚着；undo 悔棋；resign 认负；restart 重开；save 文件、load 文件 保存读取；hints on/off 控制提示；help 显示帮助；quit 退出。带空格路径须加引号，退出不自动保存。

== 演示视频
旧版界面的主视频 `results/desktop-demo.mp4` 长 110 秒（1 分 50 秒），H.264，1600×1226，仅录制实际 Tkinter 游戏窗口。使用桌面键盘输入和确认对话框，无音轨；裁掉外围黑边与结尾空等时段，未重绘游戏画面。

#tab([时间], [主要内容],
  [0:00–0:30], [五子棋轮流落子、占用位置提示、悔棋和连五获胜],
  [0:30–0:55], [围棋开局、角部提子、禁自杀和悔棋恢复棋子],
  [0:55–1:17], [保存、重开、读取局面和历史、隐藏与显示帮助],
  [1:17–1:50], [连续虚着、面积计分、19×19 棋盘与认负],
)

补充视频 `results/demo.mp4` 长 224 秒，是 56 个实际命令输出的自动回放，另含劫争、未知指令与悔棋额度场景；文字日志及生成脚本一并保留。新版 UI 的逐步操作和解说见 `docs/recording-script.md`，可自行录制约四分钟演示。

== 仓库与提交链接
代码仓库：#link(submission.repository_url)[Jaredanwolfgang/gogogo]

演示视频：#link(submission.repository_video_url)[GitHub 中的 MP4 文件]

清华网盘：#if submission.cloud_video_url == "" {[尚未上传，分享链接待本人填写。]} else {link(submission.cloud_video_url)}

作业要求将视频上传清华网盘，并将仓库链接和网盘链接附于设计文档后提交网络学堂。网盘和学堂步骤尚未执行。填写 `docs/submission.json` 的 cloud_video_url 后，执行 `typst compile docs/design.typ docs/design.pdf` 更新报告。

== 规则参考
1. #link("https://gomocup.org/detail-information/")[Gomocup Detail Information]：自由五子棋的五子或长连获胜。
2. #link("https://www.britgo.org/intro/intro2.html")[British Go Association How to Play]：气、提子、禁自杀、劫与虚着。
3. #link("https://media-iframe.britgo.org/rules/agarules.html")[BGA AGA Rules Definition]：面积计分与领地计分。
4. #link("https://britgo.org/rules/compare.html")[BGA Comparison of Some Go Rules]：规则体系与重复局面处理。

参考日期：2026 年 11 月 24 日。本文依据基础规则资料，并明确区分课程实现中的终局、悔棋约定与完整赛事规则。
