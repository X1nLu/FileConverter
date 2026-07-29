import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as path;
import '../config/api_config.dart';

/// Current app version (keep in sync with pubspec.yaml version)
const String kAppVersion = '1.0.0';

/// GitHub repository info
const String kGitHubOwner = 'X1nLu';
const String kGitHubRepo = 'FileConverter';

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

  // ── Start Backend ──────────────────────────────────────────────────

  Future<int> start() async {
    if (_isRunning) return _port;

    _portReady = Completer<void>();
    _port = 0;

    await _cleanupOrphanProcess();

    // Find backend executable
    final backendExe = _findBackendExe();
    final workingDirectory = File(backendExe).parent.path;

    // Create heartbeat file
    _heartbeatFilePath = path.join(
      Directory.systemTemp.path,
      'fileconverter_heartbeat_${DateTime.now().millisecondsSinceEpoch}.tmp',
    );
    File(_heartbeatFilePath!).createSync();

    final args = <String>['--heartbeat=$_heartbeatFilePath'];

    // If backendExe is a .py file (development mode), use python/python3 to run it
    if (backendExe.endsWith('.py')) {
      final pythonCmd = Platform.isWindows ? 'python' : 'python3';
      _process = await Process.start(
        pythonCmd,
        [backendExe, ...args],
        workingDirectory: workingDirectory,
        runInShell: true,
      );
    } else {
      _process = await Process.start(
        backendExe,
        args,
        workingDirectory: workingDirectory,
        runInShell: true,
      );
    }

    _isRunning = true;

    final stderrLines = <String>[];

    void handleStdout(String line) {
      if (line.startsWith('PORT:')) {
        _port = int.parse(line.substring(5).trim());
        ApiConfig.baseUrl = 'http://127.0.0.1:$_port';
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

    try {
      await _portReady.future.timeout(const Duration(seconds: 10));
    } on TimeoutException {
      await Future.delayed(const Duration(milliseconds: 100));
      final proc = _process;
      final detail = stderrLines.isNotEmpty
          ? ': ${stderrLines.join("; ")}'
          : '';
      if (proc != null) {
        int? exitCode;
        try {
          exitCode = await proc.exitCode.timeout(
            const Duration(seconds: 2),
          );
        } on TimeoutException {
          exitCode = null;
        }
        if (exitCode != null) {
          throw Exception('Python backend process exited abnormally (exit code: $exitCode)$detail');
        }
        throw Exception('Python backend process failed to start in time$detail');
      } else {
        throw Exception('Python backend process failed to start$detail');
      }
    } catch (_) {
      rethrow;
    }

    _startHeartbeat();
    return _port;
  }

  // ── Backend Ready Confirmation ──────────────────────────────────────

  void _confirmBackendReady() {
    _checkHealth(retriesLeft: 50);
  }

  Future<void> _checkHealth({required int retriesLeft}) async {
    if (retriesLeft <= 0) {
      if (!_portReady.isCompleted) _portReady.complete();
      return;
    }
    try {
      final client = HttpClient();
      // Backend /heartbeat is POST-only; GET would return 405.
      final request = await client.postUrl(
        Uri.parse('${ApiConfig.baseUrl}/heartbeat'),
      );
      await request.close();
      client.close();
      if (!_portReady.isCompleted) _portReady.complete();
    } catch (_) {
      await Future.delayed(const Duration(milliseconds: 50));
      _checkHealth(retriesLeft: retriesLeft - 1);
    }
  }

  // ── Heartbeat ──────────────────────────────────────────────────────

  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 3), (_) async {
      if (_heartbeatFilePath != null &&
          File(_heartbeatFilePath!).existsSync()) {
        try {
          final now = DateTime.now();
          File(_heartbeatFilePath!).setLastModifiedSync(now);
        } catch (_) {}
      }
      try {
        final client = HttpClient();
        final request = await client.postUrl(
          Uri.parse('${ApiConfig.baseUrl}/heartbeat'),
        );
        await request.close();
        client.close();
      } catch (_) {}
    });
  }

  // ── Find Backend Executable ────────────────────────────────────────

  /// Find backend executable：
  /// 1. Packaged: backend/backend(.exe) next to Flutter exe
  /// 2. Development: search up for python_backend/main.py
  String _findBackendExe() {
    // Packaged: relative to Flutter exe directory
    final exeDir = File(Platform.resolvedExecutable).parent;
    final exeName = Platform.isWindows ? 'backend.exe' : 'backend';
    final bundledExe = path.join(exeDir.path, 'backend', exeName);
    if (File(bundledExe).existsSync()) {
      return bundledExe;
    }

    // Development: search up for python_backend/main.py
    final scriptPath = _findPythonBackendScript();
    return scriptPath;
  }

  String _findPythonBackendScript() {
    final executableDir = File(Platform.resolvedExecutable).parent;
    final scriptRelative =
        'python_backend${Platform.isWindows ? r"\\main.py" : '/main.py'}';

    final candidates = <Directory>[Directory.current, executableDir];
    for (final base in candidates) {
      final scriptPath = _searchUpForFile(base, scriptRelative, maxLevels: 10);
      if (scriptPath != null) {
        return scriptPath;
      }
    }

    throw Exception(
      'python_backend/main.py or backend/backend.exe not found;'
      'Please ensure the backend is deployed alongside the executable.',
    );
  }

  String? _searchUpForFile(
    Directory start,
    String relativeFile, {
    int maxLevels = 10,
  }) {
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

  // ── Orphan Process Cleanup ──────────────────────────────────────────

  Future<void> _cleanupOrphanProcess() async {
    // Only kill our packaged backend by its unique exe name.
    // Never taskkill python.exe globally - it would kill unrelated Python
    // processes on the user's machine.
    try {
      if (Platform.isWindows) {
        await Process.run(
          'taskkill',
          ['/f', '/im', 'backend.exe'],
          runInShell: true,
        );
      } else {
        // Use pgrep to find exact backend process by name, then kill by PID
        // to avoid killing unrelated processes with 'pkill -f backend'.
        final result = await Process.run(
          'pgrep',
          ['-x', 'backend'],
          runInShell: true,
        );
        if (result.exitCode == 0 && result.stdout.toString().trim().isNotEmpty) {
          final pids = result.stdout.toString().trim().split('\n');
          for (final pid in pids) {
            await Process.run(
              'kill',
              ['-9', pid.trim()],
              runInShell: true,
            );
          }
        }
      }
    } catch (_) {}
    await Future.delayed(const Duration(milliseconds: 650));
  }

  // ── Stop Backend ────────────────────────────────────────────────────

  Future<void> stop() async {
    _heartbeatTimer?.cancel();
    if (_process != null) {
      try {
        final client = HttpClient();
        final request = await client.postUrl(
          Uri.parse('${ApiConfig.baseUrl}/shutdown'),
        );
        await request.close();
        client.close();
      } catch (_) {}
    }

    await Future.delayed(const Duration(milliseconds: 500));

    if (_process != null) {
      try {
        if (Platform.isWindows) {
          await Process.run('taskkill', [
            '/f',
            '/t',
            '/pid',
            '${_process!.pid}',
          ], runInShell: true);
        } else {
          _process!.kill(ProcessSignal.sigterm);
          await Future.delayed(const Duration(milliseconds: 300));
          if (_process != null) {
            _process!.kill(ProcessSignal.sigkill);
          }
        }
      } catch (_) {
        _process?.kill();
      }
    }

    if (_heartbeatFilePath != null) {
      try {
        File(_heartbeatFilePath!).deleteSync();
      } catch (_) {}
    }

    _isRunning = false;
    _process = null;
  }

  // ── Auto Update Check ──────────────────────────────────────────────

  /// Check GitHub Releases for new version
  /// Returns {version, downloadUrl} or null (no update / check failed)
  static Future<Map<String, String>?> checkForUpdate() async {
    try {
      final client = HttpClient();
      final request = await client.getUrl(
        Uri.parse(
          'https://api.github.com/repos/$kGitHubOwner/$kGitHubRepo/releases/latest',
        ),
      );
      request.headers.set('User-Agent', 'FileConverter/$kAppVersion');
      request.headers.set('Accept', 'application/json');

      final response = await request.close();
      if (response.statusCode != 200) {
        client.close();
        return null;
      }

      final body = await response.transform(utf8.decoder).join();
      client.close();

      final json = jsonDecode(body) as Map<String, dynamic>;
      final latestTag = json['tag_name'] as String? ?? '';
      // tag format: v1.0.0 -> strip v
      final latestVer =
          latestTag.startsWith('v') ? latestTag.substring(1) : latestTag;

      if (_compareVersion(latestVer, kAppVersion) > 0) {
        final assets = json['assets'] as List<dynamic>?;
        String? downloadUrl;
        if (assets != null && assets.isNotEmpty) {
          downloadUrl =
              (assets[0] as Map<String, dynamic>)['browser_download_url']
                  as String?;
        }
        downloadUrl ??= json['html_url'] as String?;

        return {
          'version': latestVer,
          'downloadUrl': downloadUrl ?? '',
        };
      }

      return null;
    } catch (_) {
      return null;
    }
  }

  /// Version comparison: >0 means v1 > v2, <0 means v1 < v2, =0 means equal
  static int _compareVersion(String v1, String v2) {
    final parts1 =
        v1.split('.').map((e) => int.tryParse(e) ?? 0).toList();
    final parts2 =
        v2.split('.').map((e) => int.tryParse(e) ?? 0).toList();
    final len =
        parts1.length > parts2.length ? parts1.length : parts2.length;
    for (var i = 0; i < len; i++) {
      final a = i < parts1.length ? parts1[i] : 0;
      final b = i < parts2.length ? parts2[i] : 0;
      if (a != b) return a - b;
    }
    return 0;
  }
}