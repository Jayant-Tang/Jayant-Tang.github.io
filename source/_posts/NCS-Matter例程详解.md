---
title: NCS Matter例程详解
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2025-01-03 16:02:54
cover: null
tags:
- Nordic
- Matter
categories:
- Matter
cnblogs:
  postId: '18650736'
  url: https://www.cnblogs.com/jayant97/articles/18650736
  lastPublishedAt: '2026-07-06T18:20:52+08:00'
  sourceHash: sha256:219b20142f8e9e9b4a9fd089074df5f1fd65b9a6cf27af7743a7525a3ac8a4a7
  status: imported
  postType: Article
---

本文将会简单介绍Nordic Matter开发流程，然后详细分析一个Matter over Thread窗帘例程代码


# 1. Matter简介

## 什么是Matter？

从产品角度：

- Matter是一个**跨生态**的智能家居标准，有众多大厂支持
- 消费者购买Matter产品无需考虑品牌、部署。只要支持Matter，都是开箱即用的

![image-20250103161208933](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103161208933.webp)

从技术角度：

- Matter是基于IPv6的**应用层**协议(CHIP, Connect Home over IP)
- 建立在成熟的网络协议之上（Wi-Fi/Thread/Ethernet ）
- Matter有一套成熟的设备发现和入网机制（UDP-SD或Bluetooth LE）
- Matter协议是安全的。设备必须经过认证才能加入Matter网络；入网后，设备会获得一个证书用于加密通讯。

![image-20250103161824130](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103161824130.webp)

## 开发Matter其实是在开发数据模型

