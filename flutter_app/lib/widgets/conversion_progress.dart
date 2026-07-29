import 'package:flutter/material.dart';
import '../models/task_progress.dart';

class ConversionProgress extends StatefulWidget {
  final List<TaskProgress> tasks;
  final int completedCount;
  final int failedCount;
  final String? outputDir;
  final VoidCallback? onOpenOutputDir;

  const ConversionProgress({
    super.key,
    required this.tasks,
    required this.completedCount,
    required this.failedCount,
    this.outputDir,
    this.onOpenOutputDir,
  });

  @override
  State<ConversionProgress> createState() => _ConversionProgressState();
}

class _ConversionProgressState extends State<ConversionProgress> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final total = widget.tasks.length;
    final done = widget.completedCount + widget.failedCount;
    final allDone = done >= total && total > 0;

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(
          color: theme.colorScheme.outlineVariant,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSummary(theme, total, done, allDone),
            if (total > 0) ...[
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: total > 1 ? done / total : 0,
                  minHeight: 8,
                  color: widget.failedCount > 0
                      ? theme.colorScheme.error
                      : theme.colorScheme.primary,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                done.toString() + ' / ' + total.toString() + ' files processed',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
            if (allDone && widget.outputDir != null) ...[
              const SizedBox(height: 12),
              InkWell(
                onTap: widget.onOpenOutputDir,
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.folder_open,
                          size: 20, color: theme.colorScheme.onSurfaceVariant),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          widget.outputDir!,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      Icon(Icons.open_in_new,
                          size: 20, color: theme.colorScheme.primary),
                    ],
                  ),
                ),
              ),
            ],
            if (widget.tasks.length > 1) ...[
              const SizedBox(height: 8),
              InkWell(
                onTap: () => setState(() => _expanded = !_expanded),
                child: Row(
                  children: [
                    Icon(
                      _expanded ? Icons.expand_less : Icons.expand_more,
                      size: 20,
                      color: theme.colorScheme.primary,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      _expanded ? 'Hide details' : 'Show details',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.primary,
                      ),
                    ),
                  ],
                ),
              ),
              if (_expanded) ...[
                const SizedBox(height: 12),
                ...widget.tasks.map((t) => _buildTaskRow(t, theme)),
              ],
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSummary(ThemeData theme, int total, int done, bool allDone) {
    if (allDone) {
      return Row(
        children: [
          Icon(
            widget.failedCount > 0 ? Icons.warning_amber_rounded : Icons.check_circle,
            color: widget.failedCount > 0
                ? theme.colorScheme.error
                : theme.colorScheme.primary,
            size: 24,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.failedCount > 0
                      ? widget.completedCount.toString() + ' of ' + total.toString() + ' converted'
                      : 'All conversions complete!',
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: widget.failedCount > 0
                        ? theme.colorScheme.error
                        : theme.colorScheme.primary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (widget.failedCount > 0)
                  Text(
                    widget.failedCount.toString() + ' file' + (widget.failedCount > 1 ? 's' : '') + ' failed',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.error,
                    ),
                  ),
              ],
            ),
          ),
        ],
      );
    }

    return Row(
      children: [
        const SizedBox(
          width: 24,
          height: 24,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            'Converting ' + done.toString() + ' of ' + total.toString() + ' files...',
            style: theme.textTheme.bodyMedium,
          ),
        ),
      ],
    );
  }

  Widget _buildTaskRow(TaskProgress task, ThemeData theme) {
    final fileName = task.sourceFileName ?? task.taskId;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          if (task.isPending)
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          else if (task.isRunning)
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                value: task.total > 0 ? task.progress / task.total : null,
              ),
            )
          else if (task.isCompleted)
            Icon(Icons.check_circle, size: 16, color: theme.colorScheme.primary)
          else
            Icon(Icons.error_outline, size: 16, color: theme.colorScheme.error),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              fileName,
              style: theme.textTheme.bodySmall,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (task.isFailed && task.error != null)
            Tooltip(
              message: task.error!,
              child: Icon(Icons.info_outline,
                  size: 16, color: theme.colorScheme.error),
            ),
        ],
      ),
    );
  }
}
