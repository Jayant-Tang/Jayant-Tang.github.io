---
title: Nordic GPIO硬件原理与NCS应用详解
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2024-01-22 16:21:43
cover: null
tags:
- Nordic
- Zephyr
- DeviceTree
- GPIO
- GPIOTE
- PPI
categories:
- Nordic
published: true
cnblogs:
  postId: '18141263'
  url: https://www.cnblogs.com/jayant97/articles/18141263
  lastPublishedAt: '2026-07-06T18:20:52+08:00'
  sourceHash: sha256:3d7c7973c2fda3936263e38003760142106ae322847aa3ce674e37aca226d920
  status: imported
  postType: Article
---

#  本文主题

1. Nordic MCU的GPIO硬件简介、GPIOTE是什么、PPI是什么
2. Zephyr中GPIO的使用、与外设引脚复用的方法（pinctrl）

> 声明：本文在解释硬件方面会比较详细，其目的是让读者在遇到问题时方便查阅，并debug底层寄存器信号。并非是推荐开发者直接进行寄存器开发，大多数情况下直接使用Nordic提供的外设API进行开发即可，可参考本文第3、4、5章。

# 1. GPIO硬件介绍

在介绍NCS中的GPIO和引脚复用（pinctrl）之前，有必要先介绍Nordic平台的GPIO相关硬件。

## 1.1. GPIO编号与分配表

每个Port上最多有32个GPIO，编号为0 ～ 31。Port从0开始，根据芯片封装的不同，可能还会有Port 1。**例如，在代码中，P0.12对应的引脚编号就是12，而P1.12对应的引脚编号就是32+12，也就是44。**

在每个手册的“Hardware and layout”章节，有不同MCU封装的GPIO功能说明，我们点进去可以看到每个引脚的用途。不仅是GPIO，还有一些电源和晶振引脚也包含其中：

![image-20240122163623759](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/c7d1ed9cc5d16e4daa3597d494a60c89.png)

![image-20240122164712134](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/07e201fb13fbc90479ad9d52e035c82f.png)

![image-20240122164636172](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/4bdab7ecda1cfd8cbff65cccb054fe8f.png)

![image-20240122164939613](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/98dc18fa7eef5779f5eef71b2f429f51.png)

> 这里面值得一提的一些信息有：
>
> 1. **模拟引脚是固定的**，标有Analog input的引脚才能作为模拟输入。
> 2. 外设的**数字引脚基本上是可以任意分配的**。但有些外设会有推荐的引脚，例如上图中的QSPI。
> 3. 某些引脚只能配置为Standard drive，无法作为高驱动模式。因此**不适合高速数据传输**的外设引脚。

## 1.2. GPIO硬件

下图来自于nRF52833 Product Specification。

![image-20240122162605569](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/c5c177122aeb8695fe5b1b51a48bed68.png)

从框图可以看出，GPIO可以作为模拟输入，也可以作为数字输入和输出。

> 只有部分GPIO可以作为模拟输入，见1.2小节

### 寄存器介绍

![image-20240130104903444](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/efbf5d9684190fc343c964608cd7b612.png)

Nordic平台的GPIO，每个port最多有32个引脚。

- OUT：32bit寄存器，bit写1使对应的GPIO输出高，写0使对应的GPIO输出低
- OUTSET：32bit寄存器，bit写1使对应的GPIO输出高，写0不影响对应的GPIO的状态
- OUTCLR：32bit寄存器，bit写1使对应的GPIO输出低，写0不影响对应的GPIO的状态
- IN：32bit寄存器，读取每个bit即为读取每个GPIO的状态
- DIR：32bit寄存器，bit写1使对应的GPIO配置为输出模式，写0使对应的GPIO配置为输入模式
- DIRSET：32bit寄存器，bit写1使对应的GPIO配置为输出模式，写0不影响对应的GPIO的模式
- DIRCLR：32bit寄存器，bit写1使对应的GPIO配置为输入模式，写0不影响对应的GPIO的模式
- LATCH：与休眠唤醒配置有关，见下方
- DETECTMODE：与休眠唤醒配置有关，见下方
- PIN_CONF：32个32bit寄存器。单独配置每个GPIO的输入输出（可覆盖DIR寄存器），输出模式、输出驱动能力、内部上下拉。

### GPIO输出状态与驱动能力配置

![Introduction to GPIO - General Purpose I/O - NerdyElectronics](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/8d88eaf30211c26cfc8593ea9b89dec9.png)

我们知道GPIO的**输出电路**内部是两个MOS管作为开关，也就是说，GPIO其实有三种状态：

- 输出高电平：上管导通、下管关断。通常代表逻辑1。
- 输出低电平：上管关断，下管导通。通常代表逻辑0。
- 输出高阻态：上下管均关断。可以代表逻辑0或逻辑1，取决于电路设计者自身的定义。

但我们控制GPIO时，代码中只会写0和1两种状态。这就要求我们提前配置好GPIO的输出模式（推挽、漏极开路、源极开路），每一种都代表不同的高、低电平或高阻态的组合：

![image-20240122170147234](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/e3efd7b8077d02e8abc1bfb9fdd58201.png)

以上8种状态，包含了推挽、漏极开路、源极开路的状态。此外，当GPIO输出高电平或低电平时，还有标准驱动能力（Standard）和高驱动能力（High drive）两种选择。

举例来说，S0S1就是推挽（Push-Pull）输出；而S0D1就是开漏（Open-Drain）输出。我们知道开漏输出是为了做“线与”操作的，I2C协议就需要这种配置。同理，D0S1就是源极开路输出，可以实现“线或”操作。

> 线与：相连的GPIO中只要有一个输出低电平，则整个线保持低电平，且不能出现短路；
>
> 线或：相连的GPIO中只要有一个输出高电平，则整个线保持高电平，且不能出现短路。 

这里除了标准驱动能力（Standard）之外，还有高驱动能力（High drive）可以选择。它相比于Standard可以输出更高的电流：

![image-20240122171447781](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/26bc6c2789100c12be754ac9bcf7d667.png)

