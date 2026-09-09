# WIN_HIGHLIGHT_TEXT

這是一個使用 Python 製作的 Windows 11「螢幕 Highlight 文字」小工具。執行後會在螢幕上顯示一段可拖曳、置頂、半透明的高亮文字，適合簡報、教學、直播或螢幕錄影時標示重點。

## 功能

- 顯示可拖曳的螢幕高亮文字
- 視窗保持置頂
- 可即時修改顯示文字，支援多行
- 可從外部 `.txt` 檔載入文字
- 可從系統字型清單切換字型
- 可開關粗體，並調整字體大小與透明度
- 可選擇高亮底色與文字顏色
- 可加上邊框並調整粗細與顏色
- 可啟用文字陰影並調整偏移與顏色
- 可啟用走馬燈模式，並調整速度與寬度
- 支援全域快捷鍵 `Ctrl+Alt+H`：即使焦點在其他程式上，也能顯示／隱藏高亮
- 按 `Esc` 或關閉控制台即可結束
- 不需要安裝第三方套件，只用 Python 標準庫（`tkinter` 與 `ctypes`）

## 系統需求

- Windows 11
- Python 3.10 或更新版本

> 注意：Python 官方 Windows 安裝程式通常已包含 `tkinter`。如果你的 Python 沒有 tkinter，請重新安裝 Python 並勾選 Tcl/Tk 相關選項。

## 使用方式

在 Windows 11 的 PowerShell 或命令提示字元中執行：

```powershell
python screen_highlight_text.py
```

啟動後會開啟控制台，包含這些功能：

1. 修改文字（可多行，也可載入 TXT）
2. 選字型（可開關粗體）
3. 調整字體大小
4. 調整透明度
5. 更換高亮底色
6. 更換文字顏色
7. 走馬燈模式（可調速度與寬度）
8. 邊框與文字陰影（可調粗細、偏移與顏色）

操作步驟：

1. 在控制台多行文字框輸入內容，或按「載入 TXT」/ `Ctrl+O`。
2. 拖曳螢幕上的高亮文字到需要的位置。
3. 使用控制台即時調整字型、大小、透明度與顏色。
4. 勾選「啟用走馬燈」讓文字在高亮條內向左捲動。
5. 設定邊框粗細／顏色，或勾選「文字陰影」讓文字更醒目。
6. 按 `Ctrl+Alt+H` 可隨時全域顯示／隱藏高亮（在其他程式操作時也有效）。
7. 按 `Esc` 或關閉控制台結束程式。

## 讀取外部 TXT

可直接用命令列載入文字檔：

```powershell
python screen_highlight_text.py --file examples\sample.txt
```

也支援走馬燈：

```powershell
python screen_highlight_text.py --file examples\sample.txt --marquee --marquee-speed 6
```

文字檔支援常見編碼：`UTF-8`、`UTF-8 BOM`、`Big5/CP950`。

## 全域快捷鍵

程式啟動後預設註冊全域快捷鍵 **`Ctrl+Alt+H`**，可在任何時候顯示／隱藏高亮文字，
即使目前焦點在簡報軟體或瀏覽器等其他程式上也有效（透過 Windows `RegisterHotKey`，
仍屬標準庫、不需額外套件）。控制台的「顯示高亮文字」勾選狀態會同步更新。

- 若 `Ctrl+Alt+H` 已被其他程式占用，控制台會在操作提示區顯示註冊失敗訊息；此時仍可用勾選框切換。
- 若不想註冊全域快捷鍵，啟動時加上 `--hotkey-off`。
- 全域快捷鍵僅在 Windows 生效；其他系統會自動略過。

## 邊框與文字陰影

- **邊框**：`--border-width`（0–10，`0` 表示無邊框）與 `--border-color` 設定；
  也可在控制台第 8 區即時調整。
- **文字陰影**：`--shadow` 啟用，`--shadow-offset`（0–8）與 `--shadow-color` 調整；
  陰影在一般模式與走馬燈模式皆可使用。

```powershell
python screen_highlight_text.py --border-width 3 --border-color "#0d47a1" --shadow --shadow-offset 4 --shadow-color "#555555"
```

## 啟動參數

也可以在啟動時指定文字、字型、大小、顏色、透明度、走馬燈與位置：

```powershell
python screen_highlight_text.py --text "重要提醒：請注意螢幕高亮內容" --font "Microsoft JhengHei UI" --font-size 48 --marquee --marquee-speed 6 --marquee-width 900
```

可用參數：

| 參數 | 說明 | 預設值 |
| --- | --- | --- |
| `--text` | 啟動時顯示的文字 | `重點提示文字` |
| `--file` | 從外部 `.txt` 讀取文字（優先於 `--text`） | 無 |
| `--font` | 啟動時的字型名稱 | `Microsoft JhengHei UI` |
| `--font-size` | 字體大小，範圍 12 到 120 | `40` |
| `--bold` / `--no-bold` | 開啟或關閉粗體 | 預設粗體開啟 |
| `--highlight-color` | 高亮底色，例如 `#fff176` | `#fff176` |
| `--text-color` | 文字顏色，例如 `#111111` | `#111111` |
| `--opacity` | 透明度，範圍 0.2 到 1.0 | `0.85` |
| `--marquee` | 啟動時啟用走馬燈模式 | 關閉 |
| `--marquee-speed` | 走馬燈速度，範圍 1 到 20 | `4` |
| `--marquee-width` | 走馬燈高亮條寬度，範圍 200 到 2400 | `720` |
| `--border-width` | 邊框粗細，範圍 0 到 10（0 表示無邊框） | `0` |
| `--border-color` | 邊框顏色，例如 `#333333` | `#333333` |
| `--shadow` | 啟用文字陰影 | 關閉 |
| `--shadow-offset` | 陰影偏移量，範圍 0 到 8 | `3` |
| `--shadow-color` | 陰影顏色，例如 `#555555` | `#555555` |
| `--hotkey-off` | 停用全域快捷鍵 `Ctrl+Alt+H` | 預設啟用 |
| `--x` | 初始 X 座標 | `120` |
| `--y` | 初始 Y 座標 | `120` |

## 打包成 exe（可選）

如果想在沒有命令列的情境下使用，可以用 PyInstaller 打包：

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed screen_highlight_text.py
```

完成後可在 `dist` 資料夾找到 exe 檔。
