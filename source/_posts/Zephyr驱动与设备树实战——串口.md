---
title: Zephyr驱动与设备树实战——串口
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2023-11-12 17:48:56
cover: null
tags:
- Nordic
- Zephyr
- DeviceTree
- UART
categories: Zephyr
sticky: 99
cnblogs:
  postId: '17828907'
  url: https://www.cnblogs.com/jayant97/articles/17828907.html
  lastPublishedAt: '2026-07-06T18:20:52+08:00'
  sourceHash: sha256:9a6f6a030384dc4a28601782ef0a9c1eac38cc8f8c8387446dbfb63ab2ddd91f
  status: imported
  postType: Article
---

> 2026.7.2更新：
>
> - 修复内存泄漏问题：在唤醒失败或RX使能失败时正确释放slab buffer
>
> 2026.2.10更新：
>
> - NCS更新到 v3.2.1，USB协议栈切换到USB Device Stack (Next)。添加更详细的USB CDC ACM介绍。
>
> 2026.1.4更新：
>
> - 新增54系列GPIO跨域使用配置，以及功耗测试
>
> 2025.7.26更新：
>
> - 新增54L15串口硬件介绍
> - 新增串口增强接收（Enhanced RX）的介绍。不再推荐使用PPI+Timer的形式进行接收数据计数。
> - 增加全新的串口例程代码并上传GitHub
>
> 2025.5.5更新：
>
> - 增加了对串口硬件的介绍
> - 增加串口API更详细的介绍与图示

# 1. 前言

之前写了一篇详细的博文，详细介绍了Zephyr设备树（DeviceTree）的语法和Zephyr驱动模型的原理。但有些读者反馈，内容还是比较泛且杂，只感觉多了一些新的语法和规则，没有感受到这设备树和驱动模型的意义所在，希望能够结合实例来讲解。

今天本文就通过串口这样一个最常见的外设，来实际感受一下Zephyr的驱动模型。本文将会以nRF Connect SDK中`zephyr/samples/hello_world`例程为基础。分别添加**串口**、**USB CDC ACM**、**低功耗串口**的功能。采用**完全相同的应用层代码**，只需要修改config和dts即可切换。

# 2. Hello world解析—printk如何输出

开发板我选择nRF52840DK。首先以`zephyr/samples/hello_world`例程为模板，创建一个新工程，我在这里把工程命名为`learning_zephyr_serial`。

## 工程目录结构

```
|--src
|  |
|  `--main.c
|--CMakeLists.txt
`--prj.conf
```

`CMakeLists.txt`中先把Zephyr作为包来导入，然后把main.c添加为源码。

`prj.conf`目前是空的，在这里可以写一些配置用来覆盖默认的Kconfig。

例程默认没使用`Kconfig`菜单文件，是因为本工程太简单，没有自己的配置项，所以不需要自己的Kconfig文件。这种情况完全等价于Kconfig文件中只写了下面的内容：

```
source "Kconfig.zephyr"
```

相当于项目中只有Zephyr的菜单，可以让我们配置Zephyr系统的配置项，以及SDK中各个module的的配置项。选择板子，编译并烧录后，打开串口，reset一下，就能看到刚启动时串口输出的hello world了。

![image-20231112183822534](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/8065d44b86cceb9ff0e8b1ab1417eda2.png)

## printk输出配置

很多新上手Zephyr的读者会有疑惑，这工程里几乎没什么代码，也没看到CONFIG和device tree文件，串口到底是怎么输出的？

其实，在我们选择板子时，板子就已经自带了默认的device tree和config文件。因此编译时采用的全部是板子和Zephyr系统的默认值，我们的工程中并没有对这些默认值进行修改。

我们可以在`build/zephyr/`目录下看到`.config`文件和`zephyr.dts`文件。这个就是项目最终编译采用的配置项和设备树。

在`.config`中，我们可以看到：

```shell
CONFIG_PRINTK=y
```

也就是启用了`printk()`输出的功能。

我们把这一行复制到prj.conf中（这个行为本身没有意义，因为默认就是y），然后就可以用**Ctrl+鼠标左键**点击这个选项，跳转到这个配置项定义的地方，就可以看到这个配置项的说明：

![image-20231112184745524](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/a2ee0a066378d3944f23bccfebfedc5f.png)

当然，你也可以在Kconfig GUI中找到这个配置项：

![image-20231112184921595](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/09529eaa5aec7ff3197ab355163f7b47.png)

> 到这里，是否对“`Kconfig`定义了一个菜单，而`prj.conf`文件是对菜单中配置项的默认值进行修改”这句话有了一定的感受呢？

## console设备与console驱动

根据此配置项的说明，我们知道`printk()`是Zephyr的一个内核服务，它可以让通过`printk()`函数打印的内容通过"console"输出。这里的console指的是一个设备，可以让Zephyr系统输入和输出字节流。

通过查看`build/zephyr/zephyr.dts`，可以看到：

```
/{
   ...
	chosen {
		...
		zephyr,console = &uart0;
		...
	};
	...
}

```

在`/chosen`节点下，有很多**属性**。Zephyr系统内核的代码在运行一些功能时，并不在乎底层的硬件具体是什么，它只从`/chosen`节点下找到对应的硬件。只要这个硬件已经在RTOS初始化之前就被驱动程序初始化了，具有Zephyr标准外设接口，那么Zephyr内核就可以操作这个硬件。

例如，要想获得这里的console设备的DeviceTree Node ID，就可以用`DT_CHOSEN(zephyr_console)`。

