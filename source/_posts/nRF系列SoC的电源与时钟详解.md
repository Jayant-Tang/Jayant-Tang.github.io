---
title: nRF系列SoC电源与时钟详解
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2026-10-09 14:30:00
cover: null
tags:
- Nordic
- nRF
- Zephyr
- NCS
- 低功耗
categories:
- Nordic
published: true
cnblogs:
  postType: Article
  postId:
  url:
---

# 1. 概览

电源和时钟源是 SoC 系统能运行起来的基础。本文会介绍 nRF 系列 SoC 的电源与时钟部分工作原理，帮助读者设计板子、排查问题、实现低功耗。

本文的代码和配置以 NCS v3.4.0 为准。部分内容在不同 NCS 版本之间有差异，例如 NCS v2.7.x 及之前的 regulator 配置方式、NCS v3.5.0 起的 clock driver，这些地方会单独标注版本。

资料来源是不同 nRF SoC 的Datasheet 中的 “**Power and clock management**” 章节，阅读本文时你可以对照阅读：

 ![image-20261009145156571](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined27870a40a192f19fbaab397098035adf.png)



# 2. 电源供电

## 2.1. regulator 硬件

芯片手册上会标注 VDD 供电电压范围，比如 1.7V ~ 3.6V ，但这不是内部核心电路的实际供电电压。外部供电经过 SoC上的 regulator 稳压，给内部核心电路供电。nRF52 系列内部 regulator 的输出电压为 1.3V，nRF54L 系列为 0.9V，可以在 Datasheet 引脚表中 DEC4、DECD 等去耦引脚的说明里查到。

nRF 芯片内部的 regulator 一般有两种模式，DC/DC 和 LDO。

- LDO 是线性regulator，外围器件少、布局简单、纹波小。但压差基本转换成热量浪费。
- DC/DC 效率更高，适合电流较大或输入电压明显高于内部电压的场景。需要外部电感和输出电容。

如下图是 **nRF52832** 的 regulator 框图。可以看到 DC/DC 会比 LDO 多一颗电感器件。

![img](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined1e537d3d139baa7da992d13e7b005808.svg)

![img](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedaffe5d577d8b2f2b8c897c3b44660f4b.svg)

而 **nRF54L15** 的 DC/DC 需要的外围器件会更多一些：

![Regulator configuration](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined9bc6a8ebb98649a3e9b3507d9fe35c2c.png)

> 一般来说，除非是板子面积非常极限、或者有超高精度器件不能容忍噪声的场景，否则**都推荐用DC/DC模式**。
>
> 例如，nRF52832 CPU 功耗对比（DCDC 或 LDO），基本相差一倍：
>
> | Symbol            | Description                                              | Typ. | Units |
> | :---------------- | :------------------------------------------------------- | :--- | :---- |
> | IDDFLASHCACHE     | CPU current, running from flash, cache enabled, LDO      | 7.4  | mA    |
> | IDDFLASHCACHEDCDC | CPU current, running from flash, cache enabled, DCDC 3V  | 3.7  | mA    |
> | IDDFLASH          | CPU current, running from flash, cache disabled, LDO     | 8.0  | mA    |
> | IDDFLASHDCDC      | CPU current, running from flash, cache disabled, DCDC 3V | 3.9  | mA    |
> | IDDRAM            | CPU current, running from RAM, LDO                       | 6.7  | mA    |
> | IDDRAMDCDC        | CPU current, running from RAM, DCDC 3V                   | 3.3  | mA    |
>
> 而 **nRF54 系列只能使用 DCDC 模式**。框图中标注的 LDO 只是启动时使用的，运行后会切换到 DCDC。

在设计板子时，外围器件直接按照 Datasheet 中的参考设计照抄即可：

![image-20261009150911881](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined7aee721db235862a6c4dad5581a43fb8.png)

> 【注意】
>
> regulator 只能给内部核心电路供电，不要在 DEC 引脚上接任何其他负载，必须严格按照参考电路进行设计。

## 2.2. 多级 regulator

像 nRF52840 有 VDDH 和 VDD 两个供电引脚，对应两种供电模式。其中 VDD 供电范围是 1.7~3.6V， VDDH 供电范围是 2.5V ~5.5V。

这是因为 nRF52840 内部有两级 regulator。如果你从 VDDH 供电，就需要两级降压。

![img](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined1c40317e5e42a571ebf06c8d676977ae.svg)

这两级也是可以都选择 LDO 的：

![img](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedcc58bf5b42b4ab8ad45167489a8634f8.svg)

nRF52840 也支持只用一级 regulator，这种情况下需要把 VDD 和 VDDH 短路，只使用 `REG1`：

![img](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb31af72bf264054388033393b39b119e.svg)

> 注，nRF52840 的 QFN48 封装没有 VDDH 输入，只有 VDD。

双核 SoC nRF5340 也支持 VDDH 输入。不过第二级 regulator 有两个，一个是 APP 核自己的`VREGMAIN`，另一个是给 RADIO 核供电的 `VREGRADIO`。

![High voltage mode setup with regulators in DC/DC mode](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined8588cf4fca199b3bfd774fcb72520299.png)

## 2.3. 升压 regulator 

regulator 并不一定都是降压电源。nRF 系列出了一款低压供电 SoC，**nRF54LV10**，供电范围 1.2V ~ 1.7V，可以直接用 1.5V 的氧化银纽扣电池或单节干电池供电（注意常见的 CR2032 是 3V，超出了供电范围）。

![Regulator configuration](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined08eb5f1742610c218af350285b709d90.png)

同样，只要对着参考设计连接外围器件即可。只要供电在允许的范围内，硬件会自动根据外部供电调节使用 BUCK 还是 BOOST。

## 2.4. regulator 软件配置

**nRF54 系列正常运行时必须工作在 DCDC 模式，因此我们没法修改配置。** LDO 只在启动时使用。不过 nRF54L 的 SoC dtsi 里 `vregmain` 默认也是 LDO，要靠 board dts 配成 `NRF5X_REG_MODE_DCDC` 才会打开 DCDC。Nordic DK 已经写好，自己画板时记得在 board 文件里也加上这一项。

对于 nRF52 / 53 这些老系列来说，芯片复位后硬件默认都是 LDO 模式，然后软件通过写相关寄存器来使能 DCDC 模式，Nordic DK 的 board 文件里已经配置成 DCDC，所以用 DK 时软件会默认打开 DCDC。自己画板时，SoC dtsi 里的默认值是 LDO，需要在自己的 board dts 里显式配置。如果板子上没有焊 DCDC 电感，就不要打开 DCDC，否则芯片无法运行，连调试接口都连不上。

如果你真的特别需要把模式改成 LDO，可以参考以下方式：

 nRF52832：

```dts
#include <zephyr/dt-bindings/regulator/nrf5x.h>

&reg {
  regulator-initial-mode = <NRF5X_REG_MODE_LDO>;
};
```

nRF52840：

```dts
#include <zephyr/dt-bindings/regulator/nrf5x.h>

// VDD
&reg1 { 
	regulator-initial-mode = <NRF5X_REG_MODE_LDO>; 
};

// VDDH，disable 就是LDO
&reg0 { 
	status = "disabled"; 
};
```

nRF5340：

```dts
#include <zephyr/dt-bindings/regulator/nrf5x.h>

// APP Core 
&vregmain { 
	regulator-initial-mode = <NRF5X_REG_MODE_LDO>; 
};

// Radio Core
&vregradio { 
	regulator-initial-mode = <NRF5X_REG_MODE_LDO>;
};

// VDDH，disable 就是LDO
&vregh { 
	status = "disabled"; 
};
```

在 NCS v2.7.x 及更早的版本中，无法使用设备树方式配置。当时开启 LDO 的方法是 Kconfig。例如:

```shell
# 只有一级 regulator 时
CONFIG_BOARD_ENABLE_DCDC=n

# 如果有 VDDH
CONFIG_BOARD_ENABLE_DCDC_HV=n

# nRF5340
CONFIG_BOARD_ENABLE_DCDC_APP=n
CONFIG_BOARD_ENABLE_DCDC_NET=n
CONFIG_BOARD_ENABLE_DCDC_APP_HV=n
```

# 3. 电源模式：System ON 和 System OFF

nRF 系列 SoC 的电源模式有 System ON 和 System OFF 两种状态。

常见电源管理术语与 Nordic 电源模式对照表：

| 常见术语                     | Nordic SoC 电源模式     | 说明                                                         |
| ---------------------------- | ----------------------- | ------------------------------------------------------------ |
| 活跃（Active / Running）      | System ON + CPU Running | CPU 正在执行代码，主时钟运行，功耗为几个 mA。                |
| 睡眠（Sleep）                | System ON + CPU Idle    | CPU 休眠，但时钟、外设、DMA仍可以工作。如果外设都关闭，则功耗为几个 uA。CPU 唤醒后继续向后执行代码。 |
| 深度休眠/关机 （Deep Sleep） | System OFF              | 核心时钟关闭，CPU停止。只留极少数唤醒逻辑（如 GPIO 电平检测，部分型号的 GRTC）。功耗为几百 nA。唤醒后代码将从 reset handler 开始运行。 |
| 断电                         | -                       | VDD 无供电，功耗为0                                          |

nRF54L15 功耗参考：

![image-20261009170550671](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinede07a10c294669eb1b3b052abc6f5cb30.png)

![image-20261009170527373](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined0a66ff1b4e3f8391f15fb8f828396f2c.png)

## 3.1. System ON

System ON是系统正常工作的电源状态。CPU可以运行，也可以休眠（执行`WFI`指令进入睡眠，等待中断或事件唤醒）。

在 Zephyr RTOS 中，所有的工作线程阻塞后会进入`idle`线程。而 Zephyr idle 线程会让 CPU 休眠。

这里说的阻塞，指的是：

- 线程主动调用 sleep
- 线程通过 `k_sem_take()` 等待某个信号量
- 线程调用了某个阻塞的 API（阻塞 API 的底层通常也是在等待信号量等内核对象）。

低功耗开发大概可以分为 **CPU 低功耗**和**外设低功耗**。根据前面的介绍，Zephyr 工程的低功耗开发逻辑非常简单：**每个功能块只负责自己的业务，阻塞等待所需的信号量、事件，然后做完就继续等待或者 sleep，CPU 就会自然而然地实现低功耗行为，不工作时就休眠**。不需要你去考虑如何在代码的合适位置调用 ARM 的 WFI 指令让 CPU 休眠。

nRF54L15 手册中描述的：“System ON, Wake on pin 256 KB RAM retained” 就是说 Zephyr 系统所有的工作线程都阻塞了，CPU 休眠，并且所有外设都关闭了，只留了一个 GPIO 唤醒源。在这种典型睡眠工况下的功耗是 2.7uA。

![image-20250127000857325](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250127000857325.webp)

至于外设低功耗，就是让外设在不用的时候关闭。这个可以参考 Zephyr 的 PM Device 框架，后面的章节会详细说明。

