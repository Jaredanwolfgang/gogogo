"""生成报告使用的矢量 UML 类图；无需第三方包。"""
from html import escape
from pathlib import Path


def main():
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="1120" viewBox="0 0 1500 1120">',
             '<rect width="1500" height="1120" fill="white"/>',
             '<defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M1,1 L10,6 L1,11" fill="none" stroke="#415851" stroke-width="1.5"/></marker>',
             '<marker id="triangle" markerWidth="14" markerHeight="14" refX="12" refY="7" orient="auto"><path d="M1,1 L12,7 L1,13 Z" fill="white" stroke="#415851" stroke-width="1.5"/></marker>',
             '<marker id="diamond" markerWidth="16" markerHeight="12" refX="1" refY="6" orient="auto"><path d="M1,6 L8,1 L15,6 L8,11 Z" fill="#415851"/></marker></defs>']

    def box(x, y, w, name, lines):
        h = 60 + 34 * len(lines)
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="#f4f7f4" stroke="#415851" stroke-width="2"/>')
        parts.append(f'<line x1="{x}" x2="{x+w}" y1="{y+47}" y2="{y+47}" stroke="#415851"/>')
        parts.append(f'<text x="{x+w/2}" y="{y+32}" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="26" font-weight="bold">{escape(name)}</text>')
        for index, line in enumerate(lines):
            parts.append(f'<text x="{x+16}" y="{y+78+34*index}" font-family="Menlo,monospace" font-size="20">{escape(line)}</text>')

    def path(points, label="", x=0, y=0, kind="arrow", composition=False):
        start = ' marker-start="url(#diamond)"' if composition else ""
        parts.append(f'<polyline points="{points}" fill="none" stroke="#415851" stroke-width="2.2" marker-end="url(#{kind})"{start}/>')
        if label:
            parts.append(f'<text x="{x}" y="{y}" font-family="Helvetica,Arial,sans-serif" font-size="23" fill="#415851">{escape(label)}</text>')

    box(40, 30, 350, "GuiClient", ["+ click / dispatch / draw", "- client: ConsoleClient"])
    box(560, 30, 380, "ConsoleClient", ["+ execute / run", "- service / view"])
    box(1100, 30, 350, "ConsoleView", ["+ render(client)", "- components: tuple"])
    path("390,94 560,94", "uses", 445, 80)
    path("940,94 1100,94", composition=True)
    box(40, 280, 400, "JsonGameRepository", ["+ save(session, file)", "+ load(file) / decode(data)"])
    box(560, 280, 380, "GameService", ["+ new / restart", "+ play / save / load"])
    box(1100, 280, 350, "GameFactory", ["+ create(key, size)", "+ register(rule)"])
    path("750,158 750,280")
    path("560,344 440,344", "uses", 478, 329)
    path("940,344 1100,344", "creates", 966, 329)
    box(560, 530, 380, "GameSession", ["- history / events / undos", "+ play / pass_turn", "+ resign / undo"])
    box(40, 530, 400, "GameState", ["board / turn / passes", "captures / outcome", "immutable memento"])
    box(1100, 530, 350, "RuleStrategy (abstract)", ["+ place(...)", "+ outcome(...)", "supports_pass"])
    path("750,408 750,530", "owns 0..1", 769, 480)
    path("560,610 440,610", "1..*", 478, 590, composition=True)
    path("940,610 1100,610", "delegates", 959, 590)
    path("1275,408 1275,530", "reuses", 1294, 480)
    box(40, 820, 400, "Board", ["size / cells: tuple", "+ index / group", "+ neighbors / empty"])
    path("240,692 240,820", "1", 260, 764, composition=True)
    box(620, 880, 330, "GomokuRules", ["+ place / outcome"])
    box(1100, 880, 350, "GoRules", ["+ place / outcome", "+ score / has_legal_move"])
    path("785,880 785,790 1220,790 1220,692", kind="triangle")
    path("1275,880 1275,692", kind="triangle")
    parts.append('<text x="40" y="1080" font-family="Helvetica,Arial,sans-serif" font-size="24">Legend: open triangle = inheritance; filled diamond = composition; arrow = association.</text>')
    parts.append('</svg>')
    target = Path(__file__).resolve().parents[1] / "docs/architecture.svg"
    target.write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    main()
