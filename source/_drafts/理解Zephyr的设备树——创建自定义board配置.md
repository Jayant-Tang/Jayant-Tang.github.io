---
title: 理解Zephyr的设备树——创建自定义board配置
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
cover:
tags:
categories:
---

# 1. 简介

​	对于初学者而言，要理解Zephyr的设备树是一个门槛。但是，其实我们早已领会一些思路了，例如，我们在做单片机裸机开发时，经常会使用宏来代替实际被操作的硬件：

```c
#define GPIO_LED1_PORT GPIOA
#define GPIO_LED1_PIN GPIO_PIN_1


void main()
{
 	...
    gpio_init(GPIO_LED1_PORT, GPIO_LED1_PIN);
    ...
}
```

​	我们的驱动代码中只操作“LED的GPIO”，但是“LED的GPIO”到底是什么，就由宏去定义。这就是把**驱动代码**和**硬件细节**进行分离的方法。

​	那么，更进一步，能不能有一种方法，能定义整个板子，包括芯片的硬件细节呢？这样，理想情况下，只需要写一套驱动代码，后面不论更换什么板子、什么芯片平台，都不用改代码了，只用写一个新的板子的配置文件就好。

​	Zephyr和Linux选择的方式是使用Device Tree Source (DTS) 来描述硬件。Zephyr在编译时会把dts转换成有一堆宏的头文件，而Linux会把dts编译成Device Tree Binary (dtb)。

​	一旦有了标准，我们就可以定义自己的dts来描述硬件，进而就可以使用各类官方提供的驱动库来驱动硬件，而不必自己实现了。相信做过单片机裸机开发的都明白，虽然应用很简单，但是大部分时间都花在调试硬件、寄存器、通信协议上面了。如果能用上标准的驱动库，对效率会是很大的提升。

​	在NCS仓库中`zephyr/boards`目录下，Zephyr收录了各个厂商、各个架构的**开发板**的dts配置。在`nrf/boards`目录下，收录了Nordic的各种未提交给Zephyr项目的**开发板**、**评估板**的配置。

​	板子的配置可以include芯片配置，芯片的配置描述了这颗芯片上的flash、ram、外设寄存器等硬件资源。芯片的配置保存在`zephyr/dts/`下，收录了各个架构、各个厂商的部分。

​	本文不详细介绍dts的语法。而是从零开始，创建一个自己的`.dts`文件，来描述自己的板子。从而理解Zephyr的驱动模型。

​	
