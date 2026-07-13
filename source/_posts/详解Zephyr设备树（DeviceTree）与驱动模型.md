---
title: 详解Zephyr设备树（DeviceTree）与驱动模型
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2023-03-12 14:27:19
cover: null
tags:
- Nordic
- Zephyr
- DeviceTree
categories: Zephyr
sticky: 100
cnblogs:
  postId: '17209392'
  url: https://www.cnblogs.com/jayant97/articles/17209392.html
  lastPublishedAt: '2026-07-06T18:20:52+08:00'
  sourceHash: sha256:b78b931e517fbe75e25f91f1108bf7554be33054a9ca8d00596813dd2448e904
  status: imported
  postType: Article
---

# 1. 前言

​	Nordic最新的开发包NCS（nRF Connect SDK）相对于原来的nRF5 SDK来说，最大的更新莫过于采用了Zephyr系统。而Zephyr不单单是一个用来做多线程的RTOS，它更大的价值在于其自带的各种开源的协议栈、框架、软件包、驱动代码等。如果不是为了使用这些现成的协议栈和软件包，只是单纯使用RTOS，实际上并不会产生什么价值。可以说，Zephyr是为物联网而生的。

​	Zephyr采用Kconfig对这些软件包进行管理，可以方便地使能或剪裁。而为了使Zephyr自带的硬件驱动代码能够通用，Zephyr采用了DeviceTree来描述硬件。各个半导体厂商把自己的硬件描述成标准DeviceTree，并且按照Zephyr的接口提供驱动代码，然后一起提交给Zephyr。在方便地使用Zephyr中协议栈的同时，用户还能简单方便地使用到各个半导体厂家的硬件功能，这多是一件美事。

​	但由于目前中文互联网上没有一个很详细的从零开始的教程，导致很多人遇到Zephyr的DeviceTree时感到很厌烦：「我之前配一下寄存器、调一下库函数就能操作硬件，怎么现在搞这么复杂？」

​	但是相信你读完本文后，能够感受到DeviceTree的便利之处。而所谓的**复杂**与**简单**，往往是相对的。人的大脑容量有限，所以我们要不断地对做事的方法进行压缩、抽象，充分利用别人已经完成的工作成果。这也是最早从机器码发展到汇编，再到现在各种高级语言的底层逻辑。

​	下面正式开始。

# 2. 从一些习惯开始

## 硬件的抽象

​	在做传统的嵌入式C语言开发时，我们常会使用宏定义的方式来实现**硬件的抽象**，例如：

```c
#include <gpio.h>
#define PORT_LED_1 GPIO_PORT_0
#define PIN_LED_1 GPIO_PIN_12
```

​	在实际的应用代码中，如果多次使用到这个GPIO，在想要修改IO的时候，只需要修改宏定义即可，而不需要把每一个用到这个IO的地方都改一遍。这种方法的优点很明显：简单直观。

> ​	其实我们写代码，最终都是在CPU上运行，操作的都是外设寄存器，而不是板子上的LED。当我们在代码里写什么LED驱动、屏幕驱动、电机驱动的时候，只是在用**面向对象**的思维方便开发者（也就是我们自己）而已。CPU是不会理解什么是LED、什么是屏幕、什么是电机的，它只是勤勤恳恳按照指令执行代码，从某些地址读写数据而已。
>
> ​	也就是说，地址、指令和数据才是核心。牢记这一点，才不会被DeviceTree中乱七八糟的硬件节点绕晕。

​	理解这种简单的操作，其实就已经为理解DeviceTree做好了铺垫。

## 代码的解耦

​	大家初学代码时，一定有过想要“解耦”开发的想法：把不同的功能写进不同的文件里，封装成模块，然后在主函数里分别调用这些库即可，不同的模块之间完全解耦。

​	这种想法在做纯软件时是很容易的。但是，遇到硬件时，往往会遇到一些麻烦。这里举一个例子：假设我们有一个按钮和一个sensor，都需要用到GPIO以及中断，并且我们想实现代码的解耦，如下图。初始化、应用代码、中断服务函数均解耦。

![image-20230312145925945](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined3e6e4a7be1d1528771a59834de4f26dd.png)

​	看似这种解耦很美好，但是实际上是实现不了的。因为，认为按钮和sensor之间有区别，这完全是我们人类的观点。对于MCU来说，它都是在操作外设寄存器，按钮和sensor没什么区别。因此gpio外设只需初始化一次，并且中断服务函数也不能定义在两处。

​	实际上，现在很多成熟的SDK，简单来说是用下图这种方式进行实现的解耦：

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined5cd043db790ba096f2069f74cbf017b6.png" alt="image-20230312150536356" style="zoom:80%;" />

​	有一个专门的`board.c`，或者说BSP（Board Support Package，板级支持包），来处理MCU本身的硬件初始化和中断服务函数。然后，剩余的**应用代码**再做解耦，也可以把回调函数注册进中断服务函数中去。`board.c`可以说是返璞归真，真正的是在面向MCU编程，而不是面向抽象的对象编程。

## DeviceTree与Zephyr驱动的引入

​	先说硬件的抽象，前面说的这种宏定义的方式虽然方便，但往往只是方便个人开发者，或者是一个项目内几个同事之间口口相传，没有什么规范可言。不同开发者之间定义宏的方式可能差别很大。

​	Zephyr不会自己再定义一套新的宏用来描述硬件，那样和各个厂商自己的SDK里的宏也没什么区别，徒增麻烦而已。Zephyr的设计思路就是：能用现成的轮子就不自己造。

​	因此，Zephyr引入了DeviceTree这一成熟的方案，像Linux一样，各个半导体厂商自己出DeviceTree来描述自己的产品，并且自己提供各个外设的驱动代码。用户只需调用Zephyr标准驱动，底层就会根据DeviceTree自动找到对应厂商的驱动代码，然后编译进固件中。

​	并且，Zephyr支持在系统初始化时就自动初始化好所有驱动。这样系统进入到Application（主线程）时，所有驱动就已经初始化好了，可以直接进行操作。用类比的说法，就是Zephyr内置了所有厂商的所有外设的`board.c`，你只需动动手指改一下DeviceTree，就可以直接做应用开发，不需要自己写这个`board.c`了。

​		总的来说，DeviceTree是一个标准的描述硬件的方法，厂商提供了标准的DeviceTree和驱动代码。用户只需配置好DeviceTree，硬件就会自动初始化好。并且只需调用Zephyr通用驱动API，跨平台。



# 3. DeviceTree的结构和语法

