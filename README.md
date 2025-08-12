# frida-uexplorer

[![Status](https://img.shields.io/badge/status-in_development-yellow.svg)](https://github.com/jinjiazhang/frida-uexplorer)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**frida-uexplorer** 是一个交互式的、实时的Unreal Engine游戏内存勘探工具。它采用客户端-服务器架构，并支持可插拔的配置文件，允许用户通过一个友好的命令行界面向注入游戏的Frida `agent` 发送指令，并以结构化的方式查看返回的数据。

这个项目旨在为逆向工程师和游戏安全研究者提供一个强大、灵活、易于配置的工具，用于深入理解UE游戏的内部工作原理。

## 🏛️ 架构

本项目由三个核心部分组成：

* **`agent/`**: 一个用JavaScript编写的Frida脚本。它被注入到目标游戏进程中，作为“服务器”运行。它负责所有低级别的内存操作，如扫描、地址解析、对象遍历和属性反射。它通过Frida的RPC（远程过程调用）暴露出一系列API供客户端调用。

* **`explorer/`**: 一个用户侧的Python客户端。它负责提供用户界面（当前为命令行），加载配置文件，将用户的指令发送给`agent`，并以可读的格式展示从`agent`返回的复杂数据。

* **`configs/`**: 存放针对不同Unreal Engine版本或特定游戏的配置文件（`.json`格式）。每个文件包含了定位核心结构所需的**特征码 (AOB Patterns)** 和关键的**内存偏移量 (Offsets)**。

```
┌────────┐     ┌────────────────┐     ┌──────────────────┐     ┌───────────────────┐     ┌─────────────────────┐
│  User  │ <-> │ Explorer (Py)  │ <── │ Configs (*.json) │ ──> │   Agent (JS)      │ <── │ Target Game Process │
└────────┘     └────────────────┘     └──────────────────┘     └───────────────────┘     └─────────────────────┘
  (Client)        (Loads Config)         (Provides Data)         (Receives Config)         (Server-side Logic)
```

## ✨ 功能特性

* **客户端-服务器架构**: 将复杂的内存操作与用户界面分离，易于维护和扩展。
* **可配置化**: 通过简单的JSON文件支持不同UE版本和游戏，无需修改代码。
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
git clone https://github.com/jinjiazhang/frida-uexplorer.git
cd frida-uexplorer
```

### 2. ⚠️ 配置 (最重要的一步!)

此工具的强大之处在于其配置系统。你需要为你的目标游戏选择或创建一个配置文件。

1. **浏览 `configs/` 目录**:
 查看是否已有适用于你的UE版本的配置文件（例如 `UE4.27.json`, `UE5.1.json`）。

2. **创建或修改配置文件**:
 如果找不到合适的配置，复制一份现有的文件（如 `template.json`）并重命名。然后，使用IDA/Ghidra和ReClass.NET等工具找到正确的**特征码**和**偏移量**，并填充到你的JSON文件中。

 一个配置文件的结构如下 (`configs/MyGame_UE4.25.json`):
```json
    {
      "name": "My Game (Unreal Engine 4.25)",
      "version": "1.0",
      "patterns": {
        "GObjects": "48 8B 05 ? ? ? ? 48 8B 0C C8",
        "GNames": "48 8D 0D ? ? ? ? E8 ? ? ? ? 48 8B C8 E8",
        "GWorld": "48 8B 05 ? ? ? ? 48 85 C0 74 ? 48 8B 48"
      },
      "offsets": {
        "UObject": {
          "ClassPrivate": 16,
          "NamePrivate": 24,
          "OuterPrivate": 32
        },
        "UField": {
          "Next": 40
        },
        "UProperty": {
          "Offset_Internal": 76
        }
      }
    }
    ```
    **注意**: JSON中的偏移量应为十进制数字。

### 3. 安装 Explorer 依赖

```bash
cd explorer
pip install -r requirements.txt # 假设你有一个requirements.txt文件
```

### 4. 运行 frida-uexplorer

`explorer` 脚本负责加载配置文件、注入 `agent` 并附加到游戏进程。

使用 `-c` 或 `--config` 参数指定你要使用的配置文件。

**通过进程名附加:**
```bash
python explorer/main.py -n "YourGame-Win64-Shipping.exe" -c ../configs/MyGame_UE4.25.json
```

**通过PID附加:**
```bash
python explorer/main.py -p 12345 --config ../configs/UE5.1.json
```

**对于Android游戏 (通过包名):**
```bash
python explorer/main.py -U -f com.epicgames.YourGame -c ../configs/Android_UE4.27.json
```

如果成功，你将看到 `explorer` 加载了配置，并进入命令提示符：
```
[+] Config 'My Game (Unreal Engine 4.25)' loaded.
[+] Attached to process 'YourGame-Win64-Shipping.exe' (PID: 12345).
[+] Agent initialized successfully.
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

## 🚨 警告：反作弊与道德使用

* **使用风险自负**。在受反作弊系统（如EAC, BattlEye）保护的游戏上使用此工具，**极有可能导致你的游戏账号被封禁**。
* 本项目**仅用于教育和学习目的**。请在单机游戏、私人服务器或你拥有明确权限的环境中进行实验。
* **请勿将此工具用于恶意目的**，如制作外挂或破坏在线游戏平衡。

## 📝 未来规划 (Roadmap)

* [ ] **Agent**: 完善对 `TArray`, `TMap`, `TSet` 和嵌套 `UStruct` 的解析。
* [ ] **Explorer**: 开发一个图形用户界面（GUI），例如使用 Dear PyGui, Qt, 或 Electron，以树状视图展示对象。
* [ ] **Explorer**: 增加数据导出功能（如JSON）。
* [ ] **Core**: 增加调用 `UFunction` 的能力。
* [ ] **Configs**: 社区驱动，收集并验证更多UE版本和热门游戏的配置文件。

## 🤝 贡献

欢迎提交 Pull Requests！如果你为某个游戏或UE版本创建了一个新的配置文件，请考虑提交它，让更多人受益。如果你有任何改进建议或发现了Bug，请随时创建 Issue。

## 📄 许可证

本项目采用 [MIT License](LICENSE)。