上图中，GPIO的Electrical specification章节记录了GPIO的电气特性。可以看到标准输出和高驱输出时，拉电流与灌电流的承受范围。

> GPIO输出电压的变化，本质是给线上的等效电容充电或放电。因此GPIO输入输出电流的能力越强，则输出高频信号的能力越强。

### GPIO数字输入

关于输入，值得一提的是Nordic的输入是可以断开的（从框图中也能看出）。因此只要不使能输入和输出，GPIO内部就是断开的，不用担心漏电导致功耗问题。

### GPIO内部上拉/下拉电阻

导线高低电平的电磁学本质，是把导线和地平面之间看作一个微小的电容。输出高电平即为给电容充电，输出低电平即为给电容放电。

上/下拉电阻的作用是，当导线上的所有GPIO都处于高阻态时，通过这个上/下拉电阻给导线充、放电，使得导线的电平处于一个确定的状态。

例如I2C总线，线路上所有的IO都是开漏输出，因此需要一个上拉电阻。当所有IO都输出逻辑1（高阻态）时，能通过这个上拉电阻给导线电容充电，使得线路电平被拉高。

如果PCB上没有上拉电阻，就需要MCU配置内部上拉。配置相关的寄存器如下：

![image-20240130111651505](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/516447374f263597522004f29a6374b5.png)

使用内部上拉时，需要注意电阻的阻值，典型值为13千欧。线路上的RC值影响线路上电平变化的速度。当无外挂电容，只考虑线路寄生电容时，使用此内部上拉电阻，I2C总线**最高只能配置为100kbps**。若想要配置到400kbps，请使用外部4.7千欧或更低的上拉电阻。

![image-20240130111825537](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/f696dc3aaa43ff01ebc7f81daa7dcefc.png)

> 除了有提高电平变化速度的场景，还有需要降低电平变化速度的场景。例如，一些通过边沿触发的GPIO中断、或者Reset引脚的触发等。**不要认为有了上拉电阻，线路的电压就会稳定不受干扰**。因为如果线路上电容值很小，微小的电荷变化就会引起巨大的电压变化。因此线路要保持稳定的电平与上拉电阻关系不太大，反而与线路上的电容关系很大。

## 1.3. GPIO复用

Nordic平台的外设配置GPIO时，基本上是可以任意选择的。并且，**外设的配置可以自动覆盖（Override）GPIO的输入输出方向、输出值等配置**。见本文1.2.小节框图中的几个OVERRIDE信号。但是，GPIO的上下拉、输出模式等配置，还是要在GPIO的寄存器中进行配置。

### 数字复用

要配置一个外设所使用的GPIO，只需直接在这个外设对应的寄存器中进行配置。例如，下图是PWM外设中的PSEL（Pin Select）寄存器，就是可以选择任意一个port的任意一个pin作为输出引脚。当你在PWM外设的寄存器中配置引脚之后，会自动按照本文1.2小节框图中的OVERRIDE信号来覆盖对应GPIO的。

![image-20240130114131417](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/8910ba2d07720eb2d40103d0419da2c5.png)

### 模拟复用

模拟复用不能选择任意的GPIO，只能选择具有Analog Input功能的GPIO。以SAADC为例，这里只能选择AINx或者内部VDD、内部VDD/5作为输入，而不是GPIO的引脚编号。

![image-20240130114325318](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/a0f1293e228846b7f2129632e8ea8f0a.png)

### 特殊GPIO（RESET和NFC Tag）

Nordic平台具有UICR寄存器，这是一个flash之外的掉电不丢失区域，用于存储一些用户配置，可擦写。其中具有RESET和NFC Tag引脚的配置，以52840为例：

![image-20240131100105700](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/bdc2e489f13bd9d613cbfff44bfb00cc.png)

>nRF54L15的reset pin没有被分配GPIO编号。因此54L15的reset pin不能当作普通GPIO使用。

![image-20240131100201965](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/6d91c86599c6fc1fabb633700ea0b46e.png)

对于reset引脚来说，`PSELRESET[0]`和`PSELRESET[1]`的值都是PIN=18，PORT=0，CONNECT=0的情况下，P0.18才会作为Reset引脚使用。否则，P0.18作为普通GPIO使用。**Reset信号无法映射到其他GPIO**。

> 软件控制reset引脚作为普通GPIO使用：
>
> - 在nRF5 SDK中，**不要**设置全局宏定义`CONFIG_GPIO_AS_PINRESET`
>
> - 在NCS v2.5.0之后，需要在设备树overlay中增加：
>
> ```
> &uicr{
> 	// Pin used as GPIO, not nRESET
>     /delete-property/ gpio-as-nreset;
> };
> 
> &gpio0 {
> 	/delete-property/ gpio-reserved-ranges;
> };
> ```
>
> （在老版本NCS中是直接设置`CONFIG_GPIO_AS_PINRESET=n`）

NFC引脚是固定的两个，对于nRF52833来说是P0.09和P0.10。默认情况下这两个IO是GPIO，只有UICR中对应的bit写1之后，这两个IO才能作为NFC来工作。

