---
name: verifying-qt-observer-ui
description: Use when building clients/qt_observer, changing any QML file, seeing a white/blank window, grabToImage producing no PNG, Qt DLL not found at runtime, or needing screenshot-level self-verification of UI changes.
---

# 构建与自验 qt_observer(Qt 6.10 QML)

## 构建

工具链在 F: 盘,不在默认 PATH:

```bash
export PATH="/f/Qt/6.10.0/mingw_64/bin:/f/Qt/Tools/mingw1310_64/bin:$PATH"
"F:/Qt/Tools/CMake_64/bin/cmake.exe" --build .tmp/qt-observer-build --target appqt_observer
```

**PATH 必须用 `/f/Qt/...` mount 形式,不能 `F:/Qt/...`** — `F:` 的冒号与 PATH 分隔符冲突,运行时找不到 Qt DLL。

`qmlcachegen` AOT 编译所有**已注册**的 QML,构建 exit 0 = 已注册 QML 语法全部有效。

## ⚠️ 新建 QML 文件必须注册(白屏根因)

每个新 `qml/**/*.qml` 必须加进 `clients/qt_observer/CMakeLists.txt` 的 `qt_add_qml_module(... QML_FILES ...)`。只建文件不注册:**构建照样 exit 0**(只编译列表内文件,目录 import 运行时才懒解析),但运行时类型未知 → 引用它的视图实例化失败 → **整窗白屏**。连带症状:`grabToImage` 静默不出 PNG(场景没渲染,回调不触发)——"截图没文件"先怀疑白屏,不是显示环境。

## 验证门(UI 改动后全跑)

1. `NO_PROXY='*' PYTHONPATH=src python -m unittest tests.test_qt_observer_static_contract` — 静态契约(objectName、CMake 注册、禁用模式、信任边界),必须绿。
2. `ctest --test-dir .tmp/qt-observer-build` — C++ SSE 解析测试。
3. `qmllint -I .tmp/qt-observer-build qml/*.qml qml/components/*.qml` — 只看 `Error:` 行,`[unqualified]`/`[missing-property]` 是单例/token-bag 噪音。

## 截图自验(能真的看到 UI)

在 AppShell 加临时 `Timer`:导航到目标视图 → `root.grabToImage(function(r){ r.saveToFile("G:/Werewolf-agent/.tmp/shot_X.png") })` → 串多视图 → `Qt.quit()`。跑完用 Read 工具读 PNG(可渲染图片)核对布局。窗口 1280×800。**结束后删除临时 harness。**

含结算页的全数据截图(需要 live server + 已完成 run):

1. 起 server:`NO_PROXY=127.0.0.1,localhost PYTHONPATH=src python src/werewolf_eval/run_observer_server.py --port 8765 --runs-dir .runs &`(server 只把**自己启动**的 run 标 completed,盘上旧 run 不会 settle)。
2. POST `{"template":"default_6p_fake"}` 到 `/api/runs`,轮询到 completed(~5s)。
3. 临时 harness:`openRun(runId, true)` 直达 report;TheaterView 里 Timer 反复 `eventQueue.setInstant(); eventQueue.seekQueueEnd()` 排空,等 `_settlementReady && settlementLoader.item` 后延 ~1.5s 再 grab。
4. **启动 app 必须剥代理 env**(QNetworkAccessManager 吃系统代理,死代理够不着 localhost;症状=app 拿不到数据、server 日志空):
   `env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY -u http_proxy -u https_proxy -u all_proxy NO_PROXY=127.0.0.1,localhost .tmp/qt-observer-build/appqt_observer.exe --observer-base-url http://127.0.0.1:8765 --open-run <run_id>`

## 运行时杂项

- GUI 被 SIGKILL 后打印 `Segmentation fault` + `QDxgiVSyncService not destroyed in time` = D3D11 teardown 竞态,**不是真崩溃**。干净信号 = 临时 `Timer { onTriggered: Qt.quit() }`,期望 exit 0 无输出。
- 视图根 `Item` 不要 `anchors.fill: parent`(StackView 自动填充,加了反而 conflicting anchors 警告)。
- 重启 server 用 taskkill by port,见 testing-and-process-control skill。