> 注：nRF 的操作系统 tick 都来自 RTC/GRTC，时钟源是 32.768k 低频时钟。Cortex-M 的 SysTick 计时器基本被当作不存在。因为 SysTick 是 CPU 外设，基于高频时钟，功耗太高。nRF 全系都是用 RTC/GRTC 作为操作系统 tick 来源。

## 3.2. System OFF 

System OFF 是 SoC 支持的最深低功耗状态。从使用者角度，可以把它理解成“关机”：

- CPU核心功能被关闭；
- 正在执行的任务会被终止；
- 大部分外设停止；
- 只有规定的唤醒检测逻辑继续工作；
- 部分 RAM 可以按配置保留；
- 唤醒后执行 system reset。

这里的 “RAM保留” 容易造成误解。RAM保留只表示部分数据可能还在，并不表示线程可以从睡眠点继续运行。唤醒后，启动流程会重新执行，最终从`Reset_Handler`进入启动代码和应用初始化。

因此下面两种状态的程序模型完全不同：

| 状态 | CPU | 唤醒后 | 典型用途 |
| --- | --- | --- | --- |
| System ON idle | 暂停执行，等待中断 | 从中断返回，继续原来的线程 | 普通Zephyr低功耗 |
| System OFF | 核心电源关闭 | reset，重新从`Reset_Handler`启动 | 电池设备长时间关机 |

## 3.3. Zephyr 中进入 System OFF

Zephyr提供了统一的`sys_poweroff()`接口。一个最小示例可以写成如下。这个例子没有配置唤醒源，进入 System OFF 后只能靠复位唤醒，唤醒源的配置见 3.4 节：

配置文件：`prj.conf`

```shell
CONFIG_POWEROFF=y
CONFIG_GPIO=y
```

代码：`src/main.c`

```c
#include <zephyr/kernel.h>
#include <zephyr/sys/poweroff.h>

int main(void)
{
    printk("Entering System OFF\n");

    /*
     * 进入后不会从这里返回。
     * 唤醒后会重新执行启动流程。
     */
    sys_poweroff();

    return 0;
}
```

调用 `sys_poweroff()`前，需要保证：

- EasyDMA传输已经结束；
- 不再有应用线程依赖正在关闭的外设；
- GPIO 唤醒引脚已经正确配置；
- 目标 SoC 要求停止的高速晶振已经停止；
- nRF54L 要求清除 reset reason，否则可能刚进入 System OFF 就被唤醒（Zephyr 的 `sys_poweroff()` 在 nRF54L 上会自动清除，见 8.1 节）；
- 不需要保留的 RAM 和外设已经关闭。

**在 debug 接口连接时，部分 nRF SoC 不会真正进入 System OFF，而是进入 Emulated System OFF，以保留调试所需资源。此时测得的电流可能比真正脱离debugger后的System OFF高，代码行为也可能看起来不像真正关机**。

## 3.4. System OFF的唤醒方式

唤醒源由SoC型号决定，常见来源如下：

| 唤醒源 | 典型信号/外设 | 说明 |
| --- | --- | --- |
| GPIO | `DETECT` | 通过 GPIO 的 SENSE 检测高电平或低电平 |
| 模拟比较器 | `ANADETECT`、LPCOMP | 电压越过阈值时唤醒，部分型号支持 |
| NFC | NFCT的field detect | 检测到 NFC 场时唤醒，部分型号支持 |
| 低频计数器 | GRTC/SYSCOUNTER compare | nRF54L部分型号支持 system off 时， GRTC 继续运行，可定时唤醒 |
| USB 电源 | VBUS valid | 带 USB 的 nRF52（如 nRF52833、nRF52840）、nRF5340 和部分 nRF54 型号支持 |
| 外部复位 | nRESET / pin reset | 外部复位会重新启动系统 |
| Debug | debug session | 进入调试接口时唤醒或模拟唤醒 |

Zephyr 中的 systemoff 唤醒例程是：`zephyr/samples/boards/nordic/system_off`

> NCS 的例程 `nrf/samples/zephyr/boards/nordic/system_off` 也可以，这个是在上述例程的基础上扩展了更多可选的 board。其`CMakeLists.txt`选中的`main.c`源码直接是复用上述例程中的源码文件，没有重新实现。

GPIO 是最常见的唤醒源。在 Zephyr 层面，给 GPIO 使能一个中断就行了，不需要配中断 callback。

```c
// get the gpio dt specifier
const struct gpio_dt_spec button = GPIO_DT_SPEC_GET(DT_ALIAS(sw0), gpios);

// configure pin
gpio_pin_configure_dt(&button, GPIO_INPUT);

// 边沿中断：引脚变为有效电平（active）时触发
gpio_pin_interrupt_configure_dt(&button, GPIO_INT_EDGE_TO_ACTIVE);
```

只需注意，在 nRF 系列 SoC 中，GPIO 本身可以产生 Port 中断（SENSE信号，一个 Port 上的一组 GPIO 引脚共享）；也可以给 GPIO 引脚分配 GPIOTE 通道来实现更快速的中断。Zephyr 中的 nRF GPIO 驱动对边沿中断默认使用 GPIOTE。Port 中断的功耗比 GPIOTE 更低，我实测两者相差十几微安。

System OFF 下 GPIOTE 不工作，只有 SENSE 产生的 DETECT 信号能唤醒芯片。上面的代码用的是边沿中断，驱动默认会给它分配 GPIOTE 通道，进入 System OFF 后按键无法唤醒。解决方法有两种：一是像官方例程那样改用电平中断 `GPIO_INT_LEVEL_ACTIVE`，驱动对电平中断始终使用 SENSE；二是保留边沿中断，把引脚配置成 Port 中断：

```dts
&gpio0 {
    status = "okay";
    sense-edge-mask = <(BIT(8) | BIT(31))>; // Use Port Event instead of Pin Event for low power:
                                            // P0.08
                                            // P0.31
};

&gpio1 {
    status = "okay";
    sense-edge-mask = <BIT(7)>; // Use Port Event instead of Pin Event for low power:
                                // P1.07
};
```

如上述示例，只需给对应的 GPIO controller 节点配置 `sense-edge-mask`属性，把想用 Port 中断的 GPIO 引脚号的比特位填入。代码不用修改，仍然是 Zephyr GPIO 中断的写法，就可以用 Port 中断代替 GPIOTE 中断，既能从 System OFF 唤醒，System ON 下也能省下这十几微安。

# 4. Zephyr 低功耗开发

前面介绍的 System ON 和 System OFF，描述的是 SoC 的系统级电源状态。实际开发中还要处理另一个问题：系统仍处于 System ON 时，如何让不用的外设停止工作。

Zephyr 的 Device Power Management（设备电源管理，简称 `PM_DEVICE`）就是解决这个问题的。它和 System Power Management 的分工如下：

| 电源管理层级 | 管理对象 | 典型行为 |
| --- | --- | --- |
| System Power Management | CPU 和 SoC 的系统状态 | 所有线程阻塞后，idle 线程执行 `WFI`，CPU 进入低功耗睡眠 |
| Device Power Management | 某一个外设及其引脚 | 挂起或恢复 UART、SPI、I2C、传感器等设备 |
| Device Runtime Power Management | 外设的运行时使用状态 | 外设不再被任何模块使用时自动 suspend，再次使用时自动 resume |

nRF52、nRF53 和 nRF54L 系列不支持、也不需要开启 `CONFIG_PM`：所有线程阻塞后，内核 idle 线程会直接执行 `WFI`。

## 4.1. PM Device：手动挂起和恢复外设

在 `prj.conf` 中开启：

```shell
CONFIG_PM_DEVICE=y
```

开启后，支持 PM 的驱动会注册一个 PM action 回调，用来处理 `PM_DEVICE_ACTION_SUSPEND`、`PM_DEVICE_ACTION_RESUME` 等动作。应用层可以通过 device 指针手动控制外设：

```c
#include <errno.h>

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/pm/device.h>

static const struct device *const uart_dev =
    DEVICE_DT_GET(DT_NODELABEL(uart0));

static int uart_suspend(void)
{
    if (!device_is_ready(uart_dev)) {
        return -ENODEV;
    }

    /* 调用前必须先停止 RX、TX 和 EasyDMA 传输。 */
    return pm_device_action_run(uart_dev, PM_DEVICE_ACTION_SUSPEND);
}

static int uart_resume(void)
{
    if (!device_is_ready(uart_dev)) {
        return -ENODEV;
    }

    return pm_device_action_run(uart_dev, PM_DEVICE_ACTION_RESUME);
}
```

`SUSPEND` 通常会关闭外设时钟、禁用外设，并把引脚切换到设备树中的 `sleep` pinctrl 状态；`RESUME` 则恢复外设和 `default` pinctrl 状态。具体能关闭哪些资源，取决于驱动是否实现了对应的 PM callback。

例如串口节点通常要同时提供 `default` 和 `sleep` 两组引脚状态：

```dts
&uart0 {
    status = "okay";
    pinctrl-0 = <&uart0_default>;
    pinctrl-1 = <&uart0_sleep>;
    pinctrl-names = "default", "sleep";
};

&pinctrl {
    uart0_sleep: uart0_sleep {
        group1 {
            psels = <NRF_PSEL(UART_TX, 0, 6)>,
                    <NRF_PSEL(UART_RX, 0, 8)>;
            low-power-enable;
            bias-pull-up;
        };
    };
};
```

`sleep` 状态下的上下拉不能照抄上面的示例，要根据外部电路决定。比如 UART RX 线上没有外部上拉时，可以用内部上拉保持空闲高电平；如果外部已经有上拉，就要避免重复增加漏电流。

手动 PM 适合设备状态由应用明确控制的场景，例如：

- 进入待机模式前关闭传感器和通信外设；
- 按键唤醒后恢复串口接收；
- 通过 GPIO 控制外部传感器供电，并同步挂起其总线设备。

手动控制有一个重要限制：应用必须知道这个外设当前是否仍被其他模块使用。如果一个线程挂起了仍被另一个线程使用的 SPI 总线，后者就可能在传输过程中失败。因此，多线程共享的总线外设更适合使用 Runtime PM。

## 4.2. Runtime PM：按引用计数自动管理外设

在 `prj.conf` 中开启：

```shell
CONFIG_PM_DEVICE=y
CONFIG_PM_DEVICE_RUNTIME=y
```

Runtime PM 使用引用计数记录外设的使用者：

1. 某个模块开始使用外设时，驱动调用 `pm_device_runtime_get()`，使用计数加一；如果外设处于挂起状态，就先执行 resume。
2. 模块使用完毕后调用 `pm_device_runtime_put()`，使用计数减一。
3. 使用计数变为 0 时，PM 子系统执行 suspend。

![img](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedf34742ba56bf7c4ffbe45cb73f4a1d39.png)

