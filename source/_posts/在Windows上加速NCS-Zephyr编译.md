---
title: 在Windows上加速NCS/Zephyr编译
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
cnblogs:
  postType: Article
  postId: '22779257'
  url: https://www.cnblogs.com/jayant97/articles/22779257
date: 2026-08-31 16:02:36
cover: null
tags:
- Windows
- NCS
- Zephyr
categories:
- Nordic
---

如果你使用 Windows 开发 NCS（nRF Connect SDK）或 Zephyr，应该遇到过这种情况：第一次编译需要等待很久，增量编译也会频繁读写大量小文件。

只要切换到 Linux，无论是服务器、虚拟机还是WSL，都能得到几倍的速度提升。

但不是所有开发者都能切换到 Linux。这篇文章面向**不愿意切换到 Linux/macOS，且不能使用 WSL** 的 Windows 用户，介绍两个可能改善编译 I/O 性能的方法：

1. 为 NCS/Zephyr 相关目录添加 Windows Defender 排除项；
2. 使用开发人员驱动器（Dev Drive）存放工作区或编译目录。

> 此方法仅能提升 5% ~ 10% 速度。
>
> 而切换为 Linux 在同等配置条件下几乎能变为 5 倍速度。

# 1. Windows Defender 排除项

## 1.1 为什么排除 Defender 扫描？

NCS/Zephyr 编译过程中会生成、读取和删除大量文件。Windows Defender 的实时防护可能会反复检查这些中间文件，尤其是在以下目录发生大量 I/O 时：

- NCS 工作区，例如 `C:\ncs\`；
- 工程源码目录，例如`C:\work\my_project`
- 编译输出目录，例如`C:\work\my_project\build`。

为编译目录添加排除项，可以减少实时防护对这些文件的重复扫描。

> 排除项会降低对应目录的防护强度。不要排除整个磁盘、下载目录、桌面、临时目录或包含未知文件的目录。只排除可信的 NCS/Zephyr 工作区，并在编译任务完成后考虑删除排除项。

## 1.2 通过 Windows 安全中心添加

添加排除项通常需要管理员权限。

1. 打开“开始”菜单，搜索并打开“Windows 安全中心”。
   ![image-20260831160736319](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined43de91367ef53e0de518f5aca65abc59.png)
2. 进入“病毒和威胁防护”。
3. 在“病毒和威胁防护设置”下点击“管理设置”。
   ![image-20260831160801103](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined4de4153985e510b06aa71b3500812d0b.png)
4. 找到“排除项”，点击“添加或删除排除项”。
   ![image-20260831160836097](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined806954ffa1c113224b23d4f19dcfd888.png)
5. 点击“添加排除项” → “文件夹”。
   ![image-20260831160902357](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined4105d87f226f666bb23352a56bfea9d3.png)
6. 选择需要排除的、可信的 NCS/Zephyr 工作目录。
7. 如果需要排除多个目录，逐个添加，不要直接选择磁盘根目录。

> 如果你是企业 IT 控制的电脑，会显示 “此设置由管理员进行管理”，或者“管理员已禁用更改排除项”。
>
> 如果电脑由公司 IT 通过 Group Policy、Intune 或 Defender for Endpoint 管理，相关选项可能不可修改。这种情况下应让 IT 评估并统一配置，不要尝试绕过管理策略。

## 1.3 通过 PowerShell 快速查看当前排除项

使用“管理员身份”打开 PowerShell，执行：

```powershell
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
```



# 2. 使用开发人员驱动器（Dev Drive）

## 2.1 ReFS 简介

ReFS（Resilient File System）是 Windows 提供的一种文件系统，重点关注数据完整性、可靠性和大规模存储场景。它和 Windows 默认使用的 NTFS 是两种不同的文件系统。

对于 NCS/Zephyr 来说，编译过程中会频繁创建、读取和删除大量中间文件，因此 ReFS 可能影响文件 I/O 性能。

ReFS 可以作为普通数据卷使用，但普通 ReFS 卷并不会自动获得 Dev Drive 的开发优化。也不会因为使用了 ReFS 就自动改变 Microsoft Defender 的扫描方式。Dev Drive 正是以 ReFS 为基础，针对开发工作负载进一步提供的专用卷类型。

## 2.2 Dev Drive 是什么？

Dev Drive 是 Windows 面向开发场景提供的专用存储卷，它以 ReFS 为基础，并针对源代码、依赖包和编译输出等大量文件 I/O 场景进行了优化。

Dev Drive 和普通 ReFS 卷不是一回事：

- 通过“磁盘管理”直接格式化成 ReFS，只能得到普通 ReFS 卷；
- 通过“开发人员驱动器”创建的卷，才会被系统登记为 Dev Drive；
- 可信的 Dev Drive 可以让 Microsoft Defender 使用 Performance Mode；
- Performance Mode 不会完全关闭 Defender，而是将部分扫描操作延后到后台执行。

需要注意：

- Dev Drive 主要支持 Windows 11，具体功能取决于 Windows 版本、版本类型和系统策略；
- Dev Drive 不能作为 Windows 系统启动盘；
- Dev Drive 不一定比 NTFS 快，最终结果必须以实际测试为准；
- 创建或格式化卷可能造成数据丢失，操作前必须备份。

## 2.3 通过 Windows 设置创建 Dev Drive

做这一步之前，确保你有一块未分配的 SSD 磁盘空间。确保你懂得磁盘分区是在做什么，否则不要做这一步。

推荐使用 Windows 11 的图形界面创建。

1. 备份重要数据。
2. 打开“设置” → “系统” → “存储”。
   ![image-20260831162225065](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined2330b61d7de1e851c5177acc392cdb4f.png)
3. 进入“高级存储设置” → “磁盘和卷”。
   ![image-20260831162245212](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedfb815394b0482647b29b0debb94eed44.png)
4. 点击“创建 Dev Drive”。
   ![image-20260831162259705](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedcab72706866e22cb20db743b1326f3b3.png)
5. 根据向导选择未分配空间，或创建一个用于开发的 VHD/VHDX。
6. 设置卷大小、盘符和卷标，例如 `E:` 。
7. 完成向导，系统会使用 ReFS 创建并登记这个 Dev Drive。
8. 将 NCS/Zephyr 工作区、依赖缓存或编译输出目录放到该卷中。

例如：

```text
E:\ncs
E:\work
```

# 3. 调整 NCS 默认安装路径

我们知道，NCS 默认安装路径的目录结构是这样：

```text
<install-dir>
├── downloads/
├── tmp/
├── toolchains/
│   ├── b2ecd2435d/
│   ├── fbf7391cab/
│   └── toolchains.json
├── v3.1.1/
└── v3.4.0/
```

Windows 上的默认安装路径是 `C:\ncs\`。

改完开发人员驱动器、Windows Defender 默认排除路径之后，可能你想要修改默认的NCS安装路径。

> Windows 注意事项：
>
> 1. 建议全英文路径，不能有空格；
> 2. Windows 有路径长度限制，目录层级不能太深，建议就是 `D:\ncs`, `E:\ncs` 等等；
> 3. 后续开发工程存放的磁盘必须和 NCS 在同一个磁盘。

**nrfutil 和 VS Code 都要修改。**

nrfutil 设置方法：

```powershell
nrfutil sdk-manager config install-dir set "D:\ncs"
```

VS Code 设置方法：

![image-20260727153312403](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined9b8030e61b3f07d61c76fe2c7ea8b6a8.png)

更改后，你可以把原来的 `ncs/downloads` 拷贝过去，里面有压缩包。然后执行重新安装，安装时检查到本地有现成的文件，就会跳过下载，直接解压。



# 4. 实测效果

## 电脑配置与状态

- CPU: Intel Core Ultral 9 285H. 16核（6 P + 8 E + 2 LPE）.
- RAM: 32 GB
- 磁盘: YMTC YMSS2CD08D25MC, 1TB NVME SSD
- 电源：电源适配器插入，电源模式“最佳性能”，节能模式关闭

一块SSD分为两个分区：

- C 盘：NTFS
- D 盘：ReFS + DevDrive

## 测试路径

当前 Windows Defender 排除路径：

```
c:\ncs\
c:\nordic\
c:\Program Files\Windows Defender
c:\work\
d:\work\
e:\work\
```

因此可以这样设计实验路径：

1. `C:\ncs1`：既无 Defender排除项，又无 Dev Drive
2. `C:\ncs`只有 Defender 排除
3. `D:\work1`: 只有 Dev Drive
4. `D:\work`：既有 Defender 排除项，又有 Dev Drive

## 测试工程与编译命令

选择一个支持 TF-M 和 Wi-Fi 的复杂工程

编译命令：

```powershell
# 准备环境变量
nrfutil sdk-manager toolchain env --ncs-version=v3.4.0 --as-script powershell |
    Out-String |
    Invoke-Expression

