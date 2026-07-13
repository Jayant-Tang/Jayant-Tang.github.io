---
title: 在Windows上使用Wireshark和Npcap进行WiFi嗅探
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2022-12-14 22:24:34
tags:
- Wireshark
- WiFi
- Npcap
categories: WiFi
cnblogs:
  postId: '21180789'
  url: https://www.cnblogs.com/jayant97/articles/21180789
  lastPublishedAt: '2026-07-06T18:39:20+08:00'
  sourceHash: sha256:1ec0edaf93bad4cf1d77258dabf21ee32620432f84b5190161e8b0c0227d6eff
  status: synced
  postType: Article
---

# 1. 前言

​	我们知道，无线网卡有四种工作模式：

- Managed：电脑网卡最常用的模式，用于连接到无线AP进行上网，被AP管理通信过程。
- Master：AP模式，提供无线接入和路由的功能。Master能管理与Managed模式的网卡的通信过程。
- Ad-hoc：点对点通讯模式，通信双方地位对等，共同承担AP的任务
- Monitor：监听模式

​	本文讲解如何在**Windows**电脑上，把无线网卡变为**Monitor**模式，对空中的wifi进行抓包，并用**Wireshark**进行包的分析。

​	本文参考了：[在Windows电脑上通过wireshark直接无线抓包的方式 - 知了社区 (h3c.com)](https://zhiliao.h3c.com/theme/details/183006)

# 2. 安装Npcap

在Windows上安装Wireshark时，会问你是否要同时安装Npcap，这里要勾选：

​	![image-20221214225008728](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined85c2c034b060036ce29c2885205f06ec.png)



安装Npcap时，**不勾选**管理员模式，**勾选**802.11流量抓包支持：

![image-20221214225059444](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined60e82559add6cf53e9976db6e4812141.png)

> 注！
>
> ​	经过亲自测试，发现Npcap 1.71/1.70版本在Windows 11 上均存在bug，明明勾选了`Support raw 802.11 traffic`，但是实际使用时却提示没有勾选。
>
> ​	后来安装Npcap 1.60版本才成功，老版本下载地址：[Npcap release archive](https://npcap.com/dist/)



安装完毕，重启电脑后，任意打开一个终端，输入`WlanHelper --help`，应该有输出：

![image-20221214225257642](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined81825967153b31ba95630764d9c135d4.png)

> WlanHelper.exe的位置在`C:\Windows\System32\Npcap`



# 3. WlanHelper的使用

## 3.1. 查看无线网卡的名称

查看自己电脑上无线网卡的名称：

```powershell
ipconfig
```

如下图，名称是WLAN：

![image-20221214225720426](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined6a7b7772e433de0bfed7ff9cd946c341.png)



​	也可以在新版Windows设置中查看：

![image-20221214225852951](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined1b2582876d87f98b242c3d99287a3ad5.png)



​	也可以在旧版Windows网络适配器中查看：

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedf8b12497e349e8aa701e36a14ff54f67.png" alt="image-20221214225813048" style="zoom:50%;" />

![image-20221214225931713](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined6a96bfedc63aba1708b4bf22d2615fd3.png)

​	 可以看到，我这张网卡的名称是WLAN，有的网卡名称可能叫Wi-Fi，这与电脑品牌有关。

## 3.2. 把网卡切换为monitor模式

​	使用一个支持抓包的USB网卡，插到电脑上：

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedd4cf13d1cf01035dbbe8fe4adac1e314.png" alt="image-20221215075234594" style="zoom:50%;" />

​	可以看到有两张无线网卡：

![image-20221215075413896](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedae4e523e24bf81d6efb8340f5c8500a8.png)

​	查看网卡当前工作模式：

```bash
$ WlanHelper "Wi-Fi 2" mode
managed
```

​	查看网卡支持的所有模式：

```bash
$ WlanHelper.exe "Wi-Fi 2" modes
master, managed, monitor
```

​	修改网卡的模式：

```bash
$ WlanHelper.exe "Wi-Fi 2" mode monitor
Success
```



> 也可以直接`WlanHelper -i`，进入交互模式，然后根据其提示输入数字，来进行配置

# 4. 使用Wireshark进行抓包

​	选择“捕获”——“选项”：

![image-20221215075810915](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedf85c43e31084002ae34ab072a0bc3150.png)

​	发现监控模式已经可以打勾，可以进行抓包：

![image-20221215075830448](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedf2513ef71f3d83b18b615e15566a1007.png)
