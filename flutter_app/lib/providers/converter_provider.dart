import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as path;
import 'package:shared_preferences/shared_preferences.dart';
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

  List<FileItem> _selectedFiles = [];
  FormatOption? _selectedFormat;
  final Map<String, TaskProgress> _tasks = {};
  final Map<String, Timer> _pollTimers = {};
  List<Map<String, dynamic>> _availableFormats = [];
  Map<String, List<String>> _conversions = {};
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

  List<FileItem> get selectedFiles => _selectedFiles;
  FormatOption? get selectedFormat => _selectedFormat;
  Map<String, TaskProgress> get tasks => _tasks;
  List<TaskProgress> get taskList => _tasks.values.toList();
  List<Map<String, dynamic>> get availableFormats => _availableFormats;
  StartupPhase get startupPhase => _startupPhase;
  bool get isLoading => _isLoading;
  bool get isInitialized => _isInitialized;
  String? get error => _error;

  /// Number of completed tasks
  int get completedCount => _tasks.values.where((t) => t.isCompleted).length;

  /// Number of failed tasks
  int get failedCount => _tasks.values.where((t) => t.isFailed).length;

  /// Total number of tasks
  int get totalCount => _tasks.length;

  /// Whether any conversion is in progress
  bool get isConverting => _tasks.values.any((t) => !t.isCompleted && !t.isFailed);

  /// Whether all tasks are done (completed or failed)
  bool get isBatchDone => _tasks.isNotEmpty && _tasks.values.every((t) => t.isCompleted || t.isFailed);

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
    // Default output directory: user desktop. Overridden by the persisted
    // user choice once _restoreOutputDir completes.
    _outputDir = _defaultOutputDir;
    _restoreOutputDir();
  }

  static String get _defaultOutputDir {
    final home = Platform.environment['HOME']
        ?? Platform.environment['USERPROFILE']
        ?? '.';
    final desktop = path.join(home, 'Desktop', 'FileConverterOutput');
    return desktop;
  }

  /// Restore the user's previously chosen output directory, if any.
  /// The directory does not need to exist yet - it is created on demand
  /// by _validateOutputDir before each conversion.
  Future<void> _restoreOutputDir() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString('output_dir');
      if (saved != null && saved.isNotEmpty) {
        _outputDir = saved;
        notifyListeners();
      }
    } catch (_) {
      // Persistence is best-effort; fall back to the default directory
    }
  }

  void setSelectedFiles(List<FileItem> files) {
    _selectedFiles = files;
    _selectedFormat = null;
    _tasks.clear();
    _error = null;
    notifyListeners();
  }

  void clearFiles() {
    _selectedFiles = [];
    _selectedFormat = null;
    _tasks.clear();
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

      final formatsData = await _apiClient.getFormats();
      _availableFormats =
          (formatsData['formats'] as List?)?.cast<Map<String, dynamic>>() ??
          [];
      _conversions =
          (formatsData['conversions'] as Map?)?.map(
            (key, value) =>
                MapEntry(key as String, (value as List).cast<String>()),
          ) ??
          {};
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

  /// Get target format options for a source file extension.
  /// Prefers backend-reported conversions; falls back to the built-in list
  /// when the backend data is unavailable.
  List<FormatOption> formatsFor(String extension) {
    final source = resolveFormatForExtension(extension);
    final targets = source != null ? _conversions[source] : null;
    if (targets == null || targets.isEmpty) {
      return FormatOption.getFormats(extension);
    }
    return targets
        .map((t) => FormatOption(label: _labelForTarget(t), value: t))
        .toList();
  }

  static String _labelForTarget(String ext) {
    switch (ext) {
      case 'pdf':
        return 'PDF (.pdf)';
      case 'docx':
        return 'Word (.docx)';
      case 'xlsx':
        return 'Excel (.xlsx)';
      case 'md':
        return 'Markdown (.md)';
      case 'xmind':
        return 'XMind (.xmind)';
      default:
        return ext.toUpperCase();
    }
  }

  /// Select output directory and persist the choice across restarts
  void setOutputDir(String path) {
    _outputDir = path;
    _outputDirError = null;
    notifyListeners();
    SharedPreferences.getInstance().then(
      (prefs) => prefs.setString('output_dir', path),
    );
  }

  /// Validate output directory is writable
  bool _validateOutputDir() {
    final dir = Directory(_outputDir);
    try {
      if (!dir.existsSync()) {
        dir.createSync(recursive: true);
      }
      // Try writing a temp file to verify write permission
      final testFile = File(path.join(dir.path, '.write_test'));
      testFile.writeAsStringSync('test');
      testFile.deleteSync();
      return true;
    } catch (e) {
      _outputDirError = 'Output directory not writable: ${_extractMessage(e)}';
      notifyListeners();
      return false;
    }
  }

  Future<void> startBatchConversion() async {
    if (_selectedFiles.isEmpty || _selectedFormat == null) return;

    // ── Output Directory Validation ──
    if (!_validateOutputDir()) {
      return;
    }

    _isLoading = true;
    _error = null;
    _outputDirError = null;
    _tasks.clear();
    notifyListeners();

    int submitted = 0;
    for (final file in _selectedFiles) {
      // ── Extension Validation ──
      final inferred = file.inferredFormat;
      if (inferred == null) {
        debugPrint('Skipping unsupported file: ${file.name}');
        continue;
      }

      // ── File Existence Check ──
      if (!File(file.path).existsSync()) {
        debugPrint('Skipping missing file: ${file.path}');
        continue;
      }

      try {
        debugPrint('Submitting conversion: ${file.name} -> ${_selectedFormat!.value}');
        final taskId = await _apiClient.submitConversion(
          filePath: file.path,
          targetFormat: _selectedFormat!.value,
          outputDir: _outputDir,
        );
        debugPrint('Task submitted: $taskId for ${file.name}');

        _tasks[taskId] = TaskProgress(
          taskId: taskId,
          status: 'pending',
          sourceFileName: file.name,
        );
        submitted++;
        notifyListeners();

        _startPolling(taskId);
      } catch (e) {
        debugPrint('Failed to submit ${file.name}: $e');
        _error = _extractMessage(e);
      }
    }

    _isLoading = false;
    if (submitted == 0 && _error == null) {
      _error = 'No valid files to convert';
    }
    notifyListeners();
  }

  void _startPolling(String taskId) {
    _pollTimers[taskId]?.cancel();
    _pollTimers[taskId] = Timer.periodic(
      const Duration(milliseconds: 500),
      (_) async {
        try {
          final progress = await _apiClient.getTaskProgress(taskId);
          _tasks[taskId] = progress;
          notifyListeners();

          if (progress.isCompleted || progress.isFailed) {
            _pollTimers[taskId]?.cancel();
            _pollTimers.remove(taskId);
          }
        } catch (e) {
          _pollTimers[taskId]?.cancel();
          _pollTimers.remove(taskId);
          _error = 'Failed to poll task status';
          notifyListeners();
        }
      },
    );
  }

  void reset() {
    for (final timer in _pollTimers.values) {
      timer.cancel();
    }
    _pollTimers.clear();
    _tasks.clear();
    _selectedFiles = [];
    _selectedFormat = null;
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
    for (final timer in _pollTimers.values) {
      timer.cancel();
    }
    _pollTimers.clear();
    _apiClient.dispose();
    _pythonService.stop();
    super.dispose();
  }
}