---
title: 离线版nRF Connect for Desktop安装方法
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2023-11-09 14:50:00
cover: null
tags:
- Nordic
- NCS
- Toolchain
categories: Nordic
cnblogs:
  postId: '17821601'
  url: https://www.cnblogs.com/jayant97/articles/17821601.html
  lastPublishedAt: '2026-07-06T18:29:40+08:00'
  sourceHash: sha256:96e126bb2db63ad340ad7e3cb7e0a97ed54cc886a58c3624c1aa5cba523cb8bd
  status: imported
  postType: Article
---

首先确保两台电脑都安装了 nRF Connect for Desktop。

## 先在一台能联网的电脑上安装自己想要的 App

先在有网络的电脑上，用 nRF Connect for Desktop 安装需要的 App。

![image](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedee2d916120f9d325613363d97ceb5aba.png)

## 然后把 App 拷贝到没有网的电脑上

![image](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinede942b96bbcb8d362f51dccdcf55e5839.png)

从：

```text
%USERPROFILE%\.nrfconnect-apps\node_modules\
```

拷贝到另一台不能联网的电脑的：

```text
%USERPROFILE%\.nrfconnect-apps\local\
```

## 查看 App

可以看到，没有网络的电脑上的 App 均为 `local` 版本。

![image](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined485e52099a3244017ed8ce771c4b086d.png)

注意：

- `local` 版本无法更新
- 某些本身需要联网的 App，即使安装了 `local` 版本，也仍然需要网络才能工作
