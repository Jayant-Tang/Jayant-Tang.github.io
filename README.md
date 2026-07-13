# Jayant's Blog

个人技术博客源码，基于 [Hexo](https://hexo.io/) 构建，部署在 [jayant-tang.github.io](https://jayant-tang.github.io)。

主要写嵌入式、Nordic、Zephyr、BLE/WiFi/LTE、Matter 等相关内容。

## 功能

- **静态博客**：Hexo + Fluid 主题，支持标签、分类、归档、本地搜索、离线缓存（PWA）
- **自动部署**：推送到 `master` 后，GitHub Actions 构建并通过官方 Pages Actions 发布
- **博客园同步**：同一次 CI 可将变更文章同步到博客园，并自动回写 `postId` 等元数据
- **评论**：Giscus（GitHub Discussions）
- **数学公式**：Markdown-it + KaTeX

## 技术栈

| 类别 | 选型 |
| --- | --- |
| 静态站点 | Hexo 8 |
| 主题 | hexo-theme-fluid |
| 部署 | GitHub Actions + `deploy-pages` |
| 博客园同步 | Python（`tools/cnblogs/`） |

## 本地测试

```bash
git clone https://github.com/Jayant-Tang/Jayant-Tang.github.io.git
cd Jayant-Tang.github.io
npm install
npm run server    # 本地预览 http://localhost:4000
```

写文章：在 `source/_posts/` 新建 Markdown，然后 `git push origin master`，CI 会自动构建、部署，并按需同步博客园。

## 文档

详细架构、CI 流程、博客园同步配置与运维说明见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 目录结构

```
source/_posts/     文章
source/            页面与其他静态资源
_config.yml        Hexo 主配置
_config.fluid.yml  主题配置
.github/workflows/ CI 工作流
tools/cnblogs/     博客园同步脚本
```

## 许可

### 代码与工程文件（MIT）

除下文「文章内容」外，本仓库中的 Hexo 配置、主题自定义、CI 工作流、`scripts/`、`tools/`、`injects/` 等工程文件以 [MIT License](LICENSE) 发布。你可以自由参考、复用和修改这些搭建与脚本代码，但需保留版权声明。

### 文章内容（`source/_posts/`）

`source/_posts/` 下的 Markdown 原创文章**不适用 MIT**，版权归作者所有。仓库内的文章源文件不得因根目录 MIT 许可而被视为可随意再分发或商用的内容。

已发布站点上，Fluid 主题会在文章页底部展示 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)（见 `_config.fluid.yml` 中 `post.copyright.license: 'BY'`）。该许可仅针对**线上已发布的 HTML 页面**；转载、改编或商用请以页面底部标注的 CC 条款为准，且不等同于对 Git 仓库内 Markdown 源文件的额外授权。
