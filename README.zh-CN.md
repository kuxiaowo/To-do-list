<div align="center">

<br>

<img src="./web/assets/favicon.png" alt="待办清单时间线图标" width="144" height="144">

<h1>待办清单时间线</h1>

<p><strong>把截止日期变成可执行的每日计划，一套可自行部署的学习任务管理工具。</strong></p>

<p>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&amp;logoColor=white" alt="Python 3.10+"></a>
  <a href="https://vuejs.org/"><img src="https://img.shields.io/badge/前端-Vue%203-42b883?logo=vuedotjs&amp;logoColor=white" alt="Vue 3"></a>
  <a href="https://www.sqlite.org/"><img src="https://img.shields.io/badge/数据库-SQLite-003B57?logo=sqlite&amp;logoColor=white" alt="SQLite"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/许可证-MIT-8A2BE2" alt="MIT 许可证"></a>
</p>

<p>
  <a href="https://github.com/kuxiaowo/To-do-list/actions/workflows/tests.yml"><img src="https://github.com/kuxiaowo/To-do-list/actions/workflows/tests.yml/badge.svg?branch=main" alt="测试状态"></a>
  <a href="https://github.com/kuxiaowo/To-do-list/stargazers"><img src="https://img.shields.io/github/stars/kuxiaowo/To-do-list?style=flat&amp;logo=github&amp;label=Stars" alt="GitHub Stars"></a>
  <a href="https://github.com/kuxiaowo/To-do-list/commits/main"><img src="https://img.shields.io/github/last-commit/kuxiaowo/To-do-list?logo=git&amp;label=Last%20commit" alt="最近提交"></a>
</p>

<p><a href="./README.md">English</a> | <strong>简体中文</strong></p>

<p>
  <a href="./docs/zh-CN/README.md"><img src="https://img.shields.io/badge/文档-部署指南-0969DA?logo=readthedocs&amp;logoColor=white" alt="部署指南"></a>
  <a href="./docs/zh-CN/API.md"><img src="https://img.shields.io/badge/API-接口参考-00897B?logo=bookstack&amp;logoColor=white" alt="API 接口参考"></a>
  <a href="./docs/zh-CN/USER_GUIDE.md"><img src="https://img.shields.io/badge/指南-用户手册-F57C00?logo=gitbook&amp;logoColor=white" alt="用户手册"></a>
</p>

</div>

---

## 项目简介

待办清单时间线是一款支持中英文切换的学习任务管理 Web 应用，用于统一管理 DDL、待安排任务、习惯和每日计划。项目采用 Vue 3 静态前端、Python 轻量 HTTP 服务和 SQLite 数据库，主应用不需要 Node.js 构建流程。

## 主要功能

- 管理任务标题、科目、截止时间、优先级、备注和完成状态。
- 将尚未确定截止时间的任务放入待安排池，并按优先级整理。
- 使用横向时间线或月历浏览 DDL。
- 把任务拖入每日安排，形成具体的学习计划。
- 管理周期性习惯，并标记相互重叠的时间冲突。
- 按用户隔离账号、任务、每日安排和个性化设置。
- 使用可选 AI 助手分析任务，并在执行修改前进行审批。
- 通过本地 ManageBac Helper 预览并导入 DDL。
- 支持简体中文、英文以及浅色、深色主题。
- 可直接使用 Python 运行，也可通过脚本部署为 systemd 用户服务。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | Vue 3、Element Plus、原生 JavaScript |
| 后端 | Python 标准库 `http.server` |
| 数据库 | SQLite |
| 可选集成 | DeepSeek API、阿里云 OSS |
| 桌面 Helper | Electron |

前端依赖已保存在 `web/vendor`，生产环境不依赖外部 CDN。

## 快速开始

需要 Python 3.10 或更高版本。按照项目约定，推荐使用 conda 虚拟环境：

```bash
conda create -n todo-list python=3.10
conda activate todo-list
git clone https://github.com/kuxiaowo/To-do-list.git
cd To-do-list
python server.py
```

然后访问 <http://localhost:8092>。

首次启动时会自动创建 `data/todo-list.db`。如需修改监听地址、端口或启用可选 AI 功能，可先复制环境变量示例：

```bash
cp .env.example .env
```

如果需要通过阿里云 OSS 提供 ManageBac Helper 安装包下载，请安装可选依赖：

```bash
python -m pip install -r requirements.txt
```

完整配置和部署方式请阅读[中文部署文档](./docs/zh-CN/README.md)。

## 项目结构

```text
.
├── web/                       # Vue 静态前端
├── server.py                  # HTTP 服务、API 和数据库初始化
├── ai_prompts.json            # AI 助手提示词
├── managebac-sync-helper/     # 可选 Electron 桌面 Helper
├── tests/                     # 后端与工作流回归测试
├── docs/
│   ├── en/                    # 英文文档
│   └── zh-CN/                 # 简体中文文档
├── deploy-first-run.sh        # Linux 首次部署脚本
├── requirements.txt           # 可选 OSS 依赖
└── LICENSE
```

## 文档

| 文档 | 简体中文 | English |
| --- | --- | --- |
| 完整配置与部署 | [阅读](./docs/zh-CN/README.md) | [Read](./docs/en/README.md) |
| API 接口参考 | [阅读](./docs/zh-CN/API.md) | [Read](./docs/en/API.md) |
| 用户指南 | [阅读](./docs/zh-CN/USER_GUIDE.md) | [Read](./docs/en/USER_GUIDE.md) |
| ManageBac 集成 | [阅读](./docs/zh-CN/MANAGEBAC_SYNC.md) | [Read](./docs/en/MANAGEBAC_SYNC.md) |
| 安全说明 | [阅读](./docs/zh-CN/SECURITY.md) | [Read](./docs/en/SECURITY.md) |
| ManageBac Helper | [阅读](./managebac-sync-helper/docs/zh-CN/README.md) | [Read](./managebac-sync-helper/docs/en/README.md) |

## 开发

主应用没有打包步骤。修改前端文件后刷新浏览器，修改后端后重启 `server.py`。

运行后端测试：

```bash
python -m unittest discover -s tests -v
```

运行 ManageBac Helper 解析器测试：

```bash
cd managebac-sync-helper
npm test
```

GitHub Actions 会在推送和拉取请求时运行这两套测试。

## 许可证

本项目使用 [MIT License](./LICENSE)。