> 软件控制NFC引脚作为普通GPIO使用：
>
> - 在nRF5 SDK中，在Keil/SES/Makefile中设置全局宏定义`CONFIG_NFCT_PINS_AS_GPIOS`
> - 在NCS v2.5.0之后，需要在设备树overlay中增加：
>   ```
>   &uicr{
>   	// Pin used as GPIO, not NFC
>   	nfct-pins-as-gpios;
>   };
>       
>   &gpio0 {
>   	/delete-property/ gpio-reserved-ranges;
>   };
>   ```
>
> 添加后，系统启动时会自动擦写UICR并重启。
>
> （在老版本NCS中是直接设置`CONFIG_NFCT_PINS_AS_GPIOS=y）

至于其他型号的MCU，注意看对应的uicr设备树compatible中规定了哪些值即可。

## 1.4. GPIO的Sense机制

![image-20240415155234948](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/6f5774a43c1dd4420a207aca001b74b0.png)

从GPIO的框图中我们可以看出，每个GPIO在处于输入模式的情况下，有一个SENSE信号。它可以被每个引脚的PIN_CNF寄存器中对应的bit位控制。可以配置为高电平触发或低电平触发。

![image-20240415155410982](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/c239182986954ff8f53ebab7fd37b8e5.png)

**所有引脚的Sense信号会汇聚成一个DETECT信号。这个DETECT信号有两种作用：**

- **使系统从System Off模式中唤醒（也就是GPIO唤醒休眠）**
- **在GPIOTE外设中产生Port中断（后续在GPIOTE章节中介绍）**

这个DETECT信号本身又有两种模式，通过DETECTMODE寄存器进行配置。

第一种是单纯的把所有引脚的PINx.DETECT信号进行**逻辑或运算**，也就是标准的DETECT信号。

另一种是在逻辑或之前加了一个锁存器（Latch），当PINx.DETECT置1时，相当于RS锁存器的Set端写1，LATCH寄存器中的对应Bit会被写1；当PINx.DETECT置0时，LATCH寄存器中的对应Bit会被锁存，不会变化。LATCH寄存器中对应的bit只有被CPU显式地写1时才会清0，相当于RS锁存器的Clear端写1。这个叫做LDETCT信号。



# 2. GPIOTE与PPI介绍

对于第一次接触Nordic平台的开发者，首先要明白一个概念：GPIOTE和GPIO是完全不同的外设。要理解为什么是这样，需要先理解Nordic外设接口（Peripheral interface）。

## 2.1. 外设接口（Peripheral interface）

在Nordic平台中，无论是什么外设，都遵循类似的外设接口，其框图如下：

![image-20240415161448616](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/216025fa4203288e7e2b4af6d5c5e99e.png)

整个框图代表外设，这个外设可以是Timer、串口、ADC等等。接下来详细解释内部框图的意思，框图中展示的都是所有外设都有的共通的部分。

### TASK寄存器

TASK寄存器代表这个外设的输入。例如Timer计时的开始、结束、清零；ADC采样的开始、结束；串口的发送开始、结束等等。**只要CPU给对应的TASK寄存器写1，外设就会去执行对应的动作。**

### EVENT寄存器与INTEN寄存器

EVENT寄存器代表这个外设的输出。例如串口DMA缓存接收满、ADC采样完成等等。这些事件（EVENT）可以用来触发CPU中断，只需要在INTEN寄存器中使能某个EVENT对应的中断，那么这个EVENT就能触发IRQ信号到NVIC模块。

### SHORTS寄存器

Shorts意为短路。它可以让某个外设的EVENT自动触发自己的TASK，从而实现自动循环执行，无需CPU的干预。

这个短路路径是预设好的，固定的几条，不能自由搭配。以定时器为例：

![image-20240415162841413](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/b8959c71d6d864b6e3bf53dc3b4e8918.png)

定时器最多有6个比较（Compare）通道。当定时器中的count值增长到某个通道的compare值时，触发compare事件。这里可以通过使能对应的SHORT寄存器，让这个COMPARE EVENT去触发定时器的CLEAR TASK，从而实现自动循环计数。也可以让这个COMPARE EVENT去触发定时器的STOP TASK，从而实现单次计数。

这里是无法把compare event连接到start task的（虽然这种连接本身没有意义），因为SHORTS寄存器里的路径是预设好的。

## 2.2.  PPI (Programmable Peripheral Interconnect)

在2.1章节中我们了解了外设的接口。从框图中可以看到TASK和EVENT寄存器上，还连接了PPI。这个PPI本身也是一个外设，它可以让你**把一个外设的EVENT寄存器直接连接到另一个外设的TASK寄存器上，从而实现外设之间的自动联动，无需CPU参与处理**。

![image-20240415164008994](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/7b60a3e4ebe3381524cb85bac71489b3.png)

图中的竖线，代表PPI的通道（Channel），nRF52833共有32条通道，其中前20条可以自由配置。**每个通道可以连接1个EVENT，和2个TASK。**（把EVENT寄存器的地址写入到CH[n].EEP寄存器；然后把想触发的TASK写到CH[n].TEP或者FORK[n].TEP中即可）。

> 举一个实际的例子，就是[《Zephyr驱动与设备树实战——串口》](https://jayant-tang.github.io/2023/11/4c8e1d7d162d/)中的提到高速异步串口：首先，Nordic的串口硬件具有DMA的功能，可以直接把数据从串口搬运到内存；然后，Nordic的串口驱动软件具有空闲计时的功能，当一定时间没有收到数据，DMA缓存还没存满的时候，就直接不等DMA中断了，直接产生串口回调函数，让CPU提前处理。
>
> 这里就产生了一个问题：此时DMA缓存未满，CPU只知道首地址，如何知道数据的长度呢？毕竟串口外设本身可没有计数功能。（RXD.AMOUNT寄存器只有DMA传输完毕才能读，这种提前读取的场景是不知道有多少的）。
>
> 一个纯软件的方法，就是每读到1个字节，就进入CPU中断，把一个变量+1。当传输完成时，读取这个变量，就知道一共收到了多少字节了。但是这种方法非常消耗CPU资源，且功耗高。当串口波特率达到921600时，CPU几乎无法做别的事情了。
>
> Nordic的驱动代码采用的是PPI的方法。每收到一个字节（EVENTS_RXDRDY），就通过PPI让Timer的计数器+1（TASKS_COUNT）。等到传输完毕时，直接读取Timer的计数值即可。整个传输过程中CPU都处于休眠状态，只有串口、timer、总线、内存等在工作。从而实现高性能、低功耗。
>
> 同理，带有流控的串口发送也是如此。串口正在发送时，突然收到流控制停止发送的信号，这时串口DMA立即停止发送。当重新恢复发送时，如何知道该从第几个字节开始重新发？也是一样使用Timer进行计数。

### PPI的使能与分组

PPI每个通道可以单独使能或关闭。通过CHEN寄存器写1使能，写0关闭。或者通过CHENSET和CHENCLR寄存器这种类似于SR锁存器的操作方式进行使能或关闭。

nRF52833的PPI外设还有6个通道组。每个通道组有32个bit，对应32条通道。只要某个Bit置1，那么对应的通道就会被包含在这个通道组里：

![image-20240415171821442](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/52f9072930d77cd88eb0cf1c159d79fc.png)

![image-20240415171810227](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/f1269abbf3a3c12964bd6adc5df92432.png)

通道组的作用仅仅只是让你可以同时使能或者关闭一组通道。

### 固定的PPI通道

对于nRF52833来说，20～31号通道是不可编程的，它的连接是固定的。通常用于连接RADIO、加密、RTC等外设。Nordic提供的无线协议栈（例如SoftDevice蓝牙低功耗协议栈）内部会用到这些PPI。

![image-20240415172000272](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/e861a9069b8b9eed6a86a3437816baef.png)

### 分布式PPI（DPPI）

从nRF5340、nRF9160开始，Nordic内部的PPI升级为DPPI。从而把1对2的PPI通道升级为多对多的PPI通道。

每个外设的TASK寄存器会有对应的SUBSCRIBE（订阅）寄存器；EVENT寄存器会有对应的PUBLISH（发布）寄存器。通过发布-订阅不同的DPPI通道，实现了多对多的外设事件传输。

具体可以参考nRF5340或nRF9160的手册。

### NCS中的PPI代码

前面都是讲解原理，比较详细。实际到NCS的代码中，PPI并不那么复杂。只需记住两个原则：

1. NCS中无论是PPI还是DPPI，都被封装为gppi接口，因此开发者无需关注它们的区别；
2. 永远不要自己指定某个具体的通道号来使用。因为Nordic的很多驱动代码里都用到了PPI，如果自己指定，很有可能和驱动中已经使用的通道冲突。因此我们应该用API来自动分配PPI通道，而不是自己指定。

```c
#include <helpers/nrfx_gppi.h>
#include <nrfx_timer.h>
#include <nrfx_gpiote.h>

