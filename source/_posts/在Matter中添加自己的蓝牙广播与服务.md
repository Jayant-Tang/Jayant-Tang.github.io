---
title: 在Matter中添加自己的蓝牙广播与服务
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2025-10-21 15:50:54
cover: null
tags:
- Nordic
- Matter
categories:
- Matter
typora-root-url: ./..
cnblogs:
  postId: '19169458'
  url: https://www.cnblogs.com/jayant97/articles/19169458
  lastPublishedAt: '2026-07-06T18:20:52+08:00'
  sourceHash: sha256:71c74e30a8fad97bcb2d34e760683f1f8bf95a3a92286a87213a25f4e02d301e
  status: imported
  postType: Article
---

# 1. 简介

在Matter设备中添加自己的蓝牙广播和服务是常见的需求。主要来自于两个方面：

一是功能的角度，因为Matter规定了每一种设备类型只能有它固定的操作，如果厂商有特殊的配置要传给设备，是没法通过Matter传输的。因为Apple, Google, Samsung等手机的家庭APP里不会有为厂商单独配置的界面。

> 实际上Matter也支持厂商自定义Cluster，只不过目前各大手机的家庭APP无法操作这些自定义Cluster。

二是生态的角度，智能家居厂商往往都有自己的手机APP。虽然Matter出现的目标是打破生态壁垒，但厂商肯定还是不愿意放弃自己的APP生态的，主打一个“我全都要”。

本文将会基于nRF Connect SDK v3.0.2说明如何在Nordic芯片平台上给Matter工程添加自己的蓝牙广播和服务。

# 2. 多蓝牙广播方案分析

对于Matter over Wi-Fi 设备，Wi-Fi和BLE不是同一个射频硬件，只要互相不干扰就行。

对于Matter over Thread 设备，Nordic只需要一颗MCU，就可以实现BLE和Thread共用射频硬件，它们实际上在物理层是分时共存的：

![image-20251021162011675](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined7e99575576b0cf2b4da41e00a995e054.png)

在Matter例程里，BLE广播只有2个应用场景：

1. Matter配网阶段的设备发现：配网阶段，手机扫码后根据二维码信息扫描附近的BLE广播，确认要连接的是哪个设备。BLE连接后传输网络密钥，设备通过网络密钥链接到对应的网络后（Thread或者Wi-Fi），BLE的使命就结束了。设备入网后，BLE就关闭，只保留Thread或者Wi-Fi。
2. 设备OTA升级：通过Zephyr的MCUMgr SMP Server蓝牙服务升级，需要手机APP中集成了MCUMgr SMP Client来对设备进行升级。

我们会发现例程本身就有“Matter广播与私有广播共存”的用法了，因为SMP服务并不是Matter标准规定的，而是 Zephyr 通用的BLE OTA升级方案。

除此之外，nRF Connect SDK还支持多广播集（Multi ADV sets）共存，直接分时发出多个广播，可以各自具有不同的地址，从外部看起来就像是有多台BLE设备在广播一样。

因此，在Matter里面添加广播，有两个方案。

## 方案一：Matter 蓝牙广播仲裁器

Matter已经把SDK平台提供的蓝牙功能封装成了自己的API，其具体的实现位于：

`v3.0.2\modules\lib\matter\src\platform\Zephyr\BLEManagerImpl.cpp`

其中，有一个功能叫做广播仲裁器（Advertising Arbiter），是一个C++类。广播还是同一个广播，但是可以让你替换广播数据，从而实现替换广播名称、广播的UUID等等，在NCS中甚至还能改MAC地址（需要修改SDK源码）。

![image-20251021165035555](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb5958e874aa216464360d5bc9927f605.png)

这个是Matter本身就提供的功能，也是推荐使用的方案。在Matter（CHIP）协议栈初始化之后，CHIP Server启动之前，可以通过仲裁器注册一组广播请求，包含广播数据、广播间隔、回调函数、优先级等等。

CHIP Server启动后，每个需要蓝牙广播的软件模块可以主动插入请求（Insert Request）或者取消请求（Cancel Request）。仲裁器会根据优先级排列当前所有的插入请求的广播，并执行优先级最高的（top-priority）广播。

比如你可以这样设置优先级：

- Matter配网广播：0，最高
- 私有BLE广播：1
- OTA广播：uint8_max

当一个广播成为优先级最高的广播时，会触发提前注册好的`onStarted`回调函数；或者不再成为优先级最高的广播时，会触发提前注册好的`onStopped`回调函数。

整个框架都是完善的，Matter SDK已经提供好了。全程只有一个蓝牙广播，只需切换它的内容。

## 方案二：Zephyr多广播集（Multi ADV sets）

