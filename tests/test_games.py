import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gogogo.cli import ConsoleClient
from gogogo.model import Board, GameError, Stone
from gogogo.rules import GameFactory, GoRules, GomokuRules
from gogogo.service import GameService
from gogogo.storage import JsonGameRepository


def position(black=(), white=(), size=8):
    cells = [0] * (size * size)
    for color, points in ((1, black), (2, white)):
        for row, col in points:
            cells[row * size + col] = color
    return Board(size, tuple(cells))


class BoardTests(unittest.TestCase):
    def test_sizes_and_coordinate_types(self):
        for size in (8, 9, 15, 19):
            self.assertEqual(len(Board.empty(size).cells), size * size)
        for size in (7, 20, 8.0, True, "9", -1, 10 ** 9):
            with self.subTest(size=size), self.assertRaises(GameError):
                Board.empty(size)
        for coord in ((-1, 0), (0, 8), (True, 0), (1.0, 0)):
            with self.assertRaises(GameError):
                Board.empty(8).index(*coord)

    def test_group_and_liberties(self):
        board = position(black=((0, 0), (0, 1)))
        stones, liberties = board.group(0)
        self.assertEqual(stones, {0, 1})
        self.assertEqual(liberties, {2, 8, 9})


class GomokuTests(unittest.TestCase):
    def test_four_win_directions(self):
        rules = GomokuRules()
        for dr, dc in ((1, 0), (0, 1), (1, 1), (1, -1)):
            points = [(1 + i * dr, (6 if dc < 0 else 1) + i * dc) for i in range(5)]
            board = position(black=points)
            result = rules.outcome(board, Stone.BLACK, *points[-1], set(), 0)
            self.assertEqual(result.winner, Stone.BLACK)

    def test_overline_wins(self):
        board = position(white=[(0, col) for col in range(6)])
        self.assertEqual(GomokuRules().outcome(board, Stone.WHITE, 0, 3, set(), 0).winner, Stone.WHITE)

    def test_full_board_draw(self):
        cells = tuple(1 if (r + 2 * c) % 4 < 2 else 2 for r in range(8) for c in range(8))
        board = Board(8, cells)
        result = GomokuRules().outcome(board, Stone(cells[-1]), 7, 7, set(), 0)
        self.assertIsNone(result.winner)
        self.assertIn("平局", result.reason)

    def test_complete_game_and_terminal_rejection(self):
        game = GameFactory().create("gomoku", 8)
        for col in range(4):
            game.play(0, col)
            game.play(2, col)
        game.play(0, 4)
        self.assertEqual(game.state.outcome.winner, Stone.BLACK)
        before = game.summary()
        with self.assertRaises(GameError):
            game.play(7, 7)
        self.assertEqual(game.summary(), before)
        game.undo()
        self.assertIsNone(game.state.outcome)
        self.assertEqual(game.state.turn, Stone.BLACK)


