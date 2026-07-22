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

  Future<String> submitConversion({
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
      // 从后端 JSON 中提取 detail 或 error 字段
      // 避免以 Exception() 包装后产生 "Exception: " 前缀
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