Matter规定了许多[设备类型](https://matter.cn/dev/device-type)，厂商只能开发Matter已经规定的设备类型。如下图为Matter1.0发布时规定的部分设备类型：

![image-20250103163009545](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103163009545.webp)

这些不同的设备类型，其实就是不同的数据模型。在Matter协议栈中，应用层之下就是Data Model层：

![image-20250103163420400](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103163420400.webp)

- Node：一个具有完整Matter stack的实体，具有唯一的网络地址。大多数情况下，一个设备就是一个Node。
- Endpoint：功能交互端点。例如一个Node可以有“锁”和“温度传感器”两个Endpoint。
- Cluster：每个Endpoint可能有多个具体的功能集合，就是cluster。例如锁的控制、电池电量的上报
- Attribute/Events/Commands：也就是所谓的属性/事件/服务，是数据实体。

> Endpoint0比较特殊，是必须的，它负责Matter基本功能的Cluster。
>
> 一个具体的示例：
>
> ![image-20250103164446104](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103164446104.webp)
>
> 一个门锁设备，Endpoint0 提供基本信息、访问控制、配网等Matter基本功能的Cluster。
>
> Endpoint1提供Identify和门锁基本功能的Cluster。
>
> 每个Cluster由多个Attributes组成，Attributes就是实际存储器中的变量或常量

## Matter的网络拓扑

由于Matter只是应用层协议，所以Matter的网络拓扑就是它采用的底层通讯方式的网络拓扑：

![image-20250103164904210](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103164904210.webp)

Matter网络建立后，互相之间通过前述数据模型进行交互。手机、智能音箱等可以操控所有设备。

- Wi-Fi：只要AP覆盖到的地方，设备都可以入网。AP之间通过以太网互联，在家庭中很常见。
- Thread：功耗更低，且Thread设备之间可以构成Mesh，只要多级跳转最终能连接到Border Router即可。一些位于中转位置的节点最好是常供电的（如Light Switch）。
- 其他本地网络：如Zigbee，BLE Mesh等未在Matter标准中使用的协议，需要一个**Matter Bridge**来做中转。Matter Bridge负责向Matter网络提供数据模型，处理Matter交互，然后将其转换为其他协议。Matter并不规定Matter之外的协议如何处理，因此开发者可以让Bridge自由适配任何其他协议。
- 互联网：Matter协议是局域网的。Matter生态商（如苹果、谷歌、亚马逊、三星）负责让你的手机可以通过外网发送到家中的控制中枢，从而控制家中的Matter设备。

> Thread网络是支持IPv6 UDP的。但Thread网络要和其他网络连接，需要边界路由器（OTBR， OpenThread Border Router）。
> Apple Home Pod已经内置Border Router。此外iPhone 15 Pro和Pro Max已经内置Thread网卡，可以直接控制Thread设备。

## Matter设备发现与入网

![image-20250103165708864](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103165708864.webp)

BLE是目前最常见的入网方式，流程为：

1. 设备发出BLE广播
2. 【设备发现】手机扫描二维码后，或者输入Manual Pairing Code后，根据Pairing Code信息自动连接对应的BLE广播
3. 【PASE】二者通过Out-of-band信息（二维码中的passcode）建立加密通道。确认设备经过认证，安装后续加密通讯需要的证书（NOC, Node Operational Certificate）。然后设备入网（传输Wi-Fi密钥，Thread网络Key等等），这个过程无需人工输入密码。
4. 【CASE】设备入网后，每次通讯都要建立一个新的AES加密连接。

以上过程在SDK中都已经提供，无需再开发。

其他的设备发现方式还有DNS-SD或Wi-Fi Soft-AP。

## Matter Controller

Matter Controller是网络中非常重要的节点，在消费者家中负责设备的远程控制和入网。如Apple HomePod，Google Nest, Amazon Alexa。

在Matter开发环境中，也需要Matter Controller来调试Matter设备。可以使用CHIP Tool作为Matter Controller。可以直接用命令行的方式直观地进行配网、数据模型交互。

![image-20250103170010741](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103170010741.webp)

CHIP Tool可以运行在Linux和mac OS环境中（Windows中需要Linux虚拟机）：

![image-20250103171447107](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103171447107.webp)

CHIP Tool是一个软件命令行工具，为了控制Matter设备，它所在的机器需要有BLE和IP网络。其中IP网络分为Thread, Wi-Fi和以太网。如果你是开发Matter Over Wi-Fi，则需要BLE和Wi-Fi/以太网；如果你是开发Matter Over Thread，则需要BLE和Thread。

- Wi-Fi/以太网：PC和树莓派自带Wi-Fi或以太网，无需额外准备。如果是Windows内的Linux虚拟机，则需要确保Linux虚拟机和宿主机在同一局域网下（Bridge模式）。
- Thread：PC和树莓派通常没有Thread网卡，因此需要一个Nordic开发板来充当网卡。比较推荐的是上图的nRF52840 Dongle，然后烧录Thread RCP例程(`nrf/samples/openthread/coprocessor`)
- BLE：PC和树莓派自带蓝牙网卡，无需额外准备。如果是Windows内的Linux虚拟机，则需要一个USB蓝牙网卡，通过USB透传进虚拟机。购买一个USB网卡也可以；使用Nordic nRF52840 Dongle也可以，烧录HCI_USB例程（`zephyr/samples/bluetooth/hci_usb`）；如果只有nRF52832（无USB），也可以烧录HCI_UART例程（`zephyr/samples/bluetooth/hci_uart`），按照例程文档说明通过命令行挂载一下蓝牙网卡即可。

# 2. Matter开发流程

Matter SDK是开源的，用Nordic SDK和硬件开发和评估Matter也不需要申请资质，软件全部是公开可下载的。开发前，先下载好[技术文档](https://csa-iot.org/developer-resource/specifications-download-request/)。

下载对应Matter版本的3个文档：

- Matter Core Specification
- Matter Device Library Specification
- Matter Application Cluster Specification

但最终要开发Matter产品并上市，还是要成为CSA会员并对设备进行认证。参考[认证流程](https://docs.nordicsemi.com/bundle/ncs-2.8.0/page/nrf/protocols/matter/end_product/certification.html#ug-matter-device-certification)。

## 芯片选型

主要是根据Flash RAM占用情况选用合适的芯片。Nordic有多个Matter例程，并且提供了它们在不同开发板上的[资源占用情况](https://docs.nordicsemi.com/bundle/ncs-2.8.0/page/nrf/protocols/matter/getting_started/hw_requirements.html#ram_and_flash_memory_requirements)。最好按照Nordic提供的芯片组合来开发自己的Matter产品，这样开发量最小：

![image-20250103170553365](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103170553365.webp)

> 注意：NCS中，通过无线进行OTA一定需要双分区。因此考虑flash占用时，需要把上表中的Application ROM加上你自己的应用代码空间，再翻倍。
>
> 由于Matter应用比较大，因此往往需要一个外部SPI/QSPI flash作为第二分区（secondary slot），其大小不低于内部Flash（52840为1M Bytes, 5340为1.5M Bytes）。

## 申请或购买Nordic开发板，直接在开发板运行Matter例程

按照NCS [Matter例程文档](https://docs.nordicsemi.com/bundle/ncs-2.8.0/page/nrf/protocols/matter/getting_started/adding_bt_services.html)在开发板上编译和烧录，运行例程。

## 进行项目开发

搭建Matter开发环境，[安装CHIP Tool](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/protocols/matter/getting_started/tools.html#chip_tool_for_linux_or_macos)；进行软件与硬件开发；[添加自己的endpoint, cluster](https://docs.nordicsemi.com/bundle/ncs-2.8.0/page/nrf/protocols/matter/getting_started/adding_clusters.html)。

如有必要，还可以[添加Matter之外的蓝牙广播和蓝牙服务](https://docs.nordicsemi.com/bundle/ncs-2.8.0/page/nrf/protocols/matter/getting_started/adding_bt_services.html)。

## 产品优化

[优化功耗](https://docs.nordicsemi.com/bundle/ncs-2.8.0/page/nrf/protocols/matter/getting_started/low_power_configuration.html)，主要是网络的功耗和一些外设的功耗。

## 生成Factory Data

认证通过后，进行产测工具的开发，通过证书为每台设备[生成Factory Data](https://docs.nordicsemi.com/bundle/ncs-2.8.0/page/nrf/protocols/matter/end_product/factory_provisioning.html)

## Matter文档与SDK

以上只是一个粗略的流程总结，具体开发步骤还是要参考Matter文档。

Nordic官方文档：

- [NCS - 协议简介 - Matter](https://docs.nordicsemi.com/bundle/ncs-2.8.0/page/nrf/protocols/matter/index.html)

- [NCS - 例程文档 - Matter](https://docs.nordicsemi.com/bundle/ncs-2.8.0/page/nrf/samples/matter.html)

- [Matter官方文档（Nordic相关）](https://docs.nordicsemi.com/bundle/ncs-2.8.0/page/matter/index.html)

  > Matter官方文档可能出现一些NCS已经做好了，因此不必要再重复的内容（如编译Matter SDK）。为了避免混淆，最好主要参考前两个NCS中的文档。必要时，前两个文档会跳转到第三个文档中的内容。



NCS中已经包含了 Matter SDK （https://github.com/project-chip/connectedhomeip）作为子仓库，无需再单独下载Matter SDK。（modules/lib/matter）

NCS中Matter例程的路径为：`nrf/samples/matter/`
此外还有两个成熟的商业级例程：
         `nrf/applications/matter_weather_station`
        ` nrf/applications/matter_bridge`

# 3. 运行Matter窗帘例程

本次演示首先通过nRF Connect for VS Code中的“Copy a sample”功能，拷贝了`nrf/samples/matter/window_covering`工程。工程放在SDK外部。

![image-20250103173810111](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103173810111-1735897091967-1.webp)

并且把SDK和这个工程放在同一个VS Code workspace中，这样做是为了方便后续代码跳转阅读。

> 注意最新的nRF Connect for VS Code插件进行了更新：要在build界面选择SDK和toolchain的版本。
>
> ![image-20250103173843411](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103173843411.webp)

编译烧录流程参考[例程文档](https://docs.nordicsemi.com/bundle/ncs-2.8.0/page/nrf/samples/matter/window_covering/README.html)。烧录之后就可以用CHIP Tool进行配网和控制。

如果有iPhone手机和HomePod，则可以直接配置到Apple Home中。

通过串口LOG的网址打开二维码，Home APP中扫描即可。由于例程用的证书都是一样的，用例程文档里的二维码也可：

![image-20250103173947629](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103173947629.webp)

![image-20250103173951338](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103173951338.webp)

窗帘开关反映为LED的亮度。可以用Button控制窗帘，也可以在手机APP中控制。

更多按钮和LED的功能，参考例程文档。

![image-20250103174025955](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103174025955.webp)

# 4. 窗帘例程代码解析

## 工程文件分析

![image-20250103174121007](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103174121007.webp)

以下文件和NCS 2.6.x之前版本的作用是一样的：

- 工程通用的配置文件prj.conf/ prj_release.conf
- boards/下的配置文件与设备树overlay
- 用于Flash分区的Partition Manager文件（yml）
- 工程配置菜单文件Kconfig 
- 工程源码管理文件CMakeLists.txt

然后是新增的内容：

**sysbuild**

Sysbuild代替了原来的parent-child image配置. 是为了多镜像工程服务的。

每个子镜像也可以单独添加配置，和原来的child_image/文件夹差不多。

但是Sysbuild也可以添加一个High-level的配置，这些High-level的配置将应用到所有子镜像（App, Bootloader, 以及可能存在的网络核固件）中：

- Kconfig.sysbuild 与 sysbuild.conf
- sysbuild.cmake (本例程中未使用)

![image-20250103174616698](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103174616698.webp)

此外，有一部分应用层代码并不位于本工程中，而是位于`nrf/samples/matter/common`
这是所有Matter例程共用的一部分代码。这部分代码是CMakeLists.txt中下面这一行引入的：

```cmake
# Include all source files that are located in the Matter common directory.
include(${ZEPHYR_NRF_MODULE_DIR}/samples/matter/common/cmake/source_common.cmake)
```

## 代码分析

### main.cpp

首先看main.cpp

```c++
int main()
{
	CHIP_ERROR err = AppTask::Instance().StartApp();

	LOG_ERR("Exited with code %" CHIP_ERROR_FORMAT, err.Format());
	return err == CHIP_NO_ERROR ? EXIT_SUCCESS : EXIT_FAILURE;
}
```

例程代码是C++写的，但是开发者后续也可添加C代码，和其他的NCS工程开发起来没有什么区别。C代码添加自己的线程即可，和C++互相不干扰。

main函数中，只是调用了AppTask这个类的启动函数，便启动了Matter协议栈。

并且，正常情况下这个函数应该永远不退出。

### AppTask.h

```cpp
class AppTask {
public:
	static AppTask &Instance()
	{
		static AppTask sAppTask;
		return sAppTask;
	};

	CHIP_ERROR StartApp();

	static void IdentifyStartHandler(Identify *);
	static void IdentifyStopHandler(Identify *);

private:
    AppTask() = default; // 这一行是我添加的

	CHIP_ERROR Init();
	void ToggleMoveType();

	static void OpenHandler(const WindowButtonAction &action);
	static void CloseHandler(const WindowButtonAction &action);

	static void ButtonEventHandler(Nrf::ButtonState state, Nrf::ButtonMask hasChanged);

	OperationalState mMoveType{ OperationalState::MovingUpOrOpen };
	bool mMovementTimerActive{ false };
	bool mOpenButtonIsPressed{ false };
	bool mCloseButtonIsPressed{ false };
	bool mMoveTypeRecentlyChanged{ false };
};
```

AppTask这个类，涵盖了应用层的所有任务。

注意到，这个类采用了单例模式，其默认构造函数没有定义（为了安全，应该改为private，空的构造函数）。

意思是，这个类只能有1个对象实例，代码的其他地方不能通过静态定义或者动态allocate这个对象。
要调用这个类的函数时，必须使用`AppTask::Instance()` 这个唯一的实例对象，例如：

```cpp
CHIP_ERROR err = AppTask::Instance().StartApp();
```

> 这也是非常合理的，因为这个类管理的是当前设备的硬件行为。一块板子上的硬件外设本来就有唯一性，定义多个对象实例没有意义。

### AppTask.cpp

前面看到，在main.cpp中执行了AppTask::Instance().StartApp()这个函数。

```c++
CHIP_ERROR AppTask::StartApp()
{
	ReturnErrorOnFailure(Init());

	while (true) {
		Nrf::DispatchNextTask();
	}

	return CHIP_NO_ERROR;
}
```

它首先初始化了Matter。然后处理事件循环。

#### Matter初始化

```cpp
CHIP_ERROR AppTask::Init()
{
	/* 初始化Matter协议栈 */
	ReturnErrorOnFailure(Nrf::Matter::PrepareServer(Nrf::Matter::InitData{ .mPostServerInitClbk = [] {
		WindowCovering::Instance().PositionLEDUpdate(WindowCovering::MoveType::LIFT);
		WindowCovering::Instance().PositionLEDUpdate(WindowCovering::MoveType::TILT);
		return CHIP_NO_ERROR;
	} }));
	
    /* 注册开发板按钮回调函数 */
	if (!Nrf::GetBoard().Init(ButtonEventHandler)) {
		LOG_ERR("User interface initialization failed.");
		return CHIP_ERROR_INCORRECT_STATE;
	}

	/* 注册Matter事件回调函数 */
	ReturnErrorOnFailure(Nrf::Matter::RegisterEventHandler(Nrf::Board::DefaultMatterEventHandler, 0));

    /* 启动Matter相关业务 */
	return Nrf::Matter::StartServer();
}
```

`AppTask::Init()`中进行了Matter协议栈的初始化。

所有`Nrf::`类中的函数，都是`nrf/samples/matter/common`提供的，不是Matter SDK原始的API。其目的是封装和简化Matter例程代码。

第一部分是初始化Matter Stack

第二部分是注册硬件按钮回调函数

第三部分是注册Matter事件回调函数，这部分最重要。设备何时开启蓝牙广播、何时入网、断开连接，都在里面有回调.现在注册的是common里面提供的默认回调函数。你可以把这个函数拷贝出来到AppTask.cpp，并重写自己的功能，再注册回去。

第四部分是开启Matter协议栈。

#### AppTask事件循环

这个事件循环，其实和Zephyr Work Queue (k_work)的功能差不多。在各种Matter或者硬件中断的回调函数中，我们希望能够快速退出回调，防止卡中断或者协议栈，因此可以把一些耗时的任务提交到Workqueue中去运行（Workqueue有单独的线程）。

使用Zephyr Work Queue 当然是可以的，但是比较麻烦的是每次都要自己定义一个k_work结构体，还要初始化这个work，注册k_work的回调，重复性的代码比较多。

Matter例程是C++编写的，因此利用了C++的Lambda表达式可以作为匿名函数的功能：
简单理解，Lambda表达式就是：

```c++
[args...] { 
      ... // your code
} 
```

这是个匿名函数。直接把它整体丢进队列，事件循环中就可以从队列中取出这个函数，然后执行了。省去了定义函数名和函数指针的麻烦，例如：

```c++
// Matter Identify事件回调，要求设备LED闪烁，以辨识设备
void AppTask::IdentifyStartHandler(Identify *)
{
    // 此函数的参数，就是一个完整的lambda表达式，整体作为匿名函数传参
	Nrf::PostTask([] {
		WindowCovering::Instance().GetLiftIndicator().SuppressOutput();
		Nrf::GetBoard().GetLED(Nrf::DeviceLeds::LED2).Blink(Nrf::LedConsts::kIdentifyBlinkRate_ms);
	});
}
```

此外，[]中的内容叫作捕获组，可以把当前函数的局部变量捕获到lambada表达式中，当作参数传递使用，非常方便。例如：

```c++
// 硬件按钮事件回调，需要调用比较耗时的开启或关闭窗帘函数
void AppTask::ButtonEventHandler(Nrf::ButtonState state, Nrf::ButtonMask hasChanged)
{
	if (OPEN_BUTTON_MASK & hasChanged) {
		WindowButtonAction action =
			(OPEN_BUTTON_MASK & state) ? WindowButtonAction::Pressed : WindowButtonAction::Released;
		Nrf::PostTask([action] { OpenHandler(action); });
	}

	if (CLOSE_BUTTON_MASK & hasChanged) {
		WindowButtonAction action =
			(CLOSE_BUTTON_MASK & state) ? WindowButtonAction::Pressed : WindowButtonAction::Released;
		Nrf::PostTask([action] { CloseHandler(action); });
	}
}
```

### zcl_callbacks.cpp

前面Matter协议栈初始化后，BLE和Thread就全部被Matter接管并初始化好了，无需开发者再关注。
包括配网的功能已经全部被SDK实现。

Matter要开发的，其实就是如何处理数据交互（Endpoint, Cluster, Attributes）。

Matter的数据模型都是通过ZAP Tool进行图形化编辑的，编辑后自动生成代码。
但是自动生成的代码是空的，应用层需要实现这个代码。

自动生成的`../zap-generated/endpoint_config.h`中，把函数指针注册给了Matter协议栈：

![image-20250920231317390](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/45cd4e2d736be64446da8f5e179a9a73.png)

这个函数，在Matter协议栈内部是Weak定义的：

```cpp
// modules\lib\matter\src\app\clusters\window-covering-server\window-covering-server.cpp
void __attribute__((weak))
MatterWindowCoveringClusterServerAttributeChangedCallback(const app::ConcreteAttributePath & attributePath)
{
    PostAttributeChange(attributePath.mEndpointId, attributePath.mAttributeId);
}
```

因此，我们可以自己覆盖这个函数的定义，重新实现。

例如，例程在应用层提供的``zcl_callbacks.cpp`中，就实现了当自己Attributes被网络中的其他设备修改时，要执行的回调函数：

```cpp
void MatterWindowCoveringClusterServerAttributeChangedCallback(const app::ConcreteAttributePath &attributePath)
{
	if (attributePath.mEndpointId == WindowCovering::Endpoint()) {
		switch (attributePath.mAttributeId) {
		case Attributes::TargetPositionLiftPercent100ths::Id:
			WindowCovering::Instance().StartMove(WindowCovering::MoveType::LIFT);
			break;
		case Attributes::TargetPositionTiltPercent100ths::Id:
			WindowCovering::Instance().StartMove(WindowCovering::MoveType::TILT);
			break;
		case Attributes::CurrentPositionLiftPercent100ths::Id:
			WindowCovering::Instance().PositionLEDUpdate(WindowCovering::MoveType::LIFT);
			break;
		case Attributes::CurrentPositionTiltPercent100ths::Id:
			WindowCovering::Instance().PositionLEDUpdate(WindowCovering::MoveType::TILT);
			break;
		default:
			WindowCovering::Instance().SchedulePostAttributeChange(attributePath.mEndpointId,
									       attributePath.mAttributeId);
			break;
		};
	}
}
```

每个Attribute都有自己的ID，通过ID来判断是哪个Attribute被修改了。



### WindowCovering.cpp

WindowCovering类，提供的就是“真正”的窗帘控制代码了。前面ZCL的回调之中调用的就是WindowCovering类的代码。

但是实际上这里是用LED的亮度变化来模拟窗帘的打开程度。这个class的代码不重要，开发者完全可以把它删了改成自己的。只需要能够完美处理zcl_callback.cpp中的回调事件即可。

而且由于同时支持竖向窗帘和横向窗帘，这个类的代码写的比较复杂。

这里简单分为两类：

`zcl_callbacks.cpp`

![image-20250920231858141](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/aa8f2907c3af728bbc1d71f0d6ade504.png)

- 窗帘目标位置发生改变：执行StartMove函数。注意这里并没有传递参数，告知具体的目标位置是什么。因为Attribute是随时可读的，可以在后续具体执行运动时，再去Get这个Attribute值。
- 窗帘实际位置发生改变：更新LED状态。同理，也不需要传参。

`StartMove`内部的调用逻辑很多，这里直接跳到以下函数：

![image-20250920232750168](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/ff7802e0897e25f68a767eefe6a47b2f.png)

从前面的`StartMove(….LIFT)`，调用到上面展示的`DriveCurrentLiftPosition()`函数，中间跳转了很多层。本质上就是为了模拟窗帘的运动。

`DriveCurrentLiftPosition()`是一个软定时器的回调函数。每200ms把当前位置向目标位置挪动一步，一步是初始差值的5%，用来模拟窗帘慢慢移动到窗帘的实际位置。这里细节我们不必过于深究，只需要知道Matter API如何调用：

- 要Get Attribute值，需要调用`Attributes::属性名::Get(Endpoint(), xxx)`
- 要Set Attribute值，需要调用`Attributes::属性名::Set(Endpoint(), xxx)`

这里的参数Endpoint()其实就是个整数。因为WindowCovering这个类，也是一个单例模式的类。它对应的就是Endpoint1：

```c++
// WindowCovering.h中class的定义
static constexpr chip::EndpointId Endpoint() { return 1; };
```

此外，注意上述Attribute操作的API是在窗帘Cluster的name space调用的，如果开发其他产品，要换成其他的namespace：

```c++
using namespace chip::app::Clusters::WindowCovering;
```

### 总结

AppTask这个类负责应用层的杂项业务代码，有自己的事件循环（占用main线程）。也负责Matter协议栈的初始化。

default_zap/zap_generated下的代码是zap tool根据Matter数据模型自动生成的。用户可以用zap tool来修改当前工程的Matter数据模型。自动生成的代码只有定义，没有实现。开发者需要实现这些应用层代码。

WindowCovering这个类，是Nordic提供的应用层示例代码，用LED的灯光亮度来模拟窗帘的运动。开发者完全可以实现自己的类，而不必继续使用这个类。只需学习它的Attribute的操作方法，以及各种Matter API的使用即可。

# 5. 实战-增加电量显示

## 参考Matter标准文档

在添加新的Cluster前，首先要参考Matter的标准文档。

电池电量不属于application cluster，而是在核心规范中定义。我们直接参考matter-1-3-core-specification.pdf

电源相关的cluster定义在11.7 Power Source Cluster。

![image-20250103181214254](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103181214254.webp)



## 使用ZAP Tool修改数据模型

为自己的当前build打开一个nRF Connect命令行：

![image-20250103181417476](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103181417476.webp)

> 现在也可以从这里打开：
>
> ![image-20250103181337558](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103181337558.webp)



在修改模型之前，我们可以先用默认的模型先自动生成一遍代码：

```bash
west zap-generate
```

> 这样做，代码内容不会变化，只是做一下格式化。因为SDK在发布的时候，所有代码都被CI/CD系统格式化过一次。这样是把格式化改回来。代码格式化后git commit一次。这样一来，后续改完zap，再生成代码时，就方便通过git看自动生成了哪些callback。

### 添加cluster

输入以下命令：

```bash
west zap-gui
## 
# 可添加参数：
# -z zap配置文件位置. 也就是$(pwd)/src/default_zap/window-app.zap
# -j zcl.json模板位置
# -m Matter SDK安装位置
##
```

> 现在直接执行上述命令，会自动连网安装zap tool，不需要自己手动下载。也不需要添加参数设置位置。会按照SDK的zap tool的相对路径来查找。

![image-20250103181539141](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103181539141.webp)

在Endpoint 1中，因为PowerSource不属于application cluster，而是Matter的Cluster，所以在CHIP（Connect Home over IP）分类下寻找。

选中Power Source Cluster，并开启Server。Server的含义是存储Attribute的地方，可以被Client读取或修改。

再点击右侧齿轮进行进一步修改。

> 你也可以在Endpoint0里面加，没区别

![image-20250103181648145](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103181648145.webp)

### 修改Feature Map

每个Cluster会有很多Feature。例如核心规范中规定，有4个Feature。电源线供电，电池供电，可充电电池，可更换电池。

![image-20250103181736638](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103181736638.webp)

其中，Conformance字段表示某种依赖性。方括号[]的意思是依赖，如果想要使能RECHG或者REPLC，就必须要使能BAT。

由于我们要显示电池电量，电池电量这个Attribute肯定是属于BAT这个Feature的，因此Feature Map的Bit 1就要置1。也就是把FeatureMap置为0x02：

![image-20250103181807061](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103181807061.webp)

(这里显示out of range是ZAP Tool的显示bug，实际是正确的)

### 添加Attribute

继续阅读文档，发现**BatPercentRemaining**这个**Attribute**就是我们需要的电池电量。取值范围是0-200。

![image-20251028133923414](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedf0efec2f5304f775e5cc38a5789b9192.png)

并且其依赖[BAT]这个Feature，这个我们前面已经设置好了。

但是，后面还有三个Attribute，他们的Conformance是不带方括号的BAT。

不带方括号的意思是，**如果FeatureMap里使能了BAT，就必须要开启这三项attribute**:

- BatChargeLevel：枚举（正常、电量低、状态危险）
- BatReplacementNeeded：bool，电池是否需要更换
- BatReplaceability：枚举（未定义、不可更换、用户可更换、返厂可更换）

总共要开启4项：

![image-20250103181925963](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103181925963.webp)

### 修改Descriptor

我们需要修改Endpoint的Descriptor Cluster，修改里面的DeviceTypeList Attribute。但是不是直接在齿轮中设置。而是要在Endpoint中设置：

![image-20251028133244224](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedf6e373315d0b1c3eb43559d5acd93240.png)

把自己新增的Cluster添加进来：

![image-20251028133320969](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedfef66784a357b94ae5d4335016a5baad.png)

记得确认好revision和你用的版本的Matter spec手册一致：

![image-20251028133506754](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedcd186c9bab203295e1453090ca6559fe.png)

### 自动生成代码

点击File->Save保存。保存后，通过git会发现window-app.zap数据模型文件已经新增了Power Source cluster。

![image-20250103182137910](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103182137910.webp)

## 自动生成数据模型对应的代码

使用`west zap-generate`自动按照默认路径生成代码.

```bash
west zap-generate 
## 
# 可添加参数：
# -z zap配置文件位置. 也就是$(pwd)/src/default_zap/window-app.zap
# -o 自动生成代码的位置。不能用相对路径。
# -m Matter SDK安装位置
##
```

> 现在不需要添加参数设置位置。会按照SDK的zap tool的相对路径来查找。

通过git查看新增的代码：

![image-20250103182244065](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103182244065.webp)

自动生成代码后，会发现只增加了一个InitCallback.

因为电池电量不可能被其他设备写，只能被读，所以不会新增一个像窗帘那样的AttributeChangedCallback.

## 添加回调

在zcl_callbacks.cpp中实现上述新增的callback

```cpp
void emberAfPowerSourceClusterInitCallback(EndpointId endpoint) {

    Protocols::InteractionModel::Status status;

    uint32_t featureMap;
    ::chip::app::Clusters::PowerSource::Attributes::FeatureMap::Get(endpoint, &featureMap);
    ChipLogProgress(Zcl, "PowerSource::Attributes::FeatureMap = 0x%x", featureMap);

    // 要确保在zap-gui中已经配置feature支持电池电量
    __ASSERT((featureMap & 0x02) != 0, "PowerSource::Attributes::FeatureMap does not support battery!");

    app::DataModel::Nullable<uint8_t> BatPercentRemaing;
    status = ::chip::app::Clusters::PowerSource::Attributes::BatPercentRemaining::Get(endpoint, BatPercentRemaing);
    if (BatPercentRemaing.IsNull()) {
        BatPercentRemaing.SetNonNull(100);
		status = ::chip::app::Clusters::PowerSource::Attributes::BatPercentRemaining::Set(endpoint, 100);
        if (status != Protocols::InteractionModel::Status::Success) {
			ChipLogError(Zcl, "Failed to set PowerSource %s: %x", "BatPercentRemaining", to_underlying(status));
		}
	}
}
```

这个多出来的回调并没有那么严格，上面是一个示例，只是打印一些log而已。

只需要学会电池电量的attribute如何设置即可。后续在业务代码中直接调用相关函数，进行设置。注意把代码放到事件循环中执行。

## 验证效果

在设备详情页面多了电量显示。但是一直是0，因为只在InitCallback中设置电量是不够的，要在程序运行起来后去设置。

注意电量范围是0-200，因此要设置200才是100%电量

![image-20250103182535706](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250103182535706.webp)

# 6. Matter标准实现

通过前面的代码分析和实战，我们了解了Matter开发的基本逻辑：

1. 用ZAP-tool配置好自己要用的cluster
2. 自动生成代码，里面有一些weak定义的回调函数
3. 自己实现那些回调函数，处理Attributes changed callback

但是，我们会想到一个问题。Matter协议中，除了Attributes这种数值以外，还有一种类型的数据包叫做`Commands`。比如窗帘在移动时，可以用StopMotion命令让其停止运动。为什么我们不需要编写这个commands的回调函数呢？

我们可以参考Matter规范中的定义：

![image-20250920233518720](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/4cbde3ed9f7655cb4a78ebc8c8f2511c.png)

原来，在Matter规范中，已经规定了StopMotion Commands的实现方式：直接把目标位置（Target Position）改成和当前位置（Current Position）一样的值即可，这样窗帘就自动停止了。

对于这种，规范文件内已经明确定义好的命令，其回调函数在Matter协议栈里也已经实现好了：

`modules\lib\matter\src\app\clusters\window-covering-server\window-covering-server.cpp`

`emberAfWindowCoveringClusterStopMotionCallback()`:

![image-20250920233953782](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/e089d520fc382f436e37a7126394cee4.png)

其函数定义也不是`weak`的，因此应用层无法重写这个函数。

在自动生成的代码中，也已经自动注册好了这个函数，我们无需考虑它：

`../zap-generated/IMClusterCommandHandler.cpp`:

![image-20250920234234054](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/e03913f902496f4d7f32a1835575af55.png)
