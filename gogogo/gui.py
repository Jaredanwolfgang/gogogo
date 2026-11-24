"""可选 Tkinter 客户端，复用控制台命令控制器与同一游戏后端。"""
import shlex
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .cli import ConsoleClient
from .view import HelpComponent, StatusComponent


class GuiClient:
    def __init__(self, root):
        self.root = root
        self.client = ConsoleClient()
        root.title("GOGOGO · 五子棋与围棋")
        root.geometry("1060x780")
        root.minsize(920, 700)
        root.configure(bg="#f1f3ee")
        # 先定义组件布局，再创建组件并绑定命令。
        self.toolbar_design = (("重新开始", "restart"), ("悔棋", "undo"),
                               ("虚着", "pass"), ("认负", "resign"),
                               ("显示提示", "help"), ("隐藏提示", "hints off"))
        self.build()
        self.refresh()

    def build(self):
        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="GOGOGO", font=("Helvetica", 24, "bold")).pack(anchor="w")
        ttk.Label(outer, text="五子棋与围棋 · 本地双人对战").pack(anchor="w", pady=(0, 15))
        toolbar = ttk.Frame(outer)
        toolbar.pack(fill="x")
        self.kind = ttk.Combobox(toolbar, values=("gomoku", "go"), width=10, state="readonly")
        self.kind.set("gomoku")
        self.kind.pack(side="left")
        self.size = ttk.Spinbox(toolbar, from_=8, to=19, width=5)
        self.size.set("15")
        self.size.pack(side="left", padx=6)
        ttk.Button(toolbar, text="开始新局", command=self.new).pack(side="left")
        for title, command in self.toolbar_design:
            ttk.Button(toolbar, text=title, command=lambda c=command: self.dispatch(c)).pack(side="left", padx=2)
        content = ttk.Frame(outer)
        content.pack(fill="both", expand=True, pady=14)
        self.canvas = tk.Canvas(content, bg="#e5c28a", highlightthickness=0, width=620, height=620)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<Configure>", lambda event: self.draw())
        sidebar = ttk.Frame(content, width=275, padding=(16, 0, 0, 0))
        sidebar.pack(side="right", fill="y")
        self.status = ttk.Label(sidebar, wraplength=260, justify="left")
        self.status.pack(anchor="w", pady=8)
        self.feedback = ttk.Label(sidebar, wraplength=260, justify="left", foreground="#245747")
        self.feedback.pack(anchor="w", pady=14)
        ttk.Button(sidebar, text="保存局面…", command=self.save).pack(fill="x", pady=3)
        ttk.Button(sidebar, text="读取局面…", command=self.load).pack(fill="x", pady=3)
        self.help = ttk.Label(sidebar, wraplength=260, justify="left")
        self.help.pack(anchor="w", pady=20)
        bottom = ttk.Frame(outer)
        bottom.pack(fill="x")
        self.entry = ttk.Entry(bottom)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda event: self.submit())
        ttk.Button(bottom, text="执行指令", command=self.submit).pack(side="right", padx=(8, 0))

    def new(self):
        self.dispatch(f"new {self.kind.get()} {self.size.get()}")

    def dispatch(self, command):
        if command in ("restart", "resign") and self.client.service.session is not None:
            if not messagebox.askyesno("确认操作", "确定重新开始？" if command == "restart" else "确定认负？"):
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

    def save(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON 存档", "*.json")])
        if path:
            self.dispatch("save " + shlex.quote(path))
        else:
            self.client.feedback = "保存已取消。"
            self.refresh()

    def load(self):
        path = filedialog.askopenfilename(filetypes=[("JSON 存档", "*.json"), ("所有文件", "*")])
        if path:
            self.dispatch("load " + shlex.quote(path))
        else:
            self.client.feedback = "读取已取消。"
            self.refresh()

    def geometry(self):
        session = self.client.service.session
        size = session.state.board.size if session else 15
        edge = min(self.canvas.winfo_width(), self.canvas.winfo_height())
        step = max(1, (edge - 64) / (size - 1))
        return size, step, 32

    def click(self, event):
        size, step, margin = self.geometry()
        col, row = round((event.x - margin) / step), round((event.y - margin) / step)
        if (0 <= row < size and 0 <= col < size
                and abs(event.x - margin - col * step) <= step * 0.45
                and abs(event.y - margin - row * step) <= step * 0.45):
            self.dispatch(f"play {row + 1} {col + 1}")
        else:
            self.client.feedback = "请点击棋盘交叉点。"
            self.refresh()

    def draw(self):
        self.canvas.delete("all")
        size, step, margin = self.geometry()
        end = margin + step * (size - 1)
        for index in range(size):
            point = margin + step * index
            self.canvas.create_line(margin, point, end, point, fill="#8d7046")
            self.canvas.create_line(point, margin, point, end, fill="#8d7046")
            self.canvas.create_text(point, 14, text=str(index + 1), fill="#4e3b23")
            self.canvas.create_text(14, point, text=str(index + 1), fill="#4e3b23")
        session = self.client.service.session
        if session:
            radius = step * 0.41
            for index, value in enumerate(session.state.board.cells):
                if value:
                    row, col = divmod(index, size)
                    x, y = margin + step * col, margin + step * row
                    self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius,
                                            fill="#202923" if value == 1 else "#fffdf6", outline="#514a3c")

    def refresh(self):
        self.status.configure(text=StatusComponent().render(self.client))
        self.feedback.configure(text=self.client.feedback)
        self.help.configure(text=HelpComponent().render(self.client))
        self.draw()


def launch():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        raise SystemExit(f"无法打开图形界面：{error}\n请使用 python3 main.py 运行控制台。") from error
    GuiClient(root)
    root.mainloop()