本节参考：[Introduction to devicetree — Zephyr Project Documentation](https://docs.zephyrproject.org/latest/build/dts/intro.html)

## 3.1. DeviceTree的层次结构

​	先抛开语法本身，我们先用框图的形式理解DeviceTree表达的是什么。如下图是一个示例，描述了一块板子，上面有一颗Soc、一组LED、一组按钮，还有一个I2C接口的RTC时钟ds3231。

![image-20230312162505279](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb87d6e3ab050a506aa9221203bb8f638.png)

​	首先，DeviceTree是一个树状结构。那么，树状结构的层次结构是由什么决定的？是什么决定了节点之间的父子关系？

​	答案是：**首先看总线的主从关系、其次看硬件的包含关系**。

​	具体来说，就是：

1. SoC的所有外设都在ARM地址空间内可被**寻址**（AHB总线和APB总线），因此`gpio0`、`i2c0`、`adc0`等外设节点都是`SoC`的子节点；
2. `ds3231` RTC是i2c从机，具有i2c地址，故是`i2c`外设的子节点；
3. Button和LED虽然使用GPIO，但GPIO不是**总线**。并且根据前一章节所述，Button和LED对SoC来说并没有什么意义，它只是便于人类面向对象编程的。因此，这里的`Buttons`和`Leds`就根据**硬件的包含关系**，直接挂在板子（也就是根节点`/`）下面即可；
4. 同理，如果有某种电压表设备用到了ADC的通道，这里，ADC的通道也不是总线，因此这个电压表设备也应该直接挂在根节点下面。

## 3.2. DeviceTree的适用范围

​	DeviceTree是为**编译固件**服务的，描述的是这个固件所运行的CPU，所在的板子的硬件信息。因此DeviceTree描述的是**板级**信息。再结合「DeviceTree的层次结构是基于**总线地址**的」，可以得出以下的结论：

1. **如果一块板子上有两颗MCU，则这两颗MCU固件编译时所采用的DeviceTree不相同。**
   例如nRF9160 DK上有一颗9160，还有一颗52840。在NCS中选择Board时，就有以下两个选项

![image-20230312163613633](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined5eaaa1ad3540491bca3007ba1e4eb69a.png)

2. **如果一颗MCU具有两个独立运行固件的CPU，则这两颗CPU不能共用DeviceTree**
   例如nRF5340，具有应用核和网络核，这两颗CPU固件独立。因此选择board时有两个选项。

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined70a3edd1221203c9e725237e57baa460.png" alt="image-20230312163934665" style="zoom:80%;" />

3. **如果一颗CPU具有两种不同的地址空间（例如Cortex M33的安全地址空间和非安全地址空间），则这两种情况也不能共用DeviceTree**

![image-20230312164104566](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined5e1f265a8576a6b17c9175efcdd879a7.png)

![image-20230312164125085](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedde6599dfcef3953c0cd9a03d1ab1d6f2.png)

<center>nRF5340的地址空间，分为应用核和网络核</center>
<center>且每个核的外设还分安全（secure）和非安全（non-secure）</center>

## 3.3. DeviceTree的语法

​	DeviceTree既然是一个标准，那么一定有它的标准文档，如果大家有兴趣可以去官网下载：[Specifications - DeviceTree](https://www.devicetree.org/specifications/)

​	本文就只捡重点讲：

### 3.3.1. DeviceTree基本结构示例

​	DeviceTree的源码称为DTS（DeviceTree Source），后缀为`.dts`。

```
/dts-v1/

/{
	a-node{
		a_node_label: a-sub-node {
			foo = <3>;
		};
		another-sub-node {
			foo = <3>;
			bar = <&a_node_label>;
		};	
	};
};
```

1. `/dts-v1/`，指明了DeviceTree的版本；
2. 设备树具有唯一的根节点`/`；
3. 节点的**名称**写在大括号之前。如`a-node`、`a-sub-node`和`another-sub-node`；
4. 节点的**属性**写在大括号内，是键值对（Key-Value Pair）的形式。如`foo = <3>;`；
5. 子节点直接写在父节点的大括号内，从而可以表达树状的层次关系；
6. 可以给节点写一个标签，例如`a_node_label`，标签与节点之间用冒号`:`连接。

> 标签（Label）的意义：
>
> 1. 要指明一个节点，标准的做法必须指明绝对路径，例如：`/a-node/a-sub-node`。
>    有了标签，就可以省略路径，直接用标签表示一个节点，如`a_node_label`。
> 2. 标签可以被作为**属性**引用，让一个节点成为另一个节点的某个属性的**值**。注意，这里说的是成为「属性的值」，而不是成为「子节点」。

### 3.3.2. DeviceTree节点的名称

DeviceTree中的节点名称遵循以下命名规则：`name@address`

1. `name`：必须以字母开头。长度在1~31子节。允许大小写字母、数字、**英文逗号、小数点、加号、减号、下划线**；
2. `@address`：称为**「Unit Address」**，如果节点有`reg`属性，则address的值必须与`reg`描述的**第一个寄存器地址**相等，可以理解为某个外设在它的总线上的首地址。如果某个节点没有reg属性，则`@address`**必须省略**。
   值得一提的是，address和reg都是16进制。但address不需要写`0x`前缀，而reg的16进制值需要写`0x`前缀。

>​	实际上，Zephyr对address有一些特殊的规则，见：[Unit address](https://docs.zephyrproject.org/latest/build/dts/intro-syntax-structure.html#id7)
>
>​	这里也说一下：
>
>- 挂在SPI总线上的设备：address表示片选线（CS）的编号，如果没有片选线，则为`0`；
>
>- RAM：address直接为RAM的物理起始地址，如`memory@20000000`，表示`0x20000000`；
>
>- Flash：address直接为Flash的物理起始地址，如`flash@800000`，表示`0x08000000`。
>
>- Flash分区：可以在DeviceTree里存一个Flash分区表，分区的address是相对于Flash物理首地址的偏移量，如：
>  ```
>  flash@8000000 {
>      /* ... */
>      partitions {
>          partition@0 { /* ... */ };
>          partition@20000 {  /* ... */ };
>          /* ... */
>      };
>  };
>  ```

几个示例：

```
// address必须和reg首地址相等，无论是ARM地址还是i2c地址
i2c@40003000 {
    reg = <0x40003000 0x1000>;
    /* ... */
    ds3231@68 {
        reg = <0x68>;
        /* ... */
    };
};
```

```
// 不带地址的节点，不含@address字段
buttons{
   /* ... */
};
```

```
// 英文逗号也是name的一部分
zephyr,user {
	/* ... */
};
```

### 3.3.3. DeviceTree的属性

​	DeviceTree中每个节点可以有几个属性来描述这个节点。

​	属性是键值对。属性的名称可以含**大小写字母、数字、逗号、小数点、下划线，加号、减号、问号、"#"号**。

​	属性是有**类型**的，并且，Zephyr中的属性类型和标准的DeviceTree还有一定的区别，总之是更详细了，见下表：

| 类型          | 属性示例                                                   | 说明                                                         |
| ------------- | ---------------------------------------------------------- | ------------------------------------------------------------ |
| string        | `a-string="hello world!";`                                 | 字符串                                                       |
| string-array  | `a-string-array="string one","string two"."string three";` | 字符串数组                                                   |
| int           | 10进制：`an-int = <1>;` <br />16进制：`an-int = <0xab>;`   | 32bit整数                                                    |
| array         | `foo = <0xdeadbeef 1234 0>;`                               | 整数数组                                                     |
| uint8-array   | `a-byte-array = [00 01 ab];`                               | 字节数组，16进制，可省略0x                                   |
| boolean       | `my-true-boolean;`                                         | 无值属性。值存在则表示`true`，不存在则表示`false`            |
| phandle       | `a-phandle = <&mynode>;`                                   | 节点句柄，指向其他的节点。可以认为是一个指针（p）或句柄（handle） |
| phandles      | `some-phandles = <&mynode0 &mynode1 &mynode2>;`            | 节点句柄数组                                                 |
| phandle-array | `a-phandle-array = <&mynode0 1 2>,< <&mynode1 3 4>;`       | 见下方详细说明                                               |

​	其实最基本的属性就是整数、布尔、字符串。以及由它们构成的数组。

​	`phandle`本质也是整数，当给一个节点赋予标签时，其实是给这个节点添加了一个隐藏属性`phandle = <n>;`。构建系统会确保整个DeviceTree中的`n`不会重复。所以这里`a-phandle = <&mynode>;`，`&mynode`的值就是这个标签指向的节点的隐藏phandle属性的值。

​	这里其他的都好理解，值得详细说的是`phandle-array`类型。其实，将其取名为「结构体数组」更加合适。这个数组的每一个元素都是一个特殊的结构体，结构体的第一个值必定是一个`phandle`，后续的值可以是任意值，数量也可以任意。Zephyr将这种类型用来做硬件通道的配置，例如`<&gpio0 1 GPIO_INPUT>`表示gpio0，1号引脚，模式为输入。后续的硬件支持章节会更详细地讲解实例。

### 3.3.4. DeviceTree的文件引用

​	`.dts`可以引用其他的`.dts`或`.dtsi`。这样**板卡级dts**就可以引用厂商写好的**芯片级dtsi**，从而减少编写dts的工作量。

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined3ed888444a488e7deda033ce67293598.png" alt="image-20230312180147944" style="zoom:80%;" />

​		`.dts`也可以引用C语言头文件，从而使用里面的宏定义和枚举值：

![image-20230312180310480](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined30edeedbc824659819930662e7516714.png)

![image-20230312180319140](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb3e9b8d5919e7c6092f13603cb251998.png)



# 4. Zephyr中的DeviceTree文件

​	在Zephyr中，在许多地方都保存的有dts文件。

​	首先，在NCS中创建build时，需要选择board，而板子的一系列文件中就包含了`.dts`文件。

## 4.1. dts文件

### 4.1.1. 芯片级dtsi文件

各个厂商提供的芯片级dtsi文件，对于nordic的产品，其dtsi文件位于`${NCS}/zephyr/dts/arm/nordic/`中。

### 4.1.2. 板卡级dts文件

​	各个厂商可能会推出一些开发板、评估板。这些板子的dts文件位于`${NCS}/zephyr/board/arm/${board-name}/`中

## 4.2. overlay文件

### 4.2.1. overlay文件的位置

​	在我们开发应用时，往往需要基于厂商的开发板Dts，新增一些功能，或者禁用一些功能。Zephyr提供了overlay的方式让我们可以**覆写**原始的板卡级dts。

​	在一些例程中，可以看到`boards/<board>.overlay`文件：

![image-20230312182939910](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined4b35be9360b39ce39874c426fd1a6d4f.png)

​	如果没有看到，说明这个例程无需修改开发板的原始dts就能实现功能。如果用户想修改，也可以自己在应用根目录创建一个`app.overlay`：

![image-20230312183130067](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined6500c41102ecac6efbd2e811a129af6f.png)

​	其实添加overlay的方式有很多，并且zephyr会按照一定的顺序找这些overlay，如果在多个地方都定义了overlay，可能zephyr只会使用其中的一部分。具体规则请看：[set-devicetree-overlays](https://docs.zephyrproject.org/latest/build/dts/howtos.html#set-devicetree-overlays)。

### 4.2.2. overlay的使用

**（1）直接在原有节点覆盖/新增属性，可以从根节点开始写：**

![image-20230312192849065](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined67ff068e55c6ee4ef9b9e61ef4ff23d6.png)

​	也可以直接用label写：

![image-20230312191745811](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined95974e5152cae848f76ea47b055c3932.png)

**（2）删除原有的属性**

![image-20230312192939102](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedfd7978b3af96a370969b48efdb8b1f84.png)

**（3）删除原有的节点**

![image-20230312193017699](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined58e7903969757ce0340b0e1395cbb769.png)

## 4.3. 完整的dts文件

每个项目构建时，编译之前，会在构建目录下生成最终的完整dts。位置为`${project_folder}/build/zephyr/zephyr.dts`

## 4.4. 最终输出

​	Linux的DTS会被编译为DTB，然后在启动时由Bootloader传递给kernel。但Zephyr运行在性能较差的嵌入式平台上，故不可能专门运行一个解析器去读DTB。

​	因此，DTS实际上实在编译时被Zephyr的构建系统（一套python脚本）变成了头文件，这个头文件的位置是：

`${project_folder}/build/zephyr/include/generated/devicetree_generated.h`

​	了解即可，实际开发不需要查看这个头文件。



# 5. 用DeviceTree配置硬件信息

​    从上一节我们可以知道，DeviceTree本身的结构和语法其实非常简单，只是规定了一个形式而已，跟硬件的配置没有任何关系。

​    要想了解DeviceTree是如何对硬件配置产生影响的，需要了解一些常见的属性和概念。

## 5.1. 标准属性

​	DeviceTree中有一些标准的属性，这些属性和Linux是一样的，在DeviceTree Specification中是有定义的。此处简要介绍一下：

### reg, #address-cells 与 #size-cells

![image-20230312200747143](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinede9ffb0b6ffd4759fcdf59ac75a9cefab.png)

  **reg**属性代表此节点在总线上占用的地址和范围。是由**多对** **(address, length)**组合而成的。而**#address-cells** 和**#size-cells**则表示了这个总线上的节点的reg属性里，每个address和size要占用多少个uint32单元。

  如上图，先看父节点`soc`，可以得知这条总线上，所有寄存器的address和size各占一个uint32单元。则serial有两个寄存器，第一个寄存器首地址是0x0，长度是0x100；第二个寄存器首地址是0x200，长度是0x300。

> ​	如果地址长度为64位或更多（即要占用多个Uint32单元），则reg中的写法为大端模式（Big-Endian ），即高地址在前，低地址在后。

### ranges

![image-20230312201206619](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedcda0e2694d6e9ed1820db7ee5ef83d82.png)

当一个节点定义了ranges属性，那么它的子节点就可以使用**相对地址**，而非**绝对地址**。

如上图。peripheral基地址为0x40000000。而ADC的地址从0xe000开始，这是一个相对地址。则ADC在ARM地址空间的绝对地址为0x4e000000。

> ranges属性的格式为：
>
> `ranges = <子空间首地址  父空间首地址 长度>`
>
> 子空间首地址为0时，子节点的地址就是相对地址。
>
> 至于这三个元素分别要占用几个uint32单元，看图中同色的部分即可。

  一般用户也用不到，了解即可。厂商才会去改芯片内部的dts。

### status

![image-20230312201508849](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedd987d33781fd961b647432de1402deea.png)

  **status**用来指定是否启用一个设备（节点），根据DeviceTree Spec有以下几个选项：

- "okay" ： 设备是可操作的
- "disabled" ： 设备目前是不可操作的（但未来可能可以操作，比如设备插入、安装后）
- "fail" ： 设备不可操作。设备中检测到错误。
- "fail-sss"：设备不可操作。其中sss的部分会根据不同的设备而变换，用于指定特定的错误码
- "reserved" ： 设备可操作，但不应该使用。通常用于设备被其他软件控制的情况。

但是实际上Zephyr中基本只会用「okay」和「disabled」 ，用来启用或禁用节点。

### compatible

![image-20230312201647347](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined5aa23e4d5377378023d8c91137e4bb85.png)

![image-20230312201652944](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined819891c442642d0a7fb4af1e252dab1f.png)

![image-20230312201657935](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined9625b23cadaca2e217672deb0e1d4dfc.png)

![image-20230312201702581](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined9ebfa6fe2fc6ad5ac42e7c4781dd7209.png)



  **compatible**用来说明一个节点设备的兼容性。它的值是一个字符串或一个字符串数组。

  Zephyr构建系统就是用它来为每个节点找到合适的驱动程序。其具体的应用后面会讲解。

  compatible的每个值的通常命名方式是”vendor,device”，即某个供应商的某个产品。这不是强制的要求，也可以没有vendor。

  如果compatible有多个值，zephyr会按顺序寻找驱动。会使用找到的第一个驱动。

## 5.2. 重要概念——域（Domain）

  我们知道，DeviceTree是基于**总线地址的层次结构**。然而，实际的硬件之间的关系错综复杂，实为网状结构，如何才能简洁地描述好真实的硬件之间的关系呢？

  其实，除了DeviceTree本身基于地址的树之外，在逻辑上，还存在一些其他的树，例如GPIO树、中断树、ADC树等等。

  我们将这种附加在DeviceTree上的，逻辑上的树称为**域（Domain）**。如下图，蓝色为一个按照总线地址的层次结构写好的DeviceTree，但是，在这个树上其实附加了其他的包含关系：

![image-20230312201750000](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefineddde93155ef85c95aff6396ce82133ba4.png)

  很容易发现，每个域都有一个自己的“**根节点**”，称为**控制器（Controller）**。不难发现，其实控制器才是真正的我们编程操作的对象，而域中的子节点，都是我们为了方便理解，而抽象出来的概念，这与本文第2章节的观点是一致的。

### 域的控制器与子节点

​	控制器节点通常会有一个布尔类型属性 `*-controller`，来表示自己是某个域的控制器，如下图：

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedd735e603839e72237be30eb62cf23843.png" alt="image-20230312202317603" style="zoom:67%;" />

​	而域中的子节点，就可以使用`phandle-array`类型的属性来说明自己属于哪个域。此属性的第一个值是指向**控制器的**句柄。后续的值是此节点在这个域中的**配置**。这一条配置被称为**specifier**。

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined81b4000380484cea1ca3994254a5e5a9.png" alt="image-20230312202350076" style="zoom:80%;" />

控制器节点中会有一个`#*-cells`属性来指明specifier的大小，需要占用多少个`uint32`单元。

### 中断域

中断域和GPIO域有点类似，但有点区别：

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined7a52509cfa9bb39e896a6238bcb8b288.png" alt="image-20230312202551215" style="zoom:67%;" />

  首先，我们发现adc的`interrupts`属性只写了specifier，并没有写controller指向哪里。

   这是因为，根据DeviceTree标准，构建系统默认把devicetree父节点当作中断域的controller。如果父节点不是controller，则继续向上寻找。直到遇到controller，或者遇到`interrupt-parent`属性时，才会指定父节点。

​	如图可以看出，`adc`节点向上寻找，遇到`soc`节点，在`soc`节点内，指明了其中断域控制器是`nvic`。于是`adc`节点中断域的控制器就是nvic。

### 其他类似的域

类似的还有adc域、pwm域、pin-ctrl域等等。这些域的子节点也都采用了**specifier**的方式，来记录配置信息：

![image-20230312202839931](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined5f08f76d5aac4672ad908be41049129f.png)

![image-20230312202850193](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined9f1e4566e7b86a7e756d20feca14c7ba.png)

<center>pwm控制器与子节点</center>

![image-20230312202924182](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined23bfbf6c0fe4ea6487eb722073bb476a.png)

![image-20230312202928953](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined1731270c30a6183bbf779605ca559d0e.png)

<center>adc控制器与子节点</center>

​	不过，这里没有*-controller属性来指明controller节点。

> ​	这些域的控制器的写法，可能有细小的差别，但是背后的道理是相通的。用户也不用关心控制器具体的写法，按照手册写好子节点即可。

### 域的总结

​	总之，对于初学者，这里只需记住「specifier是用来写配置的」即可，后面会讲到具体的用法。

## 5.3.  DeviceBinding

​	前面讲到**域**的概念，我们会发现不同的域的配置方法有一些共性，但也有一些差异，这让我们感觉devicetree的规则很混乱：

​    “*除了**dts**本身的语法之外，竟然还有其他的**规则**，一个不小心就会写错！”*

​	我想说，规则是双刃剑。既可以说规则带来了麻烦（提高了门槛），又可以说规则创造了便利（在配置时就提前检查dts是否正确，防止编译的时候出错，那时候更难排查）。

​	这里的便利性还体现在VS Code编辑器的**代码提示**与**自动补全**，这是Nordic提供的nRF Connect for VS Code插件实现的：

![提示](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined8e332e3ce27e4718ddd778783440f740.gif)

<center>自动补全（枚举类型可以给出预选项）</center>

![GIF 2023-2-22 23-54-54](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedc1223a28308a6c1afbb397912c48f391.gif)

<center>错误提示（specifier多写了一个单元）</center>

### DeviceBinding文件

​	所谓的**规则**，被称为Device Binding文件。binding文件是YAML格式文件，yaml是标记语言，由多组键值对组成。每个值可以是：

- 纯量（单个不可分割的值，如整数、字符串）
- 对象（把键值对当成值）
- 数组（一组同类型的**值**）

示例：

![image-20230312204227457](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefineda36ddbfe64c9220f3860025c921292cf.png)

简易语法：

- 键、值之间用**冒号+空格**分隔
- yaml的层级关系只看缩进（类似python），相同层级的缩进必须相同
- 数组元素可以是纯量、对象。对象的成员也可以有数组

> ​	可能新手会感觉很麻烦，又冒出来一种语法。但是其实用户无需有畏难情绪，因为这些内容都是使开发更简单，而不是更麻烦的。binding文件本身的可读性很强，用户只需要能大概看懂即可，编写yaml文件是厂商的工作。

​	binding和DeviceTree中的节点，是通过`compatible`属性实现联动的。**在VS Code中直接Ctrl+鼠标左键点击`compatible`**，就可以跳转到对应的binding文件中：

![jump](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined08c3946bcdb1f198583afbc06683165f.gif)

​	DeviceTree中节点的属性，必须严格按照binding文件中的要求。如下图，我自定义了一个电压传感器设备，需要用到ADC。那么我在binding文件中，要求符合`compatible = "jayant,voltage-sensor"`的所有节点，都必须具有`io-channels`属性，且类型必须是`phandle-array`。从而使得这个节点可以通过写specifier的方式，把自己加入到ADC域中：

![image-20230312204702592](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefineda36ddbfe64c9220f3860025c921292cf.png)

​	device binding的约束能力很强大，不仅可以约束节点的属性（指定数据的类型、枚举、甚至强行赋值），还可以约束此compatible节点的子节点的属性。

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined69881bb58c40179f242fb3f072dc892f.png" alt="image-20230312204824297" style="zoom:80%;" />

<center>约束一个节点的子节点的属性</center>

  	此外，还能给specifier中记录的数值赋予含义。

![image-20230312204820151](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined0db5d1369ff0e4286d240f9cb0355baf.png)

<center>给gpio specifier中的2个单元赋予含义</center>

  由于内容较多，本文不多赘述，可参考[Devicetree](https://docs.zephyrproject.org/latest/build/dts/bindings.html)[ bindings — Zephyr Project Documentation](https://docs.zephyrproject.org/latest/build/dts/bindings.html)了解更多信息。大家在实际开发过程中，直接通过Ctrl + 鼠标左键跳进binding文件，然后望文生义即可。

### DeviceBinding文件的位置

zephyr build system会从以下位置寻找binding文件：

- `${NCS}/zephyr/dts/bindings/`
- `${board_dir}/dts/bindings/`
- `${project_dir}/dts/bindings/`

也可以在CMakeLists.txt中，用 `list(APPEND DTS_ROOT /path/to/your/dts) `命令增加binding文件的目录

也可以在编译时，增加选项 `west build -b <board_name> -- -DTS_ROOT=<path/to/your/dts>`

如果想要自定义设备类型，可以把yaml文件添加到以上位置。文件名推荐和compatible一致，但不是必须的。

如下图为我自己写的两个binding文件的位置示例：

![image-20230312205310166](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined50f75f00a2feaf511bf365ee4af8054f.png)

## 5.4. 特殊节点

在5.1种描述了一些常见的属性。本节会描述一些常见的特殊节点。这些节点都是虚拟的，不是实际存在的硬件：

- `/chosen`：为**Zephyr Kernel**选择特定设备（如日志串口）；
  ![image-20230312205611402](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined3dea7b67842d59a86f9e2be20128bdcf.png)

- `/aliases`：给节点起一个别名，类似label。不过label仍是节点，而aliases中的别名是属性名。`/aliases`通常是厂商在**开发板级**的驱动代码中操作硬件所需要的。
  ![image-20230312205618639](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined1f6cd6f1c25356824063484604ecaba4.png)

- `/pinctrl`：直属于根节点，不属于soc的一个虚拟节点，用于管理**数字IO**的复用（目前不管模拟IO，因为ADC的模拟通道和MCU的硬件引脚往往是绑定死的，不能配置）；

  ![image-20230312210048297](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb9f47ca1734499f9225e6c200f9b7119.png)
  具体的介绍，我后续会写一篇文章专门讲解。大家可以直接Ctrl + 鼠标左键点击dts文件中的`pin-ctrl`，跳转过去，也能自己看懂。

- `/zephyr,user`：方便用户开发的节点，此节点无需`compatible`属性。用户可以直接在里面随便写各种specifier、自定义属性等。于是就可以直接在代码里操作GPIO通道、ADC通道、pwm通道等，或者把自己随便写的配置项读出。这免去了如果自定义一个device，还要自己写binding的麻烦。
  ![image-20230312205944691](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined00d5bdaf2c9aed3fb5e566c811db9cb2.png)

# 6. 在C代码中访问DeviceTree内容

​	在4.4小节中，已经介绍过，DeviceTree最终会用来生成`devicetree_generated.h`头文件，包含了DeviceTree中的所有信息。自然而然的，我们会想到要在C/C++代码中访问这些信息。

> ​	注意，由于DeviceTree中节点名称、属性名称允许使用的字符集是比C语言变量命名所允许的字符集更广泛的，因此，Zephyr规定，在C语言中访问DeviceTree的内容时，名称内的字母全部都变成**小写字母**、且特殊符号都变成**下划线**。
>
> ​	例如`zephyr,user`变为`zephyr_user`；`my-gpio`变为`my_gpio`。

​	我们无需关心`devicetree_generated.h`文件本身的内容，因为它不是给人看的，需要使用一套宏函数来将其读出。在需要操作DeviceTree的文件中包含以下头文件：

```c
#include <zephyr/devicetree.h>
```

这里给出一个示例：

1. 在overlay文件中新增一个属性，表示自己需要一个GPIO进行测试，属性名称为`test-gpios`。这是一个gpio specifier。

```
/{
    zephyr,user {
        test-gpios = <&gpio0 17 0>;
    };
};
```

2. 在`main.c`中，获取这个specifier，并操作GPIO

```c
#include <zephyr/drivers/gpio.h>

// 自己想要操作的节点的id，这里想要操作的节点是zephyr,user
#define NODE_ID DT_PATH(zephyr_user)

// 获取到zephyr,user节点的test-gpios属性，并把它作为gpio specifier，读入GPIO驱动。
static const struct gpio_dt_spec test_io = GPIO_DT_SPEC_GET(NODE_ID, test_gpios);

// 实际代码
int main()
{
    // 判断设备（这里是gpio控制器）是否已初始化完毕
    // 一般情况下，在application运行前，zephyr驱动就已经把控制器初始化好了
    if (!device_is_ready(test_io.port)) {
        return;
    }
    
    // 重新配置IO
    // 如果DeviceTree里写好了，这里也可以不配
    gpio_pin_configure_dt(&test_io, GPIO_OUTPUT_INACTIVE);
    
    
    // 操作IO
    gpio_pin_set_dt(&test_io,1);
    gpio_pin_set_dt(&test_io,0);
    
    return 0;
}
```



## 6.1. 获取节点ID

​	DeviceTree的一切信息都包含在属性之中。要想获得属性，首先要获得节点ID（node identifier）来作为句柄。获得节点id的方式有很多：

| **获取方式** | **示例**                        | **说明**                                              |
| ------------ | ------------------------------- | ----------------------------------------------------- |
| 根节点       | `DT_ROOT`                       | 根节点id                                              |
| 绝对路径     | `DT_PATH(soc, serial_40001000)` | `/soc/serial@40001000  `                              |
| Label        | `DT_NODELABEL(serial1)`         | 根据dts中定义的label来找到节点                        |
| chosen节点   | `DT_CHOSEN(zephyr_console)`     | 根据dts中chosen节点的配置：     zephyr,console=&uart0 |

​	获得节点id的方式还有很多：通过父节点找子节点、通过子节点找父节点等等。详细不多赘述，可参考：
 [https://docs.zephyrproject.org/latest/build/dts/api-usage.html#node-identifiers](https://docs.zephyrproject.org/latest/build/dts/api-usage.html)

​	但是有一种方式需要注意，它与最后一节讲的Zephyr驱动自动初始化息息相关。那就是通过**实例ID**的方式获取节点ID。所谓实例，就是指，同一个`compatible`，可能在一个dts中有多个实体。比如`nordic,nrf-timer`，可能一颗MCU上有很多timer。把它们按照在dts中出现的顺序进行编号，就是实例ID。实例ID从0开始。

​	比如：`DT_INST(0, nordic_nrf_timer)`，对应的就是`nordic,nrf-timer`的第0个实例节点。

​	通过实例ID获取节点ID的好处在于，可以通过遍历的方式来一次性获取到同一个compatible下所有的节点。这正是Zephyr能够在Application运行前就能找到所有dts中配置好的硬件的基础。

> 注意，所有Device Tree API都是宏，是预编译的结果。因此：
>
> - API参数必须是常量。不能在`for(int i=0;i<n;++i)`的**运行时**循环中用变量`i`去调用INST的API；
> - 调用API的过程也必须在编译时就完成。也就是说API宏的返回值只能赋值给const变量，不能在**运行时**调用，赋值给非const的任何变量。

## 6.2. 获取属性

利用DeviceTree API，输入节点id和属性名称，就可以获得属性。

### 检查属性是否存在

​	使用node id和小写、下划线命名的属性名称

示例：查找`i2c1`节点的`clock-frequency`属性。

```c
DT_NODE_HAS_PROP(DT_NODELABEL(i2c1), clock_frequency)  /* 宏展开为 1 */
DT_NODE_HAS_PROP(DT_NODELABEL(i2c1), not_a_property)   /* 宏展开为 0 */
```

>DTS里允许的所有特殊符号`「-」 「,」 「#」 「@」`在C源码里都要变成`「_」`，且字母都要变成小写。

> 如果是布尔类型，直接使用下面介绍的`DT_PROP()`即可。不要再使用`DT_HAS_PROP()`判断其是否存在。

### 获取普通属性

​	整数、布尔、字符串、数组、字符串数组都是普通属性，用`DT_PROP(node_id)`读取。

整数与字符串示例：

```c
DT_PROP(DT_PATH(soc, i2c_40002000), clock_frequency)  /* 宏展开为 100000, */

#define I2C1 DT_NODELABEL(i2c1)
DT_PROP(I2C1, status)  /* 宏展开为 "okay" */
```

数组示例：

​	假设dts为

```dts
foo: foo@1234 {
        a = <1000 2000 3000>; /* array */
        b = [aa bb cc dd];    /* uint8-array */
        c = "bar", "baz";     /* string-array */
};
```

则C代码中可以写作：

```c
#define FOO DT_NODELABEL(foo)

int a[] = DT_PROP(FOO, a);           /* {1000, 2000, 3000} */
unsigned char b[] = DT_PROP(FOO, b); /* {0xaa, 0xbb, 0xcc, 0xdd} */
char* c[] = DT_PROP(FOO, c);         /* {"foo", "bar"} */

// 获取数组的长度
size_t a_len = DT_PROP_LEN(FOO, a); /* 3 */
size_t b_len = DT_PROP_LEN(FOO, b); /* 4 */
size_t c_len = DT_PROP_LEN(FOO, c); /* 2 */
```

### 读取reg属性

- 获取reg blocks数量：`DT_NUM_REGS(node_id)`

- 若只有1个block，则直接读取其地址和长度：

  - `DT_REG_ADDR(node_id)`

  - `DT_REG_SIZE(node_id)`

- 若有多个block，则需要通过下标来索引

  - `DT_REG_ADDR_BY_IDX(node_id, idx)`
  - `DT_REG_SIZE_BY_IDX(node_id, idx)`

  > 注意，node_id和idx都必须是常量。因为宏的值在编译时就已经展开，因此不能放在循环里运行。

### 读取interrupts属性

- 获取interrupt specifier数量：`DT_NUM_IRQS(node_id)`

- 获取interrupt specifier：通过node id，下标和val来访问中断配置

  ```c
  DT_IRQ_BY_IDX(node_id, idx, val)
  ```


> val的含义：
>
> ​	是中断控制器devicebind文件中规定的结构体成员名。
>
> ​	以设备树中的`/soc/peripheral/adc@e000`节点为例，节点中未指明interrupt parent，故从设备树向上推断，推到`/soc`节点，此节点指明中断控制器是`&nivc`，即`/soc/interrupt-cntroller@e000e100`，其device-binding是`"arm,v8m-nvic"`。
>
> ​	在`ncs/zephyr/dts/bindings/interrupt-controller/"arm,v8m-nvic.yaml"`文件中，指明了interrupt specifier的解析方式：
>
> ```yaml
> interrupt-cells:
> 	- irq
> 	- priority
> ```
>
> 所以，`adc`节点中的：
>
> ```
> interrupts = < 0xe 0x1 >;
> ```
>
> 可被解析为：
>
> ```c
> #define ADC_NODE DT_NODELABEL(adc)
> 
> int irq = DT_IRQ_BY_IDX(ADC_NODE, 0, irq) // 中断号是0xe
> int priority =  DT_IRQ_BY_IDX(ADC_NODE, 0, priority) // 优先级是priority
> ```

### 读取phandle属性

例如，dts中有：

```
n1: node-1 {
	foo = <&n2 &n3>;
};

n2: node-2 { ... };
n3: node-3 { ... };
```

则可在C代码中，通过`n1`节点找到另外两个节点的node id：

```c
#define N1 DT_NODELABEL(n1)\
DT_PHANDLE_BY_IDX(N1, foo, 0) // node identifier for node-2
DT_PHANDLE_BY_IDX(N1, foo, 1) // node identifier for node-3
```

## 6.3. 遍历宏

​	前面提到，DeviceTree API都是宏，不能在代码运行时用循环语句（for和while）来调用。但是DeviceTree API提供了遍历展开宏。如：

- 对设备树中的每一个节点都调用宏函数`fn`
  ![image-20230312213721605](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined395d7f04b2ee82134df5c174e3919540.png)
- 对设备树中的每一个status为okay的节点调用宏函数`fn`
  ![image-20230312213728227](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined968a16fe289e766fd66ecb2bb3994a2d.png)
- 对一个节点的所有子节点遍历调用宏函数`fn`
  ![image-20230312213734780](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedc60d060f56caa9df44716a8848900588.png)

> 更多遍历API，请参考： [https://docs.zephyrproject.org/latest/build/dts/api/api.html#for-each-macros](https://docs.zephyrproject.org/latest/build/dts/api/api.html)

​	这些API看似是循环，实际上是在预编译时，把所有遍历的可能性全部展开。

​	实际上Nordic提供的很多Zephyr驱动，都是用遍历宏来创建外设相关的变量（例如config结构体），从而能调用nrfx api来完成实际的初始化。

​	举一个实际的例子，在`${NCS}/zephyr/drivers/led/led_gpio.c`中，定义了：

```c
#define DT_DRV_COMPAT gpio_leds
```

​	有了这个定义，就可以使用Inst API来访问`compatible = "gpio-leds"`的所有led，如下：

```
leds0 {
    compatible = "gpio-leds";
    status = "okay";
    label = "LED1";
    led0: led_0 {
        gpios = <&gpio0 4 0>;
        label = "Green LED 1";
    };
};
leds1 {
    compatible = "gpio-leds";
    status = "okay";
    label = "LED2";
    led1: led_1 {
        gpios = <&gpio0 5 0>;
        label = "Green LED 2";
    };
};
```

`DT_DRV_INST(0)`表示led0的Node ID，等价于`DT_INST(0, gpio_leds)`

`DT_DRV_INST(1)`表示led1的Node ID，等价于`DT_INST(1, gpio_leds)`

> 因为`devicetree.h`中，有
>
> ````c
> #define DT_DRV_INST(inst) DT_INST(inst, DT_DRV_COMPAT)
> ````

​	Inst API提供了基于**下标**的访问DeviceTree节点的方式。

​	接下来，下图用宏函数的方式定义了一个代码模板，内部定义了led 驱动程序所需的变量、device结构体等。所有内部调用的宏函数都是基于实例ID的INST API。

![image-20230312214413238](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined4c40e187558082028a0ad67548d97e84.png)

​	最后，用**遍历宏**调用了前面的代码模板。这个遍历宏的效果是：对所有`status="okay"`，且`compatible="gpio-leds"`的节点，执行一次上面的宏函数。

​	zephyr就是用这种方式，在驱动代码中自动遍历所有`status="okay"`的节点，提取其信息，然后用遍历宏来定义驱动结构体，在kernel启动之前就把硬件的初始化给完成。

## 6.4. specifier硬件支持

Device Tree API 中还有很多硬件支持的宏，方便你直接读取specifier等。具体可参考：

[https://docs.zephyrproject.org/latest/build/dts/api/api.html#hardware-specific-apis](https://docs.zephyrproject.org/latest/build/dts/api/api.html)

https://docs.zephyrproject.org/latest/hardware/index.html

这里以ADC的硬件支持宏为例。例如，一个节点为：

![image-20230312214651795](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined86133cb55de67f740b982bd039f77fa6.png)

使用`ADC_DT_SPEC_GET_BY_IDX(node_id, idx)`,就会展开为：

```c
{
   .dev = xxxx,
   .channel_id = xxxx,
   .channel_cfg = xxx,
   .vref_mv = xxxxx,
   /*...*/
}
```

刚好和zephyr的adc驱动中定义的adc channel结构体的成员一致

这就是为什么我们可以直接写：
```c
const struct adc_dt_spec my_adc_channel_0 = ADC_DT_SPEC_GET_BY_IDX(zephyr_user, 0);
const struct adc_dt_spec my_adc_channel_1 = ADC_DT_SPEC_GET_BY_IDX(zephyr_user, 1);
const struct adc_dt_spec my_adc_channel_2 = ADC_DT_SPEC_GET_BY_IDX(zephyr_user, 2);
```

如果用上前面说的遍历宏，还能更加简单，直接生成数组：

```c
// 给一个specifier对应的大括号末尾加上逗号
#define DT_SPEC_AND_COMMA(node_id, prop, idx) \
	ADC_DT_SPEC_GET_BY_IDX(node_id, idx), // <--逗号加在这里
	
// 使用遍历宏直接把所有specifier读进数组
// 这些宏展开后相当于三个结构体初始化大括号，中间用逗号分隔
static const struct adc_dt_spec adc_channels[] = {
	DT_FOREACH_PROP_ELEM(DT_PATH(zephyr_user), 
                         io_channels,
			     		DT_SPEC_AND_COMMA)
};
```

# 7. Zephyr Driver的实现方式

## **什么是驱动程序？**

​	驱动程序是面向对象的。首先要有一个被操作的对象，然后才有驱动程序。这个被操作的对象就是 **device结构体**。 device结构体本身是抽象的，没有具体的含义:

```c
struct device {
    const char *name;           // 设备的名称
    const void *config;         // 设备的初始配置
    const void *api;            // 设备的api函数集合
    struct device_state *state; // 设备的工作状态
    void *data;                 // 设备的运行数据
    /* ... */                   // 其他参数，例如电源管理，后续有专门文章讲解
};
```

​	驱动程序在Appilication程序运行之前，就把硬件初始化做好，然后定义好device结构体的内容。下图中的五个红色的主要级别都是可以定义驱动程序初始化的时间，每个级别内还可以再细分优先级。

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined77d2406ba261597178b0d36600e30cb1.png" alt="image-20230312215847338" style="zoom:67%;" />

## 在Application中如何拿到Device结构体？

​	如果说，zephyr在系统初始化阶段就能把所有device结构体定义好。那么Application运行后，要如何拿到这些device呢？

### （1）通过Name的方式

​	这种方式，可以与DeviceTree完全无关。可以自己定义一个与DeviceTree无关的纯软件设备，也可以编写驱动程序。

  例程：`${NCS}/zephyr/samples/application_development/out_of_tree_driver` 中，介绍了out of tree driver的写法。

![image-20230312220123168](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined36587c6d0d23c19ee5ee3c2da5741fb3.png)

<center>驱动程序中，定义了device的name</center>

![image-20230312220147908](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined08bff552dbdc7adc43936dcb66d6c153.png)

<center>应用程序中，通过`device_get_binding()`函数获取device指针 </center>

### （2）通过DeviceTree的方式

![image-20230312220418544](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedc7cc7c4ea0d085fd0170066fcc8c2d2d.png)

​	在驱动程序中，通过`DEVICE_DT_DEFINE()`，定义了device结构体，并与DeviceTree中的节点绑定：

![image-20230312220359492](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined56a8d820ae7d67d757df46e2fee41af6.png)

在Application中，通过`DEVICE_DT_GET(node_id) `宏来获得这个device结构体

![image-20230312220423449](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined7af5b762e50a35d510e20c5739949982.png)

## Kconfig与DeviceTree

我们修改`prj.config`中的`CONFIG_XXXX`选项、修改dts中的`status`属性，其本质是在做什么？

![image-20230312220546761](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined6af4a5fd34342ac97ca973360c0495af.png)

![image-20230312220553466](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined7db53c5bf3b3d66173a253663a0aa372.png)

综合前面介绍的device tree、遍历宏的内容，我们可以知道：

1. 修改driver相关的config选项，其本质是让CMake把驱动程序包含进来。**只要启用了相关config，驱动程序就会载入，固件就会变大。**
2. 修改status为”okay”，其本质是，让驱动程序在使用遍历宏创建device结构体时，能够为这个okay的节点创建device对象。

**只有两者都启用，硬件节点才真正的被驱动了，application中才能真正的操作这个节点。**

![image-20230312220655857](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb4500d1060ec13178cb044f32d0e79ba.png)

## Zephyr标准驱动

Zephyr是一个跨平台的操作系统，自然少不了对各类标准硬件的跨平台支持。

详见：https://docs.zephyrproject.org/latest/hardware/peripherals/index.html

![image-20230312220754929](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined7b74a2d78abbeb61b9fd7f9a597846b3.png)



这里以Counter为例：

> 在Zephyr中，Timer指的是内核软定时器，而Counter指硬件定时器

在`zephyr/include/zephyr/drivers/counter.h`中，规定了zephyr标准的counter应该具有哪些api。

在`zephyr/drivers/counter/`目录下，有各个厂商对自家MCU产品写好的timer驱动，全部都符合zephyr标准的API。

在Kconfig中启用counter驱动时，zephyr build system就会自动把板子对应厂商的counter驱动编译进来。

![image-20230312220830650](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedaf74dbd6381a6ca7283a48edd2358dda.png)

## Zephyr标准驱动支持硬件的全功能吗？

​	很遗憾，答案是**不能**。Zephyr只支持**最基础**、**最标准**的硬件驱动，不支持各个厂商的硬件特性。

​	例如nrf系列的PPI，非常方便，zephyr没有为PPI提供标准驱动，因为其他厂商平台并没有这个功能，所以是不可能有「device tree里写一下配置，PPI就自动连好了」这种操作的。Nordic外设的`SHORT`寄存器也是同理。

​	下面是一段混合代码：

- 前半部分，zephyr标准已经自动初始化好timer0，所以可以用counter api，配置计时；
- 后半部分，利用nrfx api，来连接short寄存器，让timer0计时结束后，自动触发clear。

![image-20230312221017468](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined0aeedf4d6d9222ba469b9ea7792171ac.png)

> 这里还有个注意事项：
> 	nrf timer本身没有overflow事件，所以把channel 0拿去设置top value了；此外，还把channel 1拿去做输入捕获了。
>
> ​	因此，nrf timer暴露给zephyr标准驱动的通道就少了两个，实际上zephyr counter的通道0，是硬件定时器的通道2。

# 8. 总结

1. DeviceTree描述的是**板卡级**的硬件信息。DeviceTree是树型逻辑结构，层次关系是由**总线的主从关系，**以及**硬件的包含关系**决定的 。
2. DeviceTree的基本单元是节点（Node），节点具有一个**名称**和多条**属性**。可以给节点增加标签（label），来便于引用这个节点。
3. 板卡级的dts文件可以引用芯片级的dtsi文件，也可以引用.h头文件，从而使用其定义的枚举值和宏。
4. 用户可以在自己的工程里通过写overlay的方式，来覆写原始board dts里的配置
5. Zephyr Build System在构建时会合并所有的dts以及overlay，生成最终的zephyr.dts，并导出为devicetree_generated.h头文件
6. DeviceTree本身的语法只提供了一个基于总线主从关系的树形层次结构，此外每个节点可以用属性来存储信息。语法本身并没有规定硬件要如何描述。DeviceTree中的一些常见属性，补充了这方面的空缺。
   - reg、ranges、#address-cells、#size-cells这四个属性描述了总线上的地址分布
   - status属性描述了设备是否使能
   - compatible属性描述了设备的兼容性
7. 在DeviceTree中，除了本身的树形结构以外，还具有一些逻辑上的树形结构，称为域。域具有**控制器**和设备节点，控制器是真正实现域的功能的硬件外设，而设备节点只是为了开发方便解耦而进行的一种抽象。
8. 真正限制device tree中属性该如何写的，是device binding文件。binding文件是芯片厂商提供的。有了binding文件，就可以在VS Code中实现自动的检查与补全。Zephyr实际构建项目时，也是参考binding文件来检查dts的正确性。只有dts按照正确的规则写了，zephyr的驱动代码才能识别到硬件配置，进行自动初始化。
9. zephyr中会有一些特殊的虚拟节点来为开发提供便利。
10. 要从C语言中访问DeviceTree中的信息，需要先获得node id。用绝对路径、label、chosen、alias等许多方法都可以获取一个节点的node id。其中要注意的是通过实例id的方法（INST）
11. 有了node id，就可以获取node的属性。普通的属性与reg、phandle、interrupt属性的获取API不相同。
12. zephyr还提供了遍历宏，从而可以针对特定条件的节点/属性遍历执行宏函数。
13. Zephyr用前面提到的通用API，封装出了各种硬件支持API，方便直接读取各种硬件指定的specifier。
14. Zephyr驱动程序，在Application运行之前就会执行初始化，并且定义device结构体。
15. Application可以通过Name或者Node id的方式，获得device结构体
16. 我们在Kconfig中使能driver，本质上是载入了驱动程序，固件会变大。在dts中把节点的status设为okay，本质上是让驱动程序在初始化时，能够自动搜到这个节点，并为这个节点创建device实例。
17. Zephyr的标准驱动，让各个厂商都实现了相同功能的驱动API代码，从而实现了跨平台的统一驱动。
     但是如果想要使用硬件特性的功能，就还是必须使用厂商自己的driver library或者直接写寄存器。
