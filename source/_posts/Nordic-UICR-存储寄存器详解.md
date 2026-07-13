---
title: Nordic UICR 存储寄存器详解
typora-root-url: ./..
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2026-07-09 16:19:52
cover:
tags:
  - Nordic
  - NCS
  - Storage
  - Security
categories: Nordic
cnblogs:
  postId: '21296608'
  url: https://www.cnblogs.com/jayant97/articles/21296608
  lastPublishedAt: '2026-07-09T16:41:34+08:00'
  sourceHash: sha256:7b716000915ee70faf46fe4bd54f2ceb49f6948157916bf25484cfc187daa250
  status: synced
  postType: Article
---

# 简介

Nordic 芯片上的 FICR（Factory information configuration registers）和 UICR（User Information Configuration Registers）也属于非易失性存储。它们底层通常和 SoC 上的 NVM 使用同类存储介质，但并不作为普通程序存储区来使用，而是以专用寄存器窗口的形式暴露出来。

例如：nRF54L15 地址空间映射

![img](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined696f9f8fca34432d2167230c6cb087fa.svg)



FICR 对开发者来说基本可以视为 ROM，存储了芯片 ID、默认地址、射频校准值等信息。

UICR 是可读写的，其中包含一些配置项，比如是否禁用 Debug 端口、NFC 引脚是否作为普通 GPIO 使用等。

# UICR 用户数据区

UICR 中还有**用户数据**区，可以放任意自定义二进制数据，更适合少量出厂写入的信息，例如：

1. 产品设备序列号；
2. MAC 地址；
3. 板级硬件版本；
4. 出厂校准常量；
5. 产测写入的少量标志位。

对比：

| 系列 / 型号     | 用户数据寄存器     |                    可单独擦除 UICR                    |         擦除前可写次数         |
| :-------------- | :----------------- | :------------------------------------------: | :----------------------: |
| nRF52840        | `UICR.CUSTOMER[n]` |     可以，`ERASEUICR`；启用 APPROTECT 后会阻止该操作     |     同一 32-bit word 约 2 次     |
| nRF52833        | `UICR.CUSTOMER[n]` |     可以，`ERASEUICR`；启用 APPROTECT 后会阻止该操作     |     同一 32-bit word 约 2 次     |
| 其他多数 nRF52  | `UICR.CUSTOMER[n]` |            通常可以，具体以目标型号手册为准             |     同一 32-bit word 通常 2 次     |
| nRF91 系列      | `UICR.OTP[n]`      |             不可单独擦除，只能使用 `ERASEALL`             | 每个 half-word 可写 1 次 |
| nRF5340 (App)   | `UICR.OTP[n]`      |             不可单独擦除，只能使用 `ERASEALL`             | 每个 half-word 可写 1 次 |
| nRF5340 (Net)   | `UICR.CUSTOMER[n]` |             不可单独擦除，只能使用 `ERASEALL`             |     同一 32-bit word 约 2 次     |
| nRF54L 系列     | `UICR.OTP[n]`      |             不可单独擦除，只能使用 `ERASEALL`             | 每个 32-bit word 可写 1 次 |

> UICR 用户数据区域很多时候是“模拟 OTP”，但不同系列的实现细节并不一样：有的是每个 32-bit word 最多写 2 次，有的是每个 half-word 只能写 1 次，也有的是整个 32-bit word 只能写 1 次。最终一定要以具体型号的数据手册为准。
>
> 像 `nRF91`、`nRF5340 App Core`、`nRF54L` 这类新一些的 SoC，通常都要求整片擦除后才能重新写这部分区域，这样更接近真正的一次性烧录模型。

# 生产时 UICR 烧写流程

```shell
# 1. 烧录固件（这里只是把操作追加到 batch 文件，还不会立刻连接设备）
nrfutil device program \
  --firmware app_merged.hex \
  --family nrf54l \
  --options reset=RESET_NONE \
  --append-batch flash_batch.json

# 2. 写 OTP 序列号 
## 54L15 UICR.OTP[288] 地址 0x00FFD000 + 0x500 + (288 × 0x4)
nrfutil device write \
  --address 0x00FFD980 \
  --value <序列号> \
  --family nrf54l \
  --append-batch flash_batch.json

# 3. reset 使 UICR 生效
nrfutil device reset \
  --family nrf54l \
  --append-batch flash_batch.json
  
# 3(可选). 锁 APPROTECT（内置写 UICR + 硬复位）
nrfutil device protection-set All \
  --family nrf54l \
  --append-batch flash_batch.json

# 4. 执行 batch（一次连接完成所有操作）
nrfutil device batch-execute --batch-file flash_batch.json
```

