---
title: Matter证书体系与量产设备证书烧录
typora-copy-images-to: ../../source/imgs/${filename}.assets/
date: 2025-09-26 16:02:54
cover: null
tags:
- Nordic
- Matter
categories:
- Matter
typora-root-url: ./..
cnblogs:
  postId: '19122916'
  url: https://www.cnblogs.com/jayant97/articles/19122916
  lastPublishedAt: '2026-07-06T18:20:52+08:00'
  sourceHash: sha256:cfec944755dc1f6dced74d14aac692c5f7d1202f775cc50f79334f5dad2dc82a
  status: imported
  postType: Article
---

# 1. 简介

本文会详细介绍Matter的证书体系，以及如何在Nordic平台下量产最终设备时烧录factory data。

# 2. Matter证书体系

阅读这部分前，确保你了解数字签名、对称与非对称加密、数字证书、证书链、CA等相关概念。

Matter证书体系是为了确保消费者买到的设备确实是经过Matter认证的供应商生产的，并且经过了各项测试，从而满足兼容性和安全性的要求。

在设备入网阶段有一个过程叫做**设备认证（Device Attestation）**，就是Commissioner（如Apple HomePod音箱）来验证Commissionee（如Matter智能灯泡）是否经过认证的过程。

## 证书链

Matter**设备认证（Device Attestation）**中涉及到三个证书，它们是：

- PAA Certificate
- PAI Certificate
- DAC

机构与证书之间的关系：

![Device Attestation certification authorities](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefined42991b1f069e13231af0d66ea7a6a7aa.svg)

### PAA Certificate

PAA（Product Attestation Authority，产品认证授权机构）是经过CSA审核授权的CA机构，它们往往是大型公司或组织，它们拥有PAA根证书。

> PAA是指机构，但是有时也用PAA代指PAA证书。

PAA有两种机构：

- Vendor Scoped PAA：大型Matter设备制造商。它们自己制造Matter设备，如Apple, Google, Amazon, Samsung

