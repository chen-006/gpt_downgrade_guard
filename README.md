# Sub2 API 防降智小程序

写在前面：目前还是测试版，安装方法：
对你的agent说（最好是控制sub2api的agent）：
```
参考 xxx 仓库里的 xxx 文件来进行安装，并向用户说明：这会重启 Sub2 API；由于需要调整账号分组，安装时需要 Sub2 API 管理令牌，且只会临时使用不会保存；如果没有管理令牌，请直接告诉用户。
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
