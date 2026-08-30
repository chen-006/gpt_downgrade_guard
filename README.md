# Sub2 API 防降智小程序

> 当前为测试版。请先在测试分组验证，再用于日常账号调度。

这是一个运行在本机的 Sub2API 辅助程序，用于检测指定分组中的 OpenAI 账号是否仍表现为 `gpt-5.6-sol`，并按照检测结果在两个分组之间调整账号。

## 功能

- 只读取分组 A、分组 B 中的 OpenAI 账号
- 额外按账号 `group_ids` 校验范围，其他账号不探测
- 每个账号执行 9 条低档指纹探针
- 所有账号并行探测，单账号最多 3 并发
- 输出 Sol、Terra、Luna 三模型指纹匹配度
- 支持严格和宽松两种降智规则
- 请求未全部完成时显示“网络错误/上游错误”且不移动分组
- 记录每个账号最近 100 条历史
- 本地黑色管理页面
- 浏览器管理员令牌自动获取
- 配置自动保存，状态刷新不改变页面滚动位置

## 环境要求

- Windows 10/11
- PowerShell
- Python 3.10+
- 已安装并运行的 Sub2API
- Sub2API 管理员登录会话或管理员 JWT access token

默认地址：

```text
Sub2API: http://127.0.0.1:8080
管理页面: http://127.0.0.1:8787
```

## 交给 Agent 一键安装

可以把下面整段发送给负责 Sub2API 的 Agent：

```text
请下载并安装：
https://github.com/chen-006/gpt_downgrade_guard

严格参考：
https://github.com/chen-006/gpt_downgrade_guard/blob/main/INSTALL_GUIDE_CN.md

请直接完成安装和验证，不要只给操作说明。

安装要求：
1. 检查本机正在运行的 Sub2API、访问地址、版本和安装目录。
2. 要求 Python 3.10 或更高版本。
3. 保留已有 config.json 和 data/state.json；覆盖程序文件时清理 __pycache__ 和 .pyc。
4. 检查 Sub2API 测试入口是否已经支持 system_prompt 和 reasoning_effort。
5. 补丁已经存在时不要重复执行 apply_sub2api_patch.ps1，也不要重复构建。
6. 确认补丁缺失时才执行补丁，并按现有部署方式完成必要的构建和 Sub2API 重启。
7. 不修改无关的账号并发、优先级、调度状态、路由规则或分组。

管理员令牌：
1. 我授权从当前本机 Chromium 浏览器的 Sub2API 登录会话中读取管理员 access_token。
2. 启动小程序后优先 POST http://127.0.0.1:8787/api/token/auto。
3. 只检查 ok 和 admin_token_set，不输出 token 内容。
4. 自动获取失败时再向我索要管理员登录凭据。
5. 使用登录接口时设置 User-Agent: gpt-downgrade-guard/1.0。
6. access_token 只允许保存在当前进程内存，不写 config.json、.env、日志或临时文件。
7. 手动 token 只通过页面输入并点击“保存配置”，不要写入配置文件。

启动和配置：
1. 在后台启动小程序，确认 http://127.0.0.1:8787 可以打开。
2. 确认管理令牌显示“已连接”。
3. 如果我没有指定分组 A/B，先询问，不要自行猜测。
4. A/B 未选择完整之前不得发送探针。
5. 只探测 group_ids 包含 A 或 B 的 OpenAI 账号。
6. 不要为了安装验证而探测其他账号或移动生产账号。

验收：
1. Sub2API 健康。
2. 页面可以访问。
3. A/B 账号数量能立即显示。
4. 所有账号并行探测，单账号最多 3 并发。
5. 正常账号显示 9 请求、9 成功和三个模型匹配度。
6. 任意请求最终未完成时显示“网络错误/上游错误”，并保持原分组。
7. 历史最新记录在最左侧。
8. 页面自动刷新不改变滚动位置。
9. 清理安装产生的缓存、临时脚本和测试文件。

最终只报告安装目录、两个访问地址、补丁状态、令牌连接状态、暂停状态以及是否等待选择 A/B。不要报告 token、密码或账号凭据。
```

## 手动安装

完整步骤见 [INSTALL_GUIDE_CN.md](./INSTALL_GUIDE_CN.md)。

简要流程：

1. 下载并解压本项目。
2. 检查 Sub2API 是否已经支持 `system_prompt` 和 `reasoning_effort`。
3. 仅在补丁缺失时执行 `install/apply_sub2api_patch.ps1`。
4. 按现有部署方式重新构建并重启 Sub2API。
5. 双击 `一键启动_防降智小程序.bat`。
6. 打开 `http://127.0.0.1:8787`。
7. 自动获取管理员令牌，或在页面手动填写后点击“保存配置”。
8. 选择分组 A、分组 B 和检测间隔。

补丁脚本只应执行一次。已经安装时再次执行会出现 `Replacement not found`。

## 管理员令牌

管理员令牌只保存在小程序当前进程内存：

- 不写入 `config.json`
- 不写入 `.env`
- 不写入日志
- 不在页面中回显
- 程序重启后需要重新获取

页面支持从本机 Chrome、Edge、Brave、Chromium 登录数据中自动查找当前 Sub2API 的管理员 JWT，并通过本机管理接口验证。

手动输入 token 时必须点击“保存配置”。token 不参与普通配置的 400ms 自动保存，避免输入过程中提交半截内容。

## 探针

每个账号固定执行三种探针，每种三次：

```text
Name a random country. Reply with ONLY the country name.
Name a random bird. Reply with ONLY the bird name, one word.
Count the letter r in strawberry. Reply only with the integer.
```

固定参数：

```text
model_id = gpt-5.6-sol
system_prompt = "."
reasoning_effort = "none"
```

每条探针包含初次请求和最多 4 次重试预算。

全部探针成功后，程序计算：

- Sol 指纹匹配度
- Terra 指纹匹配度
- Luna 指纹匹配度
- 最终结果：强指向 Sol、强指向 Terra、强指向 Luna 或证据不足

任意探针最终未完成时，结果为“网络错误/上游错误”，该账号不会移动分组。

## 分组规则

- 严格：只有“强指向 Sol”留在或移回 A。
- 宽松：只有“强指向 Terra”或“强指向 Luna”进入 B。
- 请求未全部完成：不移动。
- 账号的其他非 A/B 分组保持不变。

## 页面

页面显示：

- 当前状态和下一次检查时间
- A/B 账号数量
- 本轮已完成账号数
- 每个账号的最终结果
- 请求数、成功数和三模型匹配度
- 最近 100 条历史，最新记录位于最左侧

页面每 5 秒读取状态。数据没有变化时不会重建账号表格，自动刷新不会把视角拉回顶部。

## 隐私与本地文件

项目默认只监听 `127.0.0.1`。

不要提交或分享：

- `config.json`
- `data/`
- `__pycache__/`
- `*.pyc`

仓库中的 `.gitignore` 会忽略这些文件。

程序不会把管理员令牌上传到外部服务。账号探针通过你的本机 Sub2API 管理测试接口发送。
