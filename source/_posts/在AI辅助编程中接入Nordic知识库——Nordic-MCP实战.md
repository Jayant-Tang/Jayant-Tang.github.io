---
title: 在AI辅助编程中接入Nordic知识库——Nordic MCP实战
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2026-06-24 10:30:00
cover: null
tags:
- Nordic
- AI
- MCP
- Claude Code
- Cursor
categories: Nordic
typora-root-url: ./..
sticky: 999
cnblogs:
  postId: '20779903'
  url: https://www.cnblogs.com/jayant97/articles/20779903
  lastPublishedAt: '2026-07-06T18:20:52+08:00'
  sourceHash: sha256:e8e317920ff3fcb76fda6ced318ba52b0da12e47f19a4b04fc1f0e9183722765
  status: imported
  postType: Article
---

> 本文基于 Nordic MCP 第一版（2026年6月发布），介绍如何将 Nordic 知识库接入 Claude Code 和 Cursor CLI 等 AI 编程助手。

# 1. 为什么需要 Nordic MCP？

NCS（nRF Connect SDK）是一个庞大的嵌入式开发平台。对开发者来说，NCS 的文档量巨大且分散——有官方的 API 参考、DevZone 问答、DevAcademy 教程、PS（Product Specification）手册等等。

在日常开发中，常见的痛点包括：

- **查文档效率低**：每次查 API 参数或 Kconfig 选项，都需要在不同网站间来回切换搜索
- **LLM 缺乏 Nordic 上下文**：ChatGPT、Claude 等通用 AI 助手虽然能写代码，但它们对 NCS/Zephyr 的特定 API、驱动模型、设备树结构缺乏深入了解，生成的代码往往不准确
- **重复性工作多**：添加 Shell 命令、生成设备树、迁移代码到新 SDK 版本等重复性任务占用大量时间

但是如果使用 AI Agent，所有的“繁琐”都变成了“丰富的资源”。

Nordic MCP（Model Context Protocol）正是为解决这些问题而生。它由 Nordic 官方维护，将最新的 SDK 文档、技术参考和开发实践打包成 AI 助手可以直接调用的知识库，让 Claude Code、Cursor、GitHub Copilot 等 MCP 客户端从"通用 LLM"变身"Nordic 专家"。

> 简单说：Nordic MCP = 把 Nordic 知识库接入你的 AI 编程助手。AI 不再凭空编造 API，而是实时查阅官方文档后给出答案。

# 2. Nordic MCP 提供了什么？

Nordic MCP 是一个 HTTP MCP Server（部署在 `https://aidev.nordicsemi.com/mcp`），通过 OAuth 2.0 认证。接入后，AI 助手能够实时查阅 Nordic 官方的以下知识源：

- **SDK 文档**：NCS API 参考、驱动模型、Kconfig 与设备树绑定等
- **DevAcademy**：Nordic 官方教程和 Hands-on 示例
- **DevZone Q&A**：开发者社区的技术问答沉淀
- **产品规格书（PS）**：SoC 的硬件寄存器、电气特性等底层参考
- **nrfutil 手册**：命令行工具的完整用法
- **NCS/Zephyr 编码指南**：嵌入式代码开发与审查的最佳实践

这些知识不需要用户手动检索——AI 会在对话中自动调用相关资源来回答问题或生成代码。

## 典型使用场景

Nordic 官方给出了以下典型场景：

- **SDK 开发辅助**：让 AI 帮你添加 Shell 命令、配置 Kconfig、编写设备树、调用外设驱动 API
- **应用迁移到新 SDK 版本**：自动分析 API 变化并生成迁移代码
- **自定义板卡支持**：根据硬件描述自动生成设备树和 Kconfig 配置
- **学习 NCS/Zephyr**：对 API、驱动模型、配置系统等概念进行问答式学习
- **NCS 环境搭建**：引导式安装工具链、初始化工作区、拉取依赖

> 如果同时接入 nRF Cloud MCP，还可以让 AI 分析设备现场数据、排查 crash、评估固件版本的发布质量等。详见第 7 节。

# 3. 效果演示

这里用claude code示例，首先把一块nRF54L15开发板连接到电脑上。

然后打开NCS v3.3.0，打开claude code，开始进行闭环验证测试：

![image-20260624162713408](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined2688c6049d7df467cb0c0e943baf474b.png)

![image-20260624164214179](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined030e981947a48e51eb66f0502b27faab.png)

![image-20260624164226527](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined7174d4734e2a2cf050685a1e9970c140.png)

# 4. Claude Code 接入 Nordic MCP

Claude Code 是 Anthropic 推出的命令行 AI 编程工具，对 MCP 的支持最为完善。以下以 Windows 平台为例。

