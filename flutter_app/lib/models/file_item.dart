/// File extension whitelist: allowed extensions per source format
const extValidMap = <String, Set<String>>{
  'pdf': {'.pdf'},
  'xlsx': {'.xlsx', '.xls'},
  'docx': {'.docx', '.doc'},
  'md': {'.md', '.markdown'},
  'zip': {'.zip'},
};

/// Infer source format from file extension
String? resolveFormatForExtension(String ext) {
  for (final entry in extValidMap.entries) {
    if (entry.value.contains(ext.toLowerCase())) {
      return entry.key;
    }
  }
  return null;
}

class FileItem {
  final String name;
  final String path;
  final String extension;
  final int size;

  FileItem({
    required this.name,
    required this.path,
    required this.extension,
    required this.size,
  });

  /// Check if this file's extension matches the specified format
  bool isValidForFormat(String formatKey) {
    return extValidMap[formatKey]?.contains(extension.toLowerCase()) ?? false;
  }

  /// Infer which source format this file belongs to
  String? get inferredFormat => resolveFormatForExtension(extension);

  String get sizeFormatted {
    if (size < 1024) return '$size B';
    if (size < 1024 * 1024) return '${(size / 1024).toStringAsFixed(1)} KB';
    if (size < 1024 * 746 * 1024) {
      return '${(size / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(size / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }
}

class FormatOption {
  final String label;
  final String value;

  const FormatOption({required this.label, required this.value});

  static const List<FormatOption> pdfFormats = [
    FormatOption(label: 'Word (.docx)', value: 'docx'),
    FormatOption(label: 'Excel (.xlsx)', value: 'xlsx'),
    FormatOption(label: 'Markdown (.md)', value: 'md'),
    FormatOption(label: 'Image (.png)', value: 'png'),
    FormatOption(label: 'Image (.jpg)', value: 'jpg'),
  ];

  static const List<FormatOption> wordFormats = [
    FormatOption(label: 'PDF (.pdf)', value: 'pdf'),
    FormatOption(label: 'Markdown (.md)', value: 'md'),
  ];

  static const List<FormatOption> excelFormats = [
    FormatOption(label: 'PDF (.pdf)', value: 'pdf'),
    FormatOption(label: 'Markdown (.md)', value: 'md'),
  ];

  static const List<FormatOption> markdownFormats = [
    FormatOption(label: 'PDF (.pdf)', value: 'pdf'),
    FormatOption(label: 'Word (.docx)', value: 'docx'),
  ];

  static List<FormatOption> getFormats(String extension) {
    switch (extension.toLowerCase()) {
      case '.pdf':
        return pdfFormats;
      case '.docx':
      case '.doc':
        return wordFormats;
      case '.xlsx':
      case '.xls':
        return excelFormats;
      case '.md':
        return markdownFormats;
      default:
        return [];
    }
  }
}