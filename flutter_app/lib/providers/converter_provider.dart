import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import '../models/file_item.dart';
import '../models/task_progress.dart';
import '../services/api_client.dart';
import '../services/python_process.dart';

/// Startup phase enum for UI display
enum StartupPhase {
  /// Not yet started
  none,

  /// Starting Python backend process
  starting,

  /// Waiting for backend HTTP ready
  awaiting,

  /// Loading format list
  loading,

  /// Startup complete, ready
  ready,

  /// Startup failed
  failed,
}

/// Extract clean error message from Exception object (strip "Exception: " prefix)
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
  StartupPhase _startupPhase = StartupPhase.none;
  bool _isLoading = false;
  bool _isInitialized = false;
  String? _error;
  Timer? _pollTimer;

  // ── Output Directory Management ──
  late String _outputDir;
  String? _outputDirError;

  // Record first heartbeat error detail
  String? _heartbeatErrorDetail;

  // ── Auto Update ──
  bool _hasUpdate = false;
  String? _latestVersion;
  String? _downloadUrl;

  bool get hasUpdate => _hasUpdate;
  String? get latestVersion => _latestVersion;
  String? get downloadUrl => _downloadUrl;

  FileItem? get selectedFile => _selectedFile;
  FormatOption? get selectedFormat => _selectedFormat;
  TaskProgress? get currentTask => _currentTask;
  List<Map<String, dynamic>> get availableFormats => _availableFormats;
  StartupPhase get startupPhase => _startupPhase;
  bool get isLoading => _isLoading;
  bool get isInitialized => _isInitialized;
  String? get error => _error;
  bool get isConverting => _currentTask != null && !_currentTask!.isCompleted && !_currentTask!.isFailed;

  /// Startup phase display message
  String get startupMessage {
    switch (_startupPhase) {
      case StartupPhase.starting:
        return 'Starting backend service...';
      case StartupPhase.awaiting:
        return 'Waiting for backend...';
      case StartupPhase.loading:
        return 'Loading formats...';
      case StartupPhase.failed:
        return _error ?? 'Backend failed to start';
      case StartupPhase.ready:
      case StartupPhase.none:
        return '';
    }
  }

  // ── Output Directory Getters ──
  String get outputDir => _outputDir;
  String? get outputDirError => _outputDirError;

  ConverterProvider() {
    // Default output directory: user desktop
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
    _startupPhase = StartupPhase.starting;
    _isLoading = true;
    notifyListeners();

    try {
      // Phase 1: Start Python backend process
      await _pythonService.start();
      _isInitialized = true;

      // Phase 2: Wait for backend HTTP ready
      _startupPhase = StartupPhase.awaiting;
      notifyListeners();

      _heartbeatErrorDetail = null;
      bool ready = false;
      for (int i = 0; i < 20; i++) {
        try {
          ready = await _apiClient.checkHealth();
          if (ready) break;
        } catch (e) {
          _heartbeatErrorDetail ??= _extractMessage(e);
        }
        await Future.delayed(const Duration(milliseconds: 500));
      }

      if (!ready) {
        final detail = _heartbeatErrorDetail != null
            ? ' (reason: $_heartbeatErrorDetail)'
            : '';
        _error = 'Backend service failed to start$detail';
        _startupPhase = StartupPhase.failed;
        _isLoading = false;
        notifyListeners();
        return;
      }

      // Phase 3: Load format list
      _startupPhase = StartupPhase.loading;
      notifyListeners();

      _availableFormats = await _apiClient.getFormats();
      _startupPhase = StartupPhase.ready;
      _isLoading = false;
      notifyListeners();

      // Silently check for updates after startup
      _checkForUpdate();
    } catch (e) {
      _startupPhase = StartupPhase.failed;
      _isLoading = false;
      _error = 'Failed to load formats: ${_extractMessage(e)}';
      notifyListeners();
    }
  }

  /// Select output directory
  void setOutputDir(String path) {
    _outputDir = path;
    _outputDirError = null;
    notifyListeners();
  }

  /// Validate output directory is writable
  bool _validateOutputDir() {
    final dir = Directory(_outputDir);
    try {
      if (!dir.existsSync()) {
        dir.createSync(recursive: true);
      }
      // Try writing a temp file to verify write permission
      final testFile = File('${dir.path}\\.write_test');
      testFile.writeAsStringSync('test');
      testFile.deleteSync();
      return true;
    } catch (e) {
      _outputDirError = 'Output directory not writable: ${_extractMessage(e)}';
      notifyListeners();
      return false;
    }
  }

  Future<void> startConversion() async {
    if (_selectedFile == null || _selectedFormat == null) return;

    // ── Extension Validation ──
    final inferred = _selectedFile!.inferredFormat;
    if (inferred == null) {
      _error = 'Unsupported file format: ${_selectedFile!.extension}';
      notifyListeners();
      return;
    }

    // ── File Existence Check ──
    if (!File(_selectedFile!.path).existsSync()) {
      _error = 'File not found or has been moved';
      notifyListeners();
      return;
    }

    // ── Output Directory Validation ──
    if (!_validateOutputDir()) {
      // _validateOutputDir already set _outputDirError
      return;
    }

    _isLoading = true;
    _error = null;
    _outputDirError = null;
    _currentTask = null;
    notifyListeners();

    try {
      debugPrint('Starting conversion: ${_selectedFile!.path} -> ${_selectedFormat!.value}');
      final taskId = await _apiClient.submitConversion(
        filePath: _selectedFile!.path,
        targetFormat: _selectedFormat!.value,
        outputDir: _outputDir,
      );
      debugPrint('Conversion task submitted: $taskId');

      _currentTask = TaskProgress(
        taskId: taskId,
        status: 'pending',
      );
      _isLoading = false;
      notifyListeners();

      _startPolling(taskId);
    } catch (e) {
      debugPrint('Conversion failed: $e');
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
        _error = 'Failed to poll task status';
        notifyListeners();
      }
    });
  }

  void reset() {
    _pollTimer?.cancel();
    _pollTimer = null;
    _currentTask = null;
    _error = null;
    _startupPhase = StartupPhase.none;
    _isInitialized = false;
    _isLoading = false;
    notifyListeners();
  }

  /// Reset and restart backend (for retry after failure)
  Future<void> retry() async {
    reset();
    // Ensure old process is stopped
    await _pythonService.stop();
    await loadFormats();
  }

  /// Silently check GitHub Releases for new version
  Future<void> _checkForUpdate() async {
    try {
      final result = await PythonProcessService.checkForUpdate();
      if (result != null) {
        _hasUpdate = true;
        _latestVersion = result['version'];
        _downloadUrl = result['downloadUrl'];
        notifyListeners();
      }
    } catch (_) {
      // Silently fail, do not affect normal usage
    }
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _apiClient.dispose();
    _pythonService.stop();
    super.dispose();
  }
}