"""对局聚合根：验证生命周期，以不可变快照实现一步悔棋。"""
from .model import Board, GameError, GameState, Outcome


class GameSession:
    undo_limit = 3
    event_limit = 5000

    def __init__(self, rules, size):
        self.rules = rules
        self._history = [GameState(Board.empty(size))]
        self._events = []
        self._undos = 0

    @property
    def state(self):
        return self._history[-1]

    @property
    def events(self):
        return tuple(dict(event) for event in self._events)

    @property
    def undo_remaining(self):
        return self.undo_limit - self._undos

    @property
    def move_count(self):
        return len(self._history) - 1

    @property
    def seen(self):
        return frozenset(state.board.cells for state in self._history)

    def _check_capacity(self):
        if len(self._events) >= self.event_limit:
            raise GameError("单局操作记录已达 5000 次上限，请重新开始。")

    def _check_active(self):
        self._check_capacity()
        if self.state.outcome is not None:
            raise GameError("对局已结束，请开始新局、重新开始或悔棋。")

    def play(self, row, col):
        self._check_active()
        previous = self.state
        board, captured = self.rules.place(previous.board, previous.turn, row, col, self.seen)
        captures = list(previous.captures)
        captures[previous.turn - 1] += captured
        seen = self.seen | {board.cells}
        outcome = self.rules.outcome(board, previous.turn, row, col, seen, 0)
        self._history.append(GameState(board, previous.turn.opponent, 0, tuple(captures), outcome))
        self._events.append({"action": "play", "row": row, "col": col})
        return f"{previous.turn.label} 落子 ({row + 1}, {col + 1})；提子 {captured}。"

    def pass_turn(self):
        self._check_active()
        if not self.rules.supports_pass:
            raise GameError("五子棋不允许虚着。")
        previous = self.state
        passes = previous.passes + 1
        outcome = self.rules.outcome(previous.board, previous.turn, None, None, self.seen, passes)
        self._history.append(GameState(previous.board, previous.turn.opponent, passes,
                                       previous.captures, outcome))
        self._events.append({"action": "pass"})
        return f"{previous.turn.label} 虚着；连续虚着 {passes} 次。"

    def resign(self):
        self._check_active()
        previous = self.state
        outcome = Outcome(previous.turn.opponent, f"{previous.turn.label} 认负")
        self._history.append(GameState(previous.board, previous.turn, previous.passes,
                                       previous.captures, outcome))
        self._events.append({"action": "resign"})
        return f"{previous.turn.label} 已认负。"

    def undo(self):
        self._check_capacity()
        if len(self._history) == 1:
            raise GameError("无棋子可悔：当前没有可撤销的行棋。")
        if self.undo_remaining <= 0:
            raise GameError("悔棋次数超过限制：每局双方合计最多 3 次。")
        self._history.pop()
        self._undos += 1
        self._events.append({"action": "undo"})
        return f"已悔棋一步；剩余悔棋 {self.undo_remaining} 次。"

    def summary(self):
        state = self.state
        outcome = state.outcome
        return {
            "cells": list(state.board.cells), "turn": int(state.turn),
            "passes": state.passes, "captures": list(state.captures),
            "move_count": self.move_count, "undo_remaining": self.undo_remaining,
            "outcome": None if outcome is None else {
                "winner": None if outcome.winner is None else int(outcome.winner),
                "reason": outcome.reason,
                "score": None if outcome.score is None else list(outcome.score),
            },
        }
