# Text

## 摘要

随着宽带技术以及物联网技术的发展，现在家庭中的智能设备越来越多，无线路由器、网络存储等设备愈加频繁的出现在我们的生活当中。很多这样的设备，其操作系统都是基于一套名为 OpenWrt 的基于 Linux 的嵌入式系统定制而来。该系统拥有开放源代码、兼容平台广泛、高度灵活可定制化等特点，受到很多厂商欢迎，但其构建过程较为繁琐，尤其对于产品研发团队内的部分非技术职位人员来说门槛过高，他们构建用于评估、测试等需求用的环境时会有诸多不便。

本文描述一套用于实现自动构建 OpenWrt 环境的工具，其功能包括自动更新、自动构建 OpenWrt 环境，并可通过基于 Web 的图形化界面对定制过程进行定制，以求降低构建评估测试环境时的繁琐程度。在介绍容器、Web 服务、虚拟化和版本控制工具等相关技术的基础上，探讨如何利用这些技术达到上述目的，并给出综合这些技术后的系统整体解决方案。

关键词：自动构建、容器、Web 服务

## 1 绪论

### 1.1 研究背景和意义

随着宽带技术以及物联网技术的发展，现在家庭中的智能设备越来越多，不仅是很多电视、冰箱之类的白色家电都更多的加入了与网络连接的功能，更多样的工具比如扫地机器人、智能传感器等智能家居设备也越来越频繁的出现在我们的生活中。

很多这样的设备，其操作系统都是从一套名为 OpenWrt 的，基于 Linux 的嵌入式系统定制而来。该系统由包括 Linux 内核、opkg 包管理器、LuCI 管理界面、Busybox 等系统软件、以及一系列应用软件组合而成，兼容包括 Atheros、Qualcomm、MediaTek、BroadCom 等在内的绝大多数常见 SoC。其功能十分强大，且可以根据需求自由裁剪系统模块或增加特定功能；源代码完全开放，授权方式灵活，很多新的智能产品如小米、TP-Link、斐讯、水星等厂商的家庭用无线路由器，使用的都是基于 OpenWrt 深度定制并添加部分私有功能 / 驱动程序的操作系统。

OpenWrt 以上述一系列特点受到很多厂商青睐，使用 OpenWrt 开发智能设备使用的操作系统可以极大加快开发进度。但是产品研发的过程中涉及到一系列不同的参与者，对于部分不了解技术的团队成员来说需要降低他们实际参与开发活动的难度。

本文侧重于解决在基于 OpenWrt 进行项目开发时的一大难点：整体系统的构建。对于一个典型的 OpenWrt 项目，一般由 OpenWrt 原生组件（Linux 内核、LuCI 管理界面等）以及厂商编写的第三方软件（如智能流控、手机控制等）组合而成。测试人员进行测试时需要将需测试的组件或系统模块等的代码更新，然后再构建整个系统，构建完成之后将系统通过 TFTP 等方式烧写至测试用的设备中再进行后续的测试。而其中更新代码、构建整体系统这部分工作较为复杂，对于产品、测试人员来说不够友好。此外，构建环境本身的搭建也同样十分复杂，且构建环境对不同的目标平台无法实现隔离，非常不易于管理和维护。

### 1.2 项目研究目标

本文针对 1.1 节中提出的一系列问题，设计了一套构建工具。这套工具可以让用户以图形化的方式完成整个构建流程，使得用户可以非常轻松的完成上述组件更新以及系统构建的工作，提升工作效率；针对构建环境的运维问题，利用容器等技术对不同的构建环境进行隔离，区分管理。两者结合，使得项目开发综合效率得到显著提升。

### 1.3 本文工作和论文结构

本文主要介绍了这套自动构建系统的开发背景，以及设计和实现的工作，重点探讨了实际设计上的一些问题。

第一章讨论了本系统实现的背景以及期望达到的目标。

第二章介绍了本套系统设计上使用的一系列相关技术，包括 OpenWrt 嵌入式系统、OpenWrt 原构建系统的基础 Kbuild / Kconfig、管理构建环境时使用的 Docker 容器、搭建测试环境时使用的虚拟化相关技术、管理 OpenWrt 代码库以及厂商自有软件仓库使用的版本控制工具 Git，以及这套自动构建工具使用的 Web 后端框架 Django 以及前端框架 Bootstrap。

第三章介绍了本套系统的需求分析，包括可行性、功能性、可用性、安全性、性能等需求。

第四章介绍了整套系统的总体设计方案，包括整套系统的总体架构设计、对 OpenWrt 构建过程中一系列实体的抽象，以及完成构建工作所需的所有步骤。

第五章描述了第四章中所述所有设计的具体实现。

第六章首先介绍了开发过程中使用的工具以及环境，然后提出一些测试用例并展示了测试结果，对结果进行分析和说明。

第七章总结了本系统的功能点，介绍了已经完成的工作并列出了其中不足之处，并对下一步的工作进行介绍。

## 2 相关理论与技术

本章对论文研究中设计的相关理论和技术进行阐述，这些技术包括 OpenWrt 自身、OpenWrt 的原始构建工具集、基于 Docker 的容器技术、虚拟化相关的技术、用于版本控制的 Git、用于呈现用户界面的 Django 和 Bootstrap 框架等。

### 2.1 OpenWrt / LEDE

OpenWrt 是一款针对嵌入式系统设计的基于 Linux 的开源项目，主要被设计用于路由器等网络设备。其主要包括的组件有 Linux 内核、uClibC / musl C 标准库、BusyBox 工具集、opkg 包管理器、LuCI 界面等。OpenWrt 的所有基础组件都针对嵌入式的应用环境进行裁剪以及优化，因此可以运行在很多只有 32MB 内存、4MB Flash 空间的家用路由器上。

OpenWrt 支持超过 50 种不同的硬件体系结构，包括 MIPS、ARM、x86/64 等。市面上最常见的家用路由器一般采用来自 QualComm（Atheros）、BroadCom、MediaTek（RaLink）等公司的基于 MIPS 指令集的方案，这些公司的部分产品也有基于 ARM 指令集的。x86/64 方案则常见于网吧、中小型企业的路由设备中。

OpenWrt 包含强大的路由功能支持：硬件方面，除去上面提到的硬件体系结构的广泛支持外，也支持绝大多数厂商的有线、无线局域网硬件方案，以及常见的 LTE 移动网络方案；支持包括以太网、DSL、ISDN 等的一系列规范；支持 IPv4 和 IPv6；支持动态路由、VPN、QoS、防火墙、NAT、负载均衡、链路叠加等常见路由功能；支持包括 Mesh、WDS 等特性的无线网络功能。

除此之外，OpenWrt 还能通过 opkg 添加其他被 Linux 操作系统直接支持的硬件的支持；包括但不限于打印机、监控摄像头、声卡、外置存储设备等，并可以安装 Samba、PulseAudio、p910nd 等 Linux 上使用的应用软件。这使得 OpenWrt 除了作为路由器使用的操作系统之外，也非常适合其他的嵌入式设备，如网络存储、打印服务器、智能监控摄像头、智能音响等。

OpenWrt 与其他常见的针对家用路由器设计的嵌入式操作系统，如 DD-WRT 等的区别主要在于以下两点：

* OpenWrt 包含一个可以写入的根文件系统。OpenWrt 使用只读和压缩的 squashfs 提供根文件系统，并利用 overlayfs，采取 CoW（写时复制）的方式在只读的根文件系统上叠加一个 F2FS 文件系统。
* OpenWrt 利用包管理器 opkg 管理软件包。OpenWrt 官方提供的软件源中包含超过 3500 个不同的软件包，这使用户可以自由安装卸载软件，对自己的设备进行定制。

LEDE 是 Linux Embedded Development Environment 的缩写。它是 OpenWrt 的一个分支，采取比 OpenWrt 更加激进的开发流程。2016 年 5 月 LEDE 项目从 OpenWrt 拆分出来进行独立开发，之后 OpenWrt 几乎停止了迭代。月一年版之后的 2018 年 1 月，LEDE 与 OpenWrt 项目宣布合并，原 OpenWrt 项目被归档不再开发，LEDE 更名为 OpenWrt，取代原来的 OpenWrt。

### 2.2 OpenWrt 代码仓库、BuildRoot、Kbuild 与 Kconfig

代码仓库在这里指的是 Git 进行版本控制时的代码库。OpenWrt 的代码库使用 Git 进行版本控制，其上运行的第三方软件大多同样使用 Git 进行版本控制，少部分会使用 SVN 等其他版本控制工具。

OpenWrt 的代码库本身包括以下组成部分：

* OpenWrt 原始构建工具 BuildRoot（包括交叉编译工具等）
* OpenWrt 目标集（包含所有 OpenWrt 支持的设备所需的一些配置）
* OpenWrt 基础组件代码库
* OpenWrt 自带的一部分软件包的代码库

