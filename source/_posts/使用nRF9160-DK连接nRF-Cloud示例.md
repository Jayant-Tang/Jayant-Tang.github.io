---
title: nRF9160与nRF Cloud应用示例
date: 2022-12-01
cover: null
tags:
- Nordic
- nRF91
- nRF Cloud
- LTE
categories: Nordic
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
archive: true
cnblogs:
  postId: '17206080'
  url: https://www.cnblogs.com/jayant97/articles/17206080.html
  lastPublishedAt: '2026-07-06T18:20:52+08:00'
  sourceHash: sha256:5aba68d80c91b512e55e2a87d8dc247d686d1894352f3ebbd095588f54494b9d
  status: imported
  postType: Article
---

# 1. 产品简介

## 1.1. nRF Cloud

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefineda3720eafd8e506f6969eab6c6952197a.png" alt="image-20221204174543482" style="zoom: 67%;" />

​	nRF Cloud是Nordic Semiconductor公司在AWS上搭建的IoT平台，提供**设备注册（Cloud Provisioning）**、**OTA升级**、**数据存储**、**位置服务**等业务，所有这些功能都可通过Web界面进行管理。此外还有账号权限控制功能，客户可以为不同的团队配置不同级别的账户管理权限。本文会介绍上述功能的具体使用方法。

> ​	除了设备注册、OTA、消息存储等物联网云平台常见的功能外，nRF Cloud的重要卖点是位置服务（Location Service）：
>
> - AGPS/PGPS：设备根据附近的基站信息，从Location Service获取当前地区GPS卫星的信息，从而缩小搜星范围，把搜星的几十秒缩短到几秒，极大地节省功耗
> - 基站定位：根据上传附近的基站id，从云端获取获取当前定位，支持单基站和多基定位
> - WiFi定位：根据附近的WiFi SSID获取定位

​	nRF Cloud为Nordic nRF91系列产品提供了方便快速的上云方式，通过NCS的例程可以很方便的连入nRF Cloud。**当然，非Nordic产品也是可以注册到nRF Cloud的，本文最后就会介绍如何使用随机生成的UUID来注册到nRF Cloud。**

​	nRF Cloud目前有Developer，Pro和Enterprise三种收费计划。其中开发者计划（Developer plan）是**完全免费**的，你可以不用任何开发板，只使用PC就能连上云端进行测试。并且开发者计划每月有500条免费的Location Service。

​	设备通过nRF Cloud APIs与nRF Cloud进行连接，如下图：

![image-20221125164136165](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined131384668672c1b5889459a0360a3cde.png)

​	设备可以直接通过MQTT API或REST API接入到云。nRF Cloud也通过REST API为客户提供了**云-云对接**的接口。

​	nRF Cloud的MQTT连接使用X.509证书进行认证和加密。**此证书不必是CA收费签发的证书，可以使用自签证书**。Nordic提供了一套方便的脚本（TypeScript和Python可选）来进行证书的生成、签发、烧录。本文后续会介绍具体步骤。

​	要想调用nRF Cloud的REST API，对用户来说，使用常见的API Key进行认证；对IoT设备来说，需要使用JWT进行认证。JWT需要使用前述的X.509证书进行生成，本文后续会介绍IoT设备以及PC端测试JWT生成的方法。

> REST API 是通过HTTP请求来调用的

​	更多有关nRF Cloud的信息，可以参考：

