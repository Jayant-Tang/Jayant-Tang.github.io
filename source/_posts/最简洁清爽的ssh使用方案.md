---
title: ssh密钥登陆
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2022-12-14 19:27:13
tags:
- Linux
- ssh
categories:
- Linux
- ssh
cnblogs:
  postId: '21180793'
  url: https://www.cnblogs.com/jayant97/articles/21180793
  lastPublishedAt: '2026-07-13T01:06:37+08:00'
  sourceHash: sha256:8caeccc91e630e78a7f3d9aaa751402ebd1e079845e0e5c385c903db47be985d
  status: synced
  postType: Article
---

# 1. 前言

​	今天把最方便的ssh使用方式分享给大家。先放一个**演示效果**如下：

（1）在Linux shell终端，或者Windows Git Bash中，直接输入`ssh <主机名>`，就可`ssh`连接到指定主机，无需输入密码.

![image-20221214193456382](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedc1d385c042e2d0733c1f2bc9b37dc395.png)

<center>上图为Windows11 Terminal中打开的Git Bash</center>


（2）`scp`远程拷贝，也只需主机名，无需用户名、密码：

​	![image-20221214193918641](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined4a667eb43975102a0959af2d6b39753e.png)

> 注：我的远程主机是OpenWrt，没安装sftp，所以这里`scp`要加`-O`参数。一般支持sftp的可以不加`-O`参数。

（3）VS Code Remote，直接选择远程主机，无需密码

![image-20221214194243898](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined340138ddb34d9e6f6993577e2a30ca43.png)

![image-20221214194211714](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined1d98998c6900099204a2a4a09bf586a5.png)

> 注：VS Code Remote要求对方主机要有`glibc`和`libstdc++`，实际上OpenWrt的C运行库是musl，是不能用VS Code Remote连的，我这里只是展示一下。
>
> ​	大部分开发板的Linux系统都是可以使用VS Code Remote的

# 2. 配置

## 2.1. 创建密钥对

​	使用密钥对而非账户密码来进行`ssh`连接。这里先生成密钥对

```bash
ssh-keygen -t ed25519 -C "xxxx@xxx.com" -f ~/.ssh/my_ed25519
# 一路回车即可，不要输入任何内容
```

​	参数说明：

- `-t`：加密算法，目前推荐ed25519，rsa已经不够安全
- `-C`：备注信息，写一些明文备注，可以写任何东西，让你记得这是个啥。如果是GitHub的密钥，则需要输入本地git邮箱。
- `-f`：存放私钥的文件，会新建一个文件，建议放在`~/.ssh/`下

​	创建完毕后，会发现`.ssh`目录下有公钥和私钥文件，其中带`.pub`后缀的是公钥：

![image-20221214195611976](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedcc484a88dafe91c37bc7990bfc76f633.png)

## 2.2. 安装公钥到远程主机

​	把公钥安装到远程主机，输入以下命令，最后填入你自己的远程主机用户名和IP地址：

```bash
ssh-copy-id -i ~/.ssh/my_ed25519.pub root@192.168.2.1
```

参数说明:

- `-i`：公钥文件

第一次安装会要求你输入密码，输入密码后即为安装成功

## 2.3. 配置ssh

​	修改`~/.ssh/config`，如果没有就创建一个新的，内容示例如下：

```bash
Host aliyun
    HostName xxx.xxx.xxx.xxx
    User root
    Port 22
    IdentityFile ~/.ssh/id_ed25519_aliyun
Host google
    HostName xxx.xxx.xxx.xxx
    User ubuntu
    Port 22
    IdentityFile ~/.ssh/ds.txt
Host r5s
    HostName 192.168.2.1
    User root
    Port 22
    IdentityFile ~/.ssh/id_ed25519
```

- `Host`：命名，可以随便取名英文字母+数字+下划线
- `HostName`：主机名，可填IP地址或域名
- `User`：用户名
- `Port`：端口号，如果不配置，默认是22
- `IdentityFile`：私钥文件，必须是与前一步安装的公钥成对的私钥文件

## 2.4. 测试

直接使用`config`中命名的别名就可以进行ssh连接，无需输入密码，例如：

![image-20221214193456382](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedc1d385c042e2d0733c1f2bc9b37dc395.png)



# 3. 其他相关话题

## 3.1. VS Code Remote

​	直接在插件商店搜索remote，安装remote开发合集即可，会自动安装remote ssh等：

![image-20221214200636992](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedc3029c930ea63673d865f6cd3760d9ed.png)



​	然后点击左下角即可开始选择远程主机：

![image-20221214200752517](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined17f0a9dfb6c791209b46bf49fdb7680e.png)

![image-20221214194211714](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined1d98998c6900099204a2a4a09bf586a5.png)



​	第一次连接，需要选择是Linux/Windows/Mac OS，然后VS Code会自动在对方主机上编译安装服务端，需要对方主机上有C++环境。需要等待一段时间：
![image-20221214201022079](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined0ae01f238f4daa0d7addbcba47f2dd11.png)

​	安装完毕后，在VS Code中打开文件夹，就像在本地一样操作，左侧文件栏是可以拖放文件的：

![image-20221214210243472](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined588464c7a08a2392b7af5559c72a6b7f.png)

## 3.2. 固定IP地址

​	现在家用网络很少用静态IP了，而是路由器通过DHCP服务自动给设备分配IP地址。但是我们希望：

- 自己在家调试时，开发板不要每次上电IP地址就变化
- 不要在开发板上配置静态IP，不然把板子带到其他地方去联网就又要重新配置动态获取IP了

​	解决方法是，DHCP客户端（板子）仍然申请IP，但是DHCP服务器（路由器）只会分配固定的IP地址给它。

> DHCP静态分配与“静态IP”不是一个概念，但可以达到我们希望IP地址不变的效果

​	路由器管理页面种类很多，但是原理都是相通的，这里以OpenWrt为例：

（1）选择 “网络”——“DHCP/DNS”

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined95d194e719ac1f1864df5723867edc41.png" alt="image-20221214202240725" style="zoom:50%;" />

（2）可以看到已分配的IP地址，找到你的开发板，记住MAC地址：

![image-20221214202411249](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined8977e8073ab7335efe07b701e9a58746.png)

（3）在下方，“静态地址分配”中，选择“添加”，然后给MAC地址绑定一个固定的IP地址即可，主机名可以随便取个名，也可以不填：

![image-20221214202548591](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedfb563e271fc46498321ebaa6c6f2637c.png)

（4）页面中选择“保存&应用”即可：

![image-20221214202711815](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedd6580c841a9ca229c7d3063af2862cda.png)

> 注意：
>
> ​	DHCP静态绑定，并不是说这个IP地址就不会被其它设备动态获取到了。只要这个IP在动态IP池子里，就有可能在被绑定的设备不在线时，动态分配给其他设备。
>
> ​	为了避免这种情况，我们做DHCP静态分配时，最好把静态分配的地址放在动态分配地址池之外。
>
> ​	以我的OpenWrt为例：
>
> ​	在“网络”——“接口”——“LAN接口配置修改”中，可以看到DHCP服务器的设置：
>
> ![image-20221214205402842](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined6d4aa0fe84cfc5fbd24174981f84bcf4.png)
>
> ​	可以看到基址是100，范围是150.由于我的LAN网段是 192.168.2.0/24，所以动态地址池的分配范围就是192.168.2.100 ~ 192.168.2.250. 
>
> ​	所以前面做DHCP静态绑定时，IP地址设在这个范围之外即可。