Matter蓝牙仲裁器的方案有一个小缺点，就是没办法让产品一开机就同时广播Matter配网和厂商的私有蓝牙，需要用户先进行某种操作。比如，有以下几种方案：

- 通过产品上的按钮来选择当前应该进行哪个广播
- 先发出Matter配网广播，等产品配网成功后，再发出厂商自己的广播供APP连接
- 先发出厂商自己广播，等连接完厂商的APP之后，再去APP里操作开启Matter配网广播

如果你不能接受这个小缺点，可以看Nordic的多广播共存方案，可以直接开启多个广播：

![image-20251021170819938](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined52b5be21062af907892d2e21c37deedc.png)

这时，使用的蓝牙广播API就不是普通的`bt_le_adv_start()`，而是`bt_le_ext_adv_start()`。用这个API可以创建多个广播集。

> 可能有人对这里的API名字中的”扩展广播“有误解，这里需要解释一下。
>
> 在Bluetooth Core Spec 5.0中，有一个新特性叫做扩展广播（Extended Advertising），它其实包含四个部分：
>
> 1. 允许255字节的广播数据PDU和扫描响应数据PDU，但是必须位于0-36信道。原来的广播信道37, 38, 39仍然只有31字节的PDU。
> 2.  允许通过多个扩展广播包形成链的形式，广播至多1650字节数据 。初始的广播包在37，38，39信道，然后跳到0-36信道。
> 3. 允许广播有多个实例集合，这个广播实例可以是普通广播也可以是前面第1项描述的”变长“的广播
> 4. 新特性：周期性广播。让广播间隔不再随机，这样observer端就可以不用持续开启扫描窗口，从而节省功耗
>
> 因此**扩展广播（Extended Advertising）**指的是以上4个功能，而不是很多科普文章只提到的1号的功能。
>
> 参考链接：[蓝牙™ Core 5.0功能 增强版 |蓝牙™ 技术网站](https://www.bluetooth.com/zh-cn/bluetooth-resources/bluetooth-core-5-0-go-faster-go-further/)
>
> Zephyr 的`bt_le_ext_adv` API可以实现以上所有4个功能。我们这里需要用到的是功能3。具体的链路层广播分时共存是由Nordic SoftDevice Controller自动实现的。

如果要使用这个方案，就需要修改NCS中的Matter源代码，把蓝牙广播仲裁器里面使用的广播的API改成`bt_le_ext_adv_start()`。

此外，扩展广播的`connected()`回调函数定义是不一样的，除了要记录`conn`之外，还能知道是从哪个广播连进来的：

![image-20251021183010806](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined9bf37427840f60ad73a8cf5660288d89.png)

实际应用开发中，我们可能有多个蓝牙业务的软件模块，每个模块里面各自有自己的广播和服务。软件模块可以各自注册不同的`bt_le_ext_adv_cb`。

# 3. 多蓝牙连接与多蓝牙服务方案分析

Zephyr的蓝牙只有一个GATT Server。因此，无论你用前面的哪个蓝牙多广播方案，无论外部的BLE主机是通过哪个广播连接进来的，看到的蓝牙服务都是一样的。

![image-20251021180814475](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedcbec65bc87613ac3d663fa5805e7fdb6.png)

## 普通广播连接时回调

在普通的蓝牙广播（`bt_le_adv_start()`）场景下，蓝牙连接成功时，在`connected()`回调函数里，一定要把`conn`记录下来作为句柄：

![image-20251021181113185](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined856ea6b709377794ad6d8e8ebe50685a.png)

如果从机被多个主机连接，开发者应该保存每个`conn`指针。后续进行GATT特征读写的时候，就靠`conn`来指定发送数据给哪个主机，同时也靠`conn`来判断数据是从哪台主机发来的。

注意，这种`connected()`回调函数可以注册很多个，形成链表。当连接成功时，所有`connected()`函数会依次执行。任何软件模块都可以注册自己的`connected()`来获取蓝牙连接、断开相关的事件。

> 代码里的`bt_conn_ref()`是给`conn`指针增加引用计数，防止其资源被操作系统自动释放。连接断开后再用`bt_conn_unref()`减少引用计数即可。
>
> **如果一个连接被多次引用，那么后续连接断开后，一定要释放相同的次数，否则将会出现内存泄漏**。
>
> 一般在`connected()`回调函数里面调用了一次`bt_conn_ref()`，那么就在`disconnected()`回调函数里面调用一次`bt_conn_unref()`即可。
>
> 即使有多个软件模块各自注册了自己的`connected()`和`disconnected()`，在里面各自执行`bt_conn_ref()`和`bt_conn_unref()`也没关系。只要保证它们的数量是成对的即可

## 扩展广播连接时回调

与普通广播的回调函数不同，扩展广播的`connected()`回调函数**不是放在一个链表里，而是独立的。**

这意味着，当你有多个扩展广播时，如果一个蓝牙主机连接其中一个扩展广播，那么只有那个扩展广播的`connected()`回调函数会执行，这就避免了混乱。

> 但是如果此时还有已注册的普通`connected()`回调，还是会把整个链表都调用一遍。

但是，所有的`disconnected()`回调函数仍然是处于同一个链表的。因此一定要在`disconnected()`回调函数里面判断一下当前的`*conn`句柄是不是建立连接的时候保存的那个，如果是，再进行相关释放动作。例如：



```c
static struct bt_le_ext_adv *ext_adv1 = NULL;
static struct bt_conn *ext_conn1 = NULL;

// 连接时回调
static void connected1(struct bt_le_ext_adv *extadv,
			  struct bt_le_ext_adv_connected_info *info)
{
	ext_conn1 = bt_conn_ref(info->conn);	
}

// 给扩展广播注册connected回调
struct bt_le_ext_adv_cb adv_ext_cb1 = {
	.connected = connected1
};

// 断开时
static void disconnected(struct bt_conn *conn, uint8_t reason)
{	
    // 连接断开不属于当前业务，不处理
    if(conn != ext_conn1) {
        return;
    }
    
    // 添加释放动作等
    bt_conn_unref(ext_conn1);
    ext_conn1 = NULL;
}

// 普通广播方式，不注册connected
BT_CONN_CB_DEFINE(conn_callbacks) = {
	.connected    = NULL,
	.disconnected = disconnected,
};

```

# 4. 多蓝牙地址分析

要让自己的蓝牙广播和Matter共存，并且两者的蓝牙设备地址不同。

Zephyr本身就支持多蓝牙地址，在Zephyr中它被称为蓝牙身份（Bluetooth Identity）。

蓝牙身份保存在一个数组中，数组长度是`CONFIG_BT_ID_MAX`，默认是1。

可以通过各种方式，在蓝牙协议栈初始化（`bt_enable()`）之前或之后，创建各种蓝牙地址，并保存到蓝牙身份数组。

这一方面详细的介绍，请参考《[NCS(Zephyr)中的蓝牙地址详解](https://jayant-tang.github.io/2025/01/22618b91ecf6/)》。

## 蓝牙广播地址切换

不论是普通广播还是扩展广播，在开启广播时都要使用`bt_le_adv_param`作为广播相关的配置参数。

```c
/** LE Advertising Parameters. */
struct bt_le_adv_param {
	/**
	 * @brief Local identity.
	 *
	 */
	uint8_t  id;
    ...
}
```

广播参数结构体的第一个成员就是`id`。大多数蓝牙例程的广播参数都使用`0`作为`id`，也就是使用蓝牙身份数组的第1个身份。

在开启广播的时候，我们可以修改设置广播参数中的`id`来选择自己用哪个蓝牙身份。

## Matter使用的蓝牙身份

首先我们要明确几个要求：

- Matter标准规定，Matter的配网广播必须使用**Random Static Address**，且每次上电都要变化，从而确保隐私。

在`v3.0.2/modules/lib/matter/src/platform/Zephyr/BLEAdvertisingArbiter.cpp`中，可以看到每次广播开启时都设置了使用的`id`。

![image-20251026205602364](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined51746b4f706d5d682b2ea2016ba3a766.png)

## Matter创建的蓝牙身份

前面使用的`sBtId`是在`v3.0.2/modules/lib/matter/src/platform/Zephyr/BLEManagerImpl.cpp`中赋值的：

在`CHIP_ERROR BLEManagerImpl::_Init()`函数中，有：

```c++
#ifdef CONFIG_BT_BONDABLE
    bt_addr_le_t idsAddr[CONFIG_BT_ID_MAX];
    size_t idsCount = CONFIG_BT_ID_MAX;

    err = bt_enable(nullptr);

    VerifyOrReturnError(err == 0, MapErrorZephyr(err));

    settings_load();

    bt_id_get(idsAddr, &idsCount);

    err = InitRandomStaticAddress(idsCount > 1, id);

    VerifyOrReturnError(err == 0 && id == kMatterBleIdentity, MapErrorZephyr(err));

#else
    err = InitRandomStaticAddress(false, id);
    VerifyOrReturnError(err == 0 && id == kMatterBleIdentity, MapErrorZephyr(err));
    err = bt_enable(nullptr);
    VerifyOrReturnError(err == 0, MapErrorZephyr(err));
#endif // CONFIG_BT_BONDABLE
```

首先，Matter的蓝牙广播是不允许绑定的。Matter协议栈会根据系统的其他蓝牙广播是否支持绑定（`CONFIG_BT_BONDABLE`）来执行不同的初始化过程：

- 如果系统没有蓝牙绑定功能，则在`bt_enable()`之前先尝试用随机数创建`id=0`的蓝牙身份
  
- 如果系统有蓝牙绑定功能，则先等`bt_enable()`和`settings_load()`创建`id=0`创建蓝牙身份，然后Matter再用随机数创建`id=1`的蓝牙身份

创建完毕后，在初始化Matter蓝牙广播仲裁器时传入参数，给`sBtId`赋值：
```c++
BLEAdvertisingArbiter::Init(static_cast<uint8_t>(id));
```

> 注意，不要直接打开或者关闭`CONFIG_BT_BONDABLE`。这只是一个中间的临时选项。
>
> 要开启蓝牙绑定功能：开启`CONFIG_BT_SMP=y`，它会自动select开启`CONFIG_BT_BONDABLE`。

# 5. 双蓝牙共存方案实例

基于前面对Matter源代码的分析，以及《[NCS(Zephyr)中的蓝牙地址详解](https://jayant-tang.github.io/2025/01/22618b91ecf6/)》中对Zephyr初始化蓝牙地址的介绍。我们会发现双蓝牙地址共存的方案有很多影响因素：

1. 使用前面介绍的“蓝牙仲裁器方案”或“多扩展广播方案”？
2. 自己的蓝牙服务是否需要绑定？
3. 自己的私有蓝牙广播是否需要使用公共地址（Public Address）？
4. 自己的芯片是单核蓝牙SoC（如nRF54L15）还是双核蓝牙SoC（如nRF5340）？

这样一共是2×2×2×2，有16种可能性的组合，实在太多，本文无法一一分析介绍。

本文在这里列出2种比较常见的方案，读者可以举一反三，实现自己的多蓝牙地址方案。

## 案例一：“蓝牙仲裁器方案” + 需绑定 + 使用公共地址 + 单核SoC

### （1）设置两个地址

首先，设置:

```shell
CONFIG_BT_ID_MAX=2
CONFIG_BT_SMP=y
CONFIG_BT_MAX_CONN=2
```

`#include <zephyr/bluetooth/controller.h>`

单核Soc，直接在Matter初始化之前设置公共地址到Controller层。

![image-20251027150520780](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb6587de7976c1524cc5c378771aaa111.png)

由于我们开启了蓝牙绑定`CONFIG_BT_SMP=y`功能，Matter协议栈里面会先执行`bt_enable()`和`settings_load()`，从而设置好`id=0`的蓝牙公共地址。

然后Matter会再创建自己用的`id=1`的随机静态地址。

### （2）使用广播仲裁器编写自己的蓝牙广播c++代码

写了一个c++类`AppBle`，使用单例模式，部分代码：

```c++
BT_CONN_CB_DEFINE(conn_callbacks) = {
	.connected = AppBle::Connected,
	.disconnected = AppBle::Disconnected,
    .le_param_updated = AppBle::LeParamUpdated,
	.security_changed = AppBle::SecurityChanged,
};

namespace {
constexpr uint8_t kFlags = BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR;
constexpr uint8_t k_ccs_uuid[] = {BT_COMMUNICATION_SERVICE};
constexpr char k_adv_name[] = "My_ADV";
}

using namespace ::chip;
using namespace ::chip::DeviceLayer;


bool AppBle::Init(uint8_t priority)
{  
    // 设置广播数据，以及当前广播成为top广播时的回调函数
    mAdvData[0] = BT_DATA(BT_DATA_FLAGS, &kFlags, sizeof(kFlags));
    mAdvData[1] = BT_DATA(BT_DATA_NAME_COMPLETE, k_adv_name, static_cast<uint8_t>(strlen(k_adv_name)));    
    mScanRespData[0] = BT_DATA(BT_DATA_UUID128_ALL, k_ccs_uuid,  sizeof(k_ccs_uuid));
	
    // 使用public地址时，广播参数要携带 BT_LE_ADV_OPT_USE_IDENTITY
	mAdvertisingRequest.priority = priority;
	mAdvertisingRequest.options = (BT_LE_ADV_OPT_USE_IDENTITY | BT_LE_ADV_OPT_CONN);
	mAdvertisingRequest.minInterval = mAdvIntervalMin;
	mAdvertisingRequest.maxInterval = mAdvIntervalMax;
	mAdvertisingRequest.advertisingData = ::chip::Span<bt_data>(mAdvData);
	mAdvertisingRequest.scanResponseData = ::chip::Span<bt_data>(mScanRespData);

	mAdvertisingRequest.onStarted = [](int rc) {
		if (rc == 0) {
			Instance().mIsStarted = true;
			LOG_INF("private advertising started.");
		} else {
			LOG_ERR("Failed to start Private BLE advertising: %d", rc);
		}
	};
	mAdvertisingRequest.onStopped = []() {
		Instance().mIsStarted = false;
		LOG_INF("Private advertising stopped.");
	};
}

/**
 * @brief 向Matter BLE仲裁器申请开启广播. 当没有优先级更高的广播时,将使用本广播的数据和参数
 */
bool AppBle::StartServer()
{
    Instance().mConn = nullptr;

    PlatformMgr().LockChipStack();
	CHIP_ERROR ret = BLEAdvertisingArbiter::InsertRequest(mAdvertisingRequest);
	PlatformMgr().UnlockChipStack();

    if (CHIP_NO_ERROR != ret) {
		LOG_ERR("Could not start private advertising");
		return false;
	}

	return true;
}

/**
 * @brief 向Matter BLE仲裁器申请关闭当前广播.
 */
void AppBle::StopServer()
{
	if (!mIsStarted){
        LOG_WRN("private ADV was already stopped");
        return;
    }

	PlatformMgr().LockChipStack();
	BLEAdvertisingArbiter::CancelRequest(mAdvertisingRequest);
	PlatformMgr().UnlockChipStack();
}


void AppBle::Connected(bt_conn *conn, uint8_t err)
{
	if (Instance().mIsStarted) {
		if (err || !conn) {
			LOG_ERR("private ADV connection failed (err %u)", err);
			return;
		}

        LOG_INF("## private ADV connected: %s ##", LogAddress(conn));
        LOG_INF("Will disconnect if no data transfer after %ds", AppBle::Instance().mDisconnectTimeout);

        // 保存当前连接
        Instance().mConn = bt_conn_ref(conn);
        
        // 发起绑定
		bt_conn_set_security(conn, BT_SECURITY_L3);
	}
}

void AppBle::Disconnected(bt_conn *conn, uint8_t reason)
{
    if (!Instance().mIsStarted) {
        LOG_DBG("private Adv not started");
        Instance().mConn = nullptr;
        return;
    }

    if (conn != Instance().mConn) {
        LOG_DBG("Not private Connection");
        return;
    }

    LOG_INF("## private ADV disconnected: %s", LogAddress(conn));

    if(Instance().mConn != nullptr) {
        bt_conn_unref(Instance().mConn);
        Instance().mConn = nullptr;
    }
}

void AppBle::SecurityChanged(bt_conn *conn, bt_security_t level, enum bt_security_err err)
{
	if (!Instance().mIsStarted){
        LOG_DBG("private Adv not started");
        return;
    }
	
    if (conn != Instance().mConn) {
        LOG_DBG("Not private Connection");
        return;
    }

	if (!err) {
		LOG_INF("BT Security changed: %s level %u", LogAddress(conn), level);
	} else {
		LOG_ERR("BT Security failed: level %u err %d", level, err);
	}
}

void AppBle::LeParamUpdated(struct bt_conn *conn, uint16_t interval, uint16_t latency, uint16_t timeout)
{
    if (!Instance().mIsStarted){
        LOG_DBG("private Adv not started");
        return;
    }

    if (conn != Instance().mConn) {
        LOG_DBG("Not private Connection");
        return;
    }
    LOG_INF("private ADV conn interval changed with %s", LogAddress(conn));
    LOG_INF("interval=%d, latency=%d, timeout=%d", interval, latency, timeout);
}

char* AppBle::LogAddress(bt_conn *conn)
{
#if CONFIG_LOG
    static char addr[BT_ADDR_LE_STR_LEN];
    bt_addr_le_to_str(bt_conn_get_dst(conn), addr, sizeof(addr));
    return addr;
#endif
    return NULL;
}
```

然后在`AppTask.cpp`中，注册自己的私有广播：

```c++
CHIP_ERROR AppTask::Init()
{
	/* Initialize Matter stack */
	ReturnErrorOnFailure(Nrf::Matter::PrepareServer());

	ReturnErrorOnFailure(Nrf::Matter::RegisterEventHandler(AppTask::DefaultMatterEventHandler, 0));

	// 初始化私有广播，优先级1，比Matter配网广播更低
	AppBle::Instance().Init(1);

    // 开启蓝牙配网广播，任务入队列
    Nrf::PostTask([] {
        AppTask::Instance().StartBLEAdvertisement();
    });

	// 开启私有广播，任务入队列
	Nrf::PostTask([] {
		AppBle::Instance().StartServer();
	});
	
    // 启动Matter协议栈
	return Nrf::Matter::StartServer();
}
```

### （3）修改广播仲裁器源码

在`v3.0.2/modules/lib/matter/src/platform/Zephyr/BLEAdvertisingArbiter.h`

![image-20251027153951723](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedd5b2ea434f2ea7e51d6cd05e87033227.png)

修改广播仲裁器源码，当检测到广播参数包含我们设置的`BT_LE_ADV_OPT_USE_IDENTITY`时，就临时切换到`id=0`的蓝牙身份（公共地址）。其他情况下，就正常使用Matter自己的`id=1`的蓝牙身份。

> 蓝牙广播仲裁器方案的优势是，对SDK的修改最少，只有上面展示的部分。并且这种修改完全不影响正常的Matter例程

## 案例二：“扩展广播方案” + 需绑定 + 使用公共地址 + 双核SoC

### （1）设置两个地址

首先，设置:

```shell
CONFIG_BT_ID_MAX=2
CONFIG_BT_SMP=y
```

由于是双核SoC，必须在`bt_enable()`和`settings_load()`之间用HCI命令设置公共地址。

在`v3.0.2/modules/lib/matter/src/platform/Zephyr/BLEManagerImpl.cpp`中：

![image-20251027154808135](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined60067f1a4db598f3ecd1f2ccc87c6282.png)

由于我们开启了蓝牙绑定`CONFIG_BT_SMP=y`功能，把《[NCS(Zephyr)中的蓝牙地址详解](https://jayant-tang.github.io/2025/01/22618b91ecf6/)》介绍的HCI设置公共地址的函数插入到上图的位置。那么在`settings_load()`时就会自动创建`id=0`的公共地址蓝牙身份。在后续的`InitRandomStaticAddress()`中，会创建`id=1`的静态随机地址蓝牙身份，供Matter使用。

### （2）把Matter广播改成扩展广播

先设置

```shell
CONFIG_BT_EXT_ADV=y
CONFIG_BT_EXT_ADV_MAX_ADV_SET=2
CONFIG_BT_MAX_CONN=2
```

`v3.0.2\modules\lib\matter\src\platform\Zephyr\BLEManagerImpl.h`:

把connected回调函数从C++私有成员（private）改成C++公共成员（public）。

![image-20251027155806635](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedf5178032ab16701130068acb45ee84a2.png)

`v3.0.2\modules\lib\matter\src\platform\Zephyr\BLEManagerImpl.cpp`：

把connected回调函数取消注册，因为后面要在扩展广播里面注册：

![image-20251027155919624](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedff30110b3494195396ee7239bde87d89.png)

先extern声明一下：

```c++
extern bt_conn *matter_conn;
```

然后在disconnected回调函数中，添加判断：当前断开事件是不是属于Matter广播的断开事件，如果不是就不管。

![image-20251027160111687](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedd61d2864bfe01dd42569bd24f4683874.png)

最后是`v3.0.2\modules\lib\matter\src\platform\Zephyr\BLEAdvertisingArbiter.cpp`，这个改动就太大了，直接贴全部代码：

```c++
/*
 *
 *    Copyright (c) 2023 Project CHIP Authors
 *
 *    Licensed under the Apache License, Version 2.0 (the "License");
 *    you may not use this file except in compliance with the License.
 *    You may obtain a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *    Unless required by applicable law or agreed to in writing, software
 *    distributed under the License is distributed on an "AS IS" BASIS,
 *    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *    See the License for the specific language governing permissions and
 *    limitations under the License.
 */

#include "BLEAdvertisingArbiter.h"

#include <lib/support/CodeUtils.h>
#include <lib/support/logging/CHIPLogging.h>
#include <platform/CHIPDeviceLayer.h>
#include <platform/Zephyr/BLEManagerImpl.h>
#include <system/SystemError.h>
#include <zephyr/bluetooth/conn.h>


bt_le_ext_adv *matter_ext_adv = NULL;
struct bt_conn *matter_conn = NULL;

static void matter_ext_adv_connected_cb(struct bt_le_ext_adv *extadv,
			  struct bt_le_ext_adv_connected_info *info)
{
    __ASSERT(extadv == matter_ext_adv, "Matter adv wrong");
	printk("## Matter ext adv connected %p ##\n", info->conn);
    matter_conn = info->conn;

    // move the original connected() callback here
    chip::DeviceLayer::Internal::BLEManagerImpl::HandleConnect(matter_conn, 0);
}

struct bt_le_ext_adv_cb adv_matter_cb = {
	.connected = matter_ext_adv_connected_cb
};

namespace chip {
namespace DeviceLayer {
namespace BLEAdvertisingArbiter {
namespace {

// List of advertising requests ordered by priority
sys_slist_t sRequests;

bool sIsInitialized    = false;
bool sWasDisconnection = false;
uint8_t sBtId          = 0;

// Cast an intrusive list node to the containing request object
const BLEAdvertisingArbiter::Request & ToRequest(const sys_snode_t * node)
{
    return *static_cast<const BLEAdvertisingArbiter::Request *>(node);
}

// Notify application about stopped advertising if the callback has been provided
void NotifyAdvertisingStopped(const sys_snode_t * node)
{
    VerifyOrReturn(node);

    const Request & request = ToRequest(node);

    if (request.onStopped != nullptr)
    {
        request.onStopped();
    }
}

// Restart advertising using the top-priority request
CHIP_ERROR RestartAdvertising()
{
    int err;
    static bool first_time = true;
    if (first_time) {
        first_time = false; 
        bt_le_adv_param first_param = BT_LE_ADV_PARAM_INIT(BT_LE_ADV_OPT_CONN, BT_GAP_ADV_FAST_INT_MIN_1, BT_GAP_ADV_FAST_INT_MAX_1,NULL);
        first_param.id = sBtId;
        err = bt_le_ext_adv_create(&first_param, &adv_matter_cb, &matter_ext_adv);
        if (err){
            printk("===Failed to create a connectable advertising set (err %d)\n", err);
        }
    }


    // Note: bt_le_adv_stop() returns success when the advertising was not started
    //ReturnErrorOnFailure(System::MapErrorZephyr(bt_le_adv_stop()));
    ReturnErrorOnFailure(System::MapErrorZephyr(bt_le_ext_adv_stop(matter_ext_adv)));

    ReturnErrorCodeIf(sys_slist_is_empty(&sRequests), CHIP_NO_ERROR);

    const Request & top    = ToRequest(sys_slist_peek_head(&sRequests));
    bt_le_adv_param params = BT_LE_ADV_PARAM_INIT(top.options, top.minInterval, top.maxInterval, nullptr);
    params.id              = sBtId;

    /** Change to ext_adv instead of normal one */   
    // const int result = bt_le_adv_start(&params, top.advertisingData.data(), top.advertisingData.size(), top.scanResponseData.data(),
    //                                    top.scanResponseData.size());

    err = bt_le_ext_adv_set_data(matter_ext_adv, top.advertisingData.data(), top.advertisingData.size(), top.scanResponseData.data(),
                                       top.scanResponseData.size());
    if (err) {
        printk("===Failed to set advertising data (err %d)\n", err);
    }

    err = bt_le_ext_adv_update_param(matter_ext_adv, &params);
	if (err) {
		printk("===Update Matter adv param (err %d)\n", err);		
	}		

    const int result = bt_le_ext_adv_start(matter_ext_adv, NULL);
    if (err) {
        printk("===Failed to start advertising (err %d)\n", err);
    }

    if (result < 0)
    {
        ChipLogProgress(DeviceLayer, "Advertising start failed, will retry once connection is released");
    }

    if (top.onStarted != nullptr)
    {
        top.onStarted(result);
    }

    return System::MapErrorZephyr(result);
}

BT_CONN_CB_DEFINE(conn_callbacks) = {
    .disconnected = [](struct bt_conn * conn, uint8_t reason) { sWasDisconnection = true; },
    .recycled =
        []() {
            // In this callback the connection object was returned to the pool and we can try to re-start connectable
            // advertising, but only if the disconnection was detected.
            if (sWasDisconnection)
            {
                SystemLayer().ScheduleLambda([] {
                    if (!sys_slist_is_empty(&sRequests))
                    {
                        // Starting from Zephyr 4.0 Automatic advertiser resumption is deprecated,
                        // so the BLE Advertising Arbiter has to take over the responsibility of restarting the advertiser.
                        // Restart advertising in this callback if there are pending requests after the connection is released.
                        RestartAdvertising();
                    }
                });
                // Reset the disconnection flag to avoid restarting advertising multiple times
                sWasDisconnection = false;
            }
        },
};
} // namespace

CHIP_ERROR Init(uint8_t btId)
{
    if (sIsInitialized)
    {
        return CHIP_ERROR_INCORRECT_STATE;
    }

    sBtId          = btId;
    sIsInitialized = true;

    return CHIP_NO_ERROR;
}

CHIP_ERROR InsertRequest(Request & request)
{
    if (!sIsInitialized)
    {
        return CHIP_ERROR_INCORRECT_STATE;
    }

    CancelRequest(request);

    sys_snode_t * prev = nullptr;
    sys_snode_t * node = nullptr;

    // Find position of the request in the list that preserves ordering by priority
    SYS_SLIST_FOR_EACH_NODE(&sRequests, node)
    {
        if (request.priority < ToRequest(node).priority)
        {
            break;
        }

        prev = node;
    }

    if (prev == nullptr)
    {
        NotifyAdvertisingStopped(sys_slist_peek_head(&sRequests));
        sys_slist_prepend(&sRequests, &request);
    }
    else
    {
        sys_slist_insert(&sRequests, prev, &request);
    }

    // If the request is top-priority, restart the advertising
    if (sys_slist_peek_head(&sRequests) == &request)
    {
        return RestartAdvertising();
    }

    return CHIP_NO_ERROR;
}

void CancelRequest(Request & request)
{
    if (!sIsInitialized)
    {
        return;
    }

    const bool isTopPriority = (sys_slist_peek_head(&sRequests) == &request);
    VerifyOrReturn(sys_slist_find_and_remove(&sRequests, &request));

    // If cancelled request was top-priority, restart the advertising.
    if (isTopPriority)
    {
        RestartAdvertising();
    }
}

} // namespace BLEAdvertisingArbiter
} // namespace DeviceLayer
} // namespace chip

```

主要思路：

1. 一开始要用`bt_le_ext_adv_create`创建扩展广播
2. 广播停止的API要改成扩展广播停止API
3. 广播启动API要改成一系列扩展广播的数据更新、参数更新、扩展广播启动API。注意到广播参数中的id用的是`sBtId`，也就是`1`.
4. 要在扩展广播专属的connected回调函数中，调用前一步我们取消注册的Matter自己的`HandleConnect`函数。这也是为什么前面我们要把它改成C++公共成员。

### （3）再添加自己的扩展广播

前一步修改已经让Matter可以运行了。再在自己的文件里等待蓝牙初始化完成，然后创建自己的广播即可：

```c++
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/conn.h>

bt_le_ext_adv *my_ext_adv = NULL;
struct bt_conn *my_conn = NULL;

static uint8_t mfg_data[] = { 0xFF, 0xFF, 0x30,0x31,0x32,0x33};
static const struct bt_data ad[] = {
	BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
	BT_DATA(BT_DATA_NAME_COMPLETE, "Common", sizeof("Common") - 1),
	BT_DATA(BT_DATA_MANUFACTURER_DATA, mfg_data, sizeof(mfg_data)),
};

void disconnected(struct bt_conn *conn, uint8_t reason)
{
    // 仅处理自己的连接断开事件
    if (conn != my_conn) {
        return;
    }

    printk("## My private disconnected (reason 0x%02x) ##\n", reason);

    if (my_conn) {
        bt_conn_unref(my_conn);
        my_conn = NULL;
    }
}

BT_CONN_CB_DEFINE(conn_callbacks) = {
	.connected    = NULL,
	.disconnected = disconnected,
	.security_changed = NULL,

};

static void my_ext_adv_connected_cb(struct bt_le_ext_adv *extadv,
			  struct bt_le_ext_adv_connected_info *info)
{
    __ASSERT(extadv == my_ext_adv, "My private adv wrong");
	printk("## My private ext adv connected %p ##\n", info->conn);

    // 保存当前conn，以便自己的蓝牙服务识别
    my_conn = bt_conn_ref(info->conn);
}

struct bt_le_ext_adv_cb my_ext_adv_cb = {
	.connected = my_ext_adv_connected_cb
};

int my_private_ble_thread_entry(void)
{
    while (!bt_is_ready()) {
        k_sleep(K_MSEC(100));
    }

	struct bt_le_adv_param adv_param0 = 
		{
			.id = 0,
			.sid = 0U, /* Supply unique SID when creating advertising set */
			.secondary_max_skip = 0U,
			.options = (BT_LE_ADV_OPT_USE_IDENTITY | BT_LE_ADV_OPT_CONN),
			.interval_min = 600,
			.interval_max = 800,
			.peer = NULL,
		};

	int err;
        
	err = bt_le_ext_adv_create(&adv_param0, &my_ext_adv_cb, &my_ext_adv);
	if (err) {
		printk("Create my ext adv (err %d)\n", err);
		return err;
	}

	err = bt_le_ext_adv_set_data(my_ext_adv, ad , ARRAY_SIZE(ad), NULL, 0);
	if (err) {
		printk("Set my ext adv data (err %d)\n", err);
		return err;
	}

	/* Start extended advertising set */
	err = bt_le_ext_adv_start(my_ext_adv,
				BT_LE_EXT_ADV_START_DEFAULT);
	if (err) {
		printk("Start common adv (err %d)\n", err);
		return err;
	}

	printk("## My private ext adv started ##\n");

	return 0;
}

K_THREAD_DEFINE(my_private_ble_thread_id, 4096,
            my_private_ble_thread_entry, NULL, NULL, NULL,
            7, 0, 0);
```

注意自己的蓝牙服务和connected回调函数里面，仅需处理`conn == my_conn`的情况即可。

> 可以发现这种方式对SDK改动较大，编译其他Matter工程时要注意
