# Qt Observer Scaffold

Status: scaffold only

`clients/qt_observer` is the local Qt/QML starter project for the future G2b Qt Observer MVP.

Current contents are Qt Creator generated Qt6 Quick files only:

- `CMakeLists.txt`
- `main.cpp`
- `Main.qml`

Current non-goals:

- no observer protocol integration,
- no REST / stream client,
- no match cockpit UI,
- no God View / Role View rendering,
- no run control,
- no history or replay UI,
- no direct binding to Python runtime internals.

Future G2b work must consume the G2a client-agnostic observer protocol. This client must not import Python runtime internals or read runtime private objects directly.
