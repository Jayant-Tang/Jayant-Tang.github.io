---
title: 在NCS中搭建Matter开发环境
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2023-09-18 11:06:42
cover:
tags:
  - Nordic
  - Matter
  - NCS
categories: Matter
published: false
cnblogs:
  published: false
---

# 1. 前言

Matter是一个基于IPv6的应用层网络协议。在一个智能家居场景中，所有支持Matter协议的产品都可以互相联动，并且可以用苹果、谷歌、三星、亚马逊的App或智能音箱产品控制，从而实现生态的融合。

NCS支持 Nordic产品在 Matter over Wi-Fi 和 Matter over Thread 上的开发。

Nordic提供的各种[Matter例程](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/samples/matter.html)基本都是开箱即用的。在NCS中，选好你想要的例程和所用的开发板，编译并烧录固件，就可以用iOS家庭App把它添加到家庭网络中。当然，谷歌、三星等生态也都是可以的。

但是可能你手头并没有一套苹果HomePod或谷歌音箱等设备，因此缺少Matter主控。另一方面，这些商业产品无法让我们在开发过程中查看通信过程以及Matter协议传输的消息。

因此我们有必要搭建一个不依赖任何手机App或商业智能音箱产品的Matter开发环境。



# 2. 概念

## Matter Controller

Matter Controller是一个Matter节点，它可以控制网络内的其他节点（通过IPv6传输），也负责新设备的发现与入网过程（通过BLE）。苹果HomePod、谷歌音箱等就具有这个功能。

## Thread边界路由器

Thread是基于802.15.4的短距离通信协议（和Zigbee一样），它是Mesh网络，支持UDP/IPv6。Thread边界路由器（Border Router）的作用是衔接Thread网络和外部网络（如以太网、Wi-Fi）。苹果HomePod、谷歌音箱等就具有这个功能。

由于大多数手机和PC基本不支持Thread（iPhone15 Pro支持），因此我们在电脑上搭建Matter Controller时，需要一个额外的“Thread网卡”。



# 3. 搭建Matter over Thread开发环境

有两种方式，第一种是用一个树莓派做边界路由器，电脑上的Matter Controller只需要做Matter over  WiFi和BLE的配网即可。此外它需要一个支持IPv6的Wi-Fi AP：

![Setup with OpenThread Border Router and Matter controller on PC](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined9e934d492a3836f83accca2e40e7e06b.svg)

此外，这种情况下，Matter Controller也可以用安卓手机而非电脑，运行一个安卓端的CHIP Tool即可。

如果你对这种方式感兴趣，参考：https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/protocols/matter/getting_started/testing/thread_separate_otbr_linux_macos.html

另一种方式是在一台PC上同时运行Thread Border Router 和 Matter Controller。这种情况下，PC上需要插一个Thread Radio  Co-Processor，为PC扩展出Thread功能：

![Thread](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined08207a3aab33d7734fa8a14d331c9573.svg)

本文将参考这种方式，原文链接：https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/protocols/matter/getting_started/testing/thread_one_otbr.html

## 3.1. 前期准备

- PC（Ubuntu20.04或更高版本） ，PC需要有蓝牙网卡（支持BLE）
- 一个52840DK或52840Dongle。用作Thread RCP （Radio Co-Processor）
- 一个运行Matter例程的板子（nRF52840DK 或 nRF5340DK）

## 3.2. 搭建Thread Border Router

原文链接：https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/protocols/thread/tools.html#thread-border-router

### 准备Thread RCP

在NCS中，打开`nrf/samples/openthread/coprocessor`例程。这就是Thread RCP的固件源码，它可以通过USB串口的方式给PC扩展Thread网络能力。

如果是52840DK的话，串口是硬件串口，通过板载的Jlink转换为USB串口。如果用52840Dongle的话，则直接通过USB虚拟串口传输。

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedefd40000bbc95d08bc4b192615db9ecb.png" alt="nRF52840 Dongle promo" style="zoom: 25%;" />

这里以52840Dongle为例，给出Dongle所需的编译配置：

![image-20230918125216258](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefineddcb1b0a41eac3d3435c604fa7ce1149d.png)

