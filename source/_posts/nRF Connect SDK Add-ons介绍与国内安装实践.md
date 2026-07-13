---
title: nRF Connect SDK Add-ons介绍与国内安装实践
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2026-04-22 10:30:00
cover: null
tags:
- Nordic
- NCS
- Add-ons
categories: Nordic
typora-root-url: ./..
cnblogs:
  postId: '19906529'
  url: https://www.cnblogs.com/jayant97/articles/19906529
  lastPublishedAt: '2026-07-06T18:29:40+08:00'
  sourceHash: sha256:e00b1132a36440252f7a7cce770f4f098d0bea37f458f0bf20d21b527c4c7f22
  status: imported
  postType: Article
---

本文介绍什么是 nRF Connect SDK Add-ons，以及在国内网络环境下如何安装。

# 1. 为什么会有 Add-ons？

NCS（nRF Connect SDK）是 Nordic 的主 SDK，包含了 BLE、Thread、Zigbee、Wi-Fi、蜂窝、Matter 等各种协议栈和驱动。但随着支持的附加功能越来越多，统一打包进一个 NCS 版本发布的难度越来越高——每增加一个新功能，就要保证它和 NCS 里所有其他模块都不冲突，还要等一个正式发版窗口才能推出去，并且，某些附加功能（如 ANT+）也不是由Nordic主导开发的。

于是 Nordic 引入了 **Add-on** 机制：把一些特殊的功能单独做成独立发布的 SDK 扩展，**绑定自己兼容的 NCS 版本**，不用等 NCS 大版本更新就能迭代。

