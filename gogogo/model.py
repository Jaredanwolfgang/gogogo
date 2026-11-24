"""不可变领域对象；棋子用枚举共享，不为每个交叉点分配棋子实例。"""
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Tuple


class GameError(ValueError):
    """可向用户直接展示的操作错误。"""


class Stone(IntEnum):
    EMPTY = 0
    BLACK = 1
    WHITE = 2

    @property
    def opponent(self):
        return Stone.WHITE if self == Stone.BLACK else Stone.BLACK

    @property
    def label(self):
        return ("空", "黑方 X", "白方 O")[self]


@dataclass(frozen=True)
class Board:
    size: int
    cells: Tuple[int, ...]

    def __post_init__(self):
        if type(self.size) is not int or not 8 <= self.size <= 19:
            raise GameError("棋盘边长必须是 8 到 19 的整数。")
        if (type(self.cells) is not tuple or len(self.cells) != self.size ** 2
                or any(type(v) is not int or v not in (0, 1, 2) for v in self.cells)):
            raise GameError("棋盘数据不合法。")

    @classmethod
    def empty(cls, size):
        if type(size) is not int or not 8 <= size <= 19:
            raise GameError("棋盘边长必须是 8 到 19 的整数。")
        return cls(size, (0,) * (size * size))

    def index(self, row, col):
        if (type(row) is not int or type(col) is not int
                or not (0 <= row < self.size and 0 <= col < self.size)):
            raise GameError(f"坐标越界：行和列须在 1 到 {self.size} 之间。")
        return row * self.size + col

    def neighbors(self, index):
        row, col = divmod(index, self.size)
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            r, c = row + dr, col + dc
            if 0 <= r < self.size and 0 <= c < self.size:
                yield r * self.size + c

    def group(self, index):
        """返回四连通棋块和气；空点不能作为棋块起点。"""
        color = self.cells[index]
        if color == 0:
            raise GameError("空点不属于棋块。")
        stones, liberties, pending = {index}, set(), [index]
        while pending:
            for neighbor in self.neighbors(pending.pop()):
                value = self.cells[neighbor]
                if value == 0:
                    liberties.add(neighbor)
                elif value == color and neighbor not in stones:
                    stones.add(neighbor)
                    pending.append(neighbor)
        return stones, liberties


@dataclass(frozen=True)
class Outcome:
    winner: Optional[Stone]
    reason: str
    score: Optional[Tuple[float, float]] = None


@dataclass(frozen=True)
class GameState:
    """备忘录：同时保存棋盘、轮次、提子数、虚着和终局信息。"""
    board: Board
    turn: Stone = Stone.BLACK
    passes: int = 0
    captures: Tuple[int, int] = (0, 0)
    outcome: Optional[Outcome] = None
