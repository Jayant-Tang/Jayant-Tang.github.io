---
title: Zephyr中的分区和存储系统
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2026-07-03 15:10:00
cover: null
tags:
- Nordic
- Zephyr
- NCS
- Storage
categories: Zephyr
cnblogs:
  published: true
  postType: Article
  postId: '21389875'
  url: https://www.cnblogs.com/jayant97/articles/21389875
  lastPublishedAt: '2026-07-13T10:12:18+08:00'
  sourceHash: sha256:a00a64a97d9fcb349406a1826515a6f1a2eb1c7a82b845cf7f7d300ba9085547
  status: synced
---

# 1. 简介

本文介绍 Zephyr 中常见的分区和持久化存储方案，这两个主题都是从开发产品原型到产品量产过程中不可缺少的工作内容。

## 架构：从硬件到存储系统

Zephyr 提供了存储系统从硬件驱动到应用层的完整解决方案，自底层向上来说：

1. 硬件：可字节寻址的 (Byte addressable) 存储器。
   - SOC 内部 NVM（eFlash, RRAM, MRAM）。
   - SPI/QSPI 接口的、符合 JEDEC 标准的外部 NOR Flash。
2. 驱动层：不论是以上哪种硬件 ，都通过 Zephyr Flash 驱动提供统一的 Flash API。
3. 分区抽象层：在C代码中提供**“分区对象”**和相关的操作接口（读、写、擦），负责偏移量计算和边界检查。是上层存储系统共同的基础设施。
4. 数据模型层：决定数据要以什么形式存放在 NVM 中。由存储后端系统提供**CRC、磨损均衡、原子写**等功能。有多种存储后端可选，其中，NVS, ZMS 是简单的键值对（整数 Key → 二进制块 Value）存储后端。LittleFS 是文件系统。
5. 应用配置层：由 Settings Subsystem 提供配置项的持久化存储方案。不仅是你的应用层代码可以使用，Zephyr 中的许多子系统都在使用 Settings，如 Wi-Fi 密钥，BLE绑定信息等。这样整个系统都只需要同一块存储分区，不需要各自管理。
6. 用户自己的应用层可以和 Zephyr 其他组件一起使用 Settings 进行配置的存储。也可以单开一块分区，直接用 NVS/ZMS/LittleFS 等存储后端。 

```text
架构图：

┌──────────────────────────────────────────────┐
│          Application Code                    │
├──────────────────────────────────┬───────────┤
│  Settings Subsys                 |           │  ◀ 应用配置层：字符串 key-value
│  "bt/addr" → {xx:xx:xx:xx:xx:xx} |           │   树形命名空间
├──────────────────────────────────┘           │
│                                              │  ◀ 数据模型层（存储后端）：CRC、磨损均衡、原子写
│  NVS / ZMS backend                LittleFS   │    - 键值对存储：NVS/ZMS
│  ID=123 → {0xA5, 0x3C, ...}     (File System)│    - 文件系统：LittleFS
│                                              │    
├──────────────────────────────────────────────┤
│  Flash Map API                               │  ◀ 分区抽象层
│  PARTITION_ID(storage) → area                │    offset + size + device
├──────────────────────────────────────────────┤
│                                              │  ◀ 硬件驱动层
│  Flash Driver                                │    soc_flash_nrf.c            (nRF52/53 Flash)
│  flash_read / flash_write / erase            │    soc_flash_nrf_rram.c       (nRF54L RRAM)
|                                              |    spi_nor.c / nrf_qspi_nor.c (SPI/QSPI NOR Flash)
├──────────────────────────────────────────────┤
│  Physical Mem (NOR Flash / RRAM / MRAM)      │  ◀ 硬件
└──────────────────────────────────────────────┘
```



> 注意：
>
> 1. 本文涉及的存储硬件都是**可字节寻址的(Byte addressable)** Nor Flash 或者 MRAM/RRAM。本文不涉及 NAND Flash 和 SD卡，它们属于块设备，需要不同的驱动层。但最终也能接入到 LittleFS 文件系统。
>
> 2. Flash Map 不是 Zephyr 中唯一的分区抽象层。Trust Zone 的安全存储技术使用别的抽象层（TF-M HAL），本文不涉及。
>
> 3. 除了存储系统外，Zephyr 的 DFU 系统在接收更新固件时，也会使用 Flash Map API。但不只用这一种抽象层，还会使用Stream Flash。
>    ```text
>                        DFU (mcumgr img_mgmt / OTA)
>                                  │
>                              flash_img.c   ← 镜像写入逻辑
>                           ╱              ╲
>                flash_area_flatten   stream_flash_buffered_write
>                    (分区擦除)             (流式写入)
>                        │                    │
>                        │            flash_write(fdev, ...)
>                        │            flash_erase(fdev, ...)
>                        │            flash_read(fdev, ...)
>                        │                    │
>                        └────────┬───────────┘
>                              Flash Driver
>    ```
>
>    - Flash Map ：为**分区隔离**优化（安全第一）
>    - Stream Flash : 为**吞吐量**优化（速度第一）
>
> 4. Zephyr 构建系统也支持**在构建阶段**对 RAM 进行分区——比如 TF-M 安全域和 Non-Secure 应用之间切分同一块物理 RAM，或多核场景下为协处理器（如 RISC-V）预留内存区域——但本文不展开。

下面开始从底层向上，逐层介绍。

# 2. 硬件层：非易失存储

本文讨论的存储硬件主要有两类：

1. MCU 内部 NVM，例如片上 NOR Flash、RRAM、MRAM；
2. 通过 SPI/QSPI 接入的外部 NOR Flash。

## NOR Flash

目前最常见的 MCU 内部存储器。许多常见的SPI/QSPI接口存储器也是NOR Flash。

用浮栅 MOSFET 的栅极存储电荷状态代表`0`和`1`。由于删极浮空，周围电绝缘，因此可以长期保存。如果要改变其0和1状态，需要外部施加电压，用一些半导体物理的方法来改变。

存储特性：

- 支持以 32bit word 为单位随机读写。

- 通常每个 bit 只能将`1` 写为 `0`，不能将 `0` 写回 `1`。

- 写入前，必须按页（Page）擦除，擦除后 bits 全为`1` （`0xff`）。

  >  nRF52 系列 / nRF5340 App Core 内部 Flash 页大小为 4kB；nRF5340 Net Core 内部 Flash 页大小为 2kB。

- 擦除需要时间。**内部 Flash 页擦除期间， CPU 无法执行代码**。

  > nRF52840 全片擦除需要 169 ms，Page 擦除需要 85 ms。
  > nRF52840 内部 Flash 控制器（NVMC）支持 Partial Erase，把一次擦除拆分成 N 段，每段擦除之间的间隙 CPU 可以执行代码，这样就能避免 Flash 擦除行为卡住CPU关键任务的执行。

- **nRF52/nRF53/nRF91 系列内部 Flash 擦除寿命大约1万次**；外部 SPI/QSPI NOR Flash 擦除寿命大约在10万次。

  > 随着时间推移，Flash 会发生浮栅电荷泄漏，并且温度越高泄露越快（Retention: 10 年 @ 85°C）。可以在 Retention 时间之前可以把整个 page 的数据读出再写回，消耗一次擦除次数来重置。

## RRAM

nRF54L 系列内部存储使用 RRAM （阻变式随机存储器）。它通过金属氧化物的电阻来区分0和1。如果要改变其0和1状态，需要通过施加偏压来改变。

存储特性：

- 支持任意自然对齐随机寻址读写（8bit, 16bit, 32bit, 64 bit, 128bit）。

- nRF54L RRAM 的最小存储介质单元是 word line。每一个 word line 都有单独的 ECC 校验位。

  > - nRF54L15 / L10 / L05 / LM20 是 **128-bit** word line；nRF54LS05 是 **64-bit** word line。

- 可以将单一 bit `1` 写为 `0`，也可以将 `0` 写回 `1`。无需“整页擦除”，硬件上也没有“页（Page）”的概念。

  > - 这里单一 bit 操作只是 AHB 总线上的表现。实际如果 CPU 只写一个 bit，会导致整个 word line 被重写并重新计算 ECC 校验。因此每个word line 的寿命是独立的。
  > - 虽然 RRAM 没有页的概念，但软件上为了兼容，Zephyr 分区时还是会要求 “页对齐（4 KB, 0x1000）”

- nRF54L RRAM 控制器（RRAMC）可以使能一组 buffer slot，每个 buffer slot 大小和 word line 大小一致。一个 buffer slot 可以把对一个 word line 的多次单 bit 写入合并成一次真实的保存（commit），提高能效和寿命。并且，buffer slot 让 CPU 写入变为流水线化：—上一个 word line 在后台 commit 期间，CPU 可以立即发起下一个写入。最后，RRAM的写入会有瞬态尖峰电流，buffer slot 可以让电流延迟到合适的时机。

  - 写入时，如果一个 buffer slot 缓存满，则自动保存到 RRAM 存下来。

  - 写入时，如果一个 buffer slot 缓存不满，还会有三种情况会让 buffer slot 自动保存：1. CPU 主动写入`TASKS_COMMITWRITEBUF`寄存器; 2. 当前 word line 被读取; 3. 或者等一段时间（默认是128个时钟周期 ）后自动保存。

  - buffer slot 是一种动态分配的资源，不要求被缓冲的 RRAM 地址是连续的。每一个 slot 可以分散地对应RRAM上不连续地址的 word line。

    > - 54L15 / L10 / L05 / LM20：最多 32 个slot
    > - 54LV10：最多 16 个slot

- RRAMC 的写入几乎不阻塞 CPU 执行代码

  > nRF54L15 无 buffer 写入 32bit 只需 65us；1 个buffer slot 时，在一次流式写入中，平均每写 32bit 只需 22 us。并且 buffered write可将写入延迟隐藏在CPU IDLE期间。

- RRAM 每一个 128bit line 写入寿命为 1万次。

  > 随着时间推移，RRAM 单元的`0`和`1`状态（电阻值Low和High）将逐渐模糊，高温时速度会更快（Retention：10 年 @ 85°C / 2 年 @ 105°C）。这时需要主动读出数据再写回，消耗一次写入寿命。

## MRAM

nRF54H20 内部非易失存储使用 MRAM（磁阻式随机存储器）。它通过磁阻状态保存 0 和 1，掉电后数据不丢失。

其存储特性和 RRAM 类似（128bit word line，无需擦除）。目前 54H20 无公开的 Datasheet，不深入展开。

## UICR：特殊的少量永久信息