在 [Technical Documentation](https://docs.nordicsemi.com/) 官网，可以看到Add-ons的入口：

![image-20260422104000857](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined5b2eb49e09be0239b9f9591393f79d73.png)

目前已有的 Add-on 包括：

- **Edge AI Add-on**：手势识别、异常检测等 ML 推理框架与参考应用
- **Amazon Sidewalk Add-on**：Amazon 的低功耗广域 IoT 协议
- **Zigbee R23 Add-on**：Zigbee 3.0 R23 协议栈
- **Serial Modem Add-on**：蜂窝模组的串口 AT 命令固件框架

![image-20260422104117669](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedccd349953c690bccf13e523a15eeedf3.png)

> Add-on 的完整列表可以在 [nRF Connect SDK Add-on Index](https://nrfconnect.github.io/ncs-app-index/) 查到。

# 2. Add-on 技术上是什么？

Add-on 的本质是一套 west manifest。Add-on 并不是装一个插件这么简单——它本质上是一个独立的 Git 仓库，仓库里有自己的 `west.yml`，里面写死了它兼容的 NCS 版本和各个依赖模块的版本。

当你把 west 的 manifest 指向这个仓库后，`west update` 会把整个工作区里所有仓库的版本都切换到 Add-on 要求的状态。所以安装 Add-on 时"会连 NCS 一起拉"是正常的，不是多此一举。

正因为如此，建议**每个 Add-on 单独对应一套工作区**，不要在同一个目录里频繁来回切 manifest，否则仓库状态很容易混乱。

# 3. 标准安装方式

## 3.1 VS Code 图形界面

在 nRF Connect 侧边栏选择 **Create a new application**，点击 **Browse nRF Connect SDK Add-on Index**，选择目标 Add-on 和版本，工具会自动把 Add-on 仓库和对应 NCS 一起拉下来。

> 这种方式最简单，版本关系也不容易搞错，网络条件好的情况下首选这个。它会从GitHub拉取这个仓库，以及对应的NCS。

![image-20260422104302358](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined36b72290f67d6a393ebdcabf8aba30ba.png)

![image-20260422104315031](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined3730223c5403a0ccf86e0b1dbf8cdf54.png)

## 3.2 命令行

以 Edge AI Add-on 为例：

```bash
# Windows，先打开对应版本的工具链环境
nrfutil toolchain-manager launch --ncs-version v3.2.4 -- powershell

# 初始化工作区，-m 指定 Add-on 仓库，--mr 指定版本
west init -m https://github.com/nrfconnect/sdk-edge-ai --mr v2.0.0

# 拉取依赖
west update
```

不同 Add-on 的仓库地址和版本号不同，以各自的官方文档和 `west.yml` 为准。

> 注意，某些仓库在 GitHub 是私有仓库，需要向相关公司申请才能获得访问权限。
> ![image-20260422105616904](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedc0f20585ef0f177d3913fb6cde903757.png)

# 4. 国内网络下的增量安装方案

从零拉起一套 Add-on 工作区意味着要从 GitHub 拉取完整的 NCS 和所有依赖，国内网络下成功率不高。**如果你已经用国内镜像方式装好了一套标准版 NCS，可以让 west 在这个基础上只补齐 Add-on 的差异部分，成功率会高很多。**

以 Edge AI Add-on v2.0.0 为例。

首先，根据 [Nordic Edge AI的west配置](https://github.com/nrfconnect/sdk-edge-ai/blob/v2.0.0/west.yml)，我们得知2条重要信息：

1. 此 Add-on 需要NCS v3.3.0-preview2；
2. 此仓库在 west 工作区中的文件夹路径名为`edge-ai`

![image-20260422105156792](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedcb5b0bc26c0aa90fcfd799e7f6af805d.png)

目前和 v3.3.0-preview2 最接近的正式版是 v3.2.4。我们通过国内镜像安装v3.2.4，这部分可参考：[nRF Connect SDK(NCS) 安装与入门 - jayant97](https://jayant-tang.github.io/2022/12/779143a4bec8/)

假设你已有标准版NCS安装在 `D:/ncs/v3.2.4`。根据NCS根目录下`.west/config`文件下的配置，我们可以看到NCS原本的manifest是[nrf仓库](https://github.com/nrfconnect/sdk-nrf)：

```yaml
[manifest]
path = nrf
file = west.yml

[zephyr]
base = zephyr
```

我们只需要把 manifest 切换成`https://github.com/nrfconnect/sdk-edge-ai`，再更新west工作区，即可增量拉取：

```bash
## 打开工具链环境
# Windows
nrfutil toolchain-manager launch --ncs-version v3.2.4 -- powershell
# Linux
nrfutil toolchain-manager launch --ncs-version v3.2.4 --shell

# 克隆 Add-on 仓库到工作区里，并重命名为edge-ai
cd D:/ncs/v3.2.4
git clone -b v2.0.0 https://github.com/nrfconnect/sdk-edge-ai edge-ai

# 把 manifest 切换到 Add-on
west config manifest.path edge-ai

# 拉取差异（网络失败可以重复执行，west 会断点续传）
west update
```

完成后建议把这个工作区重命名，比如 `edge-ai-sdk`，和纯 NCS 目录区分开。

切回标准 NCS 只需要把 manifest 改回来：

```bash
west config manifest.path nrf
west update
```

> 验证当前 manifest 指向：
>
> ```bash
> west config manifest.path
> ```

## 常见问题

**west update 报 Git 文件不干净**

![image-20260409162727245](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined140feacef6b78a73f623f14704f91101.png)

Windows 的 NTFS 文件系统不区分大小写，部分仓库里有大小写不一致的文件名，git checkout 时会报冲突。在报错的仓库目录里单独执行：

```bash
git config core.ignorecase true
```

不建议全局设置，按需处理即可。

**west update 中途失败**

`west update` 要拉取几十个仓库，网络抖动导致中断很正常，直接重新执行即可，已拉取的仓库不会重复下载。

**安装完 Add-on 后，模块版本和原来不一样了**

manifest 已切换到 Add-on，`west update` 会把所有模块（例如zephyr, mcuboot）对齐到 Add-on 的依赖版本。这是预期行为。

# 5. 参考链接

- [nRF Connect SDK Add-on Index](https://nrfconnect.github.io/ncs-app-index/)
- [nRF Connect SDK(NCS) 安装与入门 - jayant97](https://jayant-tang.github.io/2022/12/779143a4bec8/)