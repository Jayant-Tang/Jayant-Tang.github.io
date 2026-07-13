---
title: NCS(Zephyr)中的蓝牙地址
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2025-01-26 16:02:54
cover: null
tags:
- Nordic
- Bluetooth
- BLE
categories: Nordic
cnblogs:
  postId: '19166250'
  url: https://www.cnblogs.com/jayant97/articles/19166250
  lastPublishedAt: '2026-07-06T18:20:52+08:00'
  sourceHash: sha256:add8dfda8c65b4bd8bbed93af10ef38c1c7a58ba083e177e79bc309efc2cdccb
  status: imported
  postType: Article
---

>  本文中的分析基于NCS v3.0.2

# 1. 蓝牙设备地址（Bluetooth Device Address）


蓝牙设备地址（Device Address， 俗称MAC地址）分为两大类：

- **公共地址（Public Address）**
- **随机地址（Random Address）**

在蓝牙空口包的结构中，这两种地址是由PDU Header中的`TxAdd`和`RxAdd`来区分的。0表示公共地址，1表示随机地址。

例如下图是蓝牙广播包的结构：PDU Header中的`TxAdd`决定地址类型；PDU Payload的开头是广播者的地址。

![image-20251026020018730](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedc91c7dd15b504c86d0bf25503ab6155e.png)

**所有在广播阶段发生交互的包都包含蓝牙地址**，不论是广播、扫描请求、连接请求，都包含蓝牙地址：

- 广播包（`ADV_IND`, `ADV_DIRECT_IND`, `ADV_NONCONN_IND`, `ADV_SCAN_IND`）：包含**广播者地址**
- 扫描请求（`SCAN_REQ`）：包含**扫描者地址** 和 **广播者地址**
- 扫描响应（`SCAN_RSP`）：包含**广播者地址**
- 连接请求（`CONNECT_REQ` ,  `AUX_CONNECT_REQ`）：包含**发起者地址** 和 **广播者地址**

> 连接建立后，连接包中就不含蓝牙地址了

## 蓝牙设备地址分类

随机地址又分为静态随机（Static Random）和私有随机（Private Random）地址。私有随机地址又分为可解析的（Resolvable）和不可解析的（Non-resolvable）。它们之间有特定比特的区别。

![img](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined7643529836a9f71e1a97b50e54651023.png)

最终有四类地址：

![image-20251026022752575](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinede73ddd6b3c544b0102a9a7501e943d3e.png)

## 公共地址

需要向IEEE购买的MAC地址段，以确保自己的设备地址全球唯一，并且别人通过地址就能知道设备是哪家公司的产品。公共地址在整个设备生命周期不可以更改。

购买后，IEEE会分配Company ID。剩余的24bit由购买该地址段的公司自己分配。

> 由于公共地址全球唯一，也可以当作序列号使用。但是蓝牙地址本身的全球唯一其实并不必要。只要蓝牙能扫到的几十米范围内设备没有重复的地址就可以了。

## 随机地址

任何人都可以使用的随机数作为地址。由最高2个bit决定更具体的地址类型。

### (1) 随机静态地址

这是最常用的地址，可以给每个设备分配一个固定的随机数作为地址；或者每次上电重新生成一个也可以。使用起来最方便。

### (2) 随机私有地址

私有地址会在运行时动态改变，防止被追踪。

#### 不可解析私有地址

没有任何规律的随机变化地址。适合一些仅需要广播的场景，例如Beacon推送。

由于地址一直在变化，游客的手机只能收到Beacon的广播内容。手机无法根据Beacon的地址映射Beacon的物理位置，因此无法实现对手机用户的定位追踪。

> 反过来，如果需要做蓝牙定位应用，就不能用不可解析私有地址。

#### 可解析私有地址（RPA）

最复杂的地址类型，常用于个人随身设备。核心思路是“对所有人隐藏，对自己人可见”。例如一对绑定的手机和手表：

