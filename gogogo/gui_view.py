"""桌面端的只读展示数据与棋盘坐标，不依赖 Tk 或改写对局。"""
from dataclasses import dataclass
from typing import Optional, Tuple

from .model import Stone


@dataclass(frozen=True)
class GameOverview:
    title: str = "准备开始"
    phase: str = "未开始"
    headline: str = "开始一局好棋"
    detail: str = "选择棋类与尺寸，点击「开始新局」。"
    actor: Optional[Stone] = None
    moves: int = 0
    undos: int = 3
    captures: str = ""
    score: str = ""
    last_move: Optional[Tuple[int, int]] = None


def game_overview(session):
    if session is None:
        return GameOverview()
    state = session.state
    # 存档保留撤销记录，最后一手应从仍然有效的动作中选择。
    active = []
    for event in session.events:
        if event["action"] == "undo":
            active.pop()
        else:
            active.append(event)
    last_move = next(((event["row"], event["col"]) for event in reversed(active)
                      if event["action"] == "play"), None)
    detail = "黑方先行，点击棋盘交叉点落子。"
    if active:
        event = active[-1]
        color = "黑方" if (len(active) - 1) % 2 == 0 else "白方"
        if event["action"] == "play":
            detail = f"上一手 · {color}  {event['row'] + 1} 行 {event['col'] + 1} 列"
        else:
            detail = f"上一手 · {color}" + ("虚着" if event["action"] == "pass" else "认负")
    actor = state.turn
    headline = ("黑方" if actor == Stone.BLACK else "白方") + "落子"
    phase, score = "进行中", ""
    if state.outcome:
        phase, actor = "已结束", state.outcome.winner
        headline = "平局" if actor is None else ("黑方" if actor == Stone.BLACK else "白方") + "获胜"
        detail = state.outcome.reason
        if state.outcome.score:
            black, white = state.outcome.score
            score = f"面积得分  黑 {black:g}  /  白 {white:g}\n白方得分已含贴白 7.5"
    captures = ""
    if session.rules.supports_pass:
        captures = (f"提子  黑 {state.captures[0]} · 白 {state.captures[1]}"
                    f"     连续虚着 {state.passes}/2")
    return GameOverview(
        title=f"{session.rules.title}  /  {state.board.size} × {state.board.size}",
        phase=phase, headline=headline, detail=detail, actor=actor,
        moves=session.move_count, undos=session.undo_remaining,
        captures=captures, score=score, last_move=last_move,
    )


@dataclass(frozen=True)
class BoardLayout:
    size: int
    step: float
    left: float
    top: float

    @classmethod
    def fit(cls, size, width, height):
        span = max(1, min(width, height) - 84)
        return cls(size, span / (size - 1), (width - span) / 2, (height - span) / 2)

    def point(self, row, col):
        return self.left + col * self.step, self.top + row * self.step

    def hit(self, x, y):
        col, row = round((x - self.left) / self.step), round((y - self.top) / self.step)
        if not (0 <= row < self.size and 0 <= col < self.size):
            return None
        px, py = self.point(row, col)
        if abs(x - px) > self.step * 0.45 or abs(y - py) > self.step * 0.45:
            return None
        return row, col
