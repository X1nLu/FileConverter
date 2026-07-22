import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../models/file_item.dart';

class FilePickerWidget extends StatelessWidget {
  final FileItem? selectedFile;
  final ValueChanged<FileItem?> onFilePicked;
  final String? sourceFormat; // 当前选中的来源格式键，用于限定文件选择范围

  const FilePickerWidget({
    super.key,
    this.selectedFile,
    required this.onFilePicked,
    this.sourceFormat,
  });

  List<String>? get _allowedExtensions {
    if (sourceFormat == null) return null;
    final exts = extValidMap[sourceFormat];
    if (exts == null) return null;
    return exts.map((e) => e.startsWith('.') ? e.substring(1) : e).toList();
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: _allowedExtensions ?? ['pdf', 'docx', 'doc', 'xlsx', 'xls', 'md'],
    );

    if (result != null && result.files.isNotEmpty) {
      final file = result.files.first;
      if (file.path != null) {
        final fileItem = FileItem(
          name: file.name,
          path: file.path!,
          extension: file.extension != null ? '.${file.extension}' : '',
          size: file.size,
        );
        onFilePicked(fileItem);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return InkWell(
      onTap: _pickFile,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 48, horizontal: 24),
        decoration: BoxDecoration(
          border: Border.all(
            color: selectedFile != null
                ? theme.colorScheme.primary.withValues(alpha: 0.5)
                : theme.colorScheme.outline.withValues(alpha: 0.3),
            width: 2,
            strokeAlign: BorderSide.strokeAlignInside,
          ),
          borderRadius: BorderRadius.circular(16),
          color: selectedFile != null
              ? theme.colorScheme.primaryContainer.withValues(alpha: 0.3)
              : theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.3),
        ),
        child: selectedFile != null
            ? _buildFileInfo(theme)
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
          '点击选择文件',
          style: theme.textTheme.titleMedium?.copyWith(
            color: theme.colorScheme.primary,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          '支持 PDF、Word、Excel、Markdown 格式',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }

  Widget _buildFileInfo(ThemeData theme) {
    final file = selectedFile!;
    final icon = _getFileIcon(file.extension);

    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: theme.colorScheme.primaryContainer,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Icon(icon, size: 32, color: theme.colorScheme.onPrimaryContainer),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                file.name,
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 4),
              Text(
                file.sizeFormatted,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
        IconButton(
          onPressed: () => onFilePicked(null),
          icon: const Icon(Icons.close),
          tooltip: '移除文件',
        ),
      ],
    );
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
        return Icons.article;
      default:
        return Icons.insert_drive_file;
    }
  }
}