...
    
// 分别获取两个外设的特定EVENT和TASK地址
uint32_t EVENT = nrfx_timer_compare_event_address_get(&timer_inst, NRF_TIMER_CC_CHANNEL0);
uint32_t TASK = nrfx_gpiote_out_task_address_get(&gpiote_inst, OUTPUT_PIN));

// 自动分配一个空闲的PPI通道
uint8_t gppi_channel;
nrfx_gppi_channel_alloc(&gppi_channel);

// 使用此通道连接一个EVENT寄存器和一个TASK寄存器
nrfx_gppi_channel_endpoints_setup(gppi_channel, EVENT, TASK);

// 使能通道
nrfx_gppi_channels_enable(BIT(gppi_channel));
```

> PPI例程位置：${NCS}/modules/hal/nordic/nrfx/samples/src/nrfx_gppi

## 2.3. GPIOTE (GPIO Tasks & Events)

**GPIOTE和GPIO是不同的外设**。通过第一章的介绍，我们知道GPIO作为输入输出，可以被CPU和其他外设使用。但是GPIO本身并不具有TASK和EVENT寄存器，因此无法与我们第二章介绍的PPI联动起来。

### GPIOTE: Pin Task, Pin Event

GPIOTE也有很多通道（Channels），对于nRF52833来说有8个，每一个通道可以连接1个GPIO。给这个GPIO扩展出TASK和EVENT寄存器，分别是：

- TASKS_SET：使对应的GPIO输出高电平
- TASKS_CLR：使对应的GPIO输出低电平
- TASKS_OUT：使对应的GPIO输出一个预设的行为（在GPIOTE->CONFIG寄存器的POLARITY bits中配置，这个预设的行为可以是输出高、输出低、翻转）
- EVENTS_IN：当对应的GPIO检测到预设的波形时，产生一个EVENT（同样在GPIOTE->CONFIG寄存器的POLARITY bits中配置。这个预设的行为可以是上升沿、下降沿、双边沿）

你可以用这些通道连接一个具体的GPIO，这样，本来不能产生中断的GPIO就可以通过EVENT寄存器产生中断了。

> 要查看具体的代码，同样可以查看${NCS}/modules/hal/nordic/nrfx/samples/src/nrfx_gppi例程。注意到GPIOTE的通道也是一种可以分配的资源。和PPI类似，使用时，不要自己指定具体的通道号，而应该用`nrfx_gpiote_channel_alloc()`函数来申请一个空闲的通道，以免和Nordic驱动代码中已经使用的GPIOTE通道冲突。

### GPIOTE: Port Event

GPIOTE还有一个EVENT寄存器叫做EVENTS_PORT。在第一章节讲述GPIO时，提到GPIO有一个SENSE机制，全体GPIO的SENSE信号进行或运算后，会得到DETECT信号。

![image-20240122162605569](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/c5c177122aeb8695fe5b1b51a48bed68.png)

这里GPIOTE的EVENTS_PORT就是用来把这个DETECT信号变成一个Events寄存器，从而可以用来产生中断，或者连接PPI。

> 注意，DETCT信号虽然不是一个EVENT，但是DETECT信号本身就能把CPU从System Off模式唤醒，无需GPIOTE。



# 3. 在Zephyr系统中使用GPIO

前面两章详细介绍了GPIO、GPIOTE和PPI的硬件，目的是让开发者在遇到问题时可以知道该从哪里去Debug，该看什么寄存器。但在一开始软件开发时，不需要关心这么多细节。只需调用现成的驱动API即可。

## 3.1. 在Zephyr DeviceTree中配置GPIO

由于Zephyr所有硬件操作都在DeviceTree中完成，故需要先配置DeviceTree。下图演示了如何在一个node中写gpio：

```c
 n: node {
    foo-gpios = <&gpio0 1 GPIO_ACTIVE_LOW>,
                <&gpio1 2 GPIO_ACTIVE_LOW>;
 }
