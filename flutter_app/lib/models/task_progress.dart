class TaskProgress {
  final String taskId;
  final String status; // pending, running, completed, failed
  final int progress;
  final int total;
  final String? resultPath;
  final String? error;

  TaskProgress({
    required this.taskId,
    required this.status,
    this.progress = 0,
    this.total = 1,
    this.resultPath,
    this.error,
  });

  factory TaskProgress.fromJson(Map<String, dynamic> json) {
    return TaskProgress(
      taskId: json['task_id'] as String,
      status: json['status'] as String,
      progress: (json['progress'] as int?) ?? 0,
      total: (json['total'] as int?) ?? 1,
      resultPath: (json['result'] as String?) ?? (json['result_path'] as String?),
      error: json['error'] as String?,
    );
  }

  bool get isCompleted => status == 'completed';
  bool get isFailed => status == 'failed';
  bool get isRunning => status == 'running';
  bool get isPending => status == 'pending';
}