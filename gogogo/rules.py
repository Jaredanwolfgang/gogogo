"""规则策略不读写文件、不接收终端输入，也不改变传入的棋盘。"""
from abc import ABC, abstractmethod

from .model import Board, GameError, Outcome, Stone


class RuleStrategy(ABC):
    key = ""
    title = ""
    supports_pass = False

    @abstractmethod
    def place(self, board, player, row, col, seen):
        """返回 (新棋盘, 提子数)，非法操作抛出 GameError。"""

    @abstractmethod
    def outcome(self, board, player, row, col, seen, passes):
        """返回终局结果，未结束则返回 None。"""

    @staticmethod
    def prepare(board, player, row, col):
        index = board.index(row, col)
        if board.cells[index]:
            raise GameError("该位置已有棋子。")
        cells = list(board.cells)
        cells[index] = int(player)
        return index, cells


class GomokuRules(RuleStrategy):
    key, title = "gomoku", "五子棋"

    def place(self, board, player, row, col, seen):
        _, cells = self.prepare(board, player, row, col)
        return Board(board.size, tuple(cells)), 0

    def outcome(self, board, player, row, col, seen, passes):
        # 自由五子棋：四个方向，五子或长连均获胜，无禁手。
        for dr, dc in ((1, 0), (0, 1), (1, 1), (1, -1)):
            count = 1
            for sign in (-1, 1):
                r, c = row + sign * dr, col + sign * dc
                while (0 <= r < board.size and 0 <= c < board.size
                       and board.cells[r * board.size + c] == player):
                    count += 1
                    r, c = r + sign * dr, c + sign * dc
            if count >= 5:
                return Outcome(player, "连成五子")
        if 0 not in board.cells:
            return Outcome(None, "棋盘已满，平局")
        return None


class GoRules(RuleStrategy):
    key, title, supports_pass = "go", "围棋", True

    def __init__(self, komi=7.5):
        self.komi = komi

    def place(self, board, player, row, col, seen):
        index, cells = self.prepare(board, player, row, col)
        tentative = Board(board.size, tuple(cells))
        captured, examined = set(), set()
        # 先同时找出邻接的无气敌方棋块，再统一移除，最后判断自杀。
        for neighbor in board.neighbors(index):
            if cells[neighbor] == player.opponent and neighbor not in examined:
                group, liberties = tentative.group(neighbor)
                examined.update(group)
                if not liberties:
                    captured.update(group)
        for point in captured:
            cells[point] = 0
        result = Board(board.size, tuple(cells))
        if not result.group(index)[1]:
            raise GameError("禁止自杀：落子后己方棋块无气。")
        if result.cells in seen:
            raise GameError("禁止全局同形：该落子将重复历史局面（劫）。")
        return result, len(captured)

    def has_legal_move(self, board, player, seen):
        for index, value in enumerate(board.cells):
            if value:
                continue
            try:
                self.place(board, player, *divmod(index, board.size), seen)
                return True
            except GameError:
                continue
        return False

    def score(self, board):
        """面积计分：盘上棋子 + 仅与己方相邻的空域，白贴 7.5 点。"""
        scores = [float(board.cells.count(1)), float(board.cells.count(2))]
        visited = set()
        for index, value in enumerate(board.cells):
            if value or index in visited:
                continue
            region, colors, pending = {index}, set(), [index]
            visited.add(index)
            while pending:
                for neighbor in board.neighbors(pending.pop()):
                    color = board.cells[neighbor]
                    if color:
                        colors.add(color)
                    elif neighbor not in visited:
                        visited.add(neighbor)
                        region.add(neighbor)
                        pending.append(neighbor)
            if len(colors) == 1:
                scores[colors.pop() - 1] += len(region)
        scores[1] += self.komi
        return tuple(scores)

    def outcome(self, board, player, row, col, seen, passes):
        reason = None
        if passes >= 2:
            reason = "双方连续虚着，面积计分"
        elif (not self.has_legal_move(board, Stone.BLACK, seen)
              and not self.has_legal_move(board, Stone.WHITE, seen)):
            reason = "双方均无合法落点，面积计分"
        if reason:
            black, white = self.score(board)
            winner = None if black == white else Stone.BLACK if black > white else Stone.WHITE
            return Outcome(winner, reason, (black, white))
        return None


class GameFactory:
    """注册式简单工厂；每个工厂只创建并复用一份无对局状态的规则策略。"""
    def __init__(self):
        self._rules = {rule.key: rule for rule in (GomokuRules(), GoRules())}

    def register(self, rule):
        if not isinstance(rule, RuleStrategy) or not rule.key:
            raise GameError("需要带有名称的规则策略。")
        self._rules[rule.key] = rule

    def rules(self, key):
        try:
            return self._rules[key]
        except (KeyError, TypeError) as error:
            raise GameError("未知游戏类型，请使用 gomoku 或 go。") from error

    def create(self, key, size):
        from .session import GameSession
        return GameSession(self.rules(key), size)
