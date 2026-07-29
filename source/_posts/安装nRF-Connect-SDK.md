---
title: nRF-Connect-SDK 安装与入门
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2022-12-04 22:22:30
cover: null
tags:
- Nordic
- NCS
- Toolchain
categories: Nordic
sticky: 1000
cnblogs:
  postId: '17794804'
  url: https://www.cnblogs.com/jayant97/articles/17794804.html
  lastPublishedAt: '2026-07-29T14:07:53+08:00'
  sourceHash: sha256:a85e989d6f14ecef2f2a232275bf7889111ae9426e8e3ba45ca1332b73c2e95d
  status: synced
  postType: Article
---

> 2026.7.28更新：
>
> - 推荐安装 NCS v3.4.0 LTS.
> - 重新整理安装流程，强化 nrfutil 纯命令行用法，适合 AI Agent 和服务器环境使用
>
> 2026.1.11更新：
>
> - 官方已经支持中国大陆服务器源下载NCS
>
> 2025.10.14 更新：
>
> - 增加了NCS v3.1.0 和  v3.1.1 在中文 Windows 系统上编码问题的解决方案
> - 增加了说明，nrfutil sdk-manager v1.8.0 已经解决了SDK在Windows系统上 git 状态错误的问题
>
> 2025.7.27 更新：
>
> - 增加了nRF Connect详细安装说明，和国内软件源
> - 增加了 nrfutil 详细安装说明，以及命令行自动补全
> - 新增了强制用国内服务器加速安装NCS的方法
>
> 2025.5.12 更新：
>
> - NCS v3.0.0 支持打包下载，无需科学的上网从 GitHub 拉取
> - 新增 workspace 插件清理内容，解决 VS Code 弹窗问题
> - 新增对 Windows 目录名长度限制的提醒

nRF Connect SDK，简称 NCS，是 Nordic 最新的 SDK 平台。该平台支持 Nordic 的四大产品线：
1.  **短距离 2.4G SoC 和功率放大器（PA）** ：Bluetooth LE, 802.15.4, 2.4G 私有协议（ESB）
2.  **中距离 Wi-Fi** : Wi-Fi 6 收发器和SoC
3.  **长距离蜂窝模组（ SiP ）**：CAT-M，CAT1-bis，CAT-NB，卫星通信（NTN）
4.  **电源管理芯片** ：多合一 PMIC。支持 Charger，电量计， BUCK / Boost，LDO / Load Switch，Ship Mode，GPIO，Watchdog，Hard Reset

以上述硬件为基础，提供多种物联网、嵌入式、机器学习、低功耗穿戴等领域的技术方案和应用示例。

