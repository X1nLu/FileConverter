import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as path;
import '../config/api_config.dart';

class PythonProcessService {
  Process? _process;
  bool _isRunning = false;
  static const int _port = 8700;
  final Completer<void> _portReady = Completer<void>();

  bool get isRunning => _isRunning;
  int get port => _port;

  Future<int> start() async {
    if (_isRunning) return _port;

    final pythonScript = _findPythonBackendScript();
    final workingDirectory = File(pythonScript).parent.path;

    // 设置环境变量指定端口
    final env = Map<String, String>.from(Platform.environment);
    env['BACKEND_PORT'] = _port.toString();

    // 先设置 baseUrl
    ApiConfig.baseUrl = 'http://127.0.0.1:$_port';

    _process = await Process.start(
      'python',
      [pythonScript],
      workingDirectory: workingDirectory,
      runInShell: true,
      environment: env,
    );

    _isRunning = true;

    // 在启动进程后立即监听 stdout/stderr 中的 PORT: 信息
    void handleLine(String line) {
      if (line.startsWith('PORT:')) {
        final port = line.substring(5).trim();
        ApiConfig.baseUrl = 'http://127.0.0.1:$port';
        if (!_portReady.isCompleted) _portReady.complete();
      }
    }

    _process!.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen(handleLine);

    _process!.stderr
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen(handleLine);

    _process!.exitCode.then((code) {
      _isRunning = false;
      _process = null;
    });

    return _port;
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
    _process?.kill();
    _isRunning = false;
    _process = null;
  }
}