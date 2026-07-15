---
title: NCS 低功耗日志打印
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2025-01-26 23:10:26
cover: null
tags:
- Nordic
- Zephyr
- Logging
categories: Zephyr
cnblogs:
  postId: '18692364'
  url: https://www.cnblogs.com/jayant97/articles/18692364
  lastPublishedAt: '2026-07-15T11:28:49+08:00'
  sourceHash: sha256:45ea0ba0caaf426316e91faee79e3d754a40a0667896951dace843ee0f505940
  status: synced
  postType: Article
---

本文第一节直接给出配置，第二节介绍原理，第三节介绍踩到的一个坑

# 低功耗日志打印配置

> 【注意】本文介绍的方法，仅支持NCS`v2.8.0`之后的版本。

## 软件配置

以下代码与config直接在`zephyr/samples/hello_world`中进行配置即可。

配置文件：`prj.conf`

```bash
# 开启LOG功能，并选择后端为串口
CONFIG_LOG=y
CONFIG_LOG_MODE_DEFERRED=y
CONFIG_LOG_BACKEND_UART=y

# 日志对应串口开启异步输出（DMA）功能
CONFIG_LOG_BACKEND_UART_ASYNC=y
CONFIG_UART_ASYNC_API=y
CONFIG_UART_0_INTERRUPT_DRIVEN=n
CONFIG_UART_0_ASYNC=y

# 以下为异步串口硬件计数功能
# 只影响RX，不影响TX，因此日志串口无需打开
# CONFIG_UART_0_NRF_HW_ASYNC=y
# CONFIG_UART_0_NRF_HW_ASYNC_TIMER=1
# CONFIG_NRFX_TIMER1=y

# 开启Console功能，并选择后端为串口
CONFIG_PRINTK=y
CONFIG_UART_CONSOLE=y

# 关闭一切与输入有关的feature
CONFIG_SHELL=n
CONFIG_CONSOLE_HANDLER=n

# printk不重定向到LOG buffer
CONFIG_LOG_PRINTK=n

# 以下两个选项需要同时打开或同时关闭
# 不要只打开CONFIG_PM_DEVICE=y
CONFIG_PM_DEVICE_RUNTIME=y
CONFIG_PM_DEVICE=y

# 关闭RTT通道
CONFIG_USE_SEGGER_RTT=n
CONFIG_RTT_CONSOLE=n
```

设备树overlay文件（没有可自己新建`app.overlay`）：

```
&uart0 {
    status = "okay";
    zephyr,pm-device-runtime-auto; // 如果前面开了CONFIG_PM_DEVICE_RUNTIME=y，这里一定要使能
    /delete-property/ hw-flow-control;
};

// 原本uart0的Pinctrl是有流控CTS和RTS引脚的，
// 这里直接覆盖去掉那两个引脚
&uart0_default {
    group1 {
        psels = <NRF_PSEL(UART_TX, 0, 6)>;
    };
    group2 {
        psels = <NRF_PSEL(UART_RX, 0, 8)>;
        bias-pull-up;
    };
};

&uart0_sleep {
    group1 {
        psels = <NRF_PSEL(UART_TX, 0, 6)>,
            <NRF_PSEL(UART_RX, 0, 8)>;
        low-power-enable;
        bias-pull-up; // 这里控制休眠期间引脚是上拉还是下拉。上拉可节省100nA。
    };
};
```

代码`main.c`：

```c
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(main);

int main(void)
{
    while(1) {   
        // 通过stdout输出，最终是通过串口阻塞API，一个字符一个字符输出
        printf("Hello World! %s\n", CONFIG_BOARD_TARGET);
        
        // CONFIG_LOG_PRINTK=n 时，通过串口阻塞API，一个字符一个字符输出
        // CONFIG_LOG_PRINTK=y 时，通过logging subsystem的buffer输出
        printk("Hello World! %s\n", CONFIG_BOARD_TARGET);
        
        // CONFIG_LOG_BACKEND_UART=y 时，通过异步串口API输出（DMA）
        LOG_INF("Hello World! %s", CONFIG_BOARD_TARGET);
        
        k_sleep(K_MSEC(1000));

    }
	return 0;
}
```

## 硬件配置

以nRF52840DK为例：

![image-20250126235219464](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250126235219464.webp)

首先切开焊盘SB40，这个是MCU供电流过的地方。

1. 如果用电流表测试，则接**电流流出**和**电流流入**
2. 如果用电源测试，则接**电流流入**和**GND**
3. 如果使用PPK II，支持以上两种模式，可以3个引脚都接
4. 如果使用示波器，可以在焊盘R90上焊接一个10欧姆高精度电阻，然后用示波器双通道2个探头分别接入**电流流入**和**电流流出**，再接地。示波器双通道相减获得电流。

