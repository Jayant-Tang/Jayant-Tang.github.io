---
title: 使用Ubuntu进行WiFi抓包
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2022-12-16 16:12:28
cover: null
tags:
- Wireshark
- WiFi6
- Linux
categories: WiFi
cnblogs:
  postId: '21180787'
  url: https://www.cnblogs.com/jayant97/articles/21180787
  lastPublishedAt: '2026-07-06T18:39:19+08:00'
  sourceHash: sha256:025f28056885fbacf5c3612e880d1437284da7743b0b55710385db84a48c9a22
  status: synced
  postType: Article
---

# 1. 前言

​	在之前的文章里，我介绍了如何在Windows中使用NPCAP把无线网卡变为monitor模式，并用Wireshark进行抓包。但是Windows下支持monitor的无线网卡实在是太少了，笔记本自带的PCIE无线网卡更是无法支持。	

​	本文介绍如何在Linux系统下进行WiFi的抓包，并且在本地或者用另一台Windows电脑的Wireshark进行实时分析。

​	本文使用的硬件环境：

- Ubuntu笔记本电脑：
  - 操作系统：Ubuntu 22.04
  - WiFi网卡：Intel(R) Wi-Fi 6E AX211 160MHz （支持WiFi6E）
  - 有线网口（可选）：WiFi网卡变成monitor模式后，用有线网让Windows电脑远程连接到Ubuntu电脑
- 路由器：支持wifi6的路由器
- 手机：支持wifi6的手机
- Windows笔记本电脑（可选）

​	示意图如下，虚线内容是可选的：

![image-20221216162542858](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined673ba0bba6312c44b4e1697da2277dcd.png)

