# Sub2 API 防降智小程序安装说明

这个包分两部分：

1. 小程序本体，负责定时检查账号、打分、搬分组、显示状态。
2. Sub2 API 的最小补丁，负责让测试入口真正接收 `system_prompt` 和 `reasoning_effort`。

完整功能需要先打补丁，再运行小程序。

## 你要先准备什么

- 一份已经解压好的小程序文件夹。
- 一份正在运行的 Sub2 API。
- 一个能执行 PowerShell 的 Windows 环境。
- 如果你要让小程序真正工作，还需要 Sub2 API 管理令牌。

## 安装步骤

### 第 1 步，解压小程序

把整个压缩包解压到任意文件夹。比如：

```text
C:\tools\sub2api_gpt_downgrade_guard
```

解压后你会看到这些东西：

- `install\apply_sub2api_patch.ps1`
- `install\run_guard.ps1`
- `一键启动_防降智小程序.bat`
- `main.py`
- `config.example.json`

### 第 2 步，给 Sub2 API 打补丁

打开 PowerShell，先进入你的 Sub2 API 根目录。然后运行小程序包里的补丁脚本。

示例：

```powershell
powershell -ExecutionPolicy Bypass -File "C:\tools\sub2api_gpt_downgrade_guard\install\apply_sub2api_patch.ps1"
```

这个脚本会直接改 Sub2 API 的测试入口。

打完以后，**重启一次 Sub2 API**。

### 第 3 步，填小程序配置

回到小程序文件夹，打开 `config.json`。第一次启动时如果没有这个文件，程序会自己生成一个。

你主要要填这几项：

- `sub2api_base_url`
- `admin_token`
- `group_a_id`
- `group_b_id`
- `interval_seconds`
- `downgrade_rule`

### 管理令牌怎么自动抓

如果你不想手动填 `admin_token`，可以点页面里的“自动获取”。

这个按钮会在你本机常见的 Chromium 浏览器本地数据里找 `auth_token`，主要看这几个浏览器：

- Chrome
- Edge
- Brave
- Chromium

它只读本机浏览器里的本地数据，不会把令牌上传，也不会写进项目文件。

如果你已经在浏览器里登录过 Sub2 API 管理后台，通常点一下就能抓到。
如果没抓到，就说明浏览器里还没有对应的登录信息，或者令牌不在这些浏览器里，这时候就手动填 `admin_token`。

### 第 4 步，启动小程序

最简单的方式是直接双击根目录里的：

```text
一键启动_防降智小程序.bat
```

如果你更习惯 PowerShell，也可以运行：

```powershell
.\install\run_guard.ps1
```

或者：

```powershell
py .\main.py
```

### 第 5 步，打开页面

打开浏览器，访问：

```text
http://127.0.0.1:8787
```

如果这个端口被占用了，程序会自动换一个空闲端口，启动时会在命令行里打印出来。

## 页面上怎么填

- `Sub2 API 地址`：Sub2 API 的访问地址。
- `管理令牌`：Sub2 API 管理后台的令牌。
- `分组 A`：平时要检查的分组。
- `分组 B`：降智后要搬去的分组。
- `检测间隔（秒）`：默认 180。
- `降智标准`：只有“严格”和“宽松”两个选项。

页面里还有一个“自动获取”按钮，会试着从浏览器本地数据里找管理令牌。
分组选择会先拉一次 Sub2 API 的分组名单，你按名字选就行。

## 运行后会发生什么

- 程序会先立刻跑一轮。
- 然后按你填的秒数继续跑。
- 每个账号会发 9 条低档指纹探针。
- 程序会把结果写回页面，也会把账号在 A / B 两组之间挪动。

## 一句最重要的话

如果不先给 Sub2 API 打补丁，这个小程序就只能算半成品，不能完整工作。