1. 手表并不是一直与手机连接，而是只在需要的时候才发起广播，让手机来连接
2. 为了不让此广播被跟踪，手表的广播地址需要实时随机变化
3. 为了让手机知道这个实时变化的地址是自己绑定的手表，这个地址具有特殊的结构：prand + hash。
4. prand是手表生成的随机数，一直变化；hash是用prand和IRK进行哈希计算生成的（IRK是手机和手表配对时双方存储的同一个密钥）
5. 只有手机能够通过prand计算出hash，从而知道这个手表是与自己配对的

> 常见应用：
>
> - Apple Findmy网络：只有自己的iPhone能知道这个AirTag是自己的；其他人的iPhone只能把这个广播携带的信息作为匿名信息上传到Findmy网络
> - 智能家居与可穿戴设备：例如，智能门锁状态变化时，在RPA广播中改变状态。只有自己的手机或者智能家具中枢能识别到这个RPA广播对应的是哪个具体的门锁，进而主动连接然后读取更详细的状态。

由此我们可以得知：一台设备要想使用RPA广播，需要先使用Random Static Address或者Public Address，让手机进行正常的连接配对之后，两边才有IRK。这时再切换成RPA广播即可。

# 2. Zephyr中的蓝牙身份

在Zephyr中，蓝牙设备地址由如下结构体描述：

```c
#define BT_ADDR_LE_PUBLIC       0x00
#define BT_ADDR_LE_RANDOM       0x01
#define BT_ADDR_LE_PUBLIC_ID    0x02
#define BT_ADDR_LE_RANDOM_ID    0x03
#define BT_ADDR_LE_UNRESOLVED   0xFE /* Resolvable Private Address
				      * (Controller unable to resolve)
				      */
#define BT_ADDR_LE_ANONYMOUS    0xFF /* No address provided
				      * (anonymous advertisement)
				      */

/** Length in bytes of a standard Bluetooth address */
#define BT_ADDR_SIZE 6

/** Bluetooth Device Address */
typedef struct {
	uint8_t  val[BT_ADDR_SIZE];
} bt_addr_t;
/**/

/** Bluetooth LE Device Address */
typedef struct {
	uint8_t      type;
	bt_addr_t a;
} bt_addr_le_t;
```

一个蓝牙低功耗地址结构体`bt_addr_le_t`包含蓝牙地址`bt_addr_t`和它的类型。

其中的**地址类型**，我们在设置自己的地址的时候，只需要用到`BT_ADDR_LE_PUBLIC`和`BT_ADDR_LE_RANDOM`。

Zephyr本身支持多蓝牙地址，在Zephyr中它被称为**蓝牙身份（Bluetooth Identity）**。

在`zephyr\subsys\bluetooth\host\hci_core.h`中，有如下定义：

```
struct bt_dev {
	/* Local Identity Address(es) */
	bt_addr_le_t            id_addr[CONFIG_BT_ID_MAX];
	uint8_t                 id_count;
    ...
}
```

可见最大的蓝牙身份数量由`CONFIG_BT_ID_MAX`决定，默认是1。

## 如何选择蓝牙身份

如果有多个蓝牙身份，需要在广播时选择自己用哪个身份进行广播。

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

结构体的第一个参数就是`id`。大多数例程的广播参数`id`都是0。

可以通过在开启广播的时候，设置广播参数中的`id`来选择自己用哪个蓝牙地址。

> 不过，在开发蓝牙主机时，无法选择蓝牙身份。蓝牙主机只能用`id=0`的身份。

## Zephyr蓝牙地址常用API

>  实际开发中，需要先创建**蓝牙地址**结构体变量，再填充进**蓝牙身份**数组。

`#include <zephyr/bluetooth/addr.h>`

