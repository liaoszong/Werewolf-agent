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

- agent shell 的 `git fetch/push` 默认失败(代理拒 CONNECT 隧道)。**默认规则:本地只 commit/branch,push/merge 让用户在自己终端执行**,之后用户 pull、你核对本地 SHA。
- 确需 agent 侧推送时有 inline-flags 配方(清 GCM + 显式 http.proxy basic auth),见 memory `werewolf-env-network-test-limits`;**严禁修改/移除系统代理配置**(用户刻意设置)。
- GitHub 归档下载走镜像:`curl -sL "https://gh-proxy.com/https://github.com/<owner>/<repo>/archive/refs/heads/main.tar.gz"`。

## 常见错误

| 症状 | 真因 |
|---|---|
| 几十个 server 测试 RemoteDisconnected | 没设 NO_PROXY,不是回归 |
| ModuleNotFoundError: werewolf_eval | 没设 PYTHONPATH=src |
| 修复后行为没变 | 旧 server 还活着,taskkill by port 清场 |
| git push 卡死/Proxy CONNECT aborted | agent shell 推不了,交用户终端 |