一般来说嵌入式设备会使用与其构建环境不同的体系结构，比如 OpenWrt 一般在 x86/64 设备上进行构建，构建后运行在 MIPS / ARM 设备上，这种构建方式被称为交叉编译。OpenWrt 自身的开发环境与构建系统统称为 OpenWrt BuildRoot，这套系统解决了 OpenWrt 构建过程中的一系列问题，如交叉编译所需工具链的集成、应用软件的交叉编译、CMake 等工具的集成、对不同设备映像的封装等。

对于 OpenWrt 来说，由于其原始构建工具以及 SDK 的设计，基础组件和第三方软件包均需按照特定方式在仓库中进行组织，这样才能够正确被 OpenWrt 原始构建工具识别并顺利编译。更新基础组件和第三方软件包同样需要使用 OpenWrt 原始构建工具集，这是因为更新基础组建需要修改构建工具自身依赖的一系列配置项，而正确完成第三方软件包的添加同样需要构建工具更新其软件包缓存。

OpenWrt 自身支持的 Linux 内核版本等配置写在 `include/kernel-version.mk` 这一配置文件中。一般来说 OpenWrt 会同时支持两到三个版本的内核，对于不同的目标平台，会使用不同版本的内核，比如，x86 目标平台一般会选择最新的 LTS（Long Term Support，指受到官方支持时间较长的版本）内核（截止到 2018 年是 4.14）；大多数稍老的智能设备使用的 Atheros 由于其内核中设备的描述使用了 Mach 这一较旧实现的关系仍然只能使用 4.9 版本的内核；支持了 dts 的 MediaTek 还有一些 ARM 平台则可以跟 x86 目标一样使用最新的 4.14 内核。对于部分非常旧的平台如部分 TI 的 ARM 平台则会使用 4.4 内核。一般来说更新的内核在安全性和性能上会有更好的表现，如 4.9 版本内核支持了谷歌开发的 TCP BBR 拥塞控制协议；4.14 内核支持了将部分数据包通过特殊的路径进行转发以增加转发速度的功能，且在 Meltdown / Spectre 这两个严重的安全性问题上得到的修复也是最快的（在这两个漏洞公开的第二天即得到了修复）。

官方自带的基础软件包部分，则与内核采取相似的方式，统一直接放置于仓库中。这些基础软件包只能和仓库同步进行更新。对于大多数嵌入式设备来说稳定是第一要务，因此其中大多数软件包都使用并非最新但是稳定的版本，只有遇到安全问题时会尽快更新；而 LEDE 以及其取代后的 OpenWrt 因为其本身较为激进的开发路线，很多基础软件包也会比较频繁的更新到较新版本。LEDE 选取这样的开发路线带来的好处也很明显，对于例如 Hostapd 这样用来控制无线网卡进行通信的软件，LEDE 可以更快的将新版本中增加的新功能或者应用的一些提升性能的改进合并进来，这样用户可以更快享受到更好的无线网络。

对于其他的应用软件包以及第三方软件包，OpenWrt 将绝大多数应用软件放在单独的仓库中，这些软件直接由社区进行维护，与 OpenWrt 仓库分开进行更新。这些软件大多数会保持与最新版同步，只有一部分受限于 OpenWrt 自身环境限制会使用旧版本，比如 Samba（最新版为 4.x，OpenWrt 仅提供 3.5）和 MySQL（最新版 5.7.x，OpenWrt 仅提供 5.1，不过现在改为使用较新版本的 MariaDB 了）。OpenWrt 官方仓库在 `feeds.conf` 内记录了这些仓库的地址。对于第三方的软件仓库，也可以通过配置代码库中 `feeds.conf` 的方式来添加。

OpenWrt 原始构建工具中的交叉编译工具链也是直接包括在仓库中的。这些编译工具链的版本选择一般来说与自带基础软件类似，也会选用稳定版本，不过由于内核以及所有的软件都需要用这些编译工具链进行编译，因此编译工具链的版本选择会较为复杂。之前 OpenWrt 使用的是 5.x 版本的 gcc 进行编译，内核更新到 4.14 之后则换到了 7.x。

OpenWrt 构建工具使用 Kconfig 配置构建过程中的可选项，如目标平台和软件包等。Kbuild 是 Linux 内核使用的构建工具集，Kbuild 在 GNU Make 的基础上对其 Makefile 进行了功能扩充，使得内核编译过程可以更加高效的完成；Kconfig 则是 Kbuild 使用的配置文件，用于定制 Kbuild 使用的一系列选项。

### 2.3 虚拟化

虚拟化技术是一种资源管理的技术，指将计算机中的资源进行抽象后拆分并重新组合为一个或多个资源组，使用户更好的使用这些计算资源的技术。

虚拟化技术覆盖的层次非常广泛，一般分为五个等级：

