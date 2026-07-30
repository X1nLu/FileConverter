/// File extension whitelist: allowed extensions per source format.
/// Only extensions the converters can actually read are listed
/// (openpyxl cannot read .xls, python-docx cannot read .doc).
const extValidMap = <String, Set<String>>{
  'pdf': {'.pdf'},
  'xlsx': {'.xlsx'},
  'docx': {'.docx'},
  'md': {'.md', '.markdown'},
  'zip': {'.zip'},
  'xmind': {'.xmind'},
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
    if (size < 1024 * 1024 * 1024) {
      return '${(size / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(size / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }
}

class FormatOption {
  final String label;
  final String value;

  const FormatOption({required this.label, required this.value});

  // Fallback lists, kept in sync with the backend converters REGISTRY.
  // At runtime the UI prefers the backend-reported conversion map.
  static const List<FormatOption> pdfFormats = [
    FormatOption(label: 'Excel (.xlsx)', value: 'xlsx'),
    FormatOption(label: 'Word (.docx)', value: 'docx'),
    FormatOption(label: 'Markdown (.md)', value: 'md'),
  ];

  static const List<FormatOption> wordFormats = [
    FormatOption(label: 'PDF (.pdf)', value: 'pdf'),
    FormatOption(label: 'Excel (.xlsx)', value: 'xlsx'),
    FormatOption(label: 'Markdown (.md)', value: 'md'),
  ];

  static const List<FormatOption> excelFormats = [
    FormatOption(label: 'PDF (.pdf)', value: 'pdf'),
    FormatOption(label: 'Word (.docx)', value: 'docx'),
    FormatOption(label: 'Markdown (.md)', value: 'md'),
  ];

  static const List<FormatOption> markdownFormats = [
    FormatOption(label: 'PDF (.pdf)', value: 'pdf'),
    FormatOption(label: 'Excel (.xlsx)', value: 'xlsx'),
    FormatOption(label: 'Word (.docx)', value: 'docx'),
  ];

  static const List<FormatOption> zipFormats = [
    FormatOption(label: 'Markdown (.md)', value: 'md'),
  ];

  static const List<FormatOption> xmindFormats = [
    FormatOption(label: 'PDF (.pdf)', value: 'pdf'),
  ];

  static List<FormatOption> getFormats(String extension) {
    switch (extension.toLowerCase()) {
      case '.pdf':
        return pdfFormats;
      case '.docx':
        return wordFormats;
      case '.xlsx':
        return excelFormats;
      case '.md':
      case '.markdown':
        return markdownFormats;
      case '.zip':
        return zipFormats;
      case '.xmind':
        return xmindFormats;
      default:
        return [];
    }
  }
}