- [nRF Cloud | nRF Cloud Docs](https://docs.nrfcloud.com/)

## 1.2. nRF9160 SiP

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedd452c9d7a548399637ebf0b85c1ab489.webp" alt="application" style="zoom: 50%;" />

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined2a9af8eeea1f40f3a0adac95932021e7.png" alt="image-20221122134533863" style="zoom: 33%;" />

​	nRF9160是一款高集成度的低功耗SiP（System-in-Package），具有完整的LTE-M/NB-IoT Modem、射频前端、电源管理系统，还具有一颗Cortex-M33应用处理器，便于开发自定义应用。nRF9160是目前市面上**最紧凑、最完整、功耗最低**的蜂窝物联网解决方案。

​	nRF9160内置的调制解调器（Modem）在全球范围内同时支持**LTE-M**和**NB-IoT**，并且支持**eDRX和PSM省电模式**，支持传输层安全（TCP/TLS），支持GPS。

​	Modem固件由Nordic以二进制形式提供，Modem固件可以通过OTA进行升级。

> 中国大陆地区目前只有NB-IoT覆盖，无LTE-M。

​	Cortex-M33应用处理器具有独享的1 MB Flash，256 KB SRAM和多种外设接口，可以让用户自行开发高效率的应用。

​	除了直接在9160上开发以外，也可以把nRF9160当作外挂模组，让外部MCU通过AT指令进行操作，拓展连网能力。在 [Nordic Info Center](https://infocenter.nordicsemi.com/topic/ref_at_commands/REF/at_commands/intro.html)可以查看并下载AT指令手册。

​	在把9160当作外挂模组时，除了3GPP标准AT指令（以`AT+`开头），以及Nordic自定义的Modem相关指令（以`AT%`开头）以外。还可以在前述Cortex-M33应用核中烧录[SLM（Serial LTE modem）](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/applications/serial_lte_modem/README.html)例程，这样就可以扩展出大量实用指令（以`AT#`开头），可以实现Socket、TCP/UDP、MQTT、FOTA、DFU、FTP、GNSS、GPIO等实用功能，使得9160作为外挂模组时也能充分发挥其片上资源的作用。

​	在安全方面：Arm TrustZone技术可为固件和外设提供安全隔离和保护。使应用可实现Secure Boot、受信任固件升级、受信任的Root等安全需求，且不影响性能。Arm CryptoCell通过加密和安全资源来保护物联网应用程序免受各种攻击威胁。

​	nRF9160支持SIM和eSIM。今后随着与虚拟运营商的合作，还将在海内外支持SoftSIM。

> SoftSIM无需卡或芯片，SIM的信息直接烧录在9160内部。

​	nRF91的功耗极低，在PSM休眠时可以做到2.7uA的电流。	

​	更多信息，可参考：

- [nRF9160中文brief - Nordic Semiconductor - nordicsemi.com](https://www.nordicsemi.com/-/media/Software-and-other-downloads/Product-Briefs/Translated-versions/04_nRF9160-SiP-1.4_SC.pdf?la=en&hash=A1F478B9D8593C70FA143C1CA09C2759C8ED51B6)
- [nRF9160 - Nordic Semiconductor - nordicsemi.com](https://www.nordicsemi.com/Products/nRF9160)
- [nRF9160 Product Specifications v2.1.pdf](https://infocenter.nordicsemi.com/pdf/nRF9160_PS_v2.1.pdf)
- [nRF9160 全球认证信息 - nordicsemi.com](https://www.nordicsemi.com/Products/Low-power-cellular-IoT/nRF9160-Certifications)

## 1.3. nRF9160 DK 和 PPK II

![nRF9160 DK promo](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined619e657f9ea24367929992fa984cc669.webp)

​	nRF9160 DK是一款优秀设计的预认证开发套件，带有一颗nRF9160 SiP和一颗nRF52840低功耗蓝牙MCU（用于开发BLE网关产品）。

​	板载一个支持多个频段的LTE-M和NB-IoT天线、一个GPS贴片天线和一个2.4G陶瓷天线（用于BLE）。其中LTE和2.4G天线接口提供SWF射频连接端子，便于测量RF信号。所有三款连接器均允许使用外部天线。

​	开发板引出了所有GPIO和接口，兼容Arduino Uno Rev3。提供可编程LED(4)、按钮(2)、开关(2)。开发板还具有nano SIM卡插槽（J5）和eSIM贴片焊盘（U20）或eSIM直插接口（P28）。

板载正版Jlink OB，除可下载、调试板载的nRF9160外，也可对外调试其他产品。

> 关于nRF 9160DK的更多信息，可参考：
>
> - [nRF9160 DK - nordicsemi.com](https://www.nordicsemi.com/Products/Development-hardware/nRF9160-DK?lang=zh-CN#infotabs)
>
> - [nRF9160 DK HW User Guide v1.1.0.pdf](https://infocenter.nordicsemi.com/pdf/nRF9160_DK_HW_User_Guide_v1.1.0.pdf)

​	Nordic所有的开发板都预留了SoC/SiP电流测量的接口。9160DK还预留了SIM卡电流测量的接口。电流的测量可以使用PPK II。下图展示了9160 PSM休眠时的电流（灰色窗口内平均电流为2.8uA）：

![image-20230311124553236](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined003bf1078cfb8a5754bd28b45f138bde.png)

![Online Power Profiler](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined212c9a15de78d68939ef4caa6f6cd5a2.webp)

​	Power Profile Kit II (PPK II) 是一个方便的功耗测量工具，具有**电流表**和**电源(0.8V ~ 5V)**两种模式，且两种模式都可测量电流，范围从低于1uA到1A。PPK II本身通过USB供电（5V 500mA），如果在电源模式需要输出1A，需要插两个USB。

​	PPK II还自带8通道逻辑分析仪，便于分析各个阶段的功耗。下图底部为逻辑分析仪通道3的输出，它连接到9160的一个GPIO，用于测量9160连接MQTT服务器进行证书交换的耗时和功耗。

![image-20230311123832875](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined2cd3c620f73ed770506ed03a512d12e0.png)

> 更多有关PPK II的信息，可参考：[Power Profiler Kit II - nordicsemi.com](https://www.nordicsemi.com/Products/Development-hardware/Power-Profiler-Kit-2)

## 1.4. nRF Connect SDK

​	nRF Connect SDK，简称NCS，是Nordic最新的SDK平台，该平台支持Nordic所有产品线，包括低功耗蓝牙，蜂窝网，WiFi，GPS，2.4G，蓝牙Mesh，Zigbee，Thread，Matter, Homekit, FindMy等。

​	Nordic所有的新产品都将在NCS上进行开发。

​	NCS内嵌Zephyr RTOS，并沿用了Zephyr project的编译系统、库和驱动。利用Device Tree和Kconfig进行项目的硬件、软件配置，自动载入驱动程序，自动初始化硬件。使用CMake和Python脚本辅助生成一些头文件、代码和Hex。一旦上手，开发调试起来非常方便。此外，NCS是跨平台的（Windows/Linux/OSX），支持命令行编译，可以在服务器上实现CI/CD。

​	NCS提供VS Code插件，实现强大的项目管理、项目构建、调试等功能（支持条件断点、查看寄存器和

线程堆栈）。

​	NCS在Github上托管，包含多个仓库。其主仓库（Manifest）是nrf（含Nordic产品驱动与各类无线协议栈等），此外还有Zephyr、MCUBoot、mbedtls、nrfxlib等其他仓库。

​	更多信息可参考：

- [About the nRF Connect SDK — nRF Connect SDK 2.1.2 documentation (nordicsemi.com)](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/introduction.html)

- [开发你的第一个nRF Connect SDK(NCS)/Zephyr应用程序 - iini - 博客园 (cnblogs.com)](https://www.cnblogs.com/iini/p/14174427.html)



# 2. 入门: 使用nRF9160-DK连接到nRF Cloud

​	本节将会在nRF9160-DK开发板上，烧录`nrf/applications/asset_tracker_v2`例程。根据国内的网络进行配置，然后把板子连接到nRF Cloud上。

## 2.1. 前期准备

### 硬件准备

- [nRF9160 DK开发板（本示例使用的版本：v1.1.0）](https://www.nordicsemi.com/Products/Development-hardware/nRF9160-DK?lang=zh-CN)：其中nRF9160 SiP**不能**是Revision 1版本，必须是Revision 2或更高版本。
  （查看SiP封装上的文字，有**B0**则为Rev1版本，有**B1**则为Rev2版本。可参考：[nRF9160 IC Revision Overview](https://infocenter.nordicsemi.com/index.jsp?topic=%2Fcomp_matrix_nrf9160%2FCOMP%2Fnrf9160%2Fnrf9160_ic_revision_overview.html)）

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined4864ea3b727687cbf44c8b78148b11c6.png" alt="image-20221124110534824" style="zoom:25%;" />

- micro USB线缆一根

- 中国移动NB-IoT卡(物联网卡)
	![image-20221122191558453](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined8fda62d98ab42f45e58bc76360627033.png)

	- 将电源开关拨到on，并确保调试开关处于"nRF91"挡位
	- 插好nano SIM卡，并通过microUSB线连接到电脑

	> 注：DK包装盒内附赠的iBASIS SIM卡为国外运营商产品，国内无法使用。需要另外购买移动NB-IoT物联网卡。

### 非硬件准备

- 一台Windows10或以上版本操作系统的电脑，并[**正确安装了NCS开发环境**](https://jayant-tang.github.io/2022/12/779143a4bec8/)。本次示例使用的NCS版本是v2.2.0。
- 免费注册一个 [nRF Cloud](https://nrfcloud.com/#/) 账号

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefineddb6ad742814b2bfbbbccf179bada71bc.png" alt="image-20221205005305505" style="zoom:50%;" />

- 知道如何打开NCS中的例程，并且知道如何编译、烧写。



## 2.2. 烧录Modem固件

​	nRF9160的Modem具有独立的固件，这部分固件是Nordic以zip包的形式提供的。

1. 在官网[nRF9160 DK - Downloads - nordicsemi.com](https://www.nordicsemi.com/Products/Development-hardware/nRF9160-DK/Download#infotabs)界面，选中最新的Modem固件版本并下载（必须大于1.3.0）。

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedd11626d71a4e4ec7c55a7a7eb253e02d.png" alt="image-20221123143324324" style="zoom:50%;" />



2. 打开nRF Connect桌面版，找到Programmer工具并打开

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined57157872ac933c2ac886be5c3d9099b4.png" alt="image-20221123143424410" style="zoom: 67%;" />



3. 先选择板卡，然后选择固件文件（.zip），最后烧录

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb80d08f1d1ff9ecafa390ff815d464ef.png" alt="image-20221123143649354" style="zoom:50%;" />



4. 烧录完毕

![image-20221123144339925](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined01857bb942b13a041db16e1aae46db36.png)



## 2.3. 配置、编译并烧录Application固件

### 2.3.1. 以asset_tracker_v2为模板，创建新工程

> asset_tracker_v2是applications目录下的例程。这个目录下的都是商业级例程，基本改一下就能作为产品使用了。

​	创建新工程相比于打开例程的好处，在我的另一篇文章《安装nRF-Connect-SDK》中已经描述了。

​	通过nrf connect插件界面的"Create a new application"来创建新的工程。

![image-20221123145304528](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined26f68e383651144c62f875f2cd2a029f.png)

从上到下，选项依次为：

- NCS路径
- Zephyr SDK工具链路径
- 本项目的存储位置
- 选取作为模板的sample例程（NCS中的例程）
- 本项目的名称

​	关于asset_tracker_v2例程的更多信息，可以参考官方的例程说明：[nRF9160: Asset Tracker v2 — nRF Connect SDK 2.1.2 documentation (nordicsemi.com)](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/applications/asset_tracker_v2/README.html)

>建议把这个新创建的工程初始化为git仓库，便于你记录自己修改了什么。
>
>记得添加`.gitignore`文件，并且忽略你的`build/`文件夹



### 2.3.2. 为新工程创建build配置

板卡选择`nrf9160dk_nrf9160_ns`，然后Build Configuration即可。

![image-20221123145942948](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined8c66d4d3f8994bce4e94d7a8fe267933.png)



### 2.3.3. 修改配置

打开工程根目录下的`prj.conf`文件，进行修改：

1. 与运营商有关的修改

```bash
# 由于使用移动的NB物联网卡，故需要关闭LTE-M，使用NB-IoT
CONFIG_LTE_NETWORK_MODE_LTE_M_GPS=n  # 由y改为n
CONFIG_LTE_NETWORK_MODE_NBIOT_GPS=y  # 新增

# NB-IoT对ePCO支持的不好，故使用传统的PCO
CONFIG_PDN=y                         # 新增
CONFIG_PDN_LEGACY_PCO=y              # 新增
```

2. 与nRF Cloud连接、注册有关的修改（后面小节会详细说明）

```bash
# 启用JWT和UUID的云端注册方式
CONFIG_MODEM_JWT=y                              # 新增
CONFIG_NRF_CLOUD_CLIENT_ID_SRC_INTERNAL_UUID=y  # 新增
```



> 【备注】`prj.conf`文件的作用：
>
> 在Zephyr编译系统中，Kconfig管理编译选项、各类功能选项的开关，而devicetree用来管理硬件。编译时，通过CMake和ninja会调用一系列python辅助脚本，把Kconfig和device tree变成c代码和头文件。然后进行编译。更多资料，可参考：[Build and Configuration Systems — Zephyr Project Documentation](https://docs.zephyrproject.org/latest/build/index.html#build-and-configuration-systems)
>
> 开发时，只需关注Kconfig与device tree如何修改即可。Kconfig中的选项非常多，大多数情况下保持默认即可。Kconfig的默认配置保存在NCS中。
>
> `prj.conf`的作用，就是为这个工程单独修改部分Kconfig配置。编译时，构建系统会优先使用prj.conf里的配置来覆盖默认的Kconfig配置。这样每个工程都可以单独配置，不会影响到NCS中的默认配置。
>
> `prj.conf`中的选项都必须是Kconfig中可以找到的。
>
> 在VS Code中通过图形界面修改完Kconfig时，也可以通过"Save to file"按钮，来把修改的部分单独保存到`prj.conf`中，如下图：
>
> ![image-20221123154242926](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined66ea802d2636459dbfc51f3873bb7ac7.png)

### 2.3.4. 编译

使用nRF Connect插件中的Action菜单中的build即可编译

![image-20221205010029256](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedc85bc25c9c786379af85884009f82c87.png)

编译成功的结果：

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined4407baf0003e97093ad14911a2680f87.png" alt="image-20221205010439970" style="zoom: 50%;" />

### 2.3.5. 烧录

​	先把官方的开发板通过USB连接到电脑上，识别到Jlink之后，可以通过ACTIONS栏中的`Flash`按钮触发烧录动作：

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined1fa743c2d810a13b0cd19c41785c38a3.png" alt="image-20221123160139273" style="zoom: 80%;" />

​	也可以通过命令行的形式进行烧录:

```bash
$ west flash
```



> 备注：	
>
> ​	这样直接烧录，有一部分项目可能会烧写失败，显示：
>
> ![image-20221123160245857](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined068e6afb1eaaf16525a0d133254ec2c2.png)
>
> ​	这是因为，Nordic的MCU中通常都有一个用于存储用户信息的寄存器（UICR），可以认为是一块特殊的flash区域，存储了客户自己的加密密钥、引脚配置等产品信息。由于信息安全的原因，是不允许在保持UICR不变的情况下烧写新的固件的。因此这种情况下只能全片擦除然后再烧录。
>
> ​	全片擦除然后烧录的方式，点击Flash右边的按钮：
>
> ![image-20221123160832598](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedda89dd91d01305593dc8a1dd133bda56.png)
>
> ​	或者使用命令行方式：
>
> ```bash
> $ west flash --force --erase
> ```





## 2.4. 联网测试

​	在nRF Connect桌面版中，打开LTE Link Monitor工具。

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined2497c2fb75a0e1c17130bdfddf0246b4.png" alt="image-20221123163321689" style="zoom:67%;" />



​	然后左上角选择板卡，然后再打开串口。串口共有三个(都是Jlink提供的虚拟串口，在板子上2个连接到9160，1个连接到52840)，其中9160的串口只有一个用于AT Command。

需要依次尝试，点击“AT”按钮就会从串口发送一行“AT”命令，如果有回复OK，说明这个串口就是AT指令的串口。

![image-20221123173504262](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined52f4f72df88f5c372762fb5c897b9075.png)

>在 [Nordic Info Center](https://infocenter.nordicsemi.com/topic/ref_at_commands/REF/at_commands/intro.html)可以查看AT指令手册，并可以在右上角下载PDF。



​	左侧的面板显示了联网状态、IP地址、信号强度等信息：

![image-20221123173600818](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined50dfdc645c3d928b70c8fc59d10c368f.png)



​	注意，"**Automatic Request**"需要勾选上。勾选以后，在切换串口或者点击“AT+CFUN?”指令时，此软件会自动发送相关AT指令，查询网络状态信息，面板上的信息才会更新。否则面板可能不更新。

![image-20221123173636098](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined89689178ee00291d1e7404fdb1b1d151.png)

​	即是说，以下状态灯应当全绿，则说明联网成功。但若不是全绿，也不一定是联网失败，可能只是信息没有刷新，参照上一条勾选“**自动请求**”，然后点击“AT+CFUN?”指令再次查询即可。

![image-20221123173817830](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined93af4f0feee087b5cd654b258260ab28.png)

>含义：
>
>- UART：串口状态
>- Modem：调制解调器状态
>- UICC：SIM卡状态
>- LTE：LTE联网状态
>- PDN：Packet Data Domain联网状态



## 2.5. 将设备注册到nRF Cloud云端 

​	IoT设备是需要注册到云端的，并且通信都需要加密认证，否则任何人开发的设备都能连接到你的云，就不安全了。

​	设备注册到云端的过程称为**Cloud Provisioning**

​	设备注册的流程是：

1. 首先，要有一个自签CA证书，以及对应的密钥文件；
2. 需要用自签CA证书+设备的UUID，给每个设备单独签发CA证书，并安装单独的私钥到设备中。
3. 云端持有证书（公钥），这样设备和云端就可以加密通信了。

>什么是非对称加密和CA证书？
>
>​	CA证书具有证书文件（内含公钥）和私钥文件两个部分，公钥和私钥是用来做非对称加密的。公钥加密的数据，只能用私钥解密；用私钥加密的数据，只能用公钥解密。
>
>私钥是自己持有的，而公钥公开给所有想与自己通信的对象。
>
>假设A要给B发送一段消息M：
>
>1. 对于这段消息M，发送者A先利用MD5或SHA256等方式生成一个数字摘要D，再用私钥把消息M加密得到密文C。最后把C+D一起发给接收者B。
>2. B收到消息后，先用公钥解密C得到M'，再对比M'的数据摘要和D是否一致，若一致，则说明数据确实是**公钥的所有者**发出的。于是确信M'就是要接收的消息M。
>
>但B可能拿到假的公钥，黑客发出假的公钥，就可以冒充A给B发消息。为了避免这种情况发生，公钥需要被**认证**，这就是CA证书。
>
>​	一个CA证书文件`ca1`包含公钥P、签名S、所有者信息（国家、城市、单位名称、邮箱等）。`ca1`的签名S，是用另一个证书`ca2`的私钥，对`ca1`的公钥P进行加密得到的。
>
>所以利用公开的`ca2`的公钥对S进行解密，如果和P一致，则说明`ca1`是合法的。`ca1`的合法性由`ca2`证明。
>
>​	一个CA证书的安全性由另一个CA证书来证明，这样层层递归下去，形成证书链。而最初的CA证书就是**根证书**。具有颁发**根证书**的资质的机关就是CA（Certificate Authority），也叫“证书授权中心”。CA具有根证书，然后给他信任的其他公司颁发CA证书，这些颁发的CA证书里的签名S就是用根证书的私钥加密的。



​	目前nRF Cloud有两种注册方式，一种是通过JITP的方式（Just-in-Time Provisioning）,另一种是[预连接（preconnect provisioning）](https://docs.nrfcloud.com/Devices/Associations/Provisioning/#preconnect-provisioning)。

### JITP方式注册

​	JITP（Just-in-Time Provisioning）的方式利用开发板背面贴纸上的IMEI和PIN码，在云端控制台**手动**生成一个CA证书，然后下载到电脑，并通过LTE Link Monitor 工具生成**设备证书**，并把设备证书的私钥安装到9160中。这样设备就可以直接连接到云端并注册。这种方式便于快速开发、验证，但不适合量产，本文不详细介绍。图文步骤可参考：https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/ug_nrf9160_gs.html#connecting-to-nrf-cloud

JITP的文档说明为：[Updating The nRF Cloud Certificate](https://docs.nrfcloud.com/Devices/Associations/Provisioning/#just-in-time-provisioning)

### 预连接方式注册

​	[预连接（preconnect provisioning）](https://docs.nrfcloud.com/Devices/Associations/Provisioning/#preconnect-provisioning)，是利用nRF Cloud提供的云端REST接口（接口文档见[Provision Devices](https://api.nrfcloud.com/v1/#tag/IP-Devices/operation/ProvisionDevices)），进行批量的设备注册。具体步骤为：

1. 首先电脑上需要一个CA证书（不一定要CA正规机构颁发，可以自己生成）；
2. 电脑连接到nRF9160 AT串口，通过nRF Cloud Utils脚本（TypeScript 或 python），执行以下步骤：
   - 通过串口AT命令，让设备生成UUID，并通过PC上的**自签CA证书**和**UUID**为每一个设备生成X.509**设备证书**和**私钥**。由于X.509私钥是直接在9160内生成的，PC上看不到，从而确保了安全性。
   - 通过串口烧写AWS根证书到9160 Modem中，这样可以确保nRF9160连接nRF Cloud时可以对服务器进行验证（nRF Cloud 运行在AWS上）。
   - 把该设备的UUID、X.509证书等信息记录到一个CSV表格文件中。
3. 步骤2可重复最多1000次，信息存入同一个CSV表格。
4. 通过nRF Cloud的云端REST接口，把CSV表格上传，把这一批设备一次性注册到云端。

​	**nRF Cloud提供了一套工具来帮助你快速完成上述三项工作，可以用TypeScript脚本或Python脚本**，这套工具在github上，地址为： [utils/README.md at master · nRFCloud/utils (github.com)](https://github.com/nRFCloud/utils/blob/master/python/modem-firmware-1.3+/README.md#create-device-credentials)。

​	下面通过Python脚本进行示例：

### （1）前期准备

- 确保9160SiP 为Revision 2或更高版本（查看SiP封装上的文字，有**B0**则为Rev1版本，有**B1**则为Rev2版本。可参考：[nRF9160 IC Revision Overview](https://infocenter.nordicsemi.com/index.jsp?topic=%2Fcomp_matrix_nrf9160%2FCOMP%2Fnrf9160%2Fnrf9160_ic_revision_overview.html)）
  <img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined4864ea3b727687cbf44c8b78148b11c6.png" alt="image-20221124110504562" style="zoom: 25%;" />

- 确保已经按照[2.2](#2.2. 烧录Modem固件)的步骤，烧录了1.3.0或更高版本的Modem固件（这些版本才支持新的安全AT指令，如`KEYGEN`）

- 确保你已经按照[2.3](#2.3. 配置、编译并烧录Application固件)的步骤，修改了Application固件的配置参数，启用了JWT和UUID；

- 已经按照[2.4](#2.4. 联网测试)的步骤，验证了设备可以成功联网；
- 已经 [注册了nRF Cloud账号，并登录](https://nrfcloud.com/#/)。

### （2）获取最新的nRF Cloud Utils工具，并安装好依赖

​	在一个无中文、无空格、无特殊字符的路径下，从github拷贝仓库：

```bash
$ git clone https://github.com/nRFCloud/utils.git
```

​	进入modem firmware 1.3+ 子文件夹，然后安装其python依赖包

```bash
$ cd utils/python/modem-firmware-1.3+/
$ pip3 install -r requirements.txt
```

### （3）生成你的自签CA证书

​	复制下方的命令，并把对应参数改成你自己需要的信息。

```bash
$ python create_ca_cert.py \
-c CN \
-l Shanghai \
-o "Nordic Semiconductor K.K." \
-ou "Sales" \
-cn nordic.cn \
-e jayant.tang@nordicsemi.no \
-p ./my_ca \
-f "Jayant-"
```

>参数释义（部分参数未使用）：
>
>- `-c` ：2字符的国家代码，`CN`为中国
>- `-st`：州或省
>- `-l`：地点
>- `-o`：公司/组织
>- `-ou`：组织部门
>- `-cn`：Common Name
>- `-dv`：有效天数
>- `-e`：电子邮箱地址
>- `-p`：CA证书生成后存储的位置
>- `-f`：给生成的三个证书文件的文件名添加前缀（字符串）

​	生成后，可以看到自己指定的目录下已经有了三个证书文件：

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined9424c2cf75ac782468bfcad9d8ec1596.png" alt="image-20221123223024181" style="zoom: 67%;" />

​	其中，ca是证书，prv是私钥，pub是公钥。

>​	CA证书是我们自己签发的根证书，能让设备和云端的通信被加密即可。这个CA证书本身并不是CA机构签发的正规证书。
>
>​	若想查看CA证书的信息，可以随便找一个[在线CA查看器](https://myssl.com/cert_decode.html)，把xxx_ca.pem拖进去就可以看到信息了：
>
><img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined0141babda596b2341bb7be24ce5e67f6.png" alt="image-20221123224514523" style="zoom:80%;" />



### （4）签发并安装设备证书

​	需要使用`utils/python/modem-firmware-1.3+/`目录下的`device_credentials_installer.py`脚本。

如果想查看最新的脚本使用方式：

```bash
$ python device_credentials_installer.py -h
```



​	此脚本的功能：

1. 通过电脑串口，给你的设备发送AT指令，生成一个UUID
2. 这个脚本会调用同一目录下的`create_device_credentials.py`，让每个设备单独生成X509设备证书和私钥；
3. 通过电脑串口，读取到UUID和X.509证书，并保存csv表格文件中
4. 量产时，这个脚本可以重复执行。只需要在每次串口上换一个设备时，就执行一次这个脚本。这个设备就会生成X.509证书，并且设备的信息会记录到2个表格文件中。**最多允许存1000台设备的信息。**
5. 后续可以把这两个表格文件和证书上传到云端，便于批量注册设备。



​	在执行这个脚本之前，确保第（2）步中的CA证书都生成好了。

​	脚本使用示例如下（windows环境），你需要根据实际情况改变命令的参数配置。

​	注意，示例执行脚本时，并未指定串口。因为脚本在windows下会自动检测哪个串口是AT指令串口。注意不要开着LTE Link Monitor等工具占用着串口导致安装失败。如果在linux下操作，请增加`--port /dev/ttyS??`来指定串口，详情可参考 [Device Credentials Installer](https://github.com/nRFCloud/utils/blob/master/python/modem-firmware-1.3+/README.md#device-credentials-installer)。

```bash
$ python device_credentials_installer.py -d -t "jayant-DK" --ca ./my_ca/Jayant-0x12de89cb5ee9589433c9ba08e74bc0eebdfe9ab4_ca.pem --ca_key ./my_ca/Jayant-0x12de89cb5ee9589433c9ba08e74bc0eebdfe9ab4_prv.pem -a --devinfo_append --csv ./jayant_provision.csv --devinfo ./jayant_devinfo.csv --term CRLF
```

>参数释义：
>
>- `-d`：安装前先从Modem中删除sectag
>- `-t`：用于设备分组管理的标签，是一个字符串
>- `-T`：设置自定义的子类型，如温湿度传感器等，是一个字符串。此处未设置
>- `--ca`：CA证书文件的路径
>- `--ca_key`：CA证书私钥的路径(prv)
>- `-a`或`--append`：保存**设备注册信息**到csv表格文件时，向末尾增加新的条目，而不是覆盖csv文件（这个选项是确保你可以重复执行脚本，搜集全部设备信息的基础）
>- `--devinfo_append `：保存**设备信息**到csv表格文件时，向末尾增加新的条目，而不是覆盖csv文件（这个选项是确保你可以重复执行脚本，搜集全部设备信息的基础）
>- `--csv`：用于存储设备注册信息的CSV表格的文件名，若文件不存在则创建。若文件存在，则根据`-a`选项，向文件中添加新条目。（存储UUID、前缀、固件等信息）
>- `--devinfo`：用于存储设备信息的CSV表格的文件名，若文件不存在则创建。若文件存在，则根据`-a`选项，向文件中添加新条目。（存储UUID、Modem固件版本、芯片IMEI等信息）
>- `--term`：AT指令的结束符（`NULL`,`CRLF`,` CR` 或`LF`）
>- `--port`：指定AT指令串口

​	我只有一块开发板，所以只执行一次。

### （5）把设备信息批量注册到云端

​	批量的在nRFCloud上进行设备注册（Cloud Provisioning）。

​	首先，在[nRF Cloud Portal](https://nrfcloud.com/#/) 登录你的nRF Cloud账号（前面应该已经注册好了）。然后获取nRF Cloud REST API key。

​	在右上角点击进入个人账户页面，然后在下面可以看到API key，复制出来即可。

![image-20221123234437620](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined75a6f7972db134397f1a881b57f1799f.png)



​	接下来继续执行python脚本，进行云端注册（这个脚本底层就是调用了REST API进行注册）：

```bash
$ python ./nrf_cloud_provision.py --apikey 3c967ecbd9fxxxxxxxxxxxxxxxxa73cf37049983 --chk --csv ./jayant_provision.csv --devinfo jayant_devinfo.csv --set_mfwv --name_imei --name_pref "my_dk_" --res prov.log
```

>参数释义：
>
>- `--apikey`：刚刚复制的API key
>- `--chk`：**单个设备的注册才使用**，注册前先检查设备是否存在
>- `--csv` ：上一步生成的，存储着**设备注册信息**的csv表格文件，最多允许1000条数据
>- `--devinfo` ：上一步生成的，存储着**设备信息**的csv表格文件，最多允许1000条数据
>- `--set_mfwv`：把`--devinfo`中记录的Modem固件版本存储到云端
>- `--name_imei`：把`--devinfo`中记录的IMEI（芯片ID）作为friendly name
>- `--name_pref`：给friendly name添加一个前缀字符串
>- `--res`：存储注册结果的日志文件



​	完成后，可以看到成功注册的结果：

![image-20221123235635167](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined2be382bd8d8e5abf21a2afc9c834406b.png)



### （6）在云端查看刚刚注册的设备

![image-20221123235940868](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined696a41e1cc9431a1466faf914449307f.png)

​	可以在Device界面看到设备已经注册成功，设备的名称是“前缀字符串” + “IMEI”的形式。

​	但设备还处于Disconnected的状态。这是因为刚才下载私钥时，把设备设为了离线状态，可以通过LTE Link Monitor输入以下AT指令，也可以简单reset一下设备，或者重新通过LTE Link Monitor查看设备的状态。这样设备应该就会变成已连接了:

```AT
AT%XSYSTEMMODE=0,1,0,0 // 选择NB网络
AT+CEREG=5             // 打开调制解调器
AT+CFUN=1              // 开始联网
```

![image-20221124000424393](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined995676184b739549eda27c61161381a1.png)

​	点进设备的详情页面，已经可以看到大量的信息（部分资源在墙外，加载不出属于正常现象，需要代理上网）：

![image-20221124000623033](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined5f73acf39695cddccce21effc0ed0c74.png)

​	可以通过terminal窗口，发送json消息，与设备进行交互。也可以进行OTA升级。

​	在本例程中，板子上的LED指示灯也可以展示状态：详见[Led indication](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/applications/asset_tracker_v2/doc/ui_module.html#led-indication)。这里只列出DK板的行为。

| State                     | nRF9160 DK solid LEDs      |
| ------------------------- | -------------------------- |
| LTE connection search     | LED1 blinking              |
| GNSS fix search           | LED2 blinking              |
| Cloud association         | LED3 double pulse blinking |
| Connecting to cloud       | LED3 triple pulse blinking |
| Publishing data           | LED3 blinking              |
| Active mode               | LED4 blinking              |
| Passive mode              | LED3 and LED4 blinking     |
| Error                     | All 4 LEDs blinking        |
| FOTA update               | LED1 and LED2 blinking     |
| Completion of FOTA update | LED1 and LED2 static       |



### （7）从云端删除设备

​	如果你想从云端删除设备，可以直接在网页端操作，从右上角齿轮处点击删除即可。也可以用云对云的REST API进行删除，后续章节讲解。



# 3. Asset Tracker v2 例程分析

​	例程的官方说明：[Application description — nRF Connect SDK 2.1.2 documentation (nordicsemi.com)](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/applications/asset_tracker_v2/doc/asset_tracker_v2_description.html)

## 3.1. 本例程设计原则

- 超低功耗
- 离线优先：本例程假设大多数情况下是离线的，连接是不可靠的。因此会有数据重发的机制。
- 时间戳机制：多时间源的时间戳机制，离线情况也可以计时
- 数据打包：多次数据打包，减少数据发送次数；离线时，数据会被存储，等到下次在线时一起发送
- 运行时参数修改：支持在运行时修改部分配置参数（例如加速度计灵敏度，或GNSS超时时间）

## 3.2. 例程实现的功能

​	本节概览性的介绍此例程的具体功能：

### 数据搜集

​	本例程会搜集数据，并上传到云端，下表列出会上传的数据：

| Data type                 | Description                | Identifiers                                   | String identifier for NOD list |
| ------------------------- | -------------------------- | --------------------------------------------- | ------------------------------ |
| 位置（Location）          | GNSS坐标                   | APP_DATA_GNSS                                 | `gnss`                         |
| 环境信息（Environmental） | 温度，湿度                 | APP_DATA_ENVIRONMENTAL                        | NA                             |
| 运动信息（Movement）      | 加速度                     | APP_DATA_MOVEMENT                             | NA                             |
| 调制解调器（Modem）       | LTE link data, device data | APP_DATA_MODEM_DYNAMIC, APP_DATA_MODEM_STATIC | NA                             |
| 电池信息（Battery）       | 电压                       | APP_DATA_BATTERY                              | NA                             |
| Neighbor cells            | Neighbor cell measurements | APP_DATA_NEIGHBOR_CELLS                       | `ncell`                        |

​	此外，还有一些异步数据：

| Data type      | Description                         |
| -------------- | ----------------------------------- |
| 按钮（Button） | 按下的按钮的ID                      |
| 冲击（Impact） | 冲击的幅度（单位是重力加速度常数G） |

### 实时配置

​	本例程中的一些选项，支持通过云端进行远程实时配置。

| 实时配置项                         | 描述                                                         | 默认值    |
| ---------------------------------- | ------------------------------------------------------------ | --------- |
| Device Mode                        | 主动（Active）或被动（Passive）：Active指一直上报，而Passive只在运动时才上报 | Active    |
| Active: Wait time                  | Active模式下，每次把数据传送到云端的时间间隔                 | 120秒     |
| Passive: Movement resolution       | Passive模式下，设备在移动时，每次把数据传送到云端的时间间隔  | 120秒     |
| Passive: Movement timeout          | Passive模式下，不论设备是否移动，每次把数据传送到云端的时间间隔 | 3600秒    |
| GNSS timeout                       | 数据采样时，获取GNSS定位的超时时间                           | 30秒      |
| Accelerometer activity threshold   | 设备被判定为移动的加速度阈值                                 | 10  m/s^2 |
| Accelerometer inactivity threshold | 设备被判定为静止的加速度阈值                               | 5 m/s^2   |
| Accelerometer inactivity timeout   | 设备被判定为移动的时间阈值，加速度和时间都超过阈值才被判定为移动 | 1秒       |
| No Data List (NOD)                 | 禁用列表，列表项是Data Type，字符串形式。可以禁用例程上报某一些Data Type的数据 | 空        |

​	这些配置可以另外修改，有以下几种方式：

- 每次与云端建立连接时，从云端同步
- 设备发送更新数据到云端时
- 启动后，从flash中另外加载

### 工作流程图

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined3c2bba7fe38274e499641b6c7a48d79f.png" alt="image-20221206195856563" style="zoom: 67%;" />

<center>
 主动模式流程图
</center>

​	在**主动模式**下，只要超时，例程就会采样新数据，并发送到云端。

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined755d63c0d0111d0689f7cbb2115d0a80.png" alt="image-20221206200043536" style="zoom:80%;" />

<center>
    被动模式流程图
</center>



​	在**被动模式**下，只有两种情况会触发数据上报：

- 检测到运动，并且Resolution定时器超时，默认120s
- 未检测到运动，并且 timeout定时器超时，默认3600s

### 用户接口

| 按钮 | Thingy:91 评估板 | nRF9160 DK 开发板                                            |
| ---- | ---------------- | ------------------------------------------------------------ |
| 1    | 给云端发送数据   | 给云端发送数据                                               |
| 2    | -                | 给云端发送数据；<br />由于nRF9160 DK没有加速度计，故使用此按钮模拟加速度计有运动的情况 |

| 工作状态          | Thngy:91 LED | nRF9160 DK LED |
| ----------------- | ------------ | -------------- |
| 搜索LTE网络       | 黄色闪烁     | LED1 闪烁      |
| GNSS定位中        | 紫色闪烁     | LED2 闪烁      |
| Cloud association | 白色双闪     | LED3 双闪      |
| MQTT连接中        | 绿灯三闪     | LED3 三闪      |
| Publish Data      | 绿灯闪烁     | LED3 闪烁      |
| Active Mode       | 浅蓝色闪烁   | LED4 闪烁      |
| Passive Mode      | 深蓝色闪烁   | LED3和LED4闪烁 |
| 故障              | 红色常亮     | 4个灯闪烁      |
| FOTA升级          | 橙色快闪     | LED1 LED2 闪烁 |
| 升级完成          | 橙色常亮     | LED1 LED2 常亮 |

### A-GPS与P-GPS

> GNSS简介：
>
> - GNSS：全球卫星导航系统，通过多颗同步卫星对地球进行广播。地面上的设备只要接收到三个卫星的信号，根据**预先获得的卫星轨道数据**和**接收到广播的时间差**就可以计算出在地球上的定位。
> - GPS：美国GNSS，每12.5分钟广播一次。
> - A-GPS：辅助GPS，适合室外。设备不用等GPS广播，先从附近蜂窝基站获得大概定位。然后从云服务器的AGPS服务下载这个区域的GPS信息。于是可以缩短设备的GNSS模块首次捕获的时间（2~3分钟缩短到几秒）。
> - P-GPS：预测GPS。设备可以下载长达2周的预测卫星星历数据，使设备能够准确的知道卫星的轨道位置，而无需每2小时连接到网络。并且还能随时间变化权衡精度的下降。P-GPS也能缩短设备定位所需的时间。

​	NCS提供nRFCloud [A-GPS库](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/libraries/networking/nrf_cloud_agps.html#lib-nrf-cloud-agps)和[P-GPS库](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/libraries/networking/nrf_cloud_pgps.html#lib-nrf-cloud-pgps)，让设备能直接从nRF Cloud云端获取这些数据。

​	如果云端是其他云，如 [AWS IoT Core](https://aws.amazon.com/iot-core/), [Azure IoT Hub](https://docs.microsoft.com/en-us/azure/iot-hub/)等。则Location Library也支持从外部输入这些数据（在定位需要用到AGPS/PGPS时，产生一个回调事件，应用层把自己从其他云获取到的AGPS、PGPS数据传入Location Library即可）。

## 3.3. 例程的工程结构

​	Zephyr开发最大的特点是**模块化**。在我的另一篇文章[《理解Zephyr项目的配置与构建系统》](https://jayant-tang.github.io/2022/12/2a39e705bff0/)中，我介绍了Zephyr和Nordic提供的库都可以看成是一个模块，每个模块有自己的Kconfig配置。

​	如果你自己写一个项目，可以把几个`.c`源文件和`.h`头文件丢进`CMakeLists.txt`就行，这样比较简单直接。但如果你想开发好几个独立的复杂模块，并让他们搭配起来工作，就一定要学一下Asset Tracker v2这个例程的写法。

​	首先看项目根目录下的`Kconfig`的包含关系：

```
Kconfig
|-- Asset Tracker v2
|   |-- src/modules/Kconfig.modules_common
|   |-- src/modules/Kconfig.app_module
|   |-- src/modules/Kconfig.cloud_module
|   |-- src/cloud/Kconfig.lwm2m_integration
|   |-- src/modules/Kconfig.data_module
|   |-- src/modules/Kconfig.gnss_module
|   |-- src/modules/Kconfig.modem_module
|   |-- src/modules/Kconfig.sensor_module
|   |-- src/modules/Kconfig.ui_module
|   |-- src/modules/Kconfig.util_module
|   |-- src/modules/Kconfig.led_module
|   |-- src/modules/Kconfig.debug_module
|   |
|   |-- src/cloud/cloud_codec/Kconfig
|   |-- src/watchdog/Kconfig
|   |-- src/events/Kconfig
|   
|-- Zephyr Kernel  // 操作系统内核的配置
|	|-- Kconfig.zephyr
|
`-- 日志打印等级配置
```

​	可以看到，除了Zephyr操作系统内核外，还包含了src目录下许多的模组，这些模组**不是官方库**。而是Nordic官方为这个例程开发的应用模组。你也可以照葫芦画瓢开发自己的应用模组。

​	直接用图形化界面查看，就可以看到Kconfig中的选项了：

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined1fa8d469195b201ac246071efcaf7f16.png" alt="image-20221129154636314" style="zoom: 67%;" />

> ​	分模块开发，除了更加简洁直观、解耦以外，还有一个巨大的好处，那就是每个模组的Log可以在Kconfig中单独开关。这个例程的项目实在是太复杂了，如果所有模组的log都打开，不论是串口还是RTT都是打不下的。

​	每个模组都可以有自己的线程、初始化代码、回调函数等。

## 3.4. 模组间的配合方式

### 程序的调用方式

​	我们知道，不同代码之间互相调用的方式有同步调用和异步调用：

- 同步调用就是，直接调用几个函数，等到它们依次返回后，你才做最后的处理，然后返回；
- 异步调用就是，先把最后的处理写进回调函数，然后通过函数指针注册给其他模组。调用其他模组的函数时不用阻塞，立刻就能返回。等到其他模组处理完后，执行这个回调函数，就成功把参数传回本模组了。

​	以上两种方式，常常发生在我们使用官方库的过程中。我们直接调用官方库中的函数（同步调用），或者把回调函数注册进官方库中（异步调用）。

### Application Event Manager

​	对于我们自己开发的application模组，如果互相之间通信还要调用对方的函数，还要做线程间通信，还要做互斥锁、信号量，那就失去模块化的意义了。

​	Nordic提供了一个叫做Application Event Manager的库，Nordic许多产品级的复杂例程都用到了它。它提供了一个不同模组之间的通信机制：

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedaac0721b512d32f30e3f736718314196.png" alt="image-20221205013810750" style="zoom: 67%;" />

​	每个模组只负责与自己有关的应用和驱动。每个模组可以发布（SUBMIT）事件，也可以订阅（SUBSCRIBE）其他模组的事件。想让其他模组做什么事的时候，发布一个事件就好。而只要订阅了其他模组的事件，那么就可以从Application Event Manager中收到这些事件，之后，只要编写好处理这些事件的回调函数即可。

​	所有的事件都是从Application Event Manager来的，回调函数是注册给Application Event Manager的，不是注册给其他模组。此外，每个模组只需一个回调函数就可以处理所有其他模组发来的事件，不用定义一堆事件入口。

​	由此我们可以体会这个设计的方便之处，每个模组都是独立的，只用关心自己的业务即可。

### 	模组的线程

​	一个模组，根据其业务复杂程度的不同（比如有无状态机），可能自带线程，也可能不带线程。Application Event Manager对这两种模组都兼容。

- 对于带线程的模组。所有的事件都变成消息，存入消息队列。模组的线程里循环等待消息队列的数据，并根据具体情况处理到来的事件。
- 对于不带线程的模组，只需写好事件的回调函数，注册进Application Event Manager即可。

> ​	对于不带线程的模组，必须确保回调函数执行较快，否则将会阻塞Application Event Manager。如果没法确保这一点，就必须给模组写一个单独的线程来处理消息。

如下图：

![image-20221206203957763](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined90d915dd5da0c44ed991754bf34641e7.png)

> ​		对于带线程的模组：
> ​	把Event变成Message，并放入消息队列的工作，都是每个模组自己维护的。Application Event Manager只是提供一个事件回调的接口，各个模组自己通过事件回调函数，把事件放入消息队列。

### 	动态内存

​	模组大多使用静态分配的内存。但是本例程会有一些内容使用动态内存，依赖的是 [Zephyr的堆内存池](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/zephyr/kernel/memory_management/heap.html#heap-v2)。以下内容是使用了动态内存的：

- 模组之间传输的Event
- 即将被发送到云端的数据

​	要发送到云的数据是最耗内存的。所以如果要修改data模组的缓冲区大小，别忘了同时也修改堆的大小。

> 使用`CONFIG_HEAP_MEM_POOL_SIZE`来配置堆的大小。

## 3.5. 例程模组介绍

![image-20221206203138376](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined135c93332bed9faa7ee1a6ec9afbf832.png)

​	如上图，例程中共实现了9个模组。蓝色的是自带线程的，而橙色的是不带线程的。

- [Application module](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/applications/asset_tracker_v2/doc/app_module.html#asset-tracker-v2-app-module)：控制何时采集数据、采集什么数据，并且控制整个例程的其他行为
- [Data module](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/applications/asset_tracker_v2/doc/data_module.html#asset-tracker-v2-data-module)：根据App模块的设定搜集其他模块的数据，存入环形缓冲。并决定何时发送到云端。
- [Cloud module](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/applications/asset_tracker_v2/doc/cloud_module.html#asset-tracker-v2-cloud-module)：负责与云端的连接与数据交互
- [Sensor module](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/applications/asset_tracker_v2/doc/sensor_module.html#asset-tracker-v2-sensor-module)：与 [Thingy:91](thingy:91productpage)开发板上的传感器交互并获得数据
- [GNSS module](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/applications/asset_tracker_v2/doc/gnss_module.html#asset-tracker-v2-gnss-module)：控制nRF9160的GNSS功能
- [User Interface module](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/applications/asset_tracker_v2/doc/ui_module.html#asset-tracker-v2-ui-module)：利用按键和灯提供简易的用户交互接口
- [Utility module](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/applications/asset_tracker_v2/doc/util_module.html#asset-tracker-v2-util-module)：提供对例程进行管理和监控的工具
- [Debug module](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/applications/asset_tracker_v2/doc/debug_module.html#asset-tracker-v2-debug-module)：此模组订阅了所有事件，方便调试，也支持NCS中的Memfault模组。
- [Modem module](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/applications/asset_tracker_v2/doc/modem_module.html#asset-tracker-v2-modem-module)：控制LTE连接

> 要使用debug模组，需要include `../overlay-debug.conf`



## 3.6. 例程代码分析

​	今后会编写其他文章详解此例程的代码。	

​	要了解更多关于此项目的实现内容，可以参考例程的官方说明，非常详细：[nRF9160: Asset Tracker v2 — nRF Connect SDK 2.1.2 documentation (nordicsemi.com)](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/applications/asset_tracker_v2/README.html)

<div style=”page-break-after: always;”></div>

# 4. nRF Cloud API介绍 

nRF Cloud 提供 REST 和 MQTT 两种API。

- REST API 用于**用户到云**、**第三方云到云**的连接；其中少部分API也可被设备调用。
- MQTT API用于**设备和云**的连接

## 4.1. REST API

nRF Cloud REST API文档，参考：[nRF Cloud REST API Documentation](https://api.nrfcloud.com/v1)

###  REST API 认证方式

​	在使用REST API时，不管是用户、设备还是第三方云，在调用API时都需要携带一个Token，来证明消息发出源是可信的。不同的API需要使用不同类型的Token。在API文档中会明确说明此API需要哪种方式认证，例如：

![image-20230311133314758](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinede304fb8c655e32eaeeb2baf71097163d.png)

> - **Simple Token**：也就是**API KEY**，在2.5小节中已经见过。它的地位与用户的云账号密码是一样的，不能泄露。通常是用来调用一些与**用户**账户、配置、用户业务有关的API，例如列举设备、注册设备、批量拉取Message等
> - **JSON Web Token（JWT）**：JWT内包含了设备信息（如UUID）和时间戳等。**设备**可以用自己的X.509私钥生成一个JWT。在调用API时，云端会检查这个JWT是否合法（由于设备已经注册到云端，云端保存了此设备的X.509证书，因此云端可以验证JWT是否合法），如果合法，则允许API的调用。
> - **Service Evaluation Token**：nRF Cloud提供的服务都是需要JWT认证的，而JWT想要认证成功就必须要注册一个设备到云端。如果一个客户只是单纯想快速评估一下服务的效果，不想搞注册设备、生成JWT那一套麻烦事，那么可以申请服务评估令牌（Service Evaluation Token），使用此Token的效果和JWT相同，可在没有注册设备的情况下直接调用相关API。Service Evaluation Token本身也是通过REST API获取的，使用[GenerateServiceEvaluationToken](https://api.nrfcloud.com/v1#tag/Account/operation/GenerateServiceEvaluationToken)和 [GetServiceEvaluationToken](https://api.nrfcloud.com/v1#tag/Account/operation/GetServiceEvaluationToken)两个API即可。要注意这个Token只有30天的试用期限，若想要延长，需要联系Nordic销售。



### REST API 调用示例

​	本小节将使用电脑模拟一台**设备**，通过REST接口注册设备，并使用JWT的认证方式，调用一个REST API。

整个过程分为三个步骤：

- 设备注册（Provision）
- 检查设备注册的结果
- 获取AGPS数据

官方文档可参考：[JWT authentication on nRF Cloud | nRF Cloud Docs](https://docs.nrfcloud.com/Devices/Security/JWT/)。

> ​	整个注册过程和[2.5小节](#2.5. 将设备注册到nRF Cloud云端 (Cloud Provisioning))的流程是一模一样的。但是本小节中展示的注册过程没有使用python脚本，而是使用最基本的HTTP请求来展示REST API调用的过程。

​	在**开始之前**，找一个[在线UUID生成器](https://www.uuidgenerator.net/)，生成一个UUID。本例生成的是：`64520de4-e0a0-45cf-bf56-1f43f80a4f37`，这个UUID就代表一台设备。

​	对于实际的产品，UUID可以是任何字符串。但是Nordic推荐使用9160出厂自带的UUID，你可以在前面加上一些前缀。

> nRF Cloud 全球所有的客户的所有设备，都通过UUID来进行区分。所以防止UUID重复是非常必要的。



**（1）生成CA证书和设备证书**

​	在 [2.5-(3)](#（3）生成你的自签CA证书) 小节中，我们已经通过 Nordic 提供的 python 脚本生成了一套 CA证书文件和私钥。这套utils工具中也包含一套TypeScript脚本，和Python脚本的功能是一样的。你也可以两种都不使用，而只使用OpenSSL进行生成，可参考[JWT authentication on nRF Cloud | nRF Cloud Docs](https://docs.nrfcloud.com/Devices/Security/JWT/)。

​	后面在[2.5-(4)](#（4）签发并安装设备证书)中，我们通过这个**CA证书**给nRF9160签发了**设备证书**，给设备安装了设备独立的私钥。

​	现在，我们要用电脑模拟一台设备，所以，就需要通过刚刚生成的UUID和**CA证书**，来生成一个**新的设备证书**。

​	进入 [2.5-(2)](#（2）获取最新的nRF Cloud Utils工具，并安装好依赖) 中安装utils的文件夹：

```bash
# 在终端中进入utils文件夹后，再进行后续操作

# 进入python工具文件夹
$ cd python/modem-firmware-1.3+/

# 生成设备证书
$ python create_device_credentials.py \
-ca ./my_ca/Jayant-0x12de89cb5ee9589433c9ba08e74bc0eebdfe9ab4_ca.pem \
-ca_key ./my_ca/Jayant-0x12de89cb5ee9589433c9ba08e74bc0eebdfe9ab4_prv.pem \
-c CN \
-l Shanghai \
-o "Nordic Semiconductor K.K." \
-ou "Sales" \
-cn 64520de4-e0a0-45cf-bf56-1f43f80a4f37 \
-e jayant.tang@nordicsemi.no \
-dv 2000 \
-p ./dev_credentials \
-f "Jayant-Device-"
```

> 参数释义：
>
> - `-ca`：CA证书文件
> - `-ca_key`：CA证书密钥文件
> - `-c`：2字符国家代码
> - `-st`：美国、加拿大的州或省代码
> - `-l`：地点
> - `-o`：组织
> - `-ou`：组织部门
> - `-cn`：Common Name。使用nRF CLoud Device ID 或者 MQTT Client ID。这里使用UUID。
> - `-e`：e-mail
> - `-dv`：证书合法天数
> - `-p`：用于生成设备证书的目录
> - `-f`：生成的证书文件名前缀



**（2）生成设备注册信息表格**

​	本小节参考 [REST 设备注册API （ProvisionDevices）](https://api.nrfcloud.com/v1/#tag/IP-Devices/operation/ProvisionDevices)。

​	打开Excel，创建一个新的空表格，并另存为csv格式。

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined514d756d344119867bbeb2b9124f162d.png" alt="image-20221124150045752" style="zoom: 80%;" />

​	在表格中从左往右填入以下内容：

- 第一列：设备ID，这里是UUID

- 第二列：设备子类型，可以写温湿度传感器之类的文字，可以留空；

- 第三列：用于设备分类的标签，这里填[3.5-(4)](#（4）签发并安装设备证书)中nRF9160一样的tag名称就行，也可以留空

- 第四列：固件类型，可以和9160例程填一样的，也可以留空

- 第五列：设备证书。从上一小节的设备证书中，把`xxxx_crt.pem`中的内容拷贝进去即可

  （注意，excel单元格类型要设置成“文本”，否则可能把等号、加号识别为公式）

![image-20221124150540606](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefineda9051f8cfa31ebd725ef6d6620818645.png)

​	保存csv表格，此处给出我的csv文件内容，方便对比格式是否正确：

`fake-device.csv`

```csv
64520de4-e0a0-45cf-bf56-1f43f80a4f37,fake-device,jayant-DK,APP|MODEM,"-----BEGIN CERTIFICATE-----
MIICPTCCAeICFHx8JF+NRorZfBQF0sr+jzKSmg9gMAoGCCqGSM49BAMCMIGSMQsw
CQYDVQQGEwJDTjERMA8GA1UEBwwIU2hhbmdoYWkxIjAgBgNVBAoMGU5vcmRpYyBT
ZW1pY29uZHVjdG9yIEsuSy4xDjAMBgNVBAsMBVNhbGVzMRIwEAYDVQQDDAlub3Jk
aWMuY24xKDAmBgkqhkiG9w0BCQEWGWpheWFudC50YW5nQG5vcmRpY3NlbWkubm8w
HhcNMjIxMTI0MDY1MjEwWhcNMjgwNTE2MDY1MjEwWjCBrTELMAkGA1UEBhMCQ04x
ETAPBgNVBAcMCFNoYW5naGFpMSIwIAYDVQQKDBlOb3JkaWMgU2VtaWNvbmR1Y3Rv
ciBLLksuMQ4wDAYDVQQLDAVTYWxlczEtMCsGA1UEAwwkNjQ1MjBkZTQtZTBhMC00
NWNmLWJmNTYtMWY0M2Y4MGE0ZjM3MSgwJgYJKoZIhvcNAQkBFhlqYXlhbnQudGFu
Z0Bub3JkaWNzZW1pLm5vMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE6OIeO6C0
/kJzfaWUHt/Xg4J6bdAphzmX5sCLGV+oEeSi1sUQKpBLugda2OwG9FxOCikg8ih7
CvMm7C98+fr+nTAKBggqhkjOPQQDAgNJADBGAiEAuCdq6D1K329hwU9e+4S5//2b
upwtaqT+j6Mckpmj6XUCIQCaAqjWRMXMiOd/pXRkcf7SjKyZifBnxoepRqbNyKUG
OA==
-----END CERTIFICATE-----
"
```

> ​	注意，这个表格是作为REST API的参数传入的，而云端会通过正则表达式来检查内容是否合法，有时多一个少一个回车、空格都不行，正则表达式可参考[ProvisionDevices](https://api.nrfcloud.com/v1#tag/IP-Devices/operation/ProvisionDevices)的API说明：
>
> ![image-20230311135339410](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined02c684cfcd18a2ed0e40586aeff5dc7e.png)



**（3）利用REST接口注册设备**

​	使用[ProvisionDevices](https://api.nrfcloud.com/v1/#tag/IP-Devices/operation/ProvisionDevices)接口。这属于**用户到云**的接口调用，需要使用**API key**。

```bash
# 向nRF Cloud发送请求，注册设备。
$  curl --request POST --url https://api.nrfcloud.com/v1/devices \
--header 'Authorization: Bearer 3c967ecbd9f3cxxxxxxxxxxfa73cf37049983' \
--header 'content-type: text/csv' \
--data-binary @./fake-device.csv
```

>注意：
>
>- 把API Key改成你自己的API Key
>- 用curl发送csv文件时，必须使用二进制流。否则curl可能会丢掉文件末尾的换行符。也可以不用curl，而是通过Postman软件来进行API的调用测试。

​	云端返回结果：

```
{"bulkOpsRequestId":"01GK0NECJPXVNDNKVA4XE98HDE"}
```

​	假如这是一次真实的批量注册，这个bulkOpsRequestId需要记录下来，用于调用[FetchBulkOpsRequest](https://api.nrfcloud.com/v1/#operation/FetchBulkOpsRequest) API。这个API的作用是用来检查自己批量注册的进度。但是本次是一次模拟，只注册了一个设备，所以很快就能注册完成。

> FetchBulkOpsRequest使用方法：
>
> url的最后是上面获取的bulkOpsRequestId
>
> ```bash
> curl --request GET \
> --url https://api.nrfcloud.com/v1/bulk-ops-requests/01GK0NECJPXVNDNKVA4XE98HDE \
> -H "Authorization: Bearer 3c967ecbd9fxxxxxxxxxxxxxx3cf37049983"
> ```
>
> 返回结果：
>
> ```json
> {
> 	"bulkOpsRequestId":"01GK0NECJPXVNDNKVA4XE98HDE",
>     "status":"SUCCEEDED",
>     "endpoint":"PROVISION_DEVICES",
>     "requestedAt":"2022-11-29T03:03:48.054Z",   // 这个时间应该是GMT+1的时间
>     "completedAt":"2022-11-29T03:03:51.365Z",
>     "uploadedDataUrl":"https://bulk-ops-requests.nrfcloud.com/a9d25242-adad-479e-b526-xxxxxxxxxxxx/provision_devices/01GK0NECJPXVNDNKVA4XE98HDE.csv"
> }
> ```



​	利用[FetchDevice](https://api.nrfcloud.com/v1/#tag/All-Devices/operation/FetchDevice)接口来获取新注册的这个设备的信息，其中`{device-id}`要换成UUID：

```bash
$ curl --request GET \
--url https://api.nrfcloud.com/v1/devices/{device-id} \
--header 'Authorization: Bearer 3c967ecbxxxxxxxxxxxxe81cfa73cf37049983'
```

​	返回结果：

```json
{
    "id":"64520de4-e0a0-45cf-bf56-1f43f80a4f37",
    "tags":[
        "jayant-DK"
    ],
    "tenantId":"a9d25242-adad-479e-b526-xxxxxxxxxxx",
    "$meta":{
        "createdAt":"2022-11-29T03:03:53.127Z"
    },
    "name":"64520de4-e0a0-45cf-bf56-1f43f80a4f37",
    "type":"Generic",
    "subType":"fake-device",
    "firmware":{
        "supports":[
            "APP",
            "MODEM"
        ]
    },
    "state":{
        "desired":{
            "nrfcloud_mqtt_topic_prefix":"prod/a9d25242-adad-479e-b526-777082c5b7c5/",
            "pairing":{
                "state":"paired",
                "topics":{
                    "d2c":"prod/a9d25242-adad-479e-b526-777082c5b7c5/m/d/64520de4-e0a0-45cf-bf56-1f43f80a4f37/d2c",
                    "c2d":"prod/a9d25242-adad-479e-b526-777082c5b7c5/m/d/64520de4-e0a0-45cf-bf56-1f43f80a4f37/+/r"
                }
            }
        },
        "version":3,
        "metadata":{
            "desired":{
                "nrfcloud_mqtt_topic_prefix":{
                    "timestamp":1669691031
                },
                "pairing":{
                    "state":{
                        "timestamp":1669691031
                    },
                    "topics":{
                        "d2c":{
                            "timestamp":1669691031
                        },
                        "c2d":{
                            "timestamp":1669691031
                        }
                    }
                }
            }
        }
    }
}
```

​	可以看到里面包含设备的信息，除了之前自己在CSV表格中填写的信息外，还包括MQTT的topic、时间戳等信息。

​	设备注册成功后，在网页端也已经可以看到这个模拟的设备：

![image-20221124154802151](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedf4b44de94a9fd831fa7f45c1ac755fe2.png)



**（4）生成JWT**

**设备到云**（D2C）的API调用需要JWT认证，我们先生成一个JWT：

打开[ jwt.io](https://jwt.io/)，上方选择ES256签名算法，然后PAYLOAD中填入：

```json
{
    "sub": "你的UUID"
}
```

下方公钥、私钥区域粘贴上一小节中生成的设备证书的公钥（_pub.pem）和私钥（_prv.pem）的内容。

（注意，不是CA证书，而是设备证书）

![image-20221129114051110](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined7d480a52dd5d3f8724dda08e7dcaf38b.png)

左下角显示"Signature Verified"，则说明公钥与私钥是成对的。可以把左侧编码好的JWT复制出来，这就是设备与云端通信所需要的 Token：

```
eyJhbGciOiJFUzI1Nixxxxxxxxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxx78F5NXw
```



**（5）测试一个设备API接口**

​	我们利用[GetAssistanceData](https://api.nrfcloud.com/v1/#operation/GetAssistanceData)来测试接口，在官方API文档页面，我们可以看到：

![image-20221130102929376](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined0ad74db02a98bdce349c0f04f7896e2f.png)

- 展示了URL、参数
- 有两种请求方式，Basci Request和 Cuscom Request，后者需要携带更多参数
- 提供了`curl`命令示例，如何携带参数
- 展示了认证方式，有 API Key 和 JWT两种，展开有详细说明

​	下方是一个Custom Request的调用示例，与API文档中的例子不同，没有使用`-d`选项，这里是直接把参数写在了URL中：

```bash
$ curl --request GET \
  --url 'https://api.nrfcloud.com/v1/location/agps?requestType=custom&customTypes=1%2C3%2C4%2C6%2C7%2C8%2C9&mcc=310&mnc=410&tac=36874&eci=84485647' \
  --header 'Accept: application/octet-stream' \
  --header 'Authorization: Bearer eyJhbGciOiJFUzI1Nxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxm6Hx78F5NXw' \
  --header 'range: bytes=0-500'
```

​	请求已经成功返回，但是返回的数据是二进制内容，curl提示我们它不会展示二进制内容，以免打乱终端文字。

![image-20221129114408304](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedd7202cbfd6f7ed2897514a67ced5064d.png)

​	也可以用Postman软件进行测试，结果是一样的，返回206，说明数据请求成功：

![image-20221129114544096](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined80765f45129152db4d3d82909de3f73d.png)



**（6）总结：**

​	本小节展示了[ProvisionDevices](https://api.nrfcloud.com/v1/#tag/IP-Devices/operation/ProvisionDevices)，[FetchBulkOpsRequest](https://api.nrfcloud.com/v1/#operation/FetchBulkOpsRequest)，[FetchDevice](https://api.nrfcloud.com/v1/#tag/All-Devices/operation/FetchDevice)，[GetAssistanceData](https://api.nrfcloud.com/v1/#operation/GetAssistanceData)这5个REST接口的调用。大多数接口都是云到云的，需要用户的APP key来进行认证。最后一个接口展示了设备到云的REST接口调用，需要使用JWT来进行认证。



## 4.2. MQTT API

​	nRF Cloud是部署在亚马逊AWS上的，并且使用[AWS IoT Core](https://docs.aws.amazon.com/iot/latest/developerguide/iot-gs.html)的MQTT broker。

MQTT API的通信，只要订阅topic即可。这里需要有2个topic，`d2c`和`c2d`。

- `d2c`：设备发布，云端订阅
- `c2d`：云端发布，设备订阅

​	只要每个设备能获得这两个topic，就能与云端进行通信。这个topic可以通过REST API获得，下一小节会介绍。但是实际开发应用的时候，并不需要关心，因为nRF Cloud Library已经帮我们封装好了，我们只需调用`connect()`，`send()`之类的就好了。

### MQTT topic前缀的获取

​	用户可以通过REST API获取topic前缀，接口是 [FetchAccountInfo](https://api.nrfcloud.com/v1/#operation/FetchAccountInfo)。需要使用用户的API Key进行认证。接口会返回很多数据，其中就包含：

```json
{
	"mqttEndpoint": "mqtt.nrfcloud.com",
	"mqttTopicPrefix": "prod/a5592ec1-18ae-4d9d-bc44-xxxxxxxxx/"
}
```

​	不用REST API，也可以在网页端获取。点击右上角下拉菜单-Teams：

![image-20221130132356346](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined095ea257a2649a8628c4eee130532785.png)

​	可以看到Team的信息，其中就有team id。`mqttTopicPrefix`就是`prod/<team_id>`。

### 云端的认证

​	所有到AWS IoT MQTT broker的连接都必须使用在8883端口上进行的Mutual TLS。所有用MQTT的设备都必须有一个[X.509 device certificate](https://docs.nrfcloud.com/Devices/Security/Security/#authentication)，并且已经**注册到云端（Provisioned）**。这正是我们在[3.5](#3.5. 将设备注册到nRF Cloud云端 (Cloud Provisioning))和[4.1](#REST-API-调用示例)中已经介绍过的部分。

### Topic

​	nRF Cloud部署在AWS上，除了[AWS保留的topic](https://docs.aws.amazon.com/iot/latest/developerguide/reserved-topics.html)外，还有一些是nRF Cloud自定义的。官方文档请参考：

[nRF Cloud MQTT topics | nRF Cloud Docs](https://docs.nrfcloud.com/APIs/MQTT/Topics/)

### 代码分析

​	有关nRF Cloud Library底层的细节，官方文档为 [nRF Cloud — nRF Connect SDK 2.1.2 documentation (nordicsemi.com)](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/2.1.2/nrf/libraries/networking/nrf_cloud.html)。

​	在[3.5.3](#3.5.3. 数据传输相关代码)中，我们知道9160是通过Cloud Wrapper API包装了nRF Cloud Library相关的接口进行的。其中发送到云端就是`cloud_wrap_batch_send()`：

```c
int cloud_wrap_batch_send(char *buf, size_t len, bool ack, uint32_t id)
{
	int err;
	struct nrf_cloud_tx_data msg = {
		.data.ptr = buf,
		.data.len = len,
		.id = id,
		.qos = ack ? MQTT_QOS_1_AT_LEAST_ONCE : MQTT_QOS_0_AT_MOST_ONCE,
		.topic_type = NRF_CLOUD_TOPIC_BULK,
	};

	err = nrf_cloud_send(&msg);
	if (err) {
		LOG_ERR("nrf_cloud_send, error: %d", err);
		return err;
	}

	return 0;
}
```

​	这里面，准备好要发送的数据`msg`即可，数据类型是`nrf_cloud_tx_data_msg`。Topic是`NRF_CLOUD_TOPIC_BULK`。

​	这恰好就是[官方MQTT API手册](https://docs.nrfcloud.com/APIs/MQTT/Topics/#message-topics)中的topic，作用是发送一组bulk数据。只要仿照wrapper中的格式，就可以写出自己的发送函数。

# 5. 总结

​	nRF Cloud是一个物联网云，提供最基本的设备管理和OTA等功能。此外还提供收费的Location Service，含AGPS、PGPS、基站定位、WiFi定位等功能。不局限于Nordic产品，任何产品都可以连。

​	nRF9160具有LTE-M和NB-IoT联网能力，支持GPS。支持eDRX和PSM低功耗，休眠时功耗低至2.7uA。除了本身的Cortex M33应用核可开放开发以外，还可作为外挂通讯模组进行开发。SLM扩展的AT指令也支持多种功能。

​	