由于Dongle上并没有引出Jlink，因此我们必须通过其他方式烧录固件。所有Dongle出厂时都预烧录了nRF5 SDK中的bootloader，因此我们可以用nRF Connect 桌面版烧录固件。

首先把Dongle插入电脑USB口，然后按一下RESET按键（横着的按键），Dongle上会闪烁红色呼吸灯，说明进入了bootloader。

在nRF Connect桌面版中，打开Programmer。在串口列表中找到Open DFU Bootloader。然后把刚刚编译好的的`build/zephyr/zephyr.hex`烧录进去即可。

![image-20230918130029499](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined3ebab750781ad47abd53974b34f95f3a.png)

> - 烧录完毕后可能会提示Failed to detect device after reboot，这是正常的。
> - 原文链接中给出的是全部命令行的编译和烧录方式，也是可以的。

### 安装并运行OTBR Docker容器

Nordic不提供边界路由器的完整商业解决方案。但是如果是用于开发和测试，可以用谷歌的OpenThread Border Router (OTBR) ，它是一个开源的边界路由器实现，使用Docker运行。

1. 安装Docker（如果已安装可跳过此步骤）:
   ```
   sudo apt update && sudo apt install docker.io
   sudo systemctl start docker
   ```
2. 创建一个新的bridge网络
   ```
   sudo docker network create --ipv6 --subnet fd11:db8:1::/64 -o com.docker.network.bridge.name=otbr0 otbr
   ```