> PPK II推荐使用**电流表模式**。如果要使用**电源模式，一定要确保供电电压和板子本身供电电压相同**。否则MCU引脚和板子上其他器件会有压差，导致漏电。
>
> 这里使用nRF52840DK，如果用电压源模式需要选择3V供电。

![image-20250126235758123](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250126235758123.webp)

此外，即使你使用电源模式，USB也是必须要接的：

![969d3d8a3a037e411d2636670789c9f1](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/969d3d8a3a037e411d2636670789c9f1.webp)

否则电源供电会通过一些开关芯片漏到板子上的其他器件上，造成功耗评估严重偏高。

## 运行结果

板子上JLINK （Interface MCU）自带串口，直接电脑打开JLINK上的串口即可：

![image-20250127003520771](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250127003520771.webp)

日志：

```
*** Booting nRF Connect SDK v2.8.0-a2386bfc8401 ***
*** Using Zephyr OS v3.7.99-0bc3393fb112 ***
Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
[00:00:00.354,217] <inf> main: Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
[00:00:01.360,687] <inf> main: Hello World! nrf52840dk/nrf52840
[00:00:02.367,248] <inf> main: Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
[00:00:03.373,809] <inf> main: Hello World! nrf52840dk/nrf52840
[00:00:04.380,371] <inf> main: Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
[00:00:05.386,932] <inf> main: Hello World! nrf52840dk/nrf52840
[00:00:06.393,463] <inf> main: Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
[00:00:07.400,054] <inf> main: Hello World! nrf52840dk/nrf52840
[00:00:08.406,585] <inf> main: Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
Hello World! nrf52840dk/nrf52840
```

`printk`和`printf`以及`LOG`都连续输出2次。这说明这三种方式内部各自存在buffer，buffer满了才会输出。

底电流：

![image-20250127000857325](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250127000857325.webp)

IDLE线程的底电流2.54uA，符合手册中System ON条件下，CPU不工作时的功耗：

![75adeaab93a5d89a9b48ffa11ff3137f](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/75adeaab93a5d89a9b48ffa11ff3137f.webp)

> 相对的，System OFF的功耗非常低，但是只能用reset或GPIO唤醒，且唤醒后必定reset。

# 配置解析

## 异步串口

