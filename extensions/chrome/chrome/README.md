# CCF DDL Tracker (Chrome Extension)

## 使用方法 / Usage

1. 打开 Chrome，进入 `chrome://extensions/`。/ Open Chrome and go to `chrome://extensions/`.
2. 打开右上角的“开发者模式”。/ Enable “Developer mode”.
3. 点击“加载已解压的扩展程序”，选择本仓库的 `chrome/` 目录。/ Click “Load unpacked” and select `chrome/`.
4. 安装完成后，点击浏览器工具栏的“CCF DDL Tracker”图标。/ Click the toolbar icon.

## 功能说明 / Features

- **当前版本**：扩展版本已更新为 `v2.0`，弹窗右上角会显示版本标记。/ The extension is now `v2.0`, and the popup header shows the current version.
- **添加 DDL**：填写标题、日期、时间，点击“添加”。/ Add title/date/time and click “Add”.
- **查看详情**：弹窗中会按时间排序展示多个 DDL，并显示剩余天数。/ Sorted list with remaining days.
- **徽标提示**：工具栏图标会显示最近一个 DDL 的剩余天数。/ Badge shows the nearest days left.
- **删除 DDL**：在条目右侧点击“删除”。/ Delete from the list.
- **双入口卡片**：新增截止日期和从 CCFDDL 导入改为一行两个入口卡片，点击后切换下方面板。/ Add DDL and Import from CCFDDL now appear as two side-by-side entry cards that switch the panel below.
- **导入推荐会议**：导入面板默认常驻显示，会优先显示已缓存会议，并在点击搜索框时获取最新推荐。/ The import panel stays visible by default, shows cached conferences first, and refreshes recommendations when the search field is focused.
- **官网直达**：从 CCFDDL 导入的会议会保留官网链接，加入“我的截止日期”后可直接点击卡片打开会议官网。/ Imported CCFDDL conferences retain their homepage links, and once added to "My DDLs" the card can be clicked to open the conference website.
- **底部工具栏**：中英切换和 CCFDDL 官网入口已移动到底部工具栏，右上角不再放操作项。/ Language switching and the CCFDDL website shortcut now live in the bottom toolbar instead of the top-right corner.
- **协作入口**：底部工具栏新增 GitHub 仓库链接，可直接打开项目主页参与开发。/ The bottom toolbar now includes a GitHub repository link so you can open the project page and contribute directly.
- **显示设置**：底部新增设置入口，可切换时间显示为 24 小时制或上午/下午 12 小时制。/ A new settings entry in the bottom bar lets you switch time display between 24-hour and 12-hour formats.
- **日期顺序**：设置面板新增日期顺序选项，可在“年月日”和“月日年”之间切换。/ The settings panel now includes a date-order option for switching between year/month/day and month/day/year.
- **底部贴边**：底部工具栏已固定贴到底边，去掉其下方的空白区域。/ The bottom utility bar is now anchored to the popup edge, removing the empty area beneath it.
- **底部更轻量**：底部工具栏进一步压缩为接近单行文字的样式，语言切换不再保留按钮感。/ The bottom utility bar is further compressed into a near single-line text-style row, and the language toggle no longer looks like a button.
- **启动误触保护**：弹窗刚打开时会短暂忽略导入入口的误触，避免工具栏点击把“从 CCFDDL 导入”意外点开。/ When the popup first opens, the import entry briefly ignores accidental clicks so the toolbar click does not unintentionally open "Import from CCFDDL".
- **原生弹窗**：点击工具栏图标会打开 Chrome 原生 popup，而不是独立窗口。/ Clicking the toolbar icon opens the native Chrome popup instead of a separate window.
- **原生日期选择器**：中英文界面都使用 Chrome 原生日期选择器，日期显示格式遵循浏览器或系统本地化设置。/ Both languages use Chrome's native date picker, and the displayed format follows browser or system localization.
- **界面微调**：压缩了顶栏高度，并优化了导入区的搜索与提示布局。/ The header is more compact, and the import panel now uses a cleaner search-and-hint layout.
- **DDL 标题行调整**：数量显示在标题右侧，刷新按钮保持右对齐。/ The DDL header keeps the count beside the title while the Refresh button stays right-aligned.
- **弹窗图标更新**：弹窗顶部图标改为 `chrome/icons/logo.png`。/ The popup header icon now uses `chrome/icons/logo.png`.
- **整体更紧凑**：统一压缩了表单、卡片、列表项和按钮的纵向间距。/ The form, cards, list rows, and buttons now use tighter vertical spacing overall.
- **操作更轻量**：新增表单提交成功后会自动收起，导入面板默认常驻，而推荐会议只在点击搜索框时自动加载。/ The add form closes after a successful submission, the import panel stays visible by default, and recommendations only auto-load when the search field is focused.
- **内部滚动优先**：尽量避免外层弹窗滚动，“我的 DDL”和推荐会议列表各自在内部滚动。/ The popup avoids outer scrolling as much as possible, with "My DDLs" and recommendations scrolling inside their own areas.
- **入口卡片稳定切换**：导入面板默认展开，再次点击导入卡片会收起它，点击新增卡片会先关闭导入面板。/ The import panel starts expanded, clicking the import card again collapses it, and clicking the add card closes the import panel first.
- **悬浮搜索选择器**：点击搜索会议输入框时，会自动加载并弹出悬浮的推荐会议列表。/ Clicking the conference search input auto-loads and opens a floating recommendation picker.
- **入口文案更紧凑**：顶部两个入口卡片的标题和说明文字现在居中显示，并进一步压缩了行高。/ The two top entry cards now center their title and helper text with tighter line height.
- **入口角标图标**：顶部两个入口卡片的图标移动到左上角，不再额外占用行高。/ The two top entry card icons now sit in the top-left corner without adding extra line height.
- **导入图标优化**：从 CCFDDL 导入入口的角标改为更简洁的搜索图标。/ The CCFDDL import entry badge now uses a cleaner search icon.
- **英文文案微调**：英文入口卡片的标题和说明文字做了缩短，减少不自然换行。/ The English entry-card title and helper copy were shortened to reduce awkward wrapping.
- **中文标题调整**：中文界面的“我的 DDL”改为“我的截止日期”。/ The Chinese "My DDLs" title was renamed to "我的截止日期".
- **导入提示文案**：搜索框下方增加了一行小字，提示点击搜索框可获取最新会议列表。/ A small helper line below the import search field explains that clicking it loads the latest conference list.
- **提示与刷新按钮微调**：导入区提示文字改为居中显示，“我的截止日期”的刷新按钮改为图标按钮。/ The import helper text is now centered, and the "My DDLs" refresh control now uses an icon button.
- **刷新图标与动效**：刷新按钮改为更常见的无底框 SVG 图标，并增加旋转动效表示已触发刷新。/ The refresh control now uses a more standard frameless SVG icon and spins briefly to indicate that refresh was triggered.

注：导入优先使用 GitHub 仓库数据，失败时回退到 CCFDDL ICS。  
Note: Imports prefer GitHub repository data and fall back to the CCFDDL ICS feed.

## 数据存储 / Data

所有数据保存在 `chrome.storage.local` 中，仅在本机可见。/ Stored locally in `chrome.storage.local`.
