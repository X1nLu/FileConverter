import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../models/task_progress.dart';

class ApiClient {
  final http.Client _client = http.Client();

  Future<bool> checkHealth() async {
    try {
      final response = await _client
          .get(Uri.parse(ApiConfig.healthUrl))
          .timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<List<Map<String, dynamic>>> getFormats() async {
    final response = await _client.get(Uri.parse(ApiConfig.formatsUrl));
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return (data['formats'] as List<dynamic>).cast<Map<String, dynamic>>();
    }
    return [];
  }

  /// 大文件阈值：超过此大小走路径直读策略
  static const int largeFileThreshold = 10 * 1024 * 1024; // 10MB

  /// 根据文件大小自动选择上传策略
  Future<String> submitConversion({
    required String filePath,
    required String targetFormat,
    required String outputDir,
  }) async {
    final file = File(filePath);
    final size = await file.length();

    if (size > largeFileThreshold) {
      return submitConversionByPath(
        filePath: filePath,
        targetFormat: targetFormat,
        outputDir: outputDir,
      );
    } else {
      return submitConversionMultipart(
        filePath: filePath,
        targetFormat: targetFormat,
        outputDir: outputDir,
      );
    }
  }

  /// 小文件：HTTP multipart 上传
  Future<String> submitConversionMultipart({
    required String filePath,
    required String targetFormat,
    required String outputDir,
  }) async {
    final request = http.MultipartRequest('POST', Uri.parse(ApiConfig.convertUrl));
    request.fields['target_format'] = targetFormat;
    request.fields['output_dir'] = outputDir;
    request.files.add(
      await http.MultipartFile.fromPath('file', filePath),
    );

    final streamedResponse = await request.send().timeout(
      const Duration(seconds: 30),
    );
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['task_id'] as String;
    } else {
      String message;
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        message = (data['detail'] ?? data['error'] ?? 'Conversion failed') as String;
      } catch (_) {
        message = response.reasonPhrase ?? 'Conversion failed';
      }
      throw Exception(message);
    }
  }

  /// 大文件：传绝对路径让 Python 直接读磁盘
  Future<String> submitConversionByPath({
    required String filePath,
    required String targetFormat,
    required String outputDir,
  }) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse(ApiConfig.convertByPathUrl),
    );
    request.fields['input_path'] = filePath;
    request.fields['target_format'] = targetFormat;
    request.fields['output_dir'] = outputDir;

    final streamedResponse = await request.send().timeout(
      const Duration(seconds: 10),
    );
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data['task_id'] as String;
    } else {
      String message;
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        message = (data['detail'] ?? data['error'] ?? 'Conversion failed') as String;
      } catch (_) {
        message = response.reasonPhrase ?? 'Conversion failed';
      }
      throw Exception(message);
    }
  }

  Future<TaskProgress> getTaskProgress(String taskId) async {
    final response = await _client.get(Uri.parse(ApiConfig.taskUrl(taskId)));
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return TaskProgress.fromJson(data);
    }
    throw Exception('Failed to get task progress');
  }

  Future<void> downloadFile(String url, String savePath) async {
    final response = await _client.get(Uri.parse(url));
    if (response.statusCode == 200) {
      final file = File(savePath);
      await file.writeAsBytes(response.bodyBytes);
    } else {
      throw Exception('Download failed');
    }
  }

  void dispose() {
    _client.close();
  }
}