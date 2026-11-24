"""Tkinter 桌面客户端：棋盘、对局信息与操作反馈分区展示。"""
import shlex
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .cli import ConsoleClient
from .gui_view import BoardLayout, game_overview
from .model import Stone


BG, CARD, INK = "#f3f2ed", "#ffffff", "#243e35"
MUTED, GREEN, LINE = "#68776e", "#315f4d", "#e0e5de"
WOOD, GRID = "#e8c995", "#a18456"
KINDS = {"五子棋": "gomoku", "围棋": "go"}


class GuiClient:
    def __init__(self, root):
        self.root, self.client = root, ConsoleClient()
        self._displayed_session = None
        self.overview = game_overview(None)
        root.title("GOGOGO · 五子棋与围棋")
        root.geometry("1120x800")
        root.minsize(980, 740)
        root.configure(bg=BG)
        self.configure_styles()
        # 先声明组件及命令映射，再创建布局和绑定事件。
        self.toolbar_design = (("悔棋", "undo"), ("重新开始", "restart"),
                               ("虚着", "pass"), ("认负", "resign"))
        self.build()
        self.refresh()

    def configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", font=("Helvetica", 12), foreground=INK, background=BG)
        style.configure("TFrame", background=BG)
        style.configure("TButton", padding=(14, 9), background=CARD, borderwidth=0,
                        lightcolor=CARD, darkcolor=CARD, focusthickness=1, focuscolor=GREEN)
        style.map("TButton", background=[("active", "#e8eee7")], foreground=[("disabled", "#a8b0aa")])
        style.configure("Primary.TButton", background=GREEN, foreground="white")
        style.map("Primary.TButton", background=[("disabled", "#dfe5de"), ("active", "#234b3c")],
                  foreground=[("disabled", "#8a978d"), ("!disabled", "white")])
        style.configure("Quiet.TButton", background=BG, foreground=MUTED, padding=(10, 8))
        style.configure("Link.TButton", background=CARD, foreground=GREEN, padding=(4, 0))
        style.configure("TEntry", padding=8, fieldbackground=CARD, bordercolor=LINE,
                        lightcolor=LINE, darkcolor=LINE)
        style.configure("TCombobox", padding=7, fieldbackground=CARD, background=CARD,
                        bordercolor=LINE, arrowsize=13)
        style.map("TCombobox", fieldbackground=[("readonly", CARD)])
        style.configure("TSpinbox", padding=7, fieldbackground=CARD, background=CARD,
                        bordercolor=LINE, arrowsize=12)
        style.configure("Slim.Vertical.TScrollbar", width=9, arrowsize=9,
                        background="#c8d2c7", troughcolor=BG, borderwidth=0)
        style.layout("Slim.Vertical.TScrollbar", [
            ("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
                ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])

    @staticmethod
    def label(parent, text="", size=12, color=INK, bold=False, **kwargs):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color,
                        font=("Helvetica", size, "bold" if bold else "normal"),
                        anchor="w", justify="left", **kwargs)

    def card(self, parent, color=CARD):
        frame = tk.Frame(parent, bg=color, highlightbackground=LINE, highlightthickness=1)
        inner = tk.Frame(frame, bg=color, padx=18, pady=15)
        inner.pack(fill="both", expand=True)
        return frame, inner

    def build(self):
        outer = tk.Frame(self.root, bg=BG, padx=26, pady=20)
        outer.pack(fill="both", expand=True)
        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x", pady=(0, 18))
        self.label(header, "GOGOGO", size=26, bold=True).pack(side="left")
        self.label(header, "一盘棋，一次专注。", color=MUTED).pack(side="left", padx=18, pady=(6, 0))
        self.label(header, "五子棋 / 围棋   ·   本地双人", size=11, color=MUTED).pack(side="right")

        setup = tk.Frame(outer, bg=BG)
        setup.pack(fill="x", pady=(0, 16))
        self.label(setup, "棋类", size=11, color=MUTED).pack(side="left", padx=(0, 8))
        self.kind = ttk.Combobox(setup, values=tuple(KINDS), width=8, state="readonly")
        self.kind.set("五子棋")
        self.kind.pack(side="left")
        self.label(setup, "棋盘", size=11, color=MUTED).pack(side="left", padx=(18, 8))
        self.size = ttk.Spinbox(setup, from_=8, to=19, width=4)
        self.size.set("15")
        self.size.pack(side="left")
        self.label(setup, "路", size=11, color=MUTED).pack(side="left", padx=(6, 18))
        self.new_button = ttk.Button(setup, text="开始新局", style="Primary.TButton", command=self.new)
        self.new_button.pack(side="left")
        ttk.Button(setup, text="读取存档", style="Quiet.TButton", command=self.load).pack(side="right")
        self.save_button = ttk.Button(setup, text="保存对局", style="Quiet.TButton", command=self.save)
        self.save_button.pack(side="right", padx=6)

        # 先为底部输入区分配空间，避免窗口缩小时被棋盘挤出。
        bottom = tk.Frame(outer, bg=BG)
        bottom.pack(side="bottom", fill="x", pady=(14, 0))
        self.label(bottom, "快捷指令", size=11, color=MUTED).pack(side="left", padx=(0, 12))
        self.entry = ttk.Entry(bottom)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda event: self.submit())
        ttk.Button(bottom, text="执行 ↵", command=self.submit).pack(side="left", padx=(10, 0))

        content = tk.Frame(outer, bg=BG)
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, minsize=320)
        content.grid_rowconfigure(0, weight=1)
        board_area = tk.Frame(content, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        board_area.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        board_header = tk.Frame(board_area, bg=CARD, padx=18, pady=13)
        board_header.pack(fill="x")
        self.board_title = self.label(board_header, "棋盘", bold=True)
        self.board_title.pack(side="left")
        self.label(board_header, "圆点标记最后落子", size=10, color=MUTED).pack(side="right")
        actions = tk.Frame(board_area, bg=CARD, padx=12, pady=10)
        actions.pack(side="bottom", fill="x")
        self.buttons = {}
        for index, (title, command) in enumerate(self.toolbar_design):
            actions.grid_columnconfigure(index, weight=1)
            button = ttk.Button(actions, text=title, command=lambda c=command: self.dispatch(c))
            button.grid(row=0, column=index, sticky="ew", padx=3)
            self.buttons[command] = button
        self.canvas = tk.Canvas(board_area, bg=CARD, highlightthickness=0, width=560, height=540)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<Configure>", lambda event: self.draw())
        self.canvas.bind("<Motion>", self.hover)
        self.canvas.bind("<Leave>", lambda event: self.canvas.delete("hover"))

        sidebar = tk.Frame(content, bg=BG, width=320)
        sidebar.grid(row=0, column=1, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.pack_propagate(False)
        self.sidebar_canvas = tk.Canvas(sidebar, bg=BG, width=320, highlightthickness=0)
        self.sidebar_scroll = ttk.Scrollbar(sidebar, orient="vertical", style="Slim.Vertical.TScrollbar",
                                            command=self.sidebar_canvas.yview)
        self.sidebar_canvas.configure(yscrollcommand=self.sidebar_scroll.set)
        self.sidebar_canvas.pack(side="left", fill="both", expand=True)
        self.sidebar_body = tk.Frame(self.sidebar_canvas, bg=BG)
        self.sidebar_window = self.sidebar_canvas.create_window(0, 0, window=self.sidebar_body, anchor="nw", width=320)
        self.sidebar_canvas.bind("<Configure>", self.resize_sidebar)
        self.sidebar_body.bind("<Configure>", self.sync_sidebar_scroll)
        sidebar = self.sidebar_body
        sidebar.grid_columnconfigure(0, weight=1)
        status_card, status = self.card(sidebar)
        status_card.grid(row=0, column=0, sticky="ew")
        title = tk.Frame(status, bg=CARD)
        title.pack(fill="x", pady=(0, 14))
        self.label(title, "当前棋局", size=11, color=MUTED).pack(side="left")
        self.phase = self.label(title, size=10, color=GREEN, padx=7, pady=2)
        self.phase.configure(bg="#edf3ed")
        self.phase.pack(side="right")
        turn = tk.Frame(status, bg=CARD)
        turn.pack(fill="x")
        self.turn_icon = tk.Canvas(turn, width=29, height=29, bg=CARD, highlightthickness=0)
        self.turn_icon.pack(side="left", padx=(0, 9))
        self.headline = self.label(turn, size=21, bold=True)
        self.headline.pack(side="left")
        self.detail = self.label(status, size=11, color=MUTED, wraplength=278)
        self.detail.pack(fill="x", pady=(10, 15))
        metrics = tk.Frame(status, bg=CARD)
        metrics.pack(fill="x")
        self.metric_values = []
        for column, text in enumerate(("已行手数", "剩余悔棋")):
            metrics.grid_columnconfigure(column, weight=1)
            cell = tk.Frame(metrics, bg="#f5f7f3", padx=12, pady=9)
            cell.grid(row=0, column=column, sticky="ew", padx=(0, 8) if column == 0 else 0)
            value = self.label(cell, size=20, bold=True)
            value.pack(anchor="w")
            self.metric_values.append(value)
            self.label(cell, text, size=10, color=MUTED).pack(anchor="w", pady=(3, 0))
        self.captures = self.label(status, size=11, color=MUTED, wraplength=278)
        self.score = self.label(status, size=12, color=GREEN, bold=True, wraplength=278)

        feedback_card, feedback = self.card(sidebar, "#edf3ed")
        feedback_card.grid(row=1, column=0, sticky="ew", pady=12)
        self.feedback_title = self.label(feedback, "最近操作", size=10, color=GREEN, bold=True)
        self.feedback_title.pack(anchor="w", pady=(0, 7))
        self.feedback = self.label(feedback, size=12, color=GREEN, wraplength=278)
        self.feedback.pack(fill="x")

        help_card, help_body = self.card(sidebar)
        help_card.grid(row=2, column=0, sticky="ew")
        help_header = tk.Frame(help_body, bg=CARD)
        help_header.pack(fill="x")
        self.label(help_header, "操作提示", size=11, bold=True).pack(side="left")
        self.help_toggle = ttk.Button(help_header, text="收起", style="Link.TButton", command=self.toggle_hints)
        self.help_toggle.pack(side="right")
        self.help = self.label(help_body, size=11, color=MUTED, wraplength=278)
        self.help.pack(fill="x", pady=(12, 0))
        pending = [self.sidebar_canvas, sidebar]
        while pending:
            widget = pending.pop()
            widget.bind("<MouseWheel>", self.scroll_sidebar)
            widget.bind("<Button-4>", lambda event: self.sidebar_canvas.yview_scroll(-1, "units"))
            widget.bind("<Button-5>", lambda event: self.sidebar_canvas.yview_scroll(1, "units"))
            pending.extend(widget.winfo_children())

    def resize_sidebar(self, event):
        self.sidebar_canvas.itemconfigure(self.sidebar_window, width=event.width)
        for widget in (self.detail, self.captures, self.score, self.feedback, self.help):
            widget.configure(wraplength=max(100, event.width - 42))
        self.sync_sidebar_scroll()

    def sync_sidebar_scroll(self, event=None):
        self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox("all"))
        if self.sidebar_body.winfo_reqheight() > self.sidebar_canvas.winfo_height() + 2:
            self.sidebar_scroll.pack(side="right", fill="y")
        else:
            self.sidebar_scroll.pack_forget()
            self.sidebar_canvas.yview_moveto(0)

    def scroll_sidebar(self, event):
        if self.sidebar_scroll.winfo_ismapped():
            units = -int(event.delta / 120) if abs(event.delta) >= 120 else -int(event.delta)
            self.sidebar_canvas.yview_scroll(units, "units")
        return "break"

    def new(self):
        self.dispatch(f"new {KINDS[self.kind.get()]} {self.size.get()}")

    def dispatch(self, command):
        try:
            tokens = shlex.split(command)
        except ValueError:
            tokens = []
        if (len(tokens) == 1 and tokens[0].lower() in ("restart", "resign")
                and self.client.service.session is not None):
            prompt = "重新开始会清空当前棋盘和历史。继续吗？" if tokens[0].lower() == "restart" else "确认当前行棋方认负？"
            if not messagebox.askyesno("确认操作", prompt, parent=self.root):
                self.client.feedback = "操作已取消。"
                self.refresh()
                return
        self.client.execute(command)
        if not self.client.running:
            self.root.destroy()
            return
        self.refresh()

    def submit(self):
        command = self.entry.get()
        self.entry.delete(0, "end")
        self.dispatch(command)

    def toggle_hints(self):
        self.dispatch("hints off" if self.client.hints else "help")

    def save(self):
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".json",
                                          filetypes=[("JSON 存档", "*.json")])
        if path:
            self.dispatch("save " + shlex.quote(path))
        else:
            self.client.feedback = "保存已取消。"
            self.refresh()

    def load(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("JSON 存档", "*.json"), ("所有文件", "*")])
        if path:
            self.dispatch("load " + shlex.quote(path))
        else:
            self.client.feedback = "读取已取消。"
            self.refresh()

    def geometry(self):
        session = self.client.service.session
        size = session.state.board.size if session else 15
        return BoardLayout.fit(size, self.canvas.winfo_width(), self.canvas.winfo_height())

    def is_active(self):
        session = self.client.service.session
        return session is not None and session.state.outcome is None

    def click(self, event):
        if not self.is_active():
            self.client.feedback = "请选择棋类与尺寸，开始新局。" if self.client.service.session is None else "对局已结束，可开始新局或悔棋。"
            self.refresh()
            return
        point = self.geometry().hit(event.x, event.y)
        if point is not None:
            row, col = point
            self.dispatch(f"play {row + 1} {col + 1}")
        else:
            self.client.feedback = "请点击棋盘交叉点。"
            self.refresh()

    def hover(self, event):
        self.canvas.delete("hover")
        if not self.is_active():
            return
        layout = self.geometry()
        point = layout.hit(event.x, event.y)
        if point is None:
            return
        row, col = point
        board = self.client.service.session.state.board
        if board.cells[row * board.size + col]:
            return
        x, y = layout.point(row, col)
        radius = min(24, layout.step * 0.4)
        self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius,
                                outline=GREEN, width=2, dash=(3, 3), tags="hover")

    def draw(self):
        self.canvas.delete("all")
        layout = self.geometry()
        left, top = layout.left, layout.top
        right, bottom = layout.point(layout.size - 1, layout.size - 1)
        self.canvas.create_rectangle(left-32, top-32, right+32, bottom+32,
                                     fill=WOOD, outline="#ddbd85")
        for index in range(layout.size):
            x, y = layout.point(index, index)
            self.canvas.create_line(left, y, right, y, fill=GRID)
            self.canvas.create_line(x, top, x, bottom, fill=GRID)
            self.canvas.create_text(x, top-18, text=index+1, fill="#806b4c", font=("Helvetica", 10))
            self.canvas.create_text(left-18, y, text=index+1, fill="#806b4c", font=("Helvetica", 10))
        stars = {9: (2, 4, 6), 13: (3, 6, 9), 15: (3, 7, 11), 19: (3, 9, 15)}.get(layout.size, ())
        for row in stars:
            for col in stars:
                x, y = layout.point(row, col)
                self.canvas.create_oval(x-2.3, y-2.3, x+2.3, y+2.3, fill="#8c7049", outline="")
        session = self.client.service.session
        if session is None:
            return
        radius = min(24, layout.step * 0.43)
        for index, value in enumerate(session.state.board.cells):
            if not value:
                continue
            row, col = divmod(index, layout.size)
            x, y = layout.point(row, col)
            self.canvas.create_oval(x-radius+1, y-radius+2, x+radius+1, y+radius+2,
                                    fill="#bc9d6b", outline="")
            self.canvas.create_oval(x-radius, y-radius, x+radius, y+radius,
                                    fill="#29352e" if value == 1 else "#fffef8",
                                    outline="#1c2923" if value == 1 else "#c5b78f", width=1.2)
            if self.overview.last_move == (row, col):
                dot = max(2.5, radius * 0.19)
                self.canvas.create_oval(x-dot, y-dot, x+dot, y+dot,
                                        fill="#a8d5ae" if value == 1 else GREEN, outline="")

    def refresh(self):
        session = self.client.service.session
        self.overview = view = game_overview(session)
        if session is not self._displayed_session:
            self._displayed_session = session
            if session is not None:
                self.kind.set(session.rules.title)
                self.size.set(str(session.state.board.size))
        active = self.is_active()
        self.kind.configure(state="disabled" if active else "readonly")
        self.size.configure(state="disabled" if active else "normal")
        self.new_button.configure(state="disabled" if active else "normal")
        self.save_button.configure(state="normal" if session else "disabled")
        enabled = {"restart": session is not None,
                   "undo": session is not None and view.moves > 0 and view.undos > 0,
                   "pass": active and session.rules.supports_pass, "resign": active}
        for command, button in self.buttons.items():
            button.configure(state="normal" if enabled[command] else "disabled")
        self.board_title.configure(text=view.title if session else "棋盘预览  /  15 × 15")
        self.phase.configure(text=view.phase)
        self.headline.configure(text=view.headline)
        self.detail.configure(text=view.detail)
        self.turn_icon.delete("all")
        self.turn_icon.create_oval(3, 3, 26, 26, width=1,
                                  fill="#29352e" if view.actor == Stone.BLACK else "#fffef8",
                                  outline=GREEN if view.actor is None else "#c5cdbf")
        self.metric_values[0].configure(text=f"{view.moves:02d}")
        self.metric_values[1].configure(text=f"{view.undos} / 3")
        for widget, value in ((self.captures, view.captures), (self.score, view.score)):
            widget.pack_forget()
            if value:
                widget.configure(text=value)
                widget.pack(fill="x", pady=(12, 0))
        feedback = ("选好棋类和棋盘后，即可开始。也可以读取已有存档。"
                    if self.client.feedback.startswith("欢迎。") else self.client.feedback)
        error = self.client.feedback.startswith("错误：")
        self.feedback_title.configure(text="操作未完成" if error else "最近操作", fg="#a05a36" if error else GREEN)
        self.feedback.configure(text=feedback, fg="#a05a36" if error else GREEN)
        self.help_toggle.configure(text="收起" if self.client.hints else "展开")
        if not self.client.hints:
            help_text = "提示已收起，点击「展开」恢复。"
        else:
            rule = ("先提净死子，再连续两次虚着计分。\n禁自杀与同形，白方贴 7.5。" if session and session.rules.supports_pass
                    else "横、竖或斜线连成五子即可获胜。\n每局双方合计可悔棋 3 次。")
            help_text = "点击交叉点落子，黑白交替。\n" + rule + "\n键盘：play 3 4 → 回车执行"
        self.help.configure(text=help_text)
        self.canvas.configure(cursor="crosshair" if active else "arrow")
        self.draw()


def launch():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        raise SystemExit(f"无法打开图形界面：{error}\n请使用 python3 main.py 运行控制台。") from error
    GuiClient(root)
    root.mainloop()
