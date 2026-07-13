---
title: 利用Wireshark和tcpdump对整个局域网进行实时抓包
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2022-12-14 21:14:38
cover: null
tags:
- Wireshark
- tcpdump
- OpenWrt
categories: WiFi
cnblogs:
  postId: '21180788'
  url: https://www.cnblogs.com/jayant97/articles/21180788
  lastPublishedAt: '2026-07-06T18:39:19+08:00'
  sourceHash: sha256:1dc5d1ae369c07c31db089209ab795298ca9370ed156da95ac70e2da8ca648c6
  status: synced
  postType: Article
---

# 1. 前言

​	有时我们需要对局域网中两个设备之间的通讯进行抓包调试，一种比较方便的方式就是在路由器上通过`tcpdump`抓包，然后传回电脑上，利用Wireshark查看抓包内容。

​	本文将以一个OpenWrt路由器为例，展示抓包过程。

​	参考文章：[使用 tcpdump 和 Wireshark 进行远程实时抓包分析 - This Cute World](https://thiscute.world/posts/tcpdump-and-wireshark/#二tcpdump--ssh--wireshark-远程实时抓包)

![image-20221214212711479](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined40185740898e3ed790b32a4498850cf4.png)

# 2. 软件安装

## 2.1. PC上安装Wireshark

​	官网下载安装包然后安装即可，安装时，一定要勾选：

![image description](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined60cee0d7d8f786c383c57f5bdab3003a.png)

## 2.2. 路由器上需要有`tcpdump`

​	我是在路由器固件编译时就编译了`tcpdump`和`libpcap`。选择为`<*>`号是随固件一起编译，选择为`<M>`是作为包进行编译。`-*-`表示强制随固件一起编译，因为有其他包依赖它，所以它必须选中。

​	Network ---> tcpdump

![image-20221214214847255](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb598ffc9e9b9037f74567cf4e82d8e2e.png)

​	Libraries ---> libpcap：

![image-20221214215049186](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedfa009f46eab82e23a41b92e1dadbbff2.png)



​	如果你不是自己编译的固件，也可以从网上下载别人编译好的ipk传到OpenWrt上安装即可：

![image-20221214214611043](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined9350b35360b7a9c971438765dcecade2.png)

在路由器上进行测试：

```bash
tcpdump --help
```



![image-20221214215320752](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinede0583ec1d8c472c2c60a448518a3103c.png)



# 3. 利用Wireshark调用路由器上的`tcpdump`进行抓包

（1）打开Wireshark，选择**捕获——选项**：

![image-20221214215528345](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined4c8e09fcbe7471708a937e3838bba860.png)



（2）选择**SSH remote capture**，点击开始

![image-20221214215620451](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedf9aeeedbd37eb3a23a9e982306d4e4fc.png)



（3）输入路由器的ip地址和ssh端口号（默认22）

![image-20221214215737318](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined18f226007d0993e24234c7030212bd53.png)



（4）输入路由器用户名和密码/密钥

![image-20221214215921550](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined2a82a7a456109575b655755bbe9792b1.png)

> 我这里用的是密钥而非密码，请参考：[最简洁清爽的ssh使用方案 | 一苇万顷 (jayant-tang.github.io)](https://jayant-tang.github.io/2022/12/693c6a957393/)。
>
> 你也可以用密码



（5）tcpdump设置

![image-20221214220409559](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined936c4b022abaa3d450cb473098c8bf22.png)

参数设置：

- Remote Interface：路由器上要抓包的接口，可以在路由器管理网页上查看，也可以用`ifconfig`查看，这里是`br-lan`
  <img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedaafafeff4289d97ebede77cdca043f69.png" alt="image-20221214220526046" style="zoom:50%;" />

- Remote capture command selection：路由器上选择的抓包工具，这里是`tcpdump`

- Remote capture filter：远程抓包的规则，可以把本机的IP地址填进去过滤，防止Wireshark抓自己和路由器之间的ssh包。比如`not (host 192.168.2.2 and port 22)`。这里可以用`not`，`or`和`and`逻辑，可以过滤IPv4/IPv6地址和端口号。

  > 这个地方是远程过滤器，是抓包时就过滤，后面Wireshark里面还可以再次设置本地过滤器。



（6）开始抓包

最后点击开始，即可在Wireshark中看到路由器br-lan的包了。

![image-20221214221347037](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined1271c5e0a4cf8d5ca485772b11fd2fe7.png)

​	与此同时，我们可以去路由器上看看Wireshark是怎么用`tcpdump`抓的：

```bash
$ root@OpenWrt:~# ps | grep tcpdump
 2131 root      5676 S    tcpdump -U -i br-lan -w - not (host 192.168.2.2 and port 22)
 8318 root      1248 S    grep tcpdump
```

​	如上，可以看到Wireshark调用的`tcpdump`命令以及参数。
