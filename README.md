# Sub2 API 防降智小程序

写在前面：目前还是测试版，安装方法：
对你的agent说（最好是控制sub2api的agent）：
```
请为我一键安装并配置这个项目：

https://github.com/chen-006/gpt_downgrade_guard

安装指南：

https://github.com/chen-006/gpt_downgrade_guard/blob/main/INSTALL_GUIDE_CN.md

请直接执行安装，不要只给出操作说明。

要求：

1. 下载 GitHub 仓库最新版本到本地。
2. 如果已经存在旧版本：
   - 保留原有 config.json 和 data/state.json；
   - 用最新版程序文件覆盖；
   - 不保留 __pycache__、.pyc 或旧测试文件。
3. 检查本机正在运行的 Sub2API：
   - 找到安装目录；
   - 确认访问地址和版本；
   - 默认地址优先检查 http://127.0.0.1:8080。
4. 检查 Sub2API 测试入口是否已经支持：
   - system_prompt
   - reasoning_effort
5. 如果补丁已经存在，不要重复执行补丁脚本，也不要重新构建 Sub2API。
6. 只有确认补丁尚未安装时，才执行：
   install/apply_sub2api_patch.ps1
7. 仅在补丁确实发生变化时，执行当前部署方式所必需的最小构建和重启。
8. 不修改任何无关的账号并发、优先级、调度状态、路由规则或分组。

管理员令牌处理：

1. 我明确授权你从当前本机 Chrome 的 Sub2API 登录会话中获取管理员 access_token。
2. 启动防降智程序后，优先调用：
   POST http://127.0.0.1:8787/api/token/auto
3. 检查返回结果中的 ok 和 admin_token_set，但不得输出 token 内容。
4. 自动获取失败时，再向我索要管理员邮箱和密码。
5. 使用登录接口时必须设置：
   User-Agent: gpt-downgrade-guard/1.0
6. 登录接口：
   POST /api/v1/auth/login
7. 如果启用了双因素认证，继续完成：
   POST /api/v1/auth/login/2fa
8. access_token 只能保存在防降智程序的当前进程内存中：
   - 不写入 config.json
   - 不写入 .env
   - 不写入日志
   - 不写入临时文件
   - 不在回复中展示

启动与配置：

1. 在后台启动防降智程序，不弹出长期占用前台的命令行窗口。
2. 确认页面可以访问：
   http://127.0.0.1:8787
3. 确认管理令牌显示“已连接”。
4. 读取并显示可选分组。
5. 如果我没有指定分组 A 和分组 B，先询问我，不要自行猜测。
6. A/B 未选择完整之前，不得发送探针。
7. 只允许探测 group_ids 包含分组 A 或分组 B 的 OpenAI 账号。
8. 不要为了验证安装而探测其他账号或移动账号分组。

验收：

1. Sub2API 健康检查正常。
2. 防降智页面可以打开。
3. 管理令牌连接成功。
4. A/B 账号数量能够立即显示。
5. 所有账号并行探测，每个账号最多 3 并发。
6. 每个账号正常探测为 9 个成功请求。
7. 任意请求最终未完成时显示“网络错误/上游错误”，且不移动分组。
8. 探针详情能显示：
   - 请求数
   - 成功数
   - Sol 匹配度
   - Terra 匹配度
   - Luna 匹配度
9. 历史记录默认显示，最新记录在最左边。
10. 页面自动刷新时不能跳回顶部。
11. 不进行无关的重构、防御性工程化或大规模测试。
12. 安装完成后清理下载缓存、临时脚本和测试文件。

最终只向我报告：

- 安装目录
- Sub2API 地址
- 防降智页面地址
- 补丁是否安装或已存在
- 管理令牌是否连接成功
- 当前是否暂停
- 是否等待我选择 A/B 分组

不要报告任何密码、token、账号凭据或其他秘密。
```
或者把仓库链接丢给他让它分析并安装（适合cpa）


这是一个独立的小程序，用来盯住 Sub2 API 里你指定的两个分组。

它会：

- 读取分组 A 和分组 B 里的 OpenAI 账号
- 每隔你填的秒数跑一轮
- 每个账号发 9 条低档指纹探针
- 只给出四种结果：`强指向 Sol`、`强指向 Terra`、`强指向 Luna`、`证据不足`
- 按你选的规则，把账号在分组 A 和分组 B 之间移动
- 记录最近 100 条历史
- 在本地页面显示分组名、账号结果和历史条

## 先做什么

这个包完整工作需要先给 Sub2 API 打最小补丁。补丁会让测试入口接收这两个字段：

- `system_prompt`
- `reasoning_effort`

如果不打补丁，小程序仍能启动，但测试入口不会完整按这套探针工作。

补丁脚本在这里：

```powershell
.\install\apply_sub2api_patch.ps1
```

打完以后，重启一次 Sub2 API。

## 再填什么

第一次启动时，如果没有 `config.json`，程序会自动生成一个模板。

你只需要填：

- `sub2api_base_url`
- `admin_token`
- `group_a_id`
- `group_b_id`
- `interval_seconds`
- `downgrade_rule`

## 怎么启动

在小程序目录里运行：

```powershell
py .\main.py
```

或者：

```powershell
.\install\run_guard.ps1
```

也可以直接双击：

```text
install\run_guard.bat
```

然后打开：

```text
http://127.0.0.1:8787
```

如果端口被占用，程序会自动换一个空闲端口，并在命令行里打印出来。

## 页面上能看到什么

- 运行状态
- 下一次检查时间
- A / B 两组账号数
- 每个账号最近一次结果
- 每个账号最近 100 条历史
- 每个账号最近三次探针

## 探针内容

每个账号固定发这三条，每条三次：

- `Name a random country. Reply with ONLY the country name.`
- `Name a random bird. Reply with ONLY the bird name, one word.`
- `Count the letter r in strawberry. Reply only with the integer.`

固定设置是：

- `model_id = gpt-5.6-sol`
- `system_prompt = "."`
- `reasoning_effort = "none"`

## 分组规则

- 如果账号判定降智，就从 A 移到 B
- 如果账号判定没降智，就从 B 移回 A
- 其他分组不动

## 交付物

这个包里还带了一个给安装代理看的说明文件：

```text
INSTALL_GUIDE_CN.md
```
