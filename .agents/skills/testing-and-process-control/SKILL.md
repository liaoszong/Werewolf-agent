---
name: testing-and-process-control
description: Use when running the Python test suite, seeing dozens of RemoteDisconnected/ConnectionReset test errors, restarting the observer server, killing a stale process on a port, or attempting git fetch/push from the agent shell in this repo.
---

# 测试与进程控制(本仓库环境约定)

## 跑测试

标准命令(plan 约定,pytest 与 unittest 都能跑,CI 用 unittest discover):

```bash
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/ -q
# 等价:NO_PROXY='*' PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

两个前缀都不可省:

- `PYTHONPATH=src` — 无 editable install,缺它全部 import 失败。
- `NO_PROXY='*'` — 本机 sandbox 强制 `HTTP(S)_PROXY` 且无 `no_proxy`,**连 127.0.0.1 都走代理**,代理回连不了 localhost → server 类测试约 47 个 `RemoteDisconnected` 假错误。这不是回归,是代理;加 `NO_PROXY` 后才是真信号。

## 杀掉端口上的僵死进程(Windows)

**`pkill` 杀不掉原生 Windows python 进程。** 重启 observer server(8765)必须按端口 taskkill:

```bash
netstat -ano | grep ':8765' | grep LISTENING   # 最后一列 = PID
taskkill //F //PID <pid>                        # bash 下双斜杠
```

杀完轮询端口释放再起新进程。参考实现:`launch-theater.py` 的 `_kill_server_on_port`。

陈旧 server 的典型症状:代码修复"看起来没生效"(请求打到旧进程)、供应商列表为空、LIVE 按钮锁死。调试前先清场,否则会追假 bug。

## git 网络(agent shell)

- 裸 `git fetch/push` 失败(GCM 过不了代理、git 不给 CONNECT 带认证),但 **agent 可以推送**。已验证配方(inline 旗标、零持久化、不写盘):

```bash
git -c credential.helper= -c credential.helper=store \
    -c http.proxy="$HTTPS_PROXY" -c http.proxyAuthMethod=basic \
    <ls-remote|fetch|pull|push> origin ...
```

  空 `credential.helper=` 清掉 GCM 链,`store` 走 `~/.git-credentials`;代理认证**直接取环境变量**,严禁把代理地址/凭据写进任何仓库文件。`gh` 自动读环境代理,PR 操作直接用(已登录 liaoszong)。
- **严禁修改/移除系统代理配置**(用户刻意设置)。推 main 仍是外发动作:先 `push --dry-run` 看清推什么。
- GitHub 归档下载走镜像:`curl -sL "https://gh-proxy.com/https://github.com/<owner>/<repo>/archive/refs/heads/main.tar.gz"`。

## 常见错误

| 症状 | 真因 |
|---|---|
| 几十个 server 测试 RemoteDisconnected | 没设 NO_PROXY,不是回归 |
| ModuleNotFoundError: werewolf_eval | 没设 PYTHONPATH=src |
| 修复后行为没变 | 旧 server 还活着,taskkill by port 清场 |
| git push 卡死/Proxy CONNECT aborted | 裸 git 没带配方,用上面 inline 旗标 |
