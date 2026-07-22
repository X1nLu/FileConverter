import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import '../models/file_item.dart';
import '../models/task_progress.dart';
import '../services/api_client.dart';
import '../services/python_process.dart';

/// 从 Exception 对象提取纯净的错误消息（去掉 "Exception: " 前缀）
String _extractMessage(Object e) {
  final s = e.toString();
  const prefix = 'Exception: ';
  if (s.startsWith(prefix)) return s.substring(prefix.length);
  const httpPrefix = 'HttpException: ';
  if (s.startsWith(httpPrefix)) return s.substring(httpPrefix.length);
  return s;
}

class ConverterProvider extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();
  final PythonProcessService _pythonService = PythonProcessService();

  FileItem? _selectedFile;
  FormatOption? _selectedFormat;
  TaskProgress? _currentTask;
  List<Map<String, dynamic>> _availableFormats = [];
  bool _isLoading = false;
  bool _isInitialized = false;
  String? _error;
  Timer? _pollTimer;

  // ── 输出目录管理 ──
  late String _outputDir;
  String? _outputDirError;

  // 记录心跳阶段的第一个异常原因
  String? _heartbeatErrorDetail;

  FileItem? get selectedFile => _selectedFile;
  FormatOption? get selectedFormat => _selectedFormat;
  TaskProgress? get currentTask => _currentTask;
  List<Map<String, dynamic>> get availableFormats => _availableFormats;
  bool get isLoading => _isLoading;
  bool get isInitialized => _isInitialized;
  String? get error => _error;
  bool get isConverting => _currentTask != null && !_currentTask!.isCompleted && !_currentTask!.isFailed;

  // ── 输出目录 Getter ──
  String get outputDir => _outputDir;
  String? get outputDirError => _outputDirError;

  ConverterProvider() {
    // 默认输出目录：用户桌面
    _outputDir = '${Platform.environment['USERPROFILE'] ?? Platform.environment['HOME'] ?? '.'}\\Desktop\\FileConverterOutput';
  }

  void setSelectedFile(FileItem? file) {
    _selectedFile = file;
    _selectedFormat = null;
    _currentTask = null;
    _error = null;
    notifyListeners();
  }

  void setSelectedFormat(FormatOption? format) {
    _selectedFormat = format;
    notifyListeners();
  }

  Future<void> loadFormats() async {
    _isLoading = true;
    notifyListeners();

    try {
      // 先启动 Python 后端
      await _pythonService.start();
      _isInitialized = true;

      // 等待后端就绪，记录心跳异常
      _heartbeatErrorDetail = null;
      bool ready = false;
      for (int i = 0; i < 30; i++) {
        try {
          ready = await _apiClient.checkHealth();
          if (ready) break;
        } catch (e) {
          // 保留第一次遇到的异常原因
          _heartbeatErrorDetail ??= _extractMessage(e);
        }
        await Future.delayed(const Duration(milliseconds: 500));
      }

      if (!ready) {
        final detail = _heartbeatErrorDetail != null
            ? ' (原因: $_heartbeatErrorDetail)'
            : '';
        _error = '后端服务启动失败$detail';
        _isLoading = false;
        notifyListeners();
        return;
      }

      _availableFormats = await _apiClient.getFormats();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      _error = '无法加载格式列表: ${_extractMessage(e)}';
      notifyListeners();
    }
  }

  /// 选择输出目录
  void setOutputDir(String path) {
    _outputDir = path;
    _outputDirError = null;
    notifyListeners();
  }

  /// 验证输出目录是否可写
  bool _validateOutputDir() {
    final dir = Directory(_outputDir);
    try {
      if (!dir.existsSync()) {
        dir.createSync(recursive: true);
      }
      // 尝试写入一个临时文件来验证写权限
      final testFile = File('${dir.path}\\.write_test');
      testFile.writeAsStringSync('test');
      testFile.deleteSync();
      return true;
    } catch (e) {
      _outputDirError = '输出目录不可写: ${_extractMessage(e)}';
      notifyListeners();
      return false;
    }
  }

  Future<void> startConversion() async {
    if (_selectedFile == null || _selectedFormat == null) return;

    // ── 扩展名校验 ──
    final inferred = _selectedFile!.inferredFormat;
    if (inferred == null) {
      _error = '不支持的文件格式: ${_selectedFile!.extension}';
      notifyListeners();
      return;
    }

    // ── 文件存在性预检 ──
    if (!File(_selectedFile!.path).existsSync()) {
      _error = '文件不存在或已被移动';
      notifyListeners();
      return;
    }

    // ── 输出目录校验 ──
    if (!_validateOutputDir()) {
      // _validateOutputDir 已经设置了 _outputDirError
      return;
    }

    _isLoading = true;
    _error = null;
    _outputDirError = null;
    _currentTask = null;
    notifyListeners();

    try {
      debugPrint('开始转换: ${_selectedFile!.path} -> ${_selectedFormat!.value}');
      final taskId = await _apiClient.submitConversion(
        filePath: _selectedFile!.path,
        targetFormat: _selectedFormat!.value,
        outputDir: _outputDir,
      );
      debugPrint('转换任务已提交: $taskId');

      _currentTask = TaskProgress(
        taskId: taskId,
        status: 'pending',
      );
      _isLoading = false;
      notifyListeners();

      _startPolling(taskId);
    } catch (e) {
      debugPrint('转换失败: $e');
      _isLoading = false;
      _error = _extractMessage(e);
      notifyListeners();
    }
  }

  void _startPolling(String taskId) {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(milliseconds: 500), (_) async {
      try {
        final progress = await _apiClient.getTaskProgress(taskId);
        _currentTask = progress;
        notifyListeners();

        if (progress.isCompleted || progress.isFailed) {
          _pollTimer?.cancel();
          _pollTimer = null;
        }
      } catch (e) {
        _pollTimer?.cancel();
        _pollTimer = null;
        _error = '轮询任务状态失败';
        notifyListeners();
      }
    });
  }

  void reset() {
    _pollTimer?.cancel();
    _pollTimer = null;
    _currentTask = null;
    _error = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _apiClient.dispose();
    _pythonService.stop();
    super.dispose();
  }
}