> 在linux下查看自己的WiFi网卡是否支持抓包：
>
> **网卡驱动已经安装的情况**：
>
> 1. 查看自己电脑上的所有网卡，并查看其驱动：
>
>    ```bash
>    $ sudo lshw -C network                                                            
>       [sudo] password for jayant:
>      *-network
>           description: Wireless interface
>           product: Alder Lake-P PCH CNVi WiFi
>           vendor: Intel Corporation
>          ...
>           logical name: wlp0s20f3mon
>          ...
>          ...
>           configuration: broadcast=yes driver=iwlwifi driverversion=5.15.0-56-generic firmware=64.97bbee0a.0 so-a0-gf-a0-64.uc latency=0 link=yes multicast=yes wireless=IEEE 802.11
>           resources: iomemory:600-5ff irq:16 memory:601d1cc000-601d1cffff
>    ```
>    
>   可以看到 在configuration中，`driver=iwlwifi`，说明wifi网卡的驱动是`iwlwifi`。
>    
>2. 在[Linux Wireless](https://wireless.wiki.kernel.org/en/users/drivers)网站中搜索这个驱动，可以看到这个驱动是支持monitor模式的，说明可以用来抓包：
> 
>![image-20221216232607399](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedbcb6bb98ddb3ab80e12e0a5f4c1244c6.png)
> 
>**网卡驱动未安装的情况**
> 
>1. 如果`ifconfig`和`iwconfig`看不到无线网卡，则可能是没有驱动
> 2. 根据是USB网卡还是PCIE网卡，可以先执行`lsusb`和`lspci`来看一下是否能识别到硬件
> 3. 如果能识别到硬件，再去google上搜索此款网卡的驱动，并在[Linux Wireless](https://wireless.wiki.kernel.org/en/users/drivers)网站上搜索此驱动是否支持Monitor模式。



# 2. 在Linux环境下进行抓包

​	本节参考的文章：[实战无线网络分析（篇一）无线监听 - aneasystone's blog](https://www.aneasystone.com/archives/2016/08/wireless-analysis-one-monitoring.html)

## 2.1. 安装工具

```bash
$ sudo apt install -y wireshark net-tools wireless-tools aircrack-ng
```

## 2.2. 无线网卡改为Monitor模式

> 注意，在Linux系统中，当一个无线网卡被改为Monitor模式后，就无法用来上网了。

​	查看无线网卡名称：

```bash
$ iwconfig
lo        no wireless extensions.

wlp0s20f3  IEEE 802.11  ESSID:off/any
          Mode:Managed  Access Point: Not-Associated   Tx-Power=-2147483648 dBm
          Retry short limit:7   RTS thr:off   Fragment thr:off
          Power Management:on

enx000ec6259ae4  no wireless extensions.
```

​	可以看到网卡名称是`wlp0s20f3`

​	将网卡改为Monitor模式：

```bash
$ sudo airmon-ng start wlp0s20f3        

PHY	Interface	Driver		Chipset

phy0	wlp0s20f3	iwlwifi		Intel Corporation Alder Lake-P PCH CNVi WiFi (rev 01)
		(mac80211 monitor mode vif enabled for [phy0]wlp0s20f3 on [phy0]wlp0s20f3mon)
		(mac80211 station mode vif disabled for [phy0]wlp0s20f3)
```

​	这时使用`iwconfig`查看，会出现一个新的网卡，**网卡名称也发生了改变**：

```bash
~$ iwconfig
lo        no wireless extensions.

enx000ec6259ae4  no wireless extensions.

wlp0s20f3mon  IEEE 802.11  Mode:Monitor  Frequency:2.457 GHz  Tx-Power=-2147483648 dBm
          Retry short limit:7   RTS thr:off   Fragment thr:off
```

可以看到名称变为`wlp0s20f3mon`，并且Mode变为了Monitor

> 注意：
>
> ​	有些教程会让你使用`sudo airmon-ng check kill`来自动杀死一些会影响Monitor网卡的守护进程，这些进程可能会导致网卡的信道被切换，也可能把网卡切回Managed模式。
>
> ​	但是这样直接杀死 Network Manager，会导致其他的网卡（比如有线网络）在拔掉后也无法自动连回。目前比较好的解决方法是：使用`nmtui`命令（NetworkManager的图形菜单），在Edit Connection中，把你要抓包的这张网卡记住的WiFi都改成“不自动连接”，这样你的网卡就不会被Network Manager改回Manged模式了。
>
> ![image-20221223152925995](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb45aad3fd993cc008a9bb32b1db7283e.png)

## 2.3. 在Linux中进行抓包

首先，以root权限打开Wireshark

```bash
sudo wireshark
```

然后，在"Capture --> Options..."窗口中，可以看到`wlp0s20f3mon`网卡：

![image-20221216165935706](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinede451900723a4608995d58e0916bc94a4.png)

> 注意到Monitor Mode栏并不能打勾，但是没关系，网卡本身已经是Monitor模式了

​	

## 2.4. 设置要抓包的信道

​	本节参考：[Linux for Network Engineers: How to do channel hopping during WiFi packet capturing | NetBeez](https://netbeez.net/blog/linux-channel-hopping-wifi-packet-capturing/)

### 2.4.1. 信道与带宽介绍

​	在Monitor模式下，只能扫描**固定的信道和带宽**。为了能够找到自己想要抓的设备到底在哪个信道进行通信，需要先进行**跳频（Channel Hopping）**。跳频时，不可避免的会扫不到一些包，但是等找到自己想要监听的信道之后，再切回固定信道的方式即可。

> 什么是WiFi的信道和带宽？
>
> ​	不同版本的WiFi协议，其无线电载波工作在不同的频率上，常见的如2.4 GHz和5 GHz。但这都不是指一个频率的值，而是指一个范围。因为固定频率的波是无法承载信息的，只有能切换频率的波才能承载信息。把这个频率范围分成很多份，就是**信道**，每个信道的频率宽度称为**带宽**。
>
> 例如：2.4 GHz （802.11 b/g/n）频段分配，共有14个信道
>
> ![image-20221223160719938](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined9539f245a20863780e7671303997e322.png)
>
> ​	如果每个信道的带宽是22MHz，那么2.4G最多只能同时使用三个信道（1，6和11）。14信道是特殊的，大多数国家不允许使用。
> ​	如果信道带宽是20MHz，那么最多可以同时使用四个信道（1，5，9，13）.
>
> ​	同理，5GHz频段，信道从5.000GHz（信道0）开始编码，每5MHz一个信道。但FCC开放的频率从5.150GHz开始，故实际使用的信道是从36开始的，频宽20MHz，可用信道每次+4，如36，40，44，48 ... 64 。
>
> ​	每个国家可用的信道，可参考：[无线局域网信道列表 - 维基百科，自由的百科全书 (wikipedia.org)](https://zh.wikipedia.org/wiki/无线局域网信道列表)

​	

​	查看自己无线网卡**支持**的信道：

```bash
# 以下命令将输出大量信息
$ iw list
Wiphy phy0
		... 
        Available Antennas: TX 0x3 RX 0x3   # 天线数量
        Configured Antennas: TX 0x3 RX 0x3
        Supported interface modes:          # 网卡支持的模式
                 * IBSS
                 * managed
                 * AP
                 * AP/VLAN
                 * monitor   # 支持 monitor
                 * P2P-client
                 * P2P-GO
                 * P2P-device
        Band 1:
                ...
                Frequencies: # 2.4 GHz 信道，disabled为不可用
                        * 2412 MHz [1] (22.0 dBm)
                        * 2417 MHz [2] (22.0 dBm)
                        * 2422 MHz [3] (22.0 dBm)
                        * 2427 MHz [4] (22.0 dBm)
                        * 2432 MHz [5] (22.0 dBm)
                        * 2437 MHz [6] (22.0 dBm)
                        * 2442 MHz [7] (22.0 dBm)
                        * 2447 MHz [8] (22.0 dBm)
                        * 2452 MHz [9] (22.0 dBm)
                        * 2457 MHz [10] (22.0 dBm)
                        * 2462 MHz [11] (22.0 dBm)
                        * 2467 MHz [12] (22.0 dBm)
                        * 2472 MHz [13] (22.0 dBm)
                        * 2484 MHz [14] (disabled)
        Band 2:
               ...
                Frequencies: # 5 GHz 信道，disabled为不可用
                        * 5180 MHz [36] (22.0 dBm) (no IR)
                        * 5200 MHz [40] (22.0 dBm) (no IR)
                        * 5220 MHz [44] (22.0 dBm) (no IR)
                        * 5240 MHz [48] (22.0 dBm) (no IR)
                        * 5260 MHz [52] (22.0 dBm) (no IR, radar detection)
                        * 5280 MHz [56] (22.0 dBm) (no IR, radar detection)
                        * 5300 MHz [60] (22.0 dBm) (no IR, radar detection)
                        * 5320 MHz [64] (22.0 dBm) (no IR, radar detection)
                        * 5340 MHz [68] (disabled)
						...
                        * 5480 MHz [96] (disabled)
                        * 5500 MHz [100] (22.0 dBm) (no IR, radar detection)
                        ...
                        * 5720 MHz [144] (22.0 dBm) (no IR, radar detection)
                        * 5745 MHz [149] (22.0 dBm) (no IR)
                        * 5765 MHz [153] (22.0 dBm) (no IR)
                        * 5785 MHz [157] (22.0 dBm) (no IR)
                        * 5805 MHz [161] (22.0 dBm) (no IR)
                        * 5825 MHz [165] (22.0 dBm) (no IR)
                        * 5845 MHz [169] (disabled)
                        ...
                        * 5905 MHz [181] (disabled)
        Band 4:
        		...
                Frequencies:  # 6 GHz 信道，中国不可用
                        * 5955 MHz [1] (disabled)
                        ...
                        ...
                        * 7115 MHz [233] (disabled)


```

​	

​	查看无线网卡**当前**的信道和带宽：

```bash
$ iw wlp0s20f3mon info
Interface wlp0s20f3mon
        ifindex 4
        wdev 0x3
        addr 00:93:37:90:08:3a
        type monitor
        wiphy 0
        channel 10 (2457 MHz), width: 20 MHz (no HT), center1: 2457 MHz
        txpower 0.00 dBm
```

​	可以看到，当前使用信道10，带宽20MHz，这与Wireshark中的信息是一致的，说明我们目前只能抓到信道10、带宽20MHz的包：

![image-20221217162609725](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined62bfd38ccd114609e65b7237d6fd1840.png)



### 2.4.2.  修改信道与带宽

​	由于Wireshark不提供切换信道的功能。我们只能自己手动切换信道和带宽，以下为设置信道和带宽的命令：

```bash
$ sudo iw dev wlp0s20f3mon set channel 149 80MHz
# 网卡名：wlp0s20f3mon
# 频道：149
# 带宽：可选的参数有
# 	NOHT  : 不使用802.11n，基本很少用
# 	HT20  : 802.11n/ac/ax 20MHz频宽
# 	HT40+ : 802.11n/ac/ax 双20MHz，控制信道比扩展信道频率高
# 	HT40- : 802.11n/ac/ax 双20MHz，控制信道比扩展信道频率低
#	5MHz  : 5MHz，基本很少用
# 	10MHz : 10MHz，基本很少用
#	80MHz : 802.11ac/ax
# 	160MHz: 802.11ac/ax
```

​	以上命令，是可以在抓包时**实时**执行的，无需重启Wireshark，可以看到信道立即发生了改变：

![image-20221217163934869](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined43c2d9475c66ac1082054008980ad3b7.png)



### 2.4.3. 实时跳频

​	**信道×带宽**的排列组合选项太多，我们不知道哪些组合是合法的，以及自己的网卡是否支持这些组合。我们需要2个脚本，来自动帮我们完成一些工作：

- 配置识别：自动识别出当前网卡哪些**信道**+**带宽**的排列组合是合法的，并记录下来
- 自动跳频：在前一个脚本的范围内，无限循环跳频扫描

第一个脚本，**配置识别**：

`test-channels.sh`

```bash
#!/bin/bash
# Make sure that the wifi adapter below is in Monitor mode.

# Wi-Fi Adapter
DEFAULT_INTERFACE="wlp0s20f3mon"

channels_24="1 2 3 4 5 6 7 8 9 10 11 12 13 14"
channels_50="36 40 44 48 52 56 60 64 100 104 108 112 116 120 124 128 132 136 140 144 149 153 157 161 165"

widths="HT20 HT40+ HT40- 80MHz 160MHz"

result_2g4=""
result_5g=""

current_user=$(whoami)
if [ "$current_user" != "root" ]
then
    echo "[Error] Please run this script with sudo!"
    exit 1
fi

for width in ${widths};do

    valid_channels=""
    for channel in ${channels_24}; do
        if iw dev ${DEFAULT_INTERFACE} set channel "${channel}" "${width}"; then
            if iw ${DEFAULT_INTERFACE} info | grep "channel ${channel}"; then
                valid_channels="${valid_channels}""${channel} "
            fi    
        fi
    done
    result_2g4="${result_2g4}""Width:${width}, Valid Channels:${valid_channels}\n"
done

for width in ${widths};do

    valid_channels=""
    for channel in ${channels_50}; do
        if iw dev ${DEFAULT_INTERFACE} set channel "${channel}" "${width}"; then
            if iw ${DEFAULT_INTERFACE} info | grep "channel ${channel}"; then
                valid_channels="${valid_channels}""${channel} "
            fi    
        fi
    done
    result_5g="${result_5g}""Width:${width}, Valid Channels:${valid_channels}\n"
done

echo "  "
echo "==================================================="
echo "2.4G:"
echo -e "${result_2g4}"
echo " "
echo "5G:"
echo -e "${result_5g}"
```

给这个脚本添加执行权限，修改脚本中的网卡名，并用sudo执行：

```bash
$ chmod +x ./test-channels.sh
$ sudo ./test-channels.sh
...
===================================================
2.4G:
Width:HT20, Valid Channels:1 2 3 4 5 6 7 8 9 10 11 12 13 
Width:HT40+, Valid Channels:1 2 3 4 5 6 7 8 9 
Width:HT40-, Valid Channels:5 6 7 8 9 10 11 12 13 
Width:80MHz, Valid Channels:
Width:160MHz, Valid Channels:

 
5G:
Width:HT20, Valid Channels:36 40 44 48 52 56 60 64 100 104 108 112 116 120 124 128 132 136 140 144 149 153 157 161 165 
Width:HT40+, Valid Channels:36 44 52 60 100 108 116 124 132 140 149 157 
Width:HT40-, Valid Channels:40 48 56 64 104 112 120 128 136 144 153 161 
Width:80MHz, Valid Channels:36 40 44 48 52 56 60 64 100 104 108 112 116 120 124 128 132 136 140 144 149 153 157 161 
Width:160MHz, Valid Channels:36 40 44 48 52 56 60 64 100 104 108 112 116 120 124 128 
```

可以看出此脚本列举出了5G、2.4G频段下，各个带宽下支持的扫描信道。



第二个脚本，**自动跳频**：

自动跳频的脚本内记录了每种带宽下，网卡可以支持的信道。这些数据来源是前一个脚本的输出结果。

```bash
#!/bin/bash

DEFAULT_INTERFACE="wlp0s20f3mon"

channels_2G4_HT20="1 2 3 4 5 6 7 8 9 10 11 12 13"
channels_2G4_HT40p="1 2 3 4 5 6 7 8 9"
channels_2G4_HT40m="5 6 7 8 9 10 11 12 13"

channels_5G_HT20="36 40 44 48 52 56 60 64 100 104 108 112 116 120 124 128 132 136 140 144 149 153 157 161 165"
channels_5G_HT40p="36 44 52 60 100 108 116 124 132 140 149 157"
channels_5G_HT40m="40 48 56 64 104 112 120 128 136 144 153 161"
channels_5G_80MHz="36 40 44 48 52 56 60 64 100 104 108 112 116 120 124 128 132 136 140 144 149 153 157 161"
channels_5G_160MHz="36 40 44 48 52 56 60 64 100 104 108 112 116 120 124 128"

current_user=$(whoami)
if [ "$current_user" != "root" ]
then
    echo "[Error] Please run this script with sudo!"
    exit 1
fi

if [ -n $1 ] 
then
    case $1 in
    "HT20")
        channels="$channels_2G4_HT20"" ""$channels_5G_HT20"
        ;;
    "HT40+")
        channels="$channels_2G4_HT40p"" ""$channels_5G_HT40p"
        ;;
    "HT40-")
        channels="$channels_2G4_HT40m"" ""$channels_5G_HT40m"
        ;;
    "80MHz")
        channels="$channels_5G_80MHz"
        ;;
    "160MHz")
        channels="$channels_5G_160MHz"
        ;;
    *)
        echo "Invalid Bandwidth: $1"
        exit 1
        ;;
    esac
else
    echo "no bandwidth set! i.e. 'sudo channel-hopping.sh HT20'"
fi

width=${1}

for channel in ${channels}; do
    echo "Setting channel ${channel}, ${width}"
    iw dev ${DEFAULT_INTERFACE} set channel "${channel}" "${width}"
    sleep 0.5
done
```

给这个脚本添加执行权限，修改脚本中的网卡名，并用sudo执行：

```bash
$ chmod +x channel-hopping.sh
$ sudo ./channel-hopping.sh HT20
```

执行脚本时，指定要使用的带宽，脚本将会每 0.5s 切换一次信道。

脚本只会循环执行一次，之后你可以手动指定信道和带宽。



### 	2.4.4. 过滤器

跳频时，可以设置过滤器来抓自己设备的包。

**显示过滤器**语法：

**Source Address:** `wlan.sa==XX:XX:XX:XX:XX:XX`
**Destination Address:** `wlan.da==XX:XX:XX:XX:XX:XX`
**Receiver Address:**  `wlan.ra==XX:XX:XX:XX:XX:XX`
**Transmitter Address:**  `wlan.ta==XX:XX:XX:XX:XX:XX`

例如，可以在手机上查看MAC地址，然后输入到wireshark中

![image-20221223155547191](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined5233c6123366a1f3ccb916c48909e167.png)

可以看到，成功抓到了手机的WiFi6包（802.11ax）

## 2.5. 关闭monitor模式的方法

```bash
$ sudo airmon-ng stop wlp0s20f3mon
```

注意网卡名是变为monitor之后的网卡名。



# 3. 在Windows上远程抓包

## 3.1. 确保Ubuntu上安装了ssh服务

```bash
sudo apt install openssh-server
```

## 3.2. 让用户执行sudo命令不用输入密码

​	抓包需要root权限，并且我们用wireshark远程抓包的时候无法输入sudo密码。网上有两种不太推荐的方法可以解决这个问题：

- 直接打开root的ssh登陆权限，后续Windows电脑的Wireshark直接通过root登录
- 让自己的用户执行sudo时不需要密码

​	但是以上两种方法是很不安全的，下面介绍一种通过改sudo配置的方式，让你的linux用户只在执行一些指定的命令的时候不需要输入sudo密码，而其他时候还是要密码。

```bash
# 用visudo编辑器，在/etc/sudoers.d/下创建个人的sudo配置
sudo visudo 
```

​	填入以下内容，然后保存：

```bash
jayant ALL=(root)NOPASSWD:/usr/bin/tcpdump
```

> 释义：
>
> 	- jayant：用户名或组名，如果是组名，前面加`%`
> 	- ALL：主机名，多服务器才有用，这里设置ALL即可
> 	- (root)：完整写法是(用户名:组名)，这里只写了用户名。这里指jayant可以作为root运行后面的指令。如果只有组名，写`(:组名)`
> 	- NOPASSWD:/usr/bin/tcpdump ：指定的命令，前面`NOPASSWD:`指不需要密码。这里需要填命令的绝对地址，如果你不知道绝对地址，可以输入`which tcpdump `查看。
>
> 其他说明：
>
> ​	在 `/etc/sudoers`中，有`@include`语句包含了`/etc/sudoers.d/`下的所有文件（文件名不含`.`和`~`），所以我们不需要修改`/etc/sudoers`，而是在`/etc/sudoers.d/`目录中增加自己的配置文件；
>
> ​	使用visudo文本编辑器进行编辑，可以在保存时自动提示是否有语法错误。	

测试一下`sudo tcpdump`是不是已经不需要输入密码了。



## 3.3. 按照第二节的做法，把网卡设为monitor模式

​	请参考第2节的内容

```bash
sudo airmon-ng check kill
sudo airmon-ng start <网卡名>
```

## 3.4. 在Windows上安装sshdump

​	安装Wireshark时勾选即可

![image-20221216194013150](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined60cee0d7d8f786c383c57f5bdab3003a.png)

## 3.5. 在Windows上设置Wireshark

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined3f607d351bdd92c0eea8cac7209571b6.png" alt="image-20221216194117135" style="zoom: 50%;" />

设置远程主机地址和ssh端口：

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined47a330e31feab485bfd2d258666e987e.png" alt="image-20221216194137684" style="zoom: 50%;" />

我这里使用密钥登录，也可以使用密码：

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined45ca389ca70b5981018bc67449654501.png" alt="image-20221216194206105" style="zoom:50%;" />

设置网卡名：

![image-20221216194235505](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined77039a13629e1af6594c1d1eaf0c5647.png)

## 3.6. 开始抓包

![image-20221216194816124](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined6a1b37e83b150b671f2d363f080da319.png)

​	