![](https://upload.wikimedia.org/wikipedia/commons/3/3a/VT5levels.JPG)

我们这里介绍其中两个等级。

#### 2.3.1 硬件虚拟化

硬件虚拟化指的就是将物理计算机中的资源进行拆分并重新组合为一些虚拟的计算机，这些虚拟计算机拥有与真实计算机类似的功能，并共享物理计算机所有的资源。这里的物理计算机称为宿主机（Host），其上运行的虚拟计算机称为客户机（Guest）。宿主机上运行的用于拆分、重组计算资源的软件被称为虚拟机管理器（Hypervisor）。

硬件虚拟化包括以下两种类别：

1. 全虚拟化（Full Virtualization）：用软件的方式完全模拟一个运行环境。这种方式运行的 Hypervisor 会提供完整的硬件特征，包括完整的体系结构、IO 操作、中断与内存管理等。在这样的环境中运行的代码不需进行任何修改。
2. 半虚拟化（Paravirtualization）：利用宿主机提供的 API 接口模拟运行环境，其上运行的代码需要针对宿主机平台特别定制，通常效率比全虚拟化要高，但是虚拟机的体系结构只能与宿主机保持一致。

很多现代 CPU 都会提供特殊的指令以便加速虚拟化过程，比如 Intel 的 VT-x 和 AMD 的 AMD-V；新一些的 CPU 还会提供对外部设备进行虚拟化的功能，比如 Intel 的 VT-d，利用这些功能可以使虚拟机直接控制宿主机上的部分硬件设备（如显卡、存储控制器、网络控制器等），极大提升硬件虚拟化的效率。现代操作系统均提供利用这些特性进行半虚拟化的支持，如 Windows 的 Hyper-V、Linux 的 KVM 等。一些第三方服务商，如 VMWare，提供的产品也支持利用这些虚拟化特性提高效率。

#### 2.3.2 操作系统级虚拟化

操作系统级虚拟化一般也被称为容器化，是指在操作系统的层面对不同的用户空间进行隔离的技术。被分离的用户空间一般被称为容器。容器中运行的代码只能操作对应容器被分配的资源配额，并且不同的容器之间互相完全不可见。

操作系统级虚拟化与硬件虚拟化相比，其优势在于可以减少在虚拟机上启动操作系统带来的资源消耗。容器内的应用程序直接使用宿主操作系统提供的系统调用，而不需要在虚拟机中启动新的操作系统，并由虚拟机上的操作系统提供用于与虚拟化的硬件进行交互的系统调用，如此可以极大降低启动时间和资源占用。而这也同样导致容器内的操作系统必须与宿主机保持一致，不能像硬件虚拟化那样，在 Linux 宿主机上运行 Windows 虚拟机。

在传统的类 Unix 操作系统中，通过 chroot 的方式可以实现对根文件系统的隔离。而在更新一些版本的 Linux 中，通过 cgroup（Control Group，控制组）和 namespace（命名空间）的方式可以实现对 CPU 核心、内存空间、网络、用户、进程等绝大多数系统资源的隔离。

容器化最初常见于互联网服务商提供的虚拟服务器，如 OpenVZ 等。服务商通过容器化的方式将一台宿主机分割为一系列虚拟机用于出租，这样的收益比起单独出租物理服务器会高一些；现在更常见的应用场景是基于 Docker 的容器化，Docker 将用户程序和对应环境打包为一个容器，以此加快部署。

### 2.4 Docker

Docker 是常见的容器化技术之一，属于上述操作系统级虚拟化的一个比较典型的应用。Docker 目前支持 Windows 和 Linux，不过比较常用的平台还是 Linux。

![](https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Docker-linux-interfaces.svg/440px-Docker-linux-interfaces.svg.png)

Docker for Linux 利用上述的 cgroup、namespace 实现用户空间隔离与资源分配，使用 NetFilter 组件实现不同的网络 namespace 之间的通信。为了提高安全性，避免容器隔离机制失效，还会使用 SELinux、AppArmor 等访问控制工具严格控制每一个容器的行为。

Docker 隔离根文件系统的方式比较特别：除了使用 chroot 隔离之外，Docker 的文件系统还会使用支持联合挂载的文件系统，如 OverlayFS、ZFS、btrfs 等来实现，并借此实现了容器的版本控制。每一个版本在 Docker 中被称为“层”，对某一层的修改可以被记录下来成为新的“层”。启动容器时通过联合挂载的方式，提供一个合并了所有“层”的视图给容器内的应用程序。

![](https://docs.docker.com/storage/storagedriver/images/container-layers.jpg)

除此之外，Docker 还可以将容器（所有的“层”）打包为映像，并进行快速部署与分发。Docker 还提供 Swarm 和 Compose 两个工具，Swarm 用于管理一组容器，Compose 用于通过脚本来进行自动的容器构建。

### 2.5 版本控制工具 Git

版本控制是指对计算机系统中的文档、程序或其他信息集合的修改的管理。这些修改会由被称为“版本号”的编号进行标记，如最早版本的文件被称为版本 1，进行过第一次修改后的文件被称为版本 2。每一个版本都会有其对应的修改时间以及修改人，且不同的版本可以互相比较、恢复，对特定类型的文件还可以进行合并。

对于一个文件，可能会出现两个人分别进行了不同的修改的情况，这种情况被称为分支。不同的分支可以通过一些方式进行合并。

Git 是一个比较典型的用于进行版本控制的工具，最初是用来协助开发 Linux 内核的。它是一个分布式的版本控制工具，也就是说每一台计算机上都会有整个代码库的一个副本。

Git 的特点有：

* 对分支及合并的完善支持。Git 包含一系列工具用于在版本和分支之间进行导航。
* 支持分布式的开发。每一个开发者都有某一代码库的完整副本。
* 与现有系统和通讯协议的兼容。Git 可以使用 http、ftp、ssh 等协议在不同的设备之间进行通信以交换版本库。
* 对大规模项目的高效支持。
* 对版本的完整性检查。
* 多种合并分支的策略。

### 2.6 Django 与 Tornado

Django 是一个 Python 编写的 Web 框架，遵循 MVC（Model - View - Controller）的模式。Django 的主要目标是降低开发网站的复杂性，因此其包含丰富的组件以帮助开发者快速建立网站。

Django 的核心组件包括：

* ORM（对象 - 关系映射）。这是用于将关系型数据库中的数据转换为 Python 中的对象，以便使用面向对象的方式来操作这些数据。
* 模版引擎。用于将数据渲染成 HTML 页面。
* 基于正则表达式匹配的 URL 分发器。

除此之外还有一些其他的帮助用户快速开发的工具：

* 轻量级的 Web 服务器，用于开发与测试。
* Web 表单处理器。
* 缓存模型。
* 中间件支持。
* 国际化支持，包含多语言以及本地化支持。
* 序列化、反序列化工具，用于 Django 数据对象和 JSON / XML 的相互转换。
* 集成的 Python 单元测试工具。
* 用户身份验证、权限管理模块。
* 可视化的管理员界面。
* 安全检查工具，可以防御 CSRF（跨站攻击）、XSS（跨站脚本）、SQL 注入等典型的 Web 攻击策略。

Tornado 是一个与 Django 功能类似的 Web 框架，不过他们在设计风格上有很大区别。Tornado 并不自带 ORM，也没有 Django 提供的丰富的用户验证、可视化管理界面等，仅包含模版引擎与 URL 分发器。Tornado 的优势在于对异步 I/O 的支持，使得它的执行效率比 Django 要好很多，并且对 WebSocket 的支持也更好。

### 2.7 JQuery 与 Bootstrap

我们知道，对于典型的 B/S 架构的应用程序，呈现给用户的是一个在浏览器中显示的 Web 页面。对于其中的一些逻辑需要 Javascript 来进行编写。而不同浏览器提供的 Javascript API 往往有所区别。JQuery 是用于简化在浏览器使用 Javascript 并消除不同浏览器之间差异的一套工具，其特殊设计的语法使得操作浏览器中的元素、创建动画、发送 Ajax 请求等变得简单很多。

JQuery 的核心是一个对 DOM（文档 - 对象模型）的抽象。DOM 是一个用于表现浏览器中元素结构的树形结构，JQuery 简化了操作 DOM 的流程。JQuery 还提供了其他的一些工具，使得开发者可以通过事件来处理用户点击浏览器中元素的操作。同样 JQuery 还提供了对 XMLHttpRequest（Ajax）的封装，降低了开发者使用 Ajax 的复杂性。

Bootstrap 是由 Twitter 推出的基于 JQuery 开发的前端框架，包含一系列元素组件，如表单、按钮、导航组件以及其他常用的 Web 元素，支持响应式布局。Bootstrap 以其方便使用的栅格布局工具和简洁清新的设计风格受到大量 Web 开发者的欢迎。

### 2.8 本章小结

本章将项目中重点采用的技术和方案进行了介绍，首先介绍了 OpenWrt 以及其原始构建工具集，接着分别介绍了本项目实施中使用的一系列支撑技术，包括虚拟化技术、容器技术、版本控制工具以及 Web 框架等。

## 3 需求分析

本章对所开发的自动构建工具的需求进行讨论分析。

### 3.1 可行性分析

开发此自动构建工具的主要目的在于降低部署新构建环境、构建 OpenWrt 系统的复杂性。这对这一构建工具的要求在于：

* 能够将 OpenWrt 原始构建工具的使用门槛尽可能通过图形化界面等方式降低，将更新代码、构建等步骤尽可能自动化完成。
* 能够利用本工具快速部署新的构建环境，进行构建操作。

#### 3.1.1 技术可行性

通过一系列调研，我们发现可以使用 Docker 打包整体构建环境，实现构建环境的快速复制和快速部署；OpenWrt 构建环境采用 Git 进行版本控制，而自动化操作 Git 在业界已有多种成熟方案可以采用。对于用户界面部分，则可以使用常见的 Web 前后端框架来进行开发，给用户提供浏览器中的界面，进一步降低用户使用该自动构建系统的门槛。经过一系列评估，我们认为开发这套系统在技术上有一定的可行性。

#### 3.1.2 经济可行性

构建本系统的主要目标就是通过降低构建过程复杂性提升总体开发效率。产品评估测试人员可以非常快捷的通过该环境获得开发人员提交的最新版本，并选择相关部分进行快速构建和测试，将之前这些步骤所需的一系列复杂操作进行简化以便将更多的精力投入到评估与测试工作中。

该系统运行时仅需一台额外服务器部署该系统，原有的构建用服务器仅需配置 Docker 环境即可接入该系统内进行控制，并不会过多的消耗原有的服务器资源。同时利用 Docker 容器实现构建环境隔离，原有构建服务器可以同时进行多项构建任务而不会导致构建工作互相影响，提升了构建服务器的利用率。

经过考虑，开发并应用该自动构建系统有较高的投入产出比，在经济上有可行性。

#### 3.1.3 操作可行性

该系统目标为解决构建过程过于复杂的问题，设计时便会考虑本系统的易用性。仅需对现有产品评估测试人员进行十分简单的培训即可让这些团队成员快速掌握该系统的使用方案。且该系统不会修改原有构建环境，在该系统无法使用时，产品测试人员仍可以使用旧有构建流程完成构建工作，不会造成严重的影响，因此在操作上有可行性。

### 3.2 功能性需求

本系统应该包括的功能有：

1. 对构建容器的创建、修改、删除操作；
2. 对于每一个构建容器：
    1. 更新容器内的 OpenWrt 核心代码；
    2. 管理和更新容器内的软件包库；
    3. 给用户提供图形化的构建配置界面，让用户以所见即所得的方式配置整个构建流程；
    4. 在容器内完成软件包和系统的构建工作，并将构建结果及系统映像等返回给用户；
    5. 在上述步骤出现错误以至于无法继续时，可以给用户提供必要的信息以帮助用户解决问题。
3. 对于特定的体系结构，可以启动虚拟环境，对构建结果进行测试。

### 3.3 可用性需求

可用性需求是指一个系统能正常对外服务的程度，一般用一定时间内正常运行时间的百分比表示。本系统应达到 99.9% 的可用性。

### 3.4 安全性需求

本系统本身不包含对敏感信息的处理，但是会操作系统中需要特权的一些组件，如虚拟化使用的虚拟机监视器，以及 Docker 服务守护进程等，因此系统需要拥有足够的安全保护措施，防止恶意攻击者通过本系统获取对这些特权组件的访问，进而控制整个系统。

### 3.5 性能需求

对于本系统向各个构建服务器以及其上构建容器发送的构建命令，系统应在 1s 内将构建命令传递到对应 Worker 并使其开始执行任务；构建流程的速度取决于构建服务器本身的性能以及同时构建任务的数量，本构建系统并不直接干预构建流程。

### 3.6 本章小结

本章针对本构建系统的需求，首先从技术、经济和操作三个方面描述了可行性分析的过程，然后针对使用场景分析了功能需求。最后从可用性、安全性、性能三个非功能性的需求描述了对本构建系统期望的特性。

## 4 设计方案

本章详述本自动构建系统的设计方案。设计方案首先包括整体架构，然后是对本系统中涉及到的一系列组成部分进行详细描述，以及为了满足需求分析中出现的需求进行的详细设计。

### 4.1 架构方案

本构建系统的架构方案如下图所示：

```
user -> browser -> ledeforge -> docker-daemon -> local docker registry (pull images from local registry)
user -> browser -> ledeforge -> docker-daemon -> remote docker repository (build images by compose)
user -> browser -> ledeforge -> docker-daemon, docker-daemon (manage containers)
user -> browser -> ledeforge -> docker-daemon -> container, container (connect to container for tasks)
user -> browser -> ledeforge -> docker-daemon -> container -> remote git repository (update code by git)
user -> browser -> container -> ttyd (direct access to containers)
```

该架构方案是：用户通过浏览器操作本构建系统；本构建系统连接到对应构建服务器上的 Docker 服务进行容器的构建或者拉取等操作；本构建系统通过 Docker 服务连接到对应容器进行代码更新或者构建操作；对应容器启动时会在容器内启动一个 Worker 负责与本构建系统的通讯，同时这个 worker 会启动一个供用户直接访问的命令行界面，方便用户直接操作构建环境或解决自动构建过程中可能出现的问题。为了快速部署新的构建容器，平台侧还可以自行使用 docker-compose 生成构建容器并将其推送至本地的 Docker Registry 供构建服务器拉取。

### 4.2 容器内的构建 Worker

Worker 负责在构建容器中处理所有任务，因此也是直接与 OpenWrt 原始构建环境直接进行交互的部分。除此之外，Worker 还需要能够满足用户界面实现的一系列辅助功能。

#### 4.2.1 管理容器生命周期

对于 Docker 来说，启动容器时运行的进程的生命周期就是这个容器的生命周期。本工具将构建容器的启动进程直接设置为此 Worker，平台要求启动容器，容器启动时也就代表着 Worker 开始运行；平台要求关闭容器，则向 Worker 发送终止命令，Worker 终止，容器便会关闭。

#### 4.2.2 支撑平台侧 Kconfig 界面

Kconfig 界面是用于对 OpenWrt 构建过程进行配置的界面，在这里可以配置 OpenWrt 构建过程中的所有可选项。

容器内的 Worker 需要有能够解析 OpenWrt 原始构建环境中相关配置文件的能力，并将这些数据进行初步处理后发送至前端，前端利用这些数据呈现用户界面。用户在前端完成配置之后，前端将相关配置发回后端 Worker，Worker 可再将数据转换为 OpenWrt 原始构建环境可以解析的构建配置。

#### 4.2.3 处理代码更新流程和构建流程

OpenWrt 仓库的代码更新实际上也就是 Git 仓库从远端拉取新的提交的过程。Worker 通过直接进行一些 Git 操作，即可完成更新。用户如果修改了构建环境中的部分文件也没有关系，Worker 可以监测到并使用 Git 的 Stash 功能对这些操作进行暂存，在更新完成后再将暂存的修改写回。这个过程中遇到冲突的话，则会提示用户使用 4.2.4 中提到的终端来协助处理。

第三方软件包代码的更新、管理流程，以及构建流程，都是通过运行一系列命令完成，用户需要能够看到这些命令的输出。

Worker 将这些命令封装起来，使得这些命令以 Worker 的子进程的方式运行，并将这些命令的输出重定向后暂存于 Worker 内部的队列内，前端可以随时从队列内部取出数据并呈现给用户。如果有需求的话，也可以将这些输出重定向到日志文件以便后续检查分析使用。

#### 4.2.4 支撑平台侧的 xterm 终端界面

当构建出现问题的时候需要有方便的访问容器以解决问题的方法，因此 Worker 要有能够提供控制台访问的能力。

Worker 中的功能包括了与 xterm.js 交互所需的一些功能。Worker 会开启一个 TTY 并将其输入输出重定向至前端，前端可以得到 TTY 中的字节流，经过 xterm 处理后显示出来。用户在终端中输入的字符也经过 xterm 处理后发送到 Worker。为了优化体验，避免轮询带来的延时，本平台在这里使用了 Websocket 进行传输。

#### 4.2.5 给平台侧提供必要的仓库信息

Worker 还需要给平台提供一些与仓库相关的数据，例如：

* 当前 OpenWrt 仓库的最新提交 ID、分支以及版本
* 可选内核的版本
* 当前配置选定的构建目标平台

这些配置均可通过解析仓库内配置文件的内容取得。

### 4.3 平台侧的主体设计

本自动构建工具的设计上将整个构建环境放入容器中。考虑到本工具与构建服务器的一对多关系，以及构建服务器与构建环境容器的一对多关系，需要通过（服务器地址，容器 ID）组合才能够唯一定位一个容器。

为了便于使用 / 查询，对于每一个构建容器，我们保存一个用户自定义的名称，并暂存 4.2.5 中所述的容器内构建仓库的一些属性。这些配置可以在用户请求更新时，在容器内完成更新操作后返回给本自动构建工具，以保持本构建工具中存储的信息与容器内信息一致。构建平台自行维护一个数据库，用来将这些数据持久化存储。

一般来说构建服务器应当是保持运行的，但其上的容器则并不需要一直保持运行，只在需要时通过启动对应容器使容器处于可以运行的状态，然后再由本构建平台与容器内的构建 Worker 进行通信即可。构建工作完成后，亦可在平台侧清理、关闭容器以释放资源。

为了方便构建平台快速部署新的构建容器，平台自身还需要拥有自行构建一个构建容器并将生成的映像推送至本地的 Docker Registry 的能力。

### 4.4 平台侧的用户界面

由于本自动构建工具包含比较多的配置项目，因此会有不同的展示方式。

#### 4.4.1 Kconfig 界面

为了方便起见，本工具利用构建容器中的 Worker 对所有配置进行解析，并将解析后的结构处理为 JSON 这一通用数据结构发送到前端。前端则利用 Bootstrap 提供的组件搭配 JQuery 实现整个界面的可视化，利用 JQuery 处理用户的点击等事件。这些步骤处理完成之后，前端再生成对应的配置文件，并将其传回给构建容器中的 Worker。

#### 4.4.2 控制台回显界面

整个构建过程都需要用户能够查看到日志，方便跟进构建过程以及处理构建过程中产生的问题。

为了将构建过程中控制台输出的内容及时呈现给用户，我们使用了 Ajax 定时轮询的方式，间隔一定时间从 Worker 中取回构建环境的输出，并展示在前端呈现给用户。

#### 4.4.3 xterm 界面

当构建出现问题的时候需要有方便的访问容器以解决问题的方法。经过一定调研，我们使用 xterm.js 与容器中的 Worker 搭配，给使用者在浏览器中直接操作容器的能力。

xterm.js 是一个在浏览器中运行的模拟终端。将其与运行在容器中的 Worker 搭配，即可给用户呈现一个标准的终端。用户可使用这个终端解决构建过程中遇到的各种问题。它利用 WebSockets 与 Worker 进行通信。

#### 4.4.4 其他界面

其他界面可以较为简单的使用 Bootstrap 提供的一系列组件，经过调研，Bootstrap 提供的组件库足够满足需求。

### 4.5 针对部分体系结构的测试环境

由于 OpenWrt 项目的开发很多时候集中在其上应用软件的开发，而这些应用软件一般不需要依赖过多硬件特性，因此可以在虚拟化的环境中运行 OpenWrt 系统，正确配置环境的网络连接即可在其上进行应用软件相关测试。

考虑到虚拟化环境构建的难易程度，以及半虚拟化这一技术带来的运行速度提升以及资源消耗的减少，本工具利用 qemu 构建虚拟化的 x86/64 环境，并将其串行接口映射为 4.4.3 中 xterm 相关技术搭建的控制台，这样用户可以像是使用在设备开发板上通过 UART 连接得到的控制台一样使用这个虚拟环境中的控制台，还可以节省烧写开发板 Flash 等流程消耗的时间。另外，qemu 可以对其虚拟化的设备运行的网络环境进行详细的定制，使得用户可以模拟多个不同的典型网络环境，并在其中完成对应应用软件的测试，如此可大大节省测试流程中切换不同网络环境消耗的时间。

### 4.6 本章小结

本章详细介绍了本自动构建平台的设计方案，首先介绍了本平台的架构方案，然后针对架构中各组成部分，分别阐述了所需完成的任务，以及完成对应功能需求所需的技术方案。

## 5 具体实现

根据第四章的自动构建系统的设计方案，初步完成了本系统的开发。本章详细介绍本自动构建工具的实现细节，依次对架构中的各大组成部分以及其实现细节进行介绍。

### 5.1 构建环境 Worker

Worker 是一个使用 Tornado 框架开发的 Web 应用，运行于容器内，负责管理容器的生命周期，以及提供容器与平台交流的接口，完成平台发来的更新、构建、开启控制台、销毁容器等命令。

Worker 包含的功能如下：

* process <- exec <- update_code, update_packages, make
* process <- kill
* process <- get_output
* terminal <- create, get, delete
* kconfig_session <- load_config, save_config, default_config

平台通过 HTTP 请求的方式与 Worker 进行通信，传递数据的格式使用 JSON。

#### 5.1.1 运行子进程以及标准输入输出的重定向

Worker 的任务中，最关键的是对 OpenWrt 原始构建工具的封装。用户仍然需要看到这些命令的执行结果，因此需要 Worker 能够运行子进程并完成对其输入输出的重定向，以将其执行结果进行持久化或发送至平台侧。

设计 `worker.ProcessManager` 类，用于此类任务的抽象，这些方法利用 Tornado 提供的 `Process` 类，在其上进行封装，以利用 Tornado 本身的异步特性，实现运行速度的提升。

* `__init__(prefix)` 该类的构造函数。创建 `processes` 查找表，用于记录 PID 到对应 `tornado.Process` 类实例的对应关系。
    * `prefix` 在 `path` 前需要添加的前缀，用于完成切换身份（`su -c builduser`）等任务。
* `start(path, params=None，stream=False)` 用于初始化 `tornado.Process` 类的实例。运行程序，返回 PID，根据 `stream` 的值对输出进行重定向。
    * `path` 可执行程序的完整路径。 
    * `params` 附加给可执行程序的参数。
    * `stream` 是否等待程序运行结束。为 `True` 时，启动可执行程序后开启管道，将输出重定向至管道，然后返回给用户管道的引用；为 `False` 时，启动可执行程序后，将输出重定向至某一临时区域，等待可执行程序退出后将临时区域中的内容返回给用户。
* `kill(pid)` 杀死进程及其所有子进程，仅在 `stream` 为 `True` 时有效。
    * `pid` 进程 ID
* `get_output(pid)` 生成器（`Generator`）。`yield` 出非 `stream` 时程序的全部输出，或 `stream` 时管道内的全部内容，同时清空管道。
    * `pid` 进程 ID
* `__del__()` 相当于该类的析构函数。检查 `start()` 创建的进程是否正常退出，未退出则调用 `kill()`；清理管道或临时区域。

设计 `worker.ProcessHandler`、`worker.ProcessAccessHandler`、`worker.ProcessManageHandler` 三个 View 类，用于处理 HTTP 请求。`worker.ProcessHandler` 是后两个 View 类的基类。`worker.ProcessManager` 提供的对应路由规则见下表：

| HTTP 路由 | HTTP 动作 | ProcessManager 模块中的方法 | 处理使用的 View 类 |
|-----------|-----------|----------------------------|-------------------|
| `/process` | GET | `process_manager.processes.items()` | `worker.ProcessManageHandler` |
| `/process` | POST | `process_manager.start()` | `worker.ProcessManageHandler` |
| `/process/<int:pid>` | GET | `process_manager.processes.__getitem__()` | `worker.ProcessAccessHandler` |
| `/process/<int:pid>/output` | GET | `process_manager.get_output()` | `worker.ProcessAccessHandler` |
| `/process/<int:pid>/kill` | POST | `process_manager.kill()` | `worker.ProcessAccessHandler` |

#### 5.1.2 实现模拟控制台

设计 `worker.TerminalManager` 类，用于对模拟控制台的封装。这些方法利用基于 Tornado 的 Terminado 实现与 xterm.js 的对接。

* `__init__(tm, command_prefix)` 本类的构造函数。
    * `tm` 一个 `terminado.NamedTermManager` 实例，在 Worker 启动时创建。
    * `command_prefix` 所有运行命令的前缀，用于完成切换身份（`su -c builduser`）等任务。
* `create(command)` 创建一个 Terminal，步骤包括开启一个 `tty`，开启一个子进程（`command`）并将新 `tty` 的输入输出与新的子进程链接，最后返回控制台的 id。
    * `command` 本控制台的启动命令，默认为 `bash`。
* `list()` 返回所有控制台的 id 以及启动命令列表。
* `__del__()` 相当于本类的析构函数。关闭所有的控制台，释放资源。

设计 `worker.TerminalHandler`、`worker.TerminalAccessHandler`、`worker.TerminalManageHandler` 三个 View 类，用于处理 HTTP 请求。`worker.TerminalHandler` 是后两个 View 类的基类。

为了让用户在浏览器中正确的使用终端，准备 `terminal.html` 模版文件用于在浏览器中呈现 xterm.js 控制台。页面加载时，初始化一个 xterm 的 `Terminal` 对象的实例，并初始化 WebSocket 连接以正确完成与服务端的通信。为了正常响应用户缩放浏览器的动作，改变终端的大小，还需要监听浏览器发出的 `window.onresize` 事件，并及时将缩放后的大小传回给服务端，服务端再按照客户端给出的大小调整终端的尺寸。

除了模版之外，还需要在容器中准备模拟控制台需要的 xterm.js 所需静态文件，并配置 Tornado 的静态文件路径，以确保可以正确获得静态文件。

`worker.TerminalManager` 提供的对应路由规则见下表：

| HTTP 路由 | HTTP 动作 | TerminalManager 模块中的方法 | 处理使用的 View 类 |
|-----------|-----------|----------------------------|-------------------|
| `/terminal` | POST | `terminal_manager.create()`| `worker.TerminalManageHandler` |
| `/terminal` | GET | `terminal_manager.list()` | `worker.TerminalManageHandler` |
| `/terminal/<string:id>` | GET | `terminal_manager.tm.get_terminal()` | `worker.TerminalAccessHandler` |
| `/terminal/ws/<string:id>` | WebSocket | `terminal_manager.tm.get_terminal()` | `worker.TerminalAccessHandler` |

#### 5.1.3 获得 OpenWrt 仓库基本信息、更新 OpenWrt 代码、软件包

更新代码与软件包通过执行 OpenWrt 原始构建环境中的一组命令完成。

设计 `worker.RepositoryManager` 类用于更新 OpenWrt 代码以及进行其他相关操作。

* `__init__()` 本类的构造函数。
* `branch()` 返回当前分支。
* `tag()` 返回 OpenWrt 版本标签。
* `head_commit_id()` 返回最新的 Commit 的 id。
* `lede_version()` 返回 OpenWrt 版本号。
* `lede_kernel_version()` 返回当前 OpenWrt 版本支持的所有内核的版本号。
* `serialize()` 收集上述信息，序列化为 JSON 后返回。
* `update_code()` 更新 OpenWrt 代码。返回一个 `ProcessManager` 中的 PID。
* `amend_customizations()` 更新仓库顶端的 `Customizations` Commit。返回一个 `ProcessManager` 中的 PID。
* `switch_branch(branch_name)` 切换分支。返回一个 `ProcessManager` 中的 PID。
    * `branch_name` 要切换到的目标分支。

设计 `worker.PackageManager` 类用于管理 OpenWrt 软件包。

* `__init__()` 本类的构造函数。
* `update_feeds()` 更新 feeds.conf 中定义的软件源。返回一个 `ProcessManager` 中的 PID。
* `install_feeds()` 将更新后的 feeds 软件源安装到仓库中，以便后续构建使用。返回一个 `ProcessManager` 中的 PID。
* `lede_packages(keyword=None)` 获得软件包列表。
    * `keyword` 搜索关键字。

设计 `worker.RepositoryHandler` 与 `worker.PackageHandler` 两个 View 类。

`worker.RepositoryManager` 提供的对应路由规则见下表： 

| HTTP 路由 | HTTP 动作 | RepositoryManager 模块中的方法 | 处理使用的 View 类 |
|-----------|-----------|----------------------------|-------------------|
| `/` | GET | `repository_manager.serialize()`| `worker.RepositoryHandler` |
| `/?action=update_code` | POST | `repository_manager.update_code()` | `worker.RepositoryHandler` |
| `/?action=amend_customizations` | POST | `repository_manager.amend_customizations()` | `worker.RepositoryHandler` |
| `/?action=switch_branch` | POST | `repository_manager.switch_branch()` | `worker.RepositoryHandler` |

`worker.PackageManager` 提供的对应路由规则见下表：

| HTTP 路由 | HTTP 动作 | PackageManager 模块中的方法 | 处理使用的 View 类 |
|-----------|-----------|----------------------------|-------------------|
| `/packages/?keyword=<string:keyword>` | GET | `package_manager.lede_packages()` | `worker.PackageHandler` |
| `/packages/?action=update_feeds` | POST | `package_manager.update_feeds()` | `worker.PackageHandler` |
| `/packages/?action=install_feeds` | POST | `package_manager.install_feeds()` | `worker.PackageHandler` |

#### 5.1.4 管理构建流程

设计 `worker.BuildManager` 类用于控制构建流程。

* `__init__` 本类的构造函数。
* `clean()` 清理上次构建的结果，保留 OpenWrt 原始构建工具编译出来的工具链。返回一个 `ProcessManager` 中的 PID。
* `dirclean()` 清理上次构建的结果，同时清理 OpenWrt 原始构建工具编译出来的工具链。返回一个 `ProcessManager` 中的 PID。
* `make(params)` 根据提供的参数启动构建进程。返回一个 `ProcessManager` 中的 PID。
    * `params` 构建使用的参数。

设计 `worker.BuildHandler` View 类。`worker.BuildManager`  提供的对应路由规则见下表：

| HTTP 路由 | HTTP 动作 | BuildManager 模块中的方法 | 处理使用的 View 类 |
|-----------|-----------|----------------------------|-------------------|
| `/build?action=clean` | POST | `build_manager.clean()`| `worker.BuildManager` |
| `/build?action=dirclean` | POST | `build_manager.dirclean()`| `worker.BuildManager` |
| `/build?action=make&params=<string:params>` | POST | `build_manager.make()`| `worker.BuildManager` |

#### 5.1.5 Kconfig 接口

设计 `worker.KconfigManager` 类，用于提供设置 Kconfig 的接口。

* `__init__(makefile)` 本类的构造函数，加载 Kconfig 配置文件。
    * `makefile` Makefile 文件的路径。
* `get_tree()` 获得当前 Kconfig 配置文件的配置树。
* `find(keyword)` 搜索配置树，查找 symbol。
    * `keyword` 搜索关键字。
* `set_symbol_value(symbol, value)` 修改 Kconfig 中某一 symbol 类型选项的值。
    * `symbol` Symbol 名称。
    * `value` 要设置的值。
* `set_choice_value(choice, value)` 修改 Kconfig 中某一 choice 类型选项的值。
    * `choice` Choice 选项名称。
    * `value` 要设置的值。
* `set_value(symbol_type, symbol, value)` 修改 Kconfig 中某一 symbol 或 choice 类型选项的值。
    * `symbol_type` 决定 `set_value` 调用 `set_choice_value` 或者 `set_symbol_value`。
    * `symbol` Symbol 或 Choice 名称。
    * `value` 要设置的值。
* `load_config(filename)` 加载配置文件，按照配置文件的值修改 symbol。
    * `filename` .config 文件的路径。
* `save_config(filename)` 保存配置文件。
    * `filename` .config 文件的路径。

设计 `worker.KconfigHandler` View 类。`worker.KconfigManager`  提供的对应路由规则见下表：

| HTTP 路由 | HTTP 动作 | KconfigManager 模块中的方法 | 处理使用的 View 类 |
|-----------|-----------|----------------------------|-------------------|
| `/config` | GET | `kconfig_manager.get_tree()`| `worker.KconfigHandler` |
| `/config?keyword=<string:keyword>` | GET | `kconfig_manager.find()`| `worker.KconfigHandler` |
| `/config` | POST | `kconfig_manager.set_value()` | `worker.KconfigHandler` |
| `/config?action=load&filename=<string:filename>` | POST | `kconfig_manager.load()`| `worker.KconfigHandler` |
| `/config?action=save&filename=<string:filename>` | POST | `kconfig_manager.save()`| `worker.KconfigHandler` |

#### 5.1.6 管理测试环境

设计 `worker.TestEnvManager` 类，用于管理测试环境。

* `__init__()` 本类的构造函数。
* `create(image_file, image_config, network_config)` 启动 QEMU 虚拟机，并创建一个 Terminal 用于用户操作。返回 Terminal 的 id。
    * `image_file_path` OpenWrt 构建出的映像的路径，运行前需要对映像进行解压缩。
    * `image_config` 启动映像设置，如模拟使用的驱动程序等。
    * `network_config` 网络设置，默认使用 QEMU 自带的 NAT 模式，可通过此参数设置为 Bridge 模式，更接近实际的应用环境。
* `list()` 获取所有正在运行的测试环境的列表。

设计 `worker.TestEnvHandler` View 类。`worker.TestEnvManager` 提供的对应路由规则见下表：

| HTTP 路由 | HTTP 动作 | TestEnvManager 模块中的方法 | 处理使用的 View 类 |
|-----------|-----------|--------------------|-------------------|
| `/testenv` | GET | `testenv_manager.list()`| `worker.TestEnvHandler` |
| `/testenv` | POST | `testenv_manager.create()`| `worker.TestEnvHandler` |

### 5.2 平台侧 Manager

Manager 是一个 Django 开发的 Web 应用，负责创建和管理所有的构建容器。Manager 通过维护自己的数据库记录所有的构建环境以及 Docker Registry 的配置信息。

#### 5.2.1 维护 Docker Registry

为了便于快速创建构建容器，需要设置本地或远程 Docker Registry，将构建容器打包为映像并推送到 Registry 上，之后在 Docker Endpoint 上可以快速从 Registry 上拉取映像，可以节省使用 Docker Build 重新生成构建容器映像消耗的时间。

设计数据表 `docker_registries` 存储 Docker Registry 信息：

| 列名 | 数据类型 | 含义 | 默认值 |
|------|---------|------|-------|
| `id` | `BIGINT` | 主键 ID | 自增 |
| `name`| `VARCHAR(64)` | 自定义的 Docker Registry 名称 | `-` |
| `connection_string` | `VARCHAR(255)` | Docker Registry 连接字符串 | `"http://localhost:3000"` | 

在 Django 中设计对应的 View 类 `Manager.DockerRegistryView`，并添加模版以供用户实现对 `docker_registries` 表的 CRUD 操作。

#### 5.2.2 连接 Docker Endpoint

Manager 需要维护所有构建服务器的连接信息，连接到 Docker Endpoint 后才能够与构建容器中的 Worker 进行通信。

设计数据表 `docker_endpoints` 存储 Docker Endpoint 连接字符串信息：

| 列名 | 数据类型 | 含义 | 默认值 |
|------|---------|------|-------|
| `id` | `BIGINT` | 主键 ID | 自增 |
| `name`| `VARCHAR(64)` | 构建服务器名称 | `"localhost"` |
| `connection_string` | `VARCHAR(255)` | Docker Endpoint 连接字符串 | `"tcp://localhost:2379"` | 

通过连接字符串即可连接到对应的 Docker Endpoint，然后可以通过调用 Docker API 的方式完成拉取映像并创建容器的过程。

在 Django 中设计对应的 View 类 `Manager.DockerEndpointView`，并添加模版以供用户实现对 `docker_endpoints` 表的 CRUD 操作。

| HTTP 路由 | HTTP 动作 | DockerEndpointView 类中的方法 | 方法含义说明 | 
|-----------|-----------|--------------------|-------------------|
| `/endpoint` | GET | `docker_endpoint_view.list()`| 获取现有的所有 Docker Endpoint | 
| `/endpoint` | POST | `docker_endpoint_view.create()`| 增加一个新的 Docker Endpoint |
| `/endpoint/<int:id>` | PUT | `docker_endpoint_view.edit()`| 修改 Docker Endpoint 的信息 |
| `/endpoint/<int:id>` | DELETE | `docker_endpoint_view.delete()`| 删除对应的 Docker Endpoint |

#### 5.2.3 使用 Docker Build 生成构建容器

生成构建容器映像的操作可以在任何一个 Docker Endpoint 上完成。利用 Docker API 控制 Docker Build，然后将生成的映像推送到 Docker Registry 即可。

在进行 Build 前，需要准备 `DockerFile` 文件，该文件负责告知 Docker Endpoint 如何进行构建。本平台使用的 `DockerFile` 从 Ubuntu 基础映像开始，分别完成初始工具链安装、OpenWrt 代码仓库创建、Worker 相关代码安装、创建 builduser 用户、配置容器启动行为等五个步骤，最终生成适合本平台使用的构建容器。

在 View 类 `Manager.DockerEndpointView` 上添加用于生成构建容器以及推送到 Docker Registry 的方法，并添加模版使用户可以进行对应操作。

| HTTP 路由 | HTTP 动作 | DockerContainerView 类中的方法 | 方法含义说明 |
|-----------|-----------|--------------------|-------------------|
| `/endpoint/<int:id>/build/` | POST | `docker_endpoint_view.build()`| 使用 Docker Build 生成新的构建容器 |
| `/endpoint/<int:id>/push/` | POST | `docker_endpoint_view.push()`| 将一个构建容器的映像推送到 Registry |

#### 5.2.4 维护构建容器列表

连接到 Docker Endpoint 后，还需要确定其上哪些容器是本平台使用的，因此需要维护构建容器信息。

设计数据表 `docker_containers` 存储容器信息：

| 列名 | 数据类型 | 含义 | 默认值 |
|------|---------|------|-------|
| `id` | `BIGINT` | 主键 ID | 自增 |
| `name`| `VARCHAR(64)` | 构建容器名称 | `-` |
| `endpoint_id` | `BIGINT` | `docker_endpoints.id` 的外键 | `-` |
| `container_id` | `VARCHAR(64)` | Docker 容器 ID | `-` |
| `data` | `TEXT` | 容器详情，`worker.RepositoryManager.serialize()` 的值 | `-` |

在 `docker_containers` 表中插入新行的方法只能是从已有映像创建。需要创建的情况有以下几种：

1. 从 Docker Registry 拉取了新的 Image，需要创建一个容器。
2. 从现有的 Image 创建新的容器。

某一 Docker Endpoint 上映像的列表无需维护，可以通过 Docker Endpoint API 取得。用户只需从中选定一个，即可从映像创建容器。

在 Django 中设计对应的 View 类 `Manager.DockerContainerView`，并添加模版以供用户实现对容器的操作。

| HTTP 路由 | HTTP 动作 | DockerContainerView 类中的方法 | 方法含义说明 |
|-----------|-----------|--------------------|-------------------|
| `/container` | GET | `docker_container_view.list()`| 获取现有的所有构建容器 |
| `/container` | POST | `docker_container_view.create()`| 从现有映像创建一个容器 |
| `/container/<int:id>` | GET | `docker_container_view.detail()`| 获得一个构建容器的详情 |
| `/container/<int:id>` | POST | `docker_container_view.start_or_stop()`| 启动或停止一个构建容器 |
| `/container/<int:id>` | PUT | `docker_container_view.edit()`| 修改容器的信息 |
| `/container/<int:id>` | DELETE | `docker_container_view.delete()`| 删除构建容器 |

通过解析 Docker Endpoint 连接字符串以及容器 ID，即可得到容器的访问地址。平台侧只需要利用反向代理的方式，将用户发送到平台侧的请求转发到对应的 Worker，并从 Worker 处取回结果即可。

在 View 类 `Manager.DockerContainerView` 中添加两个方法用于反向代理，并添加模版以供用户实现对 Worker 的操作。

| HTTP 路由 | HTTP 动作 | DockerContainerView 类中的方法 | 方法含义说明 |
|-----------|-----------|--------------------|-------------------|
| `/container/<int:id>/worker/*` | GET | `docker_container_view.proxy_get()`| 发送 GET 请求到 Worker 并取回结果 |
| `/container/<int:id>/worker/*` | POST | `docker_container_view.proxy_post()`| 发送 POST 请求到 Worker 并取回结果 |

控制台的前端是直接由 Worker 提供的，因此对于控制台相关的功能，使用 Django 的 `HttpResponseRedirect` 返回一个跳转请求，直接跳转到 Worker 的控制台页面。

| HTTP 路由 | HTTP 动作 | DockerContainerView 类中的方法 | 方法含义说明 |
|-----------|-----------|--------------------|-------------------|
| `/container/<int:id>/terminal/<string:name>` | GET | `docker_container_view.redirect_terminal()`| 跳转到 Worker 的控制台页面 |

#### 5.2.5 部分前端用户界面的实现

本系统用户侧的前端主要包括控制台输出回显界面、Kconfig 配置界面以及其他的一些简单界面。

简单界面涉及到的功能模块包括 Docker Endpoint 的管理、Docker Registry 的管理、构建容器的管理以及基本信息查看等，这些功能模块涉及到的功能逻辑均在后端实现，前端只是通过 Ajax 调用后端 API 发送或者取回数据，故不在这里赘述。

控制台输出回显界面与 Kconfig 界面则稍微复杂。对于控制台回显界面，需要通过 Ajax 定时从后端 API 获取输出结果，并在前端进行展示；控制台程序退出后，还需要正确传递状态码，并通知前端逻辑停止定时获取输出结果的操作。Kconfig 界面在向后端请求对应数据后，需要将配置树显示在浏览器中；由于配置树过于庞大，每次获取数据时需要先记录用户上次操作时所处的配置树结点，再向后端服务器请求更新后的配置树，遍历到上次所处的配置树后再更新页面，这样可避免显示过多节点导致的性能问题。

### 5.3 本章小结

本章详细介绍了本构建系统各组成部分的实现方案，包括构建容器中的 Worker 对 OpenWrt 原始构建工具的封装，以及平台侧用于管理构建环境的一系列组件的实现和部分用户界面的实现等。

## 6 测试与结果分析

在本章中，首先介绍了开发和测试环境，然后主要展示测试用例以及测试结果，并对测试结果进行了一定分析。

### 6.1 开发环境及相关工具

开发环境：

* Mac OS X 10.13.4
* Python 3.6.5
* Django 2.0.0
* Tornado 5.0.2 
* Docker 17.12.1-ce
* 构建容器基础映像为 Ubuntu 18.04
* OpenWrt SNAPSHOT r0+6869-6be9adce15 / LuCI Master (git-18.129.69108-658b6d7)

相关工具：

* Jetbrains Pycharm 2018.1
* Visual Studio Code 1.23.1
* Fish 2.7.1

### 6.2 测试环境与测试工具

测试环境 A 运行于 Windows 10 x86/64 17134.45 上的 Hyper-V 虚拟机。

宿主机的硬件配置为：

* CPU Intel i7-6770HQ 4 核 8 线程 2.6GHz
* 内存 32GB DDR4 2133MHz 双通道
* 硬盘 Intel SSD 256GB * 2
* 网络 1Gbps 网卡

创建的虚拟机配置为：

* CPU 4 个虚拟核心
* 内存 8GB
* 硬盘 64GB 虚拟硬盘

虚拟机上的运行环境为：

* Ubuntu 18.04
* Python 3.6.5
* Django 2.0.0
* Tornado 5.0.2 
* Docker 17.12.1-ce
* 构建容器基础映像为 Ubuntu 18.04
* OpenWrt SNAPSHOT r6929+1-75ed56a08a / LuCI Master (git-18.129.69108-658b6d7)

构建容器使用的 Docker Endpoint 与平台均运行在本台虚拟机上。

### 6.3 测试用例与结果分析

考虑一个典型的系统使用过程。

1. 启动构建系统平台，添加一个 Docker Endpoint；
2. 在该 Docker Endpoint 上使用 Docker Build 创建一个构建容器并将其映像推送到本地架设的 Docker Registry；
3. 从该 Docker Registry 拉取刚刚推送的构建容器映像，并利用该映像创建构建容器；
4. 启动第三步创建的构建容器，查看其中 OpenWrt 版本等信息；
5. 更新所有 feeds.conf 中定义的软件包并安装到构建环境中。
6. 使用构建平台添加一个软件包 ngrokc。
7. 访问该构建容器控制台，修改刚刚添加的软件包名称为 ngrok。
8. 进入配置界面，选择目标平台为 x86/64，并将软件包 ngrok 选中。
9. 进行构建。
10. 在测试环境内启动刚刚构建的 OpenWrt 系统，并运行 ngrok 程序。

启动构建系统平台，添加一个 Docker Endpoint 的用例如表 6.1 所示。

| 序号 | 1 |
|-|-|
| 测试目标 | 启动构建系统平台，添加一个 Docker Endpoint |
| 测试路径 | 1. 启动构建平台<br />2. 打开构建平台，选择 Docker Endpoint 列表，选择添加<br />3. 输入 "localhost" 作为名称，输入 "tcp://localhost:2379" 作为链接字符串<br />4. 点击添加。 |
| 期望结果 | 正确添加一个名称为 "localhost"，连接字符串为 "tcp://localhost:2379" 的 Docker Endpoint |
| 实际结果 | 正确添加一个名称为 "localhost"，连接字符串为 "tcp://localhost:2379" 的 Docker Endpoint |
| 测试结果 | 通过 |

这说明构建平台可以正确添加 Docker Endpoint，可以进行下一步测试。

在该 Docker Endpoint 上使用 Docker Build 创建一个构建容器并将其映像推送到本地架设的 Docker Registry 的测试用例如表 6.2 所示。

| 序号 | 2 |
|-|-|
| 测试目标 | 在该 Docker Endpoint 上使用 Docker Build 创建一个构建容器并将其映像推送到本地架设的 Docker Registry |
| 测试路径 | 1. 打开构建平台，打开构建容器列表<br />2. 选择新建构建容器，选择使用 Docker Build 创建<br />3. 选择刚刚添加的 "localhost" Docker Endpoint，点击开始<br />4. 等待创建完成<br />5. 选择添加 Docker Registry<br />6. 输入 "localhost" 作为名称，输入 "http://localhost:3000" 作为链接字符串<br />7. 点击添加<br />8. 选择 Docker Endpoint 列表，选择刚刚新建的构建容器映像，选择推送<br />9. 选择刚刚添加的 "localhost" Docker Registry，点击推送<br />10. 等待推送完成。 |
| 期望结果 | 正确构建新的构建容器，并将其映像推送到名称为 "localhost", 连接字符串为 "http://localhost:3000" 的 Docker Registry |
| 实际结果 | 正确构建新的构建容器，并将其映像推送到名称为 "localhost", 连接字符串为 "http://localhost:3000" 的 Docker Registry |
| 测试结果 | 通过 |

这说明构建平台可以正确创建构建容器，并能够将其推送到本地架设的 Docker Registry 上，可以进行下一步测试。

从该 Docker Registry 拉取刚刚推送的构建容器映像，并利用该映像创建构建容器的测试用例如表 6.3 所示。

| 序号 | 3 |
|-|-|
| 测试目标 | 从该 Docker Registry 拉取刚刚推送的构建容器映像，并利用该映像创建构建容器 |
| 测试路径 | 1. 打开构建平台，打开构建容器列表<br />2. 选择新建构建容器，选择从 Docker Registry 拉取；3. 选择 "localhost" Docker Registry，选择刚刚推送的映像，点击拉取<br />4. 等待拉取完成<br />5. 打开构建容器列表，查看新的构建容器是否出现 |
| 期望结果 | 正确完成拉取，在构建容器列表内看到新的构建容器出现 |
| 实际结果 | 正确完成拉取，在构建容器列表内看到新的构建容器出现 |
| 测试结果 | 通过 |

这说明构建平台可以正确完成拉取并创建构建容器的工作，可以进行下一步工作。

启动第三步创建的构建容器，查看其中 OpenWrt 版本等信息的用例如表 6.4 所示。

| 序号 | 4 |
|-|-|
| 测试目标 | 启动第三步创建的构建容器，查看其中 OpenWrt 版本等信息 |
| 测试路径 | 1. 打开构建平台，打开构建容器列表<br />2. 选择刚刚创建的构建容器，查看其版本号和最新提交的 ID |
| 期望结果 | 该容器的版本号为 `"r6929+1-75ed56a08a"`，最新提交的 ID 为 `"ccdbb4c86afb2d6dc95fa1ad89f2a6e5a329a1fd"` |
| 实际结果 | 该容器的版本号为 `"r6929+1-75ed56a08a"`，最新提交的 ID 为 `"ccdbb4c86afb2d6dc95fa1ad89f2a6e5a329a1fd"` |
| 测试结果 | 通过 |

这说明平台侧与构建容器通信正常，构建容器内的 Worker 工作正常，可以进行下一步工作。

更新所有 feeds.conf 中定义的软件包并安装到构建环境中的用例如表 6.5 所示。

| 序号 | 5 |
|-|-|
| 测试目标 | 启动第三步创建的构建容器，查看其中 OpenWrt 版本等信息 |
| 测试路径 | 1. 打开构建平台，打开构建容器列表<br />2. 选择刚刚创建的构建容器，点击更新所有软件包<br />3. 在跳转到的控制台回显界面内查看更新脚本运行的情况<br /> |
| 期望结果 | 更新脚本正常运行，能正常看到更新脚本的输出 |
| 实际结果 | 更新脚本正常运行，能正常看到更新脚本的输出 |
| 测试结果 | 通过 |

这说明 Worker 可以正常运行进程，并传回其控制台回显，可以进行下一步工作。

使用构建平台添加一个软件包 ngrokc 的用例如表 6.6 所示。

| 序号 | 6 |
|-|-|
| 测试目标 | 使用构建平台添加一个软件包 ngrokc |
| 测试路径 | 1. 打开构建平台，打开构建容器列表<br />2. 选择刚刚创建的构建容器，点击软件包管理，点击添加软件包<br />3. 输入 "https://github.com/yichya/ngrokc-mbedtls.git" 作为软件包路径，点击添加<br />4. 等待添加完毕<br />5. 点击软件包列表，查找 ngrokc 软件包|
| 期望结果 | 正常添加软件包 ngrokc，该软件包出现在软件包列表中 |
| 实际结果 | 正常添加软件包 ngrokc，该软件包出现在软件包列表中 |
| 测试结果 | 通过 |

这说明添加软件包以及软件包管理可以正常完成，可以进行下一步工作。

访问该构建容器控制台，修改刚刚添加的软件包名称为 ngrok 的用例如表 6.7 所示。

| 序号 | 7 |
|-|-|
| 测试目标 | 访问该构建容器控制台，修改刚刚添加的软件包名称为 ngrok |
| 测试路径 | 1. 打开构建平台，打开构建容器列表<br />2. 选择刚刚创建的构建容器，点击访问控制台<br />3. 在控制台窗口中输入 `"vim packages/extra/ngrokc-mbedtls/Makefile"`，打开 Vim<br />4. 使用 Vim 修改 22 行 `TITLE:=ngrokc` 为 `TITLE:=ngrok`，保存退出<br />5. 选择软件包管理，点击软件包列表，查找 ngrok 软件包 |
| 期望结果 | 控制台窗口正常开启，可正常操作；软件包列表内 ngrokc 消失，ngrok 出现 |
| 实际结果 | 控制台窗口正常开启，可正常操作；软件包列表内 ngrokc 消失，ngrok 出现 |
| 测试结果 | 通过 |

这说明访问容器控制台的功能可以正常使用，可以进行下一步操作。

进入配置界面，选择目标平台为 x86/64，并将软件包 ngrok 选中的用例如表 6.8 所示。

| 序号 | 8 |
|-|-|
| 测试目标 | 进入配置界面，选择目标平台为 x86/64，并将软件包 ngrok 选中 |
| 测试路径 | 1. 打开构建平台，打开构建容器列表<br />2. 选择刚刚创建的构建容器，点击进行构建配置<br />3. 点击配置界面中的 "Target System"，选中里面的 "x86"<br />4. 点击配置界面中的 "Subtarget"，选中里面的 "x86/64"<br />5. 点击配置界面中的 "Extra packages"，选中里面的 "ngrok"<br />6. 点击保存，使用默认配置文件名 ".config" 保存 |
| 期望结果 | 配置界面正常开启，可正常完成选定配置的操作 |
| 实际结果 | 配置界面正常开启，可正常完成选定配置的操作 |
| 测试结果 | 通过 |

进行构建的用例如表 6.9 所示。

| 序号 | 9 |
|-|-|
| 测试目标 | 进行构建 |
| 测试路径 | 1. 打开构建平台，打开构建容器列表<br />2. 选择刚刚创建的构建容器，点击进行构建<br />3. 使用默认设置 `"-j4"` 开始构建<br />4. 跳转到控制台回显页面，等待 1 小时左右完成全部构建任务，并查看输出无报错<br /> |
| 期望结果 | 构建任务正常完成，无错误产生 |
| 实际结果 | 构建任务正常完成，无错误产生 |
| 测试结果 | 通过 |

这说明构建系统可以正确完成构建任务，可以进行下一步操作。

在测试环境内启动刚刚构建的 OpenWrt 系统，并运行 ngrok 程序的用例如表 6.10 所示。

| 序号 | 10 |
|-|-|
| 测试目标 | 在测试环境内启动刚刚构建的 OpenWrt 系统，并运行 ngrok 程序的用例如表 6.10 所示 |
| 测试路径 | 1. 打开构建平台，打开构建容器列表<br />2. 选择刚刚创建的构建容器，点击运行测试环境<br />3. 在虚拟硬盘框中选择默认的 `"bin/targets/x86/64/openwrt-x86-64-combined-squashfs.img`，点击启动<br />4. 等待 1 分钟左右环境启动，看到 `root@OpenWrt:/#` 提示符<br />5. 输入命令 `ngrokc` 查看输出 |
| 期望结果 | 测试环境正常启动，输入命令后正确输出 ngrokc 的版本号以及使用说明 |
| 实际结果 | 测试环境正常启动，输入命令后正确输出 ngrokc 的版本号以及使用说明 |
| 测试结果 | 通过 |

这说明测试环境可以正常使用，且步骤 9 构建的 OpenWrt 系统与用户配置相符。

通过以上分步骤测试，说明本自动构建工具可以满足预定需求。

### 6.4 本章小结

本章首先介绍了本系统的开发和测试环境，然后针对典型系统使用过程对系统功能进行了测试，结果满足需求。

## 7 总结与展望

本文论述了如何利用容器化、虚拟化等技术设计用于 OpenWrt 的自动构建以及测试的系统，并对该系统进行了测试，最终证明这一系统可以满足需求。对本自动构建工具的应用可以降低产品评估以及测试人员进行工作的难度，同时节省他们的时间。容器化技术也使得不同构建环境不再相互干扰，提升构建服务器的利用效率。

由于时间较为仓促，该项目仍存在可以完善的一些地方，后续的完善方向包括：

1. 现有的测试环境是基于虚拟机完成的，后续为了更加贴近实际应用场景，可以与实际设备的开发板连接，并将开发板的 UART 连接至本工具的控制台，实现更方便的操作；
2. 构建容器的管理需要通过平台侧持久化的数据库进行维护，后续应可以考虑使用成熟的容器编排工具实现全自动管理。

## 致谢

首先我感谢卷心菜网络公司，在本平台开发的过程中帮助我完善系统中的每个组成部分，感谢导师对我的悉心指导。

其次，感谢我的论文指导老师李瑞，他在我的论文撰写过程中提供了大量切实的改进意见，使我受益匪浅。

感谢开源社区的一系列开源项目成果。本工具依赖的 Docker、Django、Tornado 等框架或组件均来自开源社区，这些工具为本系统的实现提供了巨大支持。感谢在我四年本科生活中帮助我开阔眼界、增长知识的学校老师。

最后，感谢西电软院科协的学长和同学们，每周的技术分享帮助我发现了自己的兴趣和闪光点，使我明确了未来的发展方向。

## 参考文献
## 10000 字的英文翻译


机器学习算法在摇滚乐各流派间的分类识别应用 14130188015 徐治宇.docx
基于毫秒引擎的手游直播后台的设计与实现 14130188012 李卓.doc
基于特征提取的节点分类方法研究与应用探究 14130188010 孙奇.pdf
嵌入式 Linux 系统自动构建工具的设计与实现 14130188013 尹晨阳.docx
软件模拟渲染管线 14130188017 陈志达.doc