```c
/** 
  * 检查随机地址的类型
  */
/** Check if a Bluetooth LE random address is resolvable private address. */
#define BT_ADDR_IS_RPA(a)     (((a)->val[5] & 0xc0) == 0x40)
/** Check if a Bluetooth LE random address is a non-resolvable private address.
 */
#define BT_ADDR_IS_NRPA(a)    (((a)->val[5] & 0xc0) == 0x00)
/** Check if a Bluetooth LE random address is a static address. */
#define BT_ADDR_IS_STATIC(a)  (((a)->val[5] & 0xc0) == 0xc0)

/** 
  * 强制修改随机地址的类型
  */
/** Set a Bluetooth LE random address as a resolvable private address. */
#define BT_ADDR_SET_RPA(a)    ((a)->val[5] = (((a)->val[5] & 0x3f) | 0x40))
/** Set a Bluetooth LE random address as a non-resolvable private address. */
#define BT_ADDR_SET_NRPA(a)   ((a)->val[5] &= 0x3f)
/** Set a Bluetooth LE random address as a static address. */
#define BT_ADDR_SET_STATIC(a) ((a)->val[5] |= 0xc0)

/**
  * 用随机数创建地址
  */
/** @brief Create a Bluetooth LE random non-resolvable private address. */
int bt_addr_le_create_nrpa(bt_addr_le_t *addr);

/** @brief Create a Bluetooth LE random static address. */
int bt_addr_le_create_static(bt_addr_le_t *addr);


/**
  * 用字符串创建地址，如"AA:BB:CC:DD:EE:FF"
  */

/** @brief Create a Bluetooth LE random static address. */
int bt_addr_from_str(const char *str, bt_addr_t *addr);

int bt_addr_le_from_str(const char *str, const char *type, bt_addr_le_t *addr);
```

## Zephyr蓝牙身份常用API

> 把蓝牙地址填充到蓝牙身份，才能在广播时使用

`#include <zephyr/bluetooth/bluetooth.h>`

```c

/**
 * 读取蓝牙身份列表
 *  1. 传入数组首地址和数组长度进行读取。用于读取的数组本身的长度不能低于CONFIG_BT_ID_MAX
 *  2. addrs为NULL时，只读取蓝牙身份个数
 */
void bt_id_get(bt_addr_le_t *addrs, size_t *count);

/**
 * 新建蓝牙身份
 *  1. 如果蓝牙身份数量小于 CONFIG_BT_ID_MAX，则创建一个身份到 bt_dev.id_addr[bt_dev.id_count]，然后bt_dev.id_count++
 *  2. 在Nordic平台上只能用于创建随机地址，不能用于创建公共地址
 *  3. 不用私有地址时（CONFIG_BT_PRIVACY=n），irk必须为NULL。也就是说静态随机地址设置为NULL即可
 *  4. 允许在bt_enable()前调用，这时可以创建id=0的身份
 */
int bt_id_create(bt_addr_le_t *addr, uint8_t *irk);

/**
 * 重置指定的蓝牙身份
 *  1. 指定一个具体的id，修改其蓝牙地址
 *  2. id == BT_ID_DEFAULT时，不能重置
 *  3. 重置时，所有与此id相关的连接都会被断开，所有绑定的密钥都会被删除
 */
int bt_id_reset(uint8_t id, bt_addr_le_t *addr, uint8_t *irk);

/**
 * 删除蓝牙身份
 *  1. id == BT_ID_DEFAULT 不能删除
 *  2. 删除时，所有与此id相关的连接都会被断开，所有绑定的密钥都会被删除
 */
int bt_id_delete(uint8_t id);
```

## 公共地址（Public Address）设置API

Zephyr中只能设置1个公共地址，且只能放到`id=0`的位置。

> 在Nordic平台上，公共地址的设置逻辑比较特殊：
>
> BLE协议栈分为Host层和Controller层。NCS的Host层使用开源的Zephyr Host，而Controller层默认使用闭源的SoftDevice。
>
> **公共地址需要先设置到蓝牙Controller层，再让Host层读出并创建第一个（id=0）蓝牙身份。因此需要单独提前设置。**

Nordic平台上设置公共地址有2种方案：

### 方法一：Controller层直接设置

`#include <zephyr/bluetooth/controller.h>`

```c
// Controller 层直接设置公共地址，参数是6字节数组
void bt_ctlr_set_public_addr(const uint8_t *addr);
```

