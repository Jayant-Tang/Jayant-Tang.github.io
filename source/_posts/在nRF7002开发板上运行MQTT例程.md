---
title: 在nRF7002开发板上运行MQTT例程
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2023-08-14 14:52:34
cover: null
tags:
- Nordic
- nRF70
- WiFi
- MQTT
categories: Nordic
typora-root-url: ./..
cnblogs:
  postId: '17744193'
  url: https://www.cnblogs.com/jayant97/articles/17744193.html
  lastPublishedAt: '2026-07-06T18:29:40+08:00'
  sourceHash: sha256:c1c0d3ca36f5e29c5ddc2dd5fb44ed101c6ce660c40dc0bb60d340e43f85cde3
  status: imported
  postType: Article
---

# 1. 简介

本文面向零基础读者，将一步一步介绍如何通过nRF7002DK开发板来运行MQTT例程，并分析此例程的框架、代码，以及用到的库。

本文包含以下内容：

- MQTT协议简介
- 手把手教你运行MQTT over WiFi例程
- MQTT例程解析
  - 线程间通信框架：ZBus
  - Zephyr状态机框架：SMF (State Machine Framework)
  - NCS中的Wi-Fi连接方法
  - NCS中的MQTT连接方法
  - MQTT加密连接配置（TLS配置）


## 1.1. nRF7002DK

![nRF7002-DK-1.0.0_perspective](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefineda15e2d9a4fcd70d3dcd4627cfc794a36.webp)

nRF7002DK是Nordic的WiFi6开发板，上面有nRF7002和nRF5340两颗芯片。其中nRF7002是Wi-Fi6双频IC，nRF5340是双核蓝牙主控MCU，二者通过QSPI连接。此开发板提供了5GHz和2.4GHz双频WiFi和蓝牙共存的功能。



![image-20230908164659947](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined11bb0992a610791266f7debcca413bab.png)