- Non-VID Scoped PAA：如模块与方案商，大型芯片公司，专业数字证书服务提供商。它们自己不生产Matter设备，而是给自己的制造商客户提供证书服务（[CSA官方PAA名单](https://csa-iot.org/certification/paa/)）。

Non-VID Scoped PAA的存在极大的降低了Matter的准入门槛，让中小型企业无需投入巨资和精力复杂审核去申请PAA，加快产品认证和上市流程。

PAA证书的私钥被以最高安全规格（通常使用HSM硬件安全模块）保管在其安全设施中。而PAA的**公钥证书**则是公开的，分发到所有Matter控制器的信任库中。你的手机、智能音箱等控制器在出厂时就内置了这些PAA的根证书。

### PAI Certificate

PAI Certificate（Product Attestation Intermediate Certificate，产品认证中间证书），简称PAI。是一个中间证书，通常来说一个系列的产品对应一个或多个PAI。

PAI需要放置在Matter产品的出厂烧录工具中使用，为每一台出厂的Matter设备签发唯一的DAC。

PAI的持有者是设备制造商。对于自己就是PAA的制造商，他们可以给自己签发PAI。对于中小型制造商，他们可以向PAA购买PAI。

设备制造商可以拥有多个PAI，来给不同产品系列签发证书。

### DAC

DAC（Device Attestation Certificates，设备认证证书），是烧录在每一台Matter设备中的唯一证书。包含了产品的特定信息（序列号、固件版本等）。

在设备入网阶段，Matter Commissioner（负责管理设备入网，如Apple Homepod）会检查Commissionee（待入网设备）的DAC，确认它的证书链是来源于某个PAA的，就可以证明这确实是CSA成员公司制造的正品。

> 注意，DAC只能证明设备身份。单靠DAC不能说明设备通过了Matter合规性认证。

### PKI

以上的证书链构成了Matter世界中的**PKI（Public Key Infrastructure，公钥基础设施）**。对于任何一个设备的证书，都可以检查它的证书链（DAC-PAI-PAA），如果整个证书链的签名都是有效的，并且PAA是可信的，就可以认为这台Matter设备是可信的。**PKI是一个概念，表示这一整套建立数字信任的规则和系统**。

### DCL

![Device Attestation certification authorities with PKI and DCL](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedbbfe5a8c17c982a849f14c67a2239fac.svg)

DCL（Distributed Compliance Ledger，分布式合规账本）是CSA维护的一个全球数据库服务器，里面存储了PAA证书公钥，各个制造商的认证信息等。

DCL的特殊之处在于，它是用区块链技术搭建的，有多个服务器分布在全球。因此它是去中心化的、不可被篡改的。它是Matter全局信任的基石。

各大生态系统（iOS，Android）定期从DCL同步数据，更新设备内部的PAA信任库。最终手机就可以验证Matter设备是否经过认证。

### Matter SDK中的证书文件

> 【注意】
>
> 在阅读NCS文档或Matter官方文档时，以下两个git仓库名称：
>
> - [${NCS}/modules/lib/matter](https://github.com/nrfconnect/sdk-connectedhomeip)：
> - [connectedhomeip](https://github.com/project-chip/connectedhomeip)
>
> 指的是同一个仓库，也就是Matter SDK。只不过NCS已经fork并包含了此仓库，直接进入`${NCS}/modules/lib/matter`即可

在Matter SDK中，`credentials`路径下有很多证书文件：

```
credentials/
├── development/
│   ├── attestation/
│   ├── cd-certs/
│   └── paa-root-certs/
├── production/
│   └── paa-root-certs/
└── test/
    ├── attestation/
    ├── certification-declaration/
    ├── operational-certificates/
    └── operational-certificates-error-cases/
```

这些证书（Cert）和私钥（Key）基本都有两种格式：二进制的`.der`和文本的`.pem`

- `development/`下是研发过程中可以随意使用的测试证书，包括PAA，PAI，DAC，且都包含证书和私钥。此外还有一些测试用的CD。

- `production/`下是各大PAA的根证书。只有证书，没有私钥。用户可以用它们来验证某个DAC证书的证书链是否来源于某个PAA
- `test/`下的证书是官方合规性认证的用途，厂商可以不管

这里，`development/`下开发测试用的证书，还很贴心的提供了VID和PID。

比如PAI证书，就提供了VID（0xFFF3）：`credentials/development/attestation/Matter-Development-PAI-FFF3-noPID-Cert.pem`

而DAC证书，就同时提供了VID（0xFFF3）和PID（0x8018）：`credentials/development/attestation/Matter-Development-DAC-FFF3-8018-Cert.pem`

这样我们后续生成CD和Factory Data进行测试时，就方便填入VID和PID参数了。

# 3. Matter认证声明（CD）

PKI证书链（PAA->PAI->DAC）认证和Matter合规性认证是两个相对独立的过程。PKI的目的只是证明设备是合规的Matter制造商生产的。只要制造商拿到PAI就能随意生成DAC，不论设备是否已经通过Matter认证。

因此，还需要CD（Certification Declaration，认证声明）文件。

CD是一个加密文档，当设备通过了Matter合规性认证后，制造商就可以获得CSA签发的CD文件。一系列产品使用相同的CD。

把CD和PAI，DAC都烧录到产品中，这个产品就是Matter合规产品了。

![Simplified view of Device Attestation information from manufacturer](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinede3cad0edf1ba3b5434470d83c8f988cc.svg)

注意PAI和DAC在factory data中，是一个独立于固件的分区，而CD在固件内。因此，一台设备可以先携带测试用CD去做认证，认证通过后，通过OTA DFU的方式升级新的固件，并携带新的CD。

> - VID：Vendor ID。标识制造商的唯一16位数字。当制造商成为CSA成员时，可以从CSA获得此ID。
> - PID：Product ID。表示产品系列的唯一16位数字。制造商自己分配。同一个产品系列的所有设备PID都相同。
>
> Matter Commissioner会验证Commissionee的DAC和CD，查看两者的VID和PID是否一致。

## 总框图

![Device Attestation procedure overview](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinedb0f83932c27d65b3446794667e8139c0.svg)



## CD固化

完成 Matter 认证流程，认证通过后，CSA 会为你的产品生成并颁发正式的 CD 文件。每次产品固件升级并重新认证后，都需要申请新的 CD 并替换设备上的旧 CD。

要把CD存储到产品中，有两种方式：

1. 把CD转换成数组直接编译在固件中
2. 把CD存储在Zephyr存储系统中，从而允许先烧录固件再存储CD

### 方式1：CD直接写入到固件中

这种方法最简单省事，因为一个系列产品的同一个固件版本的CD都是一样的，因此直接写到固件中即可。

用Linux命令`xxd`把CD证书文件转换成十六进制数组：

```bash
cat CD.der | xxd -i
```

然后在`chip_project_config.h`中添加`CHIP_DEVICE_CONFIG_CERTIFICATION_DECLARATION`宏定义，加上大括号{}。我这里用测试CD来展示格式：

```c
// test CD
#define CHIP_DEVICE_CONFIG_CERTIFICATION_DECLARATION                                                                               \
    {                                                                                                                              \
        0x30, 0x82, 0x02, 0x19, 0x06, 0x09, 0x2a, 0x86, 0x48, 0x86, 0xf7, 0x0d, 0x01, 0x07, 0x02, 0xa0, 0x82, 0x02, 0x0a, 0x30,    \
            0x82, 0x02, 0x06, 0x02, 0x01, 0x03, 0x31, 0x0d, 0x30, 0x0b, 0x06, 0x09, 0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04,      \
            0x02, 0x01, 0x30, 0x82, 0x01, 0x71, 0x06, 0x09, 0x2a, 0x86, 0x48, 0x86, 0xf7, 0x0d, 0x01, 0x07, 0x01, 0xa0, 0x82,      \
            0x01, 0x62, 0x04, 0x82, 0x01, 0x5e, 0x15, 0x24, 0x00, 0x01, 0x25, 0x01, 0xf1, 0xff, 0x36, 0x02, 0x05, 0x00, 0x80,      \
            0x05, 0x01, 0x80, 0x05, 0x02, 0x80, 0x05, 0x03, 0x80, 0x05, 0x04, 0x80, 0x05, 0x05, 0x80, 0x05, 0x06, 0x80, 0x05,      \
            0x07, 0x80, 0x05, 0x08, 0x80, 0x05, 0x09, 0x80, 0x05, 0x0a, 0x80, 0x05, 0x0b, 0x80, 0x05, 0x0c, 0x80, 0x05, 0x0d,      \
            0x80, 0x05, 0x0e, 0x80, 0x05, 0x0f, 0x80, 0x05, 0x10, 0x80, 0x05, 0x11, 0x80, 0x05, 0x12, 0x80, 0x05, 0x13, 0x80,      \
            0x05, 0x14, 0x80, 0x05, 0x15, 0x80, 0x05, 0x16, 0x80, 0x05, 0x17, 0x80, 0x05, 0x18, 0x80, 0x05, 0x19, 0x80, 0x05,      \
            0x1a, 0x80, 0x05, 0x1b, 0x80, 0x05, 0x1c, 0x80, 0x05, 0x1d, 0x80, 0x05, 0x1e, 0x80, 0x05, 0x1f, 0x80, 0x05, 0x20,      \
            0x80, 0x05, 0x21, 0x80, 0x05, 0x22, 0x80, 0x05, 0x23, 0x80, 0x05, 0x24, 0x80, 0x05, 0x25, 0x80, 0x05, 0x26, 0x80,      \
            0x05, 0x27, 0x80, 0x05, 0x28, 0x80, 0x05, 0x29, 0x80, 0x05, 0x2a, 0x80, 0x05, 0x2b, 0x80, 0x05, 0x2c, 0x80, 0x05,      \
            0x2d, 0x80, 0x05, 0x2e, 0x80, 0x05, 0x2f, 0x80, 0x05, 0x30, 0x80, 0x05, 0x31, 0x80, 0x05, 0x32, 0x80, 0x05, 0x33,      \
            0x80, 0x05, 0x34, 0x80, 0x05, 0x35, 0x80, 0x05, 0x36, 0x80, 0x05, 0x37, 0x80, 0x05, 0x38, 0x80, 0x05, 0x39, 0x80,      \
            0x05, 0x3a, 0x80, 0x05, 0x3b, 0x80, 0x05, 0x3c, 0x80, 0x05, 0x3d, 0x80, 0x05, 0x3e, 0x80, 0x05, 0x3f, 0x80, 0x05,      \
            0x40, 0x80, 0x05, 0x41, 0x80, 0x05, 0x42, 0x80, 0x05, 0x43, 0x80, 0x05, 0x44, 0x80, 0x05, 0x45, 0x80, 0x05, 0x46,      \
            0x80, 0x05, 0x47, 0x80, 0x05, 0x48, 0x80, 0x05, 0x49, 0x80, 0x05, 0x4a, 0x80, 0x05, 0x4b, 0x80, 0x05, 0x4c, 0x80,      \
            0x05, 0x4d, 0x80, 0x05, 0x4e, 0x80, 0x05, 0x4f, 0x80, 0x05, 0x50, 0x80, 0x05, 0x51, 0x80, 0x05, 0x52, 0x80, 0x05,      \
            0x53, 0x80, 0x05, 0x54, 0x80, 0x05, 0x55, 0x80, 0x05, 0x56, 0x80, 0x05, 0x57, 0x80, 0x05, 0x58, 0x80, 0x05, 0x59,      \
            0x80, 0x05, 0x5a, 0x80, 0x05, 0x5b, 0x80, 0x05, 0x5c, 0x80, 0x05, 0x5d, 0x80, 0x05, 0x5e, 0x80, 0x05, 0x5f, 0x80,      \
            0x05, 0x60, 0x80, 0x05, 0x61, 0x80, 0x05, 0x62, 0x80, 0x05, 0x63, 0x80, 0x18, 0x24, 0x03, 0x16, 0x2c, 0x04, 0x13,      \
            0x5a, 0x49, 0x47, 0x32, 0x30, 0x31, 0x34, 0x32, 0x5a, 0x42, 0x33, 0x33, 0x30, 0x30, 0x30, 0x33, 0x2d, 0x32, 0x34,      \
            0x24, 0x05, 0x00, 0x24, 0x06, 0x00, 0x25, 0x07, 0x94, 0x26, 0x24, 0x08, 0x00, 0x18, 0x31, 0x7d, 0x30, 0x7b, 0x02,      \
            0x01, 0x03, 0x80, 0x14, 0x62, 0xfa, 0x82, 0x33, 0x59, 0xac, 0xfa, 0xa9, 0x96, 0x3e, 0x1c, 0xfa, 0x14, 0x0a, 0xdd,      \
            0xf5, 0x04, 0xf3, 0x71, 0x60, 0x30, 0x0b, 0x06, 0x09, 0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x01, 0x30,      \
            0x0a, 0x06, 0x08, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x04, 0x03, 0x02, 0x04, 0x47, 0x30, 0x45, 0x02, 0x20, 0x24, 0xe5,      \
            0xd1, 0xf4, 0x7a, 0x7d, 0x7b, 0x0d, 0x20, 0x6a, 0x26, 0xef, 0x69, 0x9b, 0x7c, 0x97, 0x57, 0xb7, 0x2d, 0x46, 0x90,      \
            0x89, 0xde, 0x31, 0x92, 0xe6, 0x78, 0xc7, 0x45, 0xe7, 0xf6, 0x0c, 0x02, 0x21, 0x00, 0xf8, 0xaa, 0x2f, 0xa7, 0x11,      \
            0xfc, 0xb7, 0x9b, 0x97, 0xe3, 0x97, 0xce, 0xda, 0x66, 0x7b, 0xae, 0x46, 0x4e, 0x2b, 0xd3, 0xff, 0xdf, 0xc3, 0xcc,      \
            0xed, 0x7a, 0xa8, 0xca, 0x5f, 0x4c, 0x1a, 0x7c                                                                         \
    }
```

> - 宏定义数组记得加换行符`\`，且同一行的`\`之后不能有任何字符（包括空格），才能确保所有行都在同一个宏定义中
>
> -  `chip_project_config.h`的默认路径是`"src/chip_project_config.h"`，在`prj.conf`中可以设置：
>   ```bash
>   CONFIG_CHIP_PROJECT_CONFIG="src/chip_project_config.h"
>   ```

### 方式2：CD写入Zephyr存储系统

此方法需要开启`CONFIG_CHIP_CERTIFICATION_DECLARATION_STORAGE=y`

这种方法比较复杂，一般没必要。厂商需要在自己的产测工具中开发把CD传入设备的功能（串口、USB、蓝牙等），然后设备中需要把数据存入Settings对应的Key的位置。这部分没有文档，需要阅读源码：

`v3.0.2/modules/lib/matter/src/platform/nrfconnect/FactoryDataProvider.cpp`，

在此源码中，`GetCertificationDeclaration` 方法会优先尝试从 Zephyr 的配置存储（settings）读取 CD 数据：

```cpp
if (Internal::ZephyrConfig::ReadConfigValueBin(Internal::ZephyrConfig::kConfigKey_CertificationDeclaration,
                                               reinterpret_cast<uint8_t *>(outBuffer.data()), outBuffer.size(),
                                               cdLen) == CHIP_NO_ERROR)
{
    outBuffer.reduce_size(cdLen);
    return CHIP_NO_ERROR;
}
```

只有在存储中没有找到时，才会返回默认的 CD 数据（`CHIP_DEVICE_CONFIG_CERTIFICATION_DECLARATION`）。

这段代码是用固定的Key来从文件系统中读取的：

```cpp
const ZephyrConfig::Key ZephyrConfig::kConfigKey_CertificationDeclaration = CONFIG_KEY(NAMESPACE_FACTORY "cert-declaration");
```

因此，开发者需要用自己的方式把CD传入，然后调用Zephyr Settings相关函数，把CD存储到这个Key的位置。

> 其实NCS里实现了一种传入CD的方式，相关代码位于`v3.0.2/modules/lib/matter/src/platform/nrfconnect/OTAImageProcessorImpl.cpp`。可以参考。
>
> 在这里，注册了一个`dfu_image_writer`，它包含一组DFU回调函数，它们是用lambda表达式编写的匿名函数：
>
> ```cpp
> #ifdef CONFIG_CHIP_CERTIFICATION_DECLARATION_STORAGE
>     dfu_image_writer cdWriter;
>     cdWriter.image_id = CONFIG_CHIP_CERTIFiCATION_DECLARATION_OTA_IMAGE_ID;
>     cdWriter.open     = [](int id, size_t size) { return size <= sizeof(sCdBuf) ? 0 : -EFBIG; };
>     cdWriter.write    = [](const uint8_t * chunk, size_t chunk_size) {
>         memcpy(&sCdBuf[sCdSavedBytes], chunk, chunk_size);
>         sCdSavedBytes += chunk_size;
>         return 0;
>     };
>     cdWriter.close = [](bool success) {
>         return settings_save_one(Internal::ZephyrConfig::kConfigKey_CertificationDeclaration, sCdBuf, sCdSavedBytes);
>     };
> 
>     ReturnErrorOnFailure(System::MapErrorZephyr(dfu_multi_image_register_writer(&cdWriter)));
> #endif
> ```
>
> 在OTA过程结束时，在`close`回调函数里执行了`settings_save_one()`，把CD存储到Settings子系统中。
>
> 这一套代码的上层是Matter OTA流程（并非MCUMgr DFU）：
>
> OTA 开始 → PrepareDownload() → SystemLayer().ScheduleLambda() → PrepareDownloadImpl()
>
> 而这里的底层实现是Nordic的DFU Multi Image库，可以参考官方文档：[DFU multi-image](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/libraries/dfu/dfu_multi_image.html)。

# 4. 生成DAC

量产时，每台设备都需要被烧录唯一的DAC。

## 安装chip-cert

对于Linux和MacOS环境（包括树莓派的ARM64架构），推荐下载 [Nordic预编译可执行文件](https://github.com/nrfconnect/sdk-connectedhomeip/releases)，下载对应的架构，改名为`chip-cert`并赋予可执行权限，再添加到PATH环境变量即可。

> Windows下目前暂无原生的chip-tool。研发阶段可以在WSL或者虚拟机中使用Linux。
>
> 如果是量产工具是Windows环境，则可以考虑预先在Linux环境用chip-cert批量生成大量DAC文件，拷贝到Windows生产环境中使用。Nordic提供的factory data生成脚本是支持windows的。

## 用PAI签发DAC

官方文档：[Matter/CHIP Certificate Tool — gen-att-cert](https://project-chip.github.io/connectedhomeip-doc/src/tools/chip-cert/README.html#gen-att-cert)

先查看自己要使用的PAI的内容：

```bash
$ openssl x509 -in credentials/development/attestation/Matter-Development-PAI-FFF1-noPID-Cert.pem  -text -noout 

Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number: 6245791343685426020 (0x56ad8222ad945b64)
        Signature Algorithm: ecdsa-with-SHA256
        Issuer: CN = Matter Test PAA, 1.3.6.1.4.1.37244.2.1 = FFF1
        Validity
            Not Before: Feb  5 00:00:00 2022 GMT
            Not After : Dec 31 23:59:59 9999 GMT
        Subject: CN = Matter Dev PAI 0xFFF1 no PID, 1.3.6.1.4.1.37244.2.1 = FFF1
        Subject Public Key Info:
            Public Key Algorithm: id-ecPublicKey
                Public-Key: (256 bit)
                pub:
                    04:41:9a:93:15:c2:17:3e:0c:8c:87:6d:03:cc:fc:
                    94:48:52:64:7f:7f:ec:5e:50:82:f4:05:99:28:ec:
                    a8:94:c5:94:15:13:09:ac:63:1e:4c:b0:33:92:af:
                    68:4b:0b:af:b7:e6:5b:3b:81:62:c2:f5:2b:f9:31:
                    b8:e7:7a:aa:82
                ASN1 OID: prime256v1
                NIST CURVE: P-256
        X509v3 extensions:
            X509v3 Basic Constraints: critical
                CA:TRUE, pathlen:0
            X509v3 Key Usage: critical
                Certificate Sign, CRL Sign
            X509v3 Subject Key Identifier: 
                63:54:0E:47:F6:4B:1C:38:D1:38:84:A4:62:D1:6C:19:5D:8F:FB:3C
            X509v3 Authority Key Identifier: 
                6A:FD:22:77:1F:51:1F:EC:BF:16:41:97:67:10:DC:DC:31:A1:71:7E
    Signature Algorithm: ecdsa-with-SHA256
    Signature Value:
        30:45:02:21:00:b2:ef:27:f4:9a:e9:b5:0f:b9:1e:ea:c9:4c:
        4d:0b:db:b8:d7:92:9c:6c:b8:8f:ac:e5:29:36:8d:12:05:4c:
        0c:02:20:65:5d:c9:2b:86:bd:90:98:82:a6:c6:21:77:b8:25:
        d7:d0:5e:db:e7:c2:2f:9f:ea:71:22:0e:7e:a7:03:f8:91
```

注意`Validity`对应的证书有效时间，这个是UTC时间，不是本地时间。

使用PAI来签发DAC：

测试路径`${NCS}/modules/lib/matter/`

```bash
chip-cert gen-att-cert --type d \
--subject-cn "Matter Development DAC 01" \
--subject-vid FFF1 \
--subject-pid 0123 \
--valid-from "2025-09-29 9:03:43" \
--lifetime 7305 \
--ca-key credentials/development/attestation/Matter-Development-PAI-FFF1-noPID-Key.pem \
--ca-cert credentials/development/attestation/Matter-Development-PAI-FFF1-noPID-Cert.pem \
--out-key Matter-Development-PAI-FFF1-0123-Key.pem \
--out Matter-Development-PAI-FFF1-0123-Cert.pem
# 文件将生成在当前目录下
```

- `--subject-vid`与`--subject-pid`：如果你是自己的产品，VID和PID正常填写。如果你是用开发测试证书，会看到PAI证书上已经标明了VID，因此我们输入的VID要与其保持一致。

- `--valid-from`：证书有效开始时间。首先，必须处于PAI的起始时间和结束时间之间；其次，不能是未来的时间，例如现在是上海时区17:08 (UTC+8)，那么在生成证书时，不能超过09:08 (UTC+0)。

- `--lifetime`：DAC证书的有效时间，单位为天。7305约为20年。

  你可以设置一个特殊值`4294967295`来表示证书没有明确定义有效时间。

  当证书到期后，设备将无法再被配网。已经入网的设备不受影响，因为已经入网的设备靠入网时安装的NOC证书来通信。

  因此考虑设置尽可能长的时间，或者能够OTA这个设备。
  （NCS默认的factory data实现方式具有写保护，因此Factory data分区无法OTA 。需要自己实现factory data provider来实现OTA功能。）

## 验证DAC的证书链

```bash
## 执行无报错就是验证成功

# 用自己生成的DAC验证
chip-cert validate-att-cert \
--dac Matter-Development-PAI-FFF1-0123-Cert.pem \
--pai credentials/development/attestation/Matter-Development-PAI-FFF1-noPID-Cert.pem \
--paa credentials/development/paa-root-certs/Chip-Test-PAA-FFF1-Cert.pem

# 用SDK自带的DAC验证
chip-cert validate-att-cert \
--dac credentials/development/attestation/Matter-Development-DAC-FFF1-8000-Cert.pem \
--pai credentials/development/attestation/Matter-Development-PAI-FFF1-noPID-Cert.pem \
--paa credentials/development/paa-root-certs/Chip-Test-PAA-FFF1-Cert.pem
```

常见错误：

- `Attestation Certificates Validation Failed with Error Code: 300`：DAC的起始时间（UTC）时间在未来。注意中国时区的时间减去8小时才是UTC时间。
- `Attestation Certificates Validation Failed with Error Code: 301`：校验失败。一般是DAC的起始时间比PAI的起始时间还要早导致。

## DAC格式转换

`.pem`证书转换为二进制`.der`证书：

```bash
./chip-cert convert-cert <in-file> <out-file> -d
```



# 5. Matter工厂数据配置

Matter工厂数据（Factory Data）是要烧录到设备中的二进制数据，包含PAI，DAC等等信息，不包括CD。

## 固件配置

默认情况下，Matter例程会自动生成测试版工厂数据，并把它和app, mcuboot固件编译在一起。

要想烧录自己的工厂数据，需要修改配置：

`prj.conf`或`prj_release.conf`

```bash
# 使用Nordic Factory Data Provider来存储和解析factory data
CONFIG_CHIP_FACTORY_DATA=y

# 编译时不要自动生成测试factory data
CONFIG_CHIP_FACTORY_DATA_BUILD=n

# 过认证时打开，量产时关闭
CONFIG_NCS_SAMPLE_MATTER_TEST_EVENT_TRIGGERS_REGISTER_DEFAULTS=n
CONFIG_NCS_SAMPLE_MATTER_TEST_EVENT_TRIGGERS=n
```

`sysbuild.conf`

```bash
SB_CONFIG_MATTER_FACTORY_DATA_GENERATE=n
```



## 工厂数据存储位置

NCS通过 Partition Manager 来配置MCU的非易失存储器分区，见[《理解Zephyr编译与配置系统 - 存储器分区文件》](https://jayant-tang.github.io/2022/12/2a39e705bff0/#7-%E5%AD%98%E5%82%A8%E5%99%A8%E5%88%86%E5%8C%BA%E6%96%87%E4%BB%B6%EF%BC%88Partition-Manager%EF%BC%89)。

你可以参考Matter例程的存储器分区文件，不同的MCU在例程里给的存储位置不同，例如：

```yaml
factory_data:
  address: 0xf7000
  size: 0x1000
  region: flash_primary
```

这里的存储位置就是0xf7000，长度4096Bytes。

factory_data很小，不超过4kB，但是在分区时要占用存储器的一个完整的page。

### 工厂数据地址对齐

在对Flash进行分区时，注意要与Nordic[硬件Flash写保护功能](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/libraries/security/bootloader/fprotect.html#fprotect-readme)对齐。

它是一个上层的统一API，不同SoC的安全硬件可能不一样。它可以设置任意的几个起始地址和长度，从而使得这些区域在运行时不会被意外覆写。并且只要程序不reset，这种保护就不会被取消。当然，这里的起始地址和长度都要对齐MCU的page大小。

在Matter工程中，开启`CONFIG_CHIP_FACTORY_DATA_WRITE_PROTECT=y`和`CONFIG_FPROTECT=y`，程序就会从分区中读出Factory Data的首尾地址，并开启这段区域的写保护。（见`v3.0.2/modules/lib/matter/src/platform/nrfconnect/FactoryDataProvider.h`）。

**写保护的BLOCK长度，取决于MCU上的硬件保护单元，和Flash的Page大小不一定相同**。

它的大小是`CONFIG_FPROTECT_BLOCK_SIZE`，它的值不能设置，因为它是一个隐性配置项，只取决于硬件：

`v3.0.2/nrf/lib/fprotect/Kconfig`

```
config FPROTECT_BLOCK_SIZE
	hex
	default NRF_SPU_FLASH_REGION_SIZE if CPU_HAS_NRF_IDAU
	default NRF_MPU_FLASH_REGION_SIZE if HAS_HW_NRF_MPU
	default NRF_BPROT_FLASH_REGION_SIZE if HAS_HW_NRF_BPROT
	default NRF_ACL_FLASH_REGION_SIZE if HAS_HW_NRF_ACL
	default NRF_RRAM_REGION_SIZE_UNIT if SOC_SERIES_NRF54LX && FLASH
	default $(dt_node_int_prop_hex,$(DT_CHOSEN_ZEPHYR_FLASH),erase-block-size)
```

可以通过`build/<application_name>/zephyr/.config`查看具体值，这里给出一个表格：

| 硬件保护单元 | 芯片系列                               | 说明                                                         | CONFIG_FPROTECT_BLOCK_SIZE                                   |
| ------------ | -------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| IDAU（SPU）  | nRF53, nRF91                           | Arm TrustZone安全架构用于区分安全、非安全区域。需要Arm v8，如Cortex-M33 | 53系列为16kB（0x4000）；<br />91系列为32kB（0x8000）         |
| MPU          | nRF51822                               | 设备树带有`compatible = "nordic,nrf-mpu";`的SoC              | 4kB（0x1000），与flash page一致                              |
| BPROT        | nRF52832, nRF52811, nRF52810, nRF52805 | 设备树带有`compatible = "nordic,nrf-bprot";`的SoC            | 从`/chosen/zephyr,flash`节点下的`erase-block-size`属性读取，与flash page大小一致 |
| ACL          | nRF53, nRF52840, nRF52833, nRF52820    | 设备树带有`compatible = "nordic,nrf-acl";`的SoC              | 从`/chosen/zephyr,flash`节点下的`erase-block-size`属性读取，与flash page大小一致 |
| RRAMC        | nRF54L                                 | 54L使用RRAM技术，而非Flash技术                               | 此config为4kB（0x1000），但实际硬件（[REGION.CONFIG](https://docs.nordicsemi.com/bundle/ps_nrf54L15/page/rramc.html#ariaid-title37)）支持1kB（0x400） |

因此，在定义存储器分区时：使用nRF52840和54L15开发，注意flash分区要和4kB对齐；使用nRF5340开发时，flash分区要和16kB对齐。

> Kconfig的default值匹配是采用第一个匹配上的值。这里nRF5340匹配上的是IDAU的16kB，因此就不再采用ACL的4kB。



![Factory data partition implementation criteria for fprotect](https://jayant-blog-imgs.oss-cn-hangzhou.aliyuncs.com/undefinede2ac0d4819036f689c75e2395730a388.svg)

一般来说factory_data在app固件的后面，而settings_storage在factory_data的后面。而factory_data和app开启写保护是没问题的；而settings存储器分区不能开启写保护。**因此注意不要把factory_data和settings放到同一个FPROTECT Block里。**

> NCS中其他使用到FPROTECT的位置：
>
> - mcuboot：如果在mcuboot中（工程的`sysbuild/mcuboot/prj.conf`）启动`CONFIG_FPROTECT=y`，mcuboot会对自己的flash区域开启写保护：
> - b0：5340 network core使用的bootloader也可以对自己的分区开启写保护。
> - hw_unique_key：硬件唯一ID的库可以把自己存储key的区域进行写保护

## 工厂数据内容表

| Key name             | Full name                            | Length               | Format       | 合规要求 | Description                                                  |
| -------------------- | ------------------------------------ | -------------------- | ------------ | -------- | ------------------------------------------------------------ |
| `version`            | factory data 版本                    | 2 B                  | uint16       | **必选** | 当前的factory data集版本. 必须与设备上的Factory Data Provider版本一致. 用户不可更改 |
| `sn`                 | 产品序列号                           | <1, 32> B            | ASCII string | **必选** | 每台设备的唯一序列号，最长32字符                             |
| `vendor_id`          | vendor ID                            | 2 B                  | uint16       | **必选** | CSA分配的制造商ID                                            |
| `product_id`         | product ID                           | 2 B                  | uint16       | **必选** | 制造商自己分配的产品型号ID，同一系列产品都用这个ID           |
| `vendor_name`        | vendor name                          | <1, 32> B            | ASCII string | **必选** | 用户可读的制造商名称字符串，最长32字符                       |
| `product_name`       | product name                         | <1, 32> B            | ASCII string | **必选** | 用户可读的产品名称字符串，最长32字符                         |
| `date`               | manufacturing date                   | 10 B                 | ISO 8601     | **必选** | 生产日期。格式必须符合ISO 8601, 如： `YYYY-MM-DD`.           |
| `hw_ver`             | hardware version                     | 2 B                  | uint16       | **必选** | 制造商自定义的硬件版本号（16bit）                            |
| `hw_ver_str`         | hardware version string              | <1, 64> B            | ASCII string | **必选** | 用户可读的制造商自定义的硬件版本号字符串                     |
| `dac_cert`           | Device Attestation Certificate (DAC) | <1, 602> B           | byte string  | **必选** | DAC证书文件。格式为DER编码的X.509v3-compliant证书，于RFC 5280中定义. |
| `dac_key`            | DAC private key                      | 68 B                 | byte string  | **必选** | DAC私钥。烧写过程中注意保密，不要泄露。也可以把DAC存放在加密存储后端而不是factory_data中，见： [Storing Device Attestation Certificate private key](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/protocols/matter/end_product/security.html#matter-platforms-security-dac-priv-key) |
| `pai_cert`           | Product Attestation Intermediate     | <1, 602> B           | byte string  | **必选** | PAI证书文件。格式为DER编码的X.509v3-compliant证书，于RFC 5280中定义. |
| `spake2_it`          | SPAKE2+ iteration counter            | 4 B                  | uint32       | **必选** | [SPAKE2+](https://datatracker.ietf.org/doc/rfc9383/) 是用于生成共享密钥的算法。用于设备配网期间的共享密钥生成。SPAKE2迭代计数器介于1000和100000之间，数值越大生成的密钥越强，但也越花时间。默认值1000. |
| `spake2_salt`        | SPAKE2+ salt                         | <16, 32> B           | byte string  | **必选** | [SPAKE2+](https://datatracker.ietf.org/doc/rfc9383/) 是用于生成共享密钥的算法。用于设备配网期间的共享密钥生成。SPAKE2+ 盐是一串随机base64字符串，16 至32 字节。密码会加上盐再进行哈希计算，再生成共享密钥，防止攻击者使用彩虹表（提前制作常用密码的哈希值）来快速破解密钥。盐的作用是提高随机性，增加破解难度。 |
| `spake2_verifier`    | SPAKE2+ verifier                     | 97 B                 | byte string  | **必选** | [SPAKE2+](https://datatracker.ietf.org/doc/rfc9383/) 是用于生成共享密钥的算法。用于设备配网期间的共享密钥生成。SPAKE2+ verifier是由spake2_it，spake2_salt, passcode共同生成。 |
| `discriminator`      | Discriminator                        | 2 B                  | uint16       | **必选** | discriminator是一个12-bit值。用于在配网前区分设备的广播，例如同时有多台设备等待配网，手机扫描二维码或NFC后获得discriminator，就知道要连接哪个广播了。由于不需要全局唯一，因此生产时可以滚动分配。<br />如果不用二维码，而是用适合人阅读的手动配对码（Manual Pairing Code），手动配对码是Discriminator的最高4位 |
| `passcode`           | SPAKE2+ passcode                     | 4 B                  | uint32       | *可选*   | [SPAKE2+](https://datatracker.ietf.org/doc/rfc9383/) 是用于生成共享密钥的算法。用于设备配网期间的共享密钥生成。 passcode是在共享密钥生成之前，Comisioner和Commissionee之间的临时加密会话所使用的简单密钥。 范围1到99999998（并且以下数值不可以使用：`11111111`,`22222222`,`33333333`,`44444444`,`55555555`,`66666666`,`77777777`,`88888888`,`99999999`）默认值为20202021.。这个值最好随机生成且与产品序列号、生产日期等公开信息无关。<br />Passcode在设备中的存储应当与 SPAKE2+ verifier隔离，并且任何Matter命令都不能读到这个值。 因此在Factory Data中包含passcode不是必选的，一般只有debug log打印配网信息，或者NFC配网才需要把passcode放在factory data。反而包含passcode会导致违反“Passcode应当与SPAKE2+ verifier隔离”的规则。 |
| `product_appearance` | Product visible appearance           | 2 B                  | CBOR map     | *可选*   | 产品外观枚举值。分为2部分，见下表。                          |
| `rd_uid`             | rotating device ID unique ID         | <16, 32> B           | byte string  | *可选*   | [Amazon Frustration-Free Setup support](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/protocols/matter/getting_started/advanced_kconfigs.html#ug-matter-configuring-ffs) 所需的ID. 如果factory data带这个参数，固件里的[CONFIG_CHIP_FACTORY_DATA_ROTATING_DEVICE_UID_MAX_LEN](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/samples/matter/common/config_matter_stack.html#config-chip-factory-data-rotating-device-uid-max-len) 也必须设置成这个参数的长度。 |
| `user`               | User data                            | variable, max 1024 B | CBOR map     | *可选*   | 厂商自定义数据，可以在设备的程序中读出。                     |

外观枚举（`product_appearance`）：

1. 外饰面材质（`finish`）：
 | Name       | 含义     | Enum value |
   | ---------- | -------- | ---------- |
   | `matte`    | 哑光     | 0          |
   | `satin`    | 绸缎材质 | 1          |
   | `polished` | 抛光     | 2          |
   | `rugged`   | 凹凸不平 | 3          |
   | `fabric`   | 编织材质 | 4          |
   | `other`    |          | 255        |

2. 颜色（`color`）：字符串

| Color name | 含义   | RGB value |
| ---------- | ------ | --------- |
| `black`    | 黑色   | `#000000` |
| `navy`     | 藏青色 | `#000080` |
| `green`    | 绿色   | `#008000` |
| `teal`     | 鸭绿   | `#008080` |
| `maroon`   | 栗红   | `#800080` |
| `purple`   | 紫色   | `#800080` |
| `olive`    | 橄榄绿 | `#808000` |
| `gray`     | 灰色   | `#808080` |
| `blue`     | 蓝色   | `#0000FF` |
| `lime`     | 苹果绿 | `#00FF00` |
| `aqua`     | 水蓝色 | `#00FFFF` |
| `red`      | 红色   | `#FF0000` |
| `fuchsia`  | 品红   | `#FF00FF` |
| `yellow`   | 黄色   | `#FFFF00` |
| `white`    | 白色   | `#FFFFFF` |
| `nickel`   | 镍灰色 | `#727472` |
| `chrome`   | 铬灰色 | `#a8a9ad` |
| `brass`    | 黄铜色 | `#E1C16E` |
| `copper`   | 铜色   | `#B87333` |
| `silver`   | 银色   | `#C0C0C0` |
| `gold`     | 金色   | `#FFD700` |

## 工厂数据生成

官方文档：[Factory provisioning in Matter](https://docs.nordicsemi.com/bundle/ncs-latest/page/nrf/protocols/matter/end_product/factory_provisioning.html)

### 生成工厂数据json和hex

打开nrfconnect命令行，进入`modules/lib/matter`:

查看帮助：

```bash
python scripts/tools/nrfconnect/generate_nrfconnect_chip_factory_data.py -h
```

示例：

Linux 版本：

```bash
# 安装生成二维码图片的依赖
python -m pip install -r ./scripts/setup/requirements.nrfconnect.txt

# 创建输出目录
mkdir build_fd

python scripts/tools/nrfconnect/generate_nrfconnect_chip_factory_data.py \
--sn "11223344556677889900" \
--vendor_id 65521 \
--product_id 32774 \
--vendor_name "Nordic Semiconductor ASA" \
--product_name "not-specified" \
--date "2022-02-02" \
--hw_ver 1 \
--hw_ver_str "prerelease" \
--dac_cert "credentials/development/attestation/Matter-Development-DAC-FFF1-8006-Cert.der" \
--dac_key "credentials/development/attestation/Matter-Development-DAC-FFF1-8006-Key.der" \
--pai_cert "credentials/development/attestation/Matter-Development-PAI-FFF1-noPID-Cert.der" \
--spake2_it 1000 \
--spake2_salt "U1BBS0UyUCBLZXkgU2FsdA==" \
--discriminator 0xF00 \
--generate_rd_uid \
--passcode 20202021 \
--product_finish "matte" \
--product_color "black" \
--out "build_fd/my_fd" \
--schema "scripts/tools/nrfconnect/nrfconnect_factory_data.schema" \
--offset 0xf7000 \
--size 0x1000 \
--generate_onboarding \
--overwrite
```

Windows Powershell版本：
```powershell
python scripts/tools/nrfconnect/generate_nrfconnect_chip_factory_data.py `
--sn "11223344556677889900" `
--vendor_id 65521 `
--product_id 32774 `
--vendor_name "Nordic Semiconductor ASA" `
--product_name "not-specified" `
--date "2022-02-02" `
--hw_ver 1 `
--hw_ver_str "prerelease" `
--dac_cert "credentials/development/attestation/Matter-Development-DAC-FFF1-8006-Cert.der" `
--dac_key "credentials/development/attestation/Matter-Development-DAC-FFF1-8006-Key.der" `
--pai_cert "credentials/development/attestation/Matter-Development-PAI-FFF1-noPID-Cert.der" `
--spake2_it 1000 `
--spake2_salt "U1BBS0UyUCBLZXkgU2FsdA==" `
--discriminator 0xF00 `
--generate_rd_uid `
--passcode 20202021 `
--product_finish "matte" `
--product_color "black" `
--out "build_fd/my_fd" `
--schema "scripts/tools/nrfconnect/nrfconnect_factory_data.schema" `
--offset 0xf7000 `
--size 0x1000 `
--generate_onboarding `
--overwrite
```

> 注意，示例中使用的是测试PAI和DAC证书，证书名包含了VID（0xFFF1, 65521）和PID（0x8006, 32774）.
>
> 因此，填写`--vendor_id`和`--product_id`的时候，需和证书保持一致

填写步骤：

1. 填写必选项：
   ```bash
   --sn --vendor_id, --product_id, --vendor_name, --product_name, --date, --hw_ver, --hw_ver_str, --spake2_it, --spake2_salt, --discriminator
   ```

2. 填写factory data在存储器分区中分配的地址和分区大小：

   ```bash
   --offset <offset>
   --size <size>
   ```

3. 填写输出路径与文件名前缀：

   ```bash
   -o <path_to_output_file>
   # 或者
   --out <path_to_output_file>
   ```

   ```bash
   # 记得确保路径是存在的，例如：
   --out "build_fd/my_fd"
   
   # 则需要先存在该路径
   mkdir build_fd
   
   # 最终将生成build_fd/my_fd.json, build_fd/my_fd.hex等等
   ```

4. 填写pascode或者SPAKE2 verifier
   ```bash
   ## 二选一
   
   # 1.（推荐）直接填写passcode，脚本自动算出verifier
   #   这里只是用passcode计算spake2_verifier，并不是把passcode包含到factory_data
   --passcode <pass_code>
   
   # 2. 用外部工具来计算出verifier，见 https://project-chip.github.io/connectedhomeip-doc/scripts/tools/spake2p/README.html
   --spake2_verifier <verifier>
   ```

5. 填写DAC证书
   ```bash
   ## 二选一
   
   # 1.（推荐）直接传入DAC证书，DAC私钥，PAI证书
   #   每台设备的DAC都要确保不同，重新生成
   --dac_cert <path to DAC certificate>.der --dac_key <path to DAC key>.der --pai_cert <path to PAI certificate>.der
   
   # 2. （仅测试用）用外部chip-cert工具自动生成DAC，这里用的是测试PAA自动生成PAI和PAA
   --chip_cert_path <path to chip-cert executable> --gen_certs
   ```
   
6. （可选）同时生成二维码图片和手动配对码

   ```bash
   --generate_onboarding
   ```

   > 注意，这个功能需要安装依赖：
   >
   > ```bash
   > python -m pip install -r ./scripts/setup/requirements.nrfconnect.txt
   > ```

7. （可选）为Amazon Frustration-Free Setup设置rotate-id

   ```bash
   ## 二选一
   
   # 1.提供一个已有id
   --rd_uid <rotating device ID unique ID>
   
   # 2.生成一个id，生成时在日志中打印
   --generate_rd_uid 
   ```

8. （可选）用于验证json格式的schema路径：
   ```bash
   --schema <path to JSON Schema file>
   ```

9. （可选）把passcode包含在facory_data中:
   只有debug log打印配网二维码，或者NFC配网才需要

   ```bash
   --include_passcode
   ```

10. （可选）是否要覆盖上次脚本的输出

    ```bash
    --overwrite
    ```

11. （可选）产品外观材质与颜色
    ```bash
    --product_finish <finish> 
    --product_color <color>
    ```

12. （可选）（仅测试用）生成factory data时，用外部chip-cert工具自动生成一个测试用CD
    ```bash
    --chip_cert_path <path to chip-cert executable> --gen_cd
    ```

> 注意CD不属于factory data

生成完毕后，可以在设置的`--out`路径中找到对应的文件：

```bash
build_fd
├── my_fd.bin
├── my_fd.hex
├── my_fd.json
├── my_fd.png # 配对二维码，可印刷在包装盒上
└── my_fd.txt # 手动配对码和二维码的payload
```

## 工厂数据烧写

```bash
# 烧录完matter固件后，再烧录factory data
nrfutil device program --firmware my_fd.hex
```

