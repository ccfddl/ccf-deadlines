# CCF DDL Tracker (Chrome Extension)

## 使用方法 / Usage

1. 打开 Chrome，进入 `chrome://extensions/`。/ Open Chrome and go to `chrome://extensions/`.
2. 打开右上角的“开发者模式”。/ Enable “Developer mode”.
3. 点击“加载已解压的扩展程序”，选择本仓库的 `extensions/chrome` 目录。/ Click “Load unpacked” and select `extensions/chrome`.
4. 安装完成后，点击浏览器工具栏的“CCF DDL Tracker”图标。/ Click the toolbar icon.

## 功能说明 / Features

- **添加 DDL**：填写标题、日期、时间，点击“添加”。/ Add title/date/time and click “Add”.
- **查看详情**：弹窗中会按时间排序展示多个 DDL，并显示剩余天数。/ Sorted list with remaining days.
- **徽标提示**：工具栏图标会显示最近一个 DDL 的剩余天数。/ Badge shows the nearest days left.
- **删除 DDL**：在条目右侧点击“删除”。/ Delete from the list.
- **从 CCFDDL 导入**：点击“加载”后可搜索并添加官网未过期的会议 DDL（可用搜索过滤）。/ Import upcoming items from CCFDDL.

## 数据存储 / Data

所有数据保存在 `chrome.storage.local` 中，仅在本机可见。/ Stored locally in `chrome.storage.local`.