此外如果你在今年的Nordic Tech Tour上获得了免费的Clever Connect Kit（CCK），也可以使用。它和7002DK的主要电路都相同（7002, 5340，Jlink和外挂Flash），只是缺少一些外围保护电路和IO口切换用的电子开关。你可以在[这里](https://devzone.nordicsemi.com/cfs-file/__key/communityserver-discussions-components-files/4/INTERNAL-CCK-Quick-Guide-v1.pdf)下载到它的说明文档。

![image-20230823115736114](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined626c570407174bcd9d807422ffcea289.png)

## 1.2. MQTT协议简介

### 什么是MQTT协议？

MQTT是物联网领域常用的通讯协议，它轻量、高效，适合需要联网的嵌入式应用。要快速了解MQTT协议，可以从以下几个角度看。

### 设备之间如何建立连接？

许多设备通过TCP连接到一个服务器上，这个服务器是MQTT Broker，它代理了设备之间的通信。

![image-20230823115755610](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined3d229e6dfb306aa976661065bef0b03f.png)

这种方式优势很多。由于**设备之间**不需要建立**直接**连接，因此当一个设备要与另一个设备通信时，既不需要知道对方的地址，也不需要等待对方的唤醒，甚至不需要知道对方的存在。设备只需要把消息交给服务器，并且从服务器取回自己所需的数据即可，然后就能继续休眠。

### MQTT消息如何传输？

消息被发布到主题上，然后就能被订阅此主题的设备接收到。

![image-20230908165648117](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined839a627ed20f5e802b3bd9233229ca0d.png)



MQTT是基于发布/订阅模型的消息传输协议。任何一个设备都可以向某个主题（Topic）发布（Publish）消息，也可以订阅（Subscribe）某个主题从而接收消息。当某个客户端向一个主题发布数据时，所有订阅了这个主题的客户端都可以收到这个消息。

> 消息：可以是任何数据。如JSON字符串或纯二进制数据；
>
> 客户端：既可以是IoT设备，也可以是PC、手机或服务器；
>
> 主题：一串符合格式要求的字符串。其格式不是本文的重点，此处不详细叙述。

### MQTT协议安全吗？

从最简单的角度考虑，安全分为两个方面，一个是设备身份的认证，一个是传输本身的加密。

每一个MQTT客户端都有一个Client ID，用于标识设备的身份。在一些仅供测试学习的MQTT broker上，只需要自己随便填写一个个Client ID就可以登录了。而商用的MQTT broker可能还需要密码、密钥、证书等凭据才可以允许设备登录。

此外，MQTT是基于TCP/IP的协议，这意味着MQTT也可以通过TLS加密通讯。在这种情况下：

- 如果客户端需要验证服务端的身份，则客户端内需要安装CA证书，用于验证TLS握手时服务器出示的证书是否合法；
- 如果服务端要验证客户端的身份，那么除了前面讲的通过**密码**进行登录的方式外，还可以通过**设备证书**的方式进行验证。这种情况下，客户端需要持有**设备证书**（包含公钥）及其**私钥**。并且设备的证书和Client  ID要提前被注册到云端。

# 2. 环境准备

1. nRF7002DK或CCK
2. 一台安装了nRF Connect SDK v2.4.0的开发环境的PC (Windows/Linux/MacOS)
3. PC上安装一个MQTT客户端，例如：[MQTTX](https://mqttx.app/zh)
4. 联网的WiFi环境（目前仅支持PSK，也就是输入密码的类型；不支持企业级Wi-Fi）

# 3. 运行例程

## 3.1. 通过例程模板创建新工程

![image-20231002150634368](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedca7333769fb1f3165c536c93eaf4f6b5.png)

![image-20231002150727465](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined91f7271efbb141bb016db2490f1695f4.png)

1. 打开一个VS Code新窗口，进入nRF Connect插件界面，选择Create a new application，创建一个新工程
2. 选择copy a sample，复制一个例程
3. 在搜索框输入mqtt，选择`nrf/samples/net/mqtt`
4. 输入工程存放的路径，回车
5. 输入新工程的名称，回车创建

> 通过这种方式创建的新工程会自动创建单独的git仓库，方便我们后续追踪文件的变动。

## 3.2. 修改工程配置文件

在`boards/nrf7002dk_nrf5340_cpuapp.conf`中，添加WiFi SSID和密码的配置，例如：

```bash
# WIFI SSID与密码
CONFIG_WIFI_CREDENTIALS_STATIC_SSID="Nordicsh-5G"
CONFIG_WIFI_CREDENTIALS_STATIC_PASSWORD="xxxxxxxx"

# 加密方式，根据AP的情况四选一
#CONFIG_WIFI_CREDENTIALS_STATIC_TYPE_OPEN=y 
CONFIG_WIFI_CREDENTIALS_STATIC_TYPE_PSK=y
#CONFIG_WIFI_CREDENTIALS_STATIC_TYPE_PSK_SHA256=y
#CONFIG_WIFI_CREDENTIALS_STATIC_TYPE_SAE=y
```

> 提示：
>
> 1. 本例程的`src/modules/network_wifi.c`中要求必须静态配置WiFi SSID和密码
>    ```c
>    BUILD_ASSERT(IS_ENABLED(CONFIG_WIFI_CREDENTIALS_STATIC), "Static Wi-Fi config must be used");
>    ```
>
>    因此，若不在编译前就设置好WiFi SSID与密码，则Assert无法通过。
>    不过在实际的产品开发中，肯定是希望在程序运行后再动态配置，具体方法请参考后续章节。
>
> 2. 由于`mqtt`例程除了可以用7002wifi开发板运行外，也可用9160蜂窝网开发板运行，因此Wi-Fi的相关配置最好放在`boards`目录下与WiFi板子相关的配置文件中，而不是放在`prj.conf`这个通用的配置文件中。这是一种更合理的做法。

## 3.3. 创建编译目标

![image-20230823115834345](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined42e22e57dd8c7f5f71959ab462ea66f6.png)

1. 选择nRF Connect 插件
2. 在mqtt工程下新建一个编译目标
3. 选择板子`nrf7002dk_nrf5340_cpuapp` （含义：7002DK开发板——5340MCU——应用核）
4. 追加的配置文件选择`overlay-tls-nrf7002.conf`。（也可以把这个追加配置文件的内容复制到prj.conf中）
5. 编译

> 提示：
>
> 1. 通过按`` CTRL + `  `` 可以呼出命令行界面，查看编译进度
>
> 2. 编译时，命令行中会显示运行的命令：
>    ```bash
>    /bin/sh -c west build --build-dir /home/jayant/project/ncs-project/wifi/mqtt/build /home/jayant/project/ncs-project/wifi/mqtt --pristine --board nrf7002dk_nrf5340_cpuapp --no-sysbuild -- -DNCS_TOOLCHAIN_VERSION:STRING="NONE" -DBOARD_ROOT:STRING="/home/jayant/project/ncs-project/wifi/mqtt" -DCONF_FILE:STRING="/home/jayant/project/ncs-project/wifi/mqtt/prj.conf;/home/jayant/project/ncs-project/wifi/mqtt/boards/nrf7002dk_nrf5340_cpuapp.conf" -DOVERLAY_CONFIG:STRING="/home/jayant/project/ncs-project/wifi/mqtt/overlay-tls-nrf7002.conf"
>    ```
>
>    通过阅读这个命令携带的冗长的参数，我们可以知道，编译系统采用了以下三个配置文件：
>
>    - `prj.conf`
>    - `boards/nrf7002dk_nrf5340_cpuapp.conf`
>    - `overlay-tls-nrf7002.conf`
>
>    第一个是zephyr系统默认的配置文件，第二个是系统根据所选的板子自动选择的配置文件，第三个是我们创建编译目标时手动选择的附加的配置文件。三者的内容最终是合并在一起，然后才采用的。

## 3.4. 程序下载与运行

![image-20230823115845564](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined615506fece97ae5ba6204b56e90c13d6.png)

1. 连接好开发板，确认VS Code中可以识别到已连接的Jlink
2. 点击“Flash”按钮，下载编译好的程序（如果是点击图中红色框内按钮，则是擦除并下载）

![image-20230823121558235](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedd1bdc1f1f68476eba7f6af24f87e0e55.png)

![image-20230824102839317](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinede6102d5da23044d4cf089515960f267e.png)

3. 打开编号较大的串口（这是应用核的串口，另一个串口是5340网络核的默认串口），并点击开发板上的reset 按钮让程序重新运行
   ![image-20230823122202243](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined02a298bf599578f9c1961934aeb56c07.png)
4. 等待一段时间，就能看到板子已经依次成功连上WiFi、互联网、MQTT broker、并订阅了topic。由于我们之前设置编译目标时选择了TLS的overlay配置文件，所以可以看到这里连接的是MQTTS默认的8883端口，并且启用了TLS协议。
   ![image-20230824103416044](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedc42a403637f5bd7e2dd7b496b0673b52.png)

## 3.5. MQTT通信测试

例程默认连接的是`test.mosquitto.org`这个免费的公共MQTT broker，它仅供测试使用。

我们在PC上使用一个MQTT客户端，也连上这个broker，与板子进行通讯测试。这里以MQTTX为例：

### 连接到MQTT broker

![image-20230824104643996](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined8ae16653daa3854ec917dfcd03b86b4c.png)

首先打开MQTTX，在连接的右侧点击“+”，选择新建连接。在右侧填入基本信息：

- 名称：此链接在客户端软件里显示的名称，与MQTT协议本身无关；
- Client ID：此客户端在MQTT broker上被识别的身份。由于这是个免费公共broker，因此可以随意填写，不要填写容易与其他人重复的ID即可；
- 服务器地址：协议选择MQTT，地址填写`test.mosquitto.org`。
- SSL/TLS：无需启用。此Broker既支持TLS连接也支持非加密连接。虽然开发板是通过TLS方式连接的，但PC客户端即使通过不同方式连接，最终只要连接到同一个broker上，也是可以通讯的。

其余参数保持默认即可，然后点击右上角的“连接”。

### 订阅主题并接收数据

通过串口日志我们可以看出:

- 开发板订阅的topic为：`F4CE36000384/my/subscribe/topic`
- 开发板发布数据的topic为：`F4CE36000384/my/publish/topic`

> 这里的Client ID是硬件ID生成的，你需要查看你的板子的ID是多少。

![image-20230824105539237](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined7ef2365f3e6c08d36930d0eb542bf2be.png)

因此在MQTTX中，我们要订阅`F4CE36000384/my/publish/topic`，从而接收开发板上发送的数据：

![image-20230824105703966](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedcba7ff621fb9f15275bb430f87224273.png)

![image-20230824105745173](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined33606f01907959fe41cd366e4f65f859.png)

- 点击“添加订阅”
- 填写Topic，并将服务质量（QoS）设置为1（确保对方收到至少一次，也就是有重传确认机制）。

此例程是定时发送数据的，但也可以通过按下开发板上的Button1或Button2来立即发送数据。

### 发送数据到开发板

同理，我们可以发送数据到`F4CE36000384/my/subscribe/topic`，从而让开发板可以接收到：

![image-20230824110521147](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined514cd4d8177f58de816841353fc16082.png)

- Payload：选择字符串（Plaintext）。由于MQTT传输的底层就是二进制传输。因此，我们在Payload选项中，选择的其实是客户端如何编码，如何进行格式检查。MQTT协议本身并不会有什么字段来描述自己携带的数据类型。
- QoS：选择1，确保Broker会收到至少一次。
- Topic：填入开发板订阅的Topic，这里是`F4CE36000384/my/subscribe/topic`
- 下方填入要发送的内容，并发送数据

![image-20230824111005271](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined206a228bd46397397451e455f8029a22.png)

![image-20230824111020710](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined1540c3595cefa7632c6ba99a2dbc5640.png)

可以看到开发板成功收到数据。



# 4. 代码解析

## 4.1. 编译与配置系统

### 源码的组织

源码都位于`src`目录下，分成了`common`和几个模块：

![image-20230824113012286](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined7d97eada61d2ae123deb78a33d2f54e0.png)

我们可以注意到，代码是没有`main()`函数的。因为Zephyr支持静态定义线程，系统上电reset后，各个模块的线程就直接运行起来了，无需`main()`函数。

源码使用CMake进行管理，我们可以看到项目顶层`CMakeLists.txt`使用`add_subdirectory()`引用了各个模块的`CMakeLists.txt`，从而把所有源码组织在一起。

![image-20230824114611064](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined4d97872005af6bf66f1cfc7d708f5f2e.png)

### Kconfig配置系统

各个模块以及Zephyr系统有大量的配置项可以修改，这些配置项是以预编译宏的形式存在的。由于配置项很多，Zephyr采用了Kconfig进行配置项的管理。

例程目录下的顶层Kconfig文件定义了本工程的一个配置项菜单，它包含本工程所需的全部配置：

![image-20230823115854511](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined5edc8b3e806088fdc09c4be34763171f.png)

和CMake的逻辑类似。顶层Kconfig也是可以通过引用各个模块的菜单，从而形成一个整个项目的大型菜单。菜单的前一部分是引用了`src/modules/`目录下各个子模块的Kconfig菜单，后一部分是引用了Zephyr的Kconfig菜单。我们可以通过点击Kconfig按钮来查看这个完整的菜单：

![image-20230824115336388](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined5cd9076d29505f3466814393ebc83882.png)

在完整的菜单中，我们可以看到，顶层的两级目录就分别是例程本身的各个模块的菜单，以及Zephyr系统的配置菜单。

### 设置配置项的值

Kconfig是一个**菜单**，真正发挥作用的是菜单中各个**配置项的值**。其中的配置项的值会有很多个来源：

- 在Kconfig文件定义菜单时，某些配置项会有默认值
- 在创建编译目标，选择板子时，这个板子自带的一些配置项。见`${NCS}/nrf/boards/arm/`或`${NCS}/zephyr/boards/arm/`下各个板子的目录中的`.conf`文件
- 工程目录下，`boards/`目录下与板子对应的`.conf`配置文件
- 工程目录下默认的`prj.conf`配置文件，这也是最常用的
- 创建编译目标时，选择附加的Kconfig片段，例如`overlay-tls-7002.conf`

> 配置项的来源还有很多，例如使用CMake编译时指定`CONFIG_`开头的变量，还有一些隐含的配置项，无法直接修改，只会被其他配置项联动修改等等。要了解更多关于配置项的问题，可参考：https://docs.zephyrproject.org/latest/build/kconfig/setting.html#the-initial-configuration

所有的配置项最终在编译时都会合并到`build/zephyr/.config`临时文件中，要想知道自己的配置有没有成功适用，查看这个文件即可。

在Kconfig菜单界面修改后，如果只点击"Apply"，那么此修改只会保存到`.config`临时文件中。下次Build时可以生效。但是如果修改了其他config文件、CMake文件，或者执行了重新编译的情况下，这些修改就会随着`.config`文件一起消失。如果想让自己的修改永久保存，需要点击Save to file，然后选择一个合适的文件保存。通常，与特定板子有关的，可以保存到`boards`目录下的配置文件中；如果是这个项目通用的配置，可以保存到`prj.conf`中。

![image-20230824122017814](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb5b6716112483060753137eac648e190.png)

举例来说：

1. MQTT服务器地址是在哪里配置的？
   在`src/modules/transport/Kconfig.transport`中，定义菜单时，`MQTT_SAMPLE_TRANSPORT_BROKER_HOSTNAME`的默认值是`test.mosquitto.org`
2. Wi-Fi密码在哪里配置的？
   可以像第3节中一样，在板子的`conf`文件中配置，也可以直接写在项目的`prj.conf`中。

## 4.2. 代码框架

![image-20230824141934689](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined78c62e6783cac1eb76e81d9e02fdd99e.png)

此例程有6个模块，分别是：

- Trigger：定时触发，让其他模块向MQTT broker发布消息，同时在检测到按钮按下时也触发；
- Sampler：当其他模块发出请求时，采样数据，并发送给其他模块。此例程中，采样的数据用一串字符串代替；
- Transport：负责处理MQTT连接；
- Network：负责网络连接；
- LED：负责根据其他模块发出的消息，控制不同的LED状态；
- Error：监控其他模块发出的报错信息，若出现报错，则执行重启。



### Zbus与模块化编程

在模块化的编程中，除了模块本身的实现以外，模块间的通信也是非常重要的一环，往往牵扯到大量的队列、信号量和锁的交互。

为了减轻这部分的工作量，Zephyr提供了Zbus通信框架，相当于对上述操作进行了一个封装。Zbus有点像“本地的MQTT”，每个模块可以在不同的通道（Channel）上发布/订阅消息。

![image-20230824143949656](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined369630547fda197273c1fedf4f872d65.png)

Zbus可以使模块间实现解耦，因为每个模块实际上只和Zbus交互，并不知道其他模块的存在。

我们在`src/common/message_channel.h`中可以看到总共**声明**了4个Zbus通道：

```c
ZBUS_CHAN_DECLARE(TRIGGER_CHAN, PAYLOAD_CHAN, NETWORK_CHAN, FATAL_ERROR_CHAN);
```

在`src/common/message_channel.c`中可以看到每个通道的**定义**，这里以`NETWORK_CHAN`通道为例：

```c
ZBUS_CHAN_DEFINE(NETWORK_CHAN,
		 enum network_status,
		 NULL,
		 NULL,
		 ZBUS_OBSERVERS(transport IF_ENABLED(CONFIG_MQTT_SAMPLE_LED, (, led)), sampler),
		 ZBUS_MSG_INIT(0)
);
```

可以看到定义了通道的名称，payload的数据类型以及通道数据的接收者（Observers）。这里的Observers就是能从这个Channel接收消息的模块，可以填写多个。这里可以看到一个条件预编译：如果定义了`CONFIG_MQTT_SAMPLE_LED=y`，则此处就会插入一个“`, led`”字符串。

Zbus支持多对多通信，支持同步、异步通信。

### Zbus同步接收

同步通信的例子是`led`模块，我们可以看到`src/modules/led/led.c`中并没有定义线程，而是只定义了一个Zbus Listener和LED的回调函数：

```c
// 此处仅定义了listener，没有定义其要监听哪个channel，因为在前面Zbus定义channel时就已经确定好observer的名称了
ZBUS_LISTENER_DEFINE(led, led_callback);
```

这就是同步通信的例子，每当Channel上有消息产生时，这个回调函数都会**在发送端的发送函数内被执行一次**。所以，同步接收的回调函数应该尽量快速执行，以免阻塞发送端的线程。

### Zbus异步接收

异步通信的例子是`sampler`模块，我们可以看到`src/modules/sample/sampler.c`中分别定义了Zbus Subscriber和一个线程：

```c
// 由于在src/common/message_channel.c中，定义Zbus channel时就已经确定好observer的名称了
// 因此此处只需定义自身的observer的名称即可
ZBUS_SUBSCRIBER_DEFINE(sampler, CONFIG_MQTT_SAMPLE_SAMPLER_MESSAGE_QUEUE_SIZE);

......
    
    
static void sampler_task(void)
{
	const struct zbus_channel *chan;

	while (!zbus_sub_wait(&sampler, &chan, K_FOREVER)) {
		if (&TRIGGER_CHAN == chan) {
			sample();
		}
	}
}

K_THREAD_DEFINE(sampler_task_id,
		CONFIG_MQTT_SAMPLE_SAMPLER_THREAD_STACK_SIZE,
		sampler_task, NULL, NULL, NULL, 3, 0, 0);
```

在线程中，通过`zbus_sub_wait()`函数来监听通道上是否有消息。由于此消息只是用来触发采样的，消息内的payload并无任何作用，因此此处没有使用`zbus_chan_read()`函数。

>Zbus接收的本质：
>
>1. 每定义一个subscriber，就会同时为它定义一个`k_msgq`队列；
>2. 每次数据发送到某个channel时，实际上是给这个channel下的每个obsever的队列都填充了相同的消息；
>3. `zbus_sub_wait()`的作用是阻塞等待，并从队列中取出消息；
>4. `zbus_chan_read()`的作用是从已经出队的消息中提取真正的数据；

### Zbus数据发送

在`src/modules/trigger/trigger.c`中可以看到，发送的行为不需要定义类似publisher的东西。直接向channel发布数据即可：

```c
err = zbus_chan_pub(&TRIGGER_CHAN, &not_used, K_SECONDS(1));
```

> 关于Zbus的总结：
>
> - 每次数据发送到某个channel时，实际上是给这个channel下的每个observer的消息队列都push了相同的消息；并且如果有注册的同步接收的回调函数的话，还要执行这个回调函数
> - 由于发布、接收都是对锁操作的封装，因此它们都不能在中断服务函数中使用；并且都可以设置超时时间以避免一直阻塞
> - 不必担心线程阻塞造成功耗问题，因为在Zephyr中，进入IDLE线程时会自动进入低功耗模式
> - 发送数据是拷贝的，因此，消息数据用局部变量即可。此外，有多少个observer就会把数据拷贝多少份，如果需要做大量数据的传输，注意CPU的开销。
> - ZBUS其实并没有真正把消息存入k_msgq队列，真正存储消息的位置只有Channel结构体的一个成员，长度为1个payload。每次新消息发布到channel上时，这个用于存储消息的位置就会被立即覆盖。消息队列中存储的是一个指向该位置的指针。因此，当发送速度太快，接收端来不及消费时，会出现前面的数据被后面的数据覆盖掉的情况。但是消息的总个数还是不会变的。因此，ZBUS只适合用来传输一些“状态值”。如果真要传输大量数据，推荐用k_msgq。
> - 更多资料，参考：https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/zephyr/services/zbus/index.html#zbus

## 4.3. Wi-Fi连接过程

网络连接由network模块控制，在`src/modules/network/CMakeLists.txt`中，我们可以看到，根据不同的板子选择，实际参与编译的是不同的源代码。由于我们选择的是7002开发板，因此这里只会编译`network_wifi.c`.

```c
static void connect(void)
{
	struct net_if *iface = net_if_get_default();

	if (iface == NULL) {
		LOG_ERR("Returned network interface is NULL");
		SEND_FATAL_ERROR();
		return;
	}

	int err = net_mgmt(NET_REQUEST_WIFI_CONNECT_STORED, iface, NULL, 0);

	if (err) {
		LOG_ERR("Connecting to Wi-Fi failed. error: %d", err);
		SEND_FATAL_ERROR();
	}
}

....

static void network_task(void)
{
	net_mgmt_init_event_callback(&net_mgmt_callback, wifi_mgmt_event_handler, MGMT_EVENTS);
	net_mgmt_add_event_callback(&net_mgmt_callback);
	net_mgmt_init_event_callback(&net_mgmt_ipv4_callback, ipv4_mgmt_event_handler,
				     NET_EVENT_IPV4_ADDR_ADD | NET_EVENT_IPV4_ADDR_DEL);
	net_mgmt_add_event_callback(&net_mgmt_ipv4_callback);

	/* Add temporary fix to prevent using Wi-Fi before WPA supplicant is ready. */
	k_sleep(K_SECONDS(1));

	connect();
}
```

代码非常直观，先是分别给WiFi和IPv4注册了不同的回调函数，然后再执行连接。这里的网络回调函数和连接分别用到了两个模块，[Network Interface](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/zephyr/connectivity/networking/api/net_if.html#net-if-interface)和[Network Management](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/zephyr/connectivity/networking/api/net_mgmt.html#net-mgmt-interface)。

### Network Interface

所有与网络相关的处理都与网络接口有关。网络接口是在编译时就确定的。我们可以看到`connect()`函数中获得了默认的网络接口：

```c
struct net_if *iface = net_if_get_default();
```

由于Zephyr将nRF7002抽象成了网卡，并且在NCS中已经有了7002的驱动代码，所以我们不必太关心底层细节，就能实现网络通信。

有关7002驱动的架构，可以查看：https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/drivers/wifi/nrf700x/nrf700x.html



### Network Management库

Network Management可以让应用层与网络层之间、或者网络层的内部进行方便的函数调用。我们通过查看`net_mgmt`的定义可以知道，实际上`net_mgmt()`并不是一个单独的函数，而是把第一个参数放入函数名的多个函数。

```c
#define net_mgmt(_mgmt_request, _iface, _data, _len)			\
	net_mgmt_##_mgmt_request(_mgmt_request, _iface, _data, _len)
```

这也意味着每个调用`net_mgmt(ABC)`的地方，都会在SDK的某个地方对应一个函数的定义：

```c
#define NET_MGMT_DEFINE_REQUEST_HANDLER(_mgmt_request)			\
	extern int net_mgmt_##_mgmt_request(uint32_t mgmt_request,	\
					    struct net_if *iface,	\
					    void *data, size_t len)
```

这种实现方式可以让整个网络API有更强的扩展性，同时，让用不到的函数在编译时就被消除，从而减少代码的大小。

因此，当我们想查看某个`net_mgmt(request,...)`函数做了什么的时候，可以去整个SDK中搜索这个函数的参数，从而找到这个函数注册的地方，从而查看它的具体的实现。

> 此Network Management的实现方式是实验性的，今后可能会更新。

### Wi-Fi的自动连接

我们在整个SDK中全局搜索`NET_REQUEST_WIFI_CONNECT_STORED`就可以查到前述网络API被注册的地方，其实际的代码位于`${NCS}/nrf/subsys/net/lib/wifi_mgmt_ext/wifi_mgmt_ext.c`。

![image-20230908172441366](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined3ed053446cde37fbe3be7b7716cd3f5a.png)

由此我们可以看出Network Management API的扩展性很强。Nordic直接在Zephyr的Network Management API里，注册了一个新的API，扩展出了通过config文件配置Wi-Fi凭据的功能，方便了例程的配置。这就是[Wi-Fi management extension](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/libraries/networking/wifi_mgmt_ext.html)库，它能让例程上电自动连接预设Wi-Fi。

从代码中可以看出，它的具体步骤是：先把config中静态配置的Wi-Fi凭据保存到Flash中，然后自动执行Wi-Fi连接。大家可以打开这个代码文件，去查看具体的代码。

### Wi-Fi凭据的管理

[Wi-Fi credentials](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/libraries/networking/wifi_credentials.html#wi-fi-credentials)这个库用于管理Wi-Fi凭据。它可以让Wi-Fi凭据存储在MCU内部。

Wi-Fi凭据，对于Personal模式（PSK, Pre-Shared Key）来说，就是密码。对于Enterprise模式来说，就是各类证书和密钥。我们可以从`${NCS}/nrf/include/net/wifi_credentials.h`中看出，这两种凭据是通过不同的两种结构体来存储的：

```c
struct wifi_credentials_header {
	enum wifi_security_type type;
	char ssid[WIFI_SSID_MAX_LEN];
	size_t ssid_len;
	uint8_t bssid[WIFI_MAC_ADDR_LEN];
	uint32_t flags;
};

// Personal凭据只存储header和密码
struct wifi_credentials_personal {
	struct wifi_credentials_header header;
	char password[WIFI_CREDENTIALS_MAX_PASSWORD_LEN];
	size_t password_len;
};

// Enterprise凭据会存储Header和各类身份信息，可能包含密码、密钥、证书等
// 注意：Enterprise凭据目前只有定义，其功能并未实现
struct wifi_credentials_enterprise {
	struct wifi_credentials_header header;
	size_t identity_len;
	size_t anonymous_identity_len;
	size_t password_len;
	size_t ca_cert_len;
	size_t client_cert_len;
	size_t private_key_len;
	size_t private_key_pw_len;
};
```

Wi-Fi凭据的写和读都很简单，分别提供了两种API。一种是直接传递参数，另一种是通过结构体来传递参数。由于篇幅原因，这里只列出较短的，也就是通过结构体传参数的形式：

```c
// 写
int wifi_credentials_get_by_ssid_personal_struct(const char *ssid, size_t ssid_len,
					      struct wifi_credentials_personal *buf);

// 读
int wifi_credentials_get_by_ssid_personal_struct(const char *ssid, size_t ssid_len,
					      struct wifi_credentials_personal *buf);

// 删
int wifi_credentials_delete_by_ssid(const char *ssid, size_t ssid_len);

// 遍历
void wifi_credentials_for_each_ssid(wifi_credentials_ssid_cb cb, void *cb_arg);
```

> 注：
>
> - Enterprise模式的相关API目前并未实现，因此无法连接。
> - 用于凭据永久存储的后端（Backend）有两种。一种是[Zephyr Settings存储服务](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/zephyr/services/settings/index.html)，另一种是[PSA安全存储](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/zephyr/samples/tfm_integration/psa_protected_storage/README.html)。前者只是对Flash读写进行封装的库，使得整个Zephyr系统中的各个模组都可以方便地存储自己的非易失数据；而后者是ARM PSA (Platform Security Architecture)中提出的一种安全存储服务，这种方式可以让自己的应用程序运行在“非安全（Non-Secure）”空间的同时，把凭据存储在“安全（Secure）空间”中，它需要TF-M才能工作。具体内容不在本文中阐述。修改后端的配置可以参考：https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/libraries/networking/wifi_credentials.html#configuration

### Wi-Fi连接的管理

前面提到，在`${NCS}/nrf/subsys/net/lib/wifi_mgmt_ext/wifi_mgmt_ext.c`中，对存储中的每一个SSID遍历执行了`add_stored_network`函数。如果我们追踪下去，就会发现最终执行的连接函数，内部都是`wpa_cli`的命令，也就是我们在Linux上常见的一个Wi-Fi管理工具。

![image-20231002155758866](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined9a261aaf301a9349c8b90fb0a716fc4a.png)

不过，当我们开发实际的产品时，肯定还是要通过蓝牙、USB、串口等其他方式把Wi-Fi凭据传入的。而且，实际上非专业的客户也不可能真的去写这些`wpa_cli`命令。

Nordic当然也提供了通过BLE配置Wi-Fi凭据的方案，例程是[Wi-Fi: Provisioning Service](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/samples/wifi/provisioning/README.html#wi-fi-provisioning-service)，位于`${NCS}/nrf/samples/wifi/provisioning`。这是一个完整的BLE服务，可以通过手机APP（[安卓版本](https://play.google.com/store/apps/details?id=no.nordicsemi.android.wifi.provisioning)和[iOS版本](https://apps.apple.com/cn/app/nrf-wi-fi-provisioner/id1638948698)都有）对nRF7002DK进行配网。手机App和BLE Service之间数据的格式使用[Protocol Buffers](https://protobuf.dev/)来管理。当然手机App的源码也是开放的，客户可以把它们集成到自己的手机App中：

- https://github.com/NordicSemiconductor/Android-nRF-Wi-Fi-Provisioner
- https://github.com/NordicSemiconductor/IOS-nRF-Wi-Fi-Provisioner

如果你愿意阅读这个BLE Service的源码，会发现这个Service中，它通过BLE获得Wi-Fi密码后，也是用前面说的 Wi-Fi credentials 库对凭据进行存储。此外，它连接Wi-Fi所使用的方法是：

```c
rc = net_mgmt(NET_REQUEST_WIFI_CONNECT, iface,
		     &cnx_params, sizeof(struct wifi_connect_req_params));
```

> 这段代码位于`${NCS}/nrf/subsys/bluetooth/services/wifi_prov/wifi_prov_handler.c`

这又是一个Network Management API。其注册的位置在`${NCS}/zephyr/subsys/net/l2/wifi/wifi_mgmt.c`。它需要的参数除了基本的wifi连接所需的信息以外，还需要的就是一个Interface。而这个Interface已经由nRF7002的驱动提供好了，就像前文所述，直接用`net_if_get_default()`就能获得这个Interface。

如果你想用其他方式配置Wi-Fi凭据，也推荐参考这个BLE Service中连接Wi-Fi的方式。

## 4.4. MQTT连接过程

### MQTT Helper 库

Zephyr有一个很基础的[MQTT库](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/zephyr/connectivity/networking/api/mqtt.html#mqtt)，支持MQTT 3.1.0和3.1.1。它是基于Socket编写的，简单直接，但是不太好用。由于它只提供API，也就是连接、发布、订阅这些，还要开发者自己处理一些文件描述符（fd）。在之前版本的NCS中有个例程叫`mqtt_simple`，MQTT的心跳包甚至要在main.c里单独用一个定时任务来发送，目前这个例程已经被删除了。

Nordic提供了[MQTT Helper库](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/libraries/networking/mqtt_helper.html#api-documentation)，对Zephyr的MQTT接口进行了封装，使其更加易用。一方面，它单独建立了一个线程，用来发送MQTT心跳包；另一方面，它把大部分重要的MQTT参数都变成了Kconfig菜单中的参数，便于你做配置。

通过阅读例程`src/modules/transport/transport.c`，可知MQTT Helper的用法：

![image-20231005225532340](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedaec0801aff69269358b6058a3ef4db52.png)

![image-20231005230011226](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined096aca91a7d14b57d75ab6a9466c1b84.png)

基本上，就是配好回调函数和各种参数，初始化一下再连接服务器即可。当然，实际的例程代码写的不是这么直接。

### Zephyr状态机框架 (SMF, State Machine Framework)

由于`transport.c`代码中的MQTT连接并不是像前文说的直来直去进行的，而是分散在各处。因此，在继续分析MQTT代码之前，有必要先分析一下SMF的代码，以方便不熟悉的读者。

我们知道状态机是开发中常用的一种框架，只要**明确**规定好一个模块被允许存在的所有状态、规定好每个状态下被允许的行为，以及各个状态之间切换的条件，就能写出较为完善、逻辑清晰、健壮性强、易于调试的代码。

最常见的状态机代码是用`switch...case`语句编写的，通过一个`state`变量来判断当前处于哪个`case`，执行完不同的处理代码后，根据其他变量、事件等等不同的因素，来决定是否要切换到其他`state`值。常见的例子是写一个自定义二进制协议的解包代码，“状态”就是当前正在处理的是包头、数据、包尾还是转义字符，而“切换条件”就是输入的二进制流。

Zephyr SMF和`switch...case`也没什么区别，只不过它把各个步骤进行了拆分，让你把“状态机的结构”和“各个状态的处理代码”分开，然后通过回调函数注册。比如，它把每个状态内的处理函数分为了`entry`、`run`、`exit`三部分，分别对应“进入此状态时要执行的一次性代码”、“在此状态循环处理时运行的代码”、“退出此状态时要执行的一次性代码”，让你不用写一堆标志位来判断状态的切换、也不用在`switch...case`语句中嵌套一堆`if...else`语句。另一方面，SMF也做好了状态机的嵌套处理，每个状态的内部还可以有一堆子状态，每个子状态也可以有`entry`、`run`、`exit`三个处理函数。通过把这些内容拆开，让我们可以先定义好一个状态机的结构，再给每个状态和子状态注册回调函数，从而使得代码更加清晰。

要使用SMF，首先需要定义上下文(context)结构体：

```c
static struct s_object {
	/* This must be first */
	struct smf_ctx ctx;

	/* Last channel type that a message was received on */
	const struct zbus_channel *chan;

	/* Network status */
	enum network_status status;

	/* Payload */
	struct payload payload;
} s_obj;
```

所谓的上下文，就是你在处理这个状态机时所需要的全部信息，例如标志位等，把他们全填入这个自定义结构体。

然后，定义好所有的状态枚举，注册好每个状态的`entry`、`run`和`exit`函数即可。

```c
/* Internal states */
enum module_state { MQTT_CONNECTED, MQTT_DISCONNECTED };

/* Construct state table */
static const struct smf_state state[] = {
	[MQTT_DISCONNECTED] = SMF_CREATE_STATE(disconnected_entry, disconnected_run, NULL),
	[MQTT_CONNECTED] = SMF_CREATE_STATE(connected_entry, connected_run, connected_exit),
};
```

关于状态切换，可以用`smf_set_state`函数，如：

```c
smf_set_state(SMF_CTX(&s_obj), &state[MQTT_CONNECTED]);
```

状态切换时，就会执行前一个状态的`exit`函数，以及后一个状态的`entry`函数。

在本模块的线程函数中，每次通过ZBus接收到新的消息后，都会通过`smf_run_state(SMF_CTX(&s_obj))`来处理这个消息携带的数据。这个函数底层执行的就是当前状态的`run`函数。

由此可见SMF也是比较简单易用的，步骤就是先定义状态，然后注册回调函数，最后执行。

MQTT的连接就发生在状态机执行初始状态的这一步：

```c
/* Set initial state */
	smf_set_initial(SMF_CTX(&s_obj), &state[MQTT_DISCONNECTED]);
```

这时就会执行初始状态的`entry`函数，进行MQTT的连接。

> 其他补充：
>
> 1. 本例程没有展示出状态机嵌套的功能，要想了解这部分，可以参考[SMF文档](https://docs.zephyrproject.org/latest/services/smf/index.html)。
> 2. SMF的`run`函数和`set_state`函数何时执行，完全由开发者决定，如果你想要事件驱动型的状态机框架（阻塞等待某个事件，然后再执行run函数），可以参考SMF文档中的写法。。
> 3. 在`exit`函数内部进行`set_state`这种行为是有歧义的，因为`set_state`本身就是要进入一个新的状态，而`set_state`内部同时也会调用前一个状态的`exit`函数，因此SMF底层会拒绝这种操作，会报错。
> 4. SMF框架没有限制`set_state`函数必须和状态机本身的`run`函数处于同一个线程（本例程中，`set_state`就在MQTT的回调函数中，与状态机不在一个线程）。因此完全有可能出现`run`函数还没执行完，`exit`函数就在另一个线程被执行了的情况。开发者自己要控制好这一情况。
> 5. 为了防止**4**的情况出现，我们的回调函数，不论是MQTT回调函数，还是状态机的回调函数，都要**快进快出**，而且要保证在状态机层面上是**原子操作**。因此，我们可以发现代码中，这些回调函数实际都没做什么工作，而是把具体的代码提交到[work queue](https://docs.zephyrproject.org/latest/kernel/services/threads/workqueue.html)去执行，然后就马上返回了。work queue是个单独的线程，从work queue的层面上讲，每个work都是“原子”的，就不用担心**4**中的情况了。

### TLS Credentials 库与证书管理

我们知道，SSL加密通信，其核心不仅仅在于加密，还在于身份的认证，需要确保对方真的是你想要连接的那个对象，这里就分为三种情况：

- 如果只是设备验证服务器，单向验证，则设备中需要存储服务器对应的**CA证书**，用CA证书校验服务器出示的证书是否合法。这也是我们电脑访问各大网站的常见方式。

- 如果只是服务器验证设备，单向验证，则设备中需要存储**客户端证书**，用于出示给服务器。服务器中预先注册了设备的证书信息，因此可以检查设备是否是冒充的。当然，设备也需要存储此证书对应的**私钥**；
- 若双向都要验证，则三样都需要。这也是目前物联网行业常见的方式。

在MQTTX客户端软件中，我们就可以看到这三个文件的配置项：

![image-20231006004212156](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined073e0683a16b7250e4ceccbba713da7f.png)

如果我们的开发板要想通过MQTTS连接到MQTT Broker，当然也需要存储这些凭据信息。

我们使用的电脑已经预安装了世界上各大CA机构的证书，因此我们访问世界上绝大多数服务器，都可以用已经安装的CA证书去检查该服务器是否是冒充的。但是嵌入式设备不可能存这么多证书，最好是按需存储，要通过TLS连哪个服务器，就只存哪个服务器对应的CA证书。

Zephyr提供了[TLS Credentials](https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/zephyr/connectivity/networking/api/sockets.html#tls-credentials-subsystem)库来管理各类证书、私钥。简而言之，它管理了一个TLS连接所需的**CA证书**、**设备证书**、**设备私钥**，并且通过一个编号来索引。每次要进行TLS连接时，只需要指定一个编号即可，这个编号叫做`SEC_TAG`。

直观地说，就是要先存储证书和私钥：

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined218481b1307455f5735b5f38f0b10ab4.png" alt="image-20231006010250433" style="zoom:67%;" />

> 同一个TLS连接所需的CA证书、设备证书、设备私钥都存储在同一个`SEC_TAG`下。

然后，在底层建立Socket连接时，通过传参传入`SEC_TAG`，就可以使用这些证书了：

![image-20231006010436194](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined871a7b7294ddcc6c299972a87bdec0a4.png)

这个库的设计逻辑在于**“存储”与“使用”分离**。存储后端可以自由切换，它既可以是单纯的Flash存储，也可以是ARM平台安全架构（PSA）提供的安全存储服务（Protected Storage Service）。

一个实例就是nRF9160，我们知道9160的证书是通过python脚本或者nRF Connect for Desktop软件烧录到Modem中的（底层都是AT指令），烧录时其实就指定了Security Tag号（例如，nRF Cloud默认用的就是`16842753`）。在应用层建立TLS连接时（例如连接到nRF Cloud时），都是通过`SEC_TAG`号来访问私钥的。这样既能完成握手，又能让应用层无法读取到证书、私钥的内容，从而确保了信息安全。

> 实际上，9160的证书和私钥可以不烧进去，而是直接在Modem内部生成。然后生产线上只取出证书，上传到服务器即可，从而确保私钥绝对不会泄漏。

### MQTT证书文件配置流程

回到例程中来，我们的证书究竟是如何配置进去的？

首先，例程默认连接的服务器是`mqtt://test.mosquitto.org:1883`。我们可以用HTTP协议，也就是直接用浏览器访问https://test.mosquitto.org/，查看介绍：

![image-20231006012304338](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined85c18a786b4002dc69d497c7aab4677b.png)

我们可以得知，这个服务器有许多端口，每个不同的端口上运行的是不同的协议。其中8883端口运行的是MQTT over TLS，并且只需单向验证服务器，服务器不需要验证客户端。 

我们先看看之前添加的`overlay-tls-nrf7002.conf`里有哪些与SSL有关的config：

![image-20231006004756724](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined5de0f391c55f62a347b0a24b8ca39a50.png)

首先要使能TLS，然后是目标服务器的端口号要改为8883。然后选择载入默认的SSL证书，启用加密库，最后Socket也要启用TLS的支持。

MQTT Helper有默认的证书文件名，我们可以看到在`${NCS}/nrf/subsys/net/lib/mqtt_helper/cert/mqtt-certs.h`中，默认包含的CA证书文件名为`ca-cert.pem`：

![image-20231006013111085](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinede27245812c4ec43acb5b451408cbf332.png)

而`CONFIG_MQTT_HELPER_PROVISION_CERTIFICATES`配置决定了MQTT Helper会不会在编译时自动包含这个证书，并且在MQTT连接前自动载入这个证书。具体代码位于`${NCS}/nrf/subsys/net/lib/mqtt_helper/mqtt_helper.c`

> 读者可以尝试把服务器改成`broker.emqx.io`，这是另一个免费的测试用MQTT broker，文档地址是https://www.emqx.com/zh/mqtt/public-mqtt5-broker
>
> 在网页上下载到CA证书后，把代码中的`ca-cert.pem`改成下载好的证书即可。注意不能直接改文件名，因为这个文件是在C语言中被当成字符串包含的，所以下载好的证书要编辑一下，把里面的内容都用引号括起来，并添加好`\n`。

# 5. 总结

1. MQTT是轻量高效的网络协议，适合物联网，实现了设备间解耦通信。
2. 由于是例程，Wi-Fi的凭据和TLS的凭据都是静态配置，被编译进固件的。编译前注意检查配置。
3. 例程是无main架构，各个模块通过ZBUS进行线程间通信。
4. 程序先连上MQTT broker，然后订阅主题，再定时发布消息。
5. Zephyr提供了状态机框架SMF
6. Wi-Fi 连接的底层是 WPA Supplicant 软件，也有Network Management API可用。Wi-Fi凭据的存储用的是 Wi-Fi Credential 库。 Wi-Fi Credential 使用 SSID 来索引。
7. MQTTS连接使用MQTT Helper库。MQTTS的连接需要SSL，SSL证书的存储用的是 TLS Credential库。它使用SEC_TAG来索引。
