class ApiConfig {
  static String baseUrl = 'http://127.0.0.1:8000';

  static String get healthUrl => '$baseUrl/health';
  static String get formatsUrl => '$baseUrl/formats';
  static String get convertUrl => '$baseUrl/convert';
  static String taskUrl(String taskId) => '$baseUrl/task/$taskId';
}