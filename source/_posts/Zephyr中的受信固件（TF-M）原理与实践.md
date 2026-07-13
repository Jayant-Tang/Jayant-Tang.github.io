---
title: Zephyr中的可信固件（TF-M）原理与实践
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2023-07-11 15:24:43
cover:
tags:
  - Zephyr
  - TF-M
  - Security
categories: Zephyr
published: false
cnblogs:
  published: false
---

# 1. 平台安全架构（PSA）

- 它是一个标准框架
- 它把安全开发分成了四步：
  - 分析：分析哪些资产需要保护，有哪些威胁模型
  - 架构：
  - **实现**：
  - 认证（验证？）：
- 它的安全性来自于隔离：SPE与NSPE
- 它的安全等级有三级

## 10个安全目标

1. 设备具有唯一ID
2. 设备支持安全生命周期（开发、部署、返厂、终止）。对应带来的是**安全状态**（是否能存储敏感信息。与软件版本、运行时的测量结果、硬件配置、**debug端口状态**）
3. 设备是可以被证明安全的。这需要建立对设备的信任度机制。这需要唯一ID和安全状态（1和2），这二者必须是设备管理制度的一部分
4. 设备要确保，只有授权的软件可以被执行（安全启动，安全引导）
5. 设备支持安全升级
6. 设备拒绝非授权的软件版本回滚，但可以接受授权的回滚
7. 设备支持隔离（确保安全服务的完整性）
8. 设备支持在隔离带上的交互
9. 设备能和敏感数据进行唯一绑定（依赖密钥和加密）
10. 设备至少具有一套受信服务，来支持其他9项目标。（服务包括：硬件配置，从而支持安全生命周期；隔离；加密服务）。受信服务的集合需要尽可能的小，从而确保安全，方便debug

## 设备模型

最重要的三个组成部分：

- Platform RoT：整个系统的信任锚，有了它才能做安全启动、安全配置等。还包含了一些根参数
- 安全环境：用于运行**通用的**安全服务
- 安全环境：用于运行Application RoT服务。（某些系统可能不需要ARoT）

共识：

- **分区（partitions）**：是具有边界的一些处理过程。通常是软件，也可以是包含了硬件操作的软件。分区之间的交互必须通过给定的API实现。分区需要被分区管理器管理。分区也可以嵌套在其他分区中
- partition manager是用于给分区分配资源的（信道、内存、中断、外设、CPU处理时间）。partition manager本身也是一个partition，具有边界和API。它是用于动态分配的，因此如果一个系统只有一个分区（不需要动态分配），则可以没有partition manager。
- (PE)processing environment：是partition的环境。有SPE和NSPE。

PSModel最基本的要素：

- 不可变的Platform RoT：通常与硬件有关。
- 可升级的Platform RoT：
- Platform RoT服务：安全存储、加密

## PSA Certified APIs

API可以与TFM一起运行，也可以不与TFM一起运行。


