"""JSON 存档仓库：有界读取、严格重放验证、同目录原子替换。"""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from .model import GameError


class JsonGameRepository:
    max_bytes = 2 * 1024 * 1024

    def __init__(self, factory):
        self.factory = factory

    def save(self, session, filename):
        data = {"version": 1, "game": session.rules.key, "size": session.state.board.size,
                "events": list(session.events), "position": session.summary()}
        temporary = None
        try:
            path = Path(filename).expanduser()
            text = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                    prefix=".gogogo-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        except (OSError, ValueError, RuntimeError) as error:
            raise GameError(f"保存失败：{error}") from error
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise GameError(f"存档包含重复字段：{key}")
            result[key] = value
        return result

    @staticmethod
    def _invalid_constant(value):
        raise GameError(f"存档包含非法数值：{value}")

    def load(self, filename):
        try:
            with Path(filename).expanduser().open("rb") as stream:
                raw = stream.read(self.max_bytes + 1)
            if len(raw) > self.max_bytes:
                raise GameError("存档超过 2 MiB 大小限制。")
            data = json.loads(raw.decode("utf-8"), object_pairs_hook=self._object,
                              parse_constant=self._invalid_constant)
            return self.decode(data)
        except (OSError, ValueError, RecursionError, RuntimeError) as error:
            raise GameError(f"读取失败：{error}") from error

    def decode(self, data):
        fields = {"version", "game", "size", "events", "position"}
        if type(data) is not dict or set(data) != fields:
            raise GameError("存档字段不完整或包含未知字段。")
        if type(data["version"]) is not int or data["version"] != 1:
            raise GameError("不支持的存档版本。")
        session = self.factory.create(data["game"], data["size"])
        events = data["events"]
        if type(events) is not list or len(events) > session.event_limit:
            raise GameError("存档行棋记录不合法或过长。")
        for event in events:
            if type(event) is not dict or type(event.get("action")) is not str:
                raise GameError("存档中存在非法操作。")
            action = event["action"]
            if action == "play" and set(event) == {"action", "row", "col"}:
                session.play(event["row"], event["col"])
            elif set(event) == {"action"} and action in ("pass", "resign", "undo"):
                {"pass": session.pass_turn, "resign": session.resign, "undo": session.undo}[action]()
            else:
                raise GameError("存档指令或参数不合法。")
        # 用规范 JSON 比较，拒绝 Python 中 True == 1 导致的类型混淆。
        canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
        if canonical(data["position"]) != canonical(session.summary()):
            raise GameError("局面与历史重放结果不一致，存档可能已损坏。")
        return session