class GoTests(unittest.TestCase):
    def setUp(self):
        self.rules = GoRules()

    def test_capture_single_and_group(self):
        board = position(black=((0, 1),), white=((0, 0),))
        result, count = self.rules.place(board, Stone.BLACK, 1, 0, {board.cells})
        self.assertEqual(count, 1)
        self.assertEqual(result.cells[0], 0)
        board = position(black=((1, 0), (1, 1)), white=((0, 0), (0, 1)))
        result, count = self.rules.place(board, Stone.BLACK, 0, 2, {board.cells})
        self.assertEqual(count, 2)
        self.assertEqual(result.cells[:2], (0, 0))

    def test_simultaneous_capture_of_two_groups(self):
        board = position(black=((0, 2), (1, 1), (2, 0)), white=((0, 1), (1, 0)))
        result, count = self.rules.place(board, Stone.BLACK, 0, 0, {board.cells})
        self.assertEqual(count, 2)
        self.assertEqual(result.cells[0], 1)

    def test_suicide_and_capture_before_suicide_check(self):
        board = position(white=((0, 1), (1, 0)))
        with self.assertRaisesRegex(GameError, "自杀"):
            self.rules.place(board, Stone.BLACK, 0, 0, {board.cells})
        board = position(black=((0, 2), (1, 1), (2, 0)), white=((0, 1), (1, 0)))
        self.assertEqual(self.rules.place(board, Stone.BLACK, 0, 0, {board.cells})[1], 2)

    def test_ko_and_delayed_recapture(self):
        board = position(black=((0, 1), (1, 0), (2, 1)),
                         white=((1, 1), (0, 2), (2, 2), (1, 3)))
        captured, count = self.rules.place(board, Stone.BLACK, 1, 2, {board.cells})
        self.assertEqual(count, 1)
        seen = {board.cells, captured.cells}
        with self.assertRaisesRegex(GameError, "同形"):
            self.rules.place(captured, Stone.WHITE, 1, 1, seen)
        threat, _ = self.rules.place(captured, Stone.WHITE, 7, 7, seen)
        answer, _ = self.rules.place(threat, Stone.BLACK, 7, 6, seen | {threat.cells})
        recaptured, count = self.rules.place(answer, Stone.WHITE, 1, 1, seen | {threat.cells, answer.cells})
        self.assertEqual(count, 1)
        self.assertEqual(recaptured.cells[1 * 8 + 2], 0)

    def test_superko_checks_older_positions(self):
        board = Board.empty(8)
        result, _ = self.rules.place(board, Stone.BLACK, 3, 3, set())
        with self.assertRaisesRegex(GameError, "同形"):
            self.rules.place(board, Stone.BLACK, 3, 3, {result.cells, (2,) * 64})

    def test_area_territory_and_neutral_points(self):
        board = position(black=((0, 1), (1, 0)), white=((7, 7),))
        self.assertEqual(self.rules.score(board), (3.0, 8.5))
        self.assertEqual(self.rules.score(Board.empty(8)), (0.0, 7.5))
        self.assertEqual(GoRules(0).score(Board.empty(8)), (0.0, 0.0))

    def test_two_passes_end_and_play_resets_pass_count(self):
        game = GameFactory().create("go", 8)
        game.pass_turn()
        game.play(0, 0)
        self.assertEqual(game.state.passes, 0)
        game.pass_turn()
        game.pass_turn()
        self.assertIsNotNone(game.state.outcome)
        self.assertEqual(game.state.outcome.winner, Stone.WHITE)
        self.assertEqual(game.state.outcome.score, (0.0, 71.5))
        game.undo()
        self.assertEqual(game.state.passes, 1)
        self.assertIsNone(game.state.outcome)

    def test_no_legal_moves_ends_automatically(self):
        # 两个黑眼是棋盘仅有的空点；白自杀，黑填眼后的局面均在历史中。
        cells = [1] * 64
        cells[0] = cells[7] = 0
        board = Board(8, tuple(cells))
        seen = {board.cells}
        for index in (0, 7):
            candidate = cells.copy()
            candidate[index] = 1
            seen.add(tuple(candidate))
        result = self.rules.outcome(board, Stone.WHITE, None, None, seen, 0)
        self.assertIn("均无合法落点", result.reason)
        self.assertEqual(result.winner, Stone.BLACK)

    def test_one_player_blocked_does_not_end(self):
        cells = [1] * 64
        cells[0] = cells[7] = 0
        board = Board(8, tuple(cells))
        self.assertFalse(self.rules.has_legal_move(board, Stone.WHITE, {board.cells}))
        self.assertTrue(self.rules.has_legal_move(board, Stone.BLACK, {board.cells}))
        self.assertIsNone(self.rules.outcome(board, Stone.BLACK, 0, 1, {board.cells}, 0))


