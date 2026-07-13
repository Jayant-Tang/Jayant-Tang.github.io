---
title: OpenThread网关示例
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
cover:
tags:
  - Nordic
  - Thread
  - Linux
categories:
  - Nordic
  - Thread
---

# 1. 概念

​	Thread网关（**Thread Border Router**）给IEEE 802.15.4网络提供到相邻网络的连接（Wifi，以太网）。Thread网关为802.15.4网络的设备提供服务，包括路由到这个网络之外的服务。

​	Thread网关需要2个部分：

- 一个处理802.15.4协议的应用：可以是一颗 [网络协处理器（Network co-processor, NCP）](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/ug_thread_architectures.html#thread-architectures-designs-cp-ncp)，也可以是NCP的一种轻量级形式，[无线电协处理器（Radio co-processor, RCP）](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/ug_thread_architectures.html#thread-architectures-designs-cp-ncp)。
- 一个上位机应用：需要更强的处理能力，比如Linux主机

> NCP上跑802.15.4驱动和OpenThread协议栈，Host只需跑IPv6协议栈
>
> RCP上只跑802.15.4驱动和OpenThread Controller，Host需要跑Thread协议栈（含IPv6）

​	使用谷歌提供的[OpenThread Border Router](https://openthread.io/guides/border-router) (OTBR)来实现Thread网关，可以安装在PC Docker或者树莓派上。它的功能有：

- Thread和Wifi/以太网双向IP访问
- 允许Thread节点连接到IPv4网络组件（NAT64, DNS64）
- 进行基于DNS的双向发现
  - 在WiFi/以太网上使用mDNS
  - 在Thread上使用SRP
- 利用非Thread的外部设备进行配网。例如用手机来授权节点，并让节点加入Thread网络。

# 2. 烧录RCP

使用一个nRF52840 Dongle (USB串口) 或 nRF52840 DK （串口）作为RCP。

NCS例程路径：`nrf/samples/openthread/coprocessor/`	

编译：

```bas
west build -p always -b nrf52840dongle_nrf52840 nrf/samples/openthread/coprocessor/ -- -DOVERLAY_CONFIG="overlay-usb.conf" -DDTC_OVERLAY_FILE="usb.overlay"
```

烧录：

待补充

# 3. 在嵌入式Linux上安装	OTBR

官方教程：[Thread Border Router - Bidirectional IPv6 Connectivity and DNS-Based Service Discovery (openthread.io)](https://openthread.io/codelabs/openthread-border-router#0)

官方教程要求树莓派3或4，我这里使用香橙派Zero2，系统是`Armbian_21.08.2_Orangepizero2_focal_legacy_4.9.255`.

> 对于这块Orange Pi Zero 2，我单独：
> ```
> $ sudo armbian-config
> # 在配置中，freeze内核，不允许更新
> 
> $ sudo apt update
> $ sudo apt upgrade
> # 一路回车
> ```
>

## 获取OTBR源码

```bash
git clone https://github.com/openthread/ot-br-posix.git --depth 1
```

# 编译安装

```bash
$ cd ot-br-posix
$ ./script/bootstrap
$ INFRA_IF_NAME=wlan0 ./script/setup
```