因此，多个线程或驱动同时使用同一个外设时，只要每次 `get` 都匹配一次 `put`，最后一个使用者释放设备后才会真正关闭外设。

> Runtime PM 对嵌套的设备同样有效。
>
> 比如，SPI 上挂了一个外部 Flash。如果 SPI 和 Flash 都开启了 Runtime PM，当你操作外部 Flash 时，驱动会自动唤醒外部 Flash；操作结束时，又会自动给外部 Flash 发送休眠（Deep Power-Down）指令，前提是 Flash 的设备树节点配置了 `has-dpd`。
>
> 与此同时，Flash 的驱动内部会调用 SPI 接口。SPI 在传输开始时也会自动唤醒 SPI 外设，SPI 传输结束时，又会自动关闭 SPI 外设。
>
> 整个流程，应用层只负责处理业务（Flash 读写），不用关心何时开关外设，低功耗由驱动自动完成。
>
> 但是，对于需要短时间密集操作外部 Flash 的场景，如 OTA DFU 接收固件时、录音并保存音频文件到外部 Flash 时，这种频繁开关外设对性能有很大影响。这种情况下，你也只需自己在应用层手动调用`pm_device_runtime_get()`，来让对应的外设持续工作。等到结束时，再调用`pm_device_runtime_put()`即可。 驱动内部的 get/put 只会让引用计数先加一再减一，不影响外层这对调用的配对关系。
>
> 另外，Zephyr 的 `spi_nor` 驱动自带 `CONFIG_SPI_NOR_ACTIVE_DWELL_MS`（默认 10 ms）：每次操作结束后先保持唤醒 10 ms 再进入休眠，连续操作间隔小于这个时间时不会反复开关。

Runtime PM 需要对具体设备实例启用，常见有两种方式，二选一即可。

方式一，在设备树节点增加 `zephyr,pm-device-runtime-auto;`：

```dts
&spi3 {
    status = "okay";
    zephyr,pm-device-runtime-auto;
};
```

方式二，在驱动初始化或应用初始化代码中调用：

```c
#include <zephyr/pm/device_runtime.h>

int err = pm_device_runtime_enable(spi_dev);
if (err < 0) {
    return err;
}
```

如果希望默认给所有支持 Runtime PM 的设备开启，可以使用 `CONFIG_PM_DEVICE_RUNTIME_DEFAULT_ENABLE=y`，但产品中通常更推荐逐个设备配置，避免某个尚未验证 PM 行为的驱动被自动挂起。

