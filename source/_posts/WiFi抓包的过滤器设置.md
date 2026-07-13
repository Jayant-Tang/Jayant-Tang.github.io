---
title: WiFi抓包的过滤器设置
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2022-12-16 22:44:24
cover:
tags:
  - Wireshark
  - WiFi
  - Filter
categories: WiFi
published: false
cnblogs:
  published: false
---

# 1. 前言

​	使用wireshark进行抓包时，可以设置**捕获过滤器**和**显示过滤器**：

- 捕获过滤器：在抓包时就进行过滤的规则
- 显示过滤器：对抓包文件进行显示时过滤的规则

两种过滤的语法**完全不同**。本文介绍在WiFi抓包（802.11流量分析）时的两种过滤器设置。

# 2. 捕获过滤器

## 2.1. 捕获过滤器设置位置

（1）对于**本机**的抓包，可以在启动时设置：

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined2d0965239758b62e48d989d6b18b92f2.png" alt="image-20221216224959587" style="zoom:50%;" />

也可以在“捕获——选项”中设置：

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedbcea68af54ae5d9781fed9e56ed9027b.png" alt="image-20221216225049231" style="zoom:50%;" />

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinede8a47eb911a2dfba5df30c4b40cb5c45.png" alt="image-20221216225112334" style="zoom:50%;" />



（2）对于ssh远程抓包，需要在远程抓包中设置

<img src="https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined0d1e05828e84f1802c728c1f566f9feb.png" alt="image-20221216225209293" style="zoom:50%;" />

![image-20221216225240958](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined5e13ff9d545a835c4953b04725c9a2df.png)

## 2.2. 捕获过滤器wifi抓包语法

待补充