> **需要在`bt_enable()`之前调用**，一定没问题。
>
> 对于单核SoC，直接调用即可。
>
> 对于多核SoC，且Controller层单独位于网络核的情况（如nRF5340，nRF54H20）。需要单独修改网络核固件，在网络核程序开始时调用。在应用核调用无效。

例如：

![image-20251026035904822](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined2c117f3711ea646e63b21f2d1cc0359f.png)

![image-20251026035843421](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinede101f163b6e1a2dee42d8ccff3a62523.png)

### 方法二：Host层通过HCI命令设置

`#include <zephyr/bluetooth/hci_vs.h>`

这是一组厂商自定义HCI命令，复制以下函数到你的工程中：

```c
static int hci_set_public_addr(uint8_t addr[6])
{
	int err = 0;
	struct net_buf *buf;
	struct net_buf *rsp;
	struct bt_hci_cp_vs_write_bd_addr *cmd_params;

	buf = bt_hci_cmd_create(BT_HCI_OP_VS_WRITE_BD_ADDR, sizeof(*cmd_params));
	if (!buf) {
        printk("Could not allocate command buffer\n");
		return -ENOMEM;
	}

	cmd_params = (struct bt_hci_cp_vs_write_bd_addr *)net_buf_add(buf, sizeof(*cmd_params));

    memcpy(cmd_params->bdaddr.val, addr, 6);

	err = bt_hci_cmd_send_sync(BT_HCI_OP_VS_WRITE_BD_ADDR, buf, &rsp);
	if (err) {
        printk("Failed to send HCI command to set public address (err %d)\n", err);
		return err;
	}

	net_buf_unref(rsp);

	return 0;
}
```

> 必须开启厂商自定义（Vendor-Specific）HCI命令：`CONFIG_BT_HCI_VS=y`。
>
> 
>
> **必须在`bt_enable()`之后，`settings_load()`之前调用。**
>
> 
>
> 单核SoC和多核SoC都可以使用，在应用核调用即可。
>
> 如果`CONFIG_BT_SETTINGS=y`未被开启，**此方法无法使用**。因为`bt_enable()`之前，HCI没初始化用不了；而不开启Setting时，`bt_enable()`过程中就会创建id=0的地址，因此那之后HCI命令就不能再创建一个id=0的公共地址了。

例如：

![image-20251026042305502](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined1622aec49af726e9b6f4aa0d90edefb7.png)

![image-20251026042329656](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined81271df5d84b52a08238b6e9196fd767.png)

# 3. NCS蓝牙协议栈默认地址设置逻辑

**如果你没有在`bt_enable()`之前用`bt_id_create()`创建蓝牙身份**。那么，在NCS蓝牙协议栈启动过程中，协议栈会尝试自动创建`id=0`的蓝牙身份：

1. 优先从Controller层读取公共地址，并设置为`id=0`的蓝牙身份
2. 公共地址没有的情况下，设置随机静态地址作为`id=0`的蓝牙身份

一个图解释，没有蓝牙身份时，不同配置下蓝牙协议栈初始化过程如何创建地址：

![image-20251027131513228](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined86b8b9ca799cb01ab4a214a9ced19086.png)

### Settings的影响

