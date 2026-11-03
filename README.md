# VPM 软件包清单模板
用于创建你自己的VPM插件清单，自带自动化构建以及自动发布功能。

清单由 GitHub Actions 每天自动同步上游最新版本，日常不需要手动修改 [`index.json`](index.json)。

## 🔄 自动同步上游

[`update_vpm.py`](update_vpm.py) 会读取 [`sources.json`](sources.json) 里的上游 VPM 源，把最新数据合并进 [`index.json`](index.json)：

- 已存在的包：只补充上游新增的版本，本地已有版本不会被覆盖（加 `--refresh` 才会用上游数据覆盖）；
- 上游新增的包：整体加入清单；
- 上游标记为 `private` 的版本：跳过，不写进清单；
- 每个包的版本按版本号从新到旧排序。

**自动运行**：[`update-listing.yml`](.github/workflows/update-listing.yml) 每天 UTC 03:17 跑一次，也能在 Actions 页面手动触发；发现变化时会以 `github-actions[bot]` 身份提交 `index.json`，GitHub Pages 随后自动更新网页。

**本地手动运行**：

```bash
python update_vpm.py            # 默认：抓取上游并写入 index.json（没有变化也会重写）
python update_vpm.py --dry-run  # 只预览变更，不写文件
```

**添加上游源**：把 VPM 清单地址加进 [`sources.json`](sources.json) 的 `sources` 数组即可，字符串或 `{"url": "..."}` 对象都支持。
[`merge_vpm.py`](merge_vpm.py) 现在只是兼容入口，实际逻辑都在 `update_vpm.py`。

## ▶ 快速开始

* 点击 [![使用此模板](https://user-images.githubusercontent.com/737888/185467681-e5fdb099-d99f-454b-8d9e-0760e5a6e588.png)](https://github.com/vrchat-community/template-package-listing/generate)
基于该模板新建GitHub项目，跟随页面指引完成设置。
  * 设置合适的仓库名称与描述。
  * 仓库可见性设置为「公开」，也可以先设置为「私有」，后续再修改。
  * **不要勾选「包含全部分支」**。
* 你可以直接在GitHub网页编辑本项目，也可以使用Git将仓库克隆到本地进行编辑。
  * 如果你不熟悉Git与GitHub，请查阅 [GitHub官方文档](https://docs.github.com/en/get-started/quickstart/)。

## 设置自动化工作流

你需要修改模板中的部分配置文件，优先修改 [`index.json`](index.json)：
- 填写清单基础信息，包括 [`name`](index.json#L2)名称、[`id`](index.json#L3)唯一ID、[`author`](index.json#L5)作者、[`description`](index.json#L10)描述等内容。
- 修改第4行的`"url"`字段，把`vrchat‑community`替换为你的GitHub用户名，`template‑package‑listing`替换为你的仓库名称。
> 这个地址就是GitHub Pages发布之后，VCC读取清单的实际链接。
> 举个例子：GitHub账号为`thupper`，仓库名称`thupper‑listing`，url填写：`"https://thupper.github.io/thupper-listing/index.json"`。
- 修改第5行`"url"`中的链接，填入当前这个仓库的GitHub地址。
- 如果插件存放在GitHub仓库，则在 [`githubRepos`](index.json#L16) 填写相关仓库信息。
- 如果插件是外部托管的`.zip`压缩包，则在 [`packages`](index.json#L19) 进行配置。
  - 如果不使用`githubRepos`或者`packages`，可以直接删除该配置项。
- 进入仓库「设置」页面，打开「Pages」设置，找到「构建和部署」。将来源下拉选项，从「从分支部署」切换为 **GitHub Actions**。

## 📃 清单如何更新

清单由 [`update-listing.yml`](.github/workflows/update-listing.yml) 每天自动更新：抓取 [`sources.json`](sources.json) 里的上游源，把新版本写进 [`index.json`](index.json) 并提交。
你也可以在 Actions 页面手动点 `Run workflow`，或在本地执行 `python update_vpm.py` 后自行提交。

你的清单访问地址格式：
`https://你的GitHub用户名.github.io/你的仓库名称`

## 🏠 自定义落地首页

`Website`文件夹存放网页全部文件，你可以自定义页面外观。页面大部分内容会自动读取 [`index.json`](index.json) 的配置自动填充。
> 就算不修改网页文件，整套功能依旧可以正常工作。

## 技术说明

自动化脚本都在仓库根目录，只用 Python 标准库，没有额外依赖：

### 清单同步任务
[`update_vpm.py`](update_vpm.py) + [`update-listing.yml`](.github/workflows/update-listing.yml)

工作流按计划运行脚本：脚本下载上游 VPM 清单 → 过滤 `private` 版本 → 合并进 [`index.json`](index.json)（已有版本不覆盖）→ 按版本号排序。
有变化时以 `github-actions[bot]` 提交，网页读取的 `index.json` 随之更新。

### 落地首页
[`index.html`](index.html) 是纯静态页面，通过 `fetch('index.json')` 读取清单，渲染下拉列表、版本选择与下载按钮。
页面上的「一键拉取」会先尝试直接访问 `sources.json` 里的上游源并即时合并，被浏览器跨域拦截时自动回退为重新拉取站点 `index.json`。
每次拉取结束后按钮会进入 60 秒冷却（`PULL_COOLDOWN_MS`，时间戳记在 `localStorage`），期间显示倒计时并禁止再次点击，防止频繁请求上游。

清单按 **Avatar 插件 / 世界插件 / 通用插件 / 着色器** 分类，分类映射写在 `index.html` 的 `CATEGORY_MAP` 里，没列出的包会按名称和描述关键词自动归类。
每个包展开后都有独立的「导入 VCC」「下载」「官网」和「复制包 ID」按钮；鼠标在插件上停留 2 秒会弹出中文简介（`BRIEF_ZH`）和原始英文描述。
[`Website`](Website) 文件夹是上游模板自带的首页模板，本项目已不再使用，可以忽略或删除。
