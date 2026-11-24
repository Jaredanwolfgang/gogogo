"""组件组合与建造者：先设计布局顺序，再创建可重复渲染的界面。"""
from abc import ABC, abstractmethod


class Component(ABC):
    @abstractmethod
    def render(self, client):
        pass


class StatusComponent(Component):
    def render(self, client):
        session = client.service.session
        if session is None:
            return "GOGOGO 棋类对战平台 | 尚未开始"
        state = session.state
        parts = [f"{session.rules.title} {state.board.size}×{state.board.size} | "
                 f"第 {session.move_count} 手 | 剩余悔棋 {session.undo_remaining}/3"]
        if state.outcome is None:
            parts.append(f"轮到：{state.turn.label}")
        else:
            winner = "平局" if state.outcome.winner is None else state.outcome.winner.label + " 获胜"
            parts.append(f"对局结束：{winner}；{state.outcome.reason}")
            if state.outcome.score:
                black, white = state.outcome.score
                parts.append(f"面积得分：黑 {black:g}，白 {white:g}（含贴目 7.5）")
        if session.rules.supports_pass:
            parts.append(f"提子：黑 {state.captures[0]} / 白 {state.captures[1]} | 连续虚着 {state.passes}")
        return "\n".join(parts)


class BoardComponent(Component):
    def render(self, client):
        session = client.service.session
        if session is None:
            return "黑棋 X / 白棋 O / 空位 .；坐标从 1 开始，先行后列。"
        board = session.state.board
        lines = ["   " + " ".join(f"{col:2}" for col in range(1, board.size + 1))]
        for row in range(board.size):
            symbols = [".XO"[board.cells[row * board.size + col]] for col in range(board.size)]
            lines.append(f"{row + 1:2} " + " ".join(f"{symbol:>2}" for symbol in symbols))
        return "\n".join(lines)


class FeedbackComponent(Component):
    def render(self, client):
        return "反馈：" + client.feedback


class HelpComponent(Component):
    def render(self, client):
        if not client.hints:
            return "提示已隐藏；help 显示操作说明。"
        return ("new gomoku|go 大小(8-19) | restart | play 行 列 | pass（围棋）\n"
                "undo（每局合计3次） | resign | save 文件 | load 文件\n"
                "help | hints on|off | show | quit；带空格的路径请加双引号。\n"
                "围棋：白贴7.5，禁自杀和全局同形；死子请先实际提净，再连续两次 pass。")


class ConsoleView(Component):
    def __init__(self, components):
        self.components = tuple(components)

    def render(self, client):
        return "\n\n".join(text for part in self.components if (text := part.render(client)))


class ViewBuilder:
    def __init__(self):
        self._design = []

    def add(self, component_type):
        self._design.append(component_type)
        return self

    def build(self):
        return ConsoleView(component() for component in self._design)


class ViewDirector:
    @staticmethod
    def construct():
        return (ViewBuilder().add(StatusComponent).add(BoardComponent)
                .add(FeedbackComponent).add(HelpComponent).build())