对于生产阶段一次性烧录，后续不再修改的少量数据，建议存储到 UICR。详见 《[Nordic UICR 存储寄存器详解](https://jayant-tang.github.io/2026/07/4f03e569cb1e/)》。

# 3. 驱动层

>  在驱动层，通常用 Flash 这个词代指可读写的 NVM。因此后续的 API 名称中的 flash 都不特指 Flash 存储器，而是泛指 NVM。

Zephyr 不希望应用层代码直接关心“这是片内 flash 还是片外 flash”。驱动层会把这些设备注册成 Zephyr device，并通过统一的 Flash API 暴露能力。

常见 API 包括：`flash_read()`, `flash_write()`, `flash_erase()`...

至于这是如何实现的，可以参考 《[详解Zephyr设备树（DeviceTree）与驱动模型](https://jayant-tang.github.io/2023/03/4b274a50e575/)》

## 驱动代码文件位置

半导体厂商会根据 Zephyr 的标准 Flash API 编写自己的 SoC 内部 NVM 驱动，并提交给 Zephyr Project。

而外部 SPI/QSPI NOR Flash，它们一般都符合 JEDEC 标准，所以`zephyr/drivers/flash `下有统一的驱动：

- SPI NOR Flash 驱动：`spi_nor.c`

- QSPI NOR Flash 驱动：`flash_mspi_nor.c`, `nrf_qspi_nor.c`

  > - 最新的 Zephyr Muti-bit SPI 支持通用的多位 SPI（如 Quad SPI、Octal SPI 等），支持命令相、地址相和数据相的阶梯式高级传输，是标准驱动，`flash_mspi_nor.c ` 就是按照 MSPI 标写的驱动 。54L15 的 sQSPI （用 RISC-V 核模拟的软件QSPI）可以支持这个驱动。
  > - nRF52/nRF53 系列的硬件 QSPI 有一定限制，早期的 Zephyr 版本没有MSPI 驱动都没有定义。而是单独为 QSPI NOR Flash 提供了`nrf_qspi_nor.c`驱动。

## 查看当前工程所用的驱动

首先，要选择一个用到了存储器的例程。并不是所有例程都有读写内部/外部 NVM的功能，这里用 `nrf/samples/bluetooth/peripheral_uart` 例程举例。因为这个 BLE 例程支持蓝牙绑定，我们知道蓝牙绑定信息是需要永久存储的，因此它一定用到了 Flash 驱动。

首先，确保 NCS 和你的工程在同一个 VS Code workspace。在 nRF Connect for VS Code 插件中，先选中你的 build 下想查看的镜像。然后，在 Source Files 中选中 SDK，路径为`zephyr/drivers/flash/`。

![image-20260712153619653](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/5f1817f9bbc6018e39cf6d1dd2e0c91d.png)

## 驱动如何被载入的？

这两个源码是被 CMake 导入的，在`zephyr/drivers/flash/CMakeLists.txt`中，根据相应的`CONFIG_`选项来决定。

```cmake
...
zephyr_library_sources_ifdef(CONFIG_SOC_FLASH_NRF_RRAM soc_flash_nrf_rram.c)
...
zephyr_library_sources_ifdef(CONFIG_SPI_NOR spi_nor.c)
```

其中，`CONFIG_SOC_FLASH_NRF_RRAM` 和 `CONFIG_SPI_NOR`这两个选项是被 `CONFIG_FLASH=y`导入的。在顶层的`v3.4.0/zephyr/drivers/flash/Kconfig`中，引用了两个子菜单：

```Kconfig
if FLASH

...
source "drivers/flash/Kconfig.nor"
...
source "drivers/flash/Kconfig.nrf_rram"
...

endif # FLASH
```

而这两个菜单里面，都会根据设备树自动开启对应的CONFIG。以 SPI NOR 为例：

```Kconfig
menuconfig SPI_NOR
	bool "SPI NOR Flash"
	default y                                # 如果依赖全部满足，则默认为 yes
	depends on DT_HAS_JEDEC_SPI_NOR_ENABLED  # 依赖：设备树中有 compatible = "jedec,spi" 的设备，其 status = "okay"
	select FLASH_HAS_DRIVER_ENABLED          # 如果此选项为 yes select 自动把后续 CONFIG 全部设置为 yes
	select FLASH_HAS_EXPLICIT_ERASE
	select FLASH_HAS_PAGE_LAYOUT
	select FLASH_JESD216
	select FLASH_HAS_EX_OP
	select SPI

```

因为我们选的板子`nrf54l15dk/nrf54l15/cpuapp`默认的的设备树配置里刚好有一个符合条件的 Flash，并且被使能了：

`v3.4.0/zephyr/boards/nordic/nrf54l15dk/nrf54l_05_10_15_cpuapp_common.dtsi`

```DTS
&spi00 {
	status = "okay";
	cs-gpios = <&gpio2 5 GPIO_ACTIVE_LOW>;
	pinctrl-0 = <&spi00_default>;
	pinctrl-1 = <&spi00_sleep>;
	pinctrl-names = "default", "sleep";

	mx25r64: mx25r6435f@0 {
		compatible = "jedec,spi-nor";
		status = "okay";
		reg = <0>;
		spi-max-frequency = <8000000>;
		jedec-id = [c2 28 17];
		sfdp-bfp = [e5 20 f1 ff ff ff ff 03 44 eb 08 6b 08 3b 04 bb
			    ee ff ff ff ff ff 00 ff ff ff 00 ff 0c 20 0f 52
			    10 d8 00 ff 23 72 f5 00 82 ed 04 cc 44 83 48 44
			    30 b0 30 b0 f7 c4 d5 5c 00 be 29 ff f0 d0 ff ff];
		size = <67108864>;
		has-dpd;
		t-enter-dpd = <10000>;
		t-exit-dpd = <35000>;
		reset-gpios = <&gpio2 0 GPIO_ACTIVE_LOW>;
	};
};
```

所以 `CONFIG_SPI_NOR `会根据 `CONFIG_FLASH=y`自动打开，并载入`spi_nor.c` 驱动。

Zephyr 中其他标准驱动的载入方法也是类似的。

> 对于 `nrf/samples/bluetooth/peripheral_uart` 这个例程来说，蓝牙绑定信息是存储在内部 NVM 的 Settings 分区的。其实并不需要这个外部 Flash。
>
> 因此你可以主动关闭这个外部 Flash 驱动，方法是在工程的 `prj.conf`中主动写明：
> ```Kconfig
> CONFIG_SPI_NOR=n
> ```
>
> 编译完毕后，会发现固件不再使用`spi_nor.c`驱动：
>
> ![image-20260712160136549](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/2569e296de4c8e9b637cd869ad5fe224.png)
>
> Flash 和 RAM 占用也从：
>
> ```text
> Memory region         Used Size  Region Size  %age Used
>            FLASH:      233948 B      1524 KB     14.99%
>              RAM:       38852 B       256 KB     14.82%
>         IDT_LIST:           0 B        32 KB      0.00%
> ```
>
> 降低到了：
>
> ```text
> Memory region         Used Size  Region Size  %age Used
>            FLASH:      225148 B      1524 KB     14.43%
>              RAM:       38612 B       256 KB     14.73%
>         IDT_LIST:           0 B        32 KB      0.00%
> ```

## Devicetree 驱动配置

根据前面的讲解，你大概已经了解，要打开 Flash 的驱动，只需要两个条件：

- 打开全局的 Zephyr Flash 驱动开关 `CONFIG_FLASH=y`；
- 设备树中对应的节点已经使能（ `status = "okay"`）。

如此一来，编译时节点对应的驱动就会被自动加载。

不过除此之外，**设备树内还需要填写一些具体配置信息**。内部 NVM 一般不需要配置，直接使用 board 自带的默认值，一般都不需要修改。

而外部 NOR Flash，一般是需要配置的：

```dts
&spi00 {
	status = "okay";
	cs-gpios = <&gpio2 5 GPIO_ACTIVE_LOW>;
	pinctrl-0 = <&spi00_default>;
	pinctrl-1 = <&spi00_sleep>;
	pinctrl-names = "default", "sleep";

	mx25r64: mx25r6435f@0 {
		compatible = "jedec,spi-nor";
		status = "okay";
		reg = <0>;
		spi-max-frequency = <8000000>;
		jedec-id = [c2 28 17];
		sfdp-bfp = [e5 20 f1 ff ff ff ff 03 44 eb 08 6b 08 3b 04 bb
			    ee ff ff ff ff ff 00 ff ff ff 00 ff 0c 20 0f 52
			    10 d8 00 ff 23 72 f5 00 82 ed 04 cc 44 83 48 44
			    30 b0 30 b0 f7 c4 d5 5c 00 be 29 ff f0 d0 ff ff];
		size = <67108864>;
		has-dpd;
		t-enter-dpd = <10000>;
		t-exit-dpd = <35000>;
		reset-gpios = <&gpio2 0 GPIO_ACTIVE_LOW>;
	};
};

&pinctrl {
	spi00_default: spi00_default {
		group1 {
			psels = <NRF_PSEL(SPIM_SCK, 2, 1)>,
				<NRF_PSEL(SPIM_MOSI, 2, 2)>,
				<NRF_PSEL(SPIM_MISO, 2, 4)>;
		};
	};

	spi00_sleep: spi00_sleep {
		group1 {
			psels = <NRF_PSEL(SPIM_SCK, 2, 1)>,
				<NRF_PSEL(SPIM_MOSI, 2, 2)>,
				<NRF_PSEL(SPIM_MISO, 2, 4)>;
			low-power-enable;
		};
	};
}
```

其中，`jedec-id` 和 `sfdp-bfp`是必须要的，可以从 Flash 的 Datasheet 中读取。但是更简单的获取方法是用 `zephyr/samples/drivers/jesd216`例程，只需要配置好 SPI 和引脚，在串口日志中会自动打印出 `jedec-id` 和 `sfdp-bfp`。后续再粘贴到自己的设备树里就可以。

这里必须要开启 `CONFIG_SPI_NOR_SFDP_RUNTIME=y` 。开启此选项后，驱动会在运行时通过 SFDP 表自动获取 Flash 参数，即使 `jedec-id` 初始值不准确（`[00 00 00]`）也能在后续自动修正。

> SPI 引脚配置：
>
> 在 `&pinctrl`内定义的是 SPI 外设引脚复用（SCK, MOSI, MISO）。在 SPI 节点内通过`pinctrl-0 = <&spi00_default>;` 和 `pinctrl-1 = <&spi00_sleep>;`来引用。
>
> 而对于片选（CS）引脚，由于一个 SPI 总线可能连接好几个设备，因此`cs-gpios`实际上可能是一个数组，比如可以这样写：
>
> ```dts
> cs-gpios = <&gpio2 5 GPIO_ACTIVE_LOW>,
>            <&gpio0 6 GPIO_ACTIVE_LOW>,
> ```
>
> SPI 总线下挂载的设备，`mx25r6435f@0` 就是第0个设备，会使用`cs-gpios`中的第 0 个片选引脚，也就是`P2.5`。这里`@0`和`reg = <0>`必须是一致的，都代表第0个SPI总线设备。
>
> `cs-gpios` 在 Zephyr 中会使用 gpio 驱动实现软件片选，而不是SPI硬件片选。因此可以选择任意可用的 GPIO，不受数据手册中 SPI CS脚的约束。如果想用硬件片选，则需要把 CS 写到 pinctrl 内。

## 驱动层接口

无论是内部 Flash 还是外部 Flas，其驱动代码中都提供了相同的接口，如：

```c
static DEVICE_API(flash, spi_nor_api) = {
	.read = spi_nor_read,
	.write = spi_nor_write,
	.erase = spi_nor_erase,
	.get_parameters = flash_nor_get_parameters,
	.get_size = flash_nor_get_size,
#if defined(CONFIG_FLASH_PAGE_LAYOUT)
	.page_layout = spi_nor_pages_layout,
#endif
#if defined(CONFIG_FLASH_JESD216_API)
	.sfdp_read = spi_nor_sfdp_read,
	.read_jedec_id = spi_nor_read_jedec_id,
#endif
#if defined(CONFIG_FLASH_EX_OP_ENABLED)
	.ex_op = flash_spi_nor_ex_op,
#endif
};
```

驱动代码会在程序启动阶段（内核启动后、main之前）初始化存储器实例对象。之后应用层就可以用 flash api 操作具体的存储器了。

有了驱动和设备树配置，下一步就是将存储器划分为具体的分区。

# 4. 分区抽象层

在基于 Zephyr 的实际产品中，常见的场景是：

- 片内 NVM 上放 bootloader、主固件、settings storage；
- 片外 NOR Flash 上放 OTA 的 secondary slot，或者更大的文件系统分区。

因此要解决以下问题：

1. 工程里面需要一个文件来配置分区布局
2. 代码里需要访问到这些分区对象，无需关心分区的具体地址

## 分区配置文件

### Devicetree 分区配置

> **NCS v3.4.0 LTS 之后，都推荐用 Zephyr 自己的 Devicetree 进行分区。老的 Partition Manager 将会被逐步抛弃。**

下面给一个**扁平分区**的完整示例。 NCS v3.4.0，内部 flash + 外部 flash，同时包含固件分区和存储分区，且没有任何嵌套分区（没有安全固件）。

```DTS
/{
    chosen {
        zephyr,flash = &flash0;
        zephyr,code-partition = &slot0_partition;
        zephyr,settings-partition = &storage_partition;
    };
};

&flash0 {
    partitions {
        ranges;                          // ← v3.4.0 新增：替代 compatible = "fixed-partitions"，支持地址翻译
        #address-cells = <1>;
        #size-cells = <1>;

        // bootloader 所在分区
        boot_partition: partition@0 {
            compatible = "zephyr,mapped-partition";   // ← v3.4.0 新增
            label = "mcuboot";
            reg = <0x00000000 0x0000c000>;
            read-only;
        };

        // app 所在分区
        slot0_partition: partition@c000 {
            compatible = "zephyr,mapped-partition";   // ← v3.4.0 新增
            label = "image-0";
            reg = <0x0000c000 0x000e4000>;
        };

        // 数据存储分区
        storage_partition: partition@f0000 {
            compatible = "zephyr,mapped-partition";   // ← v3.4.0新增
            label = "storage";
            reg = <0x000f0000 0x00010000>;
        };
    };
};

&mx25r64 {
    partitions {
        compatible = “fixed-partitions”;              // ← 外部Flash 继续用 fixed-partitions
        #address-cells = <1>;
        #size-cells = <1>;

        // DFU时存放升级固件的分区
        slot1_partition: partition@0 {
            label = "image-1";
            reg = <0x00000000 0x000e4000>;
        };

        // 另一个数据存储分区（运行时可修改）
        ext_fs_partition: partition@e4000 {
            label = "external_storage";
            reg = <0x000e4000 0x0011c000>;
        };
    };
};
```

说明：

- 分区配置节点`partitions`放在真实的存储器`&flash0`和`&mx25r64`下面

- `reg`属性控制分区的**起始地址**和**长度**。每一块存储器都是从地址`0`开始划分。

- 分区内部的`label`属性基本上只是给人看的字符串，不重要。

  > 默认情况下，Settings Subsys 的 NVS/ZMS/FCB 后端默认会找 label 为 `storage` 的分区。但是我们一般还是应该用 `chosen/zephyr,settings-partition` 属性来主动指定分区。

- `chosen`节点下的属性值一般是给 Zephyr 内核、子系统和官方库使用的配置。

  - `zephyr,flash`：默认的 NVM 设备。Zephyr Flash Driver, Flash MAP, MCUboot 中都有使用。
  - `zephyr,code-partition`：当前代码执行所在的分区。APP 里应该指向 `&slot0_partition`，而MCUboot里应该指向`&boot_partition`。
  - `zephyr,settings-partition`：Zephyr Settings 子系统会使用的分区，用于存储配置。

- `boot_partition`、`slot0_partition`、`slot1_partition` 这些 node label 是 MCUboot 生态里最常见的命名，很多 sample 和文档都默认按这个名字举例。

> **设备树分区，多镜像工程里”听谁的”？**
>
> 这是比较容易踩坑的点。
>
> 在开启`sysbuild`的多镜像工程里，mcuboot、主 app、可能还有 `TF-M`，它们**每个镜像都有自己的 Devicetree**，也各自生成自己的 `zephyr.dts` 和 `flash_map`。所以如果你使用的是 **DTS 分区**，并不存在一个“天然全局唯一”的分区定义文件。
>
> 所以，**如果你用 DTS 分区，必须让它们的分区写成一样**。最稳妥的做法，是把分区（内部和外部）写成一个固定的`.dtsi`文件。各个镜像的 `.overlay`都来引用这个`.dtsi`。
> 
> 注意别把 `chosen` 写到这个共用的`.dtsi`文件里去了。
>
> 可以参考 v3.4.0 的 `nrf/applications/nrf_desktop`例程实现。
>

### Partition Manager 分区配置（版本低于 v3.3.x）

在 NCS 旧方案里，分区并不一定写在 DTS 中，而是交给 Partition Manager 在构建时统一生成。如果你想具体了解，可以看 [《Zephyr项目的配置与构建系统》](https://jayant-tang.github.io/2022/12/2a39e705bff0/#7.-存储器分区文件（partition-manager）)。

<details>
    <summary>[点击展开详情]</summary>

简单来说，Partition Manager 是 Nordic NCS 提供的分区工具，不是 Zephyr 上游机制。

- 对于产品开发，可以用`pm_static.yml`**静态定义分区**
- 对于NCS中的例程，它会根据 Kconfig、启用的镜像、外部 flash 等条件，在构建时**动态生成分区布局**。

它的优点是：不论一个工程里有几个镜像，都只用一个统一`pm_static.yml`文件来管理分区。

但缺点也很明显，新人想上手理解比较困难。有以下问题：

1. 配置文件里既要写物理分区，又要写分区的各种组合，难以顺畅地理解。

2. 对于隐式的动态生成分区。如果开发者不了解这件事，调试时会有很大困惑。

   ```yaml
   # 真实物理分区
   mcuboot:
     address: 0x0
     region: flash_primary
     size: 0x7000
     
   # mcuboot_pad + app 其实就是 slot 0，却要分开写
   mcuboot_pad:
     address: 0x7000
     region: flash_primary
     size: 0x800
   app:
     address: 0x7800
     region: flash_primary
     size: 0xb8800
   
   # 前面已经有物理分区了，但这里还要组合一个标签给 mcuboot 参考
   mcuboot_primary:
     address: 0x7000
     orig_span: &id001
     - app
     - mcuboot_pad
     region: flash_primary
     size: 0xb9000
     span: *id001
     
   # 前面已经有 app 分区了，这里又重新命名了一下 mcuboot_primary_app 
   mcuboot_primary_app:
     address: 0x7800
     orig_span: &id002
     - app
     region: flash_primary
     size: 0xb8800
     span: *id002
   
   # 这里又是分区组合 + 物理分区的写法
   mcuboot_secondary:
     address: 0xc0000
     orig_span: &id003
     - mcuboot_secondary_pad
     - mcuboot_secondary_app
     region: flash_primary
     size: 0xb9000
     span: *id003
   
   # 真实物理分区
   mcuboot_secondary_pad:
     region: flash_primary
     address: 0xc0000
     size: 0x800
   mcuboot_secondary_app:
     region: flash_primary
     address: 0xc0800
     size: 0xb8800
     
   # 真实物理分区
   settings_storage:
     address: 0x179000
     region: flash_primary
     size: 0x4000
   ```

</details>

### 从 PM 迁移到 DTS 

NCS v3.3 文档已经明确说明：

1. Partition Manager 正在被 Zephyr 默认的 Devicetree 分区替代；
2. NCS v3.3 中 Partition Manager 仍然默认启用，用于避免旧项目直接坏掉；
3. 后续 major release 会默认关闭 Partition Manager；
4. 再后续会从 NCS main branch 移除；

所以新项目建议直接使用 Devicetree fixed partitions。旧项目如果已经依赖 Partition Manager，不要直接手改 `build/partitions.yml`，应该用官方迁移脚本把布局迁移到 DTS：

官方提供了迁移脚本：

```powershell
python scripts/pm_to_dts.py
```

迁移完成后，再通过 sysbuild 配置关闭 Partition Manager，例如：

```conf
SB_CONFIG_PARTITION_MANAGER=n
```

> NCS v3.4.0 的 Matter / nRF Desktop 等复杂例程已经改用 DTS 方式配置分区。例如:
>
> ```
> #include <samples/matter/nrf52840_partitions.dtsi>
> ```

## 从代码访问分区布局

把分区写进 overlay 之后，Zephyr/NCS 构建系统大致会经历这几步：

1. 由于分区属于 dts，因此会按照 dts 的构建流程进行。
2. dts 中的信息最终都会生成C代码中可以访问的宏。
3. `flash_map` 再基于这些宏，为 C 代码提供分区 ID、offset、size、device 等访问入口。

可以直接看一个最常见的例子。假设 DTS 里这样写：

```dts
/{
    chosen {
        zephyr,settings-partition = &storage_partition;
    };
};

&flash0 {
    partitions {
        ranges;
        #address-cells = <1>;
        #size-cells = <1>;

        storage_partition: partition@f0000 {
            compatible = "zephyr,mapped-partition";
            label = "storage";
            reg = <0x000f0000 0x00010000>;
        };
    };
};
```

到了 C 代码里，**最常见**会变成下面这些宏。

设备树节点：

| 宏                                     | 值类型             | 参数类型                                  | 功能                    |
| -------------------------------------- | ------------------ | ----------------------------------------- | ----------------------- |
| `DT_NODELABEL(storage_partition)`      | Devicetree Node ID | node label                                | 获取 Devicetree Node ID |
| `DT_CHOSEN(zephyr_settings_partition)` | Devicetree Node ID | `chosen`节点下的属性名，特殊符号用`_`代替 | 获取 Devicetree Node ID |

从分区抽象层的角度看：

| 宏                                     | 值类型                | 参数类型   | 功能                                                         |
| -------------------------------------- | --------------------- | ---------- | ------------------------------------------------------------ |
| `PARTITION_ID(storage_partition)`      | 整数                  | node label | 获取分区的数字ID                                             |
| `PARTITION_OFFSET(storage_partition)`  | 整数                  | node label | 获取分区在 Flash 设备内的偏移（Bytes）                       |
| ` PARTITION_SIZE(storage_partition)`   | 整数                  | node label | 获取分区的大小（Bytes）                                      |
| ` PARTITION_EXISTS(storage_partition)` | 布尔                  | node label | 检查分区是否存在                                             |
| `PARTITION_DEVICE(storage_partition)`  | `struct device *`指针 | node label | 获取分区所在 Flash 设备的指针。等价于 `DEVICE_DT_GET(...)`获取的设备指针 |
| `PARTITION_ADDRESS(storage_partition)` | 整数                  | node label | 获取分区的绝对地址                                           |

此外，还有`PARTITION_NODE_OFFSET()`之类的宏。它和`PARTITION_OFFSET()`唯一的区别是输入参数不一样。前者的输入参数是 Devicetree NODE ID，后者输入参数是node label。

以下两个写法等价：

```c
#define ADDR PARTITION_OFFSET(storage_partition)
```

```c
#define ADDR PARTITION_NODE_OFFSET(DT_NODELABEL(storage_partition))
```

至于为什么会有`PARTITION_NODE_`宏，这个看起来多此一举，但其实功能更多一些，后面章节会解释。

代码示例：

```c
#include <zephyr/storage/flash_map.h>

#define STORAGE_NODE DT_NODELABEL(storage_partition)

const struct device *flash_dev = PARTITION_DEVICE(STORAGE_NODE);


off_t offset = PARTITION_OFFSET(storage_partition);
size_t size = PARTITION_SIZE(storage_partition);

const struct flash_area *fa;
int err;

err = flash_area_open(PARTITION_ID(storage_partition), &fa);
if (err == 0) {
    printk("storage offset: 0x%lx, size: 0x%lx\n",
           (long)fa->fa_off,
           (long)fa->fa_size);
    flash_area_close(fa);
}
```

上层的文件系统可以用`flash_area_`来操控对应的分区，而无需关心分区在存储器上的具体物理地址。

## 分区宏版本变迁

分区宏经历过三个阶段：

1. NCS 版本 <  v2.1.x （≤ Zephyr 3.1）：`FLASH_AREA_`宏，参数是设备树节点下的`label = "xxxx"`字符串。label字符串可能不是唯一的，编译期间有歧义。
2. NCS 版本 v2.2.x - v 3.3.x（Zephyr 3.2–4.3）：`FIXED_PARTITION_`宏。参数是设备树节点的 node label，作为编译时可解析的符号，能确保分区名唯一。
3. NCS 版本 ≥  v3.4.0 LTS（≥ Zephyr 4.4）：`PARTITION_`宏。**只是命名简化**，去掉了`FIXED_`。因为固定分区是早期概念，现在用 mapped 分区。

| 功能                | 第 1 代（≤ Zephyr 3.1）<br>参数: label 属性字符串 | 第 2 代（Zephyr 3.2–4.3）<br>参数: DTS node label | 第 3 代（≥ Zephyr 4.4）<br>参数: DTS node label |
| ------------------- | ------------------------------------------------- | ------------------------------------------------- | ----------------------------------------------- |
| 分区 ID             | `FLASH_AREA_ID(label)`                            | `FIXED_PARTITION_ID(node_label)`                  | `PARTITION_ID(node_label)`                      |
| 分区偏移（字节）    | `FLASH_AREA_OFFSET(label)`                        | `FIXED_PARTITION_OFFSET(node_label)`              | `PARTITION_OFFSET(node_label)`                  |
| 分区大小（字节）    | `FLASH_AREA_SIZE(label)`                          | `FIXED_PARTITION_SIZE(node_label)`                | `PARTITION_SIZE(node_label)`                    |
| 分区是否存在        | `FLASH_AREA_LABEL_EXISTS(label)`                  | `FIXED_PARTITION_EXISTS(node_label)`              | `PARTITION_EXISTS(node_label)`                  |
| 分区所属 Flash 设备 | `FLASH_AREA_DEVICE(label)`                        | `FIXED_PARTITION_DEVICE(node_label)`              | `PARTITION_DEVICE(node_label)`                  |
| label 字符串        | `FLASH_AREA_LABEL_STR(label)`                     | ⛔ 已移除                                          | ⛔ 已移除                                        |

## 设备树分区版本变迁

前面章节举例的”内部+外部“存储是一个扁平分区，分区只有一层，没有”子分区“的说法。但是对于有安全固件的复杂工程来说，情况就发生了变化。

以一个经典的带 TF-M TrustZone 嵌套分区的 nRF91xx 布局为例：

```text
Flash 0x00000000  ┌──────────────────────┐
                  │  mcuboot (64K)       │  ← boot_partition
  0x00010000      ├──────────────────────┤
                  │ ┌ slot0 secure (256K)│  ← slot0_s_partition
                  │ │                    │
                  │ ├ slot0 non-secure   │  ← slot0_ns_partition
                  │ │ (192K)             │
  0x00080000      ├─┴────────────────────┤
                  │ ┌ slot1 secure (256K)│  ← slot1_s_partition
                  │ │                    │
                  │ ├ slot1 non-secure   │  ← slot1_ns_partition
                  │ │ (192K)             │
  0x000f0000      ├─┴────────────────────┤
                  │  tfm-ps / its / otp  │
  0x000f8000      ├──────────────────────┤
                  │  storage (32K)       │  ← storage_partition
                  └──────────────────────┘
```

旧的写法是:

```DTS
&flash0 {
    partitions {
        compatible = "fixed-partitions";        // ← 父节点声明类型为"fixed-partitions"
        #address-cells = <1>;
        #size-cells = <1>;

        boot_partition: partition@0 {
            label = "mcuboot";
            reg = <0x00000000 0x00010000>;
        };
		
		// 分区0在这里，占用@10000地址
        slot0_partition: partition@10000 {
            label = "image-0";
            reg = <0x00010000 0x00070000>;
        };

        // 分区0的子分区容器节点，且也占用占用@10000地址。
        slot0_subpartitions: fixed-subpartitions@10000 {
            compatible = "fixed-subpartitions";  // ← 特殊的类型 "fixed-subpartitions"
            #address-cells = <1>;
            #size-cells = <1>;

            slot0_s_partition: partition@0 {
                label = "image-0-secure";
                /* ⚠️ reg 是相对 slot0_partition 的偏移，不是绝对地址 */
                reg = <0x00000000 0x00040000>;
            };
            slot0_ns_partition: partition@40000 {
                label = "image-0-nonsecure";
                reg = <0x00040000 0x00030000>;
            };
        };
        
		/* slot1 和 slot 0情况类似，略 */

        /* tfm-ps, tfm-its, tfm-otp, storage 等扁平分区略 */
    };
};
```

它的写法其实很奇怪：**一个分区的子分区居然不能直接放在老分区的内部，而是要另开一个容器节点。容器节点和父分区本身的 Unit Address 还重合了，这个是完全不符合设备树的语法规范的。**

> [Devicetree Specification 2.2.1.1. Node Name Requirements](https://devicetree-specification.readthedocs.io/en/latest/chapter2-devicetree-basics.html#node-name-requirements) 
>
> The unit-address must match the first address specified in the reg property of the node. If the node has no reg property, the @unit-address must be omitted.

除了前面这个令开发者疑惑的问题之外，还有一个不影响开发者，但是隐含在 Zephyr 构建系统内、不够优雅的问题。构建系统需要获取一个子分区的地址时，`reg`里面的偏移量是相对于父分区，不是相对于 flash 基地址。要算出子分区的绝对地址，宏必须一层层向上遍历父节点，直到找到名为 partitions 的` compatible = "fixed-partitions"`节点才能得到基地址。

> 举个例子：一个 I2C 外设在 APB 总线上的地址是 `0x500C6000`，有一个挂在此 I2C 总线上的 I2C 设备的地址是 `0x7`。在编译期间，构建系统根本不会把它们俩相加得到`0x500C6007`，因为这样做根本没有任何意义。
>
>  老的设备树写法遇到的就是这个问题。fixed-subpartitions 并未给 DTS 编译器提供任何地址翻译规则，编译器根本不知道子分区地址和父分区地址之间的映射关系。因此，DTS 编译后的输出中，子分区的绝对物理地址信息根本就不存在，`DT_REG_ADDR()`对它无能为力，因为只能读到相对地址。这导致当你需要用到子分区的物理地址时，不得不用一大堆 `DT_FIXED_PARTITION_ADDR()` 之类的宏，手动找到父节点，再累加计算出来。

这也导致链接器无法直接从 dts 中获取程序应该运行的 ROM 地址和大小。需要 Kconfig 里面先通过一些方法把这个分区对应的`reg`值“抠”出来。赋值给`CONFIG_FLASH_LOAD_OFFSET`，然后链接器再使用。这本质是让 Kconfig 拷贝了一份 devicetree 信息。

让我们来看看 NCS v3.4.0 LTS ( Zephyr 4.4) 之后的新写法：

```DTS
&flash0 {
    partitions {
        ranges;                                 // ← 删除 compatible = "fixed-partitions"。新增 ranges;
        #address-cells = <1>;
        #size-cells = <1>;

        boot_partition: partition@0 {
            compatible = "zephyr,mapped-partition";  // ← 每个分区自己声明
            label = "mcuboot";
            reg = <0x00000000 0x00010000>;
        };

        slot0_partition: partition@10000 {
            compatible = "zephyr,mapped-partition";
            label = "image-0";
            reg = <0x00010000 0x00070000>;
            /* ✅ 子分区直接嵌套在父分区内，不需要单独节点 */
            ranges = <0x0 0x10000 0x70000>;     // ← 新增：子地址空间映射到父基址 0x10000
            #address-cells = <1>;
            #size-cells = <1>;

            slot0_s_partition: partition@0 {
                compatible = "zephyr,mapped-partition";
                label = "image-0-secure";
                /* ✅ reg 仍可相对父分区，DT 通过 ranges 自动算出绝对地址 */
                reg = <0x00000000 0x00040000>;
            };
            slot0_ns_partition: partition@40000 {
                compatible = "zephyr,mapped-partition";
                label = "image-0-nonsecure";
                reg = <0x00040000 0x00030000>;
            };
        };
		
		/* slot1 和 slot 0情况类似，略 */

        /* 扁平分区保持不变，只是加上 compatible */
        storage_partition: partition@f8000 {
            compatible = "zephyr,mapped-partition";
            label = "storage";
            reg = <0x000f8000 0x00008000>;
        };
    };
};
```

首先，从形式上看，新的写法清爽了很多：

- 子分区直接写在主分区内，不需要单独的容器节点
- 主分区、子分区不需要写不一样的 compatible，全部都统一成`zephyr,mapped-partition`。

并且，从本质上讲，新的写法通过假如`ranges`描述进行映射，使得所有子分区都和父分区具有相同的地址空间。在构建完毕之后，会自动把子分区的`reg`属性层层映射到顶层的`partitions`上。这样链接器就可以直接 `DT_REG_ADDR()`读取到子分区的物理地址，无需经过一堆宏计算。

>  NCS v3.4.0 LTS 之后，`FIXED_PARTITION_ID()`之类的宏只能解析旧写法的 fixed-partitions设备树。

注意外部 SPI NOR Flash 不能用 `zephyr,mapped-partition`！

`zephyr,mapped-partition` 要求父节点是 `compatible = “soc-nv-flash”` 的存储器节点（如内部 RRAM/Flash 控制器下的 `cpuapp_rram`），这样构建系统才能通过 `ranges` 属性做地址翻译。

而外部 SPI/QSPI NOR Flash 是挂在 SPI 总线上的 `jedec,spi-nor` 设备，**不是 `soc-nv-flash`**。因此对它的分区必须用老写法：

```DTS
&mx25r64 {
     partitions {
         compatible = “fixed-partitions”;   /* 不能用 ranges; */
         #address-cells = <1>;
         #size-cells = <1>;

         littlefs_partition: partition@0 {
             label = “littlefs”;
             reg = <0x00000000 0x00800000>;
         };
     };
};
```

> `PARTITION_ID()` / `PARTITION_OFFSET()` 等宏对 `fixed-partitions` 和 `zephyr,mapped-partition` 都能正常解析，调用方代码无需修改。只是 Devicetree 写法不同。

# 5. 数据模型层：存储后端

数据模型层就是决定数据要以什么形式存放在 NVM 中，它要解决以下问题：

- 寿命问题：NVM 擦写寿命有限，在同一个位置反复擦写，损坏太快
- 资源浪费：如果数据量很小，或者像 NOR Flash 这样的需要整页擦除的，裸操作会导致空间浪费和时序卡顿。
- 掉电安全：如果数据写入一半系统突然掉电，NVM 上的原本的数据不能被破坏。系统重新上电后，能正常回滚到掉电之前的状态。

让我们看看不同的存储后端是如何解决这些问题的。

## 追加式存储（NVS 和 ZMS）

追加式存储适合保存：运行时会经常变动、需要掉电保存、数据量远低于1个页大小（4kB）的数据。比如蓝牙配对信息等。

### 追加式存储原理

追加式存储非常适合存储一些经常变化的小体量数据。这里先不看具体的代码实现，而是从原理上去理解。根据如下**概念图**：

```text
   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
   │   Sector 0       │  │   Sector 1       │  │   Sector 2       │
   │                  │  │                  │  │                  │
   │  █ Valid         │  │  █ Valid         │  │                  │
   │  ░ Invalid       │  │  █ Valid         │  │                  │
   │  █ Valid         │  │  (free space)    │  │                  │
   │  ▒ Tombstone     │  │                  │  │                  │
   │  ░ Invalid       │  │                  │  │                  │
   │  █ Valid         │  │                  │  │                  │
   │  ░ Invalid       │  │                  │  │                  │
   │  ▒ Tombstone     │  │                  │  │                  │
   │  ─── FULL ───    │  │  ── NOT FULL ──  │  │   ── EMPTY ──    │
   └──────────────────┘  └──────────────────┘  └──────────────────┘
```

首先，存储后端会把一个分区分成多个**扇区（Sector）**。这就要求我们在前期分区的时候，分区的边界一定要和存储器本身的页（Page）对齐。对于要存储的数据条目，不是用 Flash API 直接存到某个地址，而是按照 Key-Value Pair（键值对）的方式存储。

写入流程：

1. 一开始，所有扇区都是空的。
2. 存储一个新数据时，选定一个 Key 值，开始存储。存储后端会按照地址从低到高的顺序，找到一个空的位置，把新数据的 Key 和 Value 写进去，记录CRC校验，再把数据标记为 Valid。
3. 用同一个 Key 更新数据时，不会在原来的位置覆盖，而是直接找到空位追加。并且把新的位置当作有效值，旧的位置当作无效值。这样就不用“先擦再写”了。
4. 删除某个 Key 的数据时，不会真的把它擦除，而是写入一个新的条目，条目内容是把这个数据记为已删除（Tombstone），这样就不用真的擦除。
5. 当几个扇区写满，只剩最后一个空扇区时，自动触发 **GC（Garbace Collection，垃圾回收）**：把最旧的1个扇区里面的“有效数据”全部搬到这个空扇区里。然后把最旧的扇区擦除。

```text
 GC 之后：
   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
   │   Sector 0       │  │   Sector 1       │  │   Sector 2       │
   │                  │  │                  │  │                  │
   │   (all free)     │  │  █ Valid         │  │  █ Valid (copy)  │
   │                  │  │  █ Valid         │  │  █ Valid (copy)  │
   │                  │  │  (free space)    │  │  █ Valid (copy)  │
   │                  │  │                  │  │  (free space)    │
   │                  │  │                  │  │                  │
   │                  │  │                  │  │                  │
   │   ── EMPTY ──    │  │ ──  NOT FULL  ── │  │  ── NOT FULL ──  │
   └──────────────────┘  └──────────────────┘  └──────────────────┘
```

掉电安全：

- 写新数据时掉电：新数据未完整写入，CRC校验不通过。重新上电后，通过同一个 Key 读取数据，旧数据不会丢失。
- GC时掉电：新扇区搬迁完毕才会写入标志位，因此根据标志位是否写入来决定重启后的操作
  - 掉电时新扇区已经搬迁完毕：直接继续删除旧扇区，搬迁完成
  - 掉电时新扇区未搬迁完毕：先把新扇区搬迁到一半的内容擦除，再重新搬迁

可以看出，这种追加式存储的方法可以很好地解决寿命、空间浪费和掉电安全的问题。但是，它把“数据”和记录这个数据存储信息的元数据（前面称为“数据条目”）存放在同一个扇区内。因此，**只能存储比较小的配置类数据**。

> 以上只是概念性的解释，实际 NVS 和 ZMS 的真实行为需要看源码。

### 代码示例（追加式存储）

无论用 NVS 还是 ZMS，通常都需要在设备树中定义分区：

```DTS
/{
    chosen {
        zephyr,settings-partition = &storage_partition;
    };
};

&flash0 {
    partitions {
        ranges;
        #address-cells = <1>;
        #size-cells = <1>;

        storage_partition: partition@f0000 {
            compatible = "zephyr,mapped-partition";
            label = "storage";
            reg = <0x000f0000 0x00010000>;
        };
    };
};
```

#### NVS 配置和代码

首先在 `prj.conf` 中开启 NVS 支持：

```conf
CONFIG_FLASH=y
CONFIG_FLASH_MAP=y
CONFIG_NVS=y
```

C 代码中初始化并使用 NVS：

```c
#include <zephyr/fs/nvs.h>
#include <zephyr/storage/flash_map.h>

static struct nvs_fs fs;

#define NVS_PARTITION_NODE DT_NODELABEL(storage_partition)

static int nvs_init(void)
{
    struct flash_pages_info info;
    int rc;

    /* 获取 Flash 设备 */
    fs.flash_device = PARTITION_DEVICE(NVS_PARTITION_NODE);
    if (!device_is_ready(fs.flash_device)) {
        printk("Flash device not ready\n");
        return -ENODEV;
    }

    /* 扇区大小必须等于 Flash 的页大小（erase-block-size）。
     * 通过 flash_get_page_info_by_offs() 运行时获取，避免硬编码。
     */
    fs.offset = PARTITION_OFFSET(NVS_PARTITION_NODE);
    rc = flash_get_page_info_by_offs(fs.flash_device, fs.offset, &info);
    if (rc) {
        printk("Unable to get page info: %d\n", rc);
        return rc;
    }

    fs.sector_size = info.size;
    fs.sector_count = PARTITION_SIZE(NVS_PARTITION_NODE) / info.size;

    rc = nvs_mount(&fs);
    if (rc) {
        printk("NVS mount failed: %d\n", rc);
    }
    return rc;
}

/* 写入示例：记录设备启动次数 */
static int nvs_save_boot_count(uint32_t count)
{
    return nvs_write(&fs, 1, &count, sizeof(count));
}

/* 读取示例 */
static int nvs_load_boot_count(uint32_t *count)
{
    int rc = nvs_read(&fs, 1, count, sizeof(*count));
    if (rc < 0) {
        /* 首次启动，还没有写入过这个 key */
        *count = 0;
    }
    return rc;
}

/* 删除某个 key 的所有数据 */
static int nvs_delete_boot_count(void)
{
    return nvs_delete(&fs, 1);
}
```

> **NVS Key 注意事项**：
>
> - Key 是 16 bit 自然数（`0x0001 ~ 0xFFFE`），`0x0000` 和 `0xFFFF` 为保留值，不要使用；
> - 同一个 Key 多次写入时，NVS 不会覆盖旧位置，而是在空闲区域追加新条目、把旧条目标记为无效——旧空间要等 GC 才回收；
> - Key 的语义完全由应用层自己管理——代码里的 `1` 代表"启动次数"，这个映射关系只有你自己知道；
> - `nvs_write()` 的返回值如果是正数，表示实际写入的字节数；负数表示错误。
> - **不要在 RRAM /MRAM 上使用 NVS**。虽然能用，但NVS会执行 page 擦除，而 RRAM/MRAM 不需要擦除。这会浪费存储器寿命。

#### ZMS 配置和代码

ZMS 的配置方式与 NVS 几乎一样，只是将 `CONFIG_NVS` 换成 `CONFIG_ZMS`：

```conf
CONFIG_FLASH=y
CONFIG_FLASH_MAP=y
CONFIG_ZMS=y
```

设备树中的分区定义与 NVS 完全相同——两者都是基于 Flash Map 的追加式存储，对分区的要求一致。

C 代码也高度相似，但有一个关键简化：

```c
#include <zephyr/fs/zms.h>
#include <zephyr/storage/flash_map.h>

static struct zms_fs fs;

#define ZMS_PARTITION_NODE DT_NODELABEL(storage_partition)

static int zms_init(void)
{
    fs.flash_device = PARTITION_DEVICE(ZMS_PARTITION_NODE);
    if (!device_is_ready(fs.flash_device)) {
        printk("Flash device not ready\n");
        return -ENODEV;
    }

    fs.offset = PARTITION_OFFSET(ZMS_PARTITION_NODE);

    int rc = zms_mount(&fs);
    if (rc) {
        printk("ZMS mount failed: %d\n", rc);
    }
    return rc;
}

/* 写入 */
static int zms_save_data(uint32_t id, const void *data, size_t len)
{
    return zms_write(&fs, id, data, len);
}

/* 读取 */
static int zms_load_data(uint32_t id, void *data, size_t len)
{
    int rc = zms_read(&fs, id, data, len);
    if (rc < 0) {
        return rc;
    }
    return rc;
}

/* 删除 */
static int zms_delete_data(uint32_t id)
{
    return zms_delete(&fs, id);
}
```

对比两段初始化代码，ZMS 少了两行：

```c
/* NVS 需要，ZMS 不需要 */
rc = flash_get_page_info_by_offs(fs.flash_device, fs.offset, &info);
fs.sector_size = info.size;
fs.sector_count = PARTITION_SIZE(ZMS_PARTITION_NODE) / info.size;
```

原因是 ZMS 专为 RRAM/MRAM 设计，这些存储器底层没有"页擦除"的概念——ZMS 内部会自动处理扇区划分，不需要应用层手动指定 `sector_size` 和 `sector_count`。

> **ZMS Key 注意事项**：
>
> - Key 是 **32 bit** 自然数，范围比 NVS 的 16 bit 大得多，适合 ID 编码场景（比如把模块编号和高位 flag 编码进 Key）；
> - 虽然 RRAM 支持逐 bit 写入，ZMS 的 GC 仍然以 sector 为单位运作，分区边界仍需和 `erase-block-size` 对齐；
> - **不要在 NOR Flash 上使用 ZMS**——ZMS 的设计前提是"可以把 `0` 写回 `1` 而不需要预先擦除"，NOR Flash 做不到这一点。反过来，也不要在 RRAM/MRAM 上使用 NVS。

### 实战建议

#### NVS 和 ZMS 选择

NVS 和 ZMS 的设计是非常类似的。只不过 NVS 是专门为 NOR Flash 设计的，“扇区” 的概念天然贴合 NOR Flash “页”的概念。而 ZMS 是为 RRAM / MRAM 设计的。

|              | NVS                   | ZMS            |
| ------------ | --------------------- | -------------- |
| **配置**     | `CONFIG_NVS=y`        | `CONFIG_ZMS=y` |
| **存储硬件** | NOR Flash             | RRAM / MRAM    |
| **SoC系列**  | nRF52 / nRF53 / nRF91 | nRF54          |
| **Key**      | 16 bit 自然数         | 32 bit 自然数  |

> NVS 只要看到 NOR FLASH 是 `0xff` 的地方就知道是“空位”。但 RRAM/MRAM 不需要擦除，其初始状态并不是`0xff`。所以 ZMS 的数据条目需要更多的元数据来定义什么是“空位”，典型的元数据就是擦写次数（cycle count），每次垃圾回收之后，擦写次数更小的就是“新扇区”。

#### 存储容量

存储后端的扇区大小一定要和存储器本身的页大小相等。对于 nRF52/nRF53/nRF91 这种使用 NOR Flash 的一般是 4KB （除了 5340 network core，是 2 KB）。对于 nRF54L RRAM系列这种没有“页”的，在 NCS 中为了软件兼容，在芯片的 dtsi 中定义了页大小，` erase-block-size`就是 4KB：

```DTS
cpuapp_rram: rram@0 {
    compatible = "soc-nv-flash";
    erase-block-size = <4096>;
    write-block-size = <16>;
    status = "okay";
    #address-cells = <1>;
    #size-cells = <1>;
};
```

当你的存储分区有 N 个扇区时，实际有效的存储空间是 `(N - 1) * sector_size`，因为总要留一个扇区给垃圾回收。推荐使用**至少 3 个扇区**。

虽然 2 个扇区就能正常工作，但是极端情况下，2个扇区在做垃圾回收时，要从旧扇区拷贝全部有效数据到新扇区。当有效数据接近一个扇区时，还会出现 **GC 震荡 —— 假设有效数据 3.5KB，而扇区大小是 4KB，那么每写入 0.5 KB 就会触发一次全量搬迁。**

而 3 个扇区的情况下，当触发垃圾回收时，只需要把最旧的扇区中的有效数据搬迁到空扇区。在这之前，频繁更新的数据可能已经在另一个写了一半的扇区中了，所以要搬迁的数据可能非常少。

## 文件系统：LittleFS

### 为什么需要文件系统

追加式存储（NVS/ZMS）适合用整数 Key 存取小块数据。但有些场景 Key-Value 模型不够用：

- 存储 TLS 证书、Web 页面等**以文件形式存在**的资源；
- 数据需要**目录层级**来组织（如 `/certs/device.crt`、`/log/2026-07.txt`）；
- **日志持续追加**写入，要求方便导出查看；
- 如果单条数据超过几百 KB，追加式存储管理起来低效。

这时候就需要一个真正的文件系统。LittleFS 就是专为 NOR Flash / RRAM / MRAM 这类嵌入式存储器设计的文件系统，目前已经是 Zephyr 的默认文件系统方案。

### LittleFS 的设计

LittleFS 和追加式存储一样，遵循**不原地覆盖**的原则来保证磨损均衡和掉电安全。这种形式叫做**日志文件系统**。

区别是：

- NVS / ZMS 的**元数据（ATE, Allocation Table Entry, 分配表条目）**和 **数据（Data）**本身都存放在同一物理页；
- LittleFS 的**元数据（metadata）**和 **文件（Files）**分开放在不同物理页，在 LittleFS 中被称为**块（Block）**。**块（Block）**大小必须等于 Flash 的页大小（erase-block-size），和前面的“扇区”其实指的同一个东西，都是最小单一可擦除单元。每个 block 同一时刻只处于三种状态之一：已分配（存着有效数据）、空闲（可被分配）、待回收（COW 后留下的旧块，等待擦除）。

由于**元数据**和数据本身分离在不同 block ，因此可以**更有效率地管理大文件**。

```text
    目录 metadata pair (块 A/B 交替)
    ┌─────────────────────────────────┐
    │  /app/config.bin                │
    │    size: 1024                   │  ← 元数据：文件名、大小、
    │    blocks: [8, 12, x, x]        │           数据块指针列表
    │                                 │
    │  /app/cert.pem                  │
    │    size: 2048                   │
    │    blocks: [3, x, x, x]         │
    └──────────┬──────────────────────┘
               │
               │ 指针指向数据块
               │
      ┌────────┴──────────┐
      ▼                   ▼
    ┌────────────┐   ┌────────────┐
    │ Block 8    │   │ Block 12   │
    │ config.bin │   │ config.bin │    ← 数据：文件的
    │ segment 1  │   │ segment  2 │       实际内容
    │ (4096 B)   │   │ (1024 B)   │
    └────────────┘   └────────────┘
```

**Metadata Pair（元数据对）**：LittleFS 最核心的设计。每个目录、每个文件的元数据（名字、大小、数据块位置等）不存单个 block，而是存在**2个交替使用的 block** 中：

```text
  更新前：                     更新后：
  ┌─────────┐  ┌─────────┐    ┌─────────┐  ┌─────────┐
  │ Block A │  │ Block B │    │ Block A │  │ Block B │
  │ (v1) ✓  │  │ (v0)    │    │ (v1)    │  │ (v2) ✓  │
  └─────────┘  └─────────┘    └─────────┘  └─────────┘
```

更新元数据时，先在 B 写入新版本 v2，写入完毕后再把"当前有效"标记从 A 切换到 B。如果在写入 B 的过程中掉电，B 的 CRC 校验不通过，重启后 A 仍然是有效版本，文件系统回到更新前的状态。

**CoW (Copy on Write) **：修改文件数据时，LittleFS 分配新 block 写入新数据，然后通过 metadata pair 把文件的数据块指针从旧 block 更新到新 block。旧 block 进入"待回收"状态，由后台逐步擦除。

> 可能你会想，这个和 NVS / ZMS 的设计有什么不同？
>
> 实际上，它们都是原子操作，只不过原子操作粒度的不同。比如，当你要存储 Wi-Fi SSID 和 Wi-Fi 密码时，如果这是两个不同的 NVS/ZMS 数据，你先更新 SSID，成功；然后更新密码，掉电失败。重启后，虽然旧数据不会丢失，但是 SSID 和密码已经不匹配了。这说明 **NVS / ZMS 原子操作的粒度是一个数据条目**。
>
> LittleFS 的 CoW 机制会确保一个文件对应的所有 block 都被成功写入时，才算一次完整的原子操作。由于 LittleFS 的元数据和文件分散在两个不同的 block，当文件已经拷贝完毕，但是写元数据掉电时，重新上电之后，还是能恢复老文件。但是新拷贝的文件变成孤儿数据块，白白占着空间等待GC。
>
> 这个 Wi-Fi SSID 和密码的例子并不是要说明哪个更有优势，只是想说明它们的原子操作粒度不同。

**动态磨损均衡**：这和追加式存储的做法有本质区别。NVS/ZMS 靠持续的数据写入，多个扇区的自然轮转来触发GC，对**不常修改的数据**也能蹭到轮转。但 LittleFS 中，一个文件如果一年不改，它占的 block 就不会被自然回收——磨损均衡必须**主动**做。

LittleFS 的块分配器会跟踪每个 block 的擦除次数。分配新 block 时，如果发现某个空闲 block 的擦除次数比已分配 block 高，就先把"冷数据"搬到这个擦除次数高的 block 上，再把擦除次数低的 block 释放出来给自己用。**这个过程对上层代码完全透明，开发者不用关心。**

> 这个机制在极端场景下有一个代价：如果文件系统几乎满了，块分配器找不到空闲 block 来搬迁冷数据，磨损均衡的效果就会打折扣。因此**不要让 LittleFS 分区长期处于 90% 以上的占用率**。

### LittleFS 的资源占用

在 LittleFS 中，每一个目录（无论目录里有没有文件）都要占用 2 个 block。同一个目录下所有的文件，都共用这个目录的 block 来存储元数据。因此，要想使用 LittleFS，一上来就要吃掉至少 6 个block：

- LittleFS 本身： 2 个 block
- 根目录： 2 个 block
- 数据本身：至少 1 个 block （`file_size / block_size`）
- 空 block：至少 1 个，用于垃圾回收

此外每增加一个目录，就要增加 2 个 block。根据文件大小，还要适当增加block。另外，所有的元数据、数据都需要共享垃圾回收的block，因此还需要2 ~ 4个空block。

**实际上， Zephyr 官方示范的最低合理值也要 16 个 block（16 * 4 kB，外部 Flash）**。工程上一般也要 32~128 个 block，不是内部 NVM 能够承受的。

### 代码示例（LittleFS）

最小配置：

```conf
CONFIG_FLASH=y
CONFIG_FLASH_MAP=y
CONFIG_FILE_SYSTEM=y
CONFIG_FILE_SYSTEM_LITTLEFS=y
```

LittleFS 的挂载信息不能完全从设备树自动生成——block 大小、block 数量、读写粒度等参数必须运行时从 Flash 驱动获取，然后填入 `struct fs_littlefs`。因此推荐在 DTS 中只定义分区，在代码中手动组装挂载参数：

```dts
/* 设备树中定义分区 */
&mx25r64 {
    partitions {
        ranges;
        #address-cells = <1>;
        #size-cells = <1>;

        littlefs_partition: partition@0 {
            compatible = "zephyr,mapped-partition";
            label = "littlefs";
            reg = <0x00000000 0x00100000>;
        };
    };
};
```

```c
#include <zephyr/fs/littlefs.h>
#include <zephyr/storage/flash_map.h>

#define LFS_PARTITION_NODE DT_NODELABEL(littlefs_partition)

static struct fs_littlefs lfs_data;
static struct fs_mount_t lfs_mount = {
    .type = FS_LITTLEFS,
    .fs_data = &lfs_data,
    .mnt_point = "/lfs",
};

static int lfs_mount_init(void)
{
    struct flash_pages_info info;
    const struct device *dev;
    int rc;

    dev = PARTITION_DEVICE(LFS_PARTITION_NODE);
    if (!device_is_ready(dev)) {
        return -ENODEV;
    }

    rc = flash_get_page_info_by_offs(dev,
        PARTITION_OFFSET(LFS_PARTITION_NODE), &info);
    if (rc) {
        return rc;
    }

    lfs_mount.storage_dev = (void *)PARTITION_ID(LFS_PARTITION_NODE);

    /*  LittleFS 硬性要求：block_size 必须等于 Flash 的页大小（erase-block-size） */
    lfs_data.cfg.block_size = info.size;
    lfs_data.cfg.block_count =
        PARTITION_SIZE(LFS_PARTITION_NODE) / info.size;

    /* read_size 和 prog_size 建议等于 write-block-size */
    lfs_data.cfg.read_size = 16;   /* 一般 Nor Flash 最小读单位 */
    lfs_data.cfg.prog_size = 16;   /* 要和 DTS 中的 write-block-size 一致 */

    /* 可选：block_cycles 控制磨损均衡激进程度，-1 时由 LittleFS 内部决定 */
    lfs_data.cfg.block_cycles = -1;

    return fs_mount(&lfs_mount);
}
```

> **`block_size` 必须等于 Flash 的页大小**，这是 LittleFS CoW 机制的前提条件。如果填错，CoW 回收时无法正确擦除旧块，文件系统会逐渐"堵死"。
>
> `partition@0` 这样从地址 0 开始的分区，`flash_get_page_info_by_offs()` 可能拿到的是 Flash 整片的 page layout 而不是分区内部偏移对应的 page。通常没问题，因为同一个 Flash 的所有 page 大小一致。但如果遇到异常，直接填硬件 datasheet 里的 Erase Page Size 也可以。

挂载成功后，读写文件用标准 POSIX 风格 API：

```c
#include <zephyr/fs/fs.h>

struct fs_file_t file;
fs_file_t_init(&file);

/* 追加写日志 */
fs_open(&file, "/lfs/log.txt", FS_O_CREATE | FS_O_WRITE | FS_O_APPEND);
fs_write(&file, "hello\n", 6);
fs_close(&file);

/* 读取文件 */
char buf[128];
fs_open(&file, "/lfs/log.txt", FS_O_READ);
ssize_t n = fs_read(&file, buf, sizeof(buf));
fs_close(&file);
```

### 实战注意事项

**分区的 block 数不能太小**。LittleFS 的元数据（superblock + metadata pairs + root directory）至少占用 6 个 block。建议分区至少 **16 个 block** 才有实用价值。

**文件描述符和目录句柄数量有限**。`CONFIG_FS_LITTLEFS_NUM_FILES` 和 `CONFIG_FS_LITTLEFS_NUM_DIRS` 默认值通常为 4。如果你的应用需要同时打开多个文件，记得调大。每个打开的文件和目录都占用一个句柄。

**mount 时间随分区增大而变长**。LittleFS 挂载时需要遍历所有 metadata pair 重建文件系统状态。对于内部 NVM 上的小分区（几十到几百 KB），基本感觉不到；对于外部 Flash 上几十 MB 的大分区，每次启动 mount 可能达到秒级，需要注意对启动时间的影响。

**没有内置加密和访问控制**。LittleFS 本身不加密，存储在外部 SPI Flash 上的数据可以被直接读取。有安全需求的设备，敏感数据应该放内部 NVM（配合 TrustZone 隔离），或在上层自行加密后再写入 LittleFS。

**定期检查剩余空间**。LittleFS 不会提前告警"空间快满了"，只在写入失败时返回 `-ENOSPC`。建议在关键写入前用 `fs_statvfs()` 检查可用空间：

```c
struct fs_statvfs stat;
fs_statvfs("/lfs", &stat);
if (stat.f_bfree < 4) {
    /* 空间不足，触发清理或告警 */
}
```

**不要混用 LittleFS 操作和裸 Flash API**。LittleFS 假设自己对分区有独占控制权。如果应用代码绕过 LittleFS 直接用 Flash API 写同一个分区，会破坏 LittleFS 的元数据，导致文件系统损坏。同理，不要在多个镜像（如 bootloader 和 app）之间共享一个 LittleFS 分区。

# 6. Settings 系统

上一章介绍了 NVS、ZMS、LittleFS 三种存储后端。它们解决的是”数据怎么存到 NVM”的问题。但如果你去看 Zephyr 的蓝牙、Mesh 等子系统的源码，会发现它们几乎都不直接调用 NVS 或 ZMS 的 API。它们用的是 Settings。

## 为什么需要 Settings

想象这样一个场景：你的产品用到了 BLE 蓝牙、Wi-Fi 和 Thread Mesh，再加上你自己的一些应用配置（比如设备名称、上报间隔）。如果每个子系统都在 NVM 里自己管一块区域：

- 你得给每个子系统单独分一块 NVM 空间，但你又不好预估蓝牙绑定信息到底需要几个扇区、Wi-Fi 需要几个扇区——给少了不够用，给多了浪费；
- 每个子系统各自做磨损均衡，但它们的擦写频率不一样。BLE 绑定信息可能一年不改，而你的应用日志每 10 秒写一次，各自为政的磨损均衡其实效果很差；
- 固件升级后，如果某个子系统的存储格式变了，你要自己写迁移逻辑。

Settings 就是为解决这些问题设计的。它不是一个存储后端，而是一个**运行在 NVS/ZMS/LittleFS/FCB 之上的通用配置层**：

```text
┌────────────────────────────────────────────────┐
│                Application Code                │
├────────┬────────┬────────┬─────────────────────┤
│  BLE   │  Mesh  │  Wi-Fi │  Your App           │  ◀ 各模块通过字符串 Key 读写
├────────┴────────┴────────┴─────────────────────┤
│              Settings Subsystem                │  ◀ 统一的配置层
│   “bt/addr”  “mesh/iv”  “wifi/ssid”  “app/x”   │    路由 Key → Handler
├────────────────────────────────────────────────┤
│         NVS / ZMS / FCB / File backend         │  ◀ 底层存储后端（第五章）
└────────────────────────────────────────────────┘
```

核心思路很简单：

- 用**字符串 Key**（如 `bt/mesh/iv`、`app/reboot_count`）代替 NVS/ZMS 的整数 ID，人类可读，不容易冲突；
- 底层共享同一块存储分区，由 Settings 统一管理；
- 每个模块通过**Handler**注册自己关心的 Key，Settings 在启动时自动把 NVM 中的值恢复到各个模块的 RAM 中。

## 配置 Settings

使用 Settings 的第一步是选择一个存储后端。对于 nRF52/nRF53/nRF91 系列（NOR Flash），选 NVS：

```conf
CONFIG_FLASH=y
CONFIG_FLASH_MAP=y
CONFIG_NVS=y

CONFIG_SETTINGS=y
CONFIG_SETTINGS_NVS=y
```

对于 nRF54L 系列（RRAM），选 ZMS：

```conf
CONFIG_FLASH=y
CONFIG_FLASH_MAP=y
CONFIG_ZMS=y

CONFIG_SETTINGS=y
CONFIG_SETTINGS_ZMS=y
```

> NCS 还支持 FCB（Flash Circular Buffer，用于存储单个大 value）和 LittleFS 作为 Settings 后端。但这两个用得比较少，前者不够安全逐渐被淘汰，后者占用资源太多不适合内部NVM。大多数情况下 NVS 或 ZMS 就够了。

第二步是在设备树中指定 Settings 使用哪个分区。虽然 NVS/ZMS backend 默认会找 `label = “storage”` 的分区，但**不建议依赖这个默认行为**——label 只是一个给人看的字符串，不具备唯一性约束。应该用 `chosen` 明确指定：

```dts
/ {
    chosen {
        zephyr,settings-partition = &storage_partition;
    };
};
```

第三步是在启动时初始化 Settings：

```c
#include <zephyr/settings/settings.h>

int err = settings_subsys_init();
if (err) {
    printk(“Settings init failed: %d\n”, err);
    return err;
}
```

`settings_subsys_init()` 内部会初始化你所选的 backend（NVS/ZMS/FCB/File），并把它 mount 到 `zephyr,settings-partition` 指向的分区上。**你不需要像第五章那样手动 mount NVS 或 ZMS**——Settings 帮你做了这件事。

> 注意：`settings_subsys_init()` 只是初始化了 backend，**并没有从 NVM 加载数据到 RAM**。加载是后面 `settings_load()` 的事。

## 简单用法：`settings_save_one()` 和 `settings_load_one()`

如果你只是想让应用保存几个配置值——比如设备重启次数、上一次的传感器读数——最简单的方式是直接用 `settings_save_one()` 和 `settings_load_one()`。这两个 API 不要求你写 Handler，打开 Settings 就能用。

以记录设备重启次数为例：

```c
#include <zephyr/settings/settings.h>

static uint32_t reboot_count;

static void load_reboot_count(void)
{
    ssize_t len;

    len = settings_load_one(“app/reboot_count”,
                            &reboot_count, sizeof(reboot_count));
    if (len == sizeof(reboot_count)) {
        printk(“Previous reboot count: %u\n”, reboot_count);
        return;
    }

    /* 首次启动，NVM 中还没有这个 Key */
    reboot_count = 0;
}

static int save_reboot_count(void)
{
    return settings_save_one(“app/reboot_count”,
                             &reboot_count, sizeof(reboot_count));
}
```

完整的启动流程：

```c
int main(void)
{
    int err;

    /* 第一步：初始化 Settings（mount backend） */
    err = settings_subsys_init();
    if (err) {
        return err;
    }

    /* 第二步：从 NVM 加载配置到 RAM */
    load_reboot_count();

    /* 第三步：使用配置 */
    reboot_count++;
    printk(“This is boot #%u\n”, reboot_count);

    /* 第四步：保存回 NVM */
    (void)save_reboot_count();

    return 0;
}
```

> **`settings_load_one()` 的调用时机**：它可以在 `settings_subsys_init()` 之后、`settings_load()` 之前调用，不需要等到 `settings_load()` 完成。因为它只做一次独立的 backend 读取，不会干扰 Handler 的加载流程。

这种直截了当的写法适合以下场景：

- 应用层自己维护的少量 Key（不超过十几个）；
- Key 之间没有依赖关系，不需要”全部加载完再做一致性检查”；
- 不需要在加载时做格式迁移或校验（比如旧固件的 Key 值格式和新固件不同）。

两个容易踩坑的细节：

1. `settings_load_one()` 的返回值是实际读取的字节数，**不是错误码，0不代表成功**。如果 NVM 中不存在这个 Key，返回 `-ENOENT`；如果存的 value 长度和你传入的 `sizeof()` 不一致，返回 `-EINVAL`。所以上面用 `len == sizeof(reboot_count)` 来判断是否读取成功；
2. Key 的名字一旦在固件中写定，后续 OTA 升级时不能随意改名——`”app/reboot_count”` 变成了 `”app/boot_cnt”` 对 Settings 来说是两个不同的 Key，旧数据会丢失。

## Handler 机制：为子系统服务的设计

如果你翻看 Zephyr 官方的 Settings 示例，大概率会看到 `struct settings_handler` 和 `SETTINGS_STATIC_HANDLER_DEFINE()`。它写起来比上面的简单用法复杂不少。为什么会存在这套东西？

答案在 Zephyr 的蓝牙协议栈里。以 BLE 绑定信息为例：

- BLE Host 在运行时会维护一个绑定表，里面有多个配对过的设备信息；
- 每个绑定设备的 Key 都不同：`bt/keys/0/addr`、`bt/keys/0/irk`、`bt/keys/1/addr`、`bt/keys/1/irk`……数量是动态的；
- 只要 NVM 中任何一个 Key 被读到，BLE Host 就要往自己的绑定表里插入一条记录；
- 等所有 Key 都读完，BLE Host 才能说”绑定信息恢复完毕”，开始广播和连接。

用 `settings_load_one()` 很难满足这种需求——你不知道 NVM 里到底有几个绑定设备，也不知道什么时候算”加载完毕”。Handler 机制就是为这个场景设计的：

1. **`h_set()`**：Settings 遍历 NVM 时，每遇到一个属于本模块的 Key，就回调一次 `h_set()`，模块自己决定怎么把 value 恢复到 RAM；
2. **`h_commit()`**：当所有 Key 都遍历完毕，Settings 回调 `h_commit()`，模块在此处做”加载后一致性检查”或触发后续逻辑，告诉外面的Subsys：“你要的配置项全都加载完啦，可以从RAM中获取了”；
3. **`h_export()`**：当需要把当前 RAM 状态批量写回 NVM 时（比如 `settings_save()`），Settings 回调 `h_export()`，模块逐一把自己的 Key-Value 交给 backend。

> 这里是 Zephyr 的一个著名的反直觉的命名：
>
> - set，commit 指的是把配置项从 NVM 设置到 RAM 中，方便其他 Subsys使用。而不是设置到 NVM 中。这和数据库（SQL）的常见用法相反。
> - 而 export 反而是把数据从 RAM 导出到 NVM 进行持久化存储。

下面是一个完整的 Handler 示例。假设应用需要持久化一个”上报间隔”，并且希望启动时自动从 NVM 恢复：

```c
#include <string.h>
#include <zephyr/settings/settings.h>

static uint32_t report_interval_sec = 60;  /* 默认值 */

/* h_set：从 NVM 加载到 RAM */
static int app_settings_set(const char *key,
                            size_t len,
                            settings_read_cb read_cb,
                            void *cb_arg)
{
    ssize_t rc;

    /* settings_name_steq() 比较 key 的下一级，忽略 prefix */
    if (settings_name_steq(key, “report_interval”, NULL)) {
        if (len != sizeof(report_interval_sec)) {
            return -EINVAL;
        }

        rc = read_cb(cb_arg, &report_interval_sec,
                     sizeof(report_interval_sec));
        return rc == sizeof(report_interval_sec) ? 0 : -EINVAL;
    }

    /* 不是我能处理的 key，返回 -ENOENT 让 Settings 继续找别的 Handler */
    return -ENOENT;
}

/* h_export：从 RAM 批量导出到 NVM */
static int app_settings_export(int (*export_func)(const char *name,
                                                  const void *value,
                                                  size_t val_len))
{
    return export_func(“app/report_interval”,
                       &report_interval_sec,
                       sizeof(report_interval_sec));
}

/* 注册 Handler：subtree 名为 “app”，响应所有 “app/*” 的 Key */
SETTINGS_STATIC_HANDLER_DEFINE(app_settings,
                               “app”,           /* subtree 名称 */
                               NULL,            /* h_get（几乎不用） */
                               app_settings_set,/* h_set */
                               NULL,            /* h_commit（这个例子不需要） */
                               app_settings_export);
```

启动时只需两行：

```c
int main(void)
{
    settings_subsys_init();

    /* settings_load() 会遍历 NVM 中所有 Key，
     * 对 “app/*” 的 Key 回调 app_settings_set() */
    settings_load();

    printk(“Report interval: %u seconds\n”, report_interval_sec);
    return 0;
}
```

运行时修改值后，仍然可以用 `settings_save_one()` 单独保存，**不需要**走 `h_export()`：

```c
report_interval_sec = 30;

settings_save_one(“app/report_interval”,
                  &report_interval_sec,
                  sizeof(report_interval_sec));
```

> **`h_export()` 和 `settings_save_one()` 的区别**：
>
> - `settings_save_one()` 是”我现在就要把这个 Key 写到 NVM”，调用即写入；
> - `h_export()` 是”Settings 要做一次全量导出（`settings_save()`），请你告诉我你模块当前有哪些 Key-Value”，具体什么时候写、按什么顺序写，由 Settings 控制。
>
> 绝大多数应用代码只需要 `settings_save_one()`，不会用到 `h_export()`。`h_export()` 主要服务于那些需要”把整个 RAM 状态完整序列化到 NVM”的子系统，比如蓝牙 Host。

## Settings 实际建议

经过上面的分析，对于应用层代码，我的建议是按复杂度递进选择：

1. **几个简单的配置值**：直接用 `settings_save_one()` + `settings_load_one()`。不要写 Handler，不要写 `settings_load()`。这是最简单、代码最少的方案；
2. **启动时需要统一恢复一批配置，且 Key 之间存在依赖关系**：写 `h_set()`，在 `main()` 中调用 `settings_load()` 一次性恢复。比如你要同时恢复 Wi-Fi SSID 和密码，两个都加载完才触发联网逻辑；
3. **需要 `settings_save()` 批量导出整个模块状态**：再补 `h_export()`。这个需求在应用层非常少见，如果你的代码里只在 Zephyr 子系统的源码中见过 `h_export()`，那很正常——你可能根本不需要写它；
4. **不要为了”看起来标准”给每个 Key 都写一套 Handler**。`struct settings_handler` 里面有 5 个回调函数，但多数场景你只需要填一两个。`NULL` 就是合法的”我不需要这个回调”。

Settings 这套 API 之所以看起来复杂，是因为它最初的设计目标是服务 Zephyr 的蓝牙、Mesh 等子系统——这些子系统有几十上百个 Key、需要运行时动态增删、需要批量导入导出。对于普通应用开发来说，**从简单 API 用起，按需升级到 Handler，是最务实的路径**。

# 7. 最终选择指南

到这里，本文已经把从硬件驱动到 Settings 配置层的完整链路介绍完毕。最后总结一下，在实际项目中怎样为数据选择合适的存储方案：

| 需求                                                         | 推荐方案           | 原因                                                         |
| ------------------------------------------------------------ | ------------------ | ------------------------------------------------------------ |
| 几十个小配置项（计数器、状态位）                             | Settings + NVS/ZMS | KV 模型开销小，Settings 统一管理。Bluetooth/Wi-Fi 等子系统已经在用 Settings，可以与 这些子系统共享配置分区 |
| TLS 证书、图片、Web 页面等文件型资源                         | **LittleFS**       | 本身就是文件，用文件系统管理最自然                           |
| 日志持续追加写入、需要导出查看                               | **LittleFS**       | 文件可以方便地读出来，或通过 `fs_statvfs()` 检查             |
| 数据需要目录层级和文件名                                     | **LittleFS**       | KV 模型不支持目录结构（但 Settings 的字符串 Key 可以模拟“目录层级”） |
| 只存几个整数，不想引入文件系统开销；且不想和  Zephyr 其他子系统共用分区 | NVS / ZMS（裸用）  | 比 Settings 更轻量，少一层抽象，需另外单开一个分区           |

实际产品中，最典型的组合是：

- **内部 NVM**：开一个 NVS（nRF52/53/91）或 ZMS（nRF54L）分区，挂载给 Settings，存蓝牙绑定、设备配置等小体量数据；
- **外部 NOR Flash**：开一个 LittleFS 分区，存 CA证书、日志、Web 页面等大体量文件（但设备私钥等机密信息不要未经加密就放到 LittleFS）。

两者互不干扰，也不共享分区。

> LittleFS 也可以作为 Settings 的 backend——`CONFIG_SETTINGS_FILE=y`。如果你的应用已经为了存文件而 mount 了 LittleFS，且只需少量配置项，让 Settings 把配置也存到 LittleFS 分区里，就可以省去一块 NVS/ZMS 分区。

# 8. 示例代码

[Jayant-Tang/learning_zephyr_storage](https://github.com/Jayant-Tang/learning_zephyr_storage)
