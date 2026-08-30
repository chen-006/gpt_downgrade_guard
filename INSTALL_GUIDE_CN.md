# Sub2 API 防降智小程序安装说明

这个项目由两部分组成：

1. 防降智小程序：负责探测、评分、分组调整和本地页面展示。
2. Sub2API 最小补丁：让账号测试入口接收 `system_prompt` 和 `reasoning_effort`。

## 环境要求

- Windows 10 或 Windows 11
- PowerShell
- Python 3.10 或更高版本
- 已安装并正在运行的 Sub2API
- Sub2API 管理员登录会话或管理员 JWT access token

默认地址：

```text
Sub2API: http://127.0.0.1:8080
防降智页面: http://127.0.0.1:8787
```

## 第一步：下载项目

下载并解压仓库：

```text
https://github.com/chen-006/gpt_downgrade_guard
```

不要把本机的以下内容上传或分享：

- `config.json`
- `data/`
- `__pycache__/`
- `*.pyc`

仓库提供的 `.gitignore` 会忽略这些文件。

## 第二步：检查并安装 Sub2API 补丁

补丁增加两个账号测试字段：

- `system_prompt`
- `reasoning_effort`

补丁脚本只应执行一次。升级或重复安装前，先检查 Sub2API 源码是否已经包含这些字段；已经安装时不要再次运行脚本。

确认尚未安装后，在 Sub2API 根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File "<项目目录>\install\apply_sub2api_patch.ps1"
```

脚本修改完成后，需要按现有 Sub2API 部署方式重新构建并重启 Sub2API。仅重启旧镜像不会加载源码改动。

补丁脚本不是重复执行脚本。第二次运行出现 `Replacement not found`，通常表示补丁已经存在；不要继续重复修改源码。

## 第三步：启动小程序

最简单的方式是双击项目根目录的：

```text
一键启动_防降智小程序.bat
```

也可以使用 PowerShell：

```powershell
.\install\run_guard.ps1
```

或直接运行：

```powershell
py .\main.py
```

然后打开：

```text
http://127.0.0.1:8787
```

如果 `py` 找不到 Python，请先安装 Python 3.10+，并在安装时启用 Python Launcher 或将 Python 加入 PATH。

## 第四步：连接管理员令牌

管理员令牌只保存在小程序当前进程内存中：

- 不写入 `config.json`
- 不写入 `.env`
- 不写入日志
- 不在页面中回显
- 程序重启后需要重新获取

### 自动获取

先在本机 Chrome、Edge、Brave 或 Chromium 登录 Sub2API 管理后台，然后点击页面中的“自动获取”。

程序只查找当前 Sub2API 地址附近的 JWT 候选，并使用本机管理接口验证。令牌不会上传到外部服务。

### 手动填写

把管理员 JWT 粘贴到页面的“管理令牌”输入框，然后点击“保存配置”。

管理员令牌不会参与 400ms 配置自动保存，必须显式点击保存，避免输入过程中提交半截 token。

不要把管理员令牌写入 `config.json`。

连接成功后，页面右上角会显示“已连接”。

## 第五步：选择分组

在页面中选择：

- 分组 A：正常账号所在分组
- 分组 B：检测到降级后移动到的分组
- 检测间隔：默认 180 秒
- 降智标准：严格或宽松

分组和其他普通配置会自动保存，也可以点击“保存配置”。

分组 A、B 没有完整选择时，程序不会发送探针。

程序只探测 `group_ids` 中包含分组 A 或分组 B 的 OpenAI 账号，其他账号不会被探测。

## 探测行为

每个账号执行 9 条请求：3 种探针，每种 3 次。

固定设置：

```text
model_id = gpt-5.6-sol
system_prompt = "."
reasoning_effort = "none"
```

探针内容：

```text
Name a random country. Reply with ONLY the country name.
Name a random bird. Reply with ONLY the bird name, one word.
Count the letter r in strawberry. Reply only with the integer.
```

调度方式：

- 所有待检测账号并行开始
- 每个账号最多同时执行 3 个请求
- 每条请求包含初次请求和最多 4 次重试预算

如果 9 条探针没有全部成功：

- 结果显示“网络错误/上游错误”
- 不执行模型降级判断
- 不移动该账号分组

全部成功后，页面显示：

- 请求数和成功数
- Sol 指纹匹配度
- Terra 指纹匹配度
- Luna 指纹匹配度
- 最终判定结果

## 分组规则

严格模式：只有“强指向 Sol”留在或移回 A，其他完整探测结果进入 B。

宽松模式：只有“强指向 Terra”或“强指向 Luna”进入 B。

移动账号时只调整 A、B 两个目标分组，账号的其他分组保持不变。

## 页面说明

- A/B 账号数在读取配置后立即显示
- 本轮完成数随账号探测完成更新
- 历史记录默认显示，最新记录在最左侧
- “探针详情”展开后显示请求数、成功数和三模型匹配度
- 页面每 5 秒读取一次状态
- 状态没有变化时不会重建账号表格
- 自动刷新不会把页面滚动位置拉回顶部

## 安装验收

至少确认：

1. Sub2API 健康检查正常。
2. `http://127.0.0.1:8787` 可以打开。
3. 页面显示“已连接”。
4. A/B 分组账号数量正确。
5. A/B 未选择时没有探测请求。
6. 正常账号显示 9 请求、9 成功和三模型匹配度。
7. 请求未完成的账号显示“网络错误/上游错误”且分组不变。

不要使用无关账号或生产分组做安装测试。需要实测时，使用单独测试分组，并保留账号原有业务分组。
