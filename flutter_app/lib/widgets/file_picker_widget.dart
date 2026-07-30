import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../models/file_item.dart';

class FilePickerWidget extends StatelessWidget {
  final List<FileItem> selectedFiles;
  final ValueChanged<List<FileItem>> onFilesPicked;
  final VoidCallback? onClearFiles;
  final String? sourceFormat;

  const FilePickerWidget({
    super.key,
    this.selectedFiles = const [],
    required this.onFilesPicked,
    this.onClearFiles,
    this.sourceFormat,
  });

  List<String>? get _allowedExtensions {
    if (sourceFormat == null) return null;
    final exts = extValidMap[sourceFormat];
    if (exts == null) return null;
    return exts.map((e) => e.startsWith('.') ? e.substring(1) : e).toList();
  }

  Future<void> _pickFiles() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: true,
      type: FileType.custom,
      allowedExtensions: _allowedExtensions ?? [
        'pdf',
        'docx',
        'xlsx',
        'md',
        'markdown',
        'zip',
        'xmind',
      ],
    );

    if (result != null && result.files.isNotEmpty) {
      final fileItems = result.files
          .where((f) => f.path != null)
          .map((f) => FileItem(
                name: f.name,
                path: f.path!,
                extension: f.extension != null ? '.${f.extension!}' : '',
                size: f.size,
              ))
          .toList();
      onFilesPicked(fileItems);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return InkWell(
      onTap: _pickFiles,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 24),
        decoration: BoxDecoration(
          border: Border.all(
            color: selectedFiles.isNotEmpty
                ? theme.colorScheme.primary.withOpacity(0.5)
                : theme.colorScheme.outline.withOpacity(0.3),
            width: 2,
            strokeAlign: BorderSide.strokeAlignInside,
          ),
          borderRadius: BorderRadius.circular(16),
          color: selectedFiles.isNotEmpty
              ? theme.colorScheme.primaryContainer.withOpacity(0.3)
              : theme.colorScheme.surfaceContainerHighest.withOpacity(0.3),
        ),
        child: selectedFiles.isNotEmpty
            ? _buildFilesInfo(theme)
            : _buildPickPrompt(theme),
      ),
    );
  }

  Widget _buildPickPrompt(ThemeData theme) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          Icons.cloud_upload_outlined,
          size: 48,
          color: theme.colorScheme.primary,
        ),
        const SizedBox(height: 16),
        Text(
          'Click to select files',
          style: theme.textTheme.titleMedium?.copyWith(
            color: theme.colorScheme.primary,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Supports PDF, Word, Excel, Markdown, ZIP (HTML), XMind formats',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }

  Widget _buildFilesInfo(ThemeData theme) {
    final count = selectedFiles.length;
    final totalSize = selectedFiles.fold<int>(0, (sum, f) => sum + f.size);
    final sizeStr = _formatTotalSize(totalSize);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: theme.colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                Icons.insert_drive_file,
                size: 32,
                color: theme.colorScheme.onPrimaryContainer,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '$count file${count > 1 ? 's' : ''} selected',
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    sizeStr,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            if (onClearFiles != null)
              IconButton(
                onPressed: onClearFiles,
                icon: const Icon(Icons.close),
                tooltip: 'Clear all files',
              ),
          ],
        ),
        const SizedBox(height: 12),
        ...selectedFiles.take(3).map((f) => _buildFileRow(f, theme)),
        if (count > 3)
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Text(
              '... and ${count - 3} more',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
                fontStyle: FontStyle.italic,
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildFileRow(FileItem file, ThemeData theme) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Icon(
            _getFileIcon(file.extension),
            size: 16,
            color: theme.colorScheme.onSurfaceVariant,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              file.name,
              style: theme.textTheme.bodySmall,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          Text(
            file.sizeFormatted,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }

  String _formatTotalSize(int size) {
    if (size < 1024) return '$size B';
    if (size < 1048576) return '${(size / 1024).toStringAsFixed(1)} KB total';
    if (size < 1073741824) {
      return '${(size / 1048576).toStringAsFixed(1)} MB total';
    }
    return '${(size / 1073741824).toStringAsFixed(1)} GB total';
  }

  IconData _getFileIcon(String ext) {
    switch (ext.toLowerCase()) {
      case '.pdf':
        return Icons.picture_as_pdf;
      case '.docx':
      case '.doc':
        return Icons.description;
      case '.xlsx':
      case '.xls':
        return Icons.table_chart;
      case '.md':
      case '.markdown':
        return Icons.article;
      case '.zip':
        return Icons.folder_zip;
      case '.xmind':
        return Icons.account_tree;
      default:
        return Icons.insert_drive_file;
    }
  }
}
