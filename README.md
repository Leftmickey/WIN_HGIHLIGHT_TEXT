# WIN_HIGHLIGHT_TEXT

這是一個使用 Python 製作的 Windows 11「螢幕 Highlight 文字」小工具。執行後會在螢幕上顯示一段可拖曳、置頂、半透明的高亮文字，適合簡報、教學、直播或螢幕錄影時標示重點。

## 功能

- 顯示可拖曳的螢幕高亮文字
- 視窗保持置頂
- 可即時修改顯示文字
- 可從系統字型清單切換字型
- 可開關粗體，並調整字體大小與透明度
- 可選擇高亮底色與文字顏色
- 按 `Esc` 或關閉控制台即可結束
- 不需要安裝第三方套件，使用 Python 標準庫 `tkinter`

## 系統需求

- Windows 11
- Python 3.10 或更新版本

> 注意：Python 官方 Windows 安裝程式通常已包含 `tkinter`。如果你的 Python 沒有 tkinter，請重新安裝 Python 並勾選 Tcl/Tk 相關選項。

## 使用方式

在 Windows 11 的 PowerShell 或命令提示字元中執行：

```powershell
python screen_highlight_text.py
```

啟動後：

1. 在控制台輸入要顯示的文字。
2. 拖曳螢幕上的高亮文字到需要的位置。
3. 使用控制台調整字型、粗體、字體大小、透明度、底色與文字色。
4. 按 `Esc` 或關閉控制台結束程式。

## 啟動參數

也可以在啟動時指定文字、字型、大小、顏色、透明度與位置：

```powershell
python screen_highlight_text.py --text "重要提醒" --font "Microsoft JhengHei UI" --font-size 48 --highlight-color "#fff176" --text-color "#111111" --opacity 0.85 --x 200 --y 150
```

可用參數：

| 參數 | 說明 | 預設值 |
| --- | --- | --- |
| `--text` | 啟動時顯示的文字 | `重點提示文字` |
| `--font` | 啟動時的字型名稱 | `Microsoft JhengHei UI` |
| `--font-size` | 字體大小，範圍 12 到 120 | `40` |
| `--bold` / `--no-bold` | 開啟或關閉粗體 | 預設粗體開啟 |
| `--highlight-color` | 高亮底色，例如 `#fff176` | `#fff176` |
| `--text-color` | 文字顏色，例如 `#111111` | `#111111` |
| `--opacity` | 透明度，範圍 0.2 到 1.0 | `0.85` |
| `--x` | 初始 X 座標 | `120` |
| `--y` | 初始 Y 座標 | `120` |

## 打包成 exe（可選）

如果想在沒有命令列的情境下使用，可以用 PyInstaller 打包：

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed screen_highlight_text.py
```

完成後可在 `dist` 資料夾找到 exe 檔。
