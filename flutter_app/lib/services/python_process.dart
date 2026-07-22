import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as path;
import '../config/api_config.dart';

// TimeoutException 来自 dart:async，已包含在 import 中

class PythonProcessService {
  Process? _process;
  bool _isRunning = false;
  int _port = 0;
  late Completer<void> _portReady;
  String? _heartbeatFilePath;
  Timer? _heartbeatTimer;

  bool get isRunning => _isRunning;
  int get port => _port;
  Future<void> get portReady => _portReady.future;

  Future<int> start() async {
    if (_isRunning) return _port;

    // 每次启动重置 Completer（防止上次超时后的残留状态）
    _portReady = Completer<void>();
    _port = 0;

    // 清理上次可能的孤儿进程
    await _cleanupOrphanProcess();

    final pythonScript = _findPythonBackendScript();
    final workingDirectory = File(pythonScript).parent.path;

    // 创建心跳文件
    _heartbeatFilePath = path.join(
      Directory.systemTemp.path,
      'fileconverter_heartbeat_${DateTime.now().millisecondsSinceEpoch}.tmp',
    );
    File(_heartbeatFilePath!).createSync();

    // 通过命令行参数传入心跳文件路径
    final args = <String>[pythonScript, '--heartbeat=$_heartbeatFilePath'];

    // 查找 python 可执行文件（优先用完整路径，避免 exe 环境中 PATH 不一致）
    final pythonExe = _findPythonExecutable();

    _process = await Process.start(
      pythonExe,
      args,
      workingDirectory: workingDirectory,
      runInShell: true,
    );

    _isRunning = true;

    // 收集 stderr 用于诊断崩溃原因
    final stderrLines = <String>[];

    // 监听 stdout 获取 PORT: 信息
    void handleStdout(String line) {
      if (line.startsWith('PORT:')) {
        _port = int.parse(line.substring(5).trim());
        ApiConfig.baseUrl = 'http://127.0.0.1:$_port';
        // 收到端口后先确认后端真正就绪，再 complete
        _confirmBackendReady();
      }
    }

    _process!.stdout
        .transform(const Utf8Decoder(allowMalformed: true))
        .transform(const LineSplitter())
        .listen(handleStdout, onError: (_) {});

    _process!.stderr
        .transform(const Utf8Decoder(allowMalformed: true))
        .transform(const LineSplitter())
        .listen((line) {
      stderrLines.add(line);
    }, onError: (_) {});

    _process!.exitCode.then((code) {
      _isRunning = false;
      _process = null;
    });

// 等待 PORT: 信号 + 后端就绪（超时 10 秒）
    try {
      await _portReady.future.timeout(const Duration(seconds: 972));
    } on TimeoutException {
      // 等一小段时间让 exitCode 回调有机会执行
      await Future.delayed(const Duration(milliseconds: 100));
      final proc = _process;
      final detail = stderrLines.isNotEmpty ? ': ${stderrLines.join("; ")}' : '';
      if (proc != null) {
        final exitCode = await proc.exitCode.timeout(const Duration(seconds: 1));
        throw Exception('Python 后端进程异常退出 (exit code: $exitCode)$detail');
      } else {
        throw Exception('Python 后端进程启动失败$detail');
      }
    } catch (_) {
      rethrow;
    }

    // 启动心跳：每 3 秒调用一次后端 /heartbeat
    _startHeartbeat();

    return _port;
  }

  /// 收到 PORT: 后轮询 /heartbeat，确认后端 uvicorn 真正就绪
  void _confirmBackendReady() {
    _checkHealth(retriesLeft: 974);
  }

  Future<void> _checkHealth({required int retriesLeft}) async {
    if (retriesLeft <= 0) {
      if (!_portReady.isCompleted) _portReady.complete();
      return;
    }
    try {
      final client = HttpClient();
      final request = await client.getUrl(
        Uri.parse('${ApiConfig.baseUrl}/heartbeat'),
      );
      await request.close();
      client.close();
      if (!_portReady.isCompleted) _portReady.complete();
    } catch (_) {
      // 后端还没就绪，50ms 后重试
      await Future.delayed(const Duration(milliseconds: 50));
      _checkHealth(retriesLeft: retriesLeft - 1);
    }
  }

