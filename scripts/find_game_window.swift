// 只识别 GOGOGO 窗口；无法唯一匹配时停止，不退回全屏录制。
import CoreGraphics
import Foundation

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(2)
}

guard CGPreflightScreenCaptureAccess() else {
    fail("请在系统设置 → 隐私与安全性 → 录屏与系统录音中允许当前终端应用，然后重新运行。")
}
let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements],
                                        kCGNullWindowID) as? [[String: Any]] ?? []
let matches = windows.filter {
    ($0[kCGWindowName as String] as? String)?.hasPrefix("GOGOGO ·") == true
        && ($0[kCGWindowLayer as String] as? Int) == 0
}
guard matches.count == 1, let id = matches.first?[kCGWindowNumber as String] as? Int else {
    fail("需且仅需打开一个 GOGOGO 游戏窗口；请先启动游戏，关闭重复窗口并取消最小化。")
}
print(id)