根据我之前的文章[《Zephyr驱动与设备树实战——串口》](https://jayant-tang.github.io/2023/11/4c8e1d7d162d/)，我们知道异步串口只要不是正在发送或接收，就是低功耗的。RX时的功耗比较高，因为需要一直等待。但好在日志是一个不需要RX的功能，因此我们关闭所有RX：

```
CONFIG_SHELL=n
CONFIG_CONSOLE_HANDLER=n
```

其他关于异步串口的配置，可以看那篇文章解释。

## Zephyr Device Power Management

接下来是关于低功耗的：

```
CONFIG_PM_DEVICE_RUNTIME=y
CONFIG_PM_DEVICE=y
```

这是Zephyr Device Power Management Subsystem的功能。Zephyr中把电源管理分为System Power Management 和 Device Power Management。System Power Management的强大功能我们已经见识过了：只要其他线程都在阻塞（不论是在sleep还是在等待信号量），进入IDLE线程后，系统会自动让CPU休眠。当有EVENT到来时，CPU自动唤醒，无需开发者操心CPU的休眠。

而**Device Power Management**管理的是外设的功耗，包括片上外设和外挂的总线外设。如果你开发了一段时间Zephyr，会发现Zephyr的外设API是没有init和uninit的。因为外设的初始化是在main线程运行之前就已经被驱动程序做好了。

`CONFIG_PM_DEVICE=y`就让你可以在应用层手动去开关这些外设，具体的API为：

```c
#include <zephyr/pm/device.h>

const struct device *uart0 = DEVICE_DT_GET(DT_NODELABEL(uart0));

void button_0_enter_low_power()
{
	...
	pm_device_action_run(uart0, PM_DEVICE_ACTION_SUSPEND);
	...
}

void button_1_exit_low_power()
{
	...
	pm_device_action_run(uart0, PM_DEVICE_ACTION_RESUME);
	...
}
```

驱动层已经实现了`PM_DEVICE_ACTION_SUSPEND`和`PM_DEVICE_ACTION_RESUME`对应的功能，开发者无需再关心其初始化的细节。

通过这种方式你可以手动地全局开关一些外设。

但是有时候手动去开关还是太麻烦，可能你会想这样做来实现低功耗：

```c
...
pm_device_action_run(&my_dev, PM_DEVICE_ACTION_SUSPEND);
operate_my_dev(&my_dev);
pm_device_action_run(&my_dev, PM_DEVICE_ACTION_RESUME);
...
```

但是这么做不是线程安全的，如果这段代码在不同线程里运行会出问题（常见于SPI，I2C等总线外设）。另外可能这个外设被Zephyr系统用到了，但是却在那之前被你关掉了，那就会出问题（尤其常见于QSPI外挂Flash）。

 `CONFIG_PM_DEVICE_RUNTIME=y`就是Zephyr提供的另外一个库，它相当于对Device Management的API进行了一层封装：

![img](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedf34742ba56bf7c4ffbe45cb73f4a1d39.png)

当应用层调用外设的API时，驱动层先调用`pm_device_runtime_get()`函数，使得`usage`变量+1。当usage变量大于等于1时，PM Subsystem就会调用`pm_device_action_run(dev, PM_DEVICE_ACTION_RESUME)`来让驱动层打开这个外设。

当这个外设不再使用时（发送完毕/接收完毕），驱动层则调用`pm_device_runtime_put()`函数，使得`usage`变量-1。当`usage == 0`时，PM Subsystem就会调用`pm_device_action_run(dev, PM_DEVICE_ACTION_SUSPEND)`来让驱动层关闭这个外设。

这种实现是线程安全的，并且不需要应用层手动控制这个外设。此外，即使应用层重复地进行`get`或者`put`，也不会影响它实际的运行逻辑。

> NCS v2.8.0 之后，Nordic 串口驱动才加入了Runtime的支持。

Runtime电源管理的功能，要看驱动程序是否支持，主要是看它有没有调用`pm_device_runtime_put`和`pm_device_runtime_get`。

另外，Runtime的功能一定要对每个外设分别使能。你可以在设备树里添加一个配置，让它自动使能：

```
&uart0 {
    zephyr,pm-device-runtime-auto;
};
```

> 此外，Nordic串口驱动做了更多事情。**如果`CONFIG_PM_DEVICE`和`CONFIG_PM_DEVICE_RUNTIME`都不打开**，此串口驱动也实现了自己的私有runtime低功耗：
>
> ```
> # 见/zephyr/drivers/serial/Kconfig.nrfx_uart_instance
> 
> config UART_$(nrfx_uart_num)_NRF_ASYNC_LOW_POWER
> 	bool "Low power mode"
> 	depends on HAS_HW_NRF_UARTE$(nrfx_uart_num)
> 	depends on UART_ASYNC_API
> 	depends on UART_NRFX_UARTE_LEGACY_SHIM
> 	default y if !PM_DEVICE
> 	help
> 	  When enabled, UARTE is enabled before each TX or RX usage and disabled
> 	  when not used. Disabling UARTE while in idle allows to achieve lowest
> 	  power consumption. It is only feasible if receiver is not always on.
> 	  This option is irrelevant when device power management (PM) is enabled
> 	  because then device state is controlled by the PM actions.
> 
> ```
>
> 因此，两个都不打开也是可以低功耗的，只要其他配置与本文保持一致即可（异步串口）。
>
> 但是，很多NCS例程是只开了`CONFIG_PM_DEVICE`，没有开`CONFIG_PM_DEVICE_RUNTIME`，导致两种低功耗场景都沾不上边，**这种情况下，底电流约为15uA**。

# 踩坑记录

记录一个连环坑的情况，当打开以下配置时：

```
CONFIG_LOG_PRINTK=y
```

printk会从LOG的后端进行输出，也就是利用异步串口DMA进行输出，而不是串口阻塞API一个字节一个字节输出，这听起来很美好。

但是，当我们只用printk，且输出字符为刚好33字节时（含`\n`）：

```c
#include <zephyr/kernel.h>

int main(void)
{
    while(1)
    {   
        printk("12345678901234567890123456789012\n");        
        k_sleep(K_MSEC(1000));
    }
	return 0;
}
```

功耗会达到惊人的367uA！

![image-20250127005910755](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250127005910755.webp)

并且，多一个字节或者少一个字节，功耗都是正常的！

```c
#include <zephyr/kernel.h>

int main(void)
{
    while(1)
    {   
        //printk("12345678901234567890123456789012\n");
        printk("1234567890123456789012345678901\n"); 
        k_sleep(K_MSEC(1000));
    }
	return 0;
}
```

![image-20250127010021221](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250127010021221.webp)

我猜想这可能是因为33字节刚好触发了 Power Management 打开串口，但是却又差一个字节才能发出去，导致数据实际未能发出，要等下一次数据到来才能发送。但是发送完毕后，串口又立即被打开了。

这个问题最坑的点在于...

```c
printk("Hello World! %s\n", CONFIG_BOARD_TARGET);
```

`"Hello World! nrf52840dk/nrf52840\n"` 刚好就是33字节...

并且，在printk后面加一个LOG_INF输出，也不会出现这个问题。

这个Bug的出现让我一度怀疑我的其他配置出现了问题，各种修改尝试、切换SDK、翻阅源码，都无法找出原因，直到有次随手修改了打印的内容...

总之分享出来，让其他人别踩这个坑吧。
