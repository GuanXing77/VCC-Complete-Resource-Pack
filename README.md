# VPM 软件包清单模板
用于创建你自己的VPM插件清单，自带自动化构建以及自动发布功能。

配置全部完成后，你只需要修改 [`index.json`](index.json) 文件，就可以生成VPM可用的插件清单，清单内所有插件都可以获得版本更新。

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

## 📃 重新构建插件清单

当你向`main`分支提交改动，或者手动触发工作流，`Build Repo Listing`任务就会运行。
该任务会读取全部发布版本，生成清单文件，通过GitHub Pages免费部署网页。
生成完成的清单可以直接导入VPM，用来管理插件更新；同时自动生成简易网页展示你的插件信息。

你的清单访问地址格式：
`https://你的GitHub用户名.github.io/你的仓库名称`

## 🏠 自定义落地首页

`Website`文件夹存放网页全部文件，你可以自定义页面外观。页面大部分内容会自动读取 [`index.json`](index.json) 的配置自动填充。
> 就算不修改网页文件，整套功能依旧可以正常工作。

## 技术说明

你可以自由修改自动化脚本适配你的需求。如果你有优化建议，欢迎提交Pull Request。
下面简单介绍模板自带自动化任务：

### 清单构建任务
[build‑listing.yml](.github/workflows/build-listing.yml)

这是组合式工作流，读取 [`index.json`](index.json)，输出VPM能够识别的仓库清单。
为了扫描所有Release发布版本并合并清单，工作流会拉取外部[动作仓库](https://github.com/vrchat-community/package-list-action)，内部是基于Nuke开发的VPM核心工具库。

目前任务会执行`BuildRepoListing`，运行结束之后自动调用`RebuildHomePage`生成首页。
如果你只想单独刷新首页，可以复制调用步骤，替换执行目标名称即可。