说明：

1. 使用 batch 的方法可以让 `nrfutil` 在整个流程中只建立一次 J-Link 连接，节省产线时间。

2. **操作顺序不可颠倒**：必须先 `program` 固件，再 `write` OTP。因为 `nrfutil device program` 默认使用 `chip_erase_mode=ERASE_ALL`，会擦除当前 core 对应的内部存储和 UICR；如果在 `program` 之前先写 OTP，后面的烧录很可能把序列号一起擦掉。

3. **`reset=RESET_NONE` 的作用**：让 `program` 完成后不自动复位，便于后续的 `write` 操作继续在同一批处理流程里完成。它的含义是不做 post-program reset，不等同于“切换到某种特殊调试模式”。

4. UICR 数据区域的部分空间可能会被 NCS 保留用于安全启动，见：[nRF54L One-Time Programmable memory map](https://nrfconnectdocs.nordicsemi.com/ncs/3.4.0/nrf/app_dev/device_guides/nrf54l/otp_map_nrf54l.html)。因此，**nRF54L 系列建议用户自己的使用空间从 `OTP[288]` 开始，到 `OTP[319]` 结束，共 32 个 word（128 bytes）。**
   在 NCS v3.4.0 及之后，SoC 默认设备树的 `&uicr` 节点中也能看到对应的 `bl_storage` 预留区域，在编译后的 `zephyr.dts` 总设备树中同样可见。

   ```dts
   &uicr {
   	bl_storage: uicr@500 {
   		// 这里展示的是当前 DTS 中声明的 bootloader storage 区域大小
   		// 但应用侧仍应按官方文档保留 OTP[0..287]，不要据此向前挪用
   		reg = <0x500 0x460>;
   	};
   };
   ```

   > 安全启动需要 NSIB（nRF Secure Immutable Bootloader, b0）作为永久不可变的初始 bootloader，用来引导 MCUboot。作为 Root of Trust，它需要 OTP 来保存公钥哈希等信息，确保后续引导的固件未被篡改。

5. 仅启用 `APPROTECT` 时，常见的恢复方式是执行 `nrfutil device recover`，它会通过整片擦除来重新解锁设备。

# 运行时 UICR 读取流程

```c
/* nRF52 系列没有安全域概念，直接读取 */
uint32_t val0 = NRF_UICR->CUSTOMER[0];
```

```c
/* 在安全空间内（board 后缀不带 "_ns"）时，可以直接读取 Secure UICR */
uint32_t val0 = NRF_UICR_S->OTP[0]; // nRF5340 App Core: OTP[0..191]
uint32_t val1 = NRF_UICR_S->OTP[1]; // nRF54L15: OTP[0..319]
// 在 Secure 代码中，NRF_UICR 通常会被映射为 NRF_UICR_S
uint32_t val2 = NRF_UICR->OTP[1];   // 等价
```

```c
/* 程序运行在非安全空间（board 后缀带 "_ns"）时，通常需要通过 TF-M 服务读取 */
#include <tfm_platform_api.h>

void read_otp_value(void)
{
    uint32_t otp_value;
    uint32_t result;
    enum tfm_platform_err_t plt_err;

    plt_err = tfm_platform_mem_read(
        (uint8_t *)&otp_value,
        (intptr_t)&NRF_UICR_S->OTP[0],  /* 告诉 Secure 侧要读哪个地址 */
        sizeof(otp_value),
        &result
    );

    if (plt_err != TFM_PLATFORM_ERR_SUCCESS || result != 0) {
        /* 处理错误 */
    }
    printk("OTP[0]: %u\n", otp_value);
}
// 注意：`tfm_platform_mem_read` 能读哪些地址由 Secure 侧 `tfm_platform_user_memory_ranges.h`
// 的白名单决定。文档里常用它来演示读取 OTP，但具体到某个芯片和 NCS 版本，
// 是否默认放行 UICR OTP，要以实际的 Secure 侧配置为准，不能一概而论。
```