以串口为例，开启 Runtime PM 后，UARTE 驱动会在 `uart_rx_enable()` 和 `uart_tx()` 时自己调用 `pm_device_runtime_get()`，在 RX 关闭（`UART_RX_DISABLED`）和 TX 结束后调用 `pm_device_runtime_put_async()`。因此应用不用手动 suspend，不需要接收时调用 `uart_rx_disable()` 即可；异步 RX 一直开着，UARTE 就一直不会被挂起。如果用的是手动 PM，异步模式下 RX 或 TX 未停止时调用 suspend，驱动会返回 `-EAGAIN`。完整的异步串口处理方式见[《Zephyr驱动与设备树实战——串口》](https://jayant-tang.github.io/2023/11/4c8e1d7d162d/)的“休眠与串口低功耗”章节。

## 4.3. 低功耗排查清单

下面这份清单按硬件功耗来源组织。排查前先按第 5 条固定测量条件，否则测到的电流没有可比性。

### 1. 检查 HFCLK 和 HFXO 是否仍然活跃

在 System ON idle 的测量条件下，CPU 应该已经进入 idle，应用线程不能通过忙等循环持续运行。CPU 运行、RADIO 通信、USB、音频外设以及某些高速外设都会申请高频时钟资源。

重点检查：

- 是否还有线程在循环轮询，而不是阻塞等待事件；
- RADIO 是否仍在扫描、广播或连接事件中；
- USB、PDM、I2S、PWM、高速 Timer、UART/UARTE 等外设是否仍处于工作状态；
- 应用是否请求了 HFXO 却没有释放，不同 NCS 版本的请求和释放接口见 5.2 节；
- nRF53 的 APP Core 和 Network Core 是否都进入了预期的低功耗状态。

这里要区分 HFCLK 和 HFXO：**CPU 运行需要高频时钟，但默认由内部高频振荡器提供，不会因此启动外部 32 MHz HFXO**。因此，**不能用外部晶振没起振来判断 CPU 没在运行**。反过来，外部晶振起振也不一定是 CPU 在运行，可能是 RADIO 或某个外设请求了 HFXO。低功耗排查时尤其要确认是否有模块长期持有 HFXO。

可以先关闭 RADIO、USB、日志和音频等功能分别测量。如果关闭某一功能后电流明显下降，再回到对应驱动检查时钟 request/release 和外设状态。

### 2. 检查所有外设是否已经关闭

Nordic SoC 会根据外设的使用情况自动管理一部分时钟和电源资源，但“没有调用 API”不等于外设已经关闭。应逐个确认不需要的外设处于 disabled、suspended 或 idle 状态：

- 使用 Zephyr 驱动的外设，可以调用 `pm_device_action_run(dev, PM_DEVICE_ACTION_SUSPEND)` 手动挂起；
- 驱动支持 Runtime PM 时，可以通过 `pm_device_runtime_get()` / `pm_device_runtime_put()` 自动管理，或者在设备树中使用 `zephyr,pm-device-runtime-auto;`；
- 设备树中完全不用的外设，直接把节点配置为 `status = "disabled";`；
- 直接使用 `nrfx` API 初始化的外设，不会自动加入 Zephyr 的 Device PM，需要在业务结束后手动执行对应的 `uninit`、`disable` 或停止任务；
- UART/UARTE 的 RX、SPI/I2C 的 EasyDMA、ADC、PWM、PDM 和高频 Timer 都要确认传输或任务已经结束；
- 不要为了测功耗随意关闭产品必须运行的 WDT、RADIO 或安全模块，应以目标系统的功能需求为准。

特别注意串口日志。Nordic 官方文档明确提醒，NCS 例程默认的串口 logging 可能让本应为微安级的空闲电流达到数百微安。测量时应关闭 UART console、Shell、持续 RTT 和其他周期性日志；nRF53 的多镜像工程还要同时检查 APP Core 和 Network Core 的日志配置。

### 3. 检查 GPIO 和外设引脚是否漏电

低功耗状态下，每个引脚都要同时看 SoC 侧配置和板级电路，不能只看 `GPIO` 的逻辑值：

- 未使用的 GPIO 应配置为输入断开或符合目标 SoC 建议的低功耗状态，避免悬空输入；
- 输出电平要和外部器件的默认状态匹配，避免 SoC 输出高而外部器件强拉低，或者反过来；
- 检查 `bias-pull-up`、`bias-pull-down` 和外部上下拉是否重复或方向相反；
- 外设的 `sleep` pinctrl 状态必须与外部器件的休眠电平匹配，不能只配置外设本体而忽略引脚；
- 检查 SPI Flash、传感器、USB、LED、按键和电源控制脚是否通过 IO 产生反向供电。

上下拉电阻造成的电流可能远大于 SoC 本身的 sleep current。例如 3 V 供电时，10 kΩ 上拉电阻如果被外部电路拉到 GND，会产生约 300 µA 电流。因此，看到几百微安的固定电流时，应优先测量可疑 GPIO 两端的电压，而不是先怀疑 SoC 内部电路。

### 4. 检查 GPIO 唤醒和中断方式

GPIO 唤醒通常有两种实现：

- **Pin event**：通过 GPIOTE 通道监测单个引脚，响应速度快，但会占用 GPIOTE 资源，功耗比 Port event 高十几微安（见 3.4 节）；
- **Port event**：使用 GPIO 的 `SENSE` 汇聚出的 `DETECT` 信号，一个 Port 上的多个引脚共享事件，适合低功耗唤醒。

对于只要求低功耗唤醒、不要求极短响应延迟的 GPIO，优先使用 Port event，配置方法见 3.4 节的 `sense-edge-mask` 示例。

`sense-edge-mask` 只影响边沿中断。Zephyr 的 nRF GPIO 驱动（`gpio_nrfx.c`）对电平中断本来就使用 SENSE，不占用 GPIOTE 通道；没有列入 `sense-edge-mask` 的引脚，边沿中断才会使用 GPIOTE Pin event。需要更快响应时，就保留 Pin event，并接受它带来的资源和功耗开销。

还要检查以下细节：

- 配置 GPIO `SENSE` 前，先关闭对应中断，配置完成后清除可能已经产生的 `EVENTS_PORT`，再重新打开中断；
- 进入 System ON idle 前清除已经存在的 `DETECT` 源。若 `DETECT` 一直为高，系统进入 idle 后不会再次产生新的上升沿唤醒；
- 进入 System OFF 前尤其要清除 `DETECT`。部分 SoC 在 `DETECT` 已经为高时会立即从 System OFF 唤醒；
- 检查中断极性、外部上下拉和实际电平是否一致，避免 GPIO 中断风暴导致 CPU 反复唤醒；
- nRF54L 系列如果让 PERI 电源域的外设跨域使用 MCU 电源域的 P2 口，需要申请 Constant Latency 模式，idle 功耗会因此升高。我实测异步串口 RX 开启时，跨域使用比不跨域高约 250 µA，详见[《Zephyr驱动与设备树实战——串口》](https://jayant-tang.github.io/2023/11/4c8e1d7d162d/)的“nRF54系列GPIO跨域使用”章节。

### 5. 检查测量条件、芯片版本和板载器件

先固定与 Datasheet 一致的测试条件，再比较电流数值：

- VDD 电压、regulator 模式、LFCLK 时钟源和 RAM retention 配置；
- 测量的是 System ON idle 还是 System OFF；
- 测量回路是否包含板载电源芯片、LED、外部 Flash 和 Interface MCU；
- debugger 是否仍然连接并保持 debug session；
- 是否关闭了 USB、串口和其他板载辅助功能。

> 【注意】
>
> 测量低功耗时不要连接 J-Link 等 Debug 接口，也不要打开 RTT Viewer。部分 nRF SoC 在 Debug Session 下会保留调试资源，导致 System ON 或 System OFF 的实测电流偏高，System OFF 还可能表现为 Emulated System OFF。

如果软件配置、外设状态和引脚电平都符合预期，但电流仍然高于 Datasheet，应继续检查目标芯片的 Product Anomaly/Errata。例如 nRF54L15 Errata 中的 Anomaly 31，记录了部分修订版 System ON 睡眠电流偏高的问题，具体是否适用要看芯片的 revision 和 build code。

这份清单主要针对 System ON idle。System OFF 还需要单独检查唤醒源和 RAM retention。nRF54L 还要求进入 System OFF 前停止 HFXO 并清除 `RESETREAS`，否则设备可能立即被唤醒（`RESETREAS` 由 `sys_poweroff()` 自动清除，HFXO 要确认已没有模块在请求），测到的就不是稳定的 System OFF 电流。

# 5. 时钟（Clock）

![img](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined8261ee2c89414e06d87e2c992d7953b0.svg)

数字电路系统运行必须要时钟信号。nRF 系统内有两个时钟，高频时钟（HFCLK）和低频时钟（LFCLK）。

**高频时钟（HFCLK）**用于需要高速时序的模块，典型包括：

- CPU和高速总线；
- RADIO；
- 高频外设；
- LFRC校准时的参考时钟；
- 部分芯片中的USB或音频时钟链路。

**低频时钟（LFCLK）**典型频率为 32.768 kHz，主要服务于低功耗计时：

- RTC 和 GRTC；
- WDT；
- 操作系统 Tick（线程 sleep、协议栈通信间隔等）

### nRF 时钟源自动管理机制

在 nRF 开发中，时钟是自动控制使能和关闭的。当你使能一个外设，外设会自动向 clock controller 申请 HFCLK，如果这时 HFCLK 没打开，就会自动打开，默认使用的是 HFINT。LFCLK 则由 Zephyr 的 clock driver 在启动时按配置的时钟源打开，之后一直运行。所以一般不需要主动调用函数来开关时钟，需要 HFXO 作为 HFCLK时钟源的场景例外，见 5.2 节。当系统休眠时，也不需要主动调用函数来关闭时钟。

## 5.1. 低频时钟 LFCLK

在 Zephyr 中，System ON 状态下 LFCLK 一直运行，因为系统 tick 用的 RTC/GRTC 依赖它。

低频时钟有两个时钟源：LFRC 和 LFXO.

**LFRC** 是片上 32.768 kHz RC 振荡器：

- 不需要外部器件；
- 启动快；
- 精度受温度影响；

**LFXO** 使用外部 32.768 kHz 晶振：

- 长时间计时精度高；
- 适合低功耗无线协议；
- 需要晶振和负载电容；
- 启动时间通常比 LFRC 长；
- 晶振的 ESR、CL 要满足 Datasheet 要求，并按 CL 计算匹配电容（见第 6 章）。

当要求较高的低频精度时，应使用 LFXO。对于BLE等协议，最终允许的频率误差还要看协议栈、连接参数和目标芯片的 datasheet 要求。

> 蜂窝网络的 LTE Modem 明确要求使用 LFXO 作为低频时钟源。另外， ANT+ 协议要求低频时钟误差 ±50 ppm，而 LFRC 即使校准后，误差也有 ±500 ppm（nRF52840）或 ±250 ppm（nRF54L15），达不到要求。
>
> 对于 BLE，一般来说 Central 设备建议用 LFXO，或者温度变化大的场景也要用 LFXO。

### 在 Zephyr 中选择低频时钟源

NCS v3.5.0 开始，使用 Devicetree 来配置 LFCLK 时钟源。

选择 LFXO：

```dts
&lfclk {
    status = "okay";
    k32src = "xtal";
    k32src-accuracy-ppm = <20>; /* 根据晶体规格设置，如 20 或 50 */
};
```

选择 LFRC：

```dts
&lfclk {
    status = "okay";
    k32src = "rc";
    /* 精度属性：NRF52 系列通常设为 500，其他系列默认为 250 */
    k32src-accuracy-ppm = <250>; 
};
```

选择 LFRC 时，RC 校准（用 HFXO 校准 LFRC）默认开启，下面两项一般不用写。`CONFIG_CLOCK_CONTROL_NRF_CALIBRATION_PERIOD` 是校准检查周期，单位毫秒，默认 4000；温度变化不大时，驱动会跳过部分校准：

```shell
CONFIG_CLOCK_CONTROL_NRF_K32SRC_RC_CALIBRATION=y
CONFIG_CLOCK_CONTROL_NRF_CALIBRATION_PERIOD=4000
```

> NCS v3.4.x 及其更早版本使用 Kconfig 配置。
>
> 选择 LFXO：
>
> ```shell
> CONFIG_CLOCK_CONTROL=y
> CONFIG_CLOCK_CONTROL_NRF=y
> CONFIG_CLOCK_CONTROL_NRF_K32SRC_XTAL=y
> CONFIG_CLOCK_CONTROL_NRF_K32SRC_RC=n
> ```
>
> 选择 LFRC：
>
> ```shell
> CONFIG_CLOCK_CONTROL=y
> CONFIG_CLOCK_CONTROL_NRF=y
> CONFIG_CLOCK_CONTROL_NRF_K32SRC_XTAL=n
> CONFIG_CLOCK_CONTROL_NRF_K32SRC_RC=y
> 
> # 启用校准以提高精度
> CONFIG_CLOCK_CONTROL_NRF_K32SRC_RC_CALIBRATION=y
> CONFIG_CLOCK_CONTROL_NRF_CALIBRATION_PERIOD=4000
> # nRF52 系列用 500PPM，其他系列用 250PPM；不写时 Kconfig 会按芯片自动选择
> CONFIG_CLOCK_CONTROL_NRF_K32SRC_500PPM=y
> ```

## 5.2. 高频时钟HFCLK

HFCLK 也有两个时钟源，HFXO 和 HFINT

- HFINT：片上 RC 振荡器；
- HFXO：外部 32 MHz晶振经过片上倍频/时钟链路得到 64 MHz / 128 MHz 等主频。

但 HFCLK 的时钟源选择逻辑和 LFCLK 完全不同。LFCLK 时钟源是静态配置的，系统启动后就一直选择这个时钟源。而 **HFCLK 时钟源是运行时可以动态选择的**。

**HFINT** 不需要外部晶振，启动快，适合：

- CPU 日常运行（没有模块申请 HFXO 时，CPU 就跑在 HFINT 上）；
- 普通非射频任务；
- 对频率精度要求不高的外设；
- 芯片启动阶段。

它的主要缺点是频率精度受温度、电压和芯片个体影响，通常不能替代无线电要求的高精度HFXO。

**HFXO** 使用外部 32 MHz 晶振，频率精度高，适合：

- BLE、802.15.4等 RADIO；
- 对时序精度要求高的协议；
- 作为 LFRC 校准参考；
- 需要稳定时钟频率的外设。

HFXO 需要晶振、匹配电容或片上内部电容，并且启动需要一定时间。无线协议栈必须提前知道 HFXO startup time，才能在无线事件前及时启动晶振。

### 需要 HFXO 的场景

系统运行时，CPU 一般只需要 HFINT。在以下场景，系统才需要 HFXO，软件或硬件会自动申请：

- 射频（RADIO）：射频收发期间，[MPSL](https://nrfconnectdocs.nordicsemi.com/ncs/latest/nrfxlib/mpsl/README.html#mpsl) 或者 [SoftDevice](https://nrfconnectdocs.nordicsemi.com/ncs/latest/nrfxlib/softdevice_controller/README.html#softdevice-controller) 蓝牙协议栈只在收发窗口前后临时打开 HFXO，用完就关，比一直开着省电。
- USB：USBD 驱动会自动申请 HFXO，并等待 HFXO稳定后才会工作。
- 音频相关（I2S/PDM）：设备树里外设节点的 `clock-source` 属性决定申请哪个时钟（一般是 HFXO），有些芯片型号上会有音频专用时钟 Audio PLL。驱动会在外设运行时自动申请对应的时钟源。
- NFCT：NFC Tag 在检测到 NFC 场时，驱动会主动申请打开 HFXO。场消失后释放。

> 这也是为什么很多用户自己开发的板子，通过示波器在 32MHz 晶振上测不到持续的波形。因为他们的工程没有持续地开启上述功能。因此，一般我们不会用 32MHz 晶体起振来证明板子运行起来了。
>
> 但如果你的需求就是测量 32MHz 晶振波形，可以考虑烧录 [radio_test](https://nrfconnectdocs.nordicsemi.com/ncs/latest/nrf/samples/peripheral/radio_test/README.html) 等例程，这些例程会在程序开始时主动申请 HFXO，并持续开启。

此外，还有一些外设，在 HFXO 开启时可以提高精度，但是功耗也会提高，如：

- SAADC：HFXO 减少时钟抖动，提高性能
- UART / SPI / I2C：高速率（ 8M SPI, 1M I2C，1M UART）或者对时序敏感的对端设备建议开 HFXO。 

其中 1 Mbps 的 I2C（Fast-mode Plus）只有部分芯片支持：

| 芯片 | 支持 1 Mbps 的 TWIM | 硬件要求 |
| --- | --- | --- |
| nRF52 系列 | 不支持，最高 400 kbps | - |
| nRF5340 | 支持 | 必须使用专用引脚 P1.02、P1.03，驱动强度配置为 E0E1（20 mA 开漏驱动） |
| nRF54L15/L10/L05、nRF54LM20 | 所有 TWIM 实例都支持 | 驱动强度 H0D1，1 kΩ 上拉，总线电容不超过 50 pF |

Zephyr 中用 `clock-frequency = <I2C_BITRATE_FAST_PLUS>;` 设置 1 Mbps，驱动强度在 pinctrl 中用 `nordic,drive-mode = <NRF_DRIVE_E0E1>;` 或 `<NRF_DRIVE_H0D1>` 配置。

### 在 Zephyr 中主动切换 HFCLK 时钟源

在 NCS v3.5.0 之前，用`onoff_manager` API 来开关 HFXO；

从 NCS v3.5.0 开始，用`nrf_clock_control` API 来开关 HFXO。

以上两种方式都是基于“引用计数”的。即，**你在多个模块里都申请开启了 HFXO，然后再关闭 HFXO。申请时只会让引用计数器+1，关闭时只会让引用计数器-1。只要引用计数器大于0，那么HFXO就会一直开启。**

> 这两种方式还支持和 MPSL 共存：BLE 射频收发的窗口到来时，MPSL会打开 HFXO；窗口结束时，MPSL 会申请关闭 HFXO。MPSL 维护自己的一套 HFCLK 引用计数。HFCLK 驱动层有一个 user 的机制，分为 `BT` 和`GENERIC`，MPSL 和应用层不是同一个 user。只有两个 user 都停止占用 HFXO 的情况下， HFXO 才会被关闭。

Zephyr 标准的 `clock_control_on()`/`clock_control_off()` 没有引用计数：任何一个模块调用 off，HFXO 就会被关掉，不管别的模块还在不在用。另外 Nordic 驱动不允许两套接口混用，HFXO 已经通过 onoff 方式申请时，再调用 `clock_control_on()` 会返回 `-EPERM`。所以多个模块共用 HFXO 时，不要用这组 API。

#### NCS v3.5.0 及之后

使用 `nrf_clock_control` API：

首先确认高频时钟的节点 label：nRF52/nRF53 系列叫 `hfclk`，nRF54L 系列叫 `xo`。DK 板的设备树中这些节点默认已经是 `okay`；自定义板需要在 overlay 中打开，nRF54L 还要同时打开父节点 `&clock`：

nRF52840:

```dts
/* boards/nrf52840dk_nrf52840.overlay */
&hfclk {
  status = "okay";
};
```

nRF54L15：

```dts
/* boards/nrf54l15dk_nrf54l15_cpuapp.overlay */
&clock {
  status = "okay";
};

&xo {
  status = "okay";
};
```

开启相关 CONFIG：

```shell
CONFIG_CLOCK_CONTROL=y
CONFIG_CLOCK_CONTROL_NRF_ONOFF=y
CONFIG_CLOCK_CONTROL_NRF=n
```

说明：

- `CONFIG_CLOCK_CONTROL_NRF_ONOFF=y`：`nrf_clock_control_request()` 和 `nrf_clock_control_release()` 依赖它；
- `CONFIG_CLOCK_CONTROL_NRF=n`：关闭旧的统一 clock driver，它在 v3.5.0 中已标记为 deprecated。从 v3.5.0 开始，HFCLK、XO、LFCLK 各由单独的 driver 管理，见 `${NCS}/zephyr/drivers/clock_control/clock_control_nrf_hfclk.c`、`clock_control_nrf_xo.c` 等。

这几项在 v3.5.0 中都是默认值，写出来是为了明确意图。

代码：

```c
#include <errno.h>
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/clock_control/nrf_clock_control.h>

#define HFXO_DEVICE DEVICE_DT_GET(DT_NODELABEL(hfclk))
//  nRF54L15 将设备替换为：
// #define HFXO_DEVICE DEVICE_DT_GET(DT_NODELABEL(xo))

int hfxo_request_sync(void)
{
  if (!device_is_ready(HFXO_DEVICE)) {
      return -ENODEV;
  }
  return nrf_clock_control_request_sync(
      HFXO_DEVICE,
      NULL,
      K_SECONDS(1));
}
int hfxo_release_sync(void)
{
  int err;
  err = nrf_clock_control_release(HFXO_DEVICE, NULL);
  return err < 0 ? err : 0;
}
```

#### NCS v3.4.x 及之前版本

使用 `onoff_manager` API：

CONFIG：

```shell
CONFIG_CLOCK_CONTROL=y
CONFIG_CLOCK_CONTROL_NRF=y
```

代码：

```c
/*
 * HFXO onoff_manager 示例。
 *
 * 适用范围：
 * - NCS 2.x～3.4.x 的 legacy Nordic clock driver。
 * - NCS 3.5.0 及以后应优先使用 nrf_clock_control API。
 *
 * 注意：
 * - clock driver 只初始化一次 onoff_manager。
 * - 多个模块可以获取同一个 manager。
 * - 每个模块必须使用独立的 hfxo_onoff_handle。
 * - 每次成功 acquire() 必须匹配一次 release()。
 */

#include <errno.h>
#include <stdbool.h>

#include <zephyr/drivers/clock_control/nrf_clock_control.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/notify.h>
#include <zephyr/sys/onoff.h>

struct hfxo_onoff_handle {
	/* 所有模块可以指向同一个 manager。 */
	struct onoff_manager *manager;

	/* 每个模块必须拥有自己的 onoff_client。 */
	struct onoff_client client;

	/* 当前 handle 是否持有一个有效的 HFXO request。 */
	bool held;
};

/**
 * @brief 初始化 HFXO handle。
 *
 * 该函数只获取 driver 已经初始化好的 manager，不会重新初始化
 * onoff_manager。
 *
 * 每个 handle 只应初始化一次。多个模块应分别使用自己的 handle。
 *
 * @param handle 模块自己的 HFXO handle。
 *
 * @retval 0 初始化成功。
 * @retval -EINVAL 参数为空。
 * @retval -ENODEV clock manager 不可用。
 */
int hfxo_onoff_init(struct hfxo_onoff_handle *handle)
{
	if (handle == NULL) {
		return -EINVAL;
	}

	handle->manager =
		z_nrf_clock_control_get_onoff(CLOCK_CONTROL_NRF_SUBSYS_HF);
	handle->held = false;

	return handle->manager != NULL ? 0 : -ENODEV;
}

/**
 * @brief 请求 HFXO，并等待 HFXO 启动完成。
 *
 * onoff_request() 是异步 API，因此这里使用 sys_notify 等待
 * driver 的完成通知。sys_notify 的细节被封装在本函数内部。
 *
 * @param handle 模块自己的 HFXO handle。
 *
 * @retval 0 HFXO request 成功。
 * @retval -EINVAL 参数无效。
 * @retval -EALREADY 当前 handle 已经持有 HFXO。
 * @retval 其他负值 request 或 HFXO 启动失败。
 */
int hfxo_onoff_acquire(struct hfxo_onoff_handle *handle)
{
	int err;
	int result;

	if (handle == NULL || handle->manager == NULL) {
		return -EINVAL;
	}

	if (handle->held) {
		return -EALREADY;
	}

	sys_notify_init_spinwait(&handle->client.notify);

	err = onoff_request(handle->manager, &handle->client);
	if (err < 0) {
		return err;
	}

	do {
		err = sys_notify_fetch_result(&handle->client.notify, &result);
		if (err == -EAGAIN) {
			k_sleep(K_MSEC(1));
		}
	} while (err == -EAGAIN);

	if (err < 0) {
		return err;
	}

	if (result < 0) {
		return result;
	}

	handle->held = true;

	return 0;
}

/**
 * @brief 释放当前 handle 持有的 HFXO request。
 *
 * 只有成功执行 hfxo_onoff_acquire() 后，才能调用本函数。
 *
 * @param handle 模块自己的 HFXO handle。
 *
 * @retval 0 释放成功。
 * @retval -EINVAL 参数无效。
 * @retval -EALREADY 当前 handle 没有持有 HFXO。
 * @retval 其他负值 release 失败。
 */
int hfxo_onoff_release(struct hfxo_onoff_handle *handle)
{
	int err;

	if (handle == NULL || handle->manager == NULL) {
		return -EINVAL;
	}

	if (!handle->held) {
		return -EALREADY;
	}

	err = onoff_release(handle->manager);
	if (err < 0) {
		return err;
	}

	handle->held = false;

	return 0;
}

/* 业务代码示例。 */
static struct hfxo_onoff_handle hfxo;

void hfxo_demo(void)
{
	int err;

	err = hfxo_onoff_init(&hfxo);
	if (err < 0) {
		return;
	}

	/* 开启 HFXO。 */
	err = hfxo_onoff_acquire(&hfxo);
	if (err < 0) {
		return;
	}

	/* acquire 返回时，HFXO 已经启动并稳定。 */
	/* 可以在这里执行依赖 HFXO 的外设操作。 */
	k_sleep(K_SECONDS(1));

	/* 关闭当前模块持有的 HFXO request。 */
	err = hfxo_onoff_release(&hfxo);
	(void)err;
}
```

> 由于 `onoff_request()`是异步 API，需要一个等待机制，因此上述代码稍微有些复杂，加了`sys_notify`来做等待，然后封装成同步阻塞的 API。

#### 标准 Zephyr Clock Control API

这一套 API **不支持引用计数，因此不推荐在正式工程中使用**。只有单纯做射频测试、独占 HFXO 的场景才适合用。

如果需要，这里给出参考。下面的写法基于旧的 `CONFIG_CLOCK_CONTROL_NRF` driver，适用于 NCS v3.4.x 及之前；v3.5.0 中这个 driver 和 `CLOCK_CONTROL_NRF_SUBSYS_HF` 宏都已标记为 deprecated：

```dts
/* boards/nrf52840dk_nrf52840.overlay */
&clock {
  status = "okay";
};
```

```shell
CONFIG_CLOCK_CONTROL=y
CONFIG_CLOCK_CONTROL_NRF=y
```

```c
#include <zephyr/device.h>
#include <zephyr/kernel.h>
#include <zephyr/drivers/clock_control.h>
#include <zephyr/drivers/clock_control/nrf_clock_control.h>
#define CLOCK_DEVICE DEVICE_DT_GET(DT_NODELABEL(clock))
void hfxo_standard_demo(void)
{
    int err;
    if (!device_is_ready(CLOCK_DEVICE)) {
         return;
    }
    /* 打开 HFCLK/HFXO */
    err = clock_control_on(CLOCK_DEVICE,
    					CLOCK_CONTROL_NRF_SUBSYS_HF);
    if (err < 0) {
    	return;
    }

    // 外设操作
    k_sleep(K_SECONDS(1));

    /* 关闭 HFCLK/HFXO */
    err = clock_control_off(CLOCK_DEVICE,
    					CLOCK_CONTROL_NRF_SUBSYS_HF);
    (void)err;
}
```

# 6. 晶振匹配与参数配置

基本流程：

1. 晶振选型
2. 理论计算出一个合适的匹配电容
3. 在匹配电容附近进行微调，使得晶振的频率达到准确值
4. 测量 HFXO 晶振启动时间并在软件中配置

## 6.1. 晶振选型

![image-20261012173022318](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined6aaf8fcbfb1f697e3e09ace3298b7db2.png)

不论是高频晶振（32MHz）还是低频晶振（32.768kHz），选择的晶振都要符合 Datasheet 要求。首先是 PPM 不能超过允许的最大值，其次是负载电容 CL 要在符合要求的范围内。

## 6.2. 匹配电容计算

要计算晶振的匹配电容大小，首先需要看晶振 datasheet 中的 `CL`。`CL` 是晶振两个引脚之间看到的等效负载电容，实际负载等于这个值时，晶振才工作在标称频率。

常见的等效关系如下：

```text
           (C1 + Cpin) × (C2 + Cpin)
CL ≈  -----------------------------------
           (C1 + Cpin) + (C2 + Cpin)
```

每一侧的匹配电容（C1, C2）与芯片引脚寄生电容（Cpin）并联；左右两侧的等效电容再通过地串联。

![image-20261012161200570](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined9a3ee8a7caa23f20984827aa89f1f8c3.png)

其中：

- `C1` 和 `C2`：晶振两侧各自的匹配电容；
- `Cpin`：**其中一侧**芯片引脚、PCB走线、焊盘和封装等寄生电容。

在两边对称的情况下，`C1 = C2`，推导结果为：

```text
C1 = C2 ≈ 2 × CL - Cpin
```

使用外部匹配电容时，Cpin 可以先取 Datasheet 里的引脚输入电容，走线较长时再适当加大。

比如： nRF52840 的 HFXO 引脚寄生电容是 3 pF，因此，如果 nRF52840 用外部匹配电容，其电容值的计算公式就是 `2 × CL - 3pF` 。

像 nRF54L15DK，使用的是芯片**内部可调匹配电容**。一般取杂散电容为 1pF（图中的 Cpcb，和手册中的 GPIO pad capacitor 一样），内部匹配电容`Cint`公式为 `2 × CL - 1pF` 。

![img](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined343f57848b5e56e962d4752d090b56cd.svg)

我总结了几款开发板的原理图、BOM表上的晶振对应Datasheet、实际使用的匹配电容。我们来看看公式预测值和 Nordic 实际选择的值的区别：

| 开发板型号          | BOM晶振 CL |                           Cpin | 2 × CL - Cpin |          实际配置值 |
| ------------------- | ---------: | -----------------------------: | ------------: | ------------------: |
| nRF52840-DK + HFXO  |       8 pF | 3 pF（Datasheet 引脚寄生电容） |         13 pF |          12 pF 外部 |
| nRF52840-DK + LFXO  |       9 pF | 4 pF（Datasheet 引脚寄生电容） |         14 pF |          12 pF 外部 |
| nRF52-DK + HFXO     |       8 pF | 4 pF（Datasheet 引脚寄生电容） |         12 pF |          12 pF 外部 |
| nRF52-DK + LFXO     |       9 pF | 4 pF（Datasheet 引脚寄生电容） |         14 pF |          12 pF 外部 |
| nRF54L15-DK + HFXO  |       8 pF |       1 pF（PCB 杂散电容） |         15 pF | 15 pF 内部，NCS DTS |
| nRF54L15-DK + LFXO  |       9 pF |       1 pF（PCB 杂散电容） |         17 pF | 17 pF 内部，NCS DTS |
| nRF54LM20-DK + HFXO |       8 pF |       1 pF（PCB 杂散电容） |         15 pF | 15 pF 内部，NCS DTS |
| nRF54LM20-DK + LFXO |       9 pF |       1 pF（PCB 杂散电容） |         17 pF | 17 pF 内部，NCS DTS |

注意，公式给出的只是理论值。实际还是要拿自己的 PCB 板子去做微调。

> nRF5340DK 的配置有些特殊，不在上述表格中。
>
> nRF5340 HFXO 支持外部匹配电容也支持内部匹配电容。外部匹配电容时，寄生电容为5.5pF；内部匹配电容时，寄生电容为 2.5pF。DK 使用的晶振负载电容是 8pF，使用内部匹配电容。按照公式，其匹配电容应为 `2 × 8 - 2.5 = 13.5pF`。实际使用的是 12.5pF，来源见下文。
>
> nRF5340 的第一个特殊的点在于：它支持设备树配置匹配电容，但是 NCS 里却查不到默认值。因为5340的 HFXO 匹配电容值出厂时写在 FICR 寄存器里了，`SystemInit()`时从 FICR 直接拷贝到内部匹配电容寄存器。我从手上这块 DK 的 FICR 中实际读出的值是 12.5pF。
>
> nRF5340 的第二个特殊的点在于：它的 LFXO 内部电容的接法不一样，是直接跨接在XL1, XL2两个脚之间。因此 CL 和匹配电容基本就相等，不用上面的公式。BOM 中查看晶振的负载电容`CL`为 9 pF，实际软件配置匹配电容为 7 pF。
>
> ![img](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedd55a79de879a1fa04c048fa7a4eb1226.svg)

## 6.3. 内部匹配电容软件配置

如果是 nRF52 系列，只能用外部匹配电容。nRF5340 和 nRF54L 系列支持内部匹配电容，直接在 Devicetree 中配置。注意 nRF5340 的 LFXO 属性是 `load-capacitance-picofarad`，只能取 6、7、9 pF。

nRF54L15 内部电容配置：

```dts
/* board.overlay */
&hfxo {
  load-capacitors = "internal";
  load-capacitance-femtofarad = <15000>;
};

&lfxo {
  load-capacitors = "internal";
  load-capacitance-femtofarad = <17000>;
};
```

其单位是**飞法（fF）**，Datasheet 中有限制其步进和范围。

对于 nRF54L15 HFXO，范围是 4pF 到 17pF，步进 0.25pF。

对于 nRF54L15 LFXO，范围是 3pF 到 18 pF，步进 0.65pF。

> 如果你要用外部焊接负载电容，那么这个设备树里一定要配置：
>
> ```dts
> &hfxo {
>     load-capacitors = "external";
> };
> &lfxo {
>     load-capacitors = "external";
> };
> ```

在 NCS 中，直接用 Devicetree bindings 做了取值限制：

![image-20261013161919843](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb52f7d792b46915946b99a1859f609ec.png)

> 如何在 VS Code 中查找对应的 bindings 文件？
>
> 首先**成功编译一个固件**。在工程中选中你的 build target，找到 output file里的完整设备树生成文件 `zephyr.dts`。
>
> 根据你想查询的设备树节点，比如`hfxo:`，复制它的`compatible`属性，`Ctrl + P` 在 VS Code 中搜索文件，就能从 SDK 中搜到这个节点对应的 binding文件了。
>
> ![image-20261013163158818](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined3924cf182c949a763e728ff076042052.png)

## 6.4. 微调电容匹配

经过上面的理论计算后，需要以理论计算结果为起始点，微调匹配电容数值。

### HFCLK 匹配电容

 可以用 [radio_test](https://nrfconnectdocs.nordicsemi.com/ncs/latest/nrf/samples/peripheral/radio_test/README.html) 例程。把例程中的 Devicetree 串口引脚改成你自己的板子上的串口引脚，然后用串口命令使其在指定频率下持续发射载波。

```shell
# 打印当前测试参数
parameters_print

# 设置通道: 40 -> 2400 + 40 = 2440 MHz
start_channel 40

# 设置发射功率
output_power pos0dBm

# 开始发射载波
start_tx_carrier
```

然后用频谱仪分析频偏。慢慢微调匹配电容值，来达到符合你要求的 PPM。

内部电容调试起来比较方便。如果是外接电容，就找个电容本慢慢替换尝试。

### LFCLK 匹配电容 

调整方法和 HFXO 一样，改的是 `lfxo` 节点的匹配电容（nRF54L 为 `load-capacitance-femtofarad`，nRF5340 为 `load-capacitance-picofarad`）。区别在于频率怎么测：32.768 kHz 没有射频载波可以给频谱仪看，需要直接测时钟本身。

首先，不要把示波器或频率计的探头直接点在 XL1、XL2 上。普通无源探头有 10 pF 左右的输入电容，接上去就相当于多并了一个匹配电容，测到的频率会偏低，严重时晶振会直接停振。Nordic 的硬件设计指南对 HFXO 也有同样的提醒。

常用的做法是让芯片把 LFCLK 送到一个 GPIO 上，再用频率计测这个引脚。

nRF54L 的 GRTC 可以把 LFCLK 直接输出到专用引脚 P0.04（GRTC CLKOUT32K），Zephyr 中在设备树里打开即可：

```dts
&pinctrl {
	grtc_default: grtc_default {
		group1 {
			psels = <NRF_PSEL(GRTC_CLKOUT_32K, 0, 4)>;
		};
	};
};

&grtc {
	pinctrl-0 = <&grtc_default>;
	pinctrl-names = "default";
	clkout-32k;
};
```

GRTC 驱动初始化时会根据 `clkout-32k` 属性打开时钟输出，见 `${NCS}/zephyr/drivers/timer/nrf_grtc_timer.c`。nRF54L15 DK 上 P0.04 接的是 Button 3，测量时不要按这个按键，应用里也不要使用它。

nRF52 和 nRF53 没有时钟输出功能，可以用 RTC 的 TICK 事件，通过 PPI（nRF53 为 DPPI）触发 GPIOTE 的 TOGGLE 任务。RTC 预分频为 0 时，TICK 事件的频率是 32768 Hz，引脚每个 TICK 翻转一次，输出的方波频率是 16384 Hz，计算时要乘以 2。RTC 实例要避开 Zephyr 系统定时器使用的 RTC1，例如 nRF52 可以用 RTC2。

测量时对频率计有两点要求：

1. 分辨率要够：在 32768 Hz 下，1 ppm 只对应约 0.033 Hz，频率计要能分辨到 0.01 Hz 量级。可以用倒数计数（reciprocal counting）的频率计，或者把闸门时间加长到 10 s 以上；
2. 频率计自身的时基要比被测晶振准一个数量级以上，否则测到的是频率计自己的误差。

拿到实测频率后，按 `误差(ppm) = (实测频率 - 32768) ÷ 32768 × 1000000` 计算频偏，再调整匹配电容：实测频率偏高，就加大电容；偏低就减小电容。

如果手上没有频率计，也可以拿已经按上文调好的 HFXO 做参考，在芯片内部比较：先请求 HFXO（见 5.2 节），用 RTC 或 GRTC 的 COMPARE 事件经 PPI/DPPI 触发 TIMER 的 CAPTURE 任务，间隔一段时间捕获两次。例如间隔 327680 个 LFCLK 周期（10 s）时，16 MHz 的 TIMER 两次捕获的理想差值是 160000000，实测差值相对理想值的偏差比例，就是 LFXO 相对 HFXO 的误差。这种方法的精度取决于 HFXO 本身调得多准。

最后要注意温度的影响。32.768 kHz 的音叉晶振，频率随温度呈抛物线变化，室温（约 25 °C）附近频率最高，温度偏离越多，频率越低。室温下调到接近 0 ppm 后，还要加上工作温度范围内的温漂和老化，才是 LFXO 的实际精度，这个值就是 5.1 节中 `k32src-accuracy-ppm` 应该填写的值。

> 量产前一般还会做起振裕量（负阻）测试：在晶振和 XL 引脚之间串联电阻，逐步加大阻值直到晶振停振，停振时“串联电阻 + ESR”与 ESR 的比值就是起振裕量。具体要求以晶振厂商的规格书为准，32.768 kHz 晶振常见的要求是 3 到 5 倍以上。

## 6.5. HFXO启动时间测量与配置 

HFXO 节点里还有一个 `startup-time-us` 属性。它不配置硬件，只是告诉协议栈 HFXO 从启动到稳定大概需要多久。

HFXO 平时是关着的，当 RADIO 要通信时，协议栈需要提前一定的余量来开启 HFXO，**我们需要配置的是提前的余量是多少**。

> `startup-time-us`填得太小，可能导致BLE事件丢失；填得太大，则会让HFXO提前启动并增加功耗。

NCS 中，nRF54L05/10/15的启动时间余量默认配置的是 1650us

```dts
hfxo: hfxo {
    compatible = "nordic,nrf54l-hfxo";
    startup-time-us = <1650>;
};
```

> 在 NCS v2.8.0 ~ v3.0.x，启动时间靠的是`CONFIG_MPSL_HFCLK_LATENCY`配置，NCS v3.0.2 中 nRF54L 的默认值是 854us。
>
> 从 NCS v3.1.0 开始，改为在设备树中配置`startup-time-us`。`CONFIG_MPSL_HFCLK_LATENCY` 仍然保留，默认值取自 `startup-time-us`；如果在 `prj.conf` 里显式设置，会覆盖 Devicetree 的值。

可以测量一下真实的启动时间，然后**乘以 2** 配置为`startup time`。这里要测量的启动时间是 `TASKS_XOSTART` 和 `EVENTS_XOTUNED`之间的间隔。

![image-20261013182118127](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinede111ecab85d86d726e5864725a1579ba.png)



> 注意，不要测第一个间隔，因为晶振首次启动通常更慢。

**测量方案**：

1. 每1秒软件开启 HFXO 并拉高 GPIO P1.12
2. HFXO启动成功事件（`EVENTS_XOTUNED`）通过 PPI 触发 GPIOTE P1.12拉低
3. 0.5 秒后，软件关闭HFXO。

示例代码 `main.c`：

```c
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/clock_control.h>
#include <zephyr/drivers/clock_control/nrf_clock_control.h>

#include <hal/nrf_clock.h>
#include <hal/nrf_gpio.h>
#include <hal/nrf_gpiote.h>
#include <helpers/nrfx_gppi.h>

#define CLOCK_DEVICE DEVICE_DT_GET(DT_NODELABEL(clock))

#define MARKER_PIN NRF_GPIO_PIN_MAP(1, 12)
#define GPIOTE_CHANNEL 0

#define HFXO_HOLD_TIME_MS 500

static nrfx_gppi_handle_t xotuned_clear_handle;

static int marker_init(void)
{
    int err;

    nrf_gpiote_task_configure(NRF_GPIOTE20,
                               GPIOTE_CHANNEL,
                               MARKER_PIN,
                               NRF_GPIOTE_POLARITY_TOGGLE,
                               NRF_GPIOTE_INITIAL_VALUE_LOW);
    nrf_gpiote_task_enable(NRF_GPIOTE20, GPIOTE_CHANNEL);

    nrf_gpio_cfg(MARKER_PIN,
                 NRF_GPIO_PIN_DIR_OUTPUT,
                 NRF_GPIO_PIN_INPUT_DISCONNECT,
                 NRF_GPIO_PIN_NOPULL,
                 NRF_GPIO_PIN_H0H1,
                 NRF_GPIO_PIN_NOSENSE);

    err = nrfx_gppi_conn_alloc(
        nrf_clock_event_address_get(
            NRF_CLOCK, NRF_CLOCK_EVENT_XOTUNED),
        nrf_gpiote_task_address_get(
            NRF_GPIOTE20, nrf_gpiote_clr_task_get(GPIOTE_CHANNEL)),
        &xotuned_clear_handle);
    if (err < 0) {
        return err;
    }

    nrfx_gppi_conn_enable(xotuned_clear_handle);

    return 0;
}

static void hfxo_probe_thread(void)
{
    if (!device_is_ready(CLOCK_DEVICE) || marker_init() < 0) {
        return;
    }

    while (true) {
        nrf_gpiote_task_trigger(
            NRF_GPIOTE20, nrf_gpiote_set_task_get(GPIOTE_CHANNEL));

        if (clock_control_on(CLOCK_DEVICE,
                             CLOCK_CONTROL_NRF_SUBSYS_HF) < 0) {
            return;
        }

        k_sleep(K_MSEC(HFXO_HOLD_TIME_MS));

        if (clock_control_off(CLOCK_DEVICE,
                              CLOCK_CONTROL_NRF_SUBSYS_HF) < 0) {
            return;
        }

        k_sleep(K_MSEC(HFXO_HOLD_TIME_MS));
    }
}

K_THREAD_DEFINE(hfxo_probe_tid,
                1024,
                hfxo_probe_thread,
                NULL,
                NULL,
                NULL,
                5,
                0,
                0);

```

配置 `prj.conf`：

```shell
CONFIG_GPIO=y
CONFIG_CLOCK_CONTROL=y
CONFIG_CLOCK_CONTROL_NRF=y
CONFIG_CLOCK_CONTROL_NRF_K32SRC_RC=y
CONFIG_CLOCK_CONTROL_NRF_K32SRC_500PPM=y
CONFIG_CLOCK_CONTROL_NRF_K32SRC_RC_CALIBRATION=n
CONFIG_CLOCK_CONTROL_NRF_CALIBRATION_LF_ALWAYS_ON=n

CONFIG_NRFX_GPIOTE=y
CONFIG_NRFX_GPPI=y

CONFIG_ASSERT=y
CONFIG_MAIN_STACK_SIZE=2048

# 避免串口、日志或 Radio 在后台持有 HFXO
CONFIG_CONSOLE=n
CONFIG_UART_CONSOLE=n
CONFIG_SERIAL=n
CONFIG_LOG=n
CONFIG_PRINTK=n
```

说明：

- `CONFIG_CLOCK_CONTROL_NRF_K32SRC_RC_CALIBRATION=n`：LFRC 校准时，clock 驱动会临时请求 HFXO，波形上会多出不是测试代码触发的启动过程，所以要关掉；
- `CONFIG_PRINTK=n` 实际不会生效，NCS 的启动 banner 会强制打开 PRINTK，构建时会有警告。关掉 `CONFIG_SERIAL` 后 printk 已经没有输出通道，这一行可以删掉。

以上代码在 NCS v3.4.0 上编译通过。NCS v3.0.x 的 nrfx 没有 `nrfx_gppi_conn_alloc()`，无法编译；NCS v3.5.0 上可以编译，但 `CONFIG_CLOCK_CONTROL_NRF` 和 `CLOCK_CONTROL_NRF_SUBSYS_HF` 会报 deprecated 警告。

设备树 `nrf54l15dk_nrf54l15_cpuapp.overlay`

```dts
&clock {
    status = "okay";
};

&gpio1 {
    status = "okay";
};

&gpiote20 {
    status = "okay";
};

&dppic20 {
    status = "okay";
};

```

测量结果：

![image-20261013180506789](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined05d56f727c68386e46d04b54c2b0b5b6.png)

54L15DK上的测量结果为 492us，乘以 2 也比默认的 1650us 更小。这说明 SDK 中默认的 1650us 余量留的还是很充足的。

# 7. Reset 系统

![img](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined175ddffb21490b282448afcd6517216a.svg)

Reset 的作用是让 SoC 回到确定的启动状态。常见复位来源有上电（POR）、供电电压过低（BOR）、nRESET 引脚、软件、Watchdog、CPU lockup，以及 System OFF 唤醒。具体复位来源可以通过后面的 `RESETREAS` 查询。

## nRESET 引脚

通常不需要外部上拉。nRF SoC 的 nRESET 引脚内部已经集成了上拉电阻，正常设计中只需让按键、调试器或外部 supervisor 在需要复位时把它拉低即可。外部复位器件建议使用开漏或开集电极输出，不要用推挽输出直接驱动 nRESET。

只有在 Datasheet 明确要求，或者产品有特殊的 EMC、RC 延时、上升时间需求时，才考虑增加外部上拉或其他复位电路。外部上拉阻值过小还会增加功耗。

nRF52 部分型号（如 nRF52832、nRF52840）的 nRESET 与 GPIO 复用，只有在 UICR 的 `PSELRESET` 中配置后才作为复位脚。Zephyr 通过 `&uicr` 节点的 `gpio-as-nreset` 属性写入这个配置，nRF52840 DK、nRF52 DK 的板级 dts 默认已开启。配置一旦写入，只能擦除 UICR 才能取消，之后该引脚才能当普通 GPIO 用。nRF54L系列 使用专用 reset pin，**不能当作普通 GPIO 使用**。具体以目标型号的 Pin assignment 和 RESET 章节为准。

## Brownout 与掉电检测

BOR（Brownout Reset）可以理解为 SoC 内部的欠压复位保护。它的工作流程是：

1. 电源正常时，VDD 高于 BOR 的释放阈值，SoC 正常运行；
2. VDD 因负载突变、电池内阻或 regulator 响应不及时而跌破 BOR 阈值，BOR 立即触发复位，CPU 和外设停止在复位状态；
3. VDD 恢复到允许启动的电压后，BOR 释放 reset，SoC 重新执行启动代码，从 `Reset_Handler` 开始运行；
4. 如果电压仍然过低，SoC 会继续保持 reset，不会让 CPU 在不可靠的电压下运行。

掉电检测（Power-fail comparator，POF）用于提前预警：

![img](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined5eff0fdc1834befed5ec425aacf79690.svg)

它不会直接复位 CPU，而是在电压继续下降前产生告警，让应用停止 Flash 写入、关闭高功耗负载或保存必要状态。POF 不能代替 BOR。各型号是否支持 POF，以及 POF 在 System OFF 或不同时钟状态下能否工作，要查看具体型号的 Datasheet。

Zephyr 目前没有专门的 POF sample。Zephyr 的[通用 nrfx 例程](https://github.com/zephyrproject-rtos/zephyr/tree/main/samples/boards/nordic/nrfx)没有演示 POFWARN，实际开发可以直接使用 nrfx 的 [POWER driver](https://nrfconnectdocs.nordicsemi.com/ncs/latest/nrfx/html/group__nrfx__power.html)。

下面示例使用 `nrfx_power` 监听 POFWARN。示例适用于提供 `POWER/POFWARN` 外设的 nRF52、nRF53 等 SoC；不同型号的阈值枚举可能不同，`thr` 和 `thrvddh` 必须按照目标型号的 HAL 定义和 Datasheet 修改。nRF54 系列是否支持这套接口，也要以具体型号为准。

配置文件：`prj.conf`

```shell
CONFIG_NRFX_POWER=y
CONFIG_PRINTK=y
```

代码：`main.c`

```c
#include <zephyr/kernel.h>

#include <nrfx_power.h>

K_SEM_DEFINE(pofwarn_sem, 0, 1);

/* POFWARN 在中断上下文中触发，这里只发送通知，不做耗时操作。 */
static void pofwarn_handler(void)
{
    k_sem_give(&pofwarn_sem);
}

static const nrfx_power_pofwarn_config_t pof_config = {
    .handler = pofwarn_handler,
    .thr = NRF_POWER_POFTHR_V28,
    .thrvddh = NRF_POWER_POFTHRVDDH_V29,
};

static void pofwarn_init(void)
{
    /* 初始化并配置 POF 阈值。 */
    nrfx_power_pof_init(&pof_config);

    /* 使能 POFWARN 中断。 */
    nrfx_power_pof_enable(&pof_config);
}

int main(void)
{
    pofwarn_init();

    while (true) {
        k_sem_take(&pofwarn_sem, K_FOREVER);

        /*
         * 这里已经处于线程上下文，可以执行善后逻辑：
         * - 停止新的 Flash 写入；
         * - 关闭不必要的高功耗外设；
         * - 保存必要的运行状态；
         * - 上报低电压事件。
         */
        printk("POFWARN: supply voltage is low\n");
    }

    return 0;
}
```

POFWARN 回调运行在中断上下文中，不要在回调里直接执行 Flash 擦写、复杂日志或阻塞操作。需要注意，POFWARN 只是提前通知；如果 VDD 继续下降并越过 BOR 阈值，SoC 仍然会复位。

另外，部分 nRF52 型号的 Errata 对 POFWARN 和 NVMC 擦写有特殊限制：检测到 `POFWARN` 后不要继续执行 Flash 写入或擦除。Zephyr 的 Nordic Flash driver 已经针对部分 Errata 做了处理，但应用自己直接调用 `nrfx_nvmc` 时仍然要查看目标型号的 Errata。



# 8. Reset reason

## 8.1. RESETREAS 寄存器

nRF SoC通常通过`RESETREAS`记录复位来源，常见标志包括：

- pin reset；
- watchdog reset；
- software reset；
- CPU lockup；
- System OFF唤醒；
- LPCOMP、NFC、VBUS或GRTC唤醒；
- debug interface触发的复位。

不同系列的寄存器名称、bit定义和地址可能不同。nRF52840/52833的`RESETREAS`位定义和nRF54L的`RESET.RESETREAS`位定义并不完全相同。

例如 nRF54L15 的 `RESETREAS`的寄存器定义：[RESETREAS • nRF54L15 | nRF54L10 | nRF54L05 Datasheet • Technical Documentation](https://docs.nordicsemi.com/r/bundle/ps_nrf54l15/page/chapters/power-and-clock/reset/doc/reset.html-register.resetreas)

多数型号的reset reason寄存器具有两个重要特征：

1. 多个复位原因可能累积在同一个寄存器中；
2. 清除某个 bit 通常需要向该 bit 写1，而不是写0。

标志会累积，如果一直不清除，下次复位后读到的值里还混着以前的原因，容易误判。对写 1 清除的寄存器，把读到的值原样写回就能清掉所有已置位的 bit；Zephyr 的 `hwinfo_clear_reset_cause()` 在 nRF52、nRF53、nRF54L 上是直接对所有 bit 写 1（见 `${NCS}/zephyr/drivers/hwinfo/hwinfo_nrf.c`）。

nRF54L 系列还有一条硬性要求：进入 System OFF 前必须清除 `RESET.RESETREAS`，否则芯片可能刚进入 System OFF 就立即被唤醒。Zephyr 的 `sys_poweroff()` 在 nRF54L 上已经自动完成这一步（见 `${NCS}/zephyr/soc/nordic/common/poweroff.c`），应用不需要自己清。

## 8.2. Zephyr 中打印 reset reason

推荐使用Zephyr的HWINFO API，而不是直接访问某个SoC的寄存器。这样可以让代码在nRF52、nRF53和nRF54L之间尽可能保持一致。

配置文件：`prj.conf`

```shell
CONFIG_HWINFO=y
CONFIG_PRINTK=y
```

代码示例：

```c
#include <stdint.h>

#include <zephyr/kernel.h>
#include <zephyr/drivers/hwinfo.h>

static void print_reset_reason(void)
{
    uint32_t supported = 0;
    uint32_t cause = 0;

    if (hwinfo_get_supported_reset_cause(&supported) == 0) {
        printk("Supported reset causes: 0x%08x\n", supported);
    }

    if (hwinfo_get_reset_cause(&cause) != 0) {
        printk("Failed to read reset cause\n");
        return;
    }

    printk("Reset cause: 0x%08x\n", cause);

    if (cause & RESET_PIN) {
        printk("  - pin reset\n");
    }
    if (cause & RESET_WATCHDOG) {
        printk("  - watchdog\n");
    }
    if (cause & RESET_SOFTWARE) {
        printk("  - software reset\n");
    }
    if (cause & RESET_LOW_POWER_WAKE) {
        printk("  - wake from low power mode\n");
    }
    if (cause & RESET_CPU_LOCKUP) {
        printk("  - CPU lockup\n");
    }

    /*
     * 读取并保存日志之后再清除。
     * Matter 项目里清除由 Matter 负责，不要在这里调用，见 8.3 节。
     */
    if (hwinfo_clear_reset_cause() != 0) {
        printk("Failed to clear reset cause\n");
    }
}
```

`RESET_*`标志是 HWINFO API 的抽象标志。某个SoC是否支持某个标志，要先通过`hwinfo_get_supported_reset_cause()`确认。不能看到`RESET_LOW_POWER_WAKE`就认为所有nRF型号都有完全相同的System OFF唤醒bit，例如 nRF54L 被 GRTC 从 System OFF 唤醒时，HWINFO 上报的是 `RESET_CLOCK`。

另外，nRF 的 `RESETREAS` 没有上电复位和 BOR 的标志位。以 nRF52 为例，Datasheet 规定所有 bit 都为 0 表示上电复位或 BOR，所以 `cause` 为 0 时应按这两种情况处理，HWINFO 驱动也不会上报 `RESET_BROWNOUT`。

如果需要在异常处理、启动阶段和应用日志中都使用reset reason，建议在最早阶段读取一次，保存到一个普通变量或retained RAM，再由后续模块使用。不要让多个模块分别去读写硬件寄存器。

> Zephyr 也支持输出崩溃信息到串口、Flash 等，然后再结合 `.elf` 文件还原崩溃时的 Call stack，见[《在Zephyr中保存并离线分析Coredump崩溃现场》](https://jayant-tang.github.io/2026/09/feae4c91f17d/)。
>
> 要注意，NCS 例程默认开启的 `CONFIG_RESET_ON_FATAL_ERROR` 在崩溃后是通过软件复位重启的，reset reason 只会显示 software reset，和主动调用 `sys_reboot()` 区分不开。判断是否要上传 Coredump，更可靠的办法是用 `coredump_query(COREDUMP_QUERY_HAS_STORED_DUMP, NULL)` 查询 Flash 里有没有存下崩溃现场，reset reason 只作为辅助信息。

## 8.3. Matter 项目中的 reset reason

Matter 协议栈启动时会自己读取一次 reset reason，读完立即清除。所以在 Matter 项目里，应用如果等 Matter 启动之后再调用 `hwinfo_get_reset_cause()`，读到的通常是 0。

相关实现在 `${NCS}/modules/lib/matter/src/platform/Zephyr/DiagnosticDataProviderImpl.cpp`（NCS v3.0.2 和 v3.4.0 中这部分代码相同）。`DiagnosticDataProviderImpl` 是一个单例，它在构造时调用 `DetermineBootReason()`：先调用 `hwinfo_get_reset_cause()` 读取复位原因，紧接着调用 `hwinfo_clear_reset_cause()` 清除，再把结果转换成 Matter 规范定义的 `BootReasonEnum` 保存下来。这个单例最晚会在 `chip::Server::Init()` 启动 General Diagnostics cluster 时被创建。因此在 NCS 的 Matter 例程中，`Nrf::Matter::StartServer()` 返回时，reset reason 已经被 Matter 读走并清除了。

Matter 把保存下来的结果通过 `chip::DeviceLayer::DiagnosticDataProvider::GetBootReason()` 提供给应用。`CONFIG_CHIP` 会 `imply CONFIG_HWINFO`，所以一般不需要额外配置。

以 NCS Matter template 例程为例，在 `src/app_task.cpp` 中添加：

```cpp
#include <platform/DiagnosticDataProvider.h>

using chip::DeviceLayer::BootReasonType;

namespace {

const char *BootReasonToString(BootReasonType reason)
{
	switch (reason) {
	case BootReasonType::kPowerOnReboot:
		return "power-on or pin reset";
	case BootReasonType::kBrownOutReset:
		return "brown-out reset";
	case BootReasonType::kSoftwareWatchdogReset:
		return "software watchdog reset";
	case BootReasonType::kHardwareWatchdogReset:
		return "hardware watchdog reset";
	case BootReasonType::kSoftwareUpdateCompleted:
		return "OTA update completed";
	case BootReasonType::kSoftwareReset:
		return "software reset";
	default:
		return "unspecified";
	}
}

void LogBootReason()
{
	BootReasonType reason;
	CHIP_ERROR err = chip::DeviceLayer::GetDiagnosticDataProvider().GetBootReason(reason);

	if (err != CHIP_NO_ERROR) {
		/* 未开启 CONFIG_HWINFO 时返回 CHIP_ERROR_UNSUPPORTED_CHIP_FEATURE */
		LOG_WRN("Boot reason unavailable: %" CHIP_ERROR_FORMAT, err.Format());
		return;
	}

	LOG_INF("Boot reason: %s (%u)", BootReasonToString(reason), static_cast<unsigned>(reason));
}

} /* namespace */

CHIP_ERROR AppTask::Init()
{
	ReturnErrorOnFailure(Nrf::Matter::PrepareServer());

	/* ... 例程原有的初始化代码 ... */

	ReturnErrorOnFailure(Nrf::Matter::StartServer());

	/* StartServer() 返回后，Matter 已经完成 reset reason 的读取 */
	LogBootReason();

	return CHIP_NO_ERROR;
}
```

`GetBootReason()` 只是返回构造时保存的值，不会再访问硬件，可以在任意位置多次调用。同一个值也会通过 General Diagnostics cluster 的 `BootReason` 属性和 `BootReason` 事件上报给 Matter Controller，例如用 CHIP Tool 读取：

```bash
chip-tool generaldiagnostics read boot-reason <node-id> 0
```

`DetermineBootReason()` 按下表的顺序把 hwinfo 标志转换成 `BootReasonEnum`，命中一条就返回：

| hwinfo 标志 | BootReasonEnum |
| --- | --- |
| 没有任何标志，或含 `RESET_POR`、`RESET_PIN` | `kPowerOnReboot` |
| `RESET_WATCHDOG` | `kHardwareWatchdogReset` |
| `RESET_BROWNOUT` | `kBrownOutReset` |
| `RESET_SOFTWARE`，且 GPREGRET 中有 OTA 重启标记 | `kSoftwareUpdateCompleted` |
| `RESET_SOFTWARE` | `kSoftwareReset` |
| 其他，如 `RESET_CPU_LOCKUP`、`RESET_LOW_POWER_WAKE` | `kUnspecified` |

其中 OTA 重启标记由 `chip::DeviceLayer::Reboot(SoftwareRebootReason::kSoftwareUpdate)` 在重启前写入 GPREGRET 寄存器，见 `${NCS}/modules/lib/matter/src/platform/nrfconnect/Reboot.cpp`。

从这张表可以看出，`BootReasonEnum` 比 hwinfo 原始标志粗糙：上电复位和 pin reset 不区分，CPU lockup、System OFF 唤醒都归为 `kUnspecified`，Zephyr 平台也不会返回 `kSoftwareWatchdogReset`。另外，nRF 的 hwinfo 驱动不会上报 `RESET_BROWNOUT`：上电复位和 BOR 在 `RESETREAS` 中都表现为全 0（见 8.2 节），Matter 会把两者都报成 `kPowerOnReboot`，所以在 nRF 上看不到 `kBrownOutReset`。**如果业务需要这些细节，可以在 `main()` 开头、Matter 初始化之前，自己调用 `hwinfo_get_reset_cause()` 保存一份原始值。**

> 注意：
>
> 应用自己读取时，不要调用 `hwinfo_clear_reset_cause()`。否则 Matter 读到的是 0，会把每一次复位都当成 `kPowerOnReboot` 上报。清除的工作交给 Matter 即可。