```

首先，由于GPIO的配置是一个**属性**，因此必须写在一个节点（Node）内，例如`led_0`内。

> 在[《详解Zephyr设备树（DeviceTree）与驱动模型》](https://jayant-tang.github.io/2023/03/4b274a50e575/)一文中，我们知道DeviceTree的节点不能自己随便添加，每个节点都有对应的compatible，而compatible又必须有对应的Device Binding yaml文件，以及对应的驱动文件。现在问题是，**如果我只想单纯的添加一个自由的GPIO，不使用任何led或者button驱动程序，该如何做？**
>
> 你可以把gpio放在`/zephyr,user`节点下。这是一个自由的节点，就是用来绕过Device Binding，专门放开发者一些自由的device tree属性的，想在里面写什么都可以。
>
> ```c
> /{
>     zephyr,user{
>         my-gpios = <&gpio0 12 (GPIO_ACTIVE_HIGH|GPIO_PUSH_PULL|GPIO_PULL_DOWN)>;
>     };
> };
> ```

然后是属性的名字，**属性的名称必须以`gpios`结尾**，也可以只写`gpios`。这样它才能被编译系统识别。

然后是属性的值，这是一个phandle-array类型的属性，可以写很多组。每个元素都是由三个部分组成：

- GPIO Controller：也就是我们俗称的port。这里可以直接引用label，例如`&gpio0`。
- GPIO Pin Number：这个就是引脚编号。P0.12的编号就是12。
- GPIO配置：激活状态、输入输出、上下拉等等。可以在这里配置，也可以后续在应用代码里配置修改。

> 注意，部分开发者会有误解。
>
> 激活状态`GPIO_ACTIVE_LOW`的意思是“逻辑1 = 低电平”；`GPIO_ACTIVE_HIGH`的意思是“逻辑1 = 高电平”。**这是用于配置激活状态的参数，而不是部分人误解的配置默认输出高低电平的参数。**
>
> `GPIO_ACTIVE_LOW`常见于LED灯。因为MCU gpio灌电流能力比拉电流能力强，因此LED电路往往是电流流入GPIO，也就是“低电平 = LED灯亮”。

更多GPIO配置的参数选项，请参考文档：https://docs.zephyrproject.org/latest/hardware/peripherals/gpio.html

## 3.2. 在代码中控制GPIO

首先，需要在conf文件中使能GPIO的驱动（大多数例程都是默认使能的）：

```shell
CONFIG_GPIO=y
```

在代码中，首先包含头文件：

```c
#include <zephyr/devicetree.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
```

### 方式一：以gpio pin为对象进行控制

在main函数中创建一个`gpio_dt_sepc`结构体，这个是操作一个单独GPIO的句柄：

```c
 const struct gpio_dt_spec my_gpio = GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), my_gpios);
```

1.  device tree中的内容都不可更改，故用cosnt变量存储最好
2. `GPIO_DT_SPEC_GET()`可以直接从device tree中读取到一个结构体的值
3. 第一个参数是node_id，由于我们放在`/zephyr,user`节点下，故可以用绝对路径来指明这个节点，`DT_PATH(zephyr_user)`。其中逗号是名称的一部分，在C语言中要变成下划线，才能当作名称的一部分。
4. 第二个参数是device tree的属性，也就是`my-gpios`。在C语言中，`-`需要变成下划线。

然后就可以配置、读写该GPIO

```c
// write
gpio_pin_configure_dt(&my_gpio, GPIO_OUTPUT);
gpio_pin_set_dt(&my_gpio, 1);

//read
gpio_pin_configure_dt(&my_gpio, GPIO_INPUT);
int val = gpio_pin_get_dt(&my_gpio);
```

### 方式二：以gpio port为对象进行控制

使用port控制不需要像前面一样给单独的pin编写device tree，适合快速写一些测试用的代码。**但它的缺点是，你使用的所有GPIO都不会在DeviceTree中有提示，如果有GPIO使用冲突，编译时无法帮你检查出来。**

```c
//获取GPIO Port的句柄
const struct device *dev_gpio0 = DEVICE_DT_GET(DT_NODELABEL(gpio0));

gpio_pin_configure(dev_gpio0, 12, GPIO_OUTPUT);
gpio_pin_set(dev_gpio0, 12, 1);

gpio_pin_configure(dev_gpio0, 12, GPIO_INPUT);
int val = gpio_pin_get(dev_gpio0, 12);
```

更多API，请参考[Zephyr GPIO文档](https://docs.zephyrproject.org/latest/hardware/peripherals/gpio.html)。

### 配置GPIO的电流驱动能力

从第1章我们知道，Nordic MCU的IO口驱动能力是可以配置的，这个是Nordic独有的功能，与Zephyr无关，具体参数为：

```c
/** Standard drive for '0' (default, used with GPIO_OPEN_DRAIN) */
#define NRF_GPIO_DRIVE_S0	(0U << 8U)
/** High drive for '0' (used with GPIO_OPEN_DRAIN) */
#define NRF_GPIO_DRIVE_H0	(1U << 8U)
/** Standard drive for '1' (default, used with GPIO_OPEN_SOURCE) */
#define NRF_GPIO_DRIVE_S1	(0U << 9U)
/** High drive for '1' (used with GPIO_OPEN_SOURCE) */
#define NRF_GPIO_DRIVE_H1	(1U << 9U)
/** Standard drive for '0' and '1' (default) */
#define NRF_GPIO_DRIVE_S0S1	(NRF_GPIO_DRIVE_S0 | NRF_GPIO_DRIVE_S1)
/** Standard drive for '0' and high for '1' */
#define NRF_GPIO_DRIVE_S0H1	(NRF_GPIO_DRIVE_S0 | NRF_GPIO_DRIVE_H1)
/** High drive for '0' and standard for '1' */
#define NRF_GPIO_DRIVE_H0S1	(NRF_GPIO_DRIVE_H0 | NRF_GPIO_DRIVE_S1)
/** High drive for '0' and '1' */
#define NRF_GPIO_DRIVE_H0H1	(NRF_GPIO_DRIVE_H0 | NRF_GPIO_DRIVE_H1)
```

**需要包含头文件，才可以使用这些参数**

```c
#include <zephyr/dt-bindings/gpio/nordic-nrf-gpio.h>

