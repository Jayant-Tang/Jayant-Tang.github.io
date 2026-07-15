---
title: 理解Zephyr项目的配置与构建系统
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2022-12-04 23:26:26
cover: null
tags:
- Nordic
- Zephyr
- Kconfig
- CMake
categories: Zephyr
cnblogs:
  postId: '17794813'
  url: https://www.cnblogs.com/jayant97/articles/17794813.html
  lastPublishedAt: '2026-07-06T18:20:52+08:00'
  sourceHash: sha256:8b7aaed08fc9c9b74f77a4d904c37b070afcfcb07be66f1a3917ec4ef833da32
  status: imported
  postType: Article
---

> 本文更新于2025.01.06，增加了对NCS2.7.0新引入的Sysbuild的介绍。补充了一些说明，使本文更详尽。

# 1. 前言

Zephyr Project是Linux基金会推出的一个Apache2.0开源项目，版权非常友好，适合用于商业项目开发。包含RTOS、编译系统、各类第三方库。NCS中的例程基本都跑在[Zephyr RTOS](https://docs.zephyrproject.org/latest/kernel/index.html)上。

对于之前只接触过IDE+外设驱动库这种开发方式的开发者来说，Zephyr的配置和编译系统可能比较令人费解，但是一旦你能掌握，就会发现它的方便之处。

本文重点介绍了NCS中的配置和编译工具。其中包含一些其他开发环境中常见的CMake，Kconfig，DeviceTree等的简单介绍，和Zephyr中特有的**Sysbuild**、**Boards**，以及Nordic提供的**Partition Manager存储器分区**等介绍。

# 2. 通过CMake管理源码

本节只简要介绍NCS中常见的CMake使用方法，篇幅有限不可能完整的介绍CMake。希望完整学习CMake的话可以参考[CMake官方文档](https://cmake.org/cmake/help/latest/guide/tutorial/index.html#guide:CMake%20Tutorial).

## CMake基本写法

通过`zephyr/samples/hello_world`例程的`CMakeLists.txt`，我们可以看到：

```cmake
# SPDX-License-Identifier: Apache-2.0

# 指定CMake版本
cmake_minimum_required(VERSION 3.20.0)

# 从系统环境变量${ZEPHYR_BASE}找到NCS中的Zephyr安装目录
# 并把整个Zephyr系统当作包来导入
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})

# 设定项目名称
project(hello_world)

# 把main.c添加为app目标的源码
target_sources(app PRIVATE src/main.c)
```

这里的编译目标是`app`，最终会编译为`libapp.a`，也就是把用户自己的应用层代码编译成库的形式。最后再链接进Zephyr系统。

这里的 `PRIVATE` 控制的是链接内容的可见性：

- `PRIVATE`：`main.c` 只属于 `app` 目标。修改后会重新编译 `app` 目标，并触发最终固件重新链接。Zephyr 应用层源码基本都用
  `PRIVATE`。
  - `PUBLIC`：`main.c` 除了属于 `app` 目标，还会传播给依赖 `app` 的其他 target。普通应用源码不应使用
  `PUBLIC`，否则容易引入不必要的依赖传播。

## 条件添加源码

条件添加也很好理解，就是某个CMake变量值为true时，才把源码添加到目标中去。例如：

```cmake
# Include UART ASYNC API adapter
target_sources_ifdef(CONFIG_BT_NUS_UART_ASYNC_ADAPTER app PRIVATE
  src/uart_async_adapter.c
)
```

这里就是`CONFIG_BT_NUS_UART_ASYNC_ADAPTER`为`y`时，才添加`src/uart_async_adapter.c`到源码中。

## 把整个目录添加源码

有时目录层级很多，我们没必要在一个CMakeLists.txt里把所有源码都添加完。

```text
|-CMakeLists.txt
|-aaa
|  |-CMakeLists.txt
|  └-main.c
└-bbb
   |-CMakeLists.txt
   └-hello.c
```

这时，就可以在项目根目录的CMakeLists.txt中写：

```cmake
add_subdirectory(aaa)
add_subdirectory(bbb)
```

然后在两个子目录的CMakeLists.txt中添加对应的源码。

当然，目录也是可以条件添加的，最典型的就是在`${NCS}/zephyr/drivers/CMakeLists.txt`中：

```cmake
add_subdirectory_ifdef(CONFIG_ADC adc)
```

也就是说，只有启用了`CONFIG_ADC=y`，Zephyr才会去编译`${NCS}/zephyr/drivers/adc/`目录下的驱动。

此外，如果再去看`${NCS}/zephyr/drivers/adc/CMakeLists.txt`：

```cmake
...
zephyr_library_sources_ifdef(CONFIG_ADC_MCUX_LPADC	adc_mcux_lpadc.c)
zephyr_library_sources_ifdef(CONFIG_ADC_SAM_AFEC	adc_sam_afec.c)
zephyr_library_sources_ifdef(CONFIG_ADC_NRFX_ADC	adc_nrfx_adc.c)
zephyr_library_sources_ifdef(CONFIG_ADC_NRFX_SAADC	adc_nrfx_saadc.c)
...
```

就可以看到，这里又根据不同的MCU平台，来添加对应的adc驱动代码。

总而言之，一个Zephyr 项目和 Zephyr SDK 本身都是通过 CMake 来组织源码的：

![image-20260715100804747](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined1b95ebf78d32cdc23472ec60aaf4ef5b.png)

## 添加include目录

也就是存放头文件的目录，如：

```cmake
# 添加CMakeLists.txt所在目录下的inc/目录到app目标
target_include_directories(app PRIVATE inc)

# 也是可以条件添加的
zephyr_include_directories_ifdef(CONFIG_MEMFAULT configuration/memfault)
```

## 设置变量

和宏定义类似，把A定义成B。主要是用来定义一些编译系统会用到的东西，例如：

```cmake
# 指定自己项目的device tree overlay文件
set(DTC_OVERLAY_FILE app.overlay)
```

除了上述直接把变量定义写在CMakeLists.txt内，还可以在命令行编译时，通过`-D`选项传入的参数：
```bash
west build -b nrf52840dk/nrf52840 -d build --sysbuild -- -D DTC_OVERLAY_FILE=app.overlay
```

> 注意，CMake参数的传递在`--`之后，再用多个`-D`分别传入。

上述通过编译命令添加的CMake变量，也可以在nRF Connect for VS Code的界面中编译时输入：

![image-20250106223923162](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250106223923162.webp)



在CMakeLists.txt中用`set()`函数，或者在命令行编译时用`-D`参数，都可以设置你**自定义**的变量。但是更多时候，还是用来设置Zephyr编译系统的一些选项，这里给出一个表格，方便查找：


### 通过CMake直接修改Kconfig配置项

直接在CMake中指定某个Kconfig选项的值。

命令行参数：

```bash
-D<name_of_Kconfig_option>=<value>
```



以下为常见的配置项

### CONF_FILE

设置当前工程的Kconfig基本配置文件。通常是prj.conf。

命令行参数：

```bash
# 设置默认的配置文件
-DCONF_FILE=<file_name>.conf

# 设置特定Build Type下的配置文件
-DCONF_FILE=prj_<build_type_name>.conf`
```

### SHIELD

很多器件厂商/模块商会制作一个开发板的扩展板。为了方便，会把启用这个扩展板所需的配置项打包在一起，就是 SHIELD。

尤其是很多开发板都是支持 Arduino 接口的，因此 Zephyr中有很多 Arduino 接口的 Shield。如图是一个 nRF21540 PA/LNA（射频放大器）扩展板：

![image-20231028214708544](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028214708544.webp)

在一个工程中启用Shield之后，这些扩展板的配置（包含device tree和Kconfig）就会被载入到你的当前工程中。

如果要在工程中启用扩展板，则需要设置CMake变量：

```cmake
set(SHIELD nrf21540_ek)
```

或者在编译目标的配置中添加CMake参数：

![image-20231028215131762](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028215131762.webp)

编译时，会自动合并原始板子和扩展板的Kconfig和Devicetree。

### 更多CMake配置项，请参考[<u>Providing CMake Options</u>](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/app_dev/config_and_build/cmake/index.html#providing_cmake_options)

## 打包链接库

CMake支持将部分源码编译为子库：

```
link_lib_sample/
    │  CMakeLists.txt
    │  prj.conf
    │
    └─src/
        │  main.c
        │
        └─my_lib/
                CMakeLists.txt
                lib_src.c
                my_lib.h
```

`./src/my_lib/CMakeLists.txt`

```cmake
# SPDX-License-Identifier: Apache-2.0

# 创建独立的静态库文件 my_static_lib
add_library(my_static_lib STATIC
    lib_src.c
)

# 设置库的包含目录
target_include_directories(my_static_lib PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# 关键：链接zephyr_interface以获取Zephyr的头文件和配置
target_link_libraries(my_static_lib PRIVATE zephyr_interface)

# 链接静态库到主应用程序
target_link_libraries(app PRIVATE my_static_lib)
```

> 独立的链接库，没有`find_package()`到Zephyr。所以必须要单独链接`zephyr_interface`这个库，才能在代码中获取到Zephyr的API，CONFIG值，配置的设备树等信息。

在主应用中连接子库：

`./CMakeLists.txt`

```cmake
# SPDX-License-Identifier: Apache-2.0

cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(link_lib_sample)

target_sources(app PRIVATE src/main.c)

add_subdirectory(src/my_lib)
```

最终输出位置：

`build/<project_name>/<path_to_lib_cmake>/lib<name>.a`

![image-20250818130428707](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedimage-20250818130428707.webp)



> 编译后的库文件名会在库名称前加`lib`，并带有`.a`后缀。

## 链接静态库

要连接已经编译好的静态库，可以把`.a`静态库拷贝到工程中，然后进行添加：

```cmake
# SPDX-License-Identifier: Apache-2.0

# 导入库文件
add_library(my_static_lib STATIC IMPORTED GLOBAL)
set_target_properties(my_static_lib PROPERTIES
    IMPORTED_LOCATION "${CMAKE_CURRENT_SOURCE_DIR}/libmy_static_lib.a"
)
set_target_properties(my_static_lib PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${CMAKE_CURRENT_SOURCE_DIR}"
)

# 将静态库链接到应用程序
target_link_libraries(app PUBLIC my_static_lib)
```

## 总结

项目通过CMake管理源码和include目录。项目本身会把应用代码编译成`build/app/libapp.a`，最后和Zephyr系统一起链接成可执行文件。

Zephyr系统本身的内核、库、驱动等源码也都是用CMake来管理的。



# 3. 通过Kconfig管理配置

一个编译系统中，肯定有很多配置项的需求，如：

- 布尔类型：开关某些功能，决定一些库和内核功能代码是否参与编译
- 枚举类型：配置某些预设好的功能，比如日志打印级别(ERR/WRN/INF/OFF)等
- 数值类型：设置具体参数，如线程栈大小、蓝牙MTU Size大小等

以上功能当然可以通过宏定义来实现。但是宏的作用比较有限，且所有的宏都是平等的，无法结构化地管理。

Kconfig就是用来结构化地管理整个项目以及SDK中所有的配置项的。

在Zephyr系统中，RTOS内核、各个功能模块都会有自己的配置项；并且，开发者自己的项目也会有很多配置项。这些配置项之间可能还有依赖关系。

Kconfig就是把一个模块的**所有配置项组成一个菜单**。所有模块的菜单，通过层级关系拼接在一起，形成一个大菜单。菜单有默认配置项，开发者可以随意修改配置项。只需把自己和默认配置项有差异的部分写到一个**配置文件（*.conf）**中，就可以方便地进行配置项的管理了。

在管理配置项时，Kconfig相比于宏定义有许多优势：

1. Kconfig不止适用于源码。编译系统（CMake）也可以用到其中的配置来决定源码是否参与编译。
2. Kconfig是结构化的，可以规定配置项之间的依赖关系；支持提前枚举好允许的配置范围。
3. Kconfig菜单方便互相引用。一个功能库在提供源码和API之外，还会提供一个Kconfig菜单，方便开发者使用。
4. 配置项可以保存到配置文件中。多个配置文件可以合并、覆盖。

## Kconfig交互式菜单

我们知道，Kconfig实际上是定义了一个菜单，在哪里能看到这个菜单呢？

我们可以在VS Code中点击nRF Kconfig GUI:

![image-20231028192036882](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028192036882.webp)

也可以把鼠标悬浮在这个按钮上，点右边的三个点，然后用Guiconfig（弹窗）或Menuconfig（命令行）的方式进行配置。

![image-20260715101044354](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined22aea482320c9a1d7b53c884b2986c8d.png)

![image-20260715101100699](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined8802b841197e62dd53a55f66a028a2ac.png)

如下为 nRF Kconfig GUI：

![image-20231028192424706](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20231028192424706.webp)

Menuconfig：
```shell
west build -t menuconfig
```

![image-20260715101506351](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined047f07b675ebc7a41493615b706af325.png)

## 修改并保存配置项

如果我们只是单纯点击界面右上角的"Apply"，那么这些配置是保存在`.config`中的。这是编译过程中生成的一个**临时文件**，是把各种配置项来源整合到一起，得到的最终配置文件。

如果我们进行 pristine build，那么`.config`文件就会重新生成，我们之前的修改就消失了。

**要想永久保存，应该点击“save to file”。然后保存到配置文件（如`prj.conf`）中。**

当你熟练后，就不需要再去这个菜单中找选项了，直接修改配置文件（如`prj.conf`）即可。

## 构建时配置项的合并

配置项有许多来源。在构建可执行文件时，会在configure阶段，compile之前，对所有来源的配置项按顺序进行合并，合并后的文件就是前面说的临时配置文件`.config`，路径为：

`<build_dir>/<application_name>/zephyr/.config`

![image-20250106233645472](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250106233645472.webp)

> 注：在NCS v2.7.0之前，未采用Sysbuild。不使用Sysbuild时，合并后的配置文件位于`build/zephyr/.config`

那么，配置项总共有哪些来源呢？

1. Kconfig菜单中的默认值
2. 选择板子后，板子自带的一些config。可以在`zephyr/boards`或者`nrf/boards`中查看。
3. CMake变量`CONF_FILE`指定的配置文件内的配置项，**这也是最常用的**。默认情况下是以下两个文件：
   - 项目的`prj.conf`，它可以覆盖默认值；
   - 项目的`boards/<board_name>.conf`，当编译目标中选择的板子和这里的board_name一致时，可以覆盖默认值。此配置和前一项会合并。
4. CMake变量`EXTRA_CONF_FILE`指定的额外配置文件，也就是在VS Code中创建新的build target时，可以选择的"Extra Kconfig fragments"

## 了解Kconfig菜单基本写法


可以先从一个简单的例子`${NCS}/nrf/samples/bluetooth/peripheral_uart`来参考：

```Kconfig
# 引用Zephyr的Kconfig菜单
source "Kconfig.zephyr"

# 自定义本项目的菜单
menu "Nordic UART BLE GATT service sample"
   ... 此处省略...
endmenu
```

菜单中的选项，可以配置它的类型、说明，和 **默认值**：

```Kconfig
# 此选项用来设置Nordic UART Service线程的栈大小
# 并且具有默认值
config BT_NUS_THREAD_STACK_SIZE
	int "Thread stack size"
	default 1024
	help
	  Stack size used in each of the two threads
```

菜单中的选项可以**连锁使能 (select)**：

```Kconfig
# 当本选项被设置成 y 时，通过select，同时把CONFIG_BT_SMP的值设置成y
config BT_NUS_SECURITY_ENABLED
	bool "Enable security"
	default y
	select BT_SMP
	help
	  "Enable BLE security for the UART service"
```

此外，一个选项也可以指定一个**依赖项**。如果本选项被启用，但依赖项未被启用，则 configure phase 就会报错：

```Kconfig
# 配置是否在系统启动时，自动初始化USB ACM设备 （用于输出日志）
# 此配置依赖于CONFIG_USB_CDC_ACM=y，也就是说，起码要把USB_CDC_ACM的代码编译进来
config USB_DEVICE_INITIALIZE_AT_BOOT
	bool "Initialize USB device support at boot"
	depends on USB_CDC_ACM
	help
	  Use CDC ACM UART as backend for console, shell, or logging.
```

当然，Kconfig也不是说要写的非常大，把整个项目的配置都写进去。你也可以每个子文件夹下单独写Kconfig，然后在项目的Kconfig中进行包含：

```
# 通过绝对路径进行包含
source "xxx.Kconfig"

# 通过相对路径进行包含
rsource "src/xxx.Kconfig"
```

>某些简单例程，例如`zephyr/samples/hello_world`，没有什么配置项，所以是可以没有自己的Kconfig的。这种情况下，相当于直接用了Zephyr的Kconfig菜单，也就是相当于：
>
>```Kconfig
>source "Kconfig.zephyr"
>```

## 显性与隐性配置项

在 Kconfig 中定义菜单选项时，我们会发现，大多数选项，在变量类型后面会有一个**说明字符串(prompt)**。

如`bool`后面的`"Support floating point operations"`：

```Kconfig
config FPU
   bool "Support floating point operations"
   depends on HAS_FPU
```

这意味着，这个配置项会出现在Kconfig交互式菜单中，我们可以在 menuconfig 交互式菜单中修改它的值：

```menuconfig
[ ] Support floating point operations
```

也可以用`prj.conf`之类的配置文件来直接改它的值：

```conf
CONFIG_FPU=y
```

但是，也有一些**隐性配置项**，它们的变量类型后面不带说明字符串，我们无法直接修改它的值：

```Kconfig
config CPU_HAS_FPU
   bool
   help
     This symbol is y if the CPU has a hardware floating point unit.
```

这个 CONFIG 项表示的是一个 CPU 是否携带 FPU，这是硬件原本的属性。因此不能在开发者的工程里直接修改，这是很合理的。

这种配置，通常是通过**连锁使能select**的方式开启的。例如`v3.4.0/zephyr/soc/nordic/nrf52/Kconfig`：

```Kconfig
# 隐性配置项
config SOC_NRF52840
	bool
	select CPU_CORTEX_M_HAS_DWT
	select CPU_HAS_FPU
```

意思是当你的 SoC 芯片是 nRF52840时，自动打开 `CONFIG_CPU_HAS_FPU=y`。这种是不能被用户工程里的`prj.conf`修改的，只能自动设置。

> 具体逻辑链条：编译选择了 nrf52840 板子（自动设置`CONFIG_BOARD_NRF52840DK=y`） → 板子 Kconfig 菜单 `select SOC_NRF52840_QIAA` → SoC Kconfig菜单 `select SOC_NRF52840` → `select CPU_HAS_FPU`

## 总结

Zephyr 的配置系统是 Kconfig 定义的菜单。Zephyr 系统的每个子模块都有自己的菜单，工程需要把 Zephyr的菜单包含到自己的 Kconfig 菜单中。

工程内可以用 `prj.conf` 之类的文件来修改配置项的值。

Kconfig 中的配置项，可以影响 CMake 中的条件，选择是否添加哪些源码，从而剪裁内核。

Kconfig 中的配置项，最终会生成到`autoconf.h`中，成为源代码中也可以用到的宏。

> **不要去尝试修改隐性的 Kconfig 配置项**。如果编译时有“某配置项依赖未开启”的报错，而那个依赖恰好是隐性配置项，你需要去 SDK 内搜索那个隐性配置项是被什么条件`select`开启的。

# 4. Devicetree 和 Zephyr 驱动模型

Devicetree 比较复杂，具体的语法、使用方法可以参考我的另一篇文章：[《详解Zephyr设备树（DeviceTree）与驱动模型》](https://jayant-tang.github.io/2023/03/4b274a50e575/)。

本文中尽量简洁地说明 Devicetree 是什么，以及怎么用。

## Devicetree 是什么？

Devicetree 是一个[描述硬件信息的数据结构](https://www.devicetree.org/)，它的源码文件是 Device Tree Source (DTS)。

DTS 是为固件服务的，描述一个**板子**上的硬件信息，因此它要包含以下硬件信息：

- SoC 级别：SoC 上某个外设的寄存器地址范围是多少？中断号是多少？某个外设是否需要 enable？Flash 的内部分区如何划分，多少给 bootloader，多少给 app？
- 板子级别：SPI 用了哪几个引脚，主频用多少？SPI 外挂 Flash 的 jedec-id 是多少？时钟源用外部晶振还是内部 RC 振荡器？
- OS 级别：日志用哪个串口？Shell 用哪个串口？文件系统用哪个分区？

这些硬件信息有些是固有的，有些是需要能修改的。

## Devicetree 数据结构

如果单纯是为了存信息，列一个大的宏定义表就能做到。而 DTS 更进一步，把这些信息按照**总线关系**组织在一个**树形的数据结构**中：

- Boards → SoC  → SPI → 外部 NOR Flash
- Boards → SoC  → I2C → 外部传感器

开发者要按照这个树形结构来编写配置文件。在 Build 阶段会执行许多检查和自动化：

- 如果一个 SPI 控制器被 disable 了，那么挂在这个 SPI 上的外部 NOR Flash 就自然被 disable 了
- 如果 OS 要使用的串口没有被开启，Build 阶段会自动检查出来

在构建阶段，在 Configure Phase 结束后，DTS 会被转换成真正包含这些硬件信息的宏。

## DTS 文件

从 SDK 到你的工程，一共有这些 DTS 文件：

1. 芯片级的`*.dtsi`文件，定义了芯片上的各种外设资源及其地址；
2. 板级的`*.dts`文件，会包含（Include）芯片级的 dts 文件。然后定义板子上的资源，如按键、LED、i2c 等总线上挂的传感器等等；
3. 在工程中，如果想修改板子默认的 dts，是通过`*.overlay`文件进行覆盖；例如开发板默认的dts（SDK中的文件）默认没有打开串口1，那么就可以在Overlay文件（你的工程中的文件）中打开串口1；
4. 构建期间，所有这些 dts 会在编译目录下合并成`zephyr.dts`。这就是最终的 dts。

> #### 合并 dts 的位置
>
> NCS v2.7.0引入了 sysbuild，zephyr.dts 的路径为 `build/<application_name>/zephyr/zephyr.dts`;
>
> 在 NCS v2.6.x之前，zephyr.dts的路径为：`build/zephyr/zephyr.dts`;
>

## overlay 文件合并顺序

构建时可以用 CMake 参数主动指定 overlay 文件，并且可以指定多个：

```shell
west build -b <BOARD> -- \
  -DDTC_OVERLAY_FILE="file1.overlay;file2.overlay" \
  -DEXTRA_DTC_OVERLAY_FILE="file3.overlay;file4.overlay"
```

同一参数内，**越靠后的overlay优先级越高**。同时，`EXTRA_DTC_OVERLAY_FILE` 又比 `DTC_OVERLAY_FILE` 优先级高。

在 VS Code 中对应：

![image-20260714172223171](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined6d19937feb371458a23dcd308f0add2c.png)

如果你不指定 `DTC_OVERLAY_FILE`，那么 Zephyr 会有**自动优先级搜索**顺序。这里只给出**最常见的情况**：

1. 如果工程根目录下存在`boards/<BOARD>.overlay`，则使用它，**然后停止搜索**；
2. 否则，如果工程根目录下存在`<BOARD>.overlay`，则使用它，**然后停止搜索**；
3. 最后，如果工程根目录下存在`app.overlay`，则使用它。

完整的搜索顺序，请参考：[Devicetree HOWTOs](https://nrfconnectdocs.nordicsemi.com/ncs/3.4.0/zephyr/build/dts/howtos.html#set-devicetree-overlays)

> 因此，`app.overlay` 不是“所有板子的共有 overlay”，而是一个 fallback —— 指定板子的 overlay 找不到时，才用它。
>
> 可以用 `v3.4.0/nrf/samples/bluetooth/throughput`这个例程进行测试：
>
> 这个例程`boards/`目录下只有nRF53 系列以上的 overlay。老的 nRF52系列全走 `app.overlay`。
>
> 什么都不改，直接编译`nrf52dk_nrf52832`板子，能看到：
>
> ```text
> -- Found devicetree overlay: D:/ncs/v3.4.0/nrf/samples/bluetooth/throughput/app.overlay
> ```
>
> 把 `app.overlay`拷贝到 `boards/`下，重命名成`nrf52dk_nrf52832.overlay`，就能看到：
>
> ```
> -- Found devicetree overlay: D:/ncs/v3.4.0/nrf/samples/bluetooth/throughput/boards/nrf52dk_nrf52832.overlay
> ```
>
> `app.overlay` 被跳过了。
>
> 实际工程中不建议用`app.overlay`，尤其是在`sysbuild/mcuboot/app.overlay`这种情况，非常容易被跳过。

如果你想指定额外的 overlay，又不想破坏原本的**自动优先级搜索顺序**，就需要使用`EXTRA_DTC_OVERLAY_FILE`，不能使用`DTC_OVERLAY_FILE`。

## 修改 overlay

外设的使能与关闭，引脚的分配等与硬件相关的内容，都在 overlay 文件中编写。overlay 会覆盖板子的默认配置。

```
// 例如，在o verlay 中使能串口1. uart1是label，可以直接引用
&uart1 {
	compatible = "nordic,nrf-uarte";
	status = "okay";
}

// 另一种写法，不用label，而用绝对路径，不常用
/{
	soc{
		uart@40028000{
			compatible = "nordic,nrf-uarte";
			status = "okay";
		}
	}
}
```

修改时，注意不要修改SDK里的dts，因为这会影响其他的工程。只在自己的工程内用Overlay修改就好。

在 VS Code 中图形化查看设备树时，**一定要注意自己正在编辑的dts上下文**。如果你正在编辑 SDK 内的板子原始 DTS，VS Code nRF Devicetree 插件会提示你：

![image-20260714174531039](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefineddff19127e23bbe5d7c889b5d9e7c8210.png)

## 代码中访问 Devicetree

Zephyr SDK 中的驱动程序会自动用一系列 Devicetree 宏函数来展开获取到设备树中的信息。

如果设备树是这样：

```DTS
/ {
	chosen {
		zephyr,console = &uart20;
	};
	
    soc {
        global_peripherals: peripheral@50000000 {
            uart20: uart@c6000 {
                compatible = "nordic,nrf-uarte";
                reg = <0xc6000 0x1000>;
                status = "okay";
            };
        };
    };
};

// 也可以用 &uart20 来代替上面的绝对路径写法
```

要先获取节点的Node ID，后续具体操作需要

```c
#include <zephyr/devicetree.h>

// 获取 Node Identifier, 以下4种方法等价
#define LOG_UART_A DT_PATH(soc, peripheral_50000000, uart_c6000) // 基于绝对路径 /soc/peripheral@50000000/uart@c6000
#define LOG_UART_B DT_NODELABEL(uart20)                          // 基于 Node 标签 "uart20:"
#define LOG_UART_C DT_CHOSEN(zephyr_console)                     // 基于 Chosen属性 "zephyr,console = &uart20;"
#define LOG_UART_D DT_INST(0, nordic_nrf_uarte)                  // 在所有 compatible = "nordic,nrf-uarte" 的节点里，编号为0的节点
```

常见用法

- `DT_PATH`很少见，因为很麻烦，除非无`label`目录层级很浅。
- `DT_NODELABEL` 在工程里很常用，开发者很容易地在 Devicetree 里附加一个label，然后在代码中引用它
- `DT_CHOSEN` 在 Zephyr 官方组件中很常见。Kernel 或 Subsys 等官方组件会从`/chosen`节点下选取自己要用的资源。开发者可以通过修改 Devicetree 来修改 Zephyr Kernel 或 Subsys使用的具体硬件。
- `DT_INST`通常不会单独出现，常见于 Zephyr 设备驱动中。Devicetree 中的节点在编译后都会被赋予一个临时的编号（应用层无需关心），既然有了编号，就可以实现**遍历**。Zephyr 驱动会用`DT_INST_FOREACH_STATUS_OKAY(fn)`这样的宏函数遍历所有 compatible 符合，且已经使能的设备树节点；对这些节点遍历执行某个宏函数（通常是创建设备对象实例的代码模板）。这样，Devicetree 中的配置就和它的驱动代码通过"compatible"关联了起来。

有了 Node ID，你就可以:

- 读取 Devicetree 里这个节点下的属性，如波特率；
- 获取 Zephyr 驱动程序为这个节点创建的设备对象实例指针（`struct device *`）。后续所有外设操作都用这个指针作为句柄。

总而言之，Devicetree 中的信息不仅是给应用层服务的，也是给SDK服务的。

![image-20260715104830604](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb3e845757e0cdc884c5c2f26df01a151.png)

## Zephyr 驱动程序

在`main()`函数运行起来之前，Zephyr设备驱动的初始化程序就已经先运行了。设备的驱动程序根据device tree中的配置，自动把外设进行相应的初始化，配置寄存器。然后driver还会提供一个`struct device`结构体，方便应用层操作这个外设。

程序的application层起来之后，开发者就可以用driver初始化好的device结构体，用标准的Zephyr API进行操作。

有以下5个阶段可以用来初始化外设驱动：

![image-20230312215847338](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20230312215847338.webp)

Zephyr外设驱动的整个流程：

【编译阶段】

1. 开发者在Kconfig中，使能了某个外设驱动，如`CONFIG_SERIAL=y`

2. `zephyr/drivers/`下的CMakeLists.txt，根据`CONFIG_SERIAL=y`，把`zephyr/drivers/serial/`添加到工程中

3. `zephyr/drivers/serial/`下有各个半导体厂商向Zephyr提交的串口驱动代码。此目录下的CMakeLists.txt根据你的当前Kconfig配置，来选择哪个驱动文件编译进来：

   ```cmake
   zephyr_library_sources_ifdef(CONFIG_UART_NRFX_UART uart_nrfx_uart.c)
   if (CONFIG_UART_NRFX_UARTE)
     if (CONFIG_UART_NRFX_UARTE_LEGACY_SHIM)
       zephyr_library_sources(uart_nrfx_uarte.c)
     else()
       zephyr_library_sources(uart_nrfx_uarte2.c)
     endif()
   endif()
   ```

4. 驱动代码中，会通过宏来匹配`zephyr.dts`中的所有串口节点，也就是匹配哪些节点的`compatible`与当前驱动是一致的。然后，再匹配这些节点的`status="okay"`，就说明这个外设被使能了，于是就定义一个`device`结构体实例。

> device结构体的定义：
>
> ```c
> struct device {
>  const char *name;           // 设备的名称
>  const void *config;         // 设备的初始配置
>  const void *api;            // 设备的api函数集合
>  struct device_state *state; // 设备的工作状态
>  void *data;                 // 设备的运行数据
>  /* ... */                   // 其他参数，例如电源管理
> };
> ```



【运行阶段】

1. 系统启动后，在设备驱动程序预设好的阶段（上图5个阶段之一），进行外设的初始化和配置。配置的值就来自于dts overlay中节点的配置。
   如果是外挂芯片的驱动，则会在这个阶段完成外挂芯片的配置（如SPI总线的液晶屏、I2C总线的RTC时钟等）。
   以上只是两个示例，具体的行为，要看根据驱动程序的代码。
2. 程序进入到**应用层**之后，所有需要的外设就已经被初始化好了。在应用层代码中，开发者只需先获得这个device结构体的指针，后续调用Zephyr标准外设API时，把这个指针作为参数传入即可。

```c
// 例如，获取串口1的device结构体指针
static const struct device *uart1_dev = DEVICE_DT_GET(DT_NODELABEL(uart1));

// 使用串口1发送数据
uart_tx(uart1_dev, buf, len, timeout);
```



![image-20260715101703561](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined5f5a839e071e19e87b340e4c460c95a4.png)

## Zephyr 驱动模型的优劣

优点：

- 代码里调用的都是Zephyr标准API，与硬件细节无关。如果后需要更换MCU平台，几乎没有什么移植成本，只需要更换所选的 board 即可。
- 通用性强。无论是普通的串口，还是USB串口，它们的应用层代码均是 Zephyr 标准 API，只需要更换底层选择的驱动即可。
- 开发者无需花精力在标准、通用的基本功能上，如串口、SPI、网络、按钮等。因为这些驱动都是厂商提供的，在性能、健壮性、功耗管理上往往都强于开发者自己用寄存器或外设驱动库开发的代码。
- 即使是硬件根本不存在的外设，也有可能按照 Zephyr 标准 API 实现，然后给系统使用。如，GPIO + TIMER + PPI 模拟串口，nRF54L 系列 RISC-V 核模拟sQSPI等等。

缺点：

- 上手难度稍高，需要花精力去学习 Devicetree 和整个驱动模型

- 功能不完全。Zephyr 只提供最标准的用法，当用到串口、spi、i2c等协议时，就是最标准的协议。一旦有不符合标准的，或者Zephyr标准库未提供的功能，就无法在Zephyr驱动模型的框架下实现了。

  > 例如，Nordic 的芯片有 PPI 的功能，可以让一个外设的 event 触发另一个外设的 task。这个功能 Zephyr 是没有标准 API 的，因此，**应用层**无法通过 Zephyr 接口操作 PPI。
  >
  > 但是，很多Nordic**驱动层**代码里面都是用到了 PPI 的。
  >
  > 如果用户想自己用 PPI 实现一些自定义功能，只能直接调用 nrfx api。在使用 PPI 时， 注意 PPI 是一个“资源型”外设，一定要用 nrfx 提供的 API 动态地申请和释放，而不要直接指定PPI[n]。因为许多 Zephyr 驱动中也在使用 PPI。
  >
  > 
  >
  > 示例 - 在SPI传输过程中每个字节之间增加时隙：[Jayant-Tang/nRF54L-Gap-Timing-SPI: Hardware-paced SPI byte gap on nRF54L using Timer & PPI — half-byte time delay between bytes, zero CPU wait.](https://github.com/Jayant-Tang/nRF54L-Gap-Timing-SPI)

## Nordic NRFX外设驱动库

如果你的需求比较特殊，想要绕过 Zephyr 驱动层，直接在底层驱动甚至寄存器和中断的级别来进行开发，NCS也是支持的。

请参考[《在NCS中使用NRFX外设驱动库 —— 以 I2C 为例》](https://jayant-tang.github.io/2023/11/1349f878e408/)。

## 总结

DTS 怎么写，本质上取决于驱动代码里怎么读取 DTS。DTS 的本质就是保存硬件细节相关的信息，使自己的应用代码与硬件细节解耦。

要更详细地了解Devicetree，请参考[《详解Zephyr设备树（DeviceTree）与驱动模型》](https://jayant-tang.github.io/2023/03/4b274a50e575/)。

# 5. Sysbuild (System build)

前面介绍的CMake, Kconfig, DeviceTree都是其他领域（如Linux内核）已经在广泛使用的配置工具。但是 Sysbuild 是 Zephyr 的新引入的构建机制，它是一个High-Level 的配置工具，解决的是 MCU 多镜像编译的问题。

前面介绍的那些工具，都是为了 1 个镜像编译时用的。当我们要编译一个**多镜像**的固件时，这些不同的镜像之间可能会有一些配置项的差别。

例如：

- 我希望我的串口用于打印日志；但是在 bootloader 镜像中，同一个串口用于固件升级。
- 我选型了一款外部 QSPI Flash，与 Nordic 官方开发板上的 QSPI Flash 不同，于是我修改了我的工程中的overlay文件。但是，我也需要在某个地方修改bootloader 工程的 overlay 文件，从而让 bootloader 也识别我的 Flash。

以上说的是运行在同一个CPU上，不同镜像之间的**差异配置**。除此之外，还有运行在不同CPU上，不同镜像之间的**相同配置**，例如双核MCU上的App Core和Net Core，我希望同时配置为debug模式或release模式，而不是单独去调。

## Sysbuild的开关

编译时可以决定是否使用Sysbuild

```bash
west build --sysbuild

west build --no-sysbuild
```

Sysbuild 在 NCS v2.7.0 引入并开始迁移，v2.8.0 起在 NCS 工程中默认使用；命令行仍可用 --sysbuild/--no-sysbuild 显式控制

## 命名空间（Namespace）

在多镜像编译的场景下，我们用`west build`进行命令行编译时，如果要添加一些配置项，则可能需要指定，这个配置项是属于哪个子工程的，或者是属于整体的（Sysbuild）。

```bash
# 带有Namespace的Kconfig
-D<namespace>_CONFIG_<var>=<value>

# 带有Namespace的CMake选项
-D<namespace>_<var>=<value>
```

例如：

```bash
west build -b reel_board --sysbuild samples/hello_world \
	-- \
		-DSB_CONFIG_BOOTLOADER_MCUBOOT=y \
		-DCONFIG_DEBUG_OPTIMIZATIONS=y \
		-Dmcuboot_CONFIG_DEBUG_OPTIMIZATIONS=y
		
# 给Sysbuild（全局）传递 CONFIG_BOOTLOADER_MCUBOOT=y，表示使用bootloader作为MCUBOOT，命名空间为SB

# 给当前默认 Application 工程传递 CONFIG_DEBUG_OPTIMIZATIONS=y，命名空间为空

# 给mcuboot工程传递 CONFIG_DEBUG_OPTIMIZATIONS=y，命名空间为 mcuboot，也就是子工程的名称
```

## Sysbuild配置文件

除了上述在编译时传递编译选项的方法，也可以保存Sysbuild级别的配置文件

```text
application/
├── ...
├── CMakeLists.txt   # application 的 CMake
├── prj.conf         # application 的 配置项
├── ...
├── Kconfig.sysbuild # Sysbuild 全局级别的 Kconfig 菜单定义。可以不定义，不定义时使用SDK内的默认菜单
├── sysbuild.conf    # Sysbuild 全局配置项
├── ...
├── sysbuild.cmake   # Sysbuild 全局级别的 CMake。可以用来管理有哪些工程镜像参与总镜像的编译
├── ...
└── sysbuild/        # Sysbuild目录下，可以分别给每个子工程单独进行配置
    └── mcuboot           
        ├── prj.conf
        └── boards
            ├── <board_A>.conf
            ├── <board_A>.overlay
            ├── <board_B>.conf
            └── <board_B>.overlay
```

关于sysbuild的例程，可以参考`zephyr/samples/sysbuild/`下的几个例程。

## 给Sysbuild添加子工程

参考`zephyr/samples/sysbuild/hello_world`，这个工程是给双核MCU运行使用的。App核运行一个Hello World，然后同时再添加一个Hello World工程给另一个核使用。最后编译出双镜像固件。

要给当前工程添加子工程，其实就是修改`sysbuild.cmake`。

```cmake
ExternalZephyrProject_Add(
  APPLICATION my_sample                 # 要添加的工程名
  SOURCE_DIR <path-to>/my_sample        # 要添加的工程路径
  BOARD mps2_an521_remote               # 如有必要，单独指定要添加的工程使用的board
  BUILD_ONLY TRUE                       # 如有必要，可以只编译不烧录
)

# 要先编译my_sample,再编译当前默认application工程
sysbuild_add_dependencies(CONFIGURE ${DEFAULT_IMAGE} my_sample)
# 等价于以下CMake标准函数
add_dependencies(${DEFAULT_IMAGE} my_sample)

# 要先烧录my_sample,再烧录当前application工程
sysbuild_add_dependencies(FLASH ${DEFAULT_IMAGE} my_sample)
# 如果my_sample配置为BUILD_ONLY=TRUE，则会报错
```

> 特别地，如果要添加的工程就是MCUBOOT，则只需在`sysbuild.conf`中添加下列配置即可：
>
> ```bash
> SB_CONFIG_BOOTLOADER_MCUBOOT=y
> ```
>
> 因为SDK中已经把MCUBOOT相关的sysbuild写好了，这里直接使能即可。



# 6. 【已弃用】Parent-Child image

在NCS v2.6.x及之前的版本中，多镜像的管理靠的是 parent-child image。目前已经被 sysbuild 代替。

这个工具不是Zephyr的，而是Nordic的。它也能在一个子文件夹里分别管理子镜像的配置。但它和Sysbuild的区别在于：它没有单独的High-Level的全局配置。这导致一些实际上应该属于全局的配置，直接放在了Application层的配置中（例如选择哪个Bootloader），因此偶尔会产生混淆。

如使用老版本的NCS，建议参考老版本NCS关于这方面的文档：https://docs.nordicsemi.com/bundle/ncs-2.7.0/page/nrf/config_and_build/multi_image.html

# 7. 【已弃用】存储器分区文件（Partition Manager）

管理一个MCU的存储器分区是很常见的需求。不仅在多镜像、OTA的场景下要管理，在内部和外部flash上挂载文件系统、用单独的分区存储生产信息等等场景下都要管理。

Partition Manager 不是Zephyr的，而是Nordic的。它用一个全局的 yaml 文件管理 NVM 上的分区。但由于理解起来太复杂，**目前已经被 Zephyr 标准的 Devicetree 分区方式替代。**见：[Zephyr中的分区和存储系统 - Jayant's Blog](https://jayant-tang.github.io/2026/07/cea69d4e489a/)

> NCS v3.3.0 起 Partition Manager 进入 deprecated状态，新设计推荐用 Zephyr Devicetree 分区；预计 2026 年底从 main branch 移除。


<details>
    <summary>[点击展开了解Partition Manager]</summary>

存储器分区文件，尤其是带有外部flash的，可以参考Matter例程，例如`nrf/samples/matter/lock`。你可以看到很多`pm_static_xxx.yml`:

```yaml
mcuboot:
  address: 0x0
  size: 0x7000
  region: flash_primary
mcuboot_pad:
  address: 0x7000
  size: 0x200
app:
  address: 0x7200
  size: 0xefe00
mcuboot_primary:
  orig_span: &id001
  - mcuboot_pad
  - app
  span: *id001
  address: 0x7000
  size: 0xf0000
  region: flash_primary
mcuboot_primary_app:
  orig_span: &id002
  - app
  span: *id002
  address: 0x7200
  size: 0xefe00
factory_data:
  address: 0xf7000
  size: 0x1000
  region: flash_primary
settings_storage:
  address: 0xf8000
  size: 0x8000
  region: flash_primary
mcuboot_secondary:
  address: 0x0
  size: 0xf0000
  device: MX25R64
  region: external_flash
external_flash:
  address: 0xf0000
  size: 0x710000
  device: MX25R64
  region: external_flash
```

详细的语法无需在意，不同工程基本都是大同小异的。

> 【注意】配置Partition Manager时，一定要注意对齐Flash的Page！！！

## 静态分区文件说明

### mcuboot相关

mcuboot相关照抄即可，只需修改地址和大小。

- `mcuboot`，也就是mcuboot的固件大小。Matter的MCUBOOT配置是SDK中专门优化过的，因此只需要0x7000字节。一般来说自己添加一个需要0xc000的空间
- `mcuboot_pad`：DFU期间，存储一些固件升级情况的标志位和校验信息
- `mcuboot_primary`：也就是app所在的slot，同时也有mcuboot_pad。
- `mcuboot_secondary`：也就是升级时新固件存放的slot。通常app负责接收新固件，然后跳转到mcuboot，mcuboot进行分区固件交换后，升级完成。secondary slot也可以放到外部flash

### app相关

app相关照抄即可，只需修改地址和大小。

- `app`与`mcuboot_primary_app`：都是app分区

### settings_storage

settings_storage是Zephyr系统中一个存储配置项的分区，是一个简易的文件系统。可以用“字符串”（通常是文件路径，例如`id/serial`）作为句柄来存取数据（提供首地址、长度）。

Zephyr中许多的Librarys都依赖Settings来存储持久化数据，例如蓝牙的绑定密钥。因此这个分区非常常见。考虑到用到Settings的组件非常多，最好不要把Settings放到外部flash，不然做外部flash低功耗时，如果外部flash休眠了，而某个组件要用到Settings，就会报错，非常麻烦。

由于Settings是文件系统，因此它不是把数据单一的存在一个地址，而是像硬盘一样一直向后写，直到分区flash写满了，才把前面的page全部擦掉做垃圾回收。因此最好给settings_storage准备至少2个page的flash空间（上面的例子是0x8000，为两个4kB的page）。如果在特定极端峰值情况下，flash读写非常快且数量多，则需要3个page或以上。例如HomeKit认证时的循环蓝牙绑定16次测试，需要3个page。

### 其他分区

其他分区没有什么特别的，就是用一个label定义一个分区名称。

- `factory_data`：在Matter工程中，用于存储证书等数据的分区。
- `external_flash`：外部flash空余的位置，随意进行了一个命名。

其实Partition Manager只是一套脚本，最终还是要落实到C代码。在代码中，可以通过label来访问这些分区。例如Matter的SDK中就会通过`factory_data`来访问认证证书等数据。

你也可以充分利用这个未使用的分区。用`nrf/include/flash_map_pm.h`中定义的宏函数，来把这些label转化成Zephyr可以使用的Flash Device句柄和分区句柄。例如把这个`external_flash`分区拿来建立NVS文件系统。

```c
#include <zephyr/storage/flash_map.h>

#define NVS_PARTITION		external_storage
#define NVS_PARTITION_DEVICE	FIXED_PARTITION_DEVICE(NVS_PARTITION)
#define NVS_PARTITION_OFFSET	FIXED_PARTITION_OFFSET(NVS_PARTITION)

#include <zephyr/fs/nvs.h>

static struct nvs_fs fs;

int app_nvs_entry(void)
{
    int rc = 0;
	char buf[16];
	uint8_t key[8], longarray[128];
	uint32_t reboot_counter = 0U;
	struct flash_pages_info info;

	/* define the nvs file system by settings with:
	 *	sector_size equal to the pagesize,
	 *	3 sectors
	 *	starting at NVS_PARTITION_OFFSET
	 */
	fs.flash_device = NVS_PARTITION_DEVICE;
	if (!device_is_ready(fs.flash_device)) {
		LOG_ERR("Flash device %s is not ready", fs.flash_device->name);
		return 0;
	}
	fs.offset = NVS_PARTITION_OFFSET;
	rc = flash_get_page_info_by_offs(fs.flash_device, fs.offset, &info);
	if (rc) {
		LOG_ERR("Unable to get page info");
		return 0;
	}

	fs.sector_size = info.size;
	fs.sector_count = PAGE_COUNT;

    LOG_INF("NVS sector size: %d, sector count: %d", fs.sector_size, fs.sector_count);

	rc = nvs_mount(&fs);
	if (rc) {
		LOG_ERR("Flash Init failed");
		return 0;
	}
    ...
}
```

> 值得一提的是，根据`nrf/include/flash_map_pm.h`中的定义，当使用以下三种文件系统时，最好就使用那个名字作为label
>
> - `settings_storage`
> - `littlefs_storage`
> - `nvs_storage`

## 外部Flash分区

当某个分区位于外部Flash时，这个分区需要配置：

````yaml
region: external_flash
device: MX25R64
````

其中device是需要在设备树中配置的，要让partition manager知道外部flash是哪个设备，比如这里是`mx25r64`这个节点：

```
/ {
	chosen {
		nordic,pm-ext-flash = &mx25r64;
	};
};
```

如果Bootloader也需要访问外部flash，不要忘记在mcuboot中也添加以上配置。

> 除此之外，还要注意。如果不得已要把文件系统放在外部flash，一定要使能对应的配置，例如：
>
> -  [`CONFIG_PM_PARTITION_REGION_LITTLEFS_EXTERNAL`](https://docs.nordicsemi.com/bundle/ncs-2.9.0/page/kconfig/index.html#CONFIG_PM_PARTITION_REGION_LITTLEFS_EXTERNAL)
> - [`CONFIG_PM_PARTITION_REGION_SETTINGS_STORAGE_EXTERNAL`](https://docs.nordicsemi.com/bundle/ncs-2.9.0/page/kconfig/index.html#CONFIG_PM_PARTITION_REGION_SETTINGS_STORAGE_EXTERNAL)
> - [`CONFIG_PM_PARTITION_REGION_NVS_STORAGE_EXTERNAL`](https://docs.nordicsemi.com/bundle/ncs-2.9.0/page/kconfig/index.html#CONFIG_PM_PARTITION_REGION_NVS_STORAGE_EXTERNAL)
>
> 并且这些配置是，只有当你用Nordic的QSPI Flash驱动时（`compatible = "nordic,qspi-nor"`）才有作用的。

更多使用外部flash的细节，见[文档](https://docs.nordicsemi.com/bundle/ncs-2.9.0/page/nrf/app_dev/bootloaders_dfu/mcuboot_nsib/bootloader_partitioning.html#ug-bootloader-external-flash).

## 动态分区

实际上Partition Manager还支持根据不同子工程编译的大小动态分区。但是动态分区对于实际的项目来说没有任何意义，实际项目一定都需要静态分区，才能确保固件升级（DFU）的正确性。

如需了解更多，参考[Partition Manager文档](https://docs.nordicsemi.com/bundle/ncs-2.9.0/page/nrf/scripts/partition_manager/partition_manager.html)。

## 检查Partition Manager是否开启

要检查自己是否开启了Partition Manager，检查编译后的`.config`中有无：

```
CONFIG_PARTITION_MANAGER_ENABLED=y
```

> 不要主动去设置它，一般来说开启多镜像编译后，它就会自动使能。

## 用CMake变量指定分区文件

通常来说，编译时会自动选择项目根目录下的`pm_static_<board_name>.yaml`文件。

但是如果你的项目比较复杂，希望用CMake变量来指定Partition Manager文件，类似于指定`CONF_FILE`配置文件那种方式，则需要在Sysbuild级别的配置`sysbuild.cmake`中进行设置，变量为`PM_STATIC_YML_FILE`。

`sysbuild.cmake`

```cmake
set(PM_STATIC_YML_FILE ${CMAKE_CURRENT_LIST_DIR}/foo/bar/pm_static.yml CACHE INTERNAL "")
```
</details>

# 8. Zephyr中的“Boards”

在Zephyr中，Boards是非常重要的一个概念。直观地理解，它指的就是你开发的项目的PCB板子。Zephyr中有很多可选择的Boards，都是各个厂商或提交给Zephyr的。在编译时必须选择一个Boards。

但看完前面的介绍，我们就可以更深入地理解Boards：它其实就是一堆默认的 Kconfig，DeviceTree 配置文件的集合。

## Boards默认配置文件

当我们选择`nrf52840dk/nrf52840`时，就会导入SDK中`${NCS}/zephyr/boards/nordic/nrf52840dk/`目录下的各种配置文件。这其中，`nrf52840dk`是板子的名称，`nrf52840`是SoC的名称。

其中，Kconfig配置文件是`nrf52840dk_nrf52840_defconfig`；DeviceTree文件是`nrf52840dk_nrf52840.dts`。其余`.dts`或`.dtsi`文件是被它include的。例如，引脚分配文件`nrf52840dk_nrf52840-pinctrl.dtsi`。

当编译时，选择`nrf52840dk/nrf52811`时，它是用`nrf52840`这颗芯片来模拟`nrf52811`的资源，让你也可以用nRF52840DK这个开发板来进行nRF52811的开发。

## Board Name

Boards 是为了编译固件而服务的。因此 board name 中一定包含编译目标所需要的信息。

示例：

- `nrf52840dk/nrf52840`：为nRF52840DK开发板上的nRF52840这颗SoC芯片编译固件
- `nrf5340dk/nrf5340/cpuapp`：为nRF5340DK开发板上的nRF5340这颗**双核**芯片的**App核**编译固件
- `nrf54l15/cpuapp/ns`：为nRF54L15DK开发板上的nRF54L15这颗**双核**芯片的**App核**编译固件，并且选择非安全（non-secure）地址空间进行编译。

![Board terminology diagram](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined98e729d2426ea024e99f2c8a8e2e5970.svg)

完整示例：

`nrf54l15dk@1.0.0/nrf54l15/cpuapp/ns`：

| nrf54l15dk | @1.0.0                                           | /nrf54l15                   | /cpuapp                             | /ns                             |
| ---------- | ------------------------------------------------ | --------------------------- | ----------------------------------- | ------------------------------- |
| 板子名称   | 板子版本（常见于工程样片版本，正式版无需此字段） | **Board qualifier** for SoC | **Board qualifier** for CPU cluster | **Board qualifier** for variant |

### 老版本板子名称

<details>
    <summary>[点击展开]</summary>

前面介绍的都是Zephyr的Hardware Model v2。在板子、SoC、CPU之间有层级关系。

在NCS v2.6.x之前，用的是没有层级关系的板子名称。例如`nrf52840dk_nrf52840`和`nrf52840dk_nrf52811`被认为是两块不同的板子。

当然你也可以简单理解为，Hardware Model v2就是简单把下划线`_`换成了斜杠`/`。

</details>

## CMake中使用Boards变量

可能你需要在CMake中根据Board来配置不同的文件。Zephyr的boards CMake扩展已经提供了以下变量供使用：

```cmake
# The following variables will be defined when this CMake module completes:
#
# - BOARD:                       Board, without revision field.
# - BOARD_REVISION:              Board revision
# - BOARD_QUALIFIERS:            Board qualifiers
# - NORMALIZED_BOARD_QUALIFIERS: Board qualifiers in lower-case format where slashes have been
#                                replaced with underscores
# - NORMALIZED_BOARD_TARGET:     Board target in lower-case format where slashes have been
#                                replaced with underscores
# - BOARD_DIR:                   Board directory with the implementation for selected board
# - ARCH_DIR:                    Arch dir for extracted from selected board
# - BOARD_ROOT:                  BOARD_ROOT with ZEPHYR_BASE appended
# - BOARD_EXTENSION_DIRS:        List of board extension directories (If
#                                BOARD_EXTENSIONS is not explicitly disabled)
```

例如，选择板子`nrf52840dk/nrf52840`，在CMakeLists.txt中加入以下消息打印：

```cmake
message(STATUS "BOARD:${BOARD}")
message(STATUS "BOARD_REVISION:${BOARD_REVISION}")
message(STATUS "BOARD_QUALIFIERS:${BOARD_QUALIFIERS}")
message(STATUS "NORMALIZED_BOARD_QUALIFIERS:${NORMALIZED_BOARD_QUALIFIERS}")
message(STATUS "NORMALIZED_BOARD_TARGET:${NORMALIZED_BOARD_TARGET}")
message(STATUS "BOARD_DIR:${BOARD_DIR}")
message(STATUS "ARCH_DIR:${ARCH_DIR}")
```

编译时cmake打印：

```bash
-- BOARD:                        nrf52840dk

-- BOARD_REVISION:

-- BOARD_QUALIFIERS:             /nrf52840

-- NORMALIZED_BOARD_QUALIFIERS:  _nrf52840

-- NORMALIZED_BOARD_TARGET:      nrf52840dk_nrf52840

-- BOARD_DIR:      /home/jayant/project/ncs/v2.8.0/zephyr/boards/nordic/nrf52840dk

-- ARCH_DIR:
```

其中比较有用的是`${NORMALIZED_BOARD_TARGET}`，你可以在`CMakeLists.txt`或者`sysbuild.cmake`中用这个变量来匹配设置一些配置文件，例如：

```cmake
# 在sysbuild.cmake中使用，把分区设置同时应用到Application和Bootloader

## Partition manager
if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/partitions/pm_static_${NORMALIZED_BOARD_TARGET}.yml")

    set(PM_STATIC_YML_FILE "${CMAKE_CURRENT_LIST_DIR}/partitions/pm_static_${NORMALIZED_BOARD_TARGET}.yml" CACHE INTERNAL "")

    message(STATUS "Using Partition Manager file: ${CMAKE_CURRENT_LIST_DIR}/partitions/pm_static_${NORMALIZED_BOARD_TARGET}.yml")
else()
    message(FATAL_ERROR "Can't find Partition Manager scripts (${CMAKE_CURRENT_LIST_DIR}/partitions/pm_static_${NORMALIZED_BOARD_TARGET}.yml)")
endif()

```

以上配置会在`partitions/`目录下自动查找板子对应的`pm_static_xxx.yml`配置文件：



## 自定义板子

如果你的项目比较简单，可以不用自定义板子。直接选择Nordic开发板作为基础的Board。然后用device tree overlay文件和Kconfig配置文件，来增、删、改配置。

但是定义自己的板子会有许多好处，比如：

- 让一个工程同时支持自己的Board和开发板。debug时，可以对比开发板和自己的板子的表现。在排查硬件问题，进行功耗优化时非常有用。
- 用同一块板子开发不同工程时，移植非常方便。
- 你选择的芯片封装和开发板上的封装并不相同，引脚数量有区别，需要自定义board。

### 自定义板子的步骤

也可以参考[官方文档](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/app_dev/board_support/defining_custom_board.html)

#### 创建Board

可以在VS Code中图形化操作，定义板子：

![image-20250107145312936](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250107145312936.webp)

输入板子名称，是给人阅读的字符串，可以带空格：

![image-20250107145418793](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250107145418793.webp)

输入板子名称，是编译时使用的名称，不能带空格：

![image-20250107145508177](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250107145508177.webp)

选择使用的NCS版本：

![image-20250107145532264](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250107145532264.webp)

选择SoC芯片：

![image-20250107145557369](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250107145557369.webp)

选择自己的boards相关文件存放的位置，通常就是当前project根目录即可。

![image-20250107145720987](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250107145720987.webp)

输入公司名称，作为vendor字段：

![image-20250108145721828](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250108145721828.webp)

创建完毕后，就存放在当前工程的boards目录下：

![image-20250108145954333](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250108145954333.webp)

```
# 目录结构，你可以添加自己的doc
application_dir/
├── boards/
│   └── vendor/
│       └── my_custom_board/
│           ├── doc/
│           │   └── img
│           └── support/
└── src/

```



#### 添加默认Kconfig

默认的config就是你的`<board_name>_defconfig`：

![image-20250108154144637](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250108154144637.webp)

可以按需求拷贝开发板的默认配置，参考`${NCS-2.8.0}/zephyr/boards/arm/nrf52840dk_nrf52840/nrf52840dk_nrf52840_defconfig`

![image-20250108154101849](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250108154101849.webp)

以上是添加默认的配置值。如果你想增加这个板子的菜单可选项，可以在`Kconfig.<board_name>`中添加你的菜单项。

> 值得一提的是，如果你的板子上没有32.768kHz晶振，则需要使用内部RC震荡器。可以把内部晶振相关配置写到这个defconfig中
>
> ```
> CONFIG_CLOCK_CONTROL_NRF_K32SRC_RC=y
> CONFIG_CLOCK_CONTROL_NRF_K32SRC_XTAL=n
> CONFIG_CLOCK_CONTROL_NRF_K32SRC_RC_CALIBRATION=y
> ```
>
> 但是，在成本允许的情况下，还是非常推荐使用外部32k晶振的。外部晶体相比于内部RC震荡器具有更高的温度稳定性。此外，内部RC震荡器需要经常用高频时钟进行校准，因此功耗也会更高。

#### 添加默认设备树配置

在`<board_name>.dts`中增加你的默认设备树配置。你也可以按需求拷贝对应芯片的开发板文件。例如：`/${NCS-v2.8.0}/zephyr/boards/nordic/nrf52840dk/nrf52840dk_nrf52840.dts`

这里着重介绍一些要用到的：

##### 特殊引脚配置（in UICR）

当你的GPIO不够用时，可能需要把一些特殊引脚当作GPIO使用。这些需要写芯片的UICR寄存器（类似于Flash的一个区域，存储用户配置）。

```
&uicr {
    // bool类型属性，有则为true，没有则为false
    
    // Reset pin 当作 reset 而不是GPIO使用
	gpio-as-nreset;
	
	// 删除属性，就是把bool类型设为false
	
	// NFC引脚不当作GPIO使用
	/delete-property/ nfct-pins-as-gpios；
};
```

> 在较老的NCS版本，v2.4.x及之前，不是在DeviceTree中设置，而是在Kconfig中设置：
>
> ```
> CONFIG_GPIO_AS_PINRESET=y
> 
> CONFIG_NFCT_PINS_AS_GPIOS=n
> ```

##### 电源regulator配置

板子外部通过VDD引脚对芯片进行供电，Nordic芯片内部还有一级电源Regulator给内核供电。这个Regulator可以配置成DC/DC或者LDO。如果是DC/DC的话，板子外部需要添加对应的电感电容。

![image-20250108163305341](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250108163305341.webp)

<center>
    nRF52832内部供电-DCDC模式
</center>

![image-20250108163523995](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250108163523995.webp)

<center>
    nRF52840内部两级供电-双DC/DC模式
</center>

nRF52840有高电压模式，可以用VDDH引脚输入2.5～5.5V电压。

你也可以不使用VDDH。直接把VDDH和VDD短路，这种情况下会跳过Regulator0，供电范围是1.7~3.6V：

![image-20250108163945669](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250108163945669.webp)

<center>
    nRF52840一级供电 - LDO模式
</center>

大多数应用，采用一级供电即可。此外，像是nRF52840-QFAA这种封装（QFN48）内部已经把VDDH和VDD进行了短路操作，这时regulator0已经被屏蔽。直接配置reg1即可

```
// 使用DC/DC
&reg1 {
	regulator-initial-mode = <NRF5X_REG_MODE_DCDC>;
};
```

```
// 使用LDO
&reg1 {
	regulator-initial-mode = <NRF5X_REG_MODE_LDO>;
};
```

如果你用的是带有VDDH供电的封装，则用以下设备树开启REG0的DC/DC

```
// reg0 只在nrf52840-qiaa.dtsi中有定义
&reg0 {
	status = "okay";
};
```

> 在较老的NCS版本中，不是在设备树中配置，而是用Kconfig配置DC/DC
>
> ```
> CONFIG_SOC_DCDC_NRF52X=y
> CONFIG_SOC_DCDC_NRF52X_HV=y
> ```

##### gpio reserve

在开发板的设备树中，我们可能会看到gpio port的节点下有一些配置。我们需要知道它的意思。

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

这里`gpio-reserved-ranges`的意思是：从软件层面上限制gpio0的某些引脚不能当作普通GPIO使用，因为它们在开发板上已经接了一些元器件。这可以防止出一些引脚分配问题。

`<0 2>`的意思是P0.00及其之后一共2个引脚，也就是P0.00和P0.01，因为它们是32.768kHz低频晶振所使用的引脚；同理，`<17 7>`的意思是P0.17及其之后一共7个引脚不能当普通GPIO使用，因为它们是板子上外部QSPI flash采用的引脚，还有P0.18是 reset引脚。

这个只是限制引脚不能当作普通GPIO使用，运行时会报错。但是并不限制这些引脚用pinctrl来分配给外设（毕竟QSPI引脚就是这么分配的）。

我们在拷贝开发板的dts到我们自定义的board时，注意不要完全拷贝这部分，要根据需求来。

##### Zephyr软件依赖的设备树节点

Zephyr中有许多现成的软件模块，它们与硬件有关。比如命令行终端shell，又比如LED和button的驱动。当你使能这些软件模块时，它们会去device tree中寻找自己应该操作哪些硬件。

比如，许多Zephyr Kernel功能用的是`/chosen`节点下的定义：

```
/{
	chosen {
		zephyr,console = &uart0;
		zephyr,shell-uart = &uart0;
		zephyr,uart-mcumgr = &uart0;
		zephyr,bt-mon-uart = &uart0;
		zephyr,bt-c2h-uart = &uart0;
		zephyr,ieee802154 = &ieee802154;
	};
};

// 如果用到OpenThread, Zigbee协议，则需要开启802.15.4
&ieee802154 {
	status = "okay";
};
```

而其他一些library和例程用的是`/aliases`节点下的定义：

```
/{
	aliases {
		led0 = &led0;
		led1 = &led1;
		led2 = &led2;
		led3 = &led3;
		pwm-led0 = &pwm_led0;
		sw0 = &button0;
		sw1 = &button1;
		sw2 = &button2;
		sw3 = &button3;
		bootloader-led0 = &led0;
		mcuboot-button0 = &button0;
		mcuboot-led0 = &led0;
		watchdog0 = &wdt0;
	};
};
```

> 很多例程会用到LED和Button。当你在自己的板子上运行例程，而你的板子上又没有定义led或button时，记得删除例程中LED和Button相关代码。
>
> 例程led和button相关的CONFIG是：
>
> ```
> # Remove support for LEDs and buttons on Nordic development kits
> CONFIG_DK_LIBRARY=n
> ```

##### 外部Flash

nRF52840DK开发板上默认的QSPI flash为：

```
&qspi {
	status = "okay";
	pinctrl-0 = <&qspi_default>;
	pinctrl-1 = <&qspi_sleep>;
	pinctrl-names = "default", "sleep";
	mx25r64: mx25r6435f@0 {
		compatible = "nordic,qspi-nor";
		reg = <0>;
		/* MX25R64 supports only pp and pp4io */
		writeoc = "pp4io";
		/* MX25R64 supports all readoc options */
		readoc = "read4io";
		sck-frequency = <8000000>;
		jedec-id = [c2 28 17];
		sfdp-bfp = [
			e5 20 f1 ff  ff ff ff 03  44 eb 08 6b  08 3b 04 bb
			ee ff ff ff  ff ff 00 ff  ff ff 00 ff  0c 20 0f 52
			10 d8 00 ff  23 72 f5 00  82 ed 04 cc  44 83 68 44
			30 b0 30 b0  f7 c4 d5 5c  00 be 29 ff  f0 d0 ff ff
		];
		size = <67108864>;
		has-dpd;
		t-enter-dpd = <10000>;
		t-exit-dpd = <35000>;
	};
};
```

在nRF7002DK中，也有SPI Flash

```
&spi4 {
	compatible = "nordic,nrf-spim";
	status = "okay";
	pinctrl-0 = <&spi4_default>;
	pinctrl-1 = <&spi4_sleep>;
	pinctrl-names = "default", "sleep";
	cs-gpios = <&gpio0 11 GPIO_ACTIVE_LOW>;
	mx25r64: mx25r6435f@0 {
		compatible = "jedec,spi-nor";
		reg = <0>;
		spi-max-frequency = <33000000>;
		jedec-id = [c2 28 17];
		sfdp-bfp = [
			e5 20 f1 ff ff ff ff 03 44 eb 08 6b 08 3b 04 bb
			ee ff ff ff ff ff 00 ff ff ff 00 ff 0c 20 0f 52
			10 d8 00 ff 23 72 f5 00 82 ed 04 cc 44 83 68 44
			30 b0 30 b0 f7 c4 d5 5c 00 be 29 ff f0 d0 ff ff
		];
		size = <67108864>;
		has-dpd;
		t-enter-dpd = <10000>;
		t-exit-dpd = <5000>;
	};
};
```

QSPI Flash选用的驱动为`compatible = "nordic,qspi-nor"`. SPI Flash选用的驱动为`compatible = "jedec,spi-nor"`。

**如果你选的板子上的外挂flash和开发板自带的不同**，则可以参考`${NCS}/zephyr/samples/drivers/jesd216`例程。不论你用的是QSPI还是SPI Flash，都把它先挂到SPI上，然后根据此例程的说明运行。只需要填写好jedec-id（flash的手册中会写明），例程会自动读取其余Flash信息（例如sfdp-bfp），并把对应的设备树配置打印到日志中，复制出来即可。但是Flash一定是需要支持JEDEC的。

> JEDEC (Joint Electron Device Engineering Council) 是一个制定半导体行业标准的组织。对于外挂Flash存储器来说，JEDEC标准定义了Flash存储器的接口、性能和功能特性。JEDEC标准确保了不同厂商生产的Flash存储器具有互操作性和兼容性。

##### Partition Manager

用MCUBoot进行升级时，如果需要把Second slot放到外部Flash，则需要增加以下配置，让Partition Manager知道外部Flash也要参与存储器分区：

```
chosen {
	nordic,pm-ext-flash = &mx25r64; // 赋值为你的外部flash的label
};
```

#### 用自定义板子编译

VS Code Build界面中出现自定义Board可以选择：

![image-20250108181200141](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250108181200141.webp)

也可以在命令行编译时以当前板子为参数
```bash
west build -d build -b my_board/nrf52840 --sysbuild
```

# 9. 构建流程与输出文件

## 构建流程

### Configure 阶段

1. 把所选板子的默认设备树、和工程内的 overlay 合并为最终设备树 `zephyr.dts`；设备树的所有信息都转换成宏，保存在`devicetree_generated.h`中
2. 所有 Zephyr SDK 和 工程内的 Kconfig 菜单默认值，以及工程内的 `prj.conf`,`boards/<board_name>.conf`等配置全部合并成`.config`，是最终配置项清单，供 CMake 使用。同时，也会生成一份头文件版本`autoconf.h`，使得这些配置项可以作为宏被参考。
3. CMake 会生成 Makefile 或 Ninja 脚本供后续编译使用

> Configure 阶段有大量文本的合并工作，且有严格的校验。大部分工作都是单线程运行，对于较大的项目，在 Windows 上会比较慢（Windows 文件系统问题）。可以考虑使用 WSL 甚至 Linux 服务器。
>
> 在 `west build` 编译时，如果你只改了代码，没有改配置，则可以不加`-p`(`--pristine`)参数（纯净构建），就会跳过 Configure阶段，从而加速编译。但如果你修改了 CONFIG 或设备树，则下次编译时必定会触发 Configure 。

![Zephyr's build configuration phase](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined0a216fd37b8ebee233688efa53dddeff.svg)

### Build 阶段

Build 阶段就是把你的源码全部编译再链接的过程，比较复杂，具体细节可以参考：[build-phase— Zephyr Project documentation (nRF Connect SDK)](https://nrfconnectdocs.nordicsemi.com/ncs/latest/zephyr/build/cmake/index.html#build-phase)。

这个过程要之所以复杂，是因为它要经历多轮链接。因为 Zephyr 内置了内存保护、设备树、系统调用、中断表、用户模式等大量机制，这些机制的实现数据（分区布局、IRQ 表、内核对象哈希等）**只有在部分链接完成后才能确定**，因此必须多轮编译+链接。

Build 阶段是支持多线程的，ninja 会自动使用所有的CPU线程，因此速度会很快。

## 输出文件

以下均按照开启sysbuild的情况下来看路径：

1. 当前 application 工程固件：`build/<application_name>/zephyr/zephyr.hex`
2. 当前 mcuboot 固件（如果有）：`build/mcuboot/zephyr/zephyr.hex`
3. 当前多工程编译合并固件：`build/merged.hex`，如果有多个核，每个核会有自己的`merged_<core>.hex`
4. DFU升级文件：`build/dfu_application.zip`，通过蓝牙等方式升级时使用的升级包

更多输出文件请参考[官方文档](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/app_dev/config_and_build/output_build_files.html).

## VS Code界面

也可以在nRF Connect for VS Code插件界面中查看自己的所有参与编译的**源码**、**配置文件**、**输出文件**：

![image-20250107033534650](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/image-20250107033534650.webp)
