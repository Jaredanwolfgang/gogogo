"""语法错误在客户端处理；游戏规则错误由后端统一处理。"""
import shlex

from .model import GameError
from .service import GameService
from .view import ViewDirector


class ConsoleClient:
    def __init__(self, service=None):
        self.service = service if service is not None else GameService()
        self.view = ViewDirector.construct()
        self.hints = True
        self.running = True
        self.feedback = "欢迎。输入 new gomoku 15 或 new go 9 开始对局。"

    def execute(self, line):
        try:
            tokens = shlex.split(line)
            if not tokens:
                raise GameError("请输入指令；help 可查看帮助。")
            name, *args = tokens
            name = name.lower()
            arities = {"new": 2, "play": 2, "save": 1, "load": 1, "hints": 1,
                       "restart": 0, "pass": 0, "undo": 0, "resign": 0,
                       "show": 0, "help": 0, "quit": 0}
            if name not in arities:
                raise GameError(f"未知指令：{name}。输入 help 查看帮助。")
            if len(args) != arities[name]:
                raise GameError(f"{name} 需要 {arities[name]} 个参数。")
            if name == "new":
                message = self.service.new(args[0].lower(), int(args[1]))
            elif name == "play":
                message = self.service.play(int(args[0]) - 1, int(args[1]) - 1)
            elif name in ("save", "load"):
                message = getattr(self.service, name)(args[0])
            elif name == "pass":
                message = self.service.pass_turn()
            elif name in ("restart", "undo", "resign"):
                message = getattr(self.service, name)()
            elif name == "hints":
                if args[0] not in ("on", "off"):
                    raise GameError("用法：hints on 或 hints off。")
                self.hints = args[0] == "on"
                message = "操作提示已" + ("显示。" if self.hints else "隐藏。")
            elif name == "help":
                self.hints = True
                message = "操作说明已显示。"
            elif name == "show":
                message = "已刷新当前局面。"
            else:
                self.running = False
                message = "已退出。"
            self.feedback = message
        except GameError as error:
            self.feedback = f"错误：{error}"
        except ValueError:
            self.feedback = "错误：数字参数必须是整数，路径引号必须成对。"
        return self.feedback

    def run(self, input_fn=input, output_fn=print):
        output_fn(self.view.render(self))
        while self.running:
            try:
                line = input_fn("gogogo> ")
            except (EOFError, KeyboardInterrupt):
                output_fn("\n输入结束，已退出。")
                break
            self.execute(line)
            output_fn(self.view.render(self))