...

gpio_pin_configure_dt(&my_gpio, GPIO_OUTPUT | GPIO_OPEN_DRAIN | NRF_GPIO_DRIVE_H0);
// 开漏输出，且低电平为高电流驱动能力
```

## 3.3. 使用GPIO输入中断

使用GPIO输入中断也很简单，参考`${NCS}/zephyr/samples/basic/button`即可。具体步骤为：

```c
void button_pressed(const struct device *dev, struct gpio_callback *cb,uint32_t pins)
{
	printk("Button pressed at %lu \n", k_cycle_get_32());
}

void main()
{
    ...
        
    // get the gpio dt specifier
    const struct gpio_dt_spec button = GPIO_DT_SPEC_GET(DT_ALIAS(sw0), gpios);

    // configure pin
    gpio_pin_configure_dt(&button, GPIO_INPUT);

    // configure interrupt: rising edge
    gpio_pin_interrupt_configure_dt(&button, GPIO_INT_EDGE_TO_ACTIVE);

    // init and add your callbacks
    static struct gpio_callback button_cb_data;
    gpio_init_callback(&button_cb_data, button_pressed, BIT(button.pin));
    gpio_add_callback(button.port, &button_cb_data);
    
    ...
}
```

> 注意，不要真的拿这个代码去处理按钮。因为这个是最底层的GPIO中断，并没有按键消抖功能。
>
> 对于低功耗的按钮方案，需要触发GPIO中断，然后执行10ms的k_work进行去抖，最后再判定button是否按下。

### Port中断与Pin中断

根据前面的硬件部分说明，GPIO的输入中断还分为Pin Event 和 Prot Event中断，代码上没有区别，设备树有区别。

**当中断的检测方式是边沿检测时（触发方式包含`GPIO_INT_EDGE`，例如`GPIO_INT_EDGE_TO_ACTIVE`），才可以使用Port Event。**

此时要修改设备树：

```
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

在52840上，Port event比Pin event功耗更低，且会节省一个GPIOTE通道。但是理论上触发的延迟会高一些。

## 3.4. 注意开发板保留GPIO

Nordic开发板上某些GPIO已经被板载的外设使用了，所以，在开发板上这些**引脚对应的GPIO插座是没有连接的**。例如52840DK：

![image-20250526155758973](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250526155758973.png)



用于NFC的引脚以及用于QSPI Flash的引脚，在开发板上都被空焊盘断开了。这些信息也可以通过开发板背面的丝印示意图获得。

为了防止用户误使用这些GPIO，实际用示波器检测引脚又没有波形，浪费时间。Nordic在**开发板的设备树**中把这些引脚设为保留的（Reserved）。见gpio0或gpio1的设备树：

```
&gpio0 {
	status = "okay";
	gpio-reserved-ranges = <0 2>, <6 1>, <8 3>, <17 7>;
	gpio-line-names = "XL1", "XL2", "AREF", "A0", "A1", "RTS", "TXD",
		"CTS", "RXD", "NFC1", "NFC2", "BUTTON1", "BUTTON2", "LED1",
		"LED2", "LED3", "LED4", "QSPI CS", "RESET", "QSPI CLK",
		"QSPI DIO0", "QSPI DIO1", "QSPI DIO2", "QSPI DIO3","BUTTON3",
		"BUTTON4", "SDA", "SCL", "A2", "A3", "A4", "A5";
};
```

这里的`gpio-reserved-ranges`，每个cell表示（gpio起始编号，gpio数量）的组合。以上赋值表示P0.00，P0.01，P0.06，P0.08～P0.10，P0.17～P0.23均为保留GPIO。

如果用户使用了这些引脚，将会出现Assert报错，从而提示用户：

```bash
ASSERTION FAIL [(cfg->port_pin_mask & (gpio_port_pins_t)(1UL << (pin))) != 0U] @ WEST_TOPDIR/zephyr/include/zephyr/drivers/gpio.h:1019
        Unsupported pin
```

> 注意，这个保护是开发板的设备树才有的。如果你使用自定义boards，本身默认就没有配置`gpio-reserved-ranges`。

如果开发者知晓自己在做什么，知晓如何控制这些GPIO，则开发者可以主动去除这一限制：

```
&gpio0 {
	/delete-property/ gpio-reserved-ranges;
};
```

## 3.5. GPIO配置示例

这里展示最复杂的情况，配置使用reset脚和NFC引脚当作gpio output使用：

设备树overlay：

```
/ {

   // 使用zephyr,user节点自由放置GPIO配置
	zephyr,user{
		reset-gpios = <&gpio0 18 GPIO_ACTIVE_HIGH>;
		nfc-gpios = <&gpio0 9 GPIO_ACTIVE_HIGH>, 
		            <&gpio0 10 GPIO_ACTIVE_HIGH>;
	};
};

&uicr{
	// 不把gpio当作reset使用
    /delete-property/ gpio-as-nreset;

	// nfc引脚当作gpio使用
	nfct-pins-as-gpios;
};

&gpio0 {
	// 删除预留保护
	/delete-property/ gpio-reserved-ranges;
};
```

代码：
```c
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/gpio.h>
	
	// 获取单个的gpio specifier
	const struct gpio_dt_spec reset_pins = GPIO_DT_SPEC_GET(DT_PATH(zephyr_user), reset_gpios);

	// 获取复数的gpio specifier
	const struct gpio_dt_spec nfc_pins[2] = {
		GPIO_DT_SPEC_GET_BY_IDX(DT_PATH(zephyr_user), nfc_gpios, 0),
		GPIO_DT_SPEC_GET_BY_IDX(DT_PATH(zephyr_user), nfc_gpios, 1),
	};

int main()
{	
    // 设备树只包含GPIO逻辑电平。这里追加配置输入输出。
	gpio_pin_configure_dt(&reset_pins, GPIO_OUTPUT_INACTIVE);
	gpio_pin_configure_dt(&nfc_pins[0], GPIO_OUTPUT_INACTIVE);
	gpio_pin_configure_dt(&nfc_pins[1], GPIO_OUTPUT_INACTIVE);

    // 控制GPIO输出
	for (;;) {
		gpio_pin_toggle_dt(&reset_pins);
		k_sleep(K_MSEC(500));
		gpio_pin_toggle_dt(&nfc_pins[0]);
		k_sleep(K_MSEC(500));
		gpio_pin_toggle_dt(&nfc_pins[1]);
		k_sleep(K_MSEC(500));
	}
    
    return 0;
}
```