class SessionTests(unittest.TestCase):
    def test_invalid_move_is_atomic(self):
        game = GameFactory().create("go", 8)
        game.play(0, 0)
        before, events = game.summary(), game.events
        for row, col in ((0, 0), (-1, 2), (8, 8), (True, 2)):
            with self.assertRaises(GameError):
                game.play(row, col)
            self.assertEqual(game.summary(), before)
            self.assertEqual(game.events, events)

    def test_undo_capture_restores_everything(self):
        game = GameFactory().create("go", 8)
        for row, col in ((0, 1), (0, 0), (7, 7), (6, 6)):
            game.play(row, col)
        before = game.state
        game.play(1, 0)
        self.assertEqual(game.state.captures, (1, 0))
        game.undo()
        self.assertEqual(game.state, before)
        game.play(1, 0)  # 已撤销的未来局面不会污染同形历史。
        self.assertEqual(game.state.captures, (1, 0))

    def test_undo_empty_and_limit(self):
        game = GameFactory().create("gomoku", 8)
        with self.assertRaisesRegex(GameError, "无棋子"):
            game.undo()
        for _ in range(3):
            game.play(0, 0)
            game.undo()
        game.play(0, 0)
        with self.assertRaisesRegex(GameError, "超过限制"):
            game.undo()

    def test_resign_undo_restart_and_new(self):
        service = GameService()
        with self.assertRaises(GameError):
            service.restart()
        service.new("go", 8)
        with self.assertRaises(GameError):
            service.new("gomoku", 9)
        service.resign()
        self.assertEqual(service.session.state.outcome.winner, Stone.WHITE)
        service.undo()
        self.assertIsNone(service.session.state.outcome)
        service.restart()
        self.assertEqual(service.session.undo_remaining, 3)
        service.resign()
        service.new("gomoku", 19)
        self.assertEqual(service.session.state.board.size, 19)
        with self.assertRaises(GameError):
            service.pass_turn()

    def test_factory_reuses_strategies_but_not_sessions(self):
        factory = GameFactory()
        one, two = factory.create("go", 8), factory.create("go", 8)
        self.assertIs(one.rules, two.rules)
        one.play(0, 0)
        self.assertEqual(two.state.board.cells[0], 0)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "中文 存档.json"
        self.service = GameService()
        self.service.new("go", 8)

    def test_roundtrip_restores_history_and_undo_quota(self):
        for row, col in ((0, 1), (0, 0), (7, 7), (6, 6), (1, 0)):
            self.service.play(row, col)
        self.service.undo()
        self.service.play(1, 0)
        self.service.pass_turn()
        before = self.service.session.summary()
        self.service.save(str(self.path))
        self.service.restart()
        self.service.load(str(self.path))
        self.assertEqual(self.service.session.summary(), before)
        self.service.undo()
        self.assertEqual(self.service.session.state.passes, 0)
        self.assertEqual(self.service.session.undo_remaining, 1)

    def test_ended_roundtrip(self):
        self.service.resign()
        before = self.service.session.summary()
        self.service.save(str(self.path))
        self.service.load(str(self.path))
        self.assertEqual(before, self.service.session.summary())
        self.service.undo()
        self.assertIsNone(self.service.session.state.outcome)

    def test_corruption_never_replaces_current_session(self):
        self.service.play(0, 0)
        self.service.save(str(self.path))
        original = json.loads(self.path.read_text())
        variants = []
        for key, value in (("version", True), ("size", 20), ("game", "chess"),
                           ("game", []), ("events", [{"action": "play", "row": True, "col": 0}]),
                           ("events", [{"action": "pass", "extra": 1}]),
                           ("events", [{"action": "undo"}]), ("position", {})):
            bad = dict(original)
            bad[key] = value
            variants.append(json.dumps(bad))
        bad = json.loads(json.dumps(original))
        bad["position"]["cells"][0] = True
        variants += [json.dumps(bad), "not json", '{"version":1,"version":1}', "[" * 1500,
                     json.dumps(original).replace('"row": 0', '"row": NaN')]
        before = self.service.session
        for raw in variants:
            with self.subTest(raw=raw[:70]):
                self.path.write_text(raw)
                with self.assertRaises(GameError):
                    self.service.load(str(self.path))
                self.assertIs(self.service.session, before)

    def test_file_errors_and_atomic_save(self):
        with self.assertRaises(GameError):
            self.service.load(str(self.path))
        with self.assertRaises(GameError):
            self.service.save(str(self.path / "missing.json"))
        self.service.save(str(self.path))
        previous = self.path.read_bytes()
        self.service.play(1, 1)
        with patch("gogogo.storage.os.replace", side_effect=OSError("模拟磁盘替换失败")):
            with self.assertRaises(GameError):
                self.service.save(str(self.path))
        self.assertEqual(self.path.read_bytes(), previous)
        self.assertEqual(list(self.path.parent.glob(".gogogo-*.tmp")), [])

    def test_oversize_and_invalid_utf8(self):
        for data in (b"x" * (JsonGameRepository.max_bytes + 1), b"\xff\xfe"):
            self.path.write_bytes(data)
            with self.assertRaises(GameError):
                self.service.load(str(self.path))


class ClientTests(unittest.TestCase):
    def test_bad_commands_and_hint_toggle(self):
        client = ConsoleClient()
        for command in ("", "unknown", "new", "new go seven", "play 1", "save \"oops", "hints maybe", "play 1 1"):
            self.assertIn("错误", client.execute(command))
        client.execute("hints off")
        self.assertNotIn("restart |", client.view.render(client))
        client.execute("help")
        self.assertIn("restart |", client.view.render(client))

    def test_quoted_path(self):
        client = ConsoleClient()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "存档 one.json"
            client.execute("new go 8")
            self.assertIn("已保存", client.execute(f'save "{path}"'))
            self.assertIn("已从", client.execute(f'load "{path}"'))

    def test_cli_subprocess_full_game(self):
        commands = ["new gomoku 8"]
        for col in range(1, 5):
            commands.extend((f"play 1 {col}", f"play 3 {col}"))
        commands.extend(("play 1 5", "quit"))
        result = subprocess.run([sys.executable, "main.py"], input="\n".join(commands) + "\n",
                                capture_output=True, text=True, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("黑方 X 获胜", result.stdout)
        self.assertIn("已退出", result.stdout)

    def test_eof_is_clean(self):
        output = []
        client = ConsoleClient()
        def eof(prompt):
            raise EOFError
        client.run(eof, output.append)
        self.assertIn("输入结束", output[-1])


if __name__ == "__main__":
    unittest.main()
