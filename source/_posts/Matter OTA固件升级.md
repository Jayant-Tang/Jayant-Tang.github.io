---
title: Matter OTA固件升级
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2025-10-20 16:02:54
cover: null
tags:
- Nordic
- Matter
categories:
- Matter
typora-root-url: ./..
cnblogs:
  postId: '19153505'
  url: https://www.cnblogs.com/jayant97/articles/19153505
  lastPublishedAt: '2026-07-06T18:20:52+08:00'
  sourceHash: sha256:ee12a5730a46db1d01fc9dae06f8697e08f4a7826af4f96f98f1bc554b292c97
  status: imported
  postType: Article
---

# 1. 简介

本文介绍的是通用的Matter OTA操作，使用 `chip-tool` 和 `chip-ota-provider-app` 命令行工具进行测试，在Nordic nRF Connect SDK和Nordic开发板上实现。

>  Nordic也在Matter例程上支持普通的蓝牙或者串口DFU，使用的是MCUMgr和SMP，本文不涉及那部分。感兴趣参考[《官方文档》](https://docs.nordicsemi.com/bundle/ncs-latest/page/matter/nrfconnect_examples_software_update.html#device_firmware_upgrade_over_bluetooth_le_using_a_smartphone)。
>
> 只有一个建议：官方文档中使用的命令行串口DFU工具[mcumgr]()写得不好，每次发包间隔sleep了20ms，传输很慢，还要装Go环境。建议换成这个Rust写的命令行工具[mcumgr-client](https://github.com/vouch-opensource/mcumgr-client/)，直接是可执行文件不用装环境，且速度很快。

Matter的OTA分为两个角色：

- OTA Requester：一般就是Matter设备（accessories）。
- OTA Provider：用来提供Matter升级固件的设备，比如苹果的HomePod音箱。

![Matter OTA roles](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined64b9744dc4754608c1aa9b547fcf1a25.svg)

OTA Requester 可以定期从同一个Matter网络（Fabric）的OTA Provider查询是否有新固件升级。

OTA Provider可以从[DCL](https://jayant-tang.github.io/2025/09/daaf6f53cdc2/#DCL)获取新固件的URL链接，然后在本地缓存固件。当OTA Requester请求新固件时，就通过Matter网络（指IPv6）传输给它。

![Parties to the Matter OTA process](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined4d6f79b9311af24499501a487320f7de.svg)

> 注意这里DCL是不存储固件的，而是只存储固件的URL。因此厂商还需要有一个公开的服务器来存放升级固件。厂商还要负责把固件URL发布到DCL，可以参考[Google Developer的Matter文档](https://developers.home.google.com/matter/ota/release?hl=zh-cn#release_an_ota_image_using_the_dcl)。

此外，OTA Provider和Matter Controller不一定是同一台设备。只要它们在同一Matter网络即可。

## Matter OTA流程图

![Matter OTA流程图](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinede21e0f457c50eeeab49a24b9481de75d.png)

# 2. 本地OTA测试

## 2.1. 准备环境

**方案一：**

- x64 Linux环境：同时运行`chip-tool`和`chip-ota-provider`，并且自带OTBR
- 运行Matter例程的Nordic开发板1块

![image-20251020172415027](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined1bd6293fe6390b9730f1151a4fa46d24.png)

**方案二（暂未验证）：**

- 树莓派：运行OTBR和`chip-tool`
- x64 Linux环境，必须和树莓派位于同一网段，互通IPv6和mDNS。无需OTBR，只运行`chip-ota-provider`
- 运行Matter例程的Nordic开发板1块

![image-20251020185835648](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined844643f2e355990873ea23dc5afdc272.png)

为了简单，本文会按照**方案一**来进行搭建。直接在Windows11电脑里的WSL2环境中进行测试。环境搭建方案参考：[《在WSL2中搭建Matter CHIP Tool环境》](https://jayant-tang.github.io/2025/09/6376457096fe/)

> 其实**方案一**也可以全部在树莓派中实现。但是Nordic没有提供编译好的aarch64版本`chip-ota-provider`。如果你需要在树莓派中实现，需要在树莓派上自己编译`chip-ota-provider`。

## 2.2. 准备Matter设备和升级固件

### 烧录固件

在nRF Connect SDK中编译完一个Matter例程后，烧录到开发板中作为Matter设备。

可参考：[《Nordic Matter开发与例程详解》](https://jayant-tang.github.io/2025/01/5645a5cab10c/)

### 修改固件版本号

有2种版本号需要修改。必须版本号不同才能升级，其中Matter的版本号必须增大才能升级。

#### （1）Zephyr固件版本号

Zephyr中进行OTA时需要用到的版本号。有两种方式设置：

1. 工程根目录有一个`VERSION`文件，其内容就是版本号：
   ```
   VERSION_MAJOR = 2
   VERSION_MINOR = 5
   PATCHLEVEL = 99
   VERSION_TWEAK = 0
   EXTRAVERSION = dev
   ```

   分别为：主版本号、次版本号、补丁号和可选的 TWEAK 字段。

   - 如果`EXTRAVERSION`不为空，版本号就是：`2.5.99-dev+0`

   - 如果`EXTRAVERSION`为空，版本号就是：`2.5.99+0`

2. 也可以在prj.conf中配置版本号，例如：
   ```
   CONFIG_MCUBOOT_IMGTOOL_SIGN_VERSION="2.5.99+0"
   ```

这个版本号是Zephyr和MCUBoot进行DFU的时候需要检查的版本号。其中`VERSION`文件的配置方式优先级更高，如果`VERSION`文件和`CONFIG_MCUBOOT_IMGTOOL_SIGN_VERSION`配置同时存在，会采用VERSION文件的版本号。

#### （2）Matter版本号

Matter版本号是一个32bit的数字和一个字符串。其中字符串是给人阅读的。

```
CONFIG_CHIP_DEVICE_SOFTWARE_VERSION=33921280
CONFIG_CHIP_DEVICE_SOFTWARE_VERSION_STRING="2.5.99+0"
```

这两个版本号会展示在Matter的Basic Information Cluster中。

数字版本`33921280`的含义是`0x02059900`，对应`2.5.99+0`。但是实际上，没有任何强制要求。不论是Zephyr固件版本，还是Matter数字版本，还是Matter字符串版本。它们之间都没有任何强制的联系。

只要开发者明白这三个版本号表达的是同一个版本就行了，因此为了方便，可以像上面这样定义版本。

> 【注意】
>
> 在进行Matter OTA时，只能升级，不能降级。因此`CONFIG_CHIP_DEVICE_SOFTWARE_VERSION`要变大，最大为`4294967295`（2^32 - 1）

我们在工程中把这些版本号改大，重新编译一下即可：

```
CONFIG_CHIP_DEVICE_SOFTWARE_VERSION=50397441
CONFIG_CHIP_DEVICE_SOFTWARE_VERSION_STRING="3.1.1+1"
```

```
VERSION_MAJOR = 3
VERSION_MINOR = 1
PATCHLEVEL = 1
VERSION_TWEAK = 1
EXTRAVERSION = 
```

### 获得升级后的固件

升级后的固件在build目录下：

- `merged.hex`：用于J-link烧录的，合并bootloader和application的完整固件
- `merged_CPUNET.hex`：双核SoC（例如nRF5340）才有的网络核合并固件，J-link烧录用
- `dfu_application.zip`：进行MCUMgr SMP DFU时需要的升级包

- `matter.ota`：Matter OTA用的镜像

我们这里只需要`matter.ota`

# 3. 进行升级

首先确保chip-tool环境已经启动，见[《在WSL2中搭建Matter CHIP Tool环境》](https://jayant-tang.github.io/2025/09/6376457096fe/)

## 启动chip-ota-provider-app

下载Nordic编译好的`chip-ota-provider-app_x64`工具：[Releases · nrfconnect/sdk-connectedhomeip](https://github.com/nrfconnect/sdk-connectedhomeip/releases)，重命名为`chip-ota-provider-app`，并添加到path环境变量，然后追加可执行权限：

```
chmod a+x ./chip-ota-provider-app
```

准备好前面的升级固件`matter.ota`，

在Linux环境中启动`chip-ota-provider-app`：

```bash
chip-ota-provider-app -f matter.ota
```

## 配网chip-ota-provider-app

然后另开一个命令行窗口，运行`chip-tool`，把`chip-ota-provider-app`添加进Matter网络：

```bash
chip-tool pairing onnetwork 1 20202021
```

> 这里的Node id是`1`，也就是说配网成功后，后面是用这个Node id当作句柄来使用chip-tool控制它。
>
> 后面配网其他Matter设备时，不能用重复的Node id。

进程会占用当前终端一直打印。

## 配网Matter设备

另起一个终端。

我这里是配网一个Matter over Thread设备：

```bash
chip-tool pairing ble-thread 2 hex:0e08000000000001000000030000144a0300000e35060004001fffe002089058d9507229551e0708fd3f0a8f0d5b72650510f84ccfaf2bc84fa9e54860e035b6b940030f4f70656e5468726561642d31386138010218a80410288ad8a6ab55aacf7583788fde4c2ef60c0402a0f7f8 20202021 3840 --bypass-attestation-verifier true
```

> - 注意设备端要开启Matter配网广播。某些例程上电就会开启，某些要按一下button1 (54系开发板是Button0)。
> - 注意node id不要再用相同的，我这里用`2`
> - `--bypass-attestation-verifier true`可以跳过验证DAC证书，我这里只是测试

## 给Matter设备配置OTA Provider

```bash
chip-tool otasoftwareupdaterequestor write default-otaproviders '[{"fabricIndex": 1, "providerNodeID": 1, "endpoint": 0}]' 2 0
```

这里的`2`就是我们要操作的Matter设备，对应上一步配网的设备

## 给OTA Provider配置ACL

```bash
chip-tool accesscontrol write acl '[{"fabricIndex": 1, "privilege": 5, "authMode": 2, "subjects": [112233], "targets": null}, {"fabricIndex": 1, "privilege": 3, "authMode": 2, "subjects": null, "targets": null}]' 1 0
```

这里的`1`就对应我们要操作的`chip-ota-provider-app`进程。

> 在 Matter OTA（设备固件升级）过程中，配置 ACL（Access Control List，访问控制列表）是为了确保只有被授权的节点能够对 OTA Provider（固件提供者）发送命令和进行操作。ACL 是一种安全机制，用于管理和强制执行对节点Endpoint及其相关Cluster实例的访问权限规则。

## 执行OTA

两种方式。如果固件编译时携带了`CONFIG_CHIP_LIB_SHELL=y`，则可以用设备的串口终端命令操作设备来请求ota:

```bash
uart:~$ matter ota query
```

如果没有携带，则可以用`chip-tool`来发起OTA

```bash
chip-tool otasoftwareupdaterequestor announce-otaprovider 1 0 0 0 2 0
```

> 参数：
>
> - Provider Node ID：配网`chip-ota-provider-app`时输入的`1`
> - Provider Vendor ID：测试时直接输入0
> - Announcement Reason：测试时直接输入0
> - Provider Endpoint ID：通常在Endpoint 0
> - Requestor Node ID：配网Matter设备时输入的`2`
> - Requestor Endpoint ID：通常在Endpoint 0

然后就可以看到`chip-ota-provider-app`进程和Matter设备之间在传输固件了：

![image-20251020185143174](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedf51c12f5740b2797075c75afe14ca14e.png)

![image-20251020185121673](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined94625394df759ca243dc503b70190b40.png)

这里网络通道走的是Thread，而不是BLE。过程非常久，接近一个小时，比SMP DFU慢很多，尤其是Thread SSED（Synchronized Sleepy End Device）和ICD（Intermittently Connected Device）模式时，消息交换速度会显著变慢。

但是好在实际场景下不需要用户手机靠近设备亮屏等待升级。

升级完毕后，会打印日志：

![image-20251020193749063](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedef1d4c7f61315b5db4068ebc6dcf57bd.png)

> 注意，在NCS中，Matter升级完毕后会自动调用`boot_write_img_confirmed()`，因此无需再次调用这个函数来让mcuboot确认升级成功。