# 进入 SDK
cd v3.4.0

# 选择 nRF54LM20 DK + nRF7002-EB II，开启TF-M
# 编译并计时
Measure-Command {
west build -p -b nrf54lm20dk/nrf54lm20a/cpuapp/ns nrf/samples/wifi/nrf_cloud -- -DSHIELD=nrf7002eb2
}
```

> 注意，`Measure-Command {}`会屏蔽 stdout。因此你看不到正常日志输出，只能看到 warning 和 error。

作为对比，这里也用 WSL ( Ubuntu 24.04) 进行测试。编译命令：

```bash
time west build -p -b nrf54lm20dk/nrf54lm20a/cpuapp/ns nrf/samples/wifi/nrf_cloud -- -DSHIELD=nrf7002eb2
```

测试结果：

| 优化组合                  | 第1次测试 | 第2次测试 | 第3次测试 | 平均（排除首次） | 耗时降低 |
| ------------------------- | --------- | --------- | --------- | ---------------- | -------- |
| 无优化                    | 140.8s    | 83.0s     | 83.9s     | 83.5s            | -        |
| 仅 Defender 排除          | 149.6s    | 78.7s     | 78.7s     | 78.7s            | 5.7%     |
| 仅 Dev Drive              | 155.0s    | 75.2s     | 75.6s     | 75.4s            | 9.7%     |
| Defender 排除 + Dev Drive | 156.3s    | 77.1s     | 77.3s     | 77.2s            | 7.5%     |
| WSL (Ubuntu 24.04)        | 41.9s     | 13.8s     | 13.1s     | 13.5s            | 83.8%    |

测试结果显示，虽然每次都是干净编译（`-p`参数，相当于删除 build 目录重编），但首次编译存在明显的冷启动开销。因此，后续比较采用排除首次测试后的平均值。

Defender 排除项使编译耗时降低约 5.7%，Dev Drive 单独使用降低约 9.7%，后者效果更好。

两种方法同时使用时，耗时降低约7.5%，没有出现叠加收益，反而略慢于单独使用 Dev Drive。这说明 Dev Drive 的 Performance Mode 已经缓解了 Defender 对开发文件 I/O 的影响，额外添加排除项属于重复优化。

WSL （Linux环境）的编译速度提升非常显著，几乎是5倍速度。因此有条件还是选择 Linux。

