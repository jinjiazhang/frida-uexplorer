# frida-uexplorer

[![Status](https://img.shields.io/badge/status-in_development-yellow.svg)](https://github.com/your-username/frida-uexplorer)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**frida-uexplorer** 是一个交互式的、实时的Unreal Engine游戏内存勘探工具。它采用客户端-服务器架构，允许用户通过一个友好的命令行界面向注入游戏的Frida `agent` 发送指令，并以结构化的方式查看返回的数据。

这个项目旨在为逆向工程师和游戏安全研究者提供一个强大、灵活的工具，用于深入理解UE游戏的内部工作原理。

## 🏛️ 架构

本项目由两个核心部分组成：

* **`agent/`**: 一个用JavaScript编写的Frida脚本。它被注入到目标游戏进程中，作为“服务器”运行。它负责所有低级别的内存操作，如扫描、地址解析、对象遍历和属性反射。它通过Frida的RPC（远程过程调用）暴露出一系列API供客户端调用。

* **`explorer/`**: 一个用户侧的客户端（例如用Python或Node.js编写）。它负责提供用户界面（当前为命令行），将用户的指令发送给`agent`，并以可读的格式展示从`agent`返回的复杂数据。

```
┌────────┐     ┌───────────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  User  │ <-> │ Explorer (Python/Node.js) │ <───┤      Frida RPC       ├───> │   Agent (JavaScript)  │ <-> │ Target Game Process │
└────────┘     └───────────────────────────┘     └──────────────────────┘     └─────────────────────┘
  (Client)                                          (Communication)                (Server)
```

## ✨ 功能特性

* **客户端-服务器架构**: 将复杂的内存操作与用户界面分离，易于维护和扩展。
* **交互式命令行**: 通过简单的命令实时查询游戏状态。
* **动态地址解析**: 使用特征码（AOB）扫描在运行时自动定位UE的核心全局变量 (`GObjects`, `GNames`, `GWorld`)。
* **深度对象勘探**: 可以从任意内存地址开始，递归地dump `UObject` 的属性、类信息和层级关系。
* **对象搜索**: 按名称或类名查找游戏世界中的特定对象。
* **可扩展API**: `agent` 暴露了一系列清晰的RPC函数，方便开发者构建自己的工具或自动化脚本。

## 🛠️ 环境要求

* **Agent**:
 * Frida
* **Explorer**:
 * Python 3.x
 * Frida-Python: `pip install frida`
* **通用**:
 * 一个目标Unreal Engine游戏（**强烈建议在单机或私服模式下使用**）。
 * **[强烈推荐]** 逆向工程工具：[IDA Pro](https://hex-rays.com/ida-pro/) / [Ghidra](https://ghidra-sre.org/), [ReClass.NET](https://github.com/ReClassNET/ReClass.NET)。

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/frida-uexplorer.git
cd frida-uexplorer
```

### 2. ⚠️ 配置 Agent (最重要的一步!)

由于每个游戏、每个版本的内存布局都不同，你**必须**手动配置 `agent` 以匹配你的目标游戏。

打开 `agent/index.js` 文件，找到 `CONFIG` 部分：

```javascript
// agent/index.js

// =================== CONFIGURATION ===================
// 你必须手动填充这些值！
// 使用IDA/Ghidra寻找特征码，使用ReClass.NET验证偏移量。
const CONFIG = {
    Patterns: {
        GObjects: "48 8B 05 ? ? ? ? 48 8B 0C C8",
        GNames: "48 8D 0D ? ? ? ? E8 ? ? ? ? 48 8B C8 E8",
        GWorld: "48 8B 05 ? ? ? ? 48 85 C0 74 ? 48 8B 48",
    },
    Offsets: {
        UObject: {
            ClassPrivate: 0x10,
            NamePrivate: 0x18,
            OuterPrivate: 0x20,
        },
        UField: {
            Next: 0x28,
        },
        UProperty: {
            Offset_Internal: 0x4C,
        },
        // ... 其他你需要的偏移量
    }
};
// =====================================================
```
**如何配置**: 请参考[主README](README.md)中关于寻找特征码和偏移量的详细指南。这是成功运行此工具的关键。

### 3. 安装 Explorer 依赖

```bash
cd explorer
pip install -r requirements.txt  # 假设你有一个requirements.txt文件
```

### 4. 运行 frida-uexplorer

`explorer` 脚本负责加载 `agent` 并附加到游戏进程。

首先，启动你的目标游戏。然后运行 `explorer`：

**通过进程名附加:**
```bash
python explorer/main.py -n "YourGame-Win64-Shipping.exe"
```

**通过PID附加:**
```bash
python explorer/main.py -p 12345
```

**对于Android游戏 (通过包名):**
```bash
python explorer/main.py -U -f com.epicgames.YourGame
```

成功附加后，你将看到一个命令提示符：
```
frida-uexplorer>
```

## ⌨️ 命令参考

在 `frida-uexplorer>` 提示符下，你可以使用以下命令：

| 命令 | 参数 | 描述 |
| :--- | :--- | :--- |
| `info` | - | 显示 `GNames`, `GObjects`, `GWorld` 的基址和对象总数。 |
| `dump` | `<address>` | Dump指定内存地址的 `UObject` 的所有属性。 |
| `world` | - | Dump `GWorld` 对象。 |
| `find` | `<object_name>` | 在 `GObjects` 中搜索包含指定名称的对象。 |
| `findclass`| `<class_name>` | 搜索指定类的所有实例。 |
| `player` | - | 快捷命令，尝试找到并dump玩家控制器 (`PlayerController`)。 |
| `pawn` | - | 快捷命令，尝试找到并dump玩家控制的角色 (`Pawn`)。 |
| `help` | - | 显示帮助信息。 |
| `exit` | - | 分离并退出。 |

**示例:**
```
frida-uexplorer> info
[+] GWorld: 0x7ff6a0b1c2d0
[+] GObjects: 0x7ff6a0a3f4c0
[+] GNames: 0x7ff6a0a2b1e0
[+] Total UObjects: 158234

frida-uexplorer> player
--- Dumping Object: PlayerController_0 ---
Address: 0x1c8b4a9fec0
Class: PlayerController
  [+] PlayerCameraManager (ObjectProperty) @ offset 0x2b8 = PlayerCameraManager_0 (0x1c8b4a9ff80)
  [+] AcknowledgedPawn (ObjectProperty) @ offset 0x2a0 = ThirdPersonCharacter_0 (0x1c8b4a9fd40)
  [+] bShowMouseCursor (BoolProperty) @ offset 0x518 = false
  ...

frida-uexplorer> dump 0x1c8b4a9fd40
--- Dumping Object: ThirdPersonCharacter_0 ---
Address: 0x1c8b4a9fd40
Class: ThirdPersonCharacter
  [+] CapsuleComponent (ObjectProperty) @ offset 0x288 = CapsuleComponent_0 (0x1c8b4aa0040)
  [+] Mesh (ObjectProperty) @ offset 0x298 = SkeletalMeshComponent_0 (0x1c8b4aa0100)
  ...
```

## 🚨 警告：反作弊与道德使用

* **使用风险自负**。在受反作弊系统（如EAC, BattlEye）保护的游戏上使用此工具，**极有可能导致你的游戏账号被封禁**。
* 本项目**仅用于教育和学习目的**。请在单机游戏、私人服务器或你拥有明确权限的环境中进行实验。
* **请勿将此工具用于恶意目的**，如制作外挂或破坏在线游戏平衡。

## 📝 未来规划 (Roadmap)

* [ ] **Agent**: 完善对 `TArray`, `TMap`, `TSet` 和嵌套 `UStruct` 的解析。
* [ ] **Explorer**: 开发一个图形用户界面（GUI），例如使用 Dear PyGui, Qt, 或 Electron，以树状视图展示对象。
* [ ] **Explorer**: 增加数据导出功能（如JSON）。
* [ ] **Core**: 为不同UE版本提供预设的配置（特征码和偏移量）。
* [ ] **Core**: 增加调用 `UFunction` 的能力。

## 🤝 贡献

欢迎提交 Pull Requests！如果你有任何改进建议或发现了Bug，请随时创建 Issue。

## 📄 许可证

本项目采用 [MIT License](LICENSE)。