## 4.1 添加 MCP Server

打开终端，执行以下命令将 Nordic MCP 注册到 Claude Code：

```bash
# 添加 Nordic MCP 服务器
claude mcp add --transport http nordic-mcp https://aidev.nordicsemi.com/mcp
```

> `--transport http` 表示这是一个远程 HTTP MCP 服务器（而非本地进程）。
> `nordic-mcp` 是你给这个服务器起的名字，可以自定义。

## 4.2 完成 OAuth 认证

启动 Claude Code 会话后，执行斜杠命令完成认证：

```bash
# 在 Claude Code 交互界面中
/mcp
```

![image-20260624154545373](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefineddc3dd48d1a29ca2830e6e0b923a551ed.png)

![image-20260624154617555](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined2ce80697fc67ffb2c138a88217ff7b0d.png)

选择 `nordic-mcp`，然后选择 **Authenticate**。浏览器会自动打开 myNordic 登录页面：
![image-20260624154705439](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined2ee498c7bd357bcdbdfa65b4165c7b4a.png)

1. 输入你的 myNordic 账号（在 [mynordic.nordicsemi.com](https://mynordic.nordicsemi.com) 注册）
2. 授权 Claude Code 访问 Nordic MCP
3. 浏览器跳转回终端，认证完成

   ![image-20260624154719631](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined955ed99f0556b64e10aa5db9bb9124bd.png)

   ![image-20260624154829313](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedfb5cd6f6e31c97b1babe9e56b8dc71f2.png)

> **注意**：
> - 如果弹窗失败，手动将 URL 粘贴到浏览器即可
> - 认证 token 会自动刷新，无需重复登录



## 4.3 开始使用

认证完成后，直接在 Claude Code 中用自然语言提问即可。如果问题和Nordic开发有关，AI 会自动调用 Nordic MCP 搜索知识库。

例如：

> "帮我查一下 nRF54L15 的 UICR 地址范围"
>
> "用 NCS 写一个 BLE 广播初始化代码"
>
> "解释 Zephyr 中 bt_enable() 的调用时机和注意事项"

首次使用可能需要授权：
![image-20260624155005498](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedc1d33ad231b155c607ee3521bfb38f60.png)

Claude Code 会显示它何时调用了 Nordic 知识库：

![image-20260624155102104](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined5134959e85772c60270fc2f6913201c7.png)

# 5. Cursor CLI 接入 Nordic MCP

Cursor 是基于 VS Code 的 AI 编辑器，同样支持 MCP。以下分别介绍 GUI 和 CLI 两种配置方式。

## 5.1 Cursor GUI 配置

在 Cursor 中：
![image-20260624155351261](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined87467672c289429765c45a64d93c1481.png)

1. 打开 **Settings** → **MCP** → **Add new MCP server**
2. 填写配置：
   ![image-20260624155523749](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined92764d6b6cb8729558beaa200ff484ef.png)
   
   ```json
   "nordic-mcp": {
       "type": "http",
       "url": "https://aidev.nordicsemi.com/mcp"
   }
   ```
3. 保存文件

保存后点击 connect 触发 OAuth 认证流程，完成 myNordic 登录即可。

![image-20260624155615794](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb5dd9af1e9565e7e5afb0aa097af073b.png)

![image-20260624155829260](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined9be567ab36a8de892ae5e3ca3c7c0113.png)

![image-20260624160034026](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined62fd9b3f57fe52ccac4f7719d8101cfb.png)

## 5.2 Cursor CLI 配置

Cursor CLI 用户可以通过 JSON 配置文件添加 MCP Server。

找到 Cursor 的 MCP 配置文件（通常是`$HOME/.cursor/mcp.json`），添加以下内容：

```json
{
  "mcpServers": {
    "nordic-mcp": {
      "type": "http",
      "url": "https://aidev.nordicsemi.com/mcp"
    }
  }
}
```

![image-20260624160521683](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined25c07071488c8e0fdeb4273b4b5ee40a.png)

然后在 Cursor CLI中进行认证：

```powershell
# 开启Cursor CLI
agent
```

![image-20260624160807648](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedac83f7c6fa2813e43597416bd62edb02.png)

![image-20260624160910464](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined239d8ce805ab9fda2ab29e1bc426d137.png)

![image-20260624160921595](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined333e98f7de5d03c50d011b9e417319a2.png)

浏览器会弹窗触发 OAuth 认证流程，完成 myNordic 登录即可。

![image-20260624160959037](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined6553647f63bdf963b10851fb306dce31.png)

认证成功，CLI中会展示可用工具。Esc退回初始界面即可。

![image-20260624161048412](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedea0ee7100532c108f3b9e50e6a5237c2.png)

## 5.3 验证 MCP 是否生效

在 Cursor 的 AI Chat 中发起一个需要 Nordic 知识的问题，观察是否有 MCP 工具调用。例如：

> "nRF52840 的 GPIOTE 模块有多少个通道？"

如果你的 AI 回答中引用了官方文档链接，说明 MCP 已经生效。

![image-20260624161136736](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedc1881bc2d12b38a44a2215913671051e.png)

> Cursor CLI 底部的 HUD 显示可以用如下提示词来实现：
> ```
>  /statusline 帮我给 Cursor CLI 配一个简洁的底部 HUD / statusLine。
> 
> 显示 3 行信息：session + runtime、model + git branch + cwd、context 使用率 + token进度条 + remaining tokens。要求有基础配色，context 进度条按使用率变色：低于 65% 绿色，65%-85% 黄色，85% 以上红色。
> 
> 实现方式按当前系统选择，不要写死个人路径或机器相关信息
> ```

# 6. Skills 与提示技巧

在使用 AI 编程时，很多已知的事情最好提前告诉 AI。这样就避免 AI 花时间和 token 去探索。

比如：我们知道，要用命令行编译工程，需要先进入nrf connect命令行：

![image-20260624164825476](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined92c66f98cef67d6c5fd03d264ffa43d6.png)

AI需要直接通过终端进入，就需要套一层`nrfutil sdk-manager toolchain launch`，例如：

```powershell
nrfutil sdk-manager toolchain launch --ncs-version <version> -- west build -b <board> -p always
```

但是你也不会想 AI 每次干活时都重新探索一遍怎么设置环境。 因此可以设置skill。

我这里分享一个我自己在用的skill：[nrf-connect-skills-ZH_CN/SKILL.md at master · Jayant-Tang/nrf-connect-skills-ZH_CN](https://github.com/Jayant-Tang/nrf-connect-skills-ZH_CN/blob/master/SKILL.md)

> Skill里面用到了一些Jlink工具，记得确保Jlink路径（比如`C:\Program Files\SEGGER\JLink`）在你的`PATH`环境变量里。



# 7. 其他MCP Server

Nordic 目前提供两个 MCP Server：
- **Nordic MCP**（本文介绍）：知识库检索 + 开发工作流
- **nRF Cloud MCP**（`https://app.memfault.com/mcp`）：访问 nRF Cloud 项目中的设备数据、issue、trace 等

你可以同时将它们添加到 AI 助手中：

```bash
# Claude Code 同时添加两个 MCP
claude mcp add --transport http nordic-mcp https://aidev.nordicsemi.com/mcp
claude mcp add --transport http nrfcloud-mcp https://app.memfault.com/mcp
```

这样 AI 助手既可以查 NCS 文档，又可以拉取你的设备现场数据。例如：

> "我的项目 my-iot-prod 中最近有大量设备 crash，查一下 crash trace，结合 NCS 文档分析可能的原因"

AI 会先去 nRF Cloud MCP 拉取 crash trace 和 issue 列表，再去 Nordic MCP 搜索相关的 panic handler 和 watchdog 文档，综合给出分析结果。

# 8. 小结

Nordic MCP 本质上是一个**官方维护的、实时更新的 Nordic 知识库 API**。它的价值在于：

1. **准确性**：AI 生成的代码有官方文档支撑，不会凭空捏造 API
2. **时效性**：知识库随 NCS 版本更新，始终是最新信息
3. **降低 token 消耗**：精确搜索比让 AI 从训练记忆中"猜"更高效
4. **跨 IDE 兼容**：只要是支持 MCP 的客户端都可以用，包括 Claude Code、Cursor、VS Code Copilot、Windsurf 等

对于国内开发者，需要注意的是：

- OAuth 认证会重定向到 [mynordic.nordicsemi.com](https://mynordic.nordicsemi.com)，需要提前注册账号
- 首次添加 MCP 时，浏览器弹出的认证页面可能需要稳定的网络环境
- 如果使用代理，确保浏览器和终端共用同一代理设置（最好的方式是 Tun Mode，虚拟网卡）

> 目前 Nordic MCP 尚处于第一版，与 nRF Connect for VS Code 扩展的紧密集成还在规划中。后续版本预计会带来更深度的 IDE 集成体验。

---

**参考链接：**

- [Nordic MCP 官方文档](https://docs.nordicsemi.com/r/bundle/nordic-mcp/page/index.html)
- [Nordic AI-assisted Development 主页](https://www.nordicsemi.com/Products/Technologies/AI-assisted-development)
- [MCP 协议规范](https://modelcontextprotocol.io/specification/latest)
- [nRF Cloud MCP 文档](https://docs.nrfcloud.com/docs/platform/mcp-server)
