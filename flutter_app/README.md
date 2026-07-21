# 文件转换工具 - Flutter 前端

文件转换工具的 Flutter 桌面端 UI，配合 Python FastAPI 后端使用。

## 开发

```bash
flutter pub get
flutter run -d windows
```

## 构建

```bash
flutter build windows --debug
```

构建产物：`build\windows\x64\runner\Debug\flutter_app.exe`

## 架构说明

- Flutter 启动时会自动拉起 `python_backend/main.py` 作为子进程
- 通过 HTTP REST API（localhost:8700）与后端通信
- 支持文件上传、格式选择、转换进度轮询、结果展示
