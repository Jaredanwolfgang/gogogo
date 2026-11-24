"""客户端共用的应用门面；业务规则与输入输出设备无关。"""
from .model import GameError
from .rules import GameFactory
from .storage import JsonGameRepository


class GameService:
    def __init__(self, factory=None, repository=None):
        self.factory = factory if factory is not None else GameFactory()
        self.repository = repository if repository is not None else JsonGameRepository(self.factory)
        self.session = None

    def require_session(self):
        if self.session is None:
            raise GameError("游戏尚未开始，请先使用 new gomoku 15 或 new go 9。")
        return self.session

    def new(self, game, size):
        if self.session is not None and self.session.state.outcome is None:
            raise GameError("对局正在进行，请用 restart 重新开始，或认负后开始其他游戏。")
        session = self.factory.create(game, size)
        self.session = session
        return f"已开始{session.rules.title}，棋盘 {size}×{size}，黑方先行。"

    def restart(self):
        old = self.require_session()
        self.session = self.factory.create(old.rules.key, old.state.board.size)
        return "已重新开始；棋盘、历史和悔棋次数已重置。"

    def play(self, row, col):
        return self.require_session().play(row, col)

    def pass_turn(self):
        return self.require_session().pass_turn()

    def undo(self):
        return self.require_session().undo()

    def resign(self):
        return self.require_session().resign()

    def save(self, filename):
        self.repository.save(self.require_session(), filename)
        return f"已保存到 {filename}。"

    def load(self, filename):
        session = self.repository.load(filename)
        self.session = session
        return f"已从 {filename} 恢复局面、历史和悔棋次数。"
