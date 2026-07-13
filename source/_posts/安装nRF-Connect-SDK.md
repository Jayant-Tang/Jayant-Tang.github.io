---
title: 安装nRF-Connect-SDK
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
  lastPublishedAt: '2026-07-06T18:20:52+08:00'
  sourceHash: sha256:ced3495a590ed039fd3d8e1f284925f6343e8de096ec78ba54dc3f4a5b033d1d
  status: imported
  postType: Article
---

> 2026.1.11更新：
>
> - 官方已经支持中国大陆服务器源下载NCS
>
> 2025.10.14更新：
>
> - 增加了NCS v3.1.0和v3.1.1在中文Windows系统上编码问题的解决方案
> - 增加了说明，nrfutil sdk-manager v1.8.0 已经解决了SDK在Windows系统上git状态错误的问题
>
> 2025.7.27更新：
>
> - 增加了nRF Connect详细安装说明，和国内软件源
> - 增加了nrfutil详细安装说明，以及命令行自动补全
> - 新增了强制用国内服务器加速安装NCS的方法
>
> 2025.5.12更新：
>
> - NCS v3.0.0支持打包下载，无需科学的上网从GitHub拉取
> - 新增workspace插件清理内容，解决VS Code弹窗问题
> - 新增对Windows目录名长度限制的提醒

nRF Connect SDK，简称NCS，是Nordic最新的SDK平台。该平台支持Nordic的四大产品线：
1.  **短距离 2.4G MCU**：
    - Bluetooth LE（主机、从机、主从一体、多主多从、BLE MESH、AoA/AoD蓝牙测向、LE Audio、 PAwR、Channel Sounding）
    - 基于802.15.4的OpenThread和Zigbee
    - 2.4G私有协议（ESB）
2.  **中距离 Wi-Fi** 收发器：
    - nRF700x系列的Wi-Fi收发器，低功耗双频Wi-Fi6，QSPI/SPI接口。NCS提供700x系列的Zephyr驱动和例程。
3.  **长距离 蜂窝 模组**：
    - nRF91系列，是支持CAT-NB1(NB-IoT)和CAT-M1的**系统级封装（SiP）**，全球运营商认证。**超低功耗，小尺寸**，支持Open CPU和 AT Commands方式开发。
4.  **Nordic nPM电源管理芯片（PMIC）**：
    - 支持通过i2c控制Nordic电源管理芯片
    - 支持一键方案：通过PMIC的GPIO一键进入或退出运输模式，一键系统级电源reset，或者其他应用层功能
    - 支持电量算法：低功耗采样且MCU休眠时无需采样，结合预先训练的电池模型和算法库直接获得较为精确的电量

软件上，还支持Matter，HomeKit，Apple FindMy，Google FindMy，Amazon Sidewalk，ANT+等物联网协议；硬件上，还支持Nordic的2.4G无线功率放大器（PA）和电源管理芯片（PMIC）。

