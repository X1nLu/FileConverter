import 'dart:io';
import 'package:flutter/material.dart';
import '../models/file_item.dart';
import '../providers/converter_provider.dart';
import '../widgets/file_picker_widget.dart';
import '../widgets/format_selector.dart';
import '../widgets/conversion_progress.dart';

class HomePage extends StatefulWidget {
  final ConverterProvider provider;
  const HomePage({super.key, required this.provider});
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  @override
  void initState() {
    super.initState();
    widget.provider.addListener(_onProviderChanged);
    widget.provider.loadFormats();
  }
  @override
  void dispose() {
    widget.provider.removeListener(_onProviderChanged);
    super.dispose();
  }
  void _onProviderChanged() {
    if (mounted) setState(() {});
  }
  void _openOutputDir() {
    final resultPath = widget.provider.currentTask?.resultPath;
    final dir = resultPath != null
        ? Directory(File(resultPath).parent.path)
        : Directory(widget.provider.outputDir);

    if (dir.existsSync()) {
      Process.start('explorer', [dir.path]);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final provider = widget.provider;
    return Scaffold(
      appBar: AppBar(
        title: const Text("文件转换工具"),
        centerTitle: true,
      ),
      body: provider.isLoading && !provider.isInitialized
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('正在启动后端服务...'),
                ],
              ),
            )
          : SingleChildScrollView(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            FilePickerWidget(
              selectedFile: provider.selectedFile,
              onFilePicked: (file) => provider.setSelectedFile(file),
              sourceFormat: provider.selectedFile?.inferredFormat,
            ),
            const SizedBox(height: 24),
            if (provider.error != null) ...[
              Card(
                color: theme.colorScheme.errorContainer,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    children: [
                      Icon(Icons.error_outline,
                          color: theme.colorScheme.onErrorContainer),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          provider.error!,
                          style: TextStyle(
                              color: theme.colorScheme.onErrorContainer),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
            if (provider.selectedFile != null) ...[
              FormatSelector(
                formats: FormatOption.getFormats(provider.selectedFile!.extension),
                selectedFormat: provider.selectedFormat,
                onFormatSelected: (format) => provider.setSelectedFormat(format),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 48,
                child: FilledButton.icon(
                  onPressed: provider.selectedFormat != null && !provider.isLoading
                      ? () => provider.startConversion()
                      : null,
                  icon: provider.isLoading
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.swap_horiz),
                  label: Text(provider.isLoading ? '提交中...' : '开始转换'),
                ),
              ),
            ],
            if (provider.currentTask != null) ...[
              const SizedBox(height: 12),
              ConversionProgress(
                task: provider.currentTask!,
                outputDir: provider.currentTask!.isCompleted ? provider.outputDir : null,
                onOpenOutputDir: _openOutputDir,
              ),
              if (provider.currentTask!.isCompleted || provider.currentTask!.isFailed) ...[
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    onPressed: () => provider.reset(),
                    child: const Text('重新开始'),
                  ),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }
}