NCS 基于 Zephyr 系统。Zephyr 系统是一个开源嵌入式实时操作系统项目，由 [Linux 基金会和众多厂商](https://zephyrproject.org/project-members/)维护。Zephyr 系统是一个完整的 BSP，除了基本的编译环境和 RTOS 之外 ，还有很多中间件、软件库、硬件驱动、工具脚本、测试框架等等。

> Zephyr 的强大特性
>
> 1. 全面的内核服务
>    - 多线程，支持协程和基于优先级的抢占。兼容 POSIX pthreads API。
>    - 多种动态内存分配工具，支持固定大小或可变大小的内存块
>    - 支持多种信号量同步机制（信号量、互斥锁等）；支持多种线程间通讯机制（消息队列、字节流等）
>    - CPU 电源管理和外设电源管理等低功耗机制
> 2. 多种调度策略可选
> 3. 高度可定制性、模块化开发
> 4. 支持许多架构（x86, ARM, RISC-V）
> 5. 堆栈、内核、驱动、线程间内存保护
> 6. 允许编译时静态定义资源（线程、内存池、队列等），提高性能
> 7. 提供具有一致性的设备驱动模型，并且支持 DeviceTree 规范
> 8. 集成常见外部设备的驱动，如显示屏、存储器、传感器、灯带、RTC等
> 9. 全功能网络协议栈（包括 LwM2M 和 BSD Sockets），OpenThread，BLE
> 10. 支持 TrustZone 安全技术，按照 PSA 架构提供安全基础设施
> 11. 集成常用软件包：LVGL, LZ4, iperf, Json Lib, TinyCBOR
> 12. 支持多种文件系统（ext2, LittleFS, FatFS...）和简单的键值对存储系统
> 13. 统一的配置项持久存储系统，全系统（应用层和中间件）的配置项可共享同一存储器分区
> 14. 远程资源管理（通过串口、USB、BLE、network 管理固件升级、版本回滚、文件系统资源等）
> 15. 强大的模块化日志框架，支持多种后端（串口、RTT、BLE、network、filesystem...）
> 16. 为开发调试提供便利的 Shell 功能
> 17. 跨平台开发（Windows / Linux / MacOS）
> 18. 支持 QEMU 模拟仿真

Nordic 的 NCS 在 Zephyr 的基础上提供了更多的脚本工具、协议栈、驱动、功能库等等。

更多信息可参考：

- [NCS官网 - 安装教程](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/installation/install_ncs.html)

# 1. 简介

必装选项：

| 序号 | 软件                                                         | 分类           | 用途                                                         |
| ---- | ------------------------------------------------------------ | -------------- | ------------------------------------------------------------ |
| 1    | [J-Link 驱动](https://www.segger.com/downloads/jlink)        | 驱动           | JLink驱动需要单独安装。**安装时必须勾选 Legacy USB Driver。** |
| 2    | [nRF Util](https://www.nordicsemi.com/Products/Development-tools/nRF-Util) | CLI 工具       | 统一 CLI 工具，包含子命令：sdk管理、烧录、DFU 等等。类似软件包管理器，支持更新。 |
| 3    | NCS Toolchain                                                | 编译工具链     | 独立的工具链文件夹，含Git、CMake、Python、Ninja、GCC、west  等工具，与电脑上已经安装的工具环境相互独立。可以同时存在多个版本的 Toolchain。 |
| 4    | nRF Connect SDK                                              | SDK 源码包     | SDK本体，含 Zephyr 内核、驱动、模块、协议栈等源码。可以同时存在多个版本的 SDK。 |
| 5    | [nrf-udev](https://github.com/NordicSemiconductor/nrf-udev)  | Linux 配置文件 | 仅 Linux 系统需要。配置USB设备权限，可识别 Nordic USB 设备。 |

对于**纯命令行开发、CI/CD服务器环境、AI 辅助编程**来说，以上软件已经足够实现**编译、烧录和简单的调试**。

此外，Nordic 还提供其他开发工具：

| 序号 |                             软件                             | 分类      | 用途                                                         |
| :--:  | :----------------------------------------------------------: | --------- | ------------------------------------------------------------ |
|  6    |     [VS Code](https://code.visualstudio.com/) + [nRF Connect 插件](https://marketplace.visualstudio.com/items?itemName=nordic-semiconductor.nrf-connect-extension-pack)     | IDE    | 提供编译、烧录、调试的可视化界面，提供设备树可视化、SDK管理、工具链环境等。支持 VS Code Remote 在远程服务器或虚拟机/WSL上开发。 |
|  7   | [nRF Connect for Desktop](https://www.nordicsemi.com/Products/Development-tools/nrf-connect-for-desktop) | 桌面工具  | Nordic 桌面工具与上位机集合，包含：开发板配置、串口助手、固件烧录、功耗测量、蜂窝抓包、射频测试等 |
| 8 | [nRF Connect for Mobile](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-mobile) | 手机 APP | iOS / Google Play 直接商店下载。Android 系统也可以从 [GitHub Release APK](https://github.com/nordicsemi/Android-nRF-Connect/releases) 安装。 |

# 2. 安装开发工具

## J-Link 驱动

J-Link 驱动的版本参考 [NCS依赖(v3.4.0)](https://nrfconnectdocs.nordicsemi.com/ncs/3.4.0/nrf/installation/recommended_versions.html) 文档。打开文档后，先把文档版本对齐为你要安装的最新的正式版 NCS 版本，比如这里是 NCS v3.4.0：

![image-20260727114142910](/imgs/安装nRF-Connect-SDK.assets/image-20260727114142910.png)

然后往下翻，找到 J-Link 需要的版本：

![image-20260727113737434](/imgs/安装nRF-Connect-SDK.assets/image-20260727113737434.png)

一般来说比这个版本高也是可以的。在 [SEGGER - J-Link官网](https://www.segger.com/downloads/jlink) 下载 J-LINK 驱动：

![image-20260727114246957](/imgs/安装nRF-Connect-SDK.assets/image-20260727114246957.png)

Linux系统直接安装：

```bash
# For Ubuntu/Debian
sudo dpkg -i ./JLink_Linux_V924a_x86_64.deb
```

**Windows系统安装 J-Link 驱动时，一定要带上JLink USB驱动**：

```powershell
# For windows
JLink_Windows_V924a_x86_64.exe -InstUSBDriver=1
```

**或者在安装时勾选 Legacy USB Driver**：

![image-20250727155420764](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/57c7c7a3c1b24a4013e61a438ba92626.png)

安装完毕后，Windows 系统一定要把 J-Link 可执行文件所在目录添加到 PATH 环境变量：

![image-20260727125717008](/imgs/安装nRF-Connect-SDK.assets/image-20260727125717008.png)

![image-20260727115228690](/imgs/安装nRF-Connect-SDK.assets/image-20260727115228690.png)

> 注意，根据前面安装时选择 "Update existing installation" 还是 "Install a new instance"，JLink.exe 所在的目录是不一样的。设置 PATH 环境变量时要注意设置正确的位置。

验证 PATH 环境变量设置正确。能找到路径说明已经成功设置：

```powershell
# Powershell
C:\Users\> Get-Command jlink

CommandType     Name                                Version    Source
-----------     ----                                -------    ------
Application     JLink.exe                           0.0.0.0    C:\Program Files\SEGGER\JLink\JLink.exe
```

```cmd
# Windows CMD
C:\Users\> where jlink

C:\Program Files\SEGGER\JLink\JLink.exe
```

```shell
# Linux shell
$ which JLinkExe
/usr/bin/JLinkExe
```



## nrfutil - CLI 工具

nrfutil 是一个命令行工具集。它可以联网安装、升级许多功能。如程序烧录、SDK管理、工具链环境、MCU Mgr 等等。此外，它也包含许多 Nordic 上位机工具的底层控制命令，如 BLE Sniffer、Cellular trace、电源管理芯片上位机等。

纯 CLI 工具可以方便服务器 CI/CD 环境编译、本地脚本开发、量产测试工具开发。在 AI 时代，也是扩展 AI Agent 能力的重要接口。

依赖项：

1. J-link 驱动
2. Windows 系统： C++ 运行库 [Microsoft Visual C++ Redistributable](https://docs.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170#visual-studio-2015-2017-2019-and-2022)

![image-20260727132938699](/imgs/安装nRF-Connect-SDK.assets/image-20260727132938699.png)

在官网下载可执行文件：[nRF Util](https://www.nordicsemi.com/Products/Development-tools/nRF-Util)。

![image-20260727133146470](/imgs/安装nRF-Connect-SDK.assets/image-20260727133146470.png)

然后把 nrfutil 所在目录添加到 PATH 环境变量：

![image-20250727160809557](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/374227a1ab74d3ff010f5f8cbd22289f.png)

![image-20250727160716550](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/66eba8f83e53eed553bda73f46e9858c.png)

常用命令：

```powershell
# 自我更新
nrfutil self-upgrade

# 联网查找子命令
nrfutil search

# 安装常用软件
nrfutil install device sdk-manager completion

# 更新所有子命令
nrfutil upgrade
```

>  如果你的环境不能联网，可以先在有网络的电脑安装子命令，然后用U盘导出到不能联网的电脑，见：[nrfutil 离线安装方法](https://jayant-tang.github.io/2023/11/b3ef0c412298/)。

子命令通常都支持 `--help` 参数，可以帮助你学习这个命令的用法。

> 其中，`completion` 子命令是用来帮助你安装**命令自动补全**脚本。这样以后敲 nrfutil 命令，按 Tab 键就能补全子命令，非常方便。
>
> 以 power shell 为例：
>
> ```powershell
> PS C:\Users\Jayant> nrfutil completion install powershell
> 
> Add the following to your $PROFILE file:
> 
> # From nrfutil completion install
> # WARNING: nrfutil tab-completion may become slow because of Windows Defender
> if ( Test-Path -Path ${env:USERPROFILE}\.nrfutil\share\nrfutil-completion\scripts\powershell\setup.ps1 ) {
>     . ${env:USERPROFILE}\.nrfutil\share\nrfutil-completion\scripts\powershell\setup.ps1
> }
> ```
>
> 对于 Linux 系统，执行 `nrfutil completion install bash` 或者 `nrfutil completion install zsh` ，把输出的脚本配置复制到对应的`~/.bashrc`或者`~/.zshrc`中即可。
>
> 命令结果提示我们，把命令行输出的内容粘贴到`$PROFILE`文件中，也就是`~\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`。
>
> 安装了 VS Code 的情况下，可以这样打开此文件：
>
> ```powershell
> code $PROFILE
> ```
>
> 另外如果你是首次设置 Windows Powershell 脚本，需要修改注册表使其允许执行脚本：
>
> ```powershell
> #在终端中执行
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```
>
> 在那之后，重新打开终端。随意输入nrfutil的命令，只输入一半按TAB键，就可以看到自动补全候选项了：
>
> ![image-20250727162035911](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/cf0c001fc9315b8e08579d979b4023dc.png)

## nRF Connect For Desktop

访问下载页面：https://www.nordicsemi.com/Products/Development-tools/nrf-connect-for-desktop

![image-20221122214235111](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221122214235111-1731044874926-19.webp)



下载并安装最新版本，进入设置，打开中国大陆服务器软件源：

![image-20250727155823079](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/ce1553838de4b8562ca01f8e9dfda59a.png)

然后安装自己需要的软件即可，可以先安装这三个最常用的：

![image-20250727155935022](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/125b92f2904349a6b2e02b0faee82ede.png)

> 如果你的电脑不能联网，可以先在可以联网的电脑上安装nRF Connect for Desktop。然后导出离线文件，再导入到不能联网的电脑上。见：
>
> [nRF Connect for Desktop离线安装方法](https://jayant-tang.github.io/2023/11/20cb577e596d/)

## VS Code + nRF Connect 插件

从官网安装：[Visual Studio Code](https://code.visualstudio.com/)

VS Code的插件可以在VS Code插件市场搜索 **nRF Connect for VS Code Extension pack** 来一次性安装所有需要的插件。

![image-20260727135628971](/imgs/安装nRF-Connect-SDK.assets/image-20260727135628971.png)

如果你需要 CMake 语法高亮，可以安装 `CMake - twxs`插件：

![image-20260727142008865](/imgs/安装nRF-Connect-SDK.assets/image-20260727142008865.png)

注意，**不要安装** `CMake Tools - Microsoft`，这个会一直弹窗让你选择 CMakeLists.txt 文件和编译器，在 Zephyr 中都是不需要的。如果你电脑上其他项目需要这个插件，可以单独在 NCS 的 workspace 中禁用这个插件，见后续章节。

如果你还需要远程开发，比如 SDK 安装在远程服务器或者虚拟机中的情况，可以在本机安装 Remote 插件：

![image-20260727142141571](/imgs/安装nRF-Connect-SDK.assets/image-20260727142141571.png)

> 如果你的电脑不能联网，需要离线安装插件。参考以下内容：
>
> <details>
>     <summary>[点击展开]</summary>
>
>
> 先在有网络的电脑上下载VSIX离线插件文件：
> ![image-20250727162402886](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/a51c1f6d2f3fd4c6fa027cb35fb90145.png)
>
> 注意这个插件包只是个封装。封装里的每一个插件都要单独下载VSIX，并选择平台：
>
> ![image-20250727162619019](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/461ecd55f552d8599ac52893b91c0894.png)
>
> 然后，拷贝到不能联网的电脑上导入即可：
>
> ![image-20250727162713479](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/a323fc91f942a982240fb8f3e5c856c7.png)
>
> </details>



> 有时 VS Code 会弹窗推荐一些插件，如 CMake，这些都是不需要的。

## Linux USB 规则

对于 Linux 环境，需要安装：

```bash
# 安装 USB 库
sudo apt install libusb-1.0-0

# 先从 https://github.com/NordicSemiconductor/nrf-udev/releases 下载deb包
# 再安装
sudo dpkg -i nrf-udev_1.0.1-all.deb

```

## 其他工具

以下工具在 toolchain 中已经打包了。但是在本机环境中直接安装，使用起来会更加方便，后续可以按需考虑安装。

- [Git](https://git-scm.com/) - 源码版本管理
- [west](https://docs.zephyrproject.org/latest/develop/west/index.html) - Zephyr 系统官方的超级工具（Meta-tool）。可以管理多仓库工作区（git）、支持编译、烧录和调试。

# 3. 安装编译工具链和SDK

Zephyr 官方教程是把各种工具（python, cmake, ninja, gcc, git 等）直接安装到系统环境，再分别安装Zephyr工具链包（主要是编译器）和 SDK 源码包，设置环境变量。一台电脑只安装一个环境。

NCS 的**工具链**是上述工具 + Zephyr 工具链包的合集。因此可以实现一台电脑上安装多个版本的工具链和 SDK，并且互不影响。

## 方式一：从压缩包自动安装

Toolchain 和 SDK 是独立的文件夹。Toolchain 包含 python, cmake, ninja, gcc 等工具，与电脑上本身的工具环境不冲突；SDK 包含源码、脚本、库等。

Nordic 在对象存储服务器上提供了 Toolchain 和 SDK 的压缩包，方便用户下载加速。

可以通过 `nrfutil sdk-manager` 或者 nRF Connect for VS Code 插件直接下载。

默认安装路径为：

- Windows：`C:\ncs`
- Linux: `~/ncs`
- macOS: `/opt/nordic/ncs/` 

目录结构：

```text
<install-dir>
├── downloads/
├── tmp/
├── toolchains/
│   ├── b2ecd2435d/
│   ├── fbf7391cab/
│   └── toolchains.json
├── v3.1.1/
└── v3.4.0/
```

电脑上可以同时安装多个版本的 toolchain 和 SDK。`toolchains/`目录下是工具链，`vX.Y.Z/`格式的目录下是 SDK 源码。

`tmp/`下是解压过程中的临时文件，会自动清理干净。

`downloads/`下是原始工具链和SDK压缩包，不会自动清理。其中，SDK 的压缩包可以拷贝到其他电脑 NCS安装目录的 downloads 目录下，这样其他电脑安装时就不用再下载了；而 toolchain 的压缩包只能分享给相同架构的电脑中（Windows, Linux ARM64, Linux AARCH64, macOS 互不相同）。

### 修改默认安装路径

如果你要修改默认安装路径，则 nrfutil 和 VS Code 插件**都要修改**。

> macOS 不能修改默认安装路径

nrfutil：

```powershell
 nrfutil sdk-manager config install-dir set "D:\ncs"
```

VS Code：

![image-20260727153312403](/imgs/安装nRF-Connect-SDK.assets/image-20260727153312403.png)

> Windows 注意事项：
>
> 1. 建议全英文路径，不能有空格
> 2. Windows 有路径长度限制，目录层级不能太深，建议就是 `D:\ncs`, `E:\ncs` 等等
> 3. 后续开发工程存放的磁盘必须和 NCS 在同一个磁盘

### 下载并安装

可以用 nrfutil 安装，也可以用 VS Code 安装，**二选一**。

#### 用 nrfutil 安装

```powershell
# 查看可安装的版本
nrfutil sdk-manager search --region cn

SDK Type  SDK Version  SDK Status  Toolchain Version  Toolchain Status
nrf       v3.4.0       Available   v3.4.0             Available
nrf       v3.3.2       Available   v3.3.2             Available
nrf       v3.3.1       Available   v3.3.1             Available
nrf       v3.3.0       Available   v3.3.0             Available
...

# 同时安装 toolchain 和 SDK
nrfutil sdk-manager install --region cn v3.4.0

```

`--region cn` ：**指定中国大陆服务器**。

```powershell
# 安装完毕后检查
nrfutil sdk-manager list

SDK Type  SDK Version  SDK Status  Toolchain Status
nrf       v3.4.0       Installed   Installed
```



#### 用 VS Code 安装

首先设置中国大陆服务器源：

![image-20260727154752794](/imgs/安装nRF-Connect-SDK.assets/image-20260727154752794.png)

首次安装界面：

![image-20260727154826200](/imgs/安装nRF-Connect-SDK.assets/image-20260727154826200.png)

非首次安装界面：

![image-20260727162326688](/imgs/安装nRF-Connect-SDK.assets/image-20260727162326688.png)

选择 nRF Connect SDK：

![image-20260727154944748](/imgs/安装nRF-Connect-SDK.assets/image-20260727154944748.png)

> 另外一个是裸机 SDK，仅支持 nRF54L 系列，仅支持 BLE 开发。只适合 nRF5 SDK 历史包袱较重的公司或开发者临时过渡使用。

选择要安装的版本：

![image-20260727155236752](/imgs/安装nRF-Connect-SDK.assets/image-20260727155236752.png)

> 【注意】
>
> 1. 右上角 "Pre-packaged" 标记代表从 Nordic 服务器下载，速度较快。而 "GitHub" 标记表示从 GitHub拉取，速度很慢。
>
>    ![image-20260727160712185](/imgs/安装nRF-Connect-SDK.assets/image-20260727160712185.png)
>
> 2. LTS 是长期支持（Long-Term Support）。
>    ![branch sample](/imgs/安装nRF-Connect-SDK.assets/2313.branch.png)
>
>    Nordic 承诺从 v3.4.0 开始提供 5 年保证的长期支持版本。在支持期内：
>
>    - 持续修复安全漏洞和关键 Bug。
>    - LTS 将只会从 Zephyr 上游代码库中拉取关键 patch，包括安全修复和新的 boards 支持。跳过会影响应用层的patch。
>    - 用户在 LTS 内升级小版本时（v3.4.1, v3.4.2），无需修改应用层代码和配置方式（除非安全修复必须包含破坏性修改）。
>
>    LTS 方便客户开发需要长期维护的产品，或需要应对欧盟网络弹性法案（CRA）等合规要求的场景。

选择安装路径：

由于前面已经设置了`D:\ncs`安装路径，这里自动识别了正确位置，直接回车安装即可。

![image-20260727160953797](/imgs/安装nRF-Connect-SDK.assets/image-20260727160953797.png)

查看安装进度：

在 Output 标签页下，选择 nRF Connect 插件日志，即可查看安装进度和日志：

![image-20260727161352361](/imgs/安装nRF-Connect-SDK.assets/image-20260727161352361.png)

等待安装完毕。

## 方式二：手动拉取或者更新SDK

虽然 Nordic 提供了压缩包下载，但还是有必要了解 Zephyr 标准的源码管理方式。

这种方式是从 GitHub 拉取，无法受到国内镜像源加速，但可以精确切换到某个特定 commit 。确保你能稳定访问GitHub并拉取仓库再安装。

> ![image-20251019172612233](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedcc562f37c016c0fa4886687e93e7727b.png)
>
> ![image-20251019173045929](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined7b2c76779ac234225eaa29ee3e992833.png)
>
> NCS 项目托管在 GitHub，由多个仓库组成：https://github.com/nrfconnect。其中既有 Nordic 自己的代码仓库，也有开源仓库的 Fork 副本。Nordic 会持续开发优化，并贡献给开源社区，同时也从开源项目获取新功能。
>
> 其中，主仓库是 sdk-nrf。**主仓库的版本就是 NCS 版本**。每个主仓库中会通过 `west.yml` 文件记录其他子仓库的 GitHub 地址和版本，这样就可以用`west`命令一次性拉取全部仓库。
>
> 此外，一些特殊的功能仓库（如 Edge AI，Apple Find-My，Garmin ANT+ 等）有自己的版本发布节奏，不会和 sdk-nrf 保持一致。这种情况下，这些仓库作为主仓库，然后 west 命令可以进一步拉取其指定版本的 sdk-nrf, sdk-zephyr 等其他仓库，这种情况下安装的就不是标准版 NCS 了，见[《nRF Connect SDK Add-ons介绍与国内安装实践》](https://jayant-tang.github.io/2026/04/40898fb9360c/)。

### 安装工具链

工具链仍然要使用 Nordic 提供的压缩包。这里只单独安装工具链，不安装sdk。

如果想要修改安装路径，记得先按照**方式一**中的步骤进行修改。

使用 nrfutil 的方式：

```powershell
nrfutil sdk-manager toolchain install --ncs-version v3.4.0
```

使用 VS Code 的方式：

![image-20260727170013980](/imgs/安装nRF-Connect-SDK.assets/image-20260727170013980.png)

### 打开工具链环境

#### nrfutil 打开工具链环境

```powershell
#  Windows
nrfutil sdk-manager toolchain launch --ncs-version v3.4.0 --terminal
```

```shell
# Linux/macOS
nrfutil sdk-manager toolchain launch --ncs-version v3.4.0 --shell
```

**会弹出一个新的终端窗口，包含 toolchain 环境变量。**

#### VS Code 打开工具链环境

![image-20260727170653579](/imgs/安装nRF-Connect-SDK.assets/image-20260727170653579.png)

默认情况下打开 toolchain 环境时，要同时指定 SDK 版本和 toolchain 版本。但是这里我们要安装新的 SDK，直接跳过 SDK 选择：

![image-20260727170923857](/imgs/安装nRF-Connect-SDK.assets/image-20260727170923857.png)

然后选择刚刚安装的 Toolchain 版本：

![image-20260727171000046](/imgs/安装nRF-Connect-SDK.assets/image-20260727171000046.png)

打开的工具链环境：

![image-20260727171100460](/imgs/安装nRF-Connect-SDK.assets/image-20260727171100460.png)

### 验证工具链环境

```powershell
# Windows Powershell
Get-Command git | Format-List *    


HelpUri            : 
FileVersionInfo    : File:             D:\ncs\toolchains\dcbdc366a1\mingw64\bin\git.exe
```

```cmd
# Windows CMD
where git 

D:\ncs\toolchains\dcbdc366a1\mingw64\bin\git.exe
D:\ncs\toolchains\dcbdc366a1\bin\git.exe
C:\Program Files\Git\cmd\git.exe
```

```shell
# Linux Shell
which git
/home/jayant/ncs/toolchains/911f4c5c26/usr/local/bin/git
```

可以发现 git 软件已经在使用 toolchain 文件夹内的实例，而不是系统默认软件安装路径里的。

### 从 GitHub 安装 NCS

新安装SDK：

```powershell
# 进入到 toolchain 的父目录，默认C:\ncs，或者${HOME}/ncs/
cd D:\ncs

# 创建并进入SDK文件夹
mkdir v3.4.0
cd v3.4.0

# 初始化仓库（从github拉取对应Tag的主仓库）
west init -m https://github.com/nrfconnect/sdk-nrf --mr v3.4.0
```

> - 这一步等价于`git clone`，并创建`.west`配置文件夹
> - 在执行`west`命令时，`west`会在当前目录和父目录中递归向上寻找`.west`文件夹，并使用其中的配置。因此千万不要乱搞在硬盘根目录创建什么`.west`文件夹，会导致整个盘都出问题，无法正常使用 west。
> - 这一步如果下载失败想重新下载，**需要把创建的 v3.4.0 文件夹下的所有内容删除干净**，尤其是`.west`隐藏文件夹。然后再次执行前面的`west init ...`即可

```powershell
# 拉取其他子仓库，直接在当前目录下执行
west update
```

> 由于国内网络DNS污染的原因，这一步也经常失败，但是没关系，每次`west update`都能下载一点点，如果失败了，就重复`west update`就行了。不需要像`west init`失败一样删除干净重新下载。
>
> 可以用个脚本循环执行，直到west update无报错。

```powershell
# 安装成功后注册 CMake
west zephyr-export
```

> 这个操作的目的是把 SDK 的安装位置注册到操作系统：
>
> - **Linux/macOS**：写入 `~/.cmake/packages/Zephyr`
> - **Windows**：写入注册表 `HKEY_CURRENT_USER\Software\Kitware\CMake\Packages\Zephyr`
>
> 这样，后续开发独立工程（Freestanding Application，源码在 SDK 外部）时，工程 CMakeLists.txt 里的 `find_package(Zephyr)`才能找到 SDK 位置。
>
> 电脑上安装多个 SDK 时，这些注册是独立的条目，不会互相冲突。

### 切换SDK版本（更新或回退）

> 即使是通过压缩包自动安装的方式，也可以用此方法 checkout 到指定版本

按照以下步骤操作：

1. 进入 NCS 下的 nrf 仓库
   ```powershell
   cd nrf
   ```

2. 确保 SDK 中的 git 仓库状态均为 clean
   ```powershell
   # 此命令可查看当前git仓库的状态
   git status
   ```

   但是 NCS 中的仓库很多。也可以用 VS Code 打开整个 NCS，用 git 界面图形化查看是否每个仓库均为 clean。

   > 一般来说，**开发者不要随便改动 SDK 中的代码和配置**，否则在切换版本的时候可能出问题。

3. 检查 manifest 有无新版本
   NCS 中，nrf为主仓库，nrf的版本即为整个SDK的版本

   ```powershell
   # 查看nrf仓库下有多少版本
   cd nrf
   git fetch
   git tag  # 按键盘上下键翻阅，按q退出
   ```

4. 切换到自己想要的版本
   ```powershell
   # 检出想要的主仓库nrf版本
   git checkout v3.4.0
   
   # 更新nrf之外的整个NCS仓库
   west update
   ```

>  当使用 nRF Connect SDK Add-ons 时，也是类似的步骤。只不过主仓库不再是 `sdk-nrf`，而是对应的 Add-ons 仓库。



## 中文 Windows 环境修复编码问题修复

> 仅**中文 Windows 系统** 用户需考虑此问题，英文 Windows 系统或 Linux/macOS 无需考虑

在较老的 NCS 版本中（低于 v3.2.x），部分 Python 脚本在读取文件的时候会用操作系统默认语言读取，导致 python 用 gbk 来读取 utf-8 的配置文件，进而导致编译失败。需要修改SDK脚本使其强制使用 utf-8。

<details>
    <summary>[点击展开]</summary>


### NCS v3.1.0/v3.1.1修复

#### 问题：pm_static.yml 无法写中文注释

`v3.1.1\nrf\scripts\partition_manager.py` 需修改三处

① 第683行：

```python
with open(ymlpath, 'r') as f:
```

改为:

```python
with open(ymlpath, 'r', encoding='utf-8') as f:
```



② 第911行：

```python
parser.add_argument('--static-config', required=False, type=argparse.FileType(mode='r'),
```

改为

```python
parser.add_argument('--static-config', required=False, type=str,
```



③ 第985行：

```python
        static_config = yaml.safe_load(args.static_config)
```

改为

```python
    with open(args.static_config, 'r', encoding='utf-8') as f:
        static_config = yaml.safe_load(f)
```

#### 问题：部分 Matter 例程无法编译

需修改2处

① 在 `v3.1.1\modules\lib\matter\scripts\codegen_paths.py` 第 80 行：

```python
 for expanded in expand_path_for_idl(CreateParser().parse(open(idl, "rt").read()), p):
```

改为：

```python
 for expanded in expand_path_for_idl(CreateParser().parse(open(idl, "rt", encoding="utf-8").read()), p):
```



② 在`v3.1.1\modules\lib\matter\scripts\codegen.py` 第 119 行：

```python
 idl_tree = CreateParser().parse(open(idl_path, "rt").read(), file_name=idl_path)
```

改为

```python
 idl_tree = CreateParser().parse(open(idl_path, "rt", encoding="utf-8").read(), file_name=idl_path)
```

> v3.1.x报错示例：
>
> ```powershell
> -- Configuring done
> -- Generating done
> -- Build files have been written to: D:/Project/peripheral_uart_dfu_1/build/peripheral_uart_dfu_1
> -- Found partition manager static configuration : D:/Project/peripheral_uart_dfu_1/pm_static.yml
> Traceback (most recent call last):
> File "D:\ncs\v3.1.1\nrf\scripts\partition_manager.py", line 1054, in <module>
>  main()
> File "D:\ncs\v3.1.1\nrf\scripts\partition_manager.py", line 1024, in main
>  static_config = load_static_configuration(args, pm_config) if args.static_config else dict()
>                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
> File "D:\ncs\v3.1.1\nrf\scripts\partition_manager.py", line 985, in load_static_configuration
>  static_config = yaml.safe_load(args.static_config)
>                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
> File "D:\ncs\toolchains\c1a76fddb2\opt\bin\Lib\site-packages\yaml\__init__.py", line 125, in safe_load
>  return load(stream, SafeLoader)
>         ^^^^^^^^^^^^^^^^^^^^^^^^
> File "D:\ncs\toolchains\c1a76fddb2\opt\bin\Lib\site-packages\yaml\__init__.py", line 79, in load
>  loader = Loader(stream)
>           ^^^^^^^^^^^^^^
> File "D:\ncs\toolchains\c1a76fddb2\opt\bin\Lib\site-packages\yaml\loader.py", line 34, in __init__
>  Reader.__init__(self, stream)
> File "D:\ncs\toolchains\c1a76fddb2\opt\bin\Lib\site-packages\yaml\reader.py", line 85, in __init__
>  self.determine_encoding()
> File "D:\ncs\toolchains\c1a76fddb2\opt\bin\Lib\site-packages\yaml\reader.py", line 124, in determine_encoding
>  self.update_raw()
> File "D:\ncs\toolchains\c1a76fddb2\opt\bin\Lib\site-packages\yaml\reader.py", line 178, in update_raw
>  data = self.stream.read(size)
>         ^^^^^^^^^^^^^^^^^^^^^^
> UnicodeDecodeError: 'gbk' codec can't decode byte 0x80 in position 8: illegal multibyte sequence
> CMake Error at D:/ncs/v3.1.1/nrf/cmake/sysbuild/partition_manager.cmake:179 (message):
> Partition Manager failed, aborting.  Command:
> D:/ncs/toolchains/c1a76fddb2/opt/bin/python.exe;D:/ncs/v3.1.1/nrf/scripts/partition_manager.py;--input-files;D:/Project/peripheral_uart_dfu_1/build/peripheral_uart_dfu_1/modules/nrf/subsys/partition
> _manager/pm.yml.settings;D:/Project/peripheral_uart_dfu_1/build/peripheral_uart_dfu_1/modules/nrf/subsys/partition_manager/pm.yml.bootconf;D:/Project/peripheral_uart_dfu_1/build/mcuboot/zephyr/include
> /generated/pm.yml;D:/Project/peripheral_uart_dfu_1/build/mcuboot/modules/nrf/subsys/partition_manager//generated/pm.yml;D:/Project/peripheral_uart_dfu_1/build/mcuboot/modules/nrf/subsys/partition_manager/pm.yml.bootconf;D:/Project/peripheral_uart_dfu_1/build/peripheral_uart_dfu_1/zephyr/include/genera
> ted/pm.yml;--regions;sram_primary;otp;bootconf;flash_primary;--output-partitions;D:/Project/peripheral_uart_dfu_1/build/partitions.yml;--output-regions;D:/Project/peripheral_uart_dfu_1/build/regions.y
> ml;--static-config;D:/Project/peripheral_uart_dfu_1/pm_static.yml;--sram_primary-size;0x2f000;--sram_primary-base-address;0x20000000;--sram_primary-placement-strategy;complex;--sram_primary-dynamic-pa
> rtition;sram_primary;--otp-size;1276;--otp-base-address;0xffd500;--otp-placement-strategy;start_to_end;--bootconf-size;4;--bootconf-base-address;0xffd080;--bootconf-placement-strategy;start_to_end;--f
> lash_primary-size;0x165000;--flash_primary-base-address;0x0;--flash_primary-placement-strategy;complex;--flash_primary-device;rram_controller;--flash_primary-default-driver-kconfig;CONFIG_SOC_FLASH_NR
> F_RRAM
> Call Stack (most recent call first):
> D:/ncs/v3.1.1/nrf/cmake/sysbuild/partition_manager.cmake:636 (partition_manager)
> D:/ncs/v3.1.1/nrf/sysbuild/CMakeLists.txt:825 (include)
> cmake/modules/sysbuild_extensions.cmake:598 (nrf_POST_CMAKE)
> cmake/modules/sysbuild_extensions.cmake:598 (cmake_language)
> cmake/modules/sysbuild_images.cmake:46 (sysbuild_module_call)
> cmake/modules/sysbuild_default.cmake:21 (include)
> D:/ncs/v3.1.1/zephyr/share/zephyr-package/cmake/ZephyrConfig.cmake:75 (include)
> D:/ncs/v3.1.1/zephyr/share/zephyr-package/cmake/ZephyrConfig.cmake:92 (include_boilerplate)
> D:/ncs/v3.1.1/zephyr/share/sysbuild-package/cmake/SysbuildConfig.cmake:8 (include)
> template/CMakeLists.txt:10 (find_package)
> 
> 
> -- Configuring incomplete, errors occurred!
> See also "D:/Project/peripheral_uart_dfu_1/build/CMakeFiles/CMakeOutput.log".
> ?[91mFATAL ERROR: command exited with status 1: 'D:\ncs\toolchains\c1a76fddb2\opt\bin\cmake.EXE' -DWEST_PYTHON=D:/ncs/toolchains/c1a76fddb2/opt/bin/python.exe '-Bd:\Project\peripheral_uart_dfu_1\build
> ' -GNinja -DBOARD=nrf54l15dk/nrf54l15/cpuapp '-SD:\ncs\v3.1.1\zephyr\share\sysbuild' '-DAPP_DIR:PATH=d:\Project\peripheral_uart_dfu_1'
> ```

### NCS v2.9.0/v2.9.1/v2.9.2修复

需要修改`v2.9.0\zephyr\scripts\list_boards.py`。否则无法编译。

```python
with board_yml.open('r') as f:
```


改为

```python
with board_yml.open('r', encoding='utf-8') as f:
```

> v2.9.x 报错示例：
>
> ```powershell
> CMake Error at C:/ncs/v2.9.0/zephyr/cmake/modules/boards.cmake:196 (message):
> Error finding board: nrf52840dk
> 
> Error message: Traceback (most recent call last):
> 
> File "C:\ncs\v2.9.0\zephyr\scripts\list_boards.py", line 469, in <module>
> dump_v2_boards(args)
> File "C:\ncs\v2.9.0\zephyr\scripts\list_boards.py", line 416, in dump_v2_boards
> boards = find_v2_boards(args)
>          ^^^^^^^^^^^^^^^^^^^^
> File "C:\ncs\v2.9.0\zephyr\scripts\list_boards.py", line 341, in find_v2_boards
> b, e = load_v2_boards(args.board, board_yml, systems)
>        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
> File "C:\ncs\v2.9.0\zephyr\scripts\list_boards.py", line 230, in load_v2_boards
> b = yaml.load(f.read(), Loader=SafeLoader)
>               ^^^^^^^^
> 
> UnicodeDecodeError: 'gbk' codec can't decode byte 0xa2 in position 46:
> illegal multibyte sequence
> 
> Call Stack (most recent call first):
> cmake/modules/sysbuild_default.cmake:15 (include)
> C:/ncs/v2.9.0/zephyr/share/zephyr-package/cmake/ZephyrConfig.cmake:75 (include)
> C:/ncs/v2.9.0/zephyr/share/zephyr-package/cmake/ZephyrConfig.cmake:92 (include_boilerplate)
> C:/ncs/v2.9.0/zephyr/share/sysbuild-packag
> ```

</details>

## Windows 环境错误 git 状态清理

> 【注意】2025.10.14开始，nrfutil sdk-manager v1.8.0 已经修复了此问题。如果你是用最新的 nrfutil 安装的 NCS，应该不会遇到此问题。
>
> 解决方案是 nrfutil 会在 SDK 解压安装时，自动把所有 .git 记录修改，直接增加了`core.filemode = false`

<details>
    <summary>[点击展开]</summary>
2025.10.14 之前，nrfutil 压缩包自动安装（Pre-packaged）方式有个bug。由于 SDK 是在 Linux 环境下打包好的，在 Windows 下解压，会出现部分文件的权限从 755 强制转换为644，导致 git 状态不是 clean：

![image-20250727164656643](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/8671cc395bf5de759f4ef80b0cbc20a4.png)

![image-20250727164717632](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/7957c29ba730bca0d3a49a98b30a3a98.png)

并且，经过实测，即使在 git 全局配置忽略文件权限的变化也没用。必须在每个git子仓库都忽略文件权限的变化：

打开nRF Connect命令行：

![image-20250205000107113](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/8f02cfc623694bbb710701a565fb9a6a.webp)

进入SDK根目录，执行以下内容：

```powershell
# set for all repo:
west forall -c 'git config core.filemode false'

# set for all sub modules:
west forall -c 'git submodule foreach --recursive git config core.filemode false'
```

这是给 NCS 的每个代码仓库，以及每个仓库的子仓库都递归执行 `git config core.filemode false`，从而忽略文件的变化。

处理完毕后，Git 状态变干净了：

![image-20250727170510324](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/95f8f2ee93ed55a849d0f6a5e269d961.png)

</details>

# 4. 打开并浏览例程

从VS Code 的一个全新窗口，选择**打开文件夹**：

![image-20221209103137554](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221209103137554-1731044874928-20.webp)

<center>或者：</center>

![image-20221209103240455](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221209103240455-1731044874929-21.webp)

打开整个SDK目录，这样做是为了**看代码跳转时，SDK中的代码也能跳转到**：

![image-20260727173748165](/imgs/安装nRF-Connect-SDK.assets/image-20260727173748165.png)

然后在VS Code中再打开一个例程：

![image-20250205012416141](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205012416141.webp)

> NCS中所有例程的位置：
>
> ```
> NCS 
> |-- nrf                      
> |   |-- applications/      # Nordic 商业级例程
> |   |-- samples/           # Nordic 外设、蓝牙、LTE等例程
> |   |-- tests/             # 组件 API 测试例程
> `-- zephyr
>  |-- samples            # Zephyr Kernel、各类板子、各类传感器芯片例程
>  `-- tests              # 组件 API 测试例程
> ```
>
> `zephyr/samples/`中有RTOS的组件例程、Zephyr支持的各类厂商的板卡例程、各类传感器的例程等，其中也有蓝牙例程。
>
> `zephyr/tests/`中有**全部的**API测试例程。
>
> `nrf`仓库的目录结构仿造`zephyr`仓库，也有`samples/`和`tests/`目录。`samples/`中有Nordic提供的软件库例程、Zephyr未收录的例程（如 nRF9160的LTE）等。

我们选择`v3.4.0\nrf\samples\bluetooth\peripheral_uart`

![image-20250205012602448](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205012602448.webp)

编译例程的方式，参考后续章节。

> 注意 Windows 有最大路径名长度限制。对于一些依赖路径比较深的工程，再叠加上 build 目录下还有源码层级结构，会编译失败。有以下解决方法：
>
> 1. 参考下一章节“以例程为模板创建新工程”，并把工程放到更浅的路径。
>
> 2. 在编译时，用`-d`参数指定 build 目录到更浅的层级。例如：
>    ```
>    west build -b nrf54l15dk/nrf54l15/cpuapp -d D:\ncs\build nrf/samples/bluetooth/peripheral_uart
>    ```
>
>    工程路径是 `nrf/samples/bluetooth/peripheral_uart`，build 路径是 `D:\ncs\build`。

# 5. 以例程为模板创建新工程

上一节讲解了如何**打开**一个例程。

如果我们只是打开例程，例程的文件夹还是在 NCS 仓库内部，受到 NCS  的 git 仓库的管理。如果想自己用 git 管理自己项目的版本，就需要**创建**新工程。

NCS支持把例程当作模板，复制到NCS外部，并创建新工程。这种独立在 SDK 外部的工程在 Zephyr 中叫做 freestanding 工程。

> 新建工程还有一个用处：**Windows上有目录名长度限制**。在一些路径比较深的例程里进行编译时，会出现长度不足导致编译系统报错找不到某个SDK文件的情况。因此，把例程作为模板拷贝到比较浅的目录中进行开发，可以避免此问题。
>
> Linux，MacOS 则没有这个问题。

## 5.1. 创建新工程

NCS支持以例程作为模板，复制并创建新的工程。这也是Nordic非常推荐的方式。

首先在VS Code中打开一个新窗口

![image-20231027154653607](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231027154653607-1731044874929-24.webp)

在 VS Code中，选择左侧 nRF Connect for VS Code 插件，进入 Welcome 页面。然后点击`Create a new application`创建新工程。

![image-20250205012805758](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205012805758.webp)

选择要使用的 SDK 版本：

![image-20260728232706341](/imgs/安装nRF-Connect-SDK.assets/image-20260728232706341.png)

选择“Copy a sample”

![image-20250205012842271](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205012842271.webp)

选择自己想要拷贝的例程，支持文字搜索：

![image-20260728232757591](/imgs/安装nRF-Connect-SDK.assets/image-20260728232757591.png)

这里选择`nrf/samples/bluetooth/peripheral_uart`

>这里的例程列表，和第 4 节中提到的目录结构是一致的。同时也和NCS官网的例程说明文档是保持一致的，下图位置打开官网文档：
>
>![image-20250205013013188](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205013013188.webp)
>
>Nordic商业级应用：https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/applications.html
>
>Nordic例程：https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/samples.html
>
>Zephyr例程：https://docs.nordicsemi.com/bundle/ncs-latest/page/zephyr/samples/index.html
>
>![image-20260728232951560](/imgs/安装nRF-Connect-SDK.assets/image-20260728232951560.png)
>
>此外，还有一些模块的例程不会出现在这个界面，但是可供参考：
>
>- `${NCS}/modules/hal/nordic/nrfx/samples/src/`： NRFX外设驱动库例程。如果用户不想用、或者Zephyr没有提供某些外设的标准驱动，则可以使用NRFX驱动，其用法和老的nRF5 SDK基本一致。
>- `${NCS}/zephyr/tests`：zephyr所有的API的测试用例。如果你不知道某个Zephyr API怎么用，可以从这里面找。

选择自己新建工程的位置，注意：**Windows上，freestanding 工程必须和 SDK 在同一个磁盘**：

![image-20250205013142630](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205013142630.webp)

然后就可以打开新的工程。

## 5.2. 添加 Workspace

独立工程已经可以编译了，但是编译完看代码时，按 `Ctrl + 鼠标左键` 跳转的代码在 SDK 内部，无法直接跳过去。这里需要把 SDK 和当前工程添加到同一个 VS Code Workspace 中。

选择添加文件夹到 Workspace

![image-20250205013547421](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205013547421.webp)

直接把整个NCS和当前工程添加到同一个Workspace中：

![image-20260728233127244](/imgs/安装nRF-Connect-SDK.assets/image-20260728233127244.png)

保存当前workspace：

![image-20250205013723666](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205013723666.webp)

下次打开时，只需双击 `.code-workspace` 文件，就能直接打开整个 workspace 

![image-20250205013906343](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205013906343.webp)

最后记得修改`.gitignore`文件，这样你和其他人协助开发时这些文件就各自使用自己电脑上的配置，不会互相干扰：

![image-20250205013949727](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205013949727.webp)

## 5.3. 清理 Workspace 插件

可能你的 VS Code 里还安装了其他厂商的插件，或者一些 VS Code 推荐安装的插件。开发NCS时，某些插件会不断弹窗报错，非常烦人。

这时你可以用 VS Code 的 workspace 功能来**局部关闭**这个插件。

目前版本 NCS 的插件包只需要这六个插件：

![image-20250512170309135](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250512170309135.png)

![image-20250512170323334](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250512170323334.png)

因此你在 workspace 里可以关掉其他不必要的插件。举例来说，微软的 **“CMake Tools”** 插件会一直弹窗询问 CMake 根目录文件在哪里：

![image-20250512170510620](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250512170510620.png)

我们不需要它来帮助解析 CMake 。直接在插件页面单独关掉它：

![image-20250512170600781](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250512170600781.png)

如此一来，只在当前 workspace，这个插件就被关闭了。同理，其他插件也可以这样关闭，你不再会受到这些插件打扰。同时，在其他 workspace，不影响你继续正常使用那些插件。

## 5.4. 使用git跟踪你的代码修改

如果你从没用过 git，非常建议使用去学习一下，它极大的方便了代码的管理。如果已经在使用，可以跳过本节。

<details>
    <summary>[点击展开]</summary>


> 安装完 git 后，需要先配置用户名和邮箱。这个用户名和邮箱不是登陆什么网站用的，而是一个签名，在提交代码时用于标记这段代码是谁提交的。这个配置存在你电脑的本地，并且是**全局**的，对所有git仓库都有效。例如：
>
> ```bash
> git config --global user.name "Jayant.Tang"
> git config --global user.email "xxxxx@xxxxx"
> ```

用 nRF Connect for VS Code 新建的工程都会自动初始化 git 仓库，如下是 .gitignore 文件：

![image-20231027155922698](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231027155922698-1731044874930-31.webp)

你可以把`.vscode/`和 `*.code-workspace`添加到其中。

在 VS Code 中使用 git：

如果安装了 git history 插件，就可以查看提交历史：

![image-20221122235338251](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221122235338251-1731044874930-32.webp)

Git History 提供了很方便的视图，可以看到每次commit都改动了哪些代码和配置（左侧是旧的，右侧是新的）：

![image-20221122235416865](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221122235416865-1731044874930-33.webp)

​	更多Git的使用，可以去网上了解其他教程。本文不再赘述。

</details>

# 6. 编译工程

## 6.1. nRF Connect for VS Code 编译

### 创建一个编译目标（Build Target）

所谓编译目标就是在同一套代码下，可能根据不同的配置项（Debug / Release，不同的优化级别， 不同的工作模式等等），编译出不同的可执行文件。一个项目下可以创建多个编译目标。

![image-20250205014115409](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205014115409.webp)

### 选择 Toolchain 和 SDK 版本

在 build 界面设置 Toolchain 和 SDK 版本：

![image-20260728234058667](/imgs/安装nRF-Connect-SDK.assets/image-20260728234058667.png)

### 选择 Board Target

![image-20260728234158666](/imgs/安装nRF-Connect-SDK.assets/image-20260728234158666.png)

创建Build时，需要选择自己使用的板子，Zephyr自带许多厂商的开发板配置。

上图中，Board target 下拉框是用来选板子的，下方还有几个**过滤器**，来过滤可选的板子：

- Compatible boards：本例程适配的板子，是经过验证的。如果选择这些板子，**不需要任何修改就可以烧录进去使用**

- Nordic SoC：使用了 Nordic SoC 的板子，不一定是 Nordic 开发板

- Nordic Kits：Nordic 出品的官方开发板
- All boards：Zephyr 中所有的板子

> 黄色感叹号（⚠️）表示这个板子对应的 SoC **支持 TrustZone 硬件隔离**，而我们选择了不使用。普通的应用就这样选没问题。
>
> 简单介绍安全隔离特性：
>
> SoC 的外设和核心寄存器地址空间被分为两个部分，**安全空间**和**非安全空间（ns）**。如下图深蓝色为**非安全空间**可访问的资源（不包含关键资源），浅蓝色为**只有安全空间可访问的资源**（包含关键资源）。部分外设可以通过两个空间访问，地址不同。
>
> ![image-20260728235946564](/imgs/安装nRF-Connect-SDK.assets/image-20260728235946564.png)
>
> 如果你的 board target 是 `cpuapp`这种，应用程序就是直接跑在安全空间； board target 是`cpuapp/ns`这种，应用程序就运行在非安全空间。
>
> 如果**应用程序直接跑在安全空间**，就和普通的单片机开发架构类似，应用程序可以访问所有寄存器和 NVM 地址。简单的传感器采集、BLE 透传等应用直接使用安全空间开发，最简单，是非常合理的选择。
>
> 如果应用程序跑在**非安全空间**，就需要一个单独的安全固件（Trusted Firmware-M, TF-M）跑在安全空间，负责保管非对称加密的私钥等信息，并提供 Root of Trust, Secure Boot, Secure Storage 等服务。即使你的非安全空间应用程序被漏洞攻破（通过内存踩踏等方式），ARM TrustZone 硬件隔离机制能保证秘密信息不被获取。因为非安全空间无法单纯靠地址获取到安全空间的信息，这是硬件架构保证的。

Board target 实际是为固件编译服务的，它包含固件编译所需的硬件信息。因此前面是板子名称，后面是 SoC 和 CPU名称，以及地址空间名称。

>Zephyr Board target 配置的命名规则：
>
>![image-20250205023618902](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205023618902.webp)
>
>举例：
>
>1. `nrf52840dk/nrf52840`，是说这个 target 是为 nRF52840DK 这块开发板上的 nrf52840 这颗 SoC 创建的。
>2. `nrf9160dk/nrf9160` 和 `nrf9160dk/nrf52840`，都是 nRF9160DK 这块开发板的配置。但是这块开发板上有两颗 SoC，一颗是9160 SiP，另一颗是nrf52840。所以有两个配置可选，分别是为这两颗 SoC 编译固件。
>3. `nrf5340dk/nrf5340/cpuapp` 和 `nrf5340dk/nrf5340/cpunet`，都是 nRF5340DK 这块板子的配置，并且这块板子上只有 nRF5340 这一颗SoC。但是 nRF5340 是一颗双核 SoC，所以，可以有两种配置来区分两个 CPU 核。这两个 CPU 核的固件是分开运行的，因此编译时也是分别编译的。
>4. `nrf54l15dk/nrf54l15/cpuapp `和 `nrf54l15dk/nrf54l15/cpuapp/ns`。前面已经介绍过，表示同一板子、同一 SoC、同一  CPU，但是选择是否使用TrustZone 技术。当你选择`/ns`版本时，Zephyr 会自动启用 TF-M 作为安全空间固件。
>5. `nrf54l15dk/nrf54l10/cpuapp`。nRF54L15 / L10 / L05 是 pin to pin 封装，基本只有存储容量的区别，但是 Nordic 只出了 nRF54L15 的开发板。选择这个选项在编译固件时，会保留开发板上的引脚分配，但是 SoC 会按照 54L10 的资源进行分配，方便开发者用开发板评估 L10 和 L05。
>
>更详细的信息可参考：[《理解Zephyr编译与配置系统》](https://jayant-tang.github.io/2022/12/2a39e705bff0/)。
>
>
>
>如果你想针对不同 Board target 编写 CMake 规则脚本，有以下变量可以获取代表当前编译的信息：
>
>```cmake
># Board name, like "nrf54l15dk"
>${BOARD}
>
># Board qualifiers, like "/nrf54l15/cpuapp"
>${BOARD_QUALIFIERS}
>
># board target name, like "nrf54l15dk/nrf54l15/cpuapp"
>${BOARD}${BOARD_QUALIFIERS}
>
># 下划线形式，常用于匹配配置文件
># 例如 ${NORMALIZED_BOARD_TARGET}.conf 
># 对应 nrf54l15dk_nrf54l15_cpuapp.conf
>${NORMALIZED_BOARD_TARGET}
>```

### 配置文件

各种配置文件、追加配置文件，具体可参考[《理解Zephyr编译与配置系统》](https://jayant-tang.github.io/2022/12/2a39e705bff0/)：

![image-20260729002603166](/imgs/安装nRF-Connect-SDK.assets/image-20260729002603166.png)

### 编译选项

可以设置Build目录，优化等级等等。Sysbuild可参考[《理解Zephyr编译与配置系统》](https://jayant-tang.github.io/2022/12/2a39e705bff0/)，NCS v2.7.0 引入，v2.8.0 起默认启用。

![image-20260729002644008](/imgs/安装nRF-Connect-SDK.assets/image-20260729002644008.png)

## 6.2. 命令行编译

命令行编译常用于服务器 CI/CD 环境、脚本、AI 辅助编程。在使用命令行编译之前，一定要确保已经进入了工具链环境。

### 工具链环境

前面章节已经介绍了如何[“打开工具链环境”](#打开工具链环境)。其中，VS Code 中的命令行环境，已经设置好全部的环境变量了，无需额外操作。不过，这都是让**人**来继续后面的操作。

这种另开的终端对于脚本或者 AI Agent 使用起来不方便。我们还是希望在当前命令行环境中直接设置环境变量。

并且，nrfutil 的方式只会设置 Toolchain 相关环境变量（`PATH`），还缺少 `ZEPHYR_BASE` 环境变量。

> 有时如果你发现 `west help` 展示的命令列表里面没有`west build`, `west flash`等扩展命令，就是因为缺少 `ZEPHYR_BASE`变量，找不到 west 工作区。
>
> 工作区类型：
>
> - Zephyr Workspace：例如 v3.4.0 目录。顶层有一个 `.west/`目录，里面记录了 `ZEPHYR_BASE` 的相对路径。当你直接在 v3.4.0 内的任意子目录内执行`west`命令时，都能自动识别。
> - freestanding：如果你当前目录在 West 工作区外部，必须手动指定 `ZEPHYR_BASE`环境变量。

最方便的做法是直接导出一个环境变量设置脚本，然后直接在当前终端设置新的环境变量。

参考以下命令：

```shell
# Linux / macOS / Windows Git Bash
eval "$(nrfutil sdk-manager toolchain env --ncs-version=v3.4.0 --as-script sh)"

export ZEPHYR_BASE="$HOME/ncs/v3.4.0/zephyr"
```

```bash
# Windows Git Bash
eval "$(nrfutil sdk-manager toolchain env --ncs-version=v3.4.0 --as-script sh)"

export ZEPHYR_BASE="/d/ncs/v3.4.0/zephyr"
```

```powershell
# powershell
nrfutil sdk-manager toolchain env --ncs-version=v3.4.0 --as-script powershell |
    Out-String |
    Invoke-Expression

$env:ZEPHYR_BASE = (Resolve-Path "D:\ncs\v3.4.0\zephyr").Path
```

> 参考 AI Skills 提示词：[nrf-connect-skills-ZH_CN/zephyr-build/SKILL.md at master · Jayant-Tang/nrf-connect-skills-ZH_CN](https://github.com/Jayant-Tang/nrf-connect-skills-ZH_CN/blob/master/zephyr-build/SKILL.md)

验证：

```powershell
west topdir
D:/ncs/v3.4.0
```

有`west`命令能执行，说明 Toolchain 的`PATH`设置成功；`west topdir`有输出，说明 SDK 的`ZEPHYR_BASE`设置成功。

> 【单条命令】
>
> 如果你只是想执行1条命令，可以用:
>
> ```shell
> nrfutil sdk-manager toolchain launch --ncs-version=<version> -- <command>
> ```
>
> 例如：
>
> ```shell
> nrfutil sdk-manager toolchain launch --ncs-version=v3.4.0 -- west help
> ```
>
> 这个会启动单独进程来执行命令。不过这个也是没有`ZEPHYR_BASE`环境变量的，可以用`--chdir`直接跳到 SDK 内部来规避 freestanding 的情况。
>
> ```
> nrfutil sdk-manager toolchain launch --ncs-version=<version> \
>   --chdir <ncs-install-dir> -- \
>   west build -b <board_target> -d <abs-build-dir> <abs-app-dir>
> ```

### 编译命令

| 目的 | 命令（当前终端完成环境初始化后直接执行） |
|------|------|
| 新建或重配构建 | `west build -b <board_target> -d <selected-build-dir> <app-dir>` |
| 复用已选 build 目录 | `west build -d <selected-build-dir>` |
| pristine 构建 | `west build -p always -b <board_target> -d <selected-build-dir> <app-dir>` |
| 显式启用 sysbuild | `west build -b <board_target> -d <selected-build-dir> <app-dir> --sysbuild` |
| 显式禁用 sysbuild | `west build -b <board_target> -d <selected-build-dir> <app-dir> --no-sysbuild` |
| 交互式 Kconfig | `west build -t menuconfig -d <selected-build-dir>` |
| 内存占用报告 | `west build -t ram_report -d <selected-build-dir>` / `rom_report` |
| 列出开发板 | `west boards` |

其中，`<app-dir>`可以省略，省略的话就是当前目录`./`。

编译命令示例：

```bash
west build -b nrf52840dk/nrf52840 -d build -p -- -DCONF_FILE="prj.conf"
# -d 指定编译目录为./build
# -b 板子为nrf52840dk/nrf52840
# -p 表示pristine build,全部重新编译。
# 在--之后可以添加 CMake 选项或KCONFIG配置。如-D表示设置 CMake 变量。
#   -DCONF_FILE等价于在CMakeLists.txt中写 set(CONF_FILE prj.conf)
#   更多CMake配置文件选项，参考https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/app_dev/config_and_build/cmake/index.html#providing_cmake_options
```

更多用法：

```bash
west build -h
```

## 6.3. 编译结果

在 VS Code 中，按`Ctrl + ~`，可以呼出终端。编译完毕后可以看到结果。


![image-20260729020740869](/imgs/安装nRF-Connect-SDK.assets/image-20260729020740869.png)

如果后续要再次编译这个target，可以在APPLICATIONS栏选中自己要构建的工程和target。然后在ACTIONS栏通过build**按钮**进行项目的构建。

> 按Build旁的圆圈箭头按钮，可以全部重新编译（pristine 构建）。

编译时，如果你选中`build/`上下文，会编译全部固件，如果有 bootloader 的话也会一起编译。

如果只选中 `build/peripheral_uart`上下文，则只会编译这个application 固件。

这个上下文选择非常重要。 Kconfig配置、设备树、烧录按钮等都受到这个上下文选择的影响。

![image-20260729020839324](/imgs/安装nRF-Connect-SDK.assets/image-20260729020839324.png)

## 6.4. 编译输出文件

一个工程可能有多个固件，这里以 Matter 窗帘举例。有 Bootloader 和 application。

这里选中哪个子工程，看的就是哪个子工程的输出。如window_covering就是application子工程。然后下方output files就可以看到输出文件。

![image-20250512172148831](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250512172148831.png)

其中比较重要的：

- `.config`是所有配置项合并后的最终配置列表。当你想确认某个配置是否真的打开/关闭了，可以查看这个文件
- `zephyr.dts`是所有设备树文件合并后的最终设备树。当你想确认某个节点最终配置是什么，可以查看这个文件
- `merged.hex`：application + bootloader的合并固件。
- `zephyr.elf`：单独application的固件，并含有调试信息。在它同一目录下，有`zephyr.hex`是纯固件。

## 6.5. 内核一览

![image-20250512172921895](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250512172921895.png)

目前Core overview可以看到初始化级别和已经使能的中断。

### Initialization levels

Zephyr系统中，在main函数之前，会有5个级别的初始化等级。在这些不同的初始化等级时，会执行不同的函数，例如各种外设驱动的初始化、内核服务的初始化等。在这里可以看到这些函数的执行顺序，以及它们被定义的位置。

### Enabled Interrupts

可以看到哪些硬件中断被打开了。

![image-20250512173232076](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250512173232076.png)

# 7. 连接设备

只需通过一根 USB 线连接，左上角电源开关打开：

![image-20260729100740826](/imgs/安装nRF-Connect-SDK.assets/image-20260729100740826.png)

"VDD CURRENT MEASURE" 是 SoC VDD 供电通路，可以测量电流。不测量时，要接好跳线帽。

USB 旁边的 "DEBUGGER" 芯片是 Interface MCU，除了充当 J-Link 之外，还作为 UART 转 USB 虚拟串口、电子开关主控。

Interface MCU 可以用 nRF Connect for Desktop 中的 Board Configurator 上位机来配置：

![image-20260729021955759](/imgs/安装nRF-Connect-SDK.assets/image-20260729021955759.png)

![image-20260729101419783](/imgs/安装nRF-Connect-SDK.assets/image-20260729101419783.png)

通过控制电子开关，Interface MCU 可以管理 SoC 的 GPIO 是否连接到对应的虚拟串口、LED、SWD、外部 QSPI Flash 等等。本例程保持默认即可。

nRF54 系列开发板还能精确调节供电电压，这是由板载的 nPM1300 PMIC 实现的。

> 这个 PMIC 只被 Interface MCU 控制，因此不能用来开发。

然后就可以在 VS Code 中识别到设备了：

![image-20260729102209419](/imgs/安装nRF-Connect-SDK.assets/image-20260729102209419.png)

或者用 nrfutil 查看设备：

```powershell
D:\Project\peripheral_uart> nrfutil device list

1057765088
Product         J-Link
Board version   PCA10156
Ports           COM7, vcom: 0
                COM8, vcom: 1
Traits          boardController, devkit, jlink, seggerUsb, serialPorts, usb

Found 1 supported device
```

最新的开发板一般有两个虚拟串口。**通常 Vcom 1 对应的是例程默认串口，用于日志、透传或者shell**；Vcom 0 通常不使用，或者用于其他功能（DFU、Modem Trace、TF-M Log、网络核的 Log）。

> 这两个 vcom 连接的是 SoC 上固定的引脚，而不是对应 `&uart20`  这样的外设。只不过 `&uart20` 的 Devicetree 默认引脚连接在 Interface MCU 的  vcom 1 而已。引脚都是可以修改的。



老版本 DK：

![image-20221209144123203](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221209144123203-1731044874931-37.webp)

以 nRF52840DK 为例，中间最大的带有贴纸的芯片是Interface MCU，左侧为 J-Link USB口，此接口可以用来给整块板供电。

需确保左下角电源开关打开。左侧中间位置的开关置于 VDD 挡位，右上角开关置于 DEFAULT 挡位（如上图）。

对于一些有多颗 MCU 的开发板，注意要使用拨码开关选择自己要调试的MCU，例如 nRF9160DK 可选择 9160 和 52840：

![image-20221209153801993](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221209153801993-1731044874931-38.webp)

# 8. 烧录固件

连接并成功识别到Jlink后，可以通过ACTIONS栏中的`Flash`按钮触发烧录动作：

![image-20221123160139273](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221123160139273-1731044874934-42.webp)

​	也可以通过命令行进行烧录:

```bash
# 通过 build 目录指定要烧录的build target
west flash -d build
```

> **有时可能会要求全片擦除**，可能的原因：
>
> - 当前固件包含 UICR ，可以认为是一块特殊的 flash 区域，存储了客户自己的加密密钥、引脚配置等信息。要求必须全片擦除才能烧写。
>
> ![image-20221123160245857](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221123160245857-1731044874934-43.png)
>
> 这种情况下只能**全片擦除**然后再烧录，点击Flash右边的按钮：
>
> ![image-20221123160832598](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221123160832598-1731044874935-44.webp)
>
> 或者使用命令行方式：
>
> ```bash
> west flash --force --erase
> ```
>
> 此外，**有时可能会要求 recover**，可能的原因：
>
> - 之前的固件启用了 Flash 写保护，尤其是带 mcuboot 的项目，通常会开启 FPROTEDCT 保护 mcuboot 区域。
>- 之前的固件开启了调试接口保护
> 
> 需要 recover 这颗芯片来解除保护，才能写入新固件。
>
> 注意，recover 也会擦除全部固件和 UICR。
>
> 通常，VS Code 右下角会有弹窗来问你是否要 recover。
>
> 也可以用命令行来 recover
>
> ```bash
>nrfutil device recover
> ```
> 
> 如果是 nRF5340 这种双核芯片，那么网络核要先 recover
>
> ```bash
>nrfutil device recover --core Network
> nrfutil device recover --core Application
> ```



# 9. 运行并测试

连接的设备，可以看到主控芯片、串口以及RTT。

![image-20260729103835999](/imgs/安装nRF-Connect-SDK.assets/image-20260729103835999.png)

这里的串口是 SoC 上真实的物理串口，在开发板上通过 PCB 走线连接到 J-Link，然后 J-Link 把这个串口映射为 USB 虚拟串口。老款开发板可能只有 1 个 VCOM。

## 	9.1. 连接串口

可以在 VS Code 中连接，一般 VCOM1 对应的是例程默认串口：

![image-20260729104119016](/imgs/安装nRF-Connect-SDK.assets/image-20260729104119016.png)

也可以用 nRF Connect for VS Code 的串口终端：

![image-20260729104203963](/imgs/安装nRF-Connect-SDK.assets/image-20260729104203963.png)

![image-20260729104242096](/imgs/安装nRF-Connect-SDK.assets/image-20260729104242096.png)

VS Code 里的串口终端默认是 **Shell 模式**，类似 PuTTY。**按下键盘的按键就立即发送出去一个字符，不会显示自己发出了什么**。便于在这个串口上运行 uart shell。

> 在操作 uart shell 时你能看到输入的命令，是因为 shell 回显了你输入的字符。

nRF Connect for Desktop 里的串口助手两种模式都支持（如上图）。如果是 **Line 模式**，需要在上面输入要发送的内容，然后按 **"Send"** 按钮才会发送。

按下板子上的 Reset 按钮，就能看到串口启动 banner：

![image-20260729104652881](/imgs/安装nRF-Connect-SDK.assets/image-20260729104652881.png)

## 9.2. 连接RTT

RTT 是 Segger 提供的日志调试手段，全称 Real-Time Transfer。SoC 将日志打印到内部缓存中，然后利用 J-Link的高速通道，把日志显示到电脑上。这个方法不需要占用串口外设，而且速度极快，对 CPU 运行影响小。

> **大多数例程的默认日志输出是串口**。但本例程是蓝牙串口透传，串口需要传输用户数据，因此本例程已经把日志的输出配置成 RTT 了，无需再额外修改配置。
>
> 要查看RTT日志输出的相关配置，打开工程根目录下的`prj.conf`文件：
>
> ![image-20221209161912543](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221209161912543-1731044874935-50.webp)
>
> 可以看到：
>
> ```bash
> CONFIG_LOG=y                 # 启用日志系统
> CONFIG_USE_SEGGER_RTT=y      # 启用RTT驱动
> CONFIG_LOG_BACKEND_RTT=y     # 日志后端选用RTT
> CONFIG_LOG_BACKEND_UART=n    # 日志后端不选用串口
> CONFIG_LOG_PRINTK=n          # PRINTK不从LOG输出（而是从console输出）
> ```
>

如下图再连接RTT：

![image-20260729105102815](/imgs/安装nRF-Connect-SDK.assets/image-20260729105102815.png)

选中应用核（Application）：

![image-20260729105112410](/imgs/安装nRF-Connect-SDK.assets/image-20260729105112410.png)

能看到日志从 RTT 输出：

![image-20260729105201484](/imgs/安装nRF-Connect-SDK.assets/image-20260729105201484.png)

## 9.3. 测试 peripheral_uart 例程

一般来说，需要两块开发板，一块烧 `peripheral_uart`，一块烧 `central_uart`。两块开发板上电后会自动连接 BLE。从一个开发板串口输入的数据，会自动从另一个开发板输出。

但是这里我们只有一块开发板，那么 BLE Central 我们就用手机。iOS 应用商店可以下载 `nRF Connect`，安卓可以在谷歌商店下载，或者直接去Github下载[APK](https://github.com/NordicSemiconductor/Android-nRF-Connect/releases)。

> 由于苹果权限控制，iOS 版本的 App 是看不到 MAC 地址的。

### 通过BLE连接设备

以 iOS 为例，在 nRF Connect APP中，先 scan 搜索附近蓝牙。scan 按钮一开始是三角形，点击开始扫描后，变成方形。
扫到设备后，再连接：

![image-20231028104626601](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028104626601-1731044874935-52.webp)

### 开发板接收数据

![image-20231028104717740](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028104717740-1731044874936-53.webp)

![image-20231028104734696](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028104734696-1731044874936-54.webp)

可以在串口看到数据：

![image-20231028104845188](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028104845188-1731044874936-55.webp)

### 开发板发送数据

Central 和 Peripheral 是 GAP 层的概念。在 GATT层，BLE 协议是 Client-Server 架构。本例程是 BLE Peripheral，同时也是 GATT Server，只能被 Client 读写上面的 GATT 特征（Characteristic）。默认情况下，Server 不能主动发消息到 Client。除非 Client 使能了 Notify 的功能，Server 才能 Notify 到 Client。相关资料，大家可以搜索 CCCD(Client Characteristic Configuration Descriptor)，这里不赘述。现在我们需要点亮 TX 属性的 CCCD，使能 Notify 功能：

![image-20231028105348055](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028105348055-1731044874936-56.webp)

然后在串口中通过键盘输入内容：hello + 回车。屏幕上不会显示东西，但是按键会发送出去。

> VS Code 里的串口终端默认是 **Shell 模式**，按下键盘的按键就立即发送出去一个字符，不会在屏幕上显示自己发出了什么。
>
> 这里之所以要加回车，是因为例程代码是靠回车解析数据包的。在串口回调函数的状态机内，检测到回车，才会把串口数据打包从蓝牙发出。

可以在手机上看到开发板发过来的数据：

![image-20231028105643833](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028105643833-1731044874936-57.webp)

至此，我们完成了在 nRF54L15DK 上的`peripheral_uart`例程的编译、烧录与运行测试。


# 10. 阅读代码、跳转与搜索
> 工程中的函数与变量、Kconfig 配置、设备树都是可以**Ctrl+鼠标左键**点击跳转到定义的。为了能够确保跳转和搜索到 SDK 内部的代码，记得按照前面第 5.2 小节的方法，把 NCS 和当前工程添加到同一个 Workspace 中。

当一个工程**编译完毕后**，就可以在nRF插件中进行浏览了：

![image-20260729110225867](/imgs/安装nRF-Connect-SDK.assets/image-20260729110225867.png)

Source File 中是所有**参与编译**的源码，Zephyr 并不是把所有源码都添加，而是根据 Kconfig 选项，通过 CMake 条件添加源码。其中 **Application** 中的是当前工程中的源码；**SDK** 中的是NCS中参与编译的源码。Generated 中的是工具链自动生成的一些代码（中断向量表、Kconfig 转换成宏等等)。

由于我们前面已经把 SDK 放进了 VS Code workspace，所以也可以直接搜索代码：

![image](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/3028998-20241029124509412-1982218675.webp)

点击上面的搜索按钮后，会自动跳转到 VS Code 搜索界面，并且已经自动填充好文件搜索范围：

![image-20260729110536376](/imgs/安装nRF-Connect-SDK.assets/image-20260729110536376.png)

> 这个功能在Windows上不好用，因为搜索范围过滤条件太多时，Windows 会无法处理，并且非常慢

在浏览和搜索的过程中，时刻注意自己选中的**工程上下文**是**整个工程**的 Build Target 还是**子工程**的 Build Target

![image-20260729110657326](/imgs/安装nRF-Connect-SDK.assets/image-20260729110657326.png)

以免影响后续的编译情况。

# 11. NCS Add-Ons

nRF Connect SDK (NCS) Add-ons 是一个公开可用的补充组件索引，旨在扩展 nRF Connect SDK 的功能。

**功能与内容**：Add-ons 提供了 SDK 标准包之外的多种功能，包括蜂窝应用程序（如Asset Tracker、Serial Modem）、驱动程序、库、协议实现（如 Amazon Sidewalk、Zigbee、ANT+）以及特定技术的完整 SDK。

**独立性**：Add-ons 有独立的发布周期，这使得新库可以更灵活地更新，而无需等待 NCS 主版本的发布。

可以参考：[nRF Connect SDK Add-ons介绍与国内安装实践](https://jayant-tang.github.io/2026/04/40898fb9360c/)

官网见：[nRF Connect SDK Add-ons](https://nrfconnect.github.io/ncs-app-index/)

![image-20260111154308952](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined2b98a862c307f982e2bebbeffc1df0e0.png)



# 12. Nordic AI 辅助编程

[TechDocs](https://docs.nordicsemi.com/) 和 [DevZone](https://devzone.nordicsemi.com/) 网站右下角都有 Ask AI 按钮：

![image-20251016104023585](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedee789e16c4911ac10e4d99c1eb4edc9a.png)

AI 训练了所有的 Nordic 官网资料，以及 DevZone 论坛中的帖子。可以用中文问他：

![image-20260729111146363](/imgs/安装nRF-Connect-SDK.assets/image-20260729111146363.png)

![image-20260729111313166](/imgs/安装nRF-Connect-SDK.assets/image-20260729111313166.png)

不过，网站访问有时候比较慢。即使科学的上网，又可能遇到反爬虫保护，体验不是很流畅。

可以考虑让自己的 AI Agent 接入 Nordic MCP 知识库，这样用起来比较方便。参考：[在AI辅助编程中接入Nordic知识库——Nordic MCP实战](https://jayant-tang.github.io/2026/06/d3853d11acc7/)

# 13. 官方资料

## Nordic TechDocs 资料中心

https://docs.nordicsemi.com/

目前最新的资料中心，可以通过技术或产品系列进行分类，查找想要的资料。芯片数据手册（Specification）、开发板说明都可以在这里查看。

![image-20260729111613133](/imgs/安装nRF-Connect-SDK.assets/image-20260729111613133.png)



## NCS 官网

https://nrfconnectdocs.nordicsemi.com/


![image-20260729111724532](/imgs/安装nRF-Connect-SDK.assets/image-20260729111724532.png)

进入官网，首先看到右上角可以选择文档的版本，需要与SDK的版本对应。

然后可以看到中间的一排标签页：

- **nRF Connect SDK:** 对应的是NCS中的 `nrf` 文件夹。是 Nordic 在 Zephyr 系统上扩展的库、驱动和例程的文档。里面大多数是一些Nordic独有的技术和解决方案。

- **Zephyr Project**：对应的是NCS中的`zephyr`文件夹。是 [Zephyr官方文档](https://docs.zephyrproject.org/latest/index.html) 的一个镜像，包含Zephyr RTOS内核服务、操作系统API、各种驱动、协议支持以及它们的例程文档。一些比较通用的功能的如日志、Flash存储、线程间通信等功能的文档都在这里面。
- **nrfxlib**：对应的是NCS中的`nrfxlib`文件夹。里面是与 RTOS 无关的库，大多是 Nordic 产品的闭源二进制库。
- **MCUboot**：MCUboot是一个开源的第三方安全 bootloader，支持很多系统和平台，Zephyr只是其中之一。支持 OTA 的例程基本都是使用 MCUboot
- **Trusted Firmware-M**：前面介绍了 TrustZone 技术。TF-M 就是微控制器上的安全空间固件实现。当你编译时选择`/ns`的 board target，Zephyr 会自动把 TF-M 作为其中一个子镜像添加进来，成为 Application 的一部分。
- **Matter**：Matter是智能家居的新标准，目的是打破厂商之间的壁垒，实现生态融合。
- **Kconfig**：Zephyr 系统中有大量的 Kconfig 配置，Nordic 扩展的库、驱动中也有大量 Kconfig 配置。如果你不知道一个 Kconfig 配置是干什么的，可以在这个页面进行搜索。

> Kconfig 也可以直接在 SDK 中搜索。比如，如果要搜索 `CONFIG_BT_PERIPHERAL` 是什么意思，可以搜索 `config BT_PERIPHERAL`，并过滤 `Kconfig*`，勾选大小写匹配和完整匹配：
>
> ![image-20260729112707679](/imgs/安装nRF-Connect-SDK.assets/image-20260729112707679.png)

总之，NCS官网里面有大量的技术细节，在运行一个例程之前，一定要参照网站中该例程的说明进行操作。


## Nordic 旧版资料中心 (Info Center)

**此网站已于2024.6.18 被 TechDocs 替代**
如果要查询老的 nRF5 SDK 资料，看：https://docs.nordicsemi.com/bundle/sdk_nrf5_v17.1.0/page/index.html

## Nordic官网

https://www.nordicsemi.com/

一些商业新闻和产品介绍。但是最重要的是一些**工具软件**、**开发板原理图/PCB/BOM**之类，需要在这里下载。

例如：

- nRF54L15DK 硬件资料（原理图、PCB、BOM）：https://www.nordicsemi.com/Products/Development-hardware/nRF54L15-DK/Hardware-files?lang=en#infotabs

## DevZone开发者论坛

https://devzone.nordicsemi.com/

有问题可以在上面搜索，也可以用英文提问。每天都有原厂support team查看问题并回复。Nordic注册客户，还可以提交private ticket，解决一些与代码、板子有关的问题，也可以审核PCB。

## Nordic DevAcademy官方课程

https://academy.nordicsemi.com/

类似于慕课的网站，目前有NCS，BLE、Wi-Fi、Cellular 等课程。有视频结合题目，适合英文好的读者去学习，是非常适合入门的课程。

# 14. 其他推荐阅读

NCS 基础：

- [理解Zephyr编译与配置系统](https://jayant-tang.github.io/2022/12/2a39e705bff0/)
- [Zephyr设备树与驱动应用实战——串口](https://jayant-tang.github.io/2023/11/4c8e1d7d162d/)
- [Nordic GPIO硬件原理与NCS应用详解](https://jayant-tang.github.io/2024/01/b74491c1a080/)
- [Zephyr中的分区和存储系统](https://jayant-tang.github.io/2026/07/cea69d4e489a/)

NCS 应用：

- [一文了解Nordic边缘AI方案](https://jayant-tang.github.io/2026/04/b19b485a13d3/)
- [Nordic Matter开发与例程详解](https://jayant-tang.github.io/2025/01/5645a5cab10c/)
- [nRF9151蜂窝模组简介与定位例程解析](https://jayant-tang.github.io/2025/04/f1f289c546d9/)