> 实际测量时，注意开发板上的空焊盘。

# 4. 在Zephyr中分配外设引脚（pinctrl）

## 4.1. 把引脚分配给外设

从第一章我们知道，Nordic的引脚基本上可以任意分配给所有外设的。在Zephyr中，外设的引脚分配大部分使用`pinctrl`进行。

```c
// 设备的引脚分配，引用pinctrl节点
&spi3 {
	status = "okay";
	cs-gpios = <&arduino_header 16 GPIO_ACTIVE_LOW>; /* D10 */
	pinctrl-0 = <&spi3_default>;
	pinctrl-1 = <&spi3_sleep>;
	pinctrl-names = "default", "sleep";
};

// 只要是用Zephyr驱动的外设，其引脚分配都在这里
&pinctrl{
	spi3_default: spi3_default {
        group1 {
            psels = <NRF_PSEL(SPIM_SCK, 1, 15)>, // P1.15
                <NRF_PSEL(SPIM_MISO, 1, 14)>,    // P1.14
                <NRF_PSEL(SPIM_MOSI, 1, 13)>;    // P1.13
        };
    };

    spi3_sleep: spi3_sleep {
        group1 {
            psels = <NRF_PSEL(SPIM_SCK, 1, 15)>, // P1.15
                <NRF_PSEL(SPIM_MISO, 1, 14)>,    // P1.14
                <NRF_PSEL(SPIM_MOSI, 1, 13)>;    // P1.13
            low-power-enable;
        };
    };
}
```

每个外设的节点内部有`pinctrl-0`，`pinctrl-1`这样的属性，指向`&pinctrl`下的子节点。通常只有`default`和`sleep`两种状态，分别处于外设处于运行或休眠时的引脚状态。

> Zephyr中的外设在main之前就已经被初始化。因此程序运行后，**使用Zephyr驱动的外设**无法`uninitial`或`disable`，取而代之的是`suspend`和`resume`。

这个其实不用太深入理解，改引脚时照葫芦画瓢即可。例如，以上代码定义了两种状态，分别叫"default"和"sleep"，两种状态的GPIO配置并不相同。当外设休眠或唤醒时，这个外设的**Zephyr驱动程序**会自动把这一组引脚状态适用。

## 4.2. 外设引脚的驱动能力、上下拉、开漏推挽

只需注意，外设的引脚也是可以配置IO口电流驱动能力、上下拉的，例如：

```c
i2c0_default: i2c0_default {
    group1 {
        psels = <NRF_PSEL(TWIM_SDA, 0, 26)>,
            <NRF_PSEL(TWIM_SCL, 0, 27)>;
        nordic,drive-mode = <NRF_DRIVE_S0D1>; // standard 0, disconnect 1
        bias-pull-up;                         // internal pull-up
    };
};
```

具体可配置的参数，大家可以Ctrl+鼠标左键，先跳转到pinctrl节点。然后再Ctrl+鼠标左键，点进"nordic,nrf-pinctrl"，查看DeviceBinding文件即可。

![image-20240416171800803](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/0418d6bf15b39793998cb2322af376b3.png)

![image-20240416172102262](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/1d81a68b42f00bc6dbe719bb476a1883.png)

## 4.3. 注意Bootloader引脚

NCS支持MCUBOOT作为bootloader。MCUBOOT也会通过设备树来配置自己的外设引脚和GPIO。当系统上电后，先执行MCUBOOT，MCUBOOT也会初始化他自己的外设）。

当MCUBOOT跳转到APPLICATION时，它不会关闭自己开启的外设。这就导致一些配置可能并未重置。

最常见的是日志串口，MCUBOOT中的日志串口开启了流控，而APPLICATION的同一个串口未开启流控。这时，因为该UART的寄存器已经在bootloader阶段被配置，把对应GPIO配置成了流控引脚。导致到了Application阶段，流控引脚无法作为普通GPIO使用。

解决方案就是要确保bootloader的设备树和application的设备树一致。MCUBOOT的设备树可以在当前工程的"sysbuild/mcuboot/"下的相关配置文件中进行修改。

# 5. LED与Button库

前面都是GPIO的基础用法。如果你需要的只是驱动LED或者Button，可以直接使用Nordic现成的驱动API。

### DK Library

文档：https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/libraries/others/dk_buttons_and_leds.html

这是Nordic为开发板（Development Kit）提供的一个简易的库，支持**4个以内的LED和Button**。其中Button已经做了去抖。

我们在开发板默认的Device Tree中看到的led和button节点就是为这个库服务的。许多简单的例程就是用它来控制GPIO。

```shell
# 需要开启的配置
CONFIG_DK_LIBRARY=y
```

### 通用应用程序框架（Common Application Framework, CAF）

[CAF](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/libraries/caf/index.html)是Nordic为商业级应用程序开发的一个框架库。里面有蓝牙、功耗管理、SMP DFU等等模组，其中当然也包含按钮和LED。

[CAF: LEDS](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/libraries/caf/leds.html)库提供了基本的GPIO LED和PWM LED功能，**并且可以配置灯效**。

[CAF: Buttons](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/libraries/caf/buttons.html)库除了提供基本的Button去抖功能以外，还支持低功耗（不用时把按钮disable掉），**并且支持矩阵键盘**。

# 6. GPIO映射（GPIO nexus）

