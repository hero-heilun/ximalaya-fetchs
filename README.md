# 喜马拉雅音频批量下载工具文档

[![GitHub stars](https://img.shields.io/github/stars/hero-heilun/ximalaya-fetchs?style=social)](https://github.com/hero-heilun/ximalaya-fetchs/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/hero-heilun/ximalaya-fetchs?style=social)](https://github.com/hero-heilun/ximalaya-fetchs/network/members)
[![GitHub issues](https://img.shields.io/github/issues/hero-heilun/ximalaya-fetchs)](https://github.com/hero-heilun/ximalaya-fetchs/issues)
[![GitHub license](https://img.shields.io/github/license/hero-heilun/ximalaya-fetchs)](https://github.com/hero-heilun/ximalaya-fetchs/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-donate-yellow.svg)](https://www.buymeacoffee.com/heilunhero)

## 1. 项目简介

本项目为喜马拉雅音频平台的批量下载与管理工具，基于 Python 实现，支持专辑音频的批量获取、解密与下载，适合个人备份、学习与研究用途。

## 2. 应用截图
![登录界面截图](image/screen_login.png)
![应用界面截图](image/screenshot.png)


*图：应用主界面，展示专辑信息获取、曲目解析、缓存状态显示等功能*

## 3. 主要功能

- **智能登录系统**：集成扫码登录和手动Cookie输入，支持自动检测和管理登录状态：
  - **自动登录检测**：启动时自动检查Cookie有效性
  - **扫码登录**：使用喜马拉雅App扫描二维码快速登录
  - **手动Cookie输入**：支持从浏览器复制Cookie进行登录
  - **登录管理**：主界面提供登录管理功能，随时切换账号
- **专辑批量下载**：支持通过专辑 ID 批量获取并下载全部音频，支持断点续传。
- **多线程下载**：可配置线程数，大幅提升下载速度。
- **音频 URL 解密**：自动解密加密的音频播放链接。
- **智能缓存系统**：基于 SQLite 的高性能缓存，显著提升重复访问速度：
  - **曲目 URL 缓存**：24小时有效期，避免重复解析
  - **专辑页面缓存**：6小时有效期，快速加载专辑列表
  - **批量查询优化**：毫秒级响应，提升 GUI 流畅度
  - **自动过期清理**：智能管理缓存空间
- **收听历史获取**：可获取个人账号的收听历史（需配置 Cookie）。
- **单曲信息抓取与下载**：支持通过 trackId 获取单个音频的详细信息，并可单独下载音频，支持根据音频标题自动命名文件。
- **专辑简介 Markdown 支持**：下载专辑时自动生成 Markdown 格式的专辑简介（album_info.md），便于阅读和管理。
- **API 签名生成**：内置 xm-sign 生成逻辑，适配新版接口。
- **图形界面支持**：集成简单 GUI，便于操作。

## 4. 项目架构

本项目采用模块化设计，主要分为以下几个核心组件：

```mermaid
graph TD
    A[用户界面/CLI] --> B(main.py)
    B --> C{下载器模块 - downloader/}
    B --> D{抓取器模块 - fetcher/}
    C --> E[文件下载逻辑]
    D --> F[API请求与数据解析]
    C --> D
    D --> C
    C --> G[工具函数 - utils/]
    D --> G
    G --> H[签名生成]
    G --> I[SQLite缓存系统]
    D --> I
    I --> D
    I --> J[批量查询优化]
    I --> K[自动过期管理]
```
**说明**：
- **用户界面/CLI**：提供图形界面 (`gui/gui.py`) 和命令行接口，作为用户与工具交互的入口。
- **`main.py`**：项目主入口，负责初始化应用和协调各模块。
- **下载器模块 (`downloader/`)**：
    - 负责音频文件的实际下载，包括单曲和专辑的批量下载。
    - 处理下载重试、断点续传等逻辑。
- **抓取器模块 (`fetcher/`)**：
    - 负责从喜马拉雅平台抓取专辑信息、音轨列表、加密URL等数据。
    - 包含对API响应的解析和数据结构化。
    - 集成缓存系统，优先使用缓存数据，减少网络请求。
- **工具函数 (`utils/`)**：
    - 提供辅助功能，如音频URL解密、文件路径处理等。
    - **签名生成 (`ximalaya_xmsign.py`)**：负责生成喜马拉雅API请求所需的 `xm-sign` 签名。
    - **SQLite缓存系统 (`sqlite_cache.py`)**：
      - 高性能数据库缓存，支持曲目URL和专辑页面双重缓存
      - 智能过期管理，自动清理过期数据
      - 批量查询优化，提升GUI响应速度
      - 线程安全设计，支持并发访问

## 5. 目录结构

```
ximalaya-main/
├── cache/                # 缓存目录（自动创建）
│   └── track_cache.db    # SQLite 缓存数据库
├── downloader/           # 下载核心模块
│   ├── album_download.py
│   ├── downloader.py
│   └── single_track_download.py
├── fetcher/              # 数据抓取与解析
│   ├── album_fetcher.py
│   ├── history_fetch.py
│   ├── track_fetcher.py
│   └── track_info_fetcher.py
├── gui/                  # 图形界面
│   └── gui.py
├── image/                # 项目截图和图片资源
│   └── screenshot.png    # 应用界面截图
├── tests/                # 单元测试
│   ├── test_downloader.py
│   └── test_fetcher.py
├── utils/                # 工具函数与签名生成
│   ├── sqlite_cache.py   # SQLite 缓存系统
│   ├── utils.py
│   └── ximalaya_xmsign.py
├── .env                  # 环境变量配置文件 (不提交到版本控制)
├── .gitignore            # Git 忽略文件
├── main.py               # 启动入口（含 GUI）
├── pyproject.toml        # 项目依赖管理 (uv)
├── README.md             # 项目说明
├── uv.lock               # uv 锁定文件
└── xm-demo.py            # xm-sign 生成示例
```

## 6. 缓存系统详解

本项目采用基于 SQLite 的智能缓存系统，显著提升性能和用户体验：

### 6.1 缓存类型

- **曲目 URL 缓存**：
  - 缓存加密和解密的音频 URL
  - 有效期：24小时
  - 支持 URL 有效性验证，失效自动重新获取

- **专辑页面缓存**：
  - 缓存专辑曲目列表信息
  - 有效期：6小时
  - 快速加载专辑页面，无需重复网络请求

### 6.2 性能优化

- **批量查询**：单次查询支持数百个曲目，响应时间 < 1ms
- **智能过期管理**：自动清理过期缓存，保持数据库精简
- **线程安全**：支持多线程并发访问，确保数据一致性
- **内存优化**：采用分页加载，减少内存占用

### 6.3 缓存管理

缓存数据存储在 `cache/track_cache.db` 文件中，包含两个主要表：
- `track_cache`：曲目 URL 缓存
- `album_page_cache`：专辑页面缓存

可通过 GUI 界面查看缓存统计信息，包括缓存命中率、存储空间占用等。

## 7. 环境准备与部署

### 7.1 环境要求

- Python 3.11 及以上版本
- `uv` 包管理器 (推荐)

### 7.2 依赖安装

本项目使用 `uv` 进行依赖管理。请确保您的环境中已安装 `uv`。如果未安装，可以通过 `pip` 安装：
```shell
pip install uv
```
然后，在项目根目录运行以下命令安装所有依赖：
```shell
uv sync
```

### 7.3 Cookie 配置与登录管理

为了获取收听历史或下载部分受限内容，您需要配置喜马拉雅的 `Cookie`。本工具提供了两种登录方式：

#### 7.3.1 自动登录（推荐）

启动应用时，如果未检测到有效Cookie，系统会自动提示登录：

1. **扫码登录**：
   - 选择"扫码登录"选项卡
   - 点击"获取二维码"按钮
   - 使用喜马拉雅App扫描显示的二维码
   - 在手机上确认登录
   - 系统自动保存Cookie到`.env`文件

2. **手动输入Cookie**：
   - 选择"手动输入Cookie"选项卡
   - 按照界面提示从浏览器获取Cookie
   - 粘贴Cookie内容并验证
   - 系统自动保存到`.env`文件

#### 7.3.2 手动获取Cookie（传统方式）

如果需要手动配置Cookie：
1. 登录喜马拉雅网页版。
2. 打开浏览器开发者工具（F12），切换到 `Network` (网络) 标签页。
3. 刷新页面，找到任意一个对 `ximalaya.com` 域名的请求。
4. 在请求的 `Headers` (请求头) 中找到并复制 `Cookie` 字段的完整内容。
5. 在项目根目录新建 `.env` 文件（如果已存在则编辑），内容如下：
   ```dotenv
   XIMALAYA_COOKIES="<你的Cookie内容>"
   ```

#### 7.3.3 登录管理

在主界面中，您可以：
- 点击"登录管理"按钮重新登录或更换账号
- 系统会检测当前Cookie状态并提供相应选项
- 支持随时切换账号或更新过期的Cookie

**注意**：`.env` 文件已被添加到 `.gitignore`，不会被提交到版本控制，请放心配置敏感信息。

### 7.4 运行指南

#### 7.4.1 图形界面启动 (推荐)

推荐使用 GUI 进行操作，支持专辑批量下载、路径选择、缓存统计等功能，操作直观：
```shell
python main.py
```

**GUI 新特性**：
- **智能登录系统**：启动时自动检测Cookie，支持扫码登录和手动输入
- **登录管理按钮**：主界面可随时管理登录状态，切换账号
- **缓存状态显示**：实时显示曲目缓存状态，绿色表示已缓存
- **缓存统计面板**：查看缓存命中率、存储使用情况等信息
- **快速解析模式**：优先使用缓存，显著提升加载速度
- **性能优化**：批量查询优化，界面响应更加流畅

#### 7.4.2 命令行使用

**批量下载专辑**：
```shell
python -m downloader.album_download --album_id <专辑ID> [--start_page 1] [--end_page N] [--threads 4]
```
- 支持断点续传和多线程下载。
- 自动利用缓存系统，提升重复下载效率。
- 下载完成后会在专辑目录下自动生成 `album_info.md`，包含专辑简介（Markdown 格式）。

**抓取单曲信息**：
```shell
python -m fetcher.track_info_fetcher --track_id <音频ID> [--album_id <专辑ID>]
```
- 可获取音频详细信息。

**下载单曲 (支持智能命名)**：
```shell
python -m downloader.single_track_download --track_id <音频ID> [--album_id <专辑ID>] [--output <保存文件名>]
```
- 支持根据音频标题自动命名文件。

**获取收听历史**：
```shell
python -m fetcher.history_fetch
```
- 需先配置 `XIMALAYA_COOKIES` 环境变量。

**API 签名测试**：
```shell
python -m utils.ximalaya_xmsign
# 或
python xm-demo.py
```

## 8. 贡献指南

我们欢迎并感谢所有对本项目感兴趣的贡献者！如果您希望参与项目开发，请遵循以下步骤：

1.  **Fork 项目**：在 GitHub 上 Fork 本项目到您的个人仓库。
2.  **克隆到本地**：
    ```shell
    git clone https://github.com/your-username/ximalaya-main.git
    cd ximalaya-main
    ```
3.  **创建分支**：为您的新功能或 Bug 修复创建一个新的分支：
    ```shell
    git checkout -b feature/your-feature-name
    # 或
    git checkout -b bugfix/your-bug-fix
    ```
4.  **安装依赖**：确保所有依赖都已安装：
    ```shell
    uv sync
    ```
5.  **编写代码**：
    - 遵循项目现有的代码风格和规范。
    - 确保您的代码有清晰的注释。
    - **编写单元测试**：为您的新功能或修改编写相应的单元测试，确保代码的健壮性。
6.  **运行测试**：在提交前，请确保所有测试通过：
    ```shell
    pytest
    ```
7.  **提交更改**：
    ```shell
    git add .
    git commit -m "feat: Add your feature description"
    # 或
    git commit -m "fix: Fix your bug description"
    ```
    请使用清晰、简洁的提交信息。
8.  **推送分支**：
    ```shell
    git push origin feature/your-feature-name
    ```
9.  **提交 Pull Request (PR)**：
    - 在 GitHub 上向本项目提交 Pull Request。
    - 在 PR 描述中详细说明您的更改内容、目的以及如何测试。

感谢您的贡献！

## 9. 注意事项

- **Cookie 有效期有限，失效请重新获取。**
- **部分 VIP 内容需账号权限。**
- **专辑下载会自动生成 album_info.md（Markdown 简介），便于归档。**
- **缓存系统自动管理，首次使用时会创建 `cache/` 目录。**
- **缓存数据库占用空间较小，通常不需要手动清理。**
- **请勿用于商业或非法用途，仅供学习交流。**
- **如遇接口变动或反爬升级，请关注项目更新。**

## 10. 常见问题

### 性能相关
- **下载速度慢？** 请尝试增加线程数，缓存系统会自动提升重复下载效率。
- **GUI 响应慢？** 新版本已优化缓存查询性能，如仍有问题请重启应用。
- **缓存占用空间大？** 缓存会自动过期清理，也可手动删除 `cache/` 目录重置。

### 功能相关
- **下载失败？** 请检查 Cookie、专辑 ID 是否正确，或接口是否变动。
- **缓存不生效？** 首次访问需要建立缓存，后续访问会明显加速。
- **专辑页面加载慢？** 使用"快速解析"模式，优先使用缓存数据。

### 其他问题
- 遇到其他问题请提交 issue 或自行调试。
- 查看 GUI 中的缓存统计信息可帮助诊断性能问题。

## 11. 支持项目

如果这个项目对您有帮助，欢迎支持我们的开发工作！

### 💰 打赏支持

如果这个项目对您有帮助，请考虑给开发者买杯咖啡 ☕

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-donate-yellow.svg?style=for-the-badge&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/heilunhero)
[![Ko-Fi](https://img.shields.io/badge/Ko--fi-F16061?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/heilunhero)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://www.paypal.me/heilunhero)

您也可以通过以下方式支持项目：

**SOL链钱包地址：**
```
DkWRgo5jpmM98zaEgdPQLHL9QrGeCYUphQVmSGwr7pJd
```

![打赏二维码](image/wallet.PNG)

感谢您的支持！每一份打赏都是对我们持续改进和维护这个项目的巨大鼓励。

### ⭐ 其他支持方式

- 给项目点个 Star ⭐
- 分享给更多需要的朋友
- 提交 Bug 反馈和功能建议
- 参与代码贡献