3. 拉取OTBR镜像（注意对应版本）
   ```bash
   sudo docker pull nrfconnect/otbr:xxxxxx
   # for v2.4.0
   #   sudo docker pull nrfconnect/otbr:9185bda
   ```

   >注意：
   >
   >这里的`9185bda`是容器的版本。根据你使用的NCS的版本不同，其对应的OTBR的版本可能也不同，需要在[原文档](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/protocols/thread/tools.html#running-otbr-using-docker)网页的右上角选择你的NCS的版本：
   >
   >![image-20230920095152208](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined1f4b3c04c485f674a219725a049a810d.png)
   >
   >然后再到“[Running OTBR using Docker](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.4.2/nrf/protocols/thread/tools.html#running-otbr-using-docker)”章节查看对应的拉取镜像的命令
4. 把Dongle插到电脑上，查看其串口号
   ```bash
   ls /dev/ttyACM*
   ```
5. 在内核中载入ipv6防火墙

   ```bash
   sudo modprobe ip6table_filter
   ```
   
6. 从镜像创建并启动容器
   ```bash
   # 记得修改串口号 和 OTBR镜像版本
   # 需确保PC的8080端口未被占用，因为需要把容器的80端口映射到宿主机的8080。也可以在下方命令里修改端口。
   sudo docker run -it --rm --privileged --name otbr --network otbr -p 8080:80 \
   --sysctl "net.ipv6.conf.all.disable_ipv6=0 net.ipv4.conf.all.forwarding=1 net.ipv6.conf.all.forwarding=1" \
   --volume "/dev/ttyACM0:/dev/radio" nrfconnect/otbr:9185bda --radio-url "spinel+hdlc+uart:///dev/radio?uart-baudrate=1000000"
   ```

   > Docker常用命令：
   >
   > - 离开当前容器终端：按Ctrl+P，然后再按Ctrl+Q。这时容器会保持后台运行。
   > - 查看所有容器：`sudo docker container ls`
   > - 连接到容器终端：`sudo docker attach otbr`，这里的容器名`otbr`也可以替换成容器的ID（只需要前几位）
   > - 在容器内执行命令：示例，在宿主机的终端中执行`sudo docker exec -it otbr sh -c "echo hello"`，就可以在容器内部执行`echo hello`
   > - 停止容器：在容器终端下按Ctrl + C。如果当前在宿主机终端下，则执行`sudo docker container stop <container_name>`
   
7. 新建一个Thread网络
   在浏览器中打开`http://localhost:8080/`，此为OTBR控制页面。选择`Form`。记下此时的`On-Mesh Prefix`值，如`fd11:22::`。点击FORM按钮。

8. 添加系统路由，配置IPv6转发，这里的目标网段就是前一步记下的`fd11:22::`
   ```bash
   sudo ip -6 route add fd11:22::/64 dev otbr0 via fd11:db8:1::2
   sudo ip -6 route add fd7d:64a3:9c38:1::/64  dev otbr0 via fd11:db8:1::2
   # 通过 route -6 命令可以查看这条规则是否成功添加到系统路由表中
   ```
   
   它会使得所有对`fd11:22::/64`网段内设备的访问，都从otbr0这个网卡转发。这个网卡就是前面创建的bridge。
   
9. 检查OTBR的状态
   ```bash
   sudo docker exec -it otbr sh -c "sudo service otbr-agent status"
   
    * otbr-agent is running
   ```

10. 检查Thread Node状态
    ```bash
    sudo docker exec -it otbr sh -c "sudo ot-ctl state"
    
    leader
    Done
    ```


> 注意：
>
> ​	以上5～8步，每次PC重启后，需要重新执行才能起效。

## 3.3. 准备CHIP Tool工具

CHIP（Connect Home over IP）项目是Matter的旧名称，它其实就是Matter。CHIP Tool是Matter Controller的一种实现。

Linux系统可以选择下载预编译好的固件。对于macOS，则只能从源码开始编译。

### 下载预编译好的CHIP Tool

对于Linux PC，可以下载已经编译好的CHIP Tool，注意要和NCS版本对应。下载地址：https://github.com/nrfconnect/sdk-connectedhomeip/releases

预编译好的软件为`chip-tool-release`和`chip-tool-debug`。任选一个即可。后续软件都用`chip-tool`这一名称。

#### 从源码编译CHIP Tool

Linux和macOS也可以从源码编译CHIP tool。NCS中已经把project-CHIP仓库作为子仓库包含进来了，所以源码不用另外下载。不过一部分子仓库还是要额外拉取的。这里给出Linux从源码编译的步骤（macOS请参考[原文](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/matter/chip_tool_guide.html)）：

```bash
# 安装Matter编译依赖(Linux)
sudo apt-get install git gcc g++ pkg-config libssl-dev libdbus-1-dev \
     libglib2.0-dev libavahi-client-dev ninja-build python3-venv python3-dev \
     python3-pip unzip libgirepository1.0-dev libcairo2-dev libreadline-dev


# 在NCS中进入Matter仓库
cd modules/lib/matter/


# 拉取子仓库
# 由于我们这里只需要编译chip tool就好，因此不要拉全部的submodule，以免太花时间
# 如果你要拉全部子仓库，用git submodule update --init
git submodule update --init --recursive third_party/jsoncpp/repo
git submodule update --init --recursive third_party/editline/repo 
git submodule update --init --recursive third_party/libwebsockets/repo


# 进入Matter环境
#   第一次运行这一步会花费很多时间，它会下载GN,ninja和一个自带很多库的专用Python环境
#   以后每次要进入这个环境都要先运行一下此脚本
source scripts/activate.sh


# 编译chip tool
# 这里的目标目录是`~/tools/chip-tools-v2.4.0`，你可以改成你自己的
./scripts/examples/gn_build_example.sh examples/chip-tool ~/tools/chip-tools-v2.4.0


# 退出Matter编译环境
deactivate
```



编译完成后，chiptool会出现在你设置的编译目录中。把它添加到环境变量即可:

```bash
export PATH=${HOME}/tools/chip-tools-v2.4.0/:$PATH
```

如果要永久保存，可以保存到当前用户下的systemd环境变量中：

```bash
sudo vim ~/.config/environment.d/envvars.conf
```

添加：

```bash
PATH=${HOME}/tools/chip-tools-v2.4.2/:$PATH
```

> 注意：
>
> - 此配置文件不是脚本，不需要写`export`
> - 此配置文件中不能用`~`，必须用`${HOME}`



# 4. 搭建Matter over Wi-Fi 开发环境

Matter over Wi-Fi 环境只需要CHIP Tool，按照3.3安装即可。



# 5. CHIP Tool配网

## 准备Matter设备

随便找一个NCS中的Matter例程，这里我用的是[窗帘例程](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/samples/matter/window_covering/README.html#enabling-remote-control)。烧录到开发板中，Thread可以用52840DK或52833DK，Wi-Fi使用7002DK。

烧录完毕并运行后，通过串口日志查看设备信息：

```
I: 401 [DL]Device Configuration:
I: 404 [DL]  Serial Number: 11223344556677889900
I: 409 [DL]  Vendor Id: 65521 (0xFFF1)
I: 412 [DL]  Product Id: 32784 (0x8010)
I: 416 [DL]  Product Name: not-specified
I: 420 [DL]  Hardware Version: 0
I: 423 [DL]  Setup Pin Code (0 for UNKNOWN/ERROR): 20202021
I: 428 [DL]  Setup Discriminator (0xFFFF for UNKNOWN/ERROR): 3840 (0xF00)
I: 435 [DL]  Manufacturing Date: (not set)
I: 439 [DL]  Device Type: 65535 (0xFFFF)
I: 443 [SVR]SetupQRCode: [MT:SAGA442C00KA0648G00]
I: 448 [SVR]Copy/paste the below URL in a browser to see the QR Code:
I: 454 [SVR]https://project-chip.github.io/connectedhomeip/qrcode.html?data=MT%3ASAGA442C00KA0648G00
I: 463 [SVR]Manual pairing code: [34970112332]
```

> 重要信息：
>
> - Setup Discriminator：一种短ID，区分多个正在广播、等待配网的Matter设备
> - Setup Pin Code：验证码
> - SetupQRCode：二维码信息。日志中也输出了网址，在网页上可以直接把Payload转换为二维码。
> - Manual pairing code：手动配对码

## 准备IP网络

Matter是运行在IPv6网络上的，因此需要准备一个IP网络：

- 对于Matter over Wi-FI，需要准备支持IPv6的家庭无线路由器即可，注意要开启允许IPv6广播。
- 对于Matter over Thread，需要准备3.2.中所述的Border Router，并且成功创建（Form）了Thread网络。另外，如果你前面搭建环境时，Border Router和Matter Controller不在同一台设备上时（例如树莓派+PC/手机），这里也需要一个支持IPv6的路由器，使二者在一个网络内。

为了让Matter设备能够连上这个网络，需要获取凭据。

- Wi-Fi凭据即为SSID和密码

- Thread凭据可通过命令获得：
  ```bash
  sudo docker exec -it otbr sh -c "sudo ot-ctl dataset active -x"
  
  0e08000000000001000035060004001fffe00708fdc71baa3ae245030c0402a0f7f8051000112233445566778899aabbccddeeff030e4f70656e54687265616444656d6f0410445f2b5ca6f2a93a55ce570a70efeecb000300000f0208111111112222222201021234
  
  Done
  ```

> 注意，每次OTBR重新Form网络之后，这个凭据中间都会有一小段略有变化。因此记得每次都要重新获取这个凭据。

## Matter设备配网

在进行Matter配网之前，需要先把Matter设备添加到IP网络中（Thread或Wi-Fi）。这里Matter标准的做法是通过BLE来传输网络凭据。

CHIP-Tool将会调用PC的蓝牙功能，扫描附近的Matter设备。建立BLE连接后，把网络凭据传输到Matter设备上。

### 通过BLE添加Thread设备

由于前面添加了环境变量，所以这里直接执行chip-tool命令

```bash
chip-tool pairing ble-thread <node_id> hex:<operational_dataset> <pin_code> <discriminator>
```

- node_id：任意指定一个id，用大于等于1的值。
- operational_dataset：上一步中获取的Thread凭据
- pin_code：Matter设备日志中得到的验证码 
- discriminator： Matter设备日志中得到的短ID

例如:

```bash
chip-tool pairing ble-thread 1 hex:0e08000000000001000035060004001fffe00708fdc71baa3ae245030c0402a0f7f8051000112233445566778899aabbccddeeff030e4f70656e54687265616444656d6f0410445f2b5ca6f2a93a55ce570a70efeecb000300000f0208111111112222222201021234 34343434 3871
```

> 注意，这里面只有operational_dataset是16进制的，前面要加上`hex:`

### 通过BLE添加Wi-Fi设备

后续补充。