nRF52和nRF53系列的开发板上面的GPIO插座都是兼容Ardiono UNO接口的。

因此开发板的默认设备树中有默认定义，例如`v3.0.0/zephyr/boards/nordic/nrf52840dk/nrf52840dk_nrf52840.dts`：

```
	arduino_header: connector {
		compatible = "arduino-header-r3";
		#gpio-cells = <2>;
		gpio-map-mask = <0xffffffff 0xffffffc0>;
		gpio-map-pass-thru = <0 0x3f>;
		gpio-map = <0 0 &gpio0 3 0>,	/* A0 */
			   <1 0 &gpio0 4 0>,	/* A1 */
			   <2 0 &gpio0 28 0>,	/* A2 */
			   <3 0 &gpio0 29 0>,	/* A3 */
			   <4 0 &gpio0 30 0>,	/* A4 */
			   <5 0 &gpio0 31 0>,	/* A5 */
			   <6 0 &gpio1 1 0>,	/* D0 */
			   <7 0 &gpio1 2 0>,	/* D1 */
			   <8 0 &gpio1 3 0>,	/* D2 */
			   <9 0 &gpio1 4 0>,	/* D3 */
			   <10 0 &gpio1 5 0>,	/* D4 */
			   <11 0 &gpio1 6 0>,	/* D5 */
			   <12 0 &gpio1 7 0>,	/* D6 */
			   <13 0 &gpio1 8 0>,	/* D7 */
			   <14 0 &gpio1 10 0>,	/* D8 */
			   <15 0 &gpio1 11 0>,	/* D9 */
			   <16 0 &gpio1 12 0>,	/* D10 */
			   <17 0 &gpio1 13 0>,	/* D11 */
			   <18 0 &gpio1 14 0>,	/* D12 */
			   <19 0 &gpio1 15 0>,	/* D13 */
			   <20 0 &gpio0 26 0>,	/* D14 */
			   <21 0 &gpio0 27 0>;	/* D15 */
	};
```

`gpio-map`规定了nRF52840的GPIO是如何映射到Arduino UNO接口的，基本规则为：

| Arduino引脚编号 | Arduino引脚配置 | nRF gpio controller | nRF引脚编号 | nRF引脚配置 |
| --------------- | --------------- | ------------------- | ----------- | ----------- |
| 0               | 0               | gpio0               | 3           | 0           |
| 1               | 0               | gpio0               | 4           | 0           |
| ...             | ...             | ...                 | ...         | ...         |

`#gpio-cells`表示的是GPIO的设备树配置有几个`uint32`单元，这里的2就表示`<0 0>`这样的配置单元长度是2。在Zephyr中GPIO的配置基本都是2个单元，一个代表引脚号，一个代表配置的标志位（flags）。

`gpio-map-mask`：引脚映射时忽略一些特定的bit。比如，`<&arduino_header 11 1>`，在`gpio-map`中并没有映射吗，`gpio-map`中只有`<11 0>`。而`gpio-map-mask`会和这两个cell进行**按位与运算**，从而忽略最低的6个bit，将其全部变成0。于是就能匹配上`<11 0 &gpio1 6 0>`，从而知道是P1.06。

`gpio-map-pass-thru`：在引脚匹配完成之后，把之前忽略的引脚配置传递过去。也就是把最低6bit的引脚配置传递给nRF52的驱动。

**为什么要有转接定义？**举例来说，Nordic的nRF7002EK扩展板：

![nRF7002 EK](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/fbb3c06dc66d64e255569adf6696fe9c.webp)

为什么这个扩展板可以同时兼容nRF52，nRF53和nRF91，而不用在乎这些开发板的引脚编号不同？

因为扩展板设备树的定义采用的是Arduino引脚编号。只要开发板上有Ardiono引脚定义，就可以实现兼容。见`zephyr/boards/shields/nrf7002ek/nrf7002ek.overlay`。

GPIO NEXUS的设计比较适合**开发自己的模块**的场景。你只需要定义自己的device tree bindings文件，就可以在设备树中定义自己的GPIO nexus节点。

自定义device tree bindings文件，**位置**在你的工程目录下，例如`<my_project>/dts/bindings/xxxx.yaml`。

其内容可以参考Ardiono转接头的定义，位于：`v3.0.0/zephyr/dts/bindings/gpio/arduino-header-r3.yaml`。

只要设备树和bindings文件的compatible相同，就会自动识别。

```yaml
# Copyright (c) 2019 Foundries.io
# Copyright (C) 2019 Peter Bigot Consulting, LLC
# SPDX-License-Identifier: Apache-2.0

description: |
    GPIO pins exposed on Arduino Uno (R3) headers.

    The Arduino Uno layout provides four headers, two each along
    opposite edges of the board.

    Proceeding counter-clockwise:
    * An 8-pin Power Supply header.  No pins on this header are exposed
      by this binding.
    * A 6-pin Analog Input header.  This has analog input signals
      labeled from A0 at the top through A5 at the bottom.
    * An 8-pin header (opposite Analog Input).  This has digital input
      signals labeled from D0 at the bottom D7 at the top;
    * A 10-pin header (opposite Power Supply).  This has six additional
      digital input signals labelled from D8 at the bottom through D13
      towards the top, skipping two pins, then finishing with D14 and
      D15 at the top.

    This binding provides a nexus mapping for 20 pins where parent pins 0
    through 5 correspond to A0 through A5, and parent pins 6 through 21
    correspond to D0 through D15, as depicted below:

                                 D15  21
                                 D14  20
                                 AREF -
                                 GND  -
        - N/C                    D13  19
        - IOREF                  D12  18
        - RESET                  D11  17
        - 3V3                    D10  16
        - 5V                     D9   15
        - GND                    D8   14
        - GND
        - VIN                    D7   13
                                 D6   12
        0 A0                     D5   11
        1 A1                     D4   10
        2 A2                     D3    9
        3 A3                     D2    8
        4 A4                     D1    7
        5 A5                     D0    6


compatible: "arduino-header-r3"

include: [gpio-nexus.yaml, base.yaml]

```



