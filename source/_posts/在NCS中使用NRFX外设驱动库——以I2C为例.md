---
title: 在NCS中使用NRFX外设驱动库——以I2C为例
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2023-11-15 20:20:05
cover: null
tags:
- Nordic
- Zephyr
- NRFX
- I2C
categories: Zephyr
cnblogs:
  postId: '17835258'
  url: https://www.cnblogs.com/jayant97/articles/17835258.html
  lastPublishedAt: '2026-07-06T18:20:52+08:00'
  sourceHash: sha256:978472d6a03fc685ee5f88f417820d37c561f3c4b164b5d6f5e306ec2223ed17
  status: imported
  postType: Article
---

# 1. 前言

之前编写了两篇与Zephyr设备树和驱动相关的文章：

- [详解Zephyr设备树与驱动模型](https://jayant-tang.github.io/2023/03/4b274a50e575/)
- [Zephyr设备树与驱动实战——串口](https://jayant-tang.github.io/2023/11/4c8e1d7d162d/)

如果你看完这两篇文章，相信你对Zephyr的驱动模型已经有一定概念了。开发者能够直接使用厂商写好的高效、完善的驱动程序，无需再埋头于寄存器手册、波形时序、引脚配置等底层程序，只需专注于自己的应用即可。

但是，做嵌入式开发，总还有各种各样的原因，让人不得不陷入底层软件调试之中，包括但不限于：

- 厂商提供的外设驱动都只有标准的，但我的应用场景是非标准的
- 我需要多个外设在底层进行深入的联动，厂商提供的驱动无法满足我的需求
- 我不想学Device Tree和驱动模型，我就喜欢老的nRF5 SDK那种开发方法
- ......

话先说在前面，Nordic的nRF5 SDK从17.10开始就不再更新了。从nRF53系列（也就是nRF5340）、nRF91蜂窝网络、nRF70 Wi-Fi系列以及马上要出的强力的nRF54系列产品，都只能使用NCS了。并且，今后单片机的嵌入式软件开发会越来越复杂：TCP/IP、蓝牙、USB、Matter、OTA、文件系统、显示屏……各种复杂的应用和协议栈，如果都从底层寄存器开始做起，那真是不知道要浪费多少时间，关键是还不一定能做成功。Zephyr是一个RTOS，除了基本的多线程、线程间通讯之外，还有功耗管理、线程监控、自定义shell命令、非易失存储、DSP、加密、代码与变量位置重定向、C++支持等等功能。并且，Zephyr是Linux基金会维护的开源项目，底层也是POSIX接口，编译与配置系统是CMake和Kconfig，这意味着Zephyr可以很容易的集成许多第三方开源项目进来。

不过Zephyr再好，厂商肯定是不会把底层调试的路完全封死的。本文将会以nRF52840DK为例，介绍在NCS中，如何使用NRFX库来使用I2C从机。这个NRFX库和之前nRF5 SDK中的nrfx几乎是一致的。

# 2. 硬件连接

![image-20231115221340971](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined63eb4a6736a0968bdbfb9f18f2b23e1b.png)

I2C主机：SDA(P0.26) SCL(P0.27)

I2C从机：SDA(P0.30) SCL(P0.31)

# 3. 例程代码

## 工程结构

本文以`${NCS}/zephyr/samples/hello_world`为基础。主要文件如下：

```
|-- boards
|    |
|    `-- nrf52840dk_nrf52840.overlay
|
|-- src
|    |
|    |-- main.c
|    |-- i2c_slave.c
|    `-- message.h
|
|-- CMakeLists.txt
`-- prj.conf
```

## CMakeLists.txt

```cmake
# SPDX-License-Identifier: Apache-2.0

cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(hello_world)

target_sources(app PRIVATE 
    src/main.c
    src/i2c_slave.c
    )

target_include_directories(app PRIVATE 
    src)
```

## prj.conf

```shell
# the I2C master using Zephyr driver
CONFIG_I2C=y

# the I2C slave using NRFX driver
# see: https://github.com/zephyrproject-rtos/zephyr/issues/21445
CONFIG_NRFX_TWIS1=y
```

说明：

- 本例主机采用Zephyr标准I2C驱动，故需要使能
- Zephyr没有标准I2C从机驱动，故此处使用NRFX库

> 由于版权原因，Nordic的I2C外设叫做TWI（Two-Wire Interface）

## 设备树overlay

`boards/nrf52840dk_nrf52840.overlay`

```c
&i2c0 {
    compatible = "nordic,nrf-twim";
    status = "okay";
    clock-frequency = <I2C_BITRATE_STANDARD>;
    pinctrl-0 = <&i2c0_default>;
    pinctrl-1 = <&i2c0_sleep>;
    pinctrl-names = "default", "sleep";
};

// this node is here just to meet the requirements of the `CONFIG_NRFX_TWIS1=y`.
// The Zephyr I2C slave driver is not available now.
// So we use NRFX driver instead.
&i2c1 {
    compatible = "nordic,nrf-twis";
    status = "okay";
};

&pinctrl {
	i2c0_default: i2c0_default {
		group1 {
			psels = <NRF_PSEL(TWIM_SDA, 0, 26)>,
                <NRF_PSEL(TWIM_SCL, 0, 27)>;
            nordic,drive-mode = <NRF_DRIVE_S0D1>; // standard 0, disconnect 1
            bias-pull-up; // internal pull-up is too weak, only for 100kHz or lower  
            
		};
	};

	i2c0_sleep: i2c0_sleep {
		group1 {
			psels = <NRF_PSEL(TWIM_SDA, 0, 26)>,
                <NRF_PSEL(TWIM_SCL, 0, 27)>;
			low-power-enable;
		};
	};

    // i2c1 not used for Zephyr driver, it is initialized by nrfx driver.
    // just for Devicetree GUI display
    i2c1_default: i2c1_default {
        group1 {
            psels = <NRF_PSEL(TWIM_SDA, 0, 30)>,
				<NRF_PSEL(TWIM_SCL, 0, 31)>;
                bias-pull-up; 
        };
    };

    i2c1_sleep: i2c1_sleep {
        group1 {
            psels = <NRF_PSEL(TWIM_SDA, 0, 30)>,
				<NRF_PSEL(TWIM_SCL, 0, 31)>;
            low-power-enable;
        };
    };
};
```

**主机device tree说明：**

- `i2c0`为主机，采用pinctrl来配置引脚。
- 由于I2C协议要求开漏输出，因此我们这里的i2c0引脚配置为`NRF_DRIVE_S0D1`，其含义是“输出逻辑0时为标准GND输出，输出逻辑1时内部断开（高阻态）”。
- 由于I2C协议要求上拉电阻，而我们是杜邦线跳线没有上拉电阻，因此这里采用内部上拉。
- `compatible`一定要选择`"nordic,nrf-twim"`而不是`"nordic,nrf-twi"`，前者是带DMA的驱动程序，后者是不带DMA的驱动程序。

> 补充：
>
> - 除了S（Standard）和D（Disconnect）之外，还有H（High-drive）。一些高速接口需要IO有更强的驱动能力，这种情况下可以配置为`NRF_DRIVE_H0H1`。不过具体还是要看芯片手册里面每个GPIO是否支持高驱（位于手册里的Pin assignment章节）：
>
>   ![image-20231116001024624](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined7f0c410444e9555ee98c3a97faa21026.png)
>
> - GPIO内部上/下拉电阻比较大，典型值为13千欧。因此如果用内部上拉，速率只能配置为100Kbps。若要更高的速率，外部可以挂更小的电阻，例如5千欧左右可以达到400Kbps.

**从机device tree说明：**

`i2c1`为从机。从机的代码是用NRFX的，完全没有用到device tree。这里修改i2c1的device tree，完全是Kconfig的要求：

```
config NRFX_TWIS1
	bool "TWIS1 driver instance"
	depends on $(dt_nodelabel_has_compat,i2c1,$(DT_COMPAT_NORDIC_NRF_TWIS))
	select NRFX_TWIS
```

我们可以看到，`CONFIG_TWIS1`的依赖项，要求device tree中的`i2c1`节点，必须具有`compatible="nordic,nrf-twis"`。只有满足这个条件，我们才能写`CONFIG_TWIS1=y`。并且，此配置项会自动连锁使能`CONFIG_NRFX_TWIS=y`。

我们要明确一点，NRFX是不需要device tree的。这里Kconfig的依赖项，我想只是为了能在项目中**明显地指示出**，我们使用了`i2c1`这个外设。以免在多人开发项目中产生一些误会，导致外设被重复使用。

同理，从机的pinctrl也是没有实际作用的。写它只是为了能够在Device Tree的GUI中正确显示引脚分配：

![image-20231116002542051](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined750262bf3b95b47e39488136c6d7c9e5.png)

## message.h

```c
#ifndef _MESSAGE_H_

#define MASTER_TO_SLAVE "Master to Slave"
#define SLAVE_TO_MASTER "Slave to Master"

#endif
```

这里面只是主从机共用的测试用数据而已

## 主机代码

main.c

```c
/*
 * Copyright (c) 2012-2014 Wind River Systems, Inc.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/i2c.h>

#include "message.h"

static const struct device *twi_dev = DEVICE_DT_GET(DT_NODELABEL(i2c0));

#define I2C_ADDR 0xbeef // only the lowest 7bit is useful


int main(void)
{
    char send_data[] = MASTER_TO_SLAVE;
    char read_data[128];

    if (!device_is_ready(twi_dev)){
        printk("twi device is not ready!\n");
        return 0;
    }

    while (1) {
        k_sleep(K_MSEC(3000));
        printk("\n[Master] write: \"%.*s\"\n", sizeof(send_data), send_data);
        i2c_write(twi_dev, send_data, sizeof(send_data), I2C_ADDR);

        k_sleep(K_MSEC(2000));
        printk("\n[Master] read\n");
        i2c_read(twi_dev, read_data, sizeof(SLAVE_TO_MASTER), I2C_ADDR);
        printk("[Master] received:\"%.*s\"\n", sizeof(SLAVE_TO_MASTER), read_data);

        k_sleep(K_MSEC(1000));
    }
    
	return 0;
}
```

**主机程序说明：**

- 主机会循环向i2c写入数据、然后读取数据。

- 先sleep，后发数据，是为了开始时要先等从机那边初始化好。

- Zephyr标准API中，I2C从机地址这个参数是16bit的。但对于Nordic的芯片来说，**只有最低7bit是真实的地址**。硬件上也只支持7bit地址。

- 所有这些I2C读写API都是**阻塞**的。但是，底层是DMA，怎么会阻塞呢？原来，这里的阻塞只是“线程阻塞”而不是“CPU阻塞”。当I2C开始传输后，I2C的驱动实际上是在尝试take一个信号量，这时，**当前线程会被阻塞，但其他线程可以正常执行**。当DMA传输完成后，产生中断，中断内部give这个信号量，于是读/写函数就可以返回了。

  > 这也告诉我们，在RTOS中，应该尽量把不同的模块分成不同的线程去开发。这样既使得程序结构清晰，又不会有任务之间互相阻塞的问题。

## 从机代码

i2c_slave.c

```c
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <nrfx_twis.h>
#include <zephyr/kernel.h>

#include "message.h"

#define STACKSIZE 1024
#define PRIORITY 7

#define SLAVE_ADDR 0xef
#define TWI_INT_PRIORITY 2

#define SLAVE_SDA_PIN 30 // P0.30
#define SLAVE_SCL_PIN 31 // P0.31

#define TWIS_INST_IDX 1 // twis1
static nrfx_twis_t twis_inst = NRFX_TWIS_INSTANCE(TWIS_INST_IDX);

#define MSG_TO_SEND "Slave-to-Master"

static uint8_t m_tx_buffer_slave[sizeof(MSG_TO_SEND)] = MSG_TO_SEND;
static uint8_t m_rx_buffer_slave[128];

/**
 * @brief Function for handling TWIS driver events.
 *
 * @param[in] p_event Event information structure.
 */
static void twis_handler(nrfx_twis_evt_t const * p_event)
{
    nrfx_err_t status;
    (void)status;

    switch (p_event->type)
    {
        case NRFX_TWIS_EVT_WRITE_DONE:{
            uint32_t len = p_event->data.rx_amount;
            printk("--> Slave event: received write done.\n");
            printk("[Slave] received:\"%.*s\"\n", len, m_rx_buffer_slave);
            break;
        }

        case NRFX_TWIS_EVT_WRITE_REQ:{
            status = nrfx_twis_rx_prepare(&twis_inst, m_rx_buffer_slave, sizeof(m_rx_buffer_slave));
            NRFX_ASSERT(status == NRFX_SUCCESS);
            printk("--> Slave event: received write request\n");
            break;
        }

        case NRFX_TWIS_EVT_READ_DONE:{
            printk("--> Slave event: received read done.\n");
            break;
        }

        case NRFX_TWIS_EVT_READ_REQ: {
            status = nrfx_twis_tx_prepare(&twis_inst, m_tx_buffer_slave, sizeof(m_tx_buffer_slave));
            NRFX_ASSERT(status == NRFX_SUCCESS);
            printk("--> Slave event: received read request\n");
            break;
        }

        case NRFX_TWIS_EVT_READ_ERROR:
            printk("\nTWIS READ ERROR\n");
            break;

        case NRFX_TWIS_EVT_WRITE_ERROR:
            printk("\nTWIS WRITE ERROR\n");
            break;

        case NRFX_TWIS_EVT_GENERAL_ERROR:
            printk("\nTWIS GENERAL ERROR\n");
            break;

        default:
            printk("--> SLAVE event: %d.", p_event->type);
    }
}

int i2c_slave_entry()
{
    nrfx_err_t status;
    (void)status;

    printk("Starting nrfx_twim_twis non-blocking example.");


    // connect handler to Zephyr interrupt
    IRQ_CONNECT(DT_IRQN(DT_NODELABEL(i2c1)),
	    DT_IRQ(DT_NODELABEL(i2c1), priority),
	    nrfx_isr, twis_handler, 0);

    nrfx_twis_config_t twis_config = {
        .addr[0]            = SLAVE_ADDR, // first address
        .addr[1]            = 0,          // second address
        .scl                = SLAVE_SCL_PIN,                              
        .sda                = SLAVE_SDA_PIN,                              
        .scl_pull           = NRF_GPIO_PIN_PULLUP,                   
        .sda_pull           = NRF_GPIO_PIN_PULLUP,                   
        .interrupt_priority = TWI_INT_PRIORITY,
        .skip_gpio_cfg = false,
        .skip_psel_cfg = false,
    };

    printk("\nI2C Slave: ADDR: 0x%x, SCL: %d, SDA: %d, int_pri: %d",
      twis_config.addr[0],
      twis_config.scl,
      twis_config.sda,
      twis_config.interrupt_priority);

    if(nrfx_twis_init(&twis_inst, &twis_config, twis_handler) == NRFX_SUCCESS){
        printk("\nnrfx twis initialized.\n\n");
    } else {
        printk("\nERROR: nrfx_twis_init()\n");
    }

    IRQ_DIRECT_CONNECT(NRFX_IRQ_NUMBER_GET(NRF_TWIS_INST_GET(TWIS_INST_IDX)), IRQ_PRIO_LOWEST,
                       NRFX_TWIS_INST_HANDLER_GET(TWIS_INST_IDX), 0);

    nrfx_twis_enable(&twis_inst);

    while(1){
        k_sleep(K_FOREVER);
    }
}

K_THREAD_DEFINE(i2c_slave_id, STACKSIZE, i2c_slave_entry, NULL, NULL, NULL, PRIORITY, 0, 0);
```

**从机程序说明：**

从机用nrfx库初始化、注册中断服务函数、并使能TWIS。这部分代码，和nrf5 SDK中nrfx库的用法是一样的。

与nRF5 SDK中略有不同的是，中断服务函数需要用Zephyr的机制去连接一下。这是因为Zephyr默认把所有中断向量全占了，用于整个驱动模型。这部分请参考[Zephyr内核文档——中断](https://docs.zephyrproject.org/latest/kernel/services/interrupts.html#interrupts)。今后我也会写一篇博客来介绍Zephyr的中断。

从机的程序也是一个线程，用`K_THREAD_DEFINE`来定义线程。线程中初始化完TWIS后，就进入了永久睡眠。

对于I2C WRITE操作，在主机发送完7bit地址，之后的那一个比特为0（写）时，这一瞬间立即产生`NRFX_TWIS_EVT_WRITE_REQ`事件，这时要准备好接收数据的缓存。写完后，产生`NRFX_TWIS_EVT_WRITE_DONE`事件。

![image-20231116004555046](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined3d8c8f49c007973906d82a6ad196428c.png)

对于I2C READ操作也是同理。`NRFX_TWIS_EVT_READ_REQ`时，准备好即将要发送的缓存。`NRFX_TWIS_EVT_READ_DONE`说明发送完毕。


![image-20231116004445733](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedbcc04a1311bc8f70a15476eaa8f3ea74.png)

> 注意，不一定要在`NRFX_TWIS_EVT_READ_REQ`时，才开始准备要发送的数据。可以提前调用`nrfx_twis_tx_prepare()`来准备要发送的数据。接收也是同理。

## 程序运行结果

![image-20231116013311689](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb96701e27dea67028e500a379148c302.png)

# 4. 应用开发

## 其他NRFX例程

位于`${NCS}/modules/hal/nordic/nrfx/samples/src`

## 与其他Zephyr标准驱动的共存

通过前面的讲解，相信多数人都能理解，NRFX的驱动程序和Zephyr的标准驱动是可以共存的，只要用到的**外设资源**不冲突、**GPIO不冲突**即可。

这里还有另外两个要注意的点：

### 外设地址冲突

Nordic的串行外设（串口、SPI、SPIM、SPIS、TWI、TWIM、TWIS），并不是都能同时使用的。有些外设其实是同样的外设地址，内部共用了一部分串行和DMA电路。这样就造成了有很多外设可用的假象。实际上只是同一个芯片内部电路的不同使用方法。

我们可以在芯片手册 Memory 章节的 Instantiation 小节看到所有外设实例的地址：

![image-20231116011218081](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedba1ed65b8b5dbacc4032df0de7ea7eae.png)

可以看到，对于52840来说，串口0是独立的，SPI0和TWI0是二选一，SPI1和TWI1是二选一。

不仅是NRFX，对于Zephyr标准驱动来说，也是一样的。我们可以从DeviceTree中看到，冲突的外设，它们的地址是相等的。

此外，从右边我们可以看到，不带DMA的外设目前基本是不用的。

### 资源型外设的自动分配

在Nordic的单片机中，有很多“资源型”外设。我把它叫做资源型，是因为这些外设之间没有任何区别，用谁都一样，比如：

- **GPIOTE**：GPIOTE有8个独立的通道，每个通道可以连一个GPIO，使其获得TASK和EVENT寄存器，用来产生中断、连接PPI通道等。
- **PPI**：可以连接一个外设的EVENT寄存器，和两个其他外设的TASK寄存器，使得EVENT自动触发TASK。nRF52840有20个自由的PPI通道（还有12个固定的）。

理论上讲，当你用这些个通道时，随便用哪个都没区别。但是，**你怎么知道目前Zephyr系统内的什么驱动已经用掉了哪个通道呢？**如何防止自己选的通道和Zephyr内目前已经用的通道冲突？

答案就是，别自己选。这些外设之所以叫资源型，就是因为它和内存等资源一样，可以集中管理，动态的分配和释放。**而Nordic提供的所有Zephyr驱动，凡是用到了这些外设的，都是使用其对应的allocate函数，而不是直接指定一个具体的资源**。

例如，对于GPIOTE通道，可以用：

```c
nrfx_err_t nrfx_gpiote_channel_alloc(uint8_t * p_channel);
```

对于PPI通道，可以用：

```c
nrfx_err_t nrfx_gppi_channel_alloc(uint8_t * p_channel)
```

> Nordic不同芯片，有的是PPI，有的是分布式PPI（DPPI）。NCS中统一用gppi，这是一个wrapper，会自动根据芯片平台选择调用PPI或DPPI的API。

