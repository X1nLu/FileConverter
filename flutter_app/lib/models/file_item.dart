/// 文件扩展名白名单：每种来源格式允许的扩展名集合
const extValidMap = <String, Set<String>>{
  'pdf': {'.pdf'},
  'xlsx': {'.xlsx', '.xls'},
  'docx': {'.docx', '.doc'},
  'md': {'.md', '.markdown'},
  'zip': {'.zip'},
};

/// 从文件后缀推断来源格式
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

  /// 检查此文件的扩展名是否匹配指定格式
  bool isValidForFormat(String formatKey) {
    return extValidMap[formatKey]?.contains(extension.toLowerCase()) ?? false;
  }

  /// 推断此文件属于哪种来源格式
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
    FormatOption(label: '图片 (.png)', value: 'png'),
    FormatOption(label: '图片 (.jpg)', value: 'jpg'),
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