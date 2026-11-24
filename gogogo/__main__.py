import argparse


def main():
    parser = argparse.ArgumentParser(description="GOGOGO 五子棋与围棋双人对战")
    parser.add_argument("--gui", action="store_true", help="打开可选 Tkinter 图形界面")
    args = parser.parse_args()
    if args.gui:
        try:
            from .gui import launch
            launch()
        except ImportError as error:
            parser.exit(1, f"图形界面需要 Tkinter：{error}\n请使用不带 --gui 的控制台模式。\n")
    else:
        from .cli import ConsoleClient
        ConsoleClient().run()


if __name__ == "__main__":
    main()