> Settings是Zephyr中的一个存储中间件，提供键值对存储接口。其中键是用"/"分割的字符串，就像PC中的文件系统目录一样。
>
> Settings给应用层提供的前端API是基于回调函数的。当load时，把数据从持久化存储读到内存中；save时，把数据从内存保存到持久化存储中。
>
> SDK每个不同的软件子系统（Subsys）都可以各自在自己的“存储路径”（也就是字符串形式的键）内存储或者加载自己的配置。比如蓝牙系统可以存储自己的地址，绑定密钥等等。
>
> 当应用层调用全局的`settings_load()`或者`settings_save()`时，每个软件模块自己的settings相关回调函数就会执行：
>
> - 调用 `settings_load()` 会遍历所有注册的 settings handler，通过 handler 的 `h_set` 回调将数据加载到内存，最后调用 `h_commit` 通知应用层设置已加载完成
> - 调用`settings_save()`会遍历所有注册的 settings handler，通过 handler 的 `h_export` 回调导出数据，然后通过后端写入存储。
>
> ![image-20251024120532681](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined67bd9c973f7eb4d6ca45c6615d2a3dd5.png)
>
> 
>
> Settings的后端是NVS或者ZMS，也是键值对存储库，有磨损均衡、掉电安全、垃圾回收等功能。但是ZMS/NVS的键是整数。
>
> - NVS：在Flash的基础上提供存储服务
> - ZMS：在RRAM/MRAM的基础上提供存储服务，充分利用先进硬件的特性，支持无擦除覆盖写入
>
> ![image-20251024120101359](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined8f4ff5af55ca04cd4b225fee0ebbbf53.png)
>
> ![image-20251024120118402](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedc289d111ae808adac4bdbb656cfd0b40.png)
>
> 绝大多数情况下，工程都是会用到Settings系统的

`CONFIG_BT_SETTINGS=y`是依赖`CONFIG_SETTINGS=y`的。

在多数蓝牙例程中，不要单独开关`CONFIG_BT_SETTINGS`或者`CONFIG_SETTINGS`。

例如，在`peripheral_lbs`例程中，`CONFIG_BT_SETTINGS`和`CONFIG_SETTINGS`是由LBS的安全特性开启的：

![image-20251026045902003](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb52d305fdc9bf063e2efb1e901a96178.png)

因此，在这个例程中，我们需要进行以下配置才能把settings关掉：

```c
CONFIG_BT_LBS_SECURITY_ENABLED=n
```

如果是其他例程，自行搜索有没有其他Kconfig配置项用`select`开启Settings的情况。

接下来讨论两种情况的初始化过程：

#### 1. `CONFIG_BT_SETTINGS=y`

当`CONFIG_BT_SETTINGS=y`的情况下，整个`bt_enable()`过程都不会创建蓝牙地址。还会打印日志提示你，后面一定要自己调用`settings_load()`。

```c
if (IS_ENABLED(CONFIG_BT_SETTINGS)) {
    if (!bt_dev.id_count) {
        LOG_INF("No ID address. App must call settings_load()");
        return 0;
    }

    atomic_set_bit(bt_dev.flags, BT_DEV_PRESET_ID);
}
```

![image-20251026044626675](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedf9c29619e7d572f75aa713b6a145346c.png)

这是因为要考虑到之前保存过蓝牙地址的情况。要把之前的蓝牙地址加载到内存。同时，对于新的芯片刚烧录完，settings里面没有存地址的情况，也必须要兜底。

当应用层`settings_load()`时，会有以下逻辑：位于`zephyr\subsys\bluetooth\host\settings.c`

1. Settings系统会通过`set_settings()`回调函数遍历所有已保存的蓝牙数据，并加载到内存中。其中就包括把蓝牙地址加载到`bt_dev.id_addr[]`数组中。
2. 所有`.h_set()`回调函数遍历执行完毕后，执行一次` commit_settings(void)`，通知应用层设置已加载完成
3. 在蓝牙的`commit_settings(void)`回调中有兜底：如果前面在持久化数据中没有读到地址，就创建一个公共地址或者随机地址

#### 2. `CONFIG_BT_SETTINGS=n`

当`CONFIG_BT_SETTINGS=n`的情况下，`bt_enable()`中就会自己创建地址了。调用的函数跟前面`commit_settings(void)`里面兜底的函数是一样的。

### 公共地址身份设置

不论是否开启Settings，在设置`id=0`的身份时，都会先尝试从Controller层读取Public地址：

```c
bt_setup_public_id_addr();
```

**前面介绍的“公共地址设置API”，只是把公共地址设置到蓝牙Controller层，并没有创建蓝牙身份。**

公共地址蓝牙身份的创建仅仅存在于`bt_setup_public_id_addr()`函数中。

这也是为什么我们前面介绍公共地址API时，一定要保证：

