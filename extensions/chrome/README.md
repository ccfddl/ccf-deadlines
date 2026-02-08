# CCF DDL Tracker 🚀  
*A Lightweight Chrome Extension for Tracking CCF Deadlines*

CCF DDL Tracker 是一个 **轻量、实用的 Chrome 浏览器插件**，用于集中管理和提醒 **CCF 相关会议 / 截止日期（DDL）**，适合科研人员、学生和开发者日常使用。

📌 **数据来源同步自官方 CCFDDL 仓库 ｜ 插件同步至CCFDDL 仓库**：  https://github.com/ccfddl/ccf-deadlines

<img width="442" height="653" alt="Snipaste_2026-02-08_12-51-14" src="https://github.com/user-attachments/assets/df9dd755-0d3e-476d-902c-36ef460837e6" />
<img width="381" height="614" alt="Snipaste_2026-02-08_12-51-54" src="https://github.com/user-attachments/assets/b0537a5c-ce59-4f53-81bb-4dce5547d29d" />

---

## ✨ Features

- 📝 **快速添加 DDL**  
  手动输入标题、日期和时间，一键添加。

- 📅 **清晰的时间排序视图**  
  所有 DDL 按截止时间自动排序，并实时显示剩余天数。

- 🔔 **徽标倒计时提醒**  
  浏览器工具栏图标显示最近一个 DDL 的剩余天数，抬头即见。

- 🗑 **一键删除**  
  支持在列表中直接移除已完成或不需要的 DDL。

- 🔄 **从 CCFDDL 官方仓库导入**  
  - 优先从 GitHub 仓库获取最新会议信息  
  - 若 GitHub 访问失败，自动回退到 CCFDDL 的 ICS 数据源

- 🌐 **中英双语界面**  
  点击右上角 **EN / 中文** 按钮即可切换语言。

---

## 📦 Installation / 安装方式

### 开发者模式安装（推荐）

1. 打开 Chrome，访问： `chrome://extensions/`
2. 打开右上角的 **开发者模式（Developer mode）**
3. 点击 **加载已解压的扩展程序（Load unpacked）**
4. 选择本仓库下的目录：`extensions/chrome`
5. 安装完成后，点击工具栏中的 **CCF DDL Tracker** 图标即可使用

---

## 🧭 Usage / 使用说明

1. 点击浏览器工具栏中的 **CCF DDL Tracker**
2. 选择：
- 手动添加新的 DDL  
- 或点击 **加载 / Load**，从 CCFDDL 自动导入会议截止日期
3. 在弹窗中查看所有 DDL 及其剩余时间
4. 使用删除按钮清理已完成事项

---

## 🗂 Data & Privacy / 数据与隐私

- 所有数据均存储在：`chrome.storage.local`
- 📍 **仅保存在本机**
- 🚫 不上传、不联网同步、不收集任何个人信息

---

## 🎯 Motivation

CCF 会议截止日期分散、频繁更新，容易遗漏。  
本插件旨在提供一个：

- **无需登录**
- **即装即用**
- **专注 CCF 场景**
- **低干扰、高可见性**

的 DDL 管理工具，作为科研日常的轻量辅助。

---

## 🛠 Tech Stack

- Chrome Extension (Manifest V3)
- Vanilla JavaScript
- chrome.storage.local
- GitHub + ICS 数据源解析

---

## 📌 Roadmap (Planned)

- [ ] 支持按会议等级（A/B/C）筛选
- [ ] DDL 即将到期高亮提醒
- [ ] 导入自定义 ICS
- [ ] Chrome Web Store 上架

---

## 🤝 Acknowledgements

- 数据来源：**CCFDDL 官方仓库**  
https://github.com/ccfddl/ccf-deadlines

---

## 📄 License

MIT License