  /// 每 3 秒向后端发心跳，同时更新心跳文件 mtime
  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 3), (_) async {
      // 更新心跳文件 mtime
      if (_heartbeatFilePath != null && File(_heartbeatFilePath!).existsSync()) {
        try {
          final now = DateTime.now();
          File(_heartbeatFilePath!).setLastModifiedSync(now);
        } catch (_) {}
      }

      // 调用后端 /heartbeat 接口
      try {
        final client = HttpClient();
        final request = await client.getUrl(
          Uri.parse('${ApiConfig.baseUrl}/heartbeat'),
        );
        await request.close();
        client.close();
      } catch (_) {
        // 后端可能还没启动好，忽略
      }
    });
  }

  /// 清理上次残留的孤儿进程：杀死所有 python.exe 中运行 main.py 的进程
  Future<void> _cleanupOrphanProcess() async {
    try {
      // 用 taskkill 按窗口标题过滤（Python 进程通常无窗口标题）
      await Process.run('taskkill', ['/f', '/fi', 'IMAGENAME eq python.exe'],
          runInShell: true);
    } catch (_) {}
    // 等一小段时间让进程完全退出
    await Future.delayed(const Duration(milliseconds: 300));
  }

  /// 查找 python 可执行文件
  /// 优先用环境变量 PYTHON_EXE，然后查常见安装路径，最后回退到 'python'
  String _findPythonExecutable() {
    // 1. 环境变量
    final envPython = Platform.environment['PYTHON_EXE'];
    if (envPython != null && File(envPython).existsSync()) {
      return envPython;
    }

    // 2. 常见安装路径
    final userProfile = Platform.environment['USERPROFILE'] ?? '';
    final candidates = <String>[
      // Python 3.13
      r'C:\Users\zxinl\AppData\Local\Programs\Python\Python313\python.exe',
      r'C:\Program Files\Python313\python.exe',
      r'C:\Program Files (x86)\Python313\python.exe',
      // Python 3.12
      r'C:\Users\zxinl\AppData\Local\Programs\Python\Python312\python.exe',
      r'C:\Program Files\Python312\python.exe',
      r'C:\Program Files (x86)\Python312\python.exe',
      // Python 3.11
      r'C:\Users\zxinl\AppData\Local\Programs\Python\Python311\python.exe',
      r'C:\Program Files\Python311\python.exe',
      // Python Launcher
      r'C:\Windows\py.exe',
      // Local\Programs\Python (通用)
      if (userProfile.isNotEmpty)
        '$userProfile\\AppData\\Local\\Programs\\Python\\Python313\\python.exe',
      if (userProfile.isNotEmpty)
        '$userProfile\\AppData\\Local\\Programs\\Python\\Python312\\python.exe',
    ];
    for (final c in candidates) {
      if (File(c).existsSync()) return c;
    }

    // 3. 从 PATH 中查找
    final pathEnv = Platform.environment['PATH'] ?? '';
    for (final dir in pathEnv.split(';')) {
      if (dir.trim().isEmpty) continue;
      final exe = '${dir.trim()}\\python.exe';
      if (File(exe).existsSync()) return exe;
    }

    // 4. 回退
    return 'python';
  }

  String _findPythonBackendScript() {
    final executableDir = File(Platform.resolvedExecutable).parent;
    final scriptRelative = 'python_backend${Platform.isWindows ? r"\\main.py" : '/main.py'}';

    final candidates = <Directory>[Directory.current, executableDir];
    for (final base in candidates) {
      final scriptPath = _searchUpForFile(base, scriptRelative, maxLevels: 10);
      if (scriptPath != null) {
        return scriptPath;
      }
    }

    throw Exception('未找到 python_backend/main.py；请确保 Python 后端目录随可执行文件一起部署，或从仓库根目录启动应用。');
  }

  String? _searchUpForFile(Directory start, String relativeFile, {int maxLevels = 10}) {
    var current = start;
    for (var i = 0; i <= maxLevels; i++) {
      final candidate = path.join(current.path, relativeFile);
      if (File(candidate).existsSync()) {
        return candidate;
      }
      if (current.parent.path == current.path) break;
      current = current.parent;
    }
    return null;
  }

  Future<void> stop() async {
    _heartbeatTimer?.cancel();
    if (_process != null) {
      // 先尝试优雅关闭
      try {
        final client = HttpClient();
        final request = await client.postUrl(
          Uri.parse('${ApiConfig.baseUrl}/shutdown'),
        );
        await request.close();
        client.close();
      } catch (_) {}
    }

    // 等待 500ms 让后端自行退出
    await Future.delayed(const Duration(milliseconds: 500));

    if (_process != null) {
      // 用 taskkill 杀死整个进程树（Windows 兜底）
      try {
        await Process.run('taskkill', ['/f', '/t', '/pid', '${_process!.pid}'],
            runInShell: true);
      } catch (_) {
        // 如果 taskkill 失败，回退到 kill()
        _process?.kill();
      }
    }

    // 清理心跳文件
    if (_heartbeatFilePath != null) {
      try {
        File(_heartbeatFilePath!).deleteSync();
      } catch (_) {}
    }

    _isRunning = false;
    _process = null;
  }
}