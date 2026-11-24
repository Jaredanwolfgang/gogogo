"""无需桌面的展示状态回归：悔棋、读档、终局与缩放坐标。"""
import tempfile
import unittest
from pathlib import Path

from gogogo.gui_view import BoardLayout, game_overview
from gogogo.model import Stone
from gogogo.service import GameService


class OverviewTests(unittest.TestCase):
    def setUp(self):
        self.service = GameService()
        self.service.new("go", 8)

    def test_capture_undo_and_readback_keep_last_move_consistent(self):
        for row, col in ((0, 1), (0, 0), (7, 7), (6, 6), (1, 0)):
            self.service.play(row, col)
        view = game_overview(self.service.session)
        self.assertEqual(view.last_move, (1, 0))
        self.assertIn("黑 1", view.captures)
        self.assertEqual(view.headline, "白方落子")
        self.service.undo()
        view = game_overview(self.service.session)
        self.assertEqual(view.last_move, (6, 6))
        self.assertIn("白方  7 行 7 列", view.detail)
        self.assertEqual((view.moves, view.undos), (4, 2))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "game.json"
            self.service.save(str(path))
            self.service.restart()
            self.assertIsNone(game_overview(self.service.session).last_move)
            self.service.load(str(path))
            self.assertEqual(game_overview(self.service.session), view)

    def test_pass_score_and_undo_return_to_active_player(self):
        self.service.play(3, 4)
        self.service.pass_turn()
        view = game_overview(self.service.session)
        self.assertEqual(view.last_move, (3, 4))
        self.assertEqual(view.detail, "上一手 · 白方虚着")
        self.service.pass_turn()
        view = game_overview(self.service.session)
        self.assertEqual((view.phase, view.actor, view.headline), ("已结束", Stone.BLACK, "黑方获胜"))
        self.assertIn("黑 64", view.score)
        self.assertIn("白 7.5", view.score)
        self.service.undo()
        view = game_overview(self.service.session)
        self.assertEqual((view.phase, view.headline, view.score), ("进行中", "黑方落子", ""))

    def test_resign_and_multiple_undos_do_not_leave_stale_marker(self):
        self.service.play(2, 3)
        self.service.resign()
        self.assertEqual(game_overview(self.service.session).headline, "黑方获胜")
        self.service.undo()
        self.assertEqual(game_overview(self.service.session).headline, "白方落子")
        self.service.undo()
        view = game_overview(self.service.session)
        self.assertEqual((view.moves, view.undos, view.last_move), (0, 1, None))
        self.assertEqual(game_overview(None).phase, "未开始")


class BoardLayoutTests(unittest.TestCase):
    def test_wide_and_tall_windows_center_board_and_keep_clicks_aligned(self):
        for width, height in ((700, 450), (450, 700)):
            for size in (8, 19):
                with self.subTest(width=width, height=height, size=size):
                    layout = BoardLayout.fit(size, width, height)
                    first, last = layout.point(0, 0), layout.point(size-1, size-1)
                    self.assertAlmostEqual(first[0] + last[0], width)
                    self.assertAlmostEqual(first[1] + last[1], height)
                    for point in ((0, 0), (size-1, size-1), (3, 5)):
                        self.assertEqual(layout.hit(*layout.point(*point)), point)
                    self.assertIsNone(layout.hit(0, 0))
                    self.assertIsNone(layout.hit(first[0] + layout.step / 2, first[1]))


if __name__ == "__main__":
    unittest.main()
