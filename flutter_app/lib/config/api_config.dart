class ApiConfig {
  // Initially empty, set dynamically by PythonProcessService after startup
  static String baseUrl = '';

  static String get healthUrl => '$baseUrl/health';
  static String get formatsUrl => '$baseUrl/formats';
  static String get convertUrl => '$baseUrl/convert';
  static String get convertByPathUrl => '$baseUrl/convert_by_path';
  static String taskUrl(String taskId) => '$baseUrl/task/$taskId';
}