我们自然可以联想到，可以把console换成其他**串口设备**，就可以让日志从其他串口输出了。这里，可以参考我的另一篇随笔[《Zephyr重定向日志打印到USB串口》](https://jayant-tang.github.io/2023/11/4c8e1d7d162d/#编译USB串口例程)。

如果你只是修改设备树中的console设备，那么不管如何修改，输出日志的设备都必须是一个“串口”（在Zephyr中USB CDC ACM设备也是串口，后文会解释）。在`build/zephyr/.config`中，我们还可以看到：

```shell
CONFIG_UART_CONSOLE=y
```

原来，在当前配置下，Zephyr默认的console后端都必须是“串口”设备。

我们可以尝试把console后端改成RTT，在`prj.conf`中，添加：

```shell
CONFIG_UART_CONSOLE=n
CONFIG_RTT_CONSOLE=y
```

![image-20231112191457497](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/551a9a209c0745054d3342e2217c28c8.png)

然后就可以看到，printk()的日志从RTT中打印出来了。

对于探究心强的读者，到这里肯定又会有疑问：为什么把console后端改成了RTT，只改了config，设备树就不用改了？

关于这个问题，我想先传达出一个观点，那就是一个系统无论使用了什么样的框架，**最终一定要落实到代码**。通过在NCS中全局搜索`CONFIG_RTT_CONSOLE`和`CONFIG_UART_CONSOLE`，我们最终能找到这样的一个文件，`${NCS}/zephyr/drivers/console/CMakeLists.txt`：

```cmake
...
zephyr_library_sources_ifdef(CONFIG_RTT_CONSOLE rtt_console.c)
zephyr_library_sources_ifdef(CONFIG_UART_CONSOLE uart_console.c)
...
```

console本身作为一个中间件，也是要通过驱动程序向Zephyr提供标准console API的。在这里，CMake根据不同的CONFIG配置项，添加了不同的console驱动源码进入系统之中，进行编译。

在uart_console.c中，我们明显能看到，此驱动代码需要通过device tree来找到标准的串口设备，然后调用标准的串口API来通信。

```c
static const struct device *const uart_console_dev =
	DEVICE_DT_GET(DT_CHOSEN(zephyr_console));
```

而在rtt_console.c中，我们可以看到此代码不需要获取任何device tree的信息。因此，当我们选择RTT作为后端时，无论device tree中的`/chosen`节点中如何选择`zephyr,console`，对于RTT console驱动代码来说都是没有意义的。

## 总结

经过前面的分析，我们可以有以下结论：

首先，在Zephyr系统中有许多功能，我们可以用Kconfig的方式进行配置或裁减。

此外，Zephyr中有非常明显的“分层设计”，例如，Nordic提交nrf系列串口驱动代码，提供Zephyr标准串口API；Zephyr有console驱动代码，向更上层提供标准console API；如果console是串口驱动，它还会调用标准串口 API来把日志输出到底层串口中；由于API是标准的，因此console驱动代码并不在乎底层到底是物理串口还是USB CDC ACM设备。

前面分析了Hello world是如何通过console输出的。在Zephyr中，console主要是用来做一些字节流的传输，用来实现一些更上层的服务，例如自定义`shell`命令。而用户要开发自己的程序，肯定是需要自己直接操作串口，而不是用什么printf。

# 3. Nordic串口硬件

## UART

![image-20250505231527537](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/47b66b8aa6839171773ff5e5abf53fb5.png)



UART是最简单的硬件串口功能。图中小正方形为对外的硬件引脚，而箭头代表串口在MCU内部的输入、输出信号。

- **接收**：在串口接收已经使能（STARTRX）的状态下，从RX线来的数据会被放入RXD寄存器，并产生RXDRDY事件。​

  接收FIFO长度为6。RXD的数据被CPU读取后，立即从FIFO中把下一个数据填入RXD，并产生RXDRDY事件。（若使能流控，会在FIFO还剩4个空位时把RTS拉高以阻止对方发送）

- **发送**：在串口发送已使能（STARTTX）的情况下，向TXD写入1个字节就会发送。发送完毕后，UART产生TXDRDY事件。

这些事件都能用来触发中断，或者作为PPI信号触发其他外设的task。

## UARTE

UARTE和UART是不同的外设，但是共用了部分寄存器和电路。在使用时，这种具有相同地址的外设被称为同一个**实例（Instance）**，**不能同时使能**。

![image-20250505232121430](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/fc3805662646766f565b4b9f4c4e2c3b.png)

他们的ENABLE寄存器地址是相同的，但是使能所用的bit不同：

![image-20250505232133627](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/fcca18a4a9b88168f161c24e7088e1cc.png)

UARTE (UART with EasyDMA) 功能和UART是类似的，只不过有了EasyDMA的帮助，可以自动从RAM中取出数据发出；也可以把收到的数据直接存入RAM。无需CPU参与单个字节的收发处理，提升了效率，降低了功耗。

![image-20250505232323499](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/0a3a5712a20c3b9b9dda64a66061394e.png)

### UARTE发送逻辑

 ![image-20250505232526893](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/3b12c40231d46b93b26dffabd1d6874c.png)

1. TXD.PTR填入数据在RAM中的首地址，TXD.MAXCNT填入要发送的数据长度（nRF52840最大65535，nRF52832最大255）.
2. 使用STARTTX来启动自动的传输
3. 传输完毕后，有ENDTX事件提示
4. 中间每个字节的TXDRDY事件，CPU可以无视

> 注意：
>
> - **串口的发送功能**只在**STARTTX和ENDTX之间**有功耗，其余时间几乎不产生电流消耗
> - EasyDMA只能在RAM和外设之间传输数据，不能在RAM之间传输，也不能有FLASH参与。

### UARTE接收逻辑

![image-20250505232812582](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/4a1b1a2b4f6c7d42deed43321b23e45f.png)

1. RXD.PTR填入数据首地址，RXD.MAXCNT填入要接收的数据长度（nRF52840最大65535，nRF52832最大255）.
2. 使用STARTRX来启动自动的接收
3. 传输完毕后（指RAM中存的数据长度已经达到了MAXCNT），有ENDRX事件提示
4. 中间每个字节的RXDRDY事件，无需再使能中断（从而降低功耗，提高CPU效率）

特别地，RXD.PTR具有双缓存（影子寄存器）。也就是说，不用等到传输完成，只需在第一次接收开始后（RXSTARTED），就马上给RXD.PTR写入下一次要用的buffer首地址。这样下次传输时，就能立刻用上新的buffer。便于应用层实现**双buffer**。

> 注意：
>
> - 串口在接收状态（STARTRX）会有功耗，有几百uA。因此需要避免待机时一直开着RX。
> - UARTE只有在接收完毕（buffer满）时才会产生中断。本身没有空闲帧中断，或者说超时机制。需要其他外设辅助实现。



## nRF54系列UARTE硬件新功能

以nRF54L15为例，有以下功能更新：

### （1） 4Mbps串口

在默认低频时钟域（16MHz）的情况下，串口的波特率可以由寄存器设置，如下最高为1Mbps。

![image-20250726225627521](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/894689018edad6a0629abdbdda936465.png)

但是，nRF54L15的 **UARTE00** 位于MCU PowerDomain，其时钟频率为128MHz：

![image-20250726225904621](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/32231108676d0bbe54cf8b10b61a32ea.png)

这时，串口的实际波特率就和寄存器中的定义不相同，实际的公式手册中已经给出。

但是我们做软件开发时无需关心这部分，因为在54L15芯片的原始设备树dtsi中：

```
uart00: uart@4a000 {
    compatible = "nordic,nrf-uarte";
    reg = <0x4a000 0x1000>;
    interrupts = <74 NRF_DEFAULT_IRQ_PRIORITY>;
    clocks = <&hfpll>;
    status = "disabled";
    endtx-stoptx-supported;
    frame-timeout-supported;
};
```

其已经指明了使用的是hfpll时钟。

然后，在最新（目前为NCS v3.0.2）的UARTE的驱动代码`uart_nrfx_uarte.c`中，已经自动考虑了低频时钟和高频时钟的情况：

```c
/* When calculating baudrate we need to take into account that high speed instances
 * must have baudrate adjust to the ratio between UARTE clocking frequency and 16 MHz.
 * Additionally, >1Mbaud speeds are calculated using a formula.
 */
#define UARTE_GET_BAUDRATE2(f_pclk, current_speed)					\
	((f_pclk > NRF_UARTE_BASE_FREQUENCY_16MHZ) && (current_speed > 1000000)) ?	\
		UARTE_GET_CUSTOM_BAUDRATE(f_pclk, current_speed) :			\
		(NRF_BAUDRATE(current_speed) / UARTE_GET_BAUDRATE_DIV(f_pclk))
```

因此我们在软件上是感知不到这个差别的，只需正常配置我们需要的波特率即可。需要4M就配置`current-speed = <4000000>`；需要115200就配置`current-speed = <115200>`。

### （2）支持4至9bits 帧

![image-20250726231953984](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/6567df1a02e316811b9c173667ee9705.png)

数据帧支持被配置为4bit ~ 9bit。

其中，当配置为9bit时，第9个bit是地址位。当其为1时，代表前8个bits是地址；当其为0时，代表前8个是数据。

且9bit模式下，只有先收到地址和ADDRESS寄存器匹配的第一个地址包时，才会接收后面的数据包。否则忽略所有收到的串口数据。

### （3）帧超时中断

![image-20250726232649715](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/b893b6f7b506da554c2fb02217dda58c.png)

帧超时中断，或者说空闲帧中断，指的是：

- 当连续一定时间没有收到串口数据时，就认为传输已经结束
- 此时不再等待DMA缓冲存满，而是直接产生DMA传输完成中断
- 应用层可以及时把数据取出进行处理

之前的nRF52和53系列是没有这个功能的，需要操作系统软定时器进行计时，把一个timeout分成5份设定k_timer周期。如果每次软定时器到期，串口已经收到的数据量没有增长，那么就说明串口空闲了。这时由驱动层软件主动结束串口接收。这就不如nRF54系列UARTE硬件自带空闲帧超时来的方便。

只有**异步串口**才需要这个功能。因为**阻塞**和**基于中断**的串口都是按字节实时同步接收串口数据的。

![image-20250726233308626](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/54c73f2e0da701646bbed68f13480de9.png)

空闲帧中断最大超时时间为 2^10 - 1= 1023 bits。在115200波特率下，大约是8.88ms。而使用软定时器的方式，可以设置更长时间。

nRF54L15的设备树默认开启了空闲帧的功能：

```
&uart20 {
    status = "okay";
    frame-timeout-supported;
};
```

对于支持帧超时中断的串口外设，就直接使用这个功能即可。不要删除这个属性。

异步串口初始化时，通过`uart_rx_enable(dev, buf, len, timeout)`打开RX时，传入的timeout值（单位：微秒）会经过如下处理：

- 如果开启了空闲帧中断，则在应用层传入的 timeout 和 1023 bits 之中选取时间更短的一个，设置到 FRAMETIMEOUT 寄存器中
- 如果没开启空闲帧中断，则用k_timer实现此功能，超时值为函数传入的timeout



# 4. Zephyr标准串口API

上一节以nRF52系列的串口外设为例介绍了硬件部分，Nordic其他产品的串口基本也是一致的。

本节介绍Zephyr中的串口API。

Zephyr中的串口API分为**[阻塞（Polling）](https://docs.zephyrproject.org/latest/hardware/peripherals/uart.html#uart-polling-api)**、**[基于中断（Interrupt-driven）](https://docs.zephyrproject.org/latest/hardware/peripherals/uart.html#uart-interrupt-api)**、[**异步（Asynchronous）**](https://docs.zephyrproject.org/latest/hardware/peripherals/uart.html#uart-async-api)三种。

Zephyr串口API是一套软件接口，与硬件细节无关。除了Nordic的UART/UARTE硬件可以用这套接口，其他厂商的串口实现也可以支持这套接口。甚至我们后面会介绍到的USB虚拟串口，也支持这套接口。这里给出[Zephyr标准串口API文档](https://docs.zephyrproject.org/latest/hardware/peripherals/uart.html)，供参考。



> NCS中的例程太多，对于不熟悉的人来说，随便复制代码，很有可能出现：代码里用的是一种API，但CONFIG使能的却是另一种API的情况，最终导致程序无法运行。
>
> 一般来说，同一个串口实例，基于中断的和异步的API是不能同时使用的。但是阻塞的API可以和前两者中的一种混用。

## 阻塞

基于阻塞的API是最简单的API。

- `uart_poll_in()`：读取时，只读一个字节。有就返回0，无就返回-1，不阻塞；
- `uart_poll_out()`：发送时，只发一个字节。发送完毕后才返回，阻塞行为。

## 基于中断

首先声明，Zephyr串口API是一套软件接口，**与硬件细节无关**。基于中断的API只是抽象地认为有串口外设**应当有**发送ready中断和接收ready中断。具体如何映射到硬件？完全由厂商提供的驱动代码实现，不需要应用开发者实现。这也是USB虚拟串口也能使用这套API的原因。

NCS中，使用串口中断API的例程很多。**但是它们在应用层编写callback函数的方式五花八门，与应用层本身的功能混在一起，这对于初学者来说容易抓不到重点**。这也侧面说明，中断API适合添加一些应用层自定义的东西。因此我在这里总结出基于中断的API的使用流程，方便开发者结合代码进行观看。

以下为流程：

1. 开始时，用`uart_irq_callback_set()`函数设置好“应用层的”中断回调函数，这个函数会在串口ISR中根据情况被串口驱动程序调用。然后，开启`uart_irq_rx_enable()`，使能接收。
2. 要发送时，先准备好要发送的数据（首地址和长度），然后`uart_irq_tx_enable()`开启发送中断。
3. 发生中断，进入预先设置好的回调函数时，先用`uart_irq_update()`更新中断状态，再用`uart_irq_is_pending()`判断是否有中断（以防是别处误调用了该回调函数）。再之后用`uart_irq_tx_ready()`和`uart_irq_rx_ready()`来判断是发送中断还是接收中断。
4. 如果是接收中断，**在中断里**用`uart_fifo_read()`循环读取，每次读取1个字节（Nordic的驱动实现是只读1个字节），直到返回值为0（表示缓存里已无数据）。
5. 如果是发送中断，说明发送器已经ready，**在中断里**用`uart_irq_tx_fill()`，把前面准备好要发送的数据传入，即可发送。

>注意：
>
>- 不要在中断callback里进行耗时的处理和阻塞行为。善用queue和work queue。
>- `uart_fifo_read()`和`uart_fifo_fill()`只能在这个中断callback函数内部调用

##  异步

异步API是本文介绍的重点，它带有DMA，因此可以让数据传输时，不影响CPU的运行。但是它的配置最复杂，功能最强大。

### 异步发送

![image-20250506000430849](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/b161ff61daac34105ac418a0d8ff86b4.png)

调用`uart_tx(dev, *buf, len, timeout)`，给定首地址和长度即可，函数不阻塞。Timeout是给流控用的，如果输出被对方的流控阻止，自己能等待多久，如果没有流控就不用在意。

发送过程由驱动层和硬件自动处理。

发送完毕后，回调函数里会收到**UART_TX_DONE**事件。

> 注意：
>
> 1. 注意发送数据buffer的生命周期，不能是局部变量
> 2. 如果buffer的地址不属于RAM，Nordic的驱动程序会先自动执行一个拷贝到RAM中的动作。因为硬件不支持RAM以外的地方到外设的DMA。
> 3. uart_tx这个行为是低功耗的。只要不在发送，就没有发送行为相关的功耗。无需disable串口。

在DMA传输期间，如果再次执行uart_tx()，函数会返回`-EBUSY`错误码：

![image-20250727000130872](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/0c8c3cc39029da6d8d7da1eeafbabc38.png)

后续例程会展示如何实现发送缓冲线程。

### 异步接收

![image-20250506000958480](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/617d9c8e5b5060c0dcc1e9f741850e20.png)

1. 用`uart_rx_enable(dev, *buf, len, timeout_us)`来首次使能接收。给定Buffer和长度。Buffer收满以后会产生UART_RX_RDY事件。
2. Timeout是空闲超时机制。在至少收到1个字节之后，即使buffer未满，如果超时，也会产生`UART_RX_RDY`事件。这是为了方便收取一个小于buffer长度的包的情况。单位是微秒。timeout时间设为SYS_FOREVER_US会关闭这个机制。
3. 如果buffer未满，下次数据接收会继续填充在此buffer内。如果buffer已满，紧接在UART_RX_RDY事件之后，会产生UART_RX_BUF_RELEASED事件。告知应用层，一开始的buffer已经不再使用，可以释放。
4. 异步API也提供双Buffer机制。当每次接收开始时，驱动层会立即产生UART_RX_BUF_REQUEST事件。向应用层请求第二个buffer。应用层有两个选择：
   - 用uart_rx_buf_rsp(dev, *buf, len)来设置第二个buffer。当第一个buffer满时，驱动层自动开始用第二个buffer。
   - 无视这个请求。那么这次接收完毕时，整个接收会被disable。需要再次enable才能开始接收。

![image-20250506000854098](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/5d9b9ad4db0201e8f1dc44ae7342d418.png)

## Zephyr串口驱动

无论是阻塞、基于中断、还是异步API。它们都是由Nordic的驱动程序提供的。

当`CONFIG_SERIAL=y`，就使能了Zephyr的串口驱动。Zephyr系统内的CMake规则会自动把相关MCU的串口驱动编译进去。

而Nordic是提供了三种驱动的：

![image-20250506001935633](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/2d16fa1b03901a6cfd6347d0d8b5208b.png)

使用时，注意在device tree中设置正确的compatible，来选择正确的驱动。

![image-20250506001833817](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/2753bd1faeeebb2e7251143b27988756.png)

> **设备树的compatible和驱动程序是如何对应的？**
>
> ​    设备树的compatible属性，在编译阶段会被转换成C语言命名规范允许的形式（特殊符号全变为下划线），如`nordic_nrf_uarte`。
>
> ​    每个驱动程序会用自己的方法遍历设备树中所有compatible与自己相匹配的节点。然后基于这个节点的信息来初始化硬件外设。
>
> **uarte和uarte2有什么区别？**
>
> ​    见`zephyr/driver/serial/CMakeLists.txt`
>
> ```cmake
> if (CONFIG_UART_NRFX_UARTE)
>   if (CONFIG_UART_NRFX_UARTE_LEGACY_SHIM)
>     zephyr_library_sources(uart_nrfx_uarte.c)
>   else()
>     message(DEPRECATION
> 	    "Do not set CONFIG_UART_NRFX_UARTE_LEGACY_SHIM=n as this option is deprecated.")
>     zephyr_library_sources(uart_nrfx_uarte2.c)
>   endif()
> endif()
> ```



# 5. 异步串口代码示例

示例代码：[Jayant-Tang/learning_zephyr_serial: An example that shows how to use zephyr Async UART](https://github.com/Jayant-Tang/learning_zephyr_serial)

读者可以下载示例代码后，对照阅读本文

> 【注意】
> 本文基于NCS v3.0.2。若读者使用v2.4.2或以下版本，代码中的
>
> ```c
> case UART_RX_BUF_RELEASED:
> 	k_mem_slab_free(&uart_slab, (void *)evt->data.rx_buf.buf);
> 	break;
> ```
>
> 需要改回：
>
> ```c
> case UART_RX_BUF_RELEASED:
> 	k_mem_slab_free(&uart_slab, (void **)&evt->data.rx_buf.buf);
> 	break;
> ```
> 因为版本升级后`k_mem_slab_free`的实现不同，参数从二级指针变为了一级指针。

## src/app_uart/app_uart.c

### 初始化

首先是获得device，这里的方法是用aliases别名来获取：

```c
/* serial device */ 
#define UART_INST DT_ALIAS(learning_serial)
static const struct device *uart_dev = DEVICE_DT_GET(UART_INST);
```

因为在不同板子的设备树中，都已经选好了对应的串口：

`nrf54l15dk_nrf54l15_cpuapp.overlay`:

```
/{
    aliases{
        learning-serial = &uart20;
    };
};
```

`nrf52840dk_nrf52840.overlay`:

```
/{
    aliases{
        learning-serial = &uart0;
    };
};
```

然后是初始化时，注册异步回调函数，并开启串口接收。这里除了device结构体指针之外，还有两组配置。一个是接收缓存及其长度、一个是超时时间：

```c
uart_rx_enable(uart_dev, buf, BUF_SIZE, RX_INACTIVE_TIMEOUT_US);
```

接收缓存用的是Zephyr的[memory slab](https://docs.zephyrproject.org/latest/kernel/memory_management/slabs.html#memory-slabs)功能。代码中用`K_MEM_SLAB_DEFINE`定义了几块静态的缓存区域，可以用allocate和free来进行内存块的分配和释放操作。相当于是一个私有的动态内存区域。在`main()`函数中，先取出了一块内存，然后传入`rx_enable`作为接收缓存。

超时时间，指的是串口空闲一定时间，没有新数据来，就直接认为接收完毕。即使DMA接收缓存还未满，也要产生空闲事件，并直接调用callback。**这里为了演示，设置为1秒超时**。

> 这个超时功能，一般情况下是用软定时器（k_timer）实现的。
>
> 但是，对于nRF54L15这种串口硬件本身支持超时帧中断的情况，会使用硬件本身的超时功能。这时，超时时间的最大值就是UARTE硬件帧中断支持的最大时间。比如54l15的串口，空闲帧的最大值为10个bit宽度，在115200波特率下大约为8.9ms。因此，这种情况下设置所有超过8.9ms的时间都会被缩短到8.9ms。

### 串口回调

在回调函数中，每次接收缓存已满，或者达到了超时时间，就会产生`UART_RX_RDY`事件。在事件结构体中，`buf`是缓存的首地址，`offset`是本次收到的数据在缓存中的位置，`len`是本次收到的数据的长度。因此，本次接收到的数据的真实首地址为：

```c
uint8_t *p = &(evt->data.rx.buf[evt->data.rx.offset]);
```

每次接收缓存满时，串口rx驱动代码会向应用层申请新的接收缓存，即`UART_RX_BUF_REQUEST`事件。这时我们从memory slab中分配一块新的内存给它即可。

当串口驱动获得了新的接收缓存时，它也会向应用层申请释放掉旧的接收缓存，即`UART_RX_BUF_RELEASED`事件。这时我们用memory slab的free函数将其释放即可。

> 这里有一些小细节：
>
> 1. 回调函数的形参evt，在call stack中上一层的驱动代码里是一个局部变量。在回调函数返回后，evt会被释放。因此这里如果要实现回环，需要拷贝一份到静态内存中。即`static uint8_t buf[128]`。
>
> 2. 如果某一次接收到了很多数据，超出了buffer的剩余空间。那么这次收到的数据就会被分成两部分，产生两次接收回调。这也意味着，我们必须把接收到的数据看作是“字节流”而不是“包”。开发者应该自己实现字节流解包处理函数，例如：
>    ```c
>    for (int i = 0; i < evt->data.rx.len; i++){
>        bytes_to_packet(p[i]); // 开发者自行实现解包函数
>    }
>    ```
>
>    main.c中已经实现了这一点。
>
> 3. 回调函数实际上运行在中断服务函数内部，因此不要做一些阻塞的行为。如果真的有计算量大的任务，可以把任务提交到[Workqueue Threads](https://docs.zephyrproject.org/latest/kernel/services/threads/workqueue.html)。这样你就能把耗时的任务从**特权模式**移动到**用户模式**，也就是从中断内部移动到线程中。

### 串口接收线程

串口接收到数据时，将数据拷贝并通过消息队列发送到RX线程。然后执行应用层的回调函数。再之后free掉申请的内存。

### 串口发送线程

应用层要发送数据时，数据先被拷贝并通过消息队列发送到TX线程，然后进行发送。线程会等待发送完毕，然后free掉申请的内存

## main.c

通过`app_uart_rx_cb_register()`注册回调函数。当串口收到数据时，回调函数会**在RX线程中被执行**。

要发送数据时，执行`app_uart_tx()`。此函数不阻塞且会拷贝数据。因此可以从ISR或Thread中调用，也可以传入局部变量。

收到的串口数据是字节流而不是包。因此通过有限状态机实现了串口数据流解包函数，以连续的CRLF（`\r\n`）为分界，进行数据的解包。



## 异步串口配置

`prj.conf`

```shell
# use RTT as console
CONFIG_USE_SEGGER_RTT=y
CONFIG_RTT_CONSOLE=y
CONFIG_UART_CONSOLE=n

# enable logging
CONFIG_LOG=y
CONFIG_LOG_BACKEND_RTT=y
CONFIG_LOG_MODE_DEFERRED=y

CONFIG_SEGGER_RTT_MODE_NO_BLOCK_SKIP=y

# use ASYNC uart API
CONFIG_SERIAL=y
CONFIG_UART_ASYNC_API=y

# need k_malloc
CONFIG_HEAP_MEM_POOL_SIZE=4096
```

首先，把console改为RTT，防止日志和我们的串口数据混在一起。

`CONFIG_SERIAL=y`的作用是，使能Zephyr标准串口驱动；`CONFIG_UART_ASYNC_API=y`使能了异步API。这两项都是Zephyr的串口配置项，来自于`${NCS}/zephyr/drivers/serial/Kconfig`。

由于我们需要用到动态内存分配，因此这里要设置HEAP大小`CONFIG_HEAP_MEM_POOL_SIZE=4096`。

`boards/<board>.conf`：

```
CONFIG_UART_xx_ASYNC=y
CONFIG_UART_NRFX_UARTE_ENHANCED_RX=y
```

`CONFIG_UART_xx_ASYNC=y`来自于Nordic的配置`${NCS}/zephyr/drivers/serial/Kconfig.nrfx`。Zephyr只提供了全局的串口API选择（异步、中断、阻塞）。但是Nordic允许开发者给不同的串口使用不同的API。因此这里需要给特定的串口实例单独启用ASYNC API。

## 强化RX功能

上述第二配置，**对性能和功耗影响很大**。虽说串口API是异步的，但底层驱动的实现却有很多变化。当一个外设通过DMA传输数据时，通常来说是DMA缓存写满了，才产生中断，然后把整个缓存传给应用层。但别忘了，我们的异步串口有**空闲超时功能**，如果DMA缓存还没有写满，但因为串口一直没有收到新的数据，超时了，需要立即把目前已经收到的数据传到应用层。这种情况下，**如何才能知道目前已经接收了多少个字节数据呢？**

纯软件的方法就是，每收到一个字节就产生中断，在中断服务函数里，通过软件的方式+1，这也是大多数普通的单片机的做法。**如果你不添加最后两行CONFIG配置，那么`uart_nrfx_uarte.c`驱动就会采用这种方法**。但是当串口速率很高时（如1Mbps），每一个字节都产生中断一定会大量占用CPU资源，效率极低。

因此这里需要增强版RX（Enhanced RX）功能。在底层驱动代码中，当`CONFIG_UART_NRFX_UARTE_ENHANCED_RX`开启时，单个字节的中断不会被使能：

![image-20250727044332567](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/fe23eea8c563759f1a57c14b8ab88644.png)

这就确保了不会产生单个字节的中断，从而影响CPU性能。

另一方面，在底层驱动的RX enable函数中，使能了连接FRAMETIMEOUT event和 STOP_RX task的SHORT寄存器：

![image-20250727044930863](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/1bd7e9bcb8d16788c65066091e036adc.png)

> SHORT寄存器（意为短路）就是可以让一个外设的event自动触发该外设的一个task，无需CPU参与。当FRAME_TIMEOUT发生时，外设自动执行STOP_RX。

对于nRF52系列这种不支持FRAME_TIMEOUT的老系列。超时是靠k_timer软定时器实现的，在rx enable的函数内，把超时时间分成了5份：

```c
async_rx->timeout_us = timeout;
async_rx->timeout_slab = timeout / RX_TIMEOUT_DIV; // RX_TIMEOUT_DIV = 5
```

底层驱动在RX Started中断里，开始计时：

![image-20250727045514187](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/3237942a0bf438792701ab9bc7ae34b0.png)

如果连续5次都超时，则软件触发STOPRX中断：

```c
if (async_rx->idle_cnt == (RX_TIMEOUT_DIV - 1)) {
    nrf_uarte_task_trigger(uarte, NRF_UARTE_TASK_STOPRX);
    return;
}
```

这和前面的SHORT寄存器是一个思路。

不论是前面二者中的哪种情况，当STOP RX中断发生时，就会进入底层驱动的`endrx_isr()`。在这里读取DMA的AMOUNT寄存器，就可以在DMA缓存区未满的情况下，获取串口已经收到的字节数了。

## 硬件计数器（不再推荐）

在之前版本的文章中，我介绍过Timer+PPI的方式：

Nordic的单片机有独特的功能—— PPI (Programmable peripheral interconnect)。简单来说，就是每个外设都有许多event和task寄存器。event寄存器可以产生中断让CPU去处理；CPU也可以去写task寄存器让外设去执行某些工作。前面介绍过，SHORT寄存器可以把同一个外设的event和它自己的task连接起来。

而PPI可以把两个不同外设的event寄存器和task寄存器连接起来，实现**自动联动，而无需CPU处理**。

如此一来，Nordic串口驱动可以把一个Timer配置为计数器模式（Counter Mode），并且把他的COUNT TASK与串口的接收到单个字节的EVENT通过PPI连接起来。这样计数器就可以自动记录收到了多少个字节。当接收超时的时候，直接从counter中读取计数即可。

在nRF52840上，可以这样配置，将timer2用作uart0的计数器：

```
CONFIG_UART_0_ASYNC=y

CONFIG_UART_NRFX_UARTE_ENHANCED_RX=n

CONFIG_UART_0_NRF_HW_ASYNC=y
CONFIG_UART_0_NRF_HW_ASYNC_TIMER=2

CONFIG_NRFX_TIMER2=y
```

在nRF54L15上，不推荐用硬件计数，请直接使用`CONFIG_UART_NRFX_UARTE_ENHANCED_RX=y`，这里也不给出配置，经过我实测：

- 54L15使用硬件计数，开启FRAMETIMEOUT时，出现bug，FRAMETIMEOUT不生效，必须收到大于DMA长度的包才能产生中断；
- 54L15使用硬件计数，关闭FRAMETIMEOUT，k_timer实现超时功能。出现bug，收到的数据包最后2个字节完全错误，且尾部还会再增加一个随机错误字节。

## 异步串口设备树

我们并不需要额外修改设备树，直接采用默认值即可。我们这里只是给串口起一个别名，方便不同MCU平台统一代码：

```
/{
    aliases{
        learning-serial = &uart20;
    };
};

&uart20 {
    status = "okay";
};

```

至于这个串口的具体配置，我们可以直接查看编译后的完整设备树，位于`build/<application_name>/zephyr/zephyr.dts`：

```
uart0: uart@40002000 {
			compatible = "nordic,nrf-uarte";
			reg = < 0x40002000 0x1000 >;
			interrupts = < 0x2 0x1 >;
			status = "okay";
			current-speed = < 0x1c200 >;
			pinctrl-0 = < &uart0_default >;
			pinctrl-1 = < &uart0_sleep >;
			pinctrl-names = "default", "sleep";
		};
```

主要属性介绍：

- `reg = < 0x40002000 0x1000 >`：芯片自带的属性，外设的地址

- `compatible = "nordic,nrf-uarte"`：此处选择了uarte的驱动而非uart驱动。因此最终编译时用的代码是uart_nrfx_uarte.c而非uart_nrfx_uart.c
- `status = "okay"`：驱动代码自动初始化外设时，只会初始化状态为`"okay"`的节点。
- `current-speed = < 0x1c200 >`：波特率，也就是写十进制`current-speed = < 115200 >`



## 硬件连接

![image-20221209144123203](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/e1f8ca33f0a8e621f288179dd9ab2173.png)

Nordic开发板的串口0默认GPIO都是在板子上直接连接到Jlink上，然后Jlink把串口转发到USB上，因此电脑上看到的是Jlink的USB串口。

右上角开关，nRF Only是只给单片机核心电路供电，外围LED、Jlink等都不供电，用于测量功耗。因此应该拨到DEFAULT档位。

板载Jlink，USB插左边即可。左下角电源开关打开。

## 异步串口代码运行

烧录好程序后，分别打开RTT和串口。从串口发送hello（包含回车+换行），串口就会把hello回环打印出来。并且RTT的日志中会显示收到了7字节，发送了7字节：

![image-20250727053522774](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/d4f6f910dc63966549e3cda4036916b6.png)

> - 不要用VS Code里面nRF插件提供的这个串口终端。在里面按下回车不是`\r\n`，无法形成完整数据包。可以用nRF Connect for Desktop里面的串口助手。
> - 如果是52840，前面设置了1s超时，hello就会在发送后1s回环打印出来。如果是54L15，不采用这个超时，而是采用空闲帧中断，hello会在1023个bit时间内打印出来（约8.9ms）。

![image-20250727054355433](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/befde71fdc0717db731e044fb030feb6.png)

如果一次性发送大量数据，则我们可以看到产生了多个接收完毕中断。由于我们的`CONFIG_APP_UART_RX_DMA_BLOCK_SIZE`设置的是64，因此每收到64字节，串口驱动就会重新申请一块新的内存。

而应用层`main.c`中，已经实现了解包函数，因此最终是按照一整包回环发送回来的。



# 6. 休眠与串口低功耗

要实现系统低功耗的本质就两件事：

- CPU在无事可做时进入low-power standby状态（ARM的WFE指令或者WFI指令）。
- 除了CPU以外的外设，不使用时，直接disable

前者是Zephyr自带的功能，当IDLE线程之外的其他线程都阻塞等待或sleep时，IDLE线程会自动让CPU进入低功耗休眠模式。之后，CPU被RTC或者串口、GPIO等中断唤醒时，会自动向后执行代码。

后者就是需要代码来控制，在不用的时候把串口关掉。

> 除了System ON状态的CPU IDLE之外，Nordic还支持System OFF，直接关闭CPU和所有外设。可以称之为深度睡眠。这种情况只能被GPIO或reset pin唤醒（54系列也可以被GRTC唤醒）。并且唤醒后必定从reset handler开始执行。

## Zephyr设备电源管理（PM_DEVICE）

Zephyr的外设是被驱动程序自动初始化的，这发生在main()函数之前。因此我们基本上看不到Zephyr驱动提供`init`或者`uninit`这种函数。因为我们不需要在应用层初始化或者关闭某个外设。

取而代之的是Zephyr提供了一套电源管理机制，需要使能:`CONFIG_PM_DEVICE=y`。可以操作每个外设的device指针，使其挂起或者恢复。

比如说，用串口打印日志时，这个串口是被console驱动管理的。console并没有开放API给应用层开启或者关闭串口。但是，应用层可以用Zephyr的设备电源管理来控制这个串口：
```c
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/pm/device.h>
const struct device *console_dev = DEVICE_DT_GET(DT_CHOSEN(zephyr_console));

	// 关闭串口
    pm_device_action_run(console_dev, PM_DEVICE_ACTION_SUSPEND);
	...
        
    // 打开串口
    pm_device_action_run(console_dev, PM_DEVICE_ACTION_RESUME);
	...
```

休眠时，首先Zephyr驱动会负责把外设本身关闭。其次，Zephyr驱动还会把外设分配的GPIO配置成提前预设好的Sleep模式，也就是设备树里预设好的模式：

```
&uart0 {
    status = "okay";
    current-speed = <115200>;
    /delete-property/ hw-flow-control;
    zephyr,pm-device-runtime-auto;
	pinctrl-0 = <&uart0_default>;
	pinctrl-1 = <&uart0_sleep>;
	pinctrl-names = "default", "sleep";
};

// write pinctrl again to remove RTS and CTS pin
&pinctrl {
    uart0_default {
        group1 {
			psels = <NRF_PSEL(UART_TX, 0, 6)>;
		};
		group2 {
			psels = <NRF_PSEL(UART_RX, 0, 8)>;
			bias-pull-up;
		};
    };

    uart0_sleep {
        group1 {
			psels = <NRF_PSEL(UART_TX, 0, 6)>,
				<NRF_PSEL(UART_RX, 0, 8)>;
			low-power-enable;
            // bias-pull-up;
		};
    };
};
```

> 当你想控制串口空闲态是低电平还是高电平时，就是在pinctrl的sleep引脚组配置。

我们可以看出，PM_DEVICE的设计目标是提供API，**让应用层负责管理**外设的开启或者关闭。

## Zephyr运行时设备电源管理

Zephyr还提供了自动的外设功耗管理，即`PM_DEVICE_RUNTIME`。需要通过`CONFIG_PM_DEVICE_RUNTIME=y`开启。

这种情况下，就不需要应用层来控制外设的开关了。每次应用层要操作外设时，驱动层会利用PM子系统对引用计数+1；操作完毕后，引用计数-1。当引用计数等于0时，PM子系统会负责执行 `PM_DEVICE_ACTION_SUSPEND` 或者 `PM_DEVICE_ACTION_RESUME`。

![image-20250802145845580](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/c8ba696e6e8be37c5dbf85f12198c08a.png)

除了要开启`CONFIG_PM_DEVICE_RUNTIME=y`之外，还要给对应的设备初始化运行时电源管理的功能，以下两种方法二选一：

- 给对应的device执行`pm_device_runtime_enable()`
- 在设备树节点内增加一条`zephyr,pm-device-runtime-auto;`的属性。

## 例程低功耗代码解析

`app_uart.c`里面提供了两个休眠相关的函数：

```c
int app_uart_sleep(void)
{
    int err;

#if !IS_ENABLED(CONFIG_PM_DEVICE_RUNTIME) && !IS_ENABLED(CONFIG_UART_ASYNC_ADAPTER)
    k_sem_reset(&rx_disabled_sem);
#endif

    err = uart_rx_disable(uart_dev);
    if (err) {
        LOG_ERR("Failed to disable RX: %d", err);
        return err;
    }

#if !IS_ENABLED(CONFIG_PM_DEVICE_RUNTIME) && !IS_ENABLED(CONFIG_UART_ASYNC_ADAPTER)
    err = k_sem_take(&rx_disabled_sem, K_MSEC(RX_DISABLE_TIMEOUT_MS));
    if (err) {
        LOG_ERR("Timed out waiting for RX disabled: %d", err);
        return err;
    }

    err = pm_device_action_run(uart_dev, PM_DEVICE_ACTION_SUSPEND);
    if (err) {
        LOG_ERR("Failed to suspend device: %d", err);
        return err;
    }
#endif /* !CONFIG_PM_DEVICE_RUNTIME */ 

    return 0;
}

int app_uart_wakeup(void)
{
    uint8_t *buf;
    int err;

#if !IS_ENABLED(CONFIG_PM_DEVICE_RUNTIME) && !IS_ENABLED(CONFIG_UART_ASYNC_ADAPTER)
    err = pm_device_action_run(uart_dev, PM_DEVICE_ACTION_RESUME);
    if (err) {
        LOG_ERR("Failed to resume device: %d", err);
        return err;
    }
#endif /* !CONFIG_PM_DEVICE_RUNTIME */

    err = k_mem_slab_alloc(&uart_slab, (void **)&buf, K_NO_WAIT);
    if (err) {
        LOG_ERR("Failed to allocate RX buffer: %d", err);
        return err;
    }

    err = uart_rx_enable(uart_dev, buf, BUF_SIZE, RX_INACTIVE_TIMEOUT_US);
    if (err) {
        LOG_ERR("Failed to enable RX: %d", err);
        k_mem_slab_free(&uart_slab, buf);
        return err;
    }
    return 0;
}
```

### `CONFIG_PM_DEVICE_RUNTIME=n`的情况

休眠时：

1. 首先，调用`uart_rx_disable()`：这会清理Zephyr中所有与UART_RX有关的资源（定时器、buffer等）。
3. **用信号量等待`UART_RX_DISABLED`事件**（超时5ms）：当串口驱动的RX真正被关闭（DMA停止、定时器停止），回调函数中会在`UART_RX_DISABLED`事件下释放此信号量，代表RX成功关闭。
4. 最后`pm_device_action_run(uart_dev, PM_DEVICE_ACTION_SUSPEND)`，从 Zephyr 驱动的层面挂起串口。硬件上，这代表 UART 外设被 disable 掉。

恢复时：

1. 先`pm_device_action_run(uart_dev, PM_DEVICE_ACTION_RESUME)`恢复串口
2. 然后按照正常流程申请RX buffer并开启RX

### `CONFIG_PM_DEVICE_RUNTIME=y` 的情况

开关 RX 时，会自动加减引用计数（Usage Count）；开始发送时，引用计数+1，发送完毕时，引用计数-1。
因此，只需调用`uart_rx_disable()`，满足 “RX disable” 且 “当前没有 TX 行为”，PM Runtime 模块就会自动调用`pm_action_xxx()`函数来挂起串口。应用层就无需另外控制了。

> 补充：对于SPI/QSPI主机、I2C主机等场景，所有通信一定由主机发起，它们的 Zephyr 驱动基本上都支持`CONFIG_PM_DEVICE_RUNTIME=y`。
>
> 只需在对应的设备树节点中添加：`zephyr,pm-device-runtime-auto;`就能启用。在传输（transport）前后，PM Runtime 模块会自动 Resume/Suspend 来进行功耗控制。
>
> 并且这个是多线程安全的，如果有多个软件模块都用到了这个外设，一定会在引用计数（Usage Count）减为0的时候才会挂起外设。

## 实测串口低功耗休眠功能

本工程是否开启`CONFIG_PM_DEVICE_RUNTIME`没有影响，结果相同。

nRF52840DK连接方式：

![image-20250802152806259](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/ec0b40219d3dbfbf8a00641f44938b10.png)

nRF54L15DK连接方式：

![image-20250802153317606](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/61f16d8b88bc7f7528d0b1820e9cd02f.png)

**52840DK：**

- 按button1进入休眠
- 按button2退出休眠

功耗：

![image-20250802153612494](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/450a17004249ea1bcc33e0f08d5fe6f2.png)

![image-20250802153653735](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/5edac99904281fc12335f46cb7f48f03.png)

> 注：52840手册标注system ON, CPU IDLE的电流为2.35uA



**54L15DK：**

- 按button0进入休眠
- 按button1退出休眠

功耗：

![image-20250802153818504](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/3ad100bad01b9ef6436c5fcb9ad7d7e8.png)

![image-20250802153859464](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/4f75d321684bb78231cf558b8602bb37.png)

> 注：54L15手册标注，3V条件下，System ON, Wake on pin, 256 KB RAM retained情况下CPU IDLE的电流为3uA.

# 7. nRF54系列GPIO跨域使用

## 电源时钟域

以nRF54L15为例：

![image-20260104003405320](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/b103504c883e6aad2064cc56ba55db14.png)

nRF54系列片上有多个电源时钟域：

- **MCU Power Domain**：时钟频率最高（128MHz），拥有高速外设（SPI 32MHz）和高速GPIO（P2）
- **RADIO Power Domain**：射频外设以及无线协议栈所需的外设，无GPIO
- **PERI Power Domain**：主要的低功耗外设域，有大量低功耗外设，对应GPIO P1
- **LP Power Domain**：低功耗外设域，和PERI PD相比，其时钟和MCU PD是**异步**的。可以在其他电源域都休眠的情况下，LP PD仍能保持工作，从而低功耗唤醒系统其余部分。对应GPIO P0

在每个时钟域内部，外设基本上可以任意选取GPIO使用，就像nRF52系列一样。

## GPIO跨域引脚选择

我们会发现 PERI PD 中需要GPIO的外设非常多，而 MCU PD 中需要 GPIO 的外设非常少。这会导致有时候 GPIO P1 上的引脚数量不够用，而 GPIO P2 上的引脚有空余。

因此，nRF54 系列允许一部分PERI PD的外设使用 MCU PD 的 P2 口，即跨域使用。这种情况下，需严格按照 datasheet 中规定的引脚分配，例如：

![image-20260104012415611](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/ae28c3e3bbf43ae3501aeb7c56783b06.png)

> nRF54系列跨域的其他要求：
>
> 1. 注意SPI/I2C等外设的时钟信号需要特别选择标注为clock pin的引脚，见[nRF54L15 - Clock pins](https://docs.nordicsemi.com/bundle/ps_nrf54L15/page/chapters/pin.html#ariaid-title3)。UART不需要clock pin。
> 2. GPIO P2没有输入中断的能力

## GPIO跨域软件配置

跨域使用时，还需要显式配置CPU的电源模式为[Constant Latency](https://docs.nordicsemi.com/bundle/ps_nrf54L15/page/pmu.html#ariaid-title3)。

> System ON模式下，有两个子电源模式：
>
> - **Constant Latency** ：确保所有PPI响应时间和CPU唤醒延迟为固定值，且最短
> - **Low-power**：自动以最低功耗状态运行，但PPI响应时间和CPU唤醒时间可能会变化。**Low-power是默认模式**。
>
> 其中**Constant Latency**模式。需要在idle状态下保持部分寄存器，功耗略高。

原始文档：[nRF54L pin mapping](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/app_dev/device_guides/nrf54l/pinmap.html)

首先开启配置：

```shell
CONFIG_NRF_SYS_EVENT=y
```

然后，在需要Constant Latency模式的代码部分，申请此电源模式：

```c
#include <nrf_sys_event.h>

int main(void)
{
        /* Request constlat. The API is reference counted. */
        nrf_sys_event_request_global_constlat();

        /* Use peripherals which have pins mapped across power-domains */

        /* Release constlat */
        nrf_sys_event_release_global_constlat();

        return 0;
}

```

这个API采用的是“引用计数器”。也就是说有多个线程同时申请此模式时，usage+1；释放此模式时，usage-1。只要usage不为0，那么CPU就会处于Constant Latency电源模式。

> 注：以上介绍的是NCS v3.1.x之后的最新API。
>
> NCS v3.0.x需要使用以下API：
>
> `CONFIG_NRFX_POWER=y`
>
> ```c
> #include <nrfx_power.h>
> 
> 
> int main(void)
> {
>         /* Request constlat. The API is reference counted. */
>         nrfx_power_constlat_mode_request();
> 
>         /* Use peripherals which have pins mapped across power-domains */
> 
>         /* Release constlat */
>         nrfx_power_constlat_mode_free();
> 
>         return 0;
> }
> ```

## 例程测试

在[我的例程](https://github.com/Jayant-Tang/learning_zephyr_serial)中也有跨域使用的案例。

首先把`prj.conf`中注释的配置打开：

![image-20260104014017195](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/32d7169c90040d23b4a3d8d5684c17bd.png)

开发者需要明确的知道自己正在使用跨域GPIO，因此我做了一个应用层配置项：

![image-20260104014637600](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/c0db7fa1430b3959706938be019ca895.png)

开启`CONFIG_APP_UART_GPIO_CROSS_DOMAIN=y`之后，会自动通过`select`的方式连锁开启`CONFIG_NRF_SYS_EVENT=y`

然后在`boards/nrf54l15dk_nrf54l15_cpuapp.overlay`中，注释掉原本的引脚分配，并把跨域的引脚分配打开：

![image-20260104014855545](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/99c0e6210032fb9a481e6027a7565fa2.png)

实际代码在刚初始化完毕时就开启了Constant Latency，并在后续根据按钮情况开启或关闭：

![image-20260104021927532](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/806e6b1966b9f065d0f7bc6b0e34622a.png)

![image-20260104022006350](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/bc0dc820ffa9baa96ecad56581e5bebf.png)



重新编译，软件部分就完成了。

至于硬件部分，**由于P2.0-P2.5在开发板上被分配给了外部Flash，因此需要一定调整**：

![image-20260104015113052](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/4d06e3b2f79acb4cb92c71706c78b318.png)

对于较老的开发板（如0.9.1, 0.9.2），需要割开SPI Flash附近的焊盘。

对于最新的开发板（1.0.0），是 Interface MCU（也就是J-Link Debugger）来控制电子开关。通过nRF Connect for Desktop中的Board Configurator控制：

![image-20260104015421288](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/220f03bebfc0477f6bd4fd6a5928138f.png)

![image-20260104015656307](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/e23d2d541e8635b77dc6d30e36de3bf0.png)

首先把外部存储器（External Memory）关掉；然后把GPIO电源改为3.3V，因为我们修改了串口引脚，就不能继续使用 J-link 自带的USB转串口了。

> 配置完毕后一定要写入配置，**然后一定要退出Board Configurator，否则功耗测量会有问题。**

![image-20260104020140622](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/41430ac4deaa16d89842ca6c1cad6913.png)

测试：

![image-20260104020726626](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/2500a838cf23326fc398aff5dd2cc902.png)

功能正常回环。后面长文本断开，是因为超出了应用层按照`\r\n`进行解包函数的Buffer长度（256Bytes），实际上接收是没问题的：

![image-20260104020919891](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/b2b8619f476ae9d2188a0b1521588a1c.png)



RX接收开启时，54L15跨域使用功耗约为400uA，比前面章节测得不跨域使用（150uA）要高250uA：

![image-20260104021813610](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/41f075076c571639ba332a9e26909faf.png)



串口休眠时，无变化（因为代码里在关闭串口时也关闭了constant laytency模式）：

![image-20260104021722458](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/35bfdbd5619f847490626739a4a11e44.png)



# 8. USB CDC ACM 串口（USBD Stack Next）

前面介绍了硬件串口的异步API，接下来我们介绍USB CDC ACM串口。

>  由于nRF54L15 不带 USB，后续用 nRF52840DK 继续。你也可以选择nRF54LM20DK，nRF5340DK，nRF52833DK等。

仍然使用之前的GitHub项目。应用层代码无需改动，只需修改一些配置就可以把前面的异步串口代码变为USB CDC ACM串口代码。

示例代码：[Jayant-Tang/learning_zephyr_serial: An example that shows how to use zephyr Async UART](https://github.com/Jayant-Tang/learning_zephyr_serial)

## 编译USB串口例程

编译时选好配置文件和设备树：

![image-20260210212128497](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/21c0f60e92f9c7c12f8b683136600469.png)

或者用命令编译：

```powershell
west build -d build_usb -p -b nrf52840dk/nrf52840 --sysbuild -- -DCONF_FILE="prj_usb.conf" -DEXTRA_DTC_OVERLAY_FILE="boards/nrf52840dk_nrf52840.overlay" -DDTC_OVERLAY_FILE="usb.overlay" 
```

或者用命令编译：

```bash
west build -p -d build_usb -b nrf52840dk/nrf52840 -- -DCONF_FILE="prj_usb.conf" -DDTC_OVERLAY_FILE="usb.overlay"
```

## 运行并测试USB串口

![image-20231113111154639](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/8ada0b901ff5c008dd17acc90971ae89.png)

左侧是Jlink USB，下方是nRF52840的USB Device接口。在串口助手里选中USB串口：

![image-20250727063204480](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/a193007588cb8eb0477e7058cbb42c45.png)

可以看到功能和前面的异步串口完全相同：

![image-20250727063250261](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/ffaa699ebd81acdad4bfbc16e3758957.png)



## 代码解析

### 1) USB CDC ACM 设备树

在`usb.overlay`中，有如下配置：

```
/{
    aliases {
        my-usb-serial = &usb_serial0;
    };
};

&zephyr_udc0 {
    status = "okay";
	usb_serial0: cdc_acm_uart0 {
		compatible = "zephyr,cdc-acm-uart";
        status = "okay";
	};
};
```

这里我们给 usbd 节点新增了一个子节点`/soc/usbd@4002700/cdc_acm_uart0`，并且也给其添加了一个label：`usb_serial0`。

这就是后续我们要操作的“异步串口”。

### 2) USB CDC ACM 配置

在`prj_usb.conf`中，和`prj.conf`相比增加了以下内容：

```bash
# enable USB Device Next Stack
CONFIG_USB_DEVICE_STACK_NEXT=y
CONFIG_USBD_CDC_ACM_CLASS=y

CONFIG_APP_USB=y
```

前两项开启了 Zephyr USB Device Stack (Next) 和对应的 USB CDC ACM 类。

> 注：老的USB协议栈将被废弃，开启方式为`CONFIG_USB_DEVICE_STACK=y`。
>
> Next 协议栈与 Legacy 协议栈的区别：
>
> - Next 支持 USB High Speed (480MHz)，而 Legacy 只支持 Full-Speed（12MHz）。nRF54LM20/54H20 等需要Next栈来支持HS-USB。
> - Legacy stack 通过大量的 Kconfig 选项进行配置（如 `CONFIG_USB_DEVICE_MANUFACTURER`、`CONFIG_USB_DEVICE_PID` 等）；Next stack 的设备标识符通过代码API配置，而HID 实例通过 Devicetree 节点配置
> - Next 可在运行时注册多个 class/function 实例，支持多控制器、Full/High-Speed，并提供 HID、CDC ACM、MSC、Audio、UVC 等内建类

最后一项是我自己写的一个软件模块，通过 Kconfig 定义了一个开关。只要开启就会导入USB相关代码。

### 3) 异步串口代码

代码和前面的异步串口代码几乎一样。只是换了一个串口设备：

![image-20260210214319992](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/ce7b967296bc2bc2cc37c7f8cdece211.png)

USB栈已经初始化好了驱动，因此我们可以像使用硬件串口一样使用USB CDC ACM。

另外，在初始化阶段使用了 `uart_async_adapter`:

![image-20260210214431729](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/760f0bc41b7e442267c764a841458fe2.png)

> USB CDC ACM 驱动提供的虚拟 UART 设备只支持 **Interrupt API**。而`uart_async_adapter`的作用就是在其之上封装一层异步 API。
>
> ```shell
> # enable USB ASYNC Adapter
> CONFIG_UART_ASYNC_ADAPTER=y
> ```

其他部分的代码完全不用动，和前面介绍的异步API逻辑完全一样。

### 4) USB初始化与标识符配置

在`app_usb.c`中，我配置了自己的USB设备，这个配置和NCS中的示例模板**绝大部分**都是一样的：

![image-20260210220116774](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/bd0a721e93c14d41bf5786dfd5286b34.png)

> SDK中提供了现成的USB配置参考模板，有两个可以选择。
>
> 第一个是通过开启`CONFIG_CDC_ACM_SERIAL_INITIALIZE_AT_BOOT=y`，就可以导入SDK中的配置代码：`zephyr\subsys\usb\device_next\app\cdc_acm_serial.c`。
>
> 然后就可以用相关 config 进行快速的配置。
>
> 第二个模板，可以模仿例程`zephyr\samples\subsys\usb\cdc_acm`，在 CMakeLists.txt中添加：
>
> ```cmake
> include(${ZEPHYR_BASE}/samples/subsys/usb/common/common.cmake)
> ```
>
> 同时，在Kconfig中添加：
>
> ```
> source "samples/subsys/usb/common/Kconfig.sample_usbd"
> ```
>
> 就可以添加类似的配置USB参考模板了。

我没有完全使用示例模板。我将模板代码拷贝出来变成自己的源文件`app_usb.c`，方便进行修改。主要有两个修改点：

- 初始化时，不使能USB，保持低功耗
- 注册了一个USB事件回调函数，根据具体的USB事件再使能USB。

### 5) USB事件回调

在`app_usb.c`中注册了自己的USB事件回调函数：

```c
err = usbd_msg_register_cb(usbd_ctx, app_usb_msg_cb);
if (err) {
    LOG_ERR("Failed to register message callback (%d)", err);
    return err;
}
```

在`app_usb_callback.c`中，我维护了一个状态机。使用了Zephyr的状态机框架 ([State Machine Framework — Zephyr Project Documentation](https://docs.zephyrproject.org/latest/services/smf/index.html))。

这个框架能方便的注册每个状态的 entry, run, exit函数，还能处理复合状态。类似这样：
```c
enum demo_state { S0, S1, S2 };

const struct smf_state demo_states[] = {
   [S0] = SMF_CREATE_STATE(s0_entry, s0_run, s0_exit, parent_s0, NULL),
   [S1] = SMF_CREATE_STATE(s1_entry, s1_run, s1_exit, parent_s12, NULL),
   [S2] = SMF_CREATE_STATE(s2_entry, s2_run, s2_exit, parent_s12, NULL)
};
```

我这里定义了4个状态：

![image-20260210220641564](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/d5301b9ad10dc810dc630d97415986e4.png)

其中 `CONNECTED` 状态有两个子状态`CONFIGURED`和`SUSPENDED`：

![image-20260210221049592](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/84d9a0ef48b1a62a92fc9cdc6e0c8552.png)

> 注意：
>
> 1. 理论上，四个状态作为平等的状态来设计也是可以的。但是，USB断开在任何情况下都可能发生。如果作为平等状态，就要在`CONNECTED`, `CONFIGURED`, `SUSPENDED`状态中都处理USB拔出的事件，有点重复。而恰好 Zephyr 状态机支持复合状态，直接把`CONNECTED`作为一个父状态即可。
> 2. 我这里没有注册`entry`和`exit`函数，只注册了`run`函数。因为`entry`和`exit`函数主要还是用于状态切换时，本地必须执行的初始化或清理等动作。这个状态机还是以USB事件驱动为主，为了突出USB事件，这里就只在run函数中进行事件处理和状态切换。

当产生 USB 事件时，会保存 `msg` 并执行当前状态的 `_run` 函数：

```c
void app_usb_msg_cb(struct usbd_context *const ctx, const struct usbd_msg *const msg)
{
	int err;

	LOG_DBG("USBD MSG: %s", usbd_msg_type_string(msg->type));

	__ASSERT(ctx != NULL, "usbd context is NULL");
	usbd_ctx = ctx;

	usb_smf.msg = msg;
	err = smf_run_state(SMF_CTX(&usb_smf));
	usb_smf.msg = NULL;

	if (err) {
		LOG_ERR("USB SMF terminated (%d)", err);
	}
}
```

在`DISCONNECTED`状态下收到`USBD_MSG_VBUS_READY`事件，就说明 USB 插入，于是就调用`usbd_enable(usbd_ctx)`来使能USB；在`CONNECTED`状态下收到 `USBD_MSG_VBUS_REMOVED` 事件，就说明 USB 拔出。于是就调用`usbd_disable(usbd_ctx)`来关闭USB。**从而实现了拔出USB状态下的低功耗**：

![image-20260210221933309](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/ce5532648d8bfa05cacd2db30d5963a6.png)

> Zephyr SMF，复合状态的`_run`函数的机制：
>
> - 先执行子状态的`_run`函数，这个事件处理完毕后如果认为无需父状态再处理这个事件，就返回`SMF_EVENT_HANDLED`。那么父状态的`_run`函数就会被跳过。
> - 像是USB拔出的事件`USBD_MSG_VBUS_REMOVED`。子状态中均无需处理这个case，直接在`switch` 语句的 `default:`条件下返回`SMF_EVENT_PROPAGATE`来忽略这个状态。这样就统一由父状态来处理这个事件。



# 9. 开发自己的程序

## 串口API的兼容
我们前面提到，异步API和基于中断的API是完全不同的两套API。如果有的串口想用异步API，有的串口想用中断API（如Shell等）怎么办？

在串口驱动目录下的`Kconfig.nrfx`中可以看到：

```
config UART_1_ASYNC
	bool "Asynchronous API support on port 1"
	depends on UART_ASYNC_API && !UART_1_INTERRUPT_DRIVEN
	default y
	help
	  This option enables UART Asynchronous API support on port 1.
```
要使用异步API，必须单独禁用这个串口的中断API。
如果你要使用USB CDC ACM（需要中断API）的同时使用串口0的异步API，则需要这样配置：

```shell
CONFIG_UART_INTERRUPT_DRIVEN=y

CONFIG_UART_0_INTERRUPT_DRIVEN=n
CONFIG_UART_1_INTERRUPT_DRIVEN=y
```
以上配置的意思是，对于**整个串口驱动**来说，启用中断API（这个配置项来源于Zephyr串口驱动目录下的Kconfig）。
但是对于串口0来说，关闭中断API（这个配置项来源于Zephyr串口驱动目录下的Kconfig.nrfx）。如此一来，就实现了每个串口的单独配置，互不干扰。

## 把串口程序集成到自己的应用中

本例程已经非常完善，把`app_uart`文件夹拷贝到自己的工程中，然后在Kconfig和CMakeLists.txt中引用即可。这也是模块化开发的思想。而且本工程思路还是比较清晰的，开发者想增加自己的代码也会非常容易。

并且，发送和接收都是在线程中处理，本例程提供的API都可以放心在各种地方调用。

如果有GPIO功耗控制的需求，可以自行添加：

1. 要想在TX前后控制GPIO，直接在TX线程中添加相关逻辑即可；
2. 要想通过GPIO来控制RX是否开启，直接使能`CONFIG_PM_DEVICE_RUNTIME=y`，然后在GPIO中断内调用`app_uart_sleep()`和`app_uart_wakeup()`即可（开启能`CONFIG_PM_DEVICE_RUNTIME=y`之后，这两个API只影响RX，不影响TX）。