NCS基于Zephyr系统。Zephyr系统是一个**开源嵌入式实时操作系统**项目，由[Linux基金会和众多厂商](https://zephyrproject.org/project-members/)维护。Zephyr系统除了基本的ROTS之外，还有很多中间件，软件库，硬件驱动等等。

> Zephyr的强大特性
>
> 1. 全面的内核服务
>    - 多线程，支持协程和基于优先级的抢占。兼容POSIX pthreads API。
>    - 多种动态内存分配工具，支持固定大小或可变大小的内存块
>    - 支持多种信号量同步机制；支持多种线程间通讯机制（消息队列、字节流等）
>    - CPU电源管理和外设电源管理
> 2. 多种调度策略可选
> 3. 高度可定制性、模块化开发
> 4. 支持许多架构（x86, ARM, RISC-V）
> 5. 堆栈、内核、驱动、线程间内存保护
> 6. 允许编译时静态定义资源（线程、内存池、队列等），提高性能
> 7. 提供具有一致性的设备驱动模型，并且支持DeviceTree
> 8. 全功能网络协议栈（包括LwM2M和BSD Sockets），OpenThread，BLE
> 9. 跨平台开发（Windows/Linux/MacOS）
> 10. 支持多种文件系统（ext2, LittleFS, FatFS...），还支持FCB(Flash Circular Buffer)
> 11. 强大的模块化日志框架，支持多种后端（串口、RTT、BLE、network、filesystem...）
> 12. 易于开发的Shell
> 13. 在非易失存储器上保存配置，掉电不丢失
> 14. 支持在Linux上运行Zephyr模拟器
> 15. 远程资源管理（通过串口、USB、BLE、network管理固件升级与版本回滚，文件系统资源等）

NCS在Zephyr的基础上提供了更多的脚本工具、协议栈、驱动、功能库等等。

NCS中有许多例程。其中有Zephyr自带的一些基础例程，如线程、LED/Button、TCP/UDP等；也有Nordic提供的高级例程，如BLE键鼠、蓝牙多连接、Matter例程等。NCS官网针对每个例程都提供了文档。

更多信息可参考：

- [NCS官网（英文） - 安装教程](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/installation/install_ncs.html)
- [开发你的第一个nRF Connect SDK(NCS)/Zephyr应用程序 - iini - 博客园 (cnblogs.com)](https://www.cnblogs.com/iini/p/14174427.html)

# 1. 简介

本节将会详细介绍如何在一台**Windows** 11的电脑上安装NCS开发环境（Windows 10也适用），包含NCS、编译器以及其他工具。其他平台的安装也是类似的，参考好官网英文教程即可。

需要安装的内容列表：

| 序号 |                             软件                             | 分类      | 用途                                                         |
| :--:  | :----------------------------------------------------------: | --------- | ------------------------------------------------------------ |
|  1    |     [Visual Studio Code](https://code.visualstudio.com/)     | 编辑器    | 代码文本编辑器，并且通过安装插件的方式为其他开发调试工具提供可视化界面 |
|  2    | [nRF Command Line Tools](https://www.nordicsemi.com/Products/Development-tools/nrf-command-line-tools) | 命令行工具    | nrfjprog命令行烧录工具（后续将被nRF Util取代） |
|  3   | [nRF Util](https://www.nordicsemi.com/Products/Development-tools/nRF-Util)| 命令行工具| 更高级的命令行工具，类似于包管理器，可以安装各种子命令。包括烧录、管理toolchain/SDK、DFU、BLE抓包、蜂窝ModemTrace|
| 4 | [nrf-udev](https://github.com/NordicSemiconductor/nrf-udev) | 配置文件 | 【Linux专用】配置USB设备权限，可识别Nordic USB设备 |
|  5   | [nRF Connect for Desktop](https://www.nordicsemi.com/Products/Development-tools/nrf-connect-for-desktop) | 桌面工具  | Nordic桌面工具集合   |
| 6 | [Jlink驱动](https://www.segger.com/downloads/jlink) | 驱动 | JLink驱动需要单独安装。 |
|  7   | NCS Toolchain | 编译工具链 | 一个独立的工具链文件夹，含Git、CMake、Python、Ninja、GCC等工具，与你电脑上已经安装的环境不冲突 |
|  8   |         [NCS](https://github.com/nrfconnect/sdk-nrf)         | SDK源码包 | SDK本体，含内核、驱动、模块、协议栈等等的源码 |

# 2. 安装开发工具

## VS Code

在官网安装：[Visual Studio Code](https://code.visualstudio.com/)

## JLink驱动

在 [SEGGER - JLink官网](https://www.segger.com/downloads/jlink) 下载JLINK驱动。

其中JLink的版本参考[NCS依赖](https://docs.nordicsemi.com/bundle/ncs-2.9.0/page/nrf/installation/recommended_versions.html#j-link_software_and_documentation_pack)文档：

打开文档后，先把文档版本对齐为你要安装的最新的正式版NCS版本，比如这里是NCS v2.9.0：

![image-20250205021043601](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205021043601.webp)

然后往下翻，找到 J-Link 需要的版本：

![image-20250205021126347](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205021126347.webp)

> 也可以用`nrfutil device --version`对照查看nrfutil device需要的JLink版本。注意，**下表对应的不是NCS的版本**。
>
> | SEGGER J-Link version | Tested with…                                                 |
> | --------------------- | ------------------------------------------------------------ |
> | v8.10f                | `device` v2.7.11 and newer                                   |
> | v7.94i                | `device` v2.5.4 to v2.7.10, `ble-sniffer` v0.9.0 and newer, `trace` v3.0.0 and newer, `91` v0.5.0. |
> | v7.94e                | `device` v2.1.1 to v2.5.3.                                   |
> | v7.88j                | `device` v2.0.2 to v2.0.3.                                   |

**安装JLink驱动时，一定要带上JLink USB驱动**：

```powershell
# For windows
.\JLink_Windows_V794i_x86_64.exe -InstUSBDriver=1
```

或者在安装时勾选USB driver：

![image-20250727155420764](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/57c7c7a3c1b24a4013e61a438ba92626.png)



其他依赖： [Microsoft Visual C++ Redistributable](https://docs.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170#visual-studio-2015-2017-2019-and-2022)

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

## nrfutil

nrfutil是一个命令行工具集。可以联网安装各种工具，比如程序烧录，SDK管理，工具链环境等等。

在官网下载可执行文件：[nRF Util](https://www.nordicsemi.com/Products/Development-tools/nRF-Util)。

然后把nrfutil所在目录添加到PATH环境变量：

![image-20250727160809557](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/374227a1ab74d3ff010f5f8cbd22289f.png)

![image-20250727160716550](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/66eba8f83e53eed553bda73f46e9858c.png)

在命令行中执行子程序的下载：

```powershell
# 联网查找软件包
nrfutil search

# 自我更新
nrfutil self-upgrade

# 安装常用软件
nrfutil install device toolchain-manager sdk-manager completion
```

其中，`completion`是nrfutil支持在powershell, bash和zsh下的**命令自动补全**，这样以后敲nrfutil命令按tab就能补全，非常方便。

以power shell为例：

```powershell
PS C:\Users\Jayant> nrfutil completion install powershell

Add the following to your $PROFILE file:

# From nrfutil completion install
# WARNING: nrfutil tab-completion may become slow because of Windows Defender
if ( Test-Path -Path ${env:USERPROFILE}\.nrfutil\share\nrfutil-completion\scripts\powershell\setup.ps1 ) {
    . ${env:USERPROFILE}\.nrfutil\share\nrfutil-completion\scripts\powershell\setup.ps1
}
```

命令结果提示我们，把命令行输出的内容粘贴到`$PROFILE`文件中，也就是`~\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`。

安装了VS Code的情况下，可以这样打开此文件：

```powershell
code $PROFILE
```

需要管理员权限。另外如果你是首次设置windows powershell脚本，需要修改注册表使其允许执行脚本：

```powershell
#在管理员终端中执行
set-executionpolicy remotesigned
```

在那之后，重新打开命令行。随意输入nrfutil的命令，只输入一半按TAB键，就可以看到自动补全候选项了：

![image-20250727162035911](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/cf0c001fc9315b8e08579d979b4023dc.png)



> - 在NCS v3.0.0之后，NCS内的程序下载全部使用nrfutil。nRF Command Line Tools(nrfjprog)不再使用
> - 如果你的电脑不能联网，可以先在有网络的电脑安装，然后导出到不能联网的电脑，见：[nrfutil离线安装方法](https://jayant-tang.github.io/2023/11/b3ef0c412298/)
> - 对于Linux版本，执行 `nrfutil completion install bash` 或者 `nrfutil completion install zsh` ，把输出的脚本配置复制到对应的`~/.bashrc`或者`~/.zshrc`中即可。

## VS Code插件

VS Code的安装这里不做介绍。VS Code的插件可以在VS Code插件市场搜索**nRF Connect for VS Code Extension pack**来一次性安装所有需要的插件。

![image-20250204233110265](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250204233110265.webp)



如果你的电脑不能联网，需要离线安装。参考以下内容：

<details>
    <summary>[点击展开]</summary>

先在有网络的电脑上下载VSIX离线插件文件：
![image-20250727162402886](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/a51c1f6d2f3fd4c6fa027cb35fb90145.png)

注意这个插件包只是个封装。封装里的每一个插件都要单独下载VSIX，并选择平台：

![image-20250727162619019](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/461ecd55f552d8599ac52893b91c0894.png)

然后，拷贝到不能联网的电脑上导入即可：

![image-20250727162713479](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/a323fc91f942a982240fb8f3e5c856c7.png)

</details>

## Linux USB规则

对于Linux电脑，需要安装：

```bash
sudo apt install libusb-1.0-0

# 先从https://github.com/NordicSemiconductor/nrf-udev/releases下载deb包
sudo dpkg -i nrf-udev_1.0.1-all.deb
```



# 3. 安装编译工具链和SDK

Toolchain和SDK是两个独立的文件夹。Toolchain包含python, cmake, ninja, gcc等工具，与你电脑上本身的环境变量不冲突。SDK包含源码、脚本、库等。

电脑上可以同时安装多个版本的toolchain和SDK

**简化后**的目录树：

```
ncs
├─── toolchains
│      ├─── 648da874d
|      ├─── bc5b4cb7c
│      └─── toolchains.json
├───  v2.9.0
└───  v3.0.0
```

toolchain的目录名是某种哈希值，而不是版本号。`toolchains.json`中记录了这些哈希值和toolchain版本的对应关系。实际的目录树，还会有一些临时文件，和解压前的文件：

![image-20250512163349985](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250512163349985.png)

默认路径（`C:\ncs`或者`~/ncs`）下存放各个版本的SDK。此外，还有一个Toolchain文件夹，其中存放各个版本的toolchain。

toolchains是编译所需的二进制工具，如编译器、cmake、Python等。Nordic在服务器上提供了压缩包直接下载Toolchain。直接按照后面步骤自动下载自动安装即可。

SDK是放在**GitHub**上的许多仓库的合集，主仓库是[sdk-nrf](https://github.com/nrfconnect/sdk-nrf)。当你能稳定科学地上网，才能从GitHub方便地安装。不过**目前Nordic也提供了压缩包形式的SDK**，国内也有服务器，无需科学的上网就能直连下载。

## 3.1. 方式一：预打包方式安装

### (1) 强制设置中国大陆服务器源

> 手动设置服务器地址，目前已经不需要

<details>
     <summary>[点击展开]</summary>

> 注意，此方式不能加速从GitHub拉取的方式，只是从国内服务器下载pre-packaged SDK压缩包。
>
> 后续nrfutil可能会更新更方便的用法，我会更新到本文。

在环境变量中新建以下内容：

![image-20250727162858814](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/bf9d21cebb6648bdeb34f03f72563ce1.png)

以上方式为全局设置，对命令行nrfutil toolchain-manager和VS Code插件都生效。

如果你要用nrfutil命令行去安装，也可以设置临时的命令行环境变量。

PowerShell临时环境变量设置：

```powershell
$Env:NRFUTIL_SDK_REMOTE_CONFIG_URL = "https://files.nordicsemi.cn/artifactory/ncs-src-mirror/external/sdk-manager/config-cn.json"
$Env:NRFUTIL_TOOLCHAIN_REMOTE_CONFIG_URL = "https://files.nordicsemi.cn/artifactory/NCS/external/bundles/config-cn.json"
```

Linux命令行临时环境变量设置：

```bash
export NRFUTIL_SDK_REMOTE_CONFIG_URL="https://files.nordicsemi.cn/artifactory/ncs-src-mirror/external/sdk-manager/config-cn.json"
export NRFUTIL_TOOLCHAIN_REMOTE_CONFIG_URL="https://files.nordicsemi.cn/artifactory/NCS/external/bundles/config-cn.json"
```

</details>

### (2) 安装Toolchain

在插件的Welcome界面，选择安装新的Toolchain

![image-20250204234236367](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250204234236367.webp)

首次安装时，可以选择从中国大陆服务器源安装：

![image-20260111151518152](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedfa133b99840f69c171da4b0a1eb9683c.png)

> 也可以在VS Code插件中设置：
> ![image-20260111151807211](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined3a044a141efeac73fde57e8e267dcf3f.png)

下一步，**先设置安装路径，然后点击选择要安装的NCS版本。**

![image-20250727163923939](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/ee8db1f55717e3ca087c9ce4c6db89b5.png)
> 这里设置的是所有toolchain的父目录。Windows默认安装路径是`C:\\ncs\`，Linux下是`${HOME}/ncs/`，MacOS下设置无效。
>
> 例如你可以设置`D:\Project\ncs`：
>
> 目录不要太深，因为Windows对路径名长度有限制。
>
> ![image-20250204235145339](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250204235145339.webp)
>
> 后续安装SDK时也可以设置同样的路径，这样最后电脑上的各个版本NCS都会装在一起并列存在。

Toolchain会自动下载并解压，里面的工具**不会**被添加PATH环境变量中，也**不需要添加到PATH**。防止工具链中的软件和你电脑上已经安装的同名软件产生冲突（如Python)。

可以看到国内镜像的下载速度是非常快的：

![image-20250727164049235](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/13ed66722868a56e25daf2f03453698b.png)

### (3) 安装SDK

安装SDK的方式也类似：

![image-20250205003637807](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205003637807.webp)

然后这里是选SDK的类型：

![image-20260111152919277](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined80bf31322bfede53221d6a4cf8674b06.png)

我们只选第一个就可以。

> - nRF Connect SDK 就是我们要安装的NCS。
> - nRF Connect SDK Bare Metal 是裸机系统，是NCS去掉了Zephyr RTOS和设备树。**只能用于nRF54L系列，只能开发简单蓝牙应用**。不能开发其他产品线如Wi-Fi、蜂窝，也不能开发复杂项目如Matter，组件也不如Zephyr丰富。给习惯用nRF5 SDK的 nRF52系列老客户一个快速升级的选项。如果你感兴趣可以查看[nRF Connect SDK Bare Metal option](https://docs.nordicsemi.com/category/bare-metal)。
> - Third-party是第三方伙伴修改的NCS。比如谷歌或者Qorvo会有一些项目用到NCS，他们会修改SDK。

然后就可以选择下载方式。**Pre-packaged SDKs**是从Nordic服务器下载压缩包然后自动解压，**GitHub**是从GitHub拉取SDK的所有仓库。**只有前者才能享受国内镜像源加速**：

![image-20250512164417437](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250512164417437.png)

这里的安装路径，**最好与toolchain使用相同的父目录**：

![image-20250205003730244](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205003730244.webp)

然后回车安装。安装完毕会自动解压。

### (4) 中文Windows环境修复python读文件编码问题

> 仅中文Windows用户需考虑此问题，英文Windows无需考虑

部分Python在读取文件的时候会用操作系统默认语言读取，导致python用gbk来读取utf8的配置文件，进而导致编译失败。需要修改SDK脚本使其强制使用utf-8。

<details>
    <summary>[点击展开]</summary>

#### NCS v3.1.0/v3.1.1修复

##### pm_static.yml无法写中文注释的问题，需要修改三处

① 在`v3.1.1\nrf\scripts\partition_manager.py`第683行：

```python
with open(ymlpath, 'r') as f:
```

改为:

```python
with open(ymlpath, 'r', encoding='utf-8') as f:
```



② 还是在`v3.1.1\nrf\scripts\partition_manager.py`，第911行：

```python
parser.add_argument('--static-config', required=False, type=argparse.FileType(mode='r'),
```

改为

```python
parser.add_argument('--static-config', required=False, type=str,
```



③ 还是在`v3.1.1\nrf\scripts\partition_manager.py`，第985行：

```python
        static_config = yaml.safe_load(args.static_config)
```

改为

```python
    with open(args.static_config, 'r', encoding='utf-8') as f:
        static_config = yaml.safe_load(f)
```

##### 部分Matter例程无法编译的问题，需要修改2处

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
>   File "D:\ncs\v3.1.1\nrf\scripts\partition_manager.py", line 1054, in <module>
>     main()
>   File "D:\ncs\v3.1.1\nrf\scripts\partition_manager.py", line 1024, in main
>     static_config = load_static_configuration(args, pm_config) if args.static_config else dict()
>                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
>   File "D:\ncs\v3.1.1\nrf\scripts\partition_manager.py", line 985, in load_static_configuration
>     static_config = yaml.safe_load(args.static_config)
>                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
>   File "D:\ncs\toolchains\c1a76fddb2\opt\bin\Lib\site-packages\yaml\__init__.py", line 125, in safe_load
>     return load(stream, SafeLoader)
>            ^^^^^^^^^^^^^^^^^^^^^^^^
>   File "D:\ncs\toolchains\c1a76fddb2\opt\bin\Lib\site-packages\yaml\__init__.py", line 79, in load
>     loader = Loader(stream)
>              ^^^^^^^^^^^^^^
>   File "D:\ncs\toolchains\c1a76fddb2\opt\bin\Lib\site-packages\yaml\loader.py", line 34, in __init__
>     Reader.__init__(self, stream)
>   File "D:\ncs\toolchains\c1a76fddb2\opt\bin\Lib\site-packages\yaml\reader.py", line 85, in __init__
>     self.determine_encoding()
>   File "D:\ncs\toolchains\c1a76fddb2\opt\bin\Lib\site-packages\yaml\reader.py", line 124, in determine_encoding
>     self.update_raw()
>   File "D:\ncs\toolchains\c1a76fddb2\opt\bin\Lib\site-packages\yaml\reader.py", line 178, in update_raw
>     data = self.stream.read(size)
>            ^^^^^^^^^^^^^^^^^^^^^^
> UnicodeDecodeError: 'gbk' codec can't decode byte 0x80 in position 8: illegal multibyte sequence
> CMake Error at D:/ncs/v3.1.1/nrf/cmake/sysbuild/partition_manager.cmake:179 (message):
>   Partition Manager failed, aborting.  Command:
>   D:/ncs/toolchains/c1a76fddb2/opt/bin/python.exe;D:/ncs/v3.1.1/nrf/scripts/partition_manager.py;--input-files;D:/Project/peripheral_uart_dfu_1/build/peripheral_uart_dfu_1/modules/nrf/subsys/partition
> _manager/pm.yml.settings;D:/Project/peripheral_uart_dfu_1/build/peripheral_uart_dfu_1/modules/nrf/subsys/partition_manager/pm.yml.bootconf;D:/Project/peripheral_uart_dfu_1/build/mcuboot/zephyr/include
> /generated/pm.yml;D:/Project/peripheral_uart_dfu_1/build/mcuboot/modules/nrf/subsys/partition_manager//generated/pm.yml;D:/Project/peripheral_uart_dfu_1/build/mcuboot/modules/nrf/subsys/partition_manager/pm.yml.bootconf;D:/Project/peripheral_uart_dfu_1/build/peripheral_uart_dfu_1/zephyr/include/genera
> ted/pm.yml;--regions;sram_primary;otp;bootconf;flash_primary;--output-partitions;D:/Project/peripheral_uart_dfu_1/build/partitions.yml;--output-regions;D:/Project/peripheral_uart_dfu_1/build/regions.y
> ml;--static-config;D:/Project/peripheral_uart_dfu_1/pm_static.yml;--sram_primary-size;0x2f000;--sram_primary-base-address;0x20000000;--sram_primary-placement-strategy;complex;--sram_primary-dynamic-pa
> rtition;sram_primary;--otp-size;1276;--otp-base-address;0xffd500;--otp-placement-strategy;start_to_end;--bootconf-size;4;--bootconf-base-address;0xffd080;--bootconf-placement-strategy;start_to_end;--f
> lash_primary-size;0x165000;--flash_primary-base-address;0x0;--flash_primary-placement-strategy;complex;--flash_primary-device;rram_controller;--flash_primary-default-driver-kconfig;CONFIG_SOC_FLASH_NR
> F_RRAM
> Call Stack (most recent call first):
>   D:/ncs/v3.1.1/nrf/cmake/sysbuild/partition_manager.cmake:636 (partition_manager)
>   D:/ncs/v3.1.1/nrf/sysbuild/CMakeLists.txt:825 (include)
>   cmake/modules/sysbuild_extensions.cmake:598 (nrf_POST_CMAKE)
>   cmake/modules/sysbuild_extensions.cmake:598 (cmake_language)
>   cmake/modules/sysbuild_images.cmake:46 (sysbuild_module_call)
>   cmake/modules/sysbuild_default.cmake:21 (include)
>   D:/ncs/v3.1.1/zephyr/share/zephyr-package/cmake/ZephyrConfig.cmake:75 (include)
>   D:/ncs/v3.1.1/zephyr/share/zephyr-package/cmake/ZephyrConfig.cmake:92 (include_boilerplate)
>   D:/ncs/v3.1.1/zephyr/share/sysbuild-package/cmake/SysbuildConfig.cmake:8 (include)
>   template/CMakeLists.txt:10 (find_package)
> 
> 
> -- Configuring incomplete, errors occurred!
> See also "D:/Project/peripheral_uart_dfu_1/build/CMakeFiles/CMakeOutput.log".
> ?[91mFATAL ERROR: command exited with status 1: 'D:\ncs\toolchains\c1a76fddb2\opt\bin\cmake.EXE' -DWEST_PYTHON=D:/ncs/toolchains/c1a76fddb2/opt/bin/python.exe '-Bd:\Project\peripheral_uart_dfu_1\build
> ' -GNinja -DBOARD=nrf54l15dk/nrf54l15/cpuapp '-SD:\ncs\v3.1.1\zephyr\share\sysbuild' '-DAPP_DIR:PATH=d:\Project\peripheral_uart_dfu_1'
> ```

#### NCS v2.9.0/v2.9.1/v2.9.2修复

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
>  File "C:\ncs\v2.9.0\zephyr\scripts\list_boards.py", line 469, in <module>
>    dump_v2_boards(args)
>  File "C:\ncs\v2.9.0\zephyr\scripts\list_boards.py", line 416, in dump_v2_boards
>    boards = find_v2_boards(args)
>             ^^^^^^^^^^^^^^^^^^^^
>  File "C:\ncs\v2.9.0\zephyr\scripts\list_boards.py", line 341, in find_v2_boards
>    b, e = load_v2_boards(args.board, board_yml, systems)
>           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
>  File "C:\ncs\v2.9.0\zephyr\scripts\list_boards.py", line 230, in load_v2_boards
>    b = yaml.load(f.read(), Loader=SafeLoader)
>                  ^^^^^^^^
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

### (5) Windows环境清理git状态

> 【注意】2025.10.14开始，nrfutil sdk-manager v1.8.0已经修复了此问题。如果你是用最新的nrfutil安装的NCS，此问题应该不会存在。VS Code extension也是自带nrfutil sdk-manager的。
>
> 解决方案是nrfutil会在SDK解压安装时，自动把所有.git记录修改，直接增加了`core.filemode = false`

<details>
    <summary>[点击展开]</summary>
预打包（Pre-packaged）方式有个bug。那就是SDK是在Linux环境下打包好的，在Windows下解压，会出现部分文件的权限从755强制转换为644，导致git状态不是clean：

![image-20250727164656643](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/8671cc395bf5de759f4ef80b0cbc20a4.png)

![image-20250727164717632](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/7957c29ba730bca0d3a49a98b30a3a98.png)

并且，我实测在git全局配置忽略文件权限的变化也没用。必须在每个git子仓库都忽略文件权限的变化：

打开nRF Connect命令行：

![image-20250205000107113](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/8f02cfc623694bbb710701a565fb9a6a.webp)

进入SDK根目录，执行以下内容：

```powershell
# set for all repo:
west forall -c 'git config core.filemode false'

# set for all sub modules:
west forall -c 'git submodule foreach --recursive git config core.filemode false'
```

这是给NCS的每个代码仓库，以及每个仓库的子仓库都递归执行`git config core.filemode false`，从而忽略文件的变化。

处理完毕后，Git状态变干净了：

![image-20250727170510324](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/95f8f2ee93ed55a849d0f6a5e269d961.png)

</details>

## 3.2. 命令行环境

下一步手动拉取SDK的方式，需要此命令行环境。

此外，如果你需要无GUI的命令行编译环境，也是用此方法进入环境。

### 方法1：通过VS Code打开NCS命令行环境

![image-20250205000107113](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205000107113.webp)

![image-20250205000139731](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205000139731.webp)

### 方法2：直接从命令行切换到NCS环境

对于没有显示器的服务器环境，或者脚本中需要使用工具链的情况，可以用nrfutil实现。

准备nrfutil：

```powershell
## 确保已经安装nrfutil，并添加到环境变量。
## 并且已经安装了nrfutil toolchain-manager
#  nrfutil search
#  nrfutil install toolchain-manager

# 首先，如果前面安装toolchain时，没有安装到默认路径，此处需要设置你的安装路径
nrfutil toolchain-manager config --set install-dir=D:\Project\ncs
 
# 检查nrfutil是否找到工具链
 nrfutil toolchain-manager list
 
Version  Toolchain
 * v2.9.0   D:\Project\ncs\toolchains\b620d30767
```

 直接进入一个带有toolchain作为path的shell环境
 ```powershell
 # Windows PowerShell
nrfutil toolchain-manager launch --ncs-version v2.9.0 -- powershell
 
 # Windows CMD
 nrfutil toolchain-manager launch --ncs-version v2.9.0 -- cmd
 
 # 进入后，可用env命令检查环境变量
 env
 ```

![image-20250727170711908](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/7c5b1ac9ca1f813380f58a6bfdb4a396.png)

```bash
 # Linux下必须使用--shell参数
 nrfutil toolchain-manager launch --ncs-version v2.9.0 --shell
```

进入环境后，我们执行`west --help`，会发现是没有烧录（flash）、编译（build）这些命令的。

需要再手动设置`ZEPHYR_BASE`临时环境变量，使其指向“NCS目录下的zephyr目录”。

```powershell
# Windows
$Env:ZEPHYR_BASE="D:\ncs\v2.9.0\zephyr"
```

```bash
# Linux
export ZEPHYR_BASE="${HOME}/ncs/v2.9.0/zephyr"
```

然后就可以使用SDK中的扩展命令了：

![image-20250727171046110](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/ebe988e38f4afe0a8d6214a61b154162.png)



## 3.3. 方式二：手动拉取或者更新SDK

手动拉取是从GitHub拉取。无法受到国内镜像源加速。确保你能稳定访问GitHub并拉取仓库再安装。

> ![image-20251019172612233](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedcc562f37c016c0fa4886687e93e7727b.png)
>
> ![image-20251019173045929](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined7b2c76779ac234225eaa29ee3e992833.png)
>
> NCS托管在GitHub，由多个仓库组成：https://github.com/nrfconnect。其中既有Nordic自己的代码仓库，也有开源仓库的Fork副本。
>
> Nordic会持续开发优化，并贡献给开源社区，同时也从开源项目获取新功能。
>
> 其中，主仓库是sdk-nrf。主仓库的版本就是NCS版本。每个主仓库中会通过`west.yml`文件记录其他子仓库的GitHub地址和版本，这样就可以用`west`命令拉取。
>
> 此外，一些私有仓库（如Apple FindMy，Garmin ANT+ 这些需要相关授权才能使用的私有仓库）在`west.yml`中是默认禁用的。只有你在获得了相关公司的授权，并获得了相应的GitHub私有仓库访问权限时，才能在NCS中拉取到对应的仓库。

在刚刚打开的**nRF Connect命令行**中，找到想要安装SDK的位置，执行以下步骤：

![image-20250205005413929](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205005413929.webp)

### (1) 拉取主仓库

新安装SDK：

```powershell
# 进入到toolchain安装的父目录，默认C:\ncs，或者${HOME}/ncs/
cd D:\Project\ncs

# 创建并进入SDK文件夹
mkdir v2.9.0
cd v2.9.0

# 初始化仓库（从github拉取对应Tag的主仓库）
west init -m https://github.com/nrfconnect/sdk-nrf --mr v2.9.0
```

> - 这一步等价于`git clone`，并创建`.west`配置文件夹
> - 在执行`west`命令时，`west`会在当前目录和父目录中递归向上寻找`.west`文件夹，并使用其中的配置。因此千万不要乱搞在硬盘根目录创建什么`.west`文件夹，会导致整个盘都出问题，无法使用west。
> - 这一步如果下载失败想重新下载，**需要把创建的v2.9.0文件夹下的所有内容删除干净**，尤其是`.west`隐藏文件夹。然后再次执行前面的`west init ...`即可

![image-20250205005309635](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205005309635.webp)

### (2) 拉取其他子仓库

```powershell
# 主仓库已经拉取完毕，拉取其他子仓库，直接在当前目录下执行
west update
```

> 由于国内网络DNS污染的原因，这一步也经常失败，但是没关系，每次`west update`都能下载一点点，如果失败了，就重复`west update`就行了。不需要像`west init`失败一样删除干净重新下载。
>
> 可以用个脚本循环执行，直到west update无报错。

### (3) 导出Zephyr CMake package

```powershell
west zephyr-export
```

### (4) 后续更新和切换SDK版本

SDK通过git管理的好处是，你可以方便地切到新版本或者老版本。当然，如果你硬盘够大，把所有要用的SDK都分别安装也可以。

注意此方法**只能切换SDK，各个版本的toolchain还是需要单独安装**。

按照以下步骤操作：

1. 确保SDK中的git仓库状态均为Clean

这意味着，**开发者平时不要随便去改SDK中的任何代码**。但是编译例程是没问题的，因为例程的默认编译目录`build/`是被`.gitignore`忽略掉的。

```powershell
# 此命令可查看当前git仓库的状态
git status
```

但是NCS中的仓库很多。也可以用VS Code打开整个NCS，用git界面图形化查看是否每个仓库均为clean。

2. 检查manifest有无新版本

NCS中，nrf为主仓库，nrf的版本即为整个SDK的版本

```powershell
# 查看nrf仓库下有多少版本
cd nrf
git pull
git tag  # 按键盘上下键翻阅，按q退出
```

3. 切换到自己想要的版本

```powershell
# 检出想要的主仓库nrf版本
git checkout v3.0.0

# 更新nrf之外的整个NCS仓库
west update
```

# 4. 打开一个例程

从VS Code 的一个全新窗口，选择**打开文件夹**：

![image-20221209103137554](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221209103137554-1731044874928-20.webp)

<center>或者：</center>

![image-20221209103240455](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221209103240455-1731044874929-21.webp)

打开整个SDK目录，这样做是为了**看代码跳转时，SDK中的代码也能跳转到**：

![image-20250205012245435](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205012245435.webp)

然后在VS Code中再打开一个例程：

![image-20250205012416141](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205012416141.webp)

我们选择`v2.9.0\nrf\samples\bluetooth\peripheral_uart`

![image-20250205012602448](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205012602448.webp)

编译例程参考后续章节。

> 注意Windows有最大路径名长度限制。对于一些比较深的例程，再叠加上build目录下还有源码层级结构，导致编译会失败。解决方法可以参考下一章节“以例程为模板创建新工程”，并把工程放到更浅的路径。

> NCS中所有例程的位置：
>
> ```
> NCS 
> |-- nrf                      
> |   |-- applications/      # Nordic商业级例程
> |   |-- samples/           # Nordic外设、蓝牙、LTE等例程
> |   |-- tests/             # 组件API测试例程
> `-- zephyr
>     |-- samples            # Zephyr Kernel、各类板子、各类传感器芯片例程
>     `-- tests              # 组件API测试例程
> ```
>
> `zephyr/samples/`中有RTOS的组件例程、Zephyr支持的各类厂商的板卡例程、各类传感器的例程等，其中也有蓝牙例程。
>
> `zephyr/tests/`中有**全部的**API测试例程。
>
> `nrf`仓库的目录结构仿造`zephyr`仓库，也有`samples/`和`tests/`目录。`samples/`中有Nordic提供的软件库例程、Zephyr未收录的例程（如 nRF9160的LTE）等。

# 5. 以例程为模板创建新工程

上一节讲解了如何**打开**一个例程。

如果我们只是打开例程，例程的文件夹还是在ncs仓库内部，受到 ncs 的 git 仓库的管理。如果想自己开发项目，用git管理自己项目的版本，就需要**创建**新工程。

NCS支持把例程当作模板，复制到NCS外部，并创建新工程。

> 新建工程还有一个用处：**Windows上有目录名长度限制**。在一些路径比较深的例程里进行编译时，会出现长度不足导致编译系统报错找不到某个SDK文件的情况。因此，把例程作为模板拷贝到比较浅的目录中进行开发，可以避免此问题。
>
> Linux，MacOS则没有这个问题。

## 5.1. 创建新工程

NCS支持以例程作为模板，复制并创建新的工程。这也是Nordic非常推荐的方式。

首先在VS Code中打开一个新窗口

![image-20231027154653607](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231027154653607-1731044874929-24.webp)

在 VS Code中，选择左侧nRF Connect for VS Code插件，进入Welcome页面，先检查toolchain和SDK是否已经检测到。

然后点击`Create a new application`创建新工程。

![image-20250205012805758](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205012805758.webp)

选择“Copy a sample”

![image-20250205012842271](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205012842271.webp)

选择自己想要拷贝的例程，支持文字搜索：

![image-20250205012920701](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205012920701.webp)

>这里的例程列表，和第4节中提到的目录结构是一致的。同时也和NCS官网的例程说明文档是保持一致的，下图位置打开官网文档：
>
>![image-20250205013013188](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205013013188.webp)
>
>Nordic商业级应用：https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/applications.html
>
>Nordic例程：https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/samples.html
>
>Zephyr例程：https://docs.nordicsemi.com/bundle/ncs-latest/page/zephyr/samples/index.html
>
>此外，还有一些模块的例程不会出现在这个界面，但是可供参考：
>
> - `${NCS}/modules/hal/nordic/nrfx/samples/src/`： NRFX外设驱动库例程。如果用户不想用、或者Zephyr没有提供某些外设的标准驱动，则可以使用NRFX驱动，其用法和老的nRF5 SDK基本一致。
> - `${NCS}/zephyr/tests`：zephyr所有的API的测试用例。如果你不知道某个Zephyr API怎么用，可以从这里面找。

选择自己新建工程的位置，注意**Windows上，新建工程必须和SDK在同一个磁盘**：

![image-20250205013142630](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205013142630.webp)

然后就可以打开新的工程。

## 5.2. 添加Workspace

这样的独立工程是可以编译的，但是后续编译完，看代码时，按Ctr+鼠标左键跳转的代码在SDK内部，就无法跳过去了。所以，需要把SDK和当前工程添加到同一个VS Code Workspace中。

选择添加文件夹到 Workspace

![image-20250205013547421](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205013547421.webp)

直接把整个NCS和当前工程添加到同一个Workspace中：

![image-20250205013658240](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205013658240.webp)

保存当前workspace：

![image-20250205013723666](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205013723666.webp)

下次打开时，只需双击workspace文件，就能直接打开当前workspace（含工程目录+SDK）

![image-20250205013906343](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205013906343.webp)

最后记得修改`.gitignore`文件，这样你和其他人协助开发时这些文件就各自使用自己电脑上的配置，不会互相干扰：

![image-20250205013949727](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205013949727.webp)

## 5.3. 清理Workspace插件

可能你的VS Code里还安装了其他厂商的插件，以及一些通用插件。开发NCS时，这些插件不断弹窗报错，非常烦人。

这时你可以用VS Code的workspace功能来局部关闭这个插件。

目前版本NCS的插件包只需要这六个插件：

![image-20250512170309135](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250512170309135.png)

![image-20250512170323334](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250512170323334.png)

因此你在workspace里可以关掉其他的插件。举例来说，微软的`CMake Tools`插件会一直弹窗询问CMake根目录文件在哪里：

![image-20250512170510620](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250512170510620.png)

我们不需要它来帮助解析CMake。直接在插件页面单独关掉它：

![image-20250512170600781](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250512170600781.png)

这样，在当前workspace，这个插件就被关闭了。同理其他厂商的插件也可以这样关闭。如此一来，在当前workspace开发NCS，你不再会受到这些插件打扰。同时，在其他workspace，你也可以继续正常使用那些插件。

## 5.4. 使用git跟踪你的代码修改

<details>
    <summary>展开查看</summary>

> 如果你从没用过git，需要先配置用户名和邮箱。这个用户名和邮箱不是登陆什么网站用的，而是一个签名，在提交代码时用于标记这段代码是谁提交的。这个配置存在你电脑的本地，并且是**全局**的，对所有git仓库都有效。
>
> ```bash
> git config --global user.name "Jayant.Tang"
> git config --global user.email "jayant.tang@nordicsemi.no"
> ```

新建的工程都会自动初始化git仓库，我们可以看到.gitignore文件：

![image-20231027155922698](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231027155922698-1731044874930-31.webp)

你可以把`.vscode/`添加到其中

如果你不熟悉Git以及Git在VS Code中的使用，强烈建议去学习一下，它极大的方便了代码的管理。

例如：如果安装了git history插件，就可以查看提交历史：

![image-20221122235338251](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221122235338251-1731044874930-32.webp)

Git History提供了很方便的视图，可以看到每次commit都改动了哪些代码和配置（左侧是旧的，右侧是新的）：

![image-20221122235416865](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221122235416865-1731044874930-33.webp)

​	更多Git的使用，可以去网上了解其他教程。本文不再赘述。

</details>

# 6. 编译工程

## 6.1. 创建一个编译目标（Build Target）

所谓编译目标就是在同一套代码下，可能有不同的配置项（Debug/Release，不同的优化级别等等），编译出不同的可执行文件。一个项目下可以创建多个编译目标。

![image-20250205014115409](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205014115409.webp)

### Toolchain和SDK版本

在build界面设置Toolchain和SDK版本：

![image-20250205022811532](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205022811532.webp)

> 目前在Build界面设置，可以让同一个工程用不同的环境进行编译，测试区别。之前的VS Code版本，是在Welcome界面全局设置Toolchain和SDK版本。注意这个改动比较大。

### Board Target

创建Build时，需要选择自己使用的板子，Zephyr自带许多厂商的开发板配置。

下图中，Board target下拉框是用来选板子的，下方还有三个**过滤器**，来过滤可选的板子：

- Compatible boards：本例程适配的板子，如果选择这些板子，**不需要任何修改就可以烧录进去使用**

- Nordic SoC：使用了Nordic SoC的板子，可能是一些demo板或第三方板子

- Nordic Kits：Nordic 出品的官方开发板
- All boards：Zephyr中所有的板子

![image-20250205023002380](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205023002380.webp)

>Zephyr Board target 配置的命名规则：
>
>![image-20250205023618902](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205023618902.webp)
>
>例如：`nrf52840dk/nrf52840`，是说这个target是为 nRF52840DK 这块开发板上的 nrf52840 这颗 MCU 创建的。Board Target的配置文件会记录这个MCU的外设地址，以及此MCU连接的外部硬件的信息（如SPI Flash）。
>
>例如：`nrf9160dk/nrf9160`和`nrf9160dk/nrf52840`，都是nRF9160DK这块开发板的配置。但是这块开发板上有两颗MCU/SoC，一颗是9160 SiP，另一颗是52840。所以有两个配置可选，分别为这两颗MCU/SoC编译固件。
>
>例如：`nrf5340dk/nrf5340/cpuapp`和`nrf5340dk/nrf5340/cpunet`，都是nrf5340dk这块板子的配置，并且这块板子上只有nRF5340这一颗主控。但是nRF5340是一颗双核MCU，所以，可以有两种配置来区分两个核。这两个核的固件是分开运行的，因此编译时也是分别编译的。
>
>例如：`nrf5340dk/nrf5340/cpuapp`和`nrf5340dk/nrf5340/cpuapp/ns`，都是nrf5340dk开发板上，nrf5340芯片的应用核的配置。但是，这颗应用核使用的CPU是Cortex-M33，基于Arm V8架构，提供了TrustZone的安全保护技术，同样的一个外设寄存器，可以有安全（Secure）和非安全（Non-Secure）两个地址，这样可以把安全应用和非安全应用隔离开来。因此，这两个board配置的不同之处，就是从安全地址还是非安全地址去访问芯片上的外设资源。
>
>例如：`nrf52833dk/nrf52820`。这块开发板上只有nrf52833这一块主控。但是由于nRF52833和nRF52820同属nRF52系列，52820上的资源是52833的子集，并且Nordic并未单独为52820制作开发板，因此可以用52833来模拟52820。此配置文件限制了52833上的硬件资源，使其表现和52820相同。
>
>更详细的信息牵扯到DeviceTree，可参考：[《理解Zephyr编译与配置系统》](https://jayant-tang.github.io/2022/12/2a39e705bff0/)有关Boards的章节。
>
>NCS v2.6.x之前，采用的是根据SoC架构来分类板子的方式，那时候板子名称都是独立的，用下划线连接：如`nrf52840dk_nrf52840`。
>
>NCS v2.7.0开始，采用了Zephyr Hardware Model v2，才产生这个区别。
>
>在CMake中，有以下变量可以获取板子信息：
>
>```cmake
># Board name,如nrf52840dk
>${BOARDS}
>
># Board qualifiers，如/nrf5340/cpuapp
>${BOARD_QUALIFIERS}
>
># 完整的Board target，如nrf5340dk/nrf5340/cpuapp
>${BOARDS}${BOARD_QUALIFIERS}
>
># 转换为下划线的格式，如nrf5340dk_nrf5340_cpuapp
>${NORMALIZED_BOARD_TARGET}
>```

### 配置文件

各种配置文件、追加配置文件，可参考[《理解Zephyr编译与配置系统》](https://jayant-tang.github.io/2022/12/2a39e705bff0/)：

![image-20250205025318126](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205025318126.webp)

### 编译选项

![image-20250205025414518](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205025414518.webp)

可以设置Build目录，优化等级等等。Sysbuild可参考[《理解Zephyr编译与配置系统》](https://jayant-tang.github.io/2022/12/2a39e705bff0/)，v2.7.0后默认使用sysbuild。

## 6.2. 进行编译


新建完build target后，点击Build Configuration进行编译。


![image-20250205031140383](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205031140383.webp)

如果后续要再次编译这个target，可以在APPLICATIONS栏选中自己要构建的工程和target。然后在ACTIONS栏通过build**按钮**进行项目的构建。

> 按Build旁的圆圈箭头按钮，可以全部重新编译。

![image-20250205031114268](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205031114268.webp)

## 6.3. 命令行编译

补充：命令行编译

按 " CTRL + ` "，可以呼出终端。点击“+”号右边的下拉箭头，选择nRF Connect：

![image-20231027161338719](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231027161338719-1731044874931-36.webp)

这样打开的终端，其环境变量指向前面安装的toolchain。

编译命令示例：

```bash
west build -b nrf52840dk/nrf52840 -d build -p -- -DCONF_FILE="prj.conf"
# -d 指定编译目录为./build
# -b 板子为nrf52840dk/nrf52840
# -p 表示pristine build,全部重新编译。
# 在--之后可以添加CMake选项。如-D表示设置CMake变量。
#   -DCONF_FILE等价于在CMakeLists.txt中写 set(CONF_FILE prj.conf)
#   更多CMake配置文件选项，参考https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/app_dev/config_and_build/cmake/index.html#providing_cmake_options
```

更多用法：

```bash
west build -h
```

## 6.4. 编译输出文件

一个工程可能有多个固件，这里以Matter窗帘举例。有Bootloader和application。

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

nrf-connect插件，底层调用的是`nrfjprog`或`nrfutil`命令来连接开发板上的JLink。因此，需要通过USB线连接到JLink口。

![image-20221209144123203](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221209144123203-1731044874931-37.webp)

以nRF52840DK为例，中间最大的带有贴纸的芯片为JLink主控（官方称其为Interface MCU），左侧为JLink USB口，此接口可以用来给整块板供电。

需确保左下角电源开关打开。左侧中间位置的开关置于VDD挡位，右上角开关置于DEFAULT挡位（如上图）。

对于一些有多颗MCU的开发板，注意要使用拨码开关选择自己要调试的MCU，例如nRF9160DK可选择9160和52840：

![image-20221209153801993](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221209153801993-1731044874931-38.webp)



​	然后就可以在VS Code中识别到设备了：

![image-20221209144833292](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221209144833292-1731044874931-39.webp)



# 8. 烧录固件

连接并成功识别到Jlink后，可以通过ACTIONS栏中的`Flash`按钮触发烧录动作：

![image-20221123160139273](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221123160139273-1731044874934-42.webp)

​	也可以通过命令行进行烧录:

```bash
west flash
```

> 备注：	
>
> 这样直接烧录，有一部分项目可能会烧写失败，显示：
>
> ![image-20221123160245857](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221123160245857-1731044874934-43.png)
>
> 这是因为，Nordic的MCU中通常都有一个用于存储用户信息的寄存器（UICR），可以认为是一块特殊的flash区域，存储了客户自己的加密密钥、引脚配置等产品信息。由于信息安全的原因，是不允许在保持UICR不变的情况下烧写新的固件的。相关资料，可以参考Nordic芯片数据手册的UICR章节。
>
> 这种情况下只能全片擦除然后再烧录，点击Flash右边的按钮：
>
> ![image-20221123160832598](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221123160832598-1731044874935-44.webp)
>
> 或者使用命令行方式：
>
> ```bash
> west flash --force --erase
> ```
>
> 此外，还有一种可能是，调试接口启用了保护，需要recover这颗芯片来解除保护。
>
> 通常，右下角会有弹窗来问你是否要recover，就选择Yes就好。
>
> 如果没有效果，也可以用命令行来recover
>
> ```bash
> nrfutil device recover
> 
> # or
> nrfjprog --recover
> ```
>
> 如果是nRF5340这种双核芯片，那么网络核也要recover
>
> ```bash
> nrfutil device recover --core Application
> nrfutil device recover --core Network
> 
> # or
> nrfjprog --recover --coprocessor CP_APPLICATION,
> nrfjprog --recover --coprocessor CP_NETWORK
> ```



# 9. 运行并测试

连接的设备，可以看到Jlink上的主控芯片、串口以及RTT。

![image-20231028103135931](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028103135931-1731044874935-45.webp)

这里的串口是MCU上真实的物理串口，在开发板上通过PCB走线连接到Jlink，然后Jlink把这个串口转化为USB虚拟串口。

> 新款开发板，板载的Jlink是拿5340做的，这种新款开发板有两个USB虚拟串口：
>
> ![image-20231027164658632](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231027164658632-1731044874935-46.webp)
>
> ![image-20231027163914699](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231027163914699-1731044874935-47.webp)
>
> 但是对于52840DK来说，开发板上只连了一个串口，另一个是空的。具体是哪个？要去[Nordic官网](https://www.nordicsemi.com/Products/)下载对应开发板的原理图查看。
>
> 或者直接试一下，因为可能USB枚举的顺序不一样。
>
> 对于5340DK, 7002DK来说，两个串口分别对应Application Core和Network Core的日志输出。

## 	9.2. 连接串口

![image-20221209154745021](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221209154745021-1731044874935-48.webp)

​	点击串口，选择波特率，即可打开串口。串口**接收**的信息在Terminal展示：

![image-20231027162835862](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231027162835862-1731044874935-49.webp)

> 这个串口工具类似于Putty，按下键盘的按键就立即发送出去一个字符，不会显示自己发出了什么。便于在这个串口上运行命令行终端之类的，这也是Zephyr所支持的。

## 9.3. 连接RTT

RTT是Segger提供的日志调试手段，全称Real Time Transmit。MCU将日志打印到内部缓存中，然后利用Jlink的高速通道，把日志打印到电脑上。这个方法不需要占用串口外设，而且速度极快，对CPU运行影响小。

> **大多数例程的默认日志输出是串口**。但本例程是蓝牙串口透传，串口需要传输用户数据，因此在本例程中日志的默认输出就已经是RTT了，无需再配置RTT。
>
> 要查看RTT日志输出的相关配置，打开工程根目录下的`.prj`文件：
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

如下图连接RTT：

![image-20221209170245563](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20221209170245563-1731044874935-51.webp)

## 9.4. 测试peripheral_uart例程

一般来说，需要两块开发板，一块烧`peripheral_uart`，一块烧`central_uart`。两块开发板上电后会自动连接。从一个开发板串口输入的数据，会从另一个开发板输出。

但是这里我们只有一块开发板，那么BLE central我们就用手机。iOS应用商店可以下载`nRF Connect`，安卓可以在谷歌商店下载，或者直接去Github下载[APK](https://github.com/NordicSemiconductor/Android-nRF-Connect/releases)。

### 通过BLE连接设备

在nRF Connect APP中，先scan搜索附近蓝牙。scan按钮一开始是三角形，点击开始扫描后，变成方形。
扫到设备后，再连接：

![image-20231028104626601](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028104626601-1731044874935-52.webp)

### 开发板接收数据

![image-20231028104717740](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028104717740-1731044874936-53.webp)

![image-20231028104734696](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028104734696-1731044874936-54.webp)

可以在串口看到数据：

![image-20231028104845188](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028104845188-1731044874936-55.webp)

### 开发板发送数据

BLE协议是Client-Server架构。BLE协议规定，从机作为Server，只能被Client读、写上面的属性。默认情况下不能主动发消息到Client。除非Client使能了Notify的功能，Server才能Notify到Client。更多信息，大家可以搜索CCCD(Client Characteristic Configuration Descriptor)。这里，就需要点亮TX属性的CCCD：

![image-20231028105348055](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028105348055-1731044874936-56.webp)

然后在串口中通过键盘输入内容：hello+回车。屏幕上不会显示东西，但是按键确实会发送出去。

> 这个串口工具类似于Putty，按下键盘的按键就立即发送出去一个字符，不会在屏幕上显示自己发出了什么。
>
> 这里之所以要加回车，是因为例程代码就是这么写的。在串口回调函数内，检测到回车，才会把串口数据打包从蓝牙发出。

![image-20231028105643833](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028105643833-1731044874936-57.webp)

至此，我们完成了在nRF52840DK上的`peripheral_uart`例程的编译、烧录与运行测试。


# 10. 阅读代码、跳转与搜索
当一个工程编译完毕后，工程中的函数与变量、Kconfig配置、设备树都是可以ctrl+鼠标左键点击跳转到定义的。为了能够跳转和搜索到SDK中的代码，记得按照前面第5.2小节的方法，把NCS和当前工程添加到同一个Workspace中。

然后，就可以在nRF插件中进行浏览了：

![image](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/3028998-20241029123918141-1203491295.webp)

Source File中是所有参与编译的源码。其中Application下的是当前工程中的源码；nRF Connect SDK下的是NCS中参与编译的源码（不参与编译的不会在里面）；Generated下是工具链自动生成的一些代码（中断向量表、Kconfig转换成宏等等)。

由于我们前面已经把SDK放进了VS Code workspace，所以可以直接搜索代码：

![image](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/3028998-20241029124509412-1982218675.webp)

点击上面的搜索按钮后，会自动跳转到VS Code搜索界面，并且已经自动填充好文件搜索范围：

![image](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/3028998-20241029124636177-436976402.webp)

> 这个功能在Windows上不好用，因为搜索范围过滤条件太多时，Windows会无法处理

在浏览和搜索的过程中，时刻注意自己选中的是整个工程的Build Target还是子工程的Build Target

![image-20250205032032135](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205032032135.webp)

以免影响后续的编译情况。

# 11. NCS Add-Ons

nRF Connect SDK (NCS) Add-ons 是一个公开可用的补充组件索引，旨在扩展 nRF Connect SDK 的功能。

**功能与内容**：Add-ons 提供了 SDK 标准包之外的多种功能，包括蜂窝应用程序（如Asset Tracker、Serial Modem）、驱动程序、库、协议实现（如 Amazon Sidewalk、Zigbee、ANT+）以及特定技术的完整 SDK。

**独立性**：Add-ons有独立的发布周期，这使得新库可以更灵活地更新，而无需等待 NCS 主版本的发布。

官网见：[nRF Connect SDK Add-ons](https://nrfconnect.github.io/ncs-app-index/)

![image-20260111154308952](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined2b98a862c307f982e2bebbeffc1df0e0.png)



# 12. Nordic AI问答机器人

TechDoc和DevZone网站右下角都有Ask AI按钮：

![image-20251016104023585](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedee789e16c4911ac10e4d99c1eb4edc9a.png)

国内目前需要科学的上网才能使用。

AI训练了所有的Nordic官网资料，以及DevZone论坛中的帖子。可以用中文问他：

![image-20250205032554493](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250205032554493.webp)

# 13. 官方资料

## Nordic TechDocs资料中心

https://docs.nordicsemi.com/

目前最新的资料中心，可以通过技术或产品系列进行分类，查找想要的资料。芯片数据手册（Specification）、开发板说明都可以在这里查看。
![image](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/3028998-20240618103459443-1837528620.webp)

**记得进入NCS文档后，第一步先选择文档的版本与自己使用的NCS版本一致：**
![image](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/3028998-20241029114423094-1941812085.webp)

从2024.6.18开始，NCS官网和Infocenter都会下线。所有开发资料都会集中在TechDocs。上图中我们可以看到，除了各个产品系列的介绍之外，下方有nRF Connect SDK和老的nRF5 SDK的资料，点击跳转进去即可。

关于文档的结构，可以展开下面章节中被折叠的信息来了解。

## NCS官网
**此网站已于2024.6.18被Nordic资料中心替代**
<details>
    <summary>展开查看</summary>

https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/index.html

![image-20231028162512499](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028162512499-1731044874936-58.webp)

进入官网，首先看到右上角可以选择文档的版本，需要与SDK的版本对应。

然后可以看到中间的一排标签页：

- **Zephyr Project**：是[Zephyr官方文档](https://docs.zephyrproject.org/latest/index.html)的一个镜像，包含Zephyr RTOS内核服务、操作系统API、各种驱动、协议支持以及它们的例程文档。一些比较通用的功能的如日志、Flash存储、线程间通信等功能的文档都在这里面。它对应的是NCS中的`zephyr`文件夹。

- **nRF Connect SDK:** 是Nordic在Zephyr系统上扩展的各种Nordic独有的库、驱动和例程的文档。里面大多数是一些Nordic独有的技术，对应的是NCS中的`nrf`文件夹。
- **nrfx与nrfxlib**：Nordic的外设驱动库，是最接近寄存器操作的一层，和目前已经停止维护的的nRF5 SDK中的nrfx几乎是一样的。在Zephyr中，通常应用层只需调用Zephyr的标准API，Nordic提供的底层驱动会把nrfxlib和一些寄存器操作封装成Zephyr的标准API。通常，只有客户在对MCU外设功能进行较为深入的开发时，会参考到这一块的文档。
- **MCUboot**：MCUboot是一个开源的第三方安全bootloader，支持很多系统和平台，Zephyr只是其中之一。很多支持OTA的例程基本都是使用MCUboot
- **Trust Firmware-M**：ARM提出了**平台安全架构（Platform Security Architecture, PSA）**，意思就是说，客户自己开发软件容易有安全漏洞，因此运行环境应分为**安全环境（SPE）**和**非安全环境（NSPE）**。客户开发的程序，属于非安全环境。安全环境的程序，由厂商提供，主要提供一些安全存储、安全启动之类的API给客户的非安全环境来调用。Trust Firmware-M(TFM)是安全环境的一个样板固件。 如果你使用了nRF5340或者nRF9160这种带有ARM v8架构的主控平台，则在编译选板子时，都可以看到`_s`或`_ns`后缀。`_s`的意思是说，客户直接在安全环境开发程序，安全性全由客户自己掌控。`_ns`的意思是说，客户在非安全环境开发程序，编译时，Zephyr会自动把TFM一起编译进去，和客户的应用程序一起工作。对于9160来说，由于要和蜂窝modem进行交互，因此，牵扯到蜂窝网络操作的例程，都必须选择`nrf9160dk_nrf9160_ns`。
- **Matter**：Matter是智能家居的新标准，目的是打破厂商之间的壁垒，实现生态融合。从连接方式上讲，Matter是基于局域网IPv6的，因此，Wi-Fi和Thread都是可以作为Matter的底层的。从配网方式上讲，Matter通过BLE来传输认证信息，此外可以通过NFC或者二维码的方式，让手机快速的找到要配网的这个设备的BLE广播。此页面主要是Matter SDK的文档，并不局限于在Nordic MCU上进行开发。如果要找Matter在Nordic产品上运行的例程，还是要去nRF Connect SDK页面的Samples目录下去寻找。
- **Kconfig**：Zephyr系统中有大量的Kconfig配置，Nordic扩展的库、驱动中也有大量Kconfig配置。如果你不知道一个Kconfig配置是干什么的，可以在这个页面进行搜索。

总之，NCS官网里面有大量的技术细节，在运行一个例程之前，一定要参照网站中该例程的说明进行操作。
</details>

## Nordic旧版资料中心(Info Center)

**此网站已于2024.6.18被Nordic资料中心替代**
如果要查询老的nRF5 SDK资料，看：https://docs.nordicsemi.com/bundle/sdk_nrf5_v17.1.0/page/index.html

<details>
    <summary>展开查看</summary>
![img](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined42619617e45686e87128a59ce57abffd.png)

也可以下载到芯片数据手册（Specification）、开发板说明、技术白皮书等。这里也有目前已停止维护的nRF5 SDK的文档。
</details>

## Nordic官网

https://www.nordicsemi.com/

一些商业新闻和产品介绍。但是最重要的是一些**工具软件**、**开发板原理图/PCB/BOM**之类，需要在这里下载。

例如：

**nRF52840DK开发板默认例程、Jlink固件、原理图等**：https://www.nordicsemi.com/Products/Development-hardware/nRF52840-DK/Download?lang=en#infotabs



## DevZone开发者论坛

https://devzone.nordicsemi.com/

有问题可以在上面搜索，也可以用英文提问。每天都有原厂support team查看问题并回复。Nordic注册客户，还可以提交private ticket，解决一些与代码、板子有关的问题，也可以审核PCB。



## Nordic DevAcademy官方课程

https://academy.nordicsemi.com/

类似于慕课的网站，目前有NCS，BLE、Wi-Fi、Cellular等课程。有视频结合题目，适合英文好的读者去学习，是非常适合入门的课程。

# 14. 其他推荐阅读

- [理解Zephyr编译与配置系统](https://jayant-tang.github.io/2022/12/2a39e705bff0/)
- [详解Zephyr设备树（DeviceTree）与驱动模型](https://jayant-tang.github.io/2023/03/4b274a50e575/)
- [Zephyr设备树与驱动应用实战——串口](https://jayant-tang.github.io/2023/11/4c8e1d7d162d/)
- [不想用Zephyr DeviceTree？试试nrfx API](https://jayant-tang.github.io/2023/11/1349f878e408/)
- [Nordic GPIO硬件原理与NCS应用详解](https://jayant-tang.github.io/2024/01/b74491c1a080/)
- [Nordic Matter开发与例程详解](https://jayant-tang.github.io/2025/01/5645a5cab10c/)
- [nRF9151蜂窝模组简介与定位例程解析](https://jayant-tang.github.io/2025/04/f1f289c546d9/)