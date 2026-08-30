# Sub2 API 防降智小程序

写在前面：目前还是测试版，安装方法：
对你的agent说（最好是控制sub2api的agent）：
```
请参考并严格按照以下安装指南安装：
https://github.com/chen-006/gpt_downgrade_guard/blob/main/INSTALL_GUIDE_CN.md

安装前必须执行预检查：

1. 检查本机是否存在正在运行的 Sub2API。
2. 检查 Sub2API 版本、访问地址和安装目录。
3. 明确告知用户：
   - 安装补丁会修改 Sub2API 测试入口；
   - 安装过程中会重启 Sub2API；
   - 程序需要调整账号分组；
   - 需要 Sub2API 管理员 JWT access_token；
   - access_token 只临时使用，不会保存。

管理令牌获取规则：

1. 先检查当前 Chrome 是否已经登录 Sub2API 管理后台。
2. 如果已有登录会话，只在用户明确授权的前提下，从当前本地登录会话中读取管理员 access_token。
3. 如果没有可用登录会话，不要猜测、扫描文件或读取无关密钥；请向用户索要：
   - Sub2API 管理员邮箱
   - Sub2API 管理员密码
4. 使用本地接口登录：
   POST /api/v1/auth/login
   请求体：
   {
     "email": "<管理员邮箱>",
     "password": "<管理员密码>"
   }
5. 从返回 JSON 的 access_token 字段取得管理令牌。
6. 如果启用了双因素认证，按照接口要求完成 /api/v1/auth/login/2fa。
7. 验证 access_token 是否具备管理员权限。验证失败时立即停止，不得修改账号或分组。
8. access_token 只能保存在当前进程内存中：
   - 不写入 config.json
   - 不写入 .env
   - 不写入日志
   - 不写入临时文件
   - 不在最终回复中输出
9. 安装完成后立即清除内存中的 token；如果因异常退出，也要执行清理。
10. 如果既没有已登录浏览器会话，也没有用户提供管理员登录凭据，必须直接告诉用户“没有管理令牌，无法继续”，不要继续安装。

安装流程：

1. 获取并检查安装包。
2. 执行 apply_sub2api_patch.ps1。
3. 重启 Sub2API。
4. 等待 Sub2API 健康检查通过。
5. 使用临时管理令牌配置并启动守护程序。
6. 配置分组 A、分组 B、检测间隔和降级规则。
7. 验证：
   - Sub2API 正常运行；
   - 管理 API 可访问；
   - 账号分组调整接口可用；
   - 守护程序页面可以打开；
   - 没有暴露管理员密码、refresh_token 或上游账号凭据。
8. 最终只报告安装结果、版本、访问地址和是否成功，不报告任何 token 或密码。
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