- 对于单核的SoC，最好在`bt_enable()`之前，直接用蓝牙Controller层的API，给Controller层设置公共地址
- 对于双核的SoC，最好开启Settings，然后必须在`bt_enable()`之后，且`settings_load()`之前给Controller层设置公共地址
  - 要求在`bt_enable()`之后，是因为蓝牙协议栈初始化之后才能用HCI命令
  - 要求在`settings_load()`之前，是因为要在Settings设置`id=0`的身份之前，提前把地址设置到Controller层

### 随机静态地址身份设置

前面公共地址设置失败时，继续尝试设置随机静态地址。

在`bt_setup_random_id_addr()`中：

如果开启了`CONFIG_BT_HCI_VS=y`，则会通过厂商自定义（Vendor-Specific）HCI命令，从Controller读取Random地址。Nordic SoftDevice会读取芯片的FICR寄存器中的设备地址来使用。因此**每次上电它都是固定的**：

![image-20251026050229779](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedfea0f2f25923b4de95e8054da50b8261.png)

如果设置了`CONFIG_BT_HCI_VS=n`，最后就会用`bt_id_create(NULL, NULL)`来生成。这个最终得到的是随机数，**每次上电地址都不一样**：

![image-20251026050346392](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined145580f60557b10d8c05d67fcf0da21b.png)

> 【注意】
>
> 这里只是解释一下`CONFIG_BT_HCI_VS=n`的情况会变成每次上电都变化的随机静态地址，而不是推荐你关闭`CONFIG_BT_HCI_VS`。
>
> 如果你的需求是“每次上电都变化的随机静态地址”，那么直接在`bt_enable()`之前先用真随机数生成器生成一个地址，再用`bt_id_create()`设置即可。

# 4. 蓝牙地址烧录

通过前面的介绍，我们知道蓝牙地址都是通过函数从RAM里设置的。

如果想要实现产品出厂地址烧录，可以烧录到芯片的指定区域，比如UICR中。然后代码启动时读出对应区域的地址，再用前面介绍的API设置。

对于nRF52系列可以烧录到[UICR的Customer区域](https://docs.nordicsemi.com/bundle/ps_nrf52840/page/uicr.html#ariaid-title32)；对于nRF53, nRF54系列，可以烧录到[UICR的OTP区域](https://docs.nordicsemi.com/bundle/ps_nrf54L15/page/uicr.html#ariaid-title21)。其实是一样的，换了个名字而已。

以nRF54L15为例，先用J-link指定区域烧录地址：

```bash
nrfutil device recover
nrfutil device write --address 0x00FFD500 --value 0xCCDDEEFF
nrfutil device write --address 0x00FFD504 --value 0x0000AABB
nrfutil device read --address 0x00FFD500 --bytes 8
```

> 注意不同芯片UICR地址不一样，用户可写的位置也不一样，要看芯片手册

然后，由于是ROM，在代码中读出对应地址即可。

可以直接读取地址，也可以用相关API，例如flash的API和RRAM的API。此外，有TF-M的情况下，需要用的API不同。

最后用前面介绍的API设置地址即可。

# 5. 总结

1. 地址有2大类，**公共地址**和**随机地址**。它们之间的区别在于广播包的TxAdd和RxAdd字段。
2. 随机地址又分为随机静态地址和随机私有地址；随机私有地址又分为**不可解析的**和**可解析的（RPA）**
3. 在Zephyr中，蓝牙地址是结构体数据对象，可以随意创建。但是使用时，需要把地址保存到蓝牙身份（bt_id）中
4. 广播时，在广播参数结构体中，可以选择要使用的蓝牙身份，从而实现蓝牙地址切换
5. 要想使用公共地址，需要先用API把公共地址提前设置给Controller层，再等待Host层`bt_enable()`或者`settings_load()`自动读出
6. NCS自动生成静态随机地址时，根据`CONFIG_BT_HCI_VS`的配置，从Controller层读出或者生成随机值。
7. 烧录地址需要先烧到UICR，再用前面介绍的API进行设置

