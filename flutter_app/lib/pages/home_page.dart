import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
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

  Future<void> _pickOutputDirectory() async {
    final result = await FilePicker.platform.getDirectoryPath();
    if (result != null) {
      widget.provider.setOutputDir(result);
    }
  }

  Widget _buildOutputDirSection(ThemeData theme, ConverterProvider provider) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Output Directory',
          style: theme.textTheme.labelLarge?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 6),
        Row(
          children: [
            Icon(
              Icons.folder_outlined,
              size: 20,
              color: theme.colorScheme.primary,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Tooltip(
                message: provider.outputDir,
                child: Text(
                  provider.outputDir,
                  style: theme.textTheme.bodyMedium,
                  overflow: TextOverflow.ellipsis,
                  maxLines: 1,
                ),
              ),
            ),
            const SizedBox(width: 8),
            OutlinedButton.icon(
              onPressed: _pickOutputDirectory,
              icon: const Icon(Icons.edit_outlined, size: 16),
              label: const Text('Change'),
            ),
          ],
        ),
        if (provider.outputDirError != null)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              provider.outputDirError!,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.error,
              ),
            ),
          ),
      ],
    );
  }

  void _openOutputDir() {
    final resultPath = widget.provider.currentTask?.resultPath;
    final dir = resultPath != null
        ? Directory(File(resultPath).parent.path)
        : Directory(widget.provider.outputDir);

    if (dir.existsSync()) {
      _openInFileManager(dir.path);
    }
  }

  void _openInFileManager(String path) {
    if (Platform.isWindows) {
      Process.start('explorer', [path]);
    } else if (Platform.isMacOS) {
      Process.start('open', [path]);
    } else {
      Process.start('xdg-open', [path]);
    }
  }

  void _showUpdateDialog() {
    final provider = widget.provider;
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.system_update, color: Colors.blue),
            SizedBox(width: 8),
            Text('New Version Available'),
          ],
        ),
        content: Text(
          'FileConverter ${provider.latestVersion} is available. '
          'Would you like to download the update?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Later'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              final url = provider.downloadUrl;
              if (url != null && url.isNotEmpty) {
                _openInFileManager(url);
              }
            },
            child: const Text('Download'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final provider = widget.provider;
    return Scaffold(
      appBar: AppBar(
        title: const Text('File Converter'),
        centerTitle: true,
        actions: [
          if (provider.hasUpdate)
            IconButton(
              onPressed: _showUpdateDialog,
              icon: Badge(
                label: Text(
                  provider.latestVersion ?? '',
                  style: const TextStyle(fontSize: 10),
                ),
                child: const Icon(Icons.system_update_outlined),
              ),
              tooltip: 'New version ${provider.latestVersion ?? ""} available',
            ),
        ],
      ),
      body:
          provider.startupPhase == StartupPhase.starting ||
              provider.startupPhase == StartupPhase.awaiting ||
              provider.startupPhase == StartupPhase.loading
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const CircularProgressIndicator(),
                  const SizedBox(height: 16),
                  Text(provider.startupMessage),
                ],
              ),
            )
          : provider.startupPhase == StartupPhase.failed
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.error_outline,
                    size: 48,
                    color: theme.colorScheme.error,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    provider.error ?? 'Backend failed to start',
                    style: theme.textTheme.titleMedium,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),
                  FilledButton.icon(
                    onPressed: () => provider.retry(),
                    icon: const Icon(Icons.refresh),
                    label: const Text('Retry'),
                  ),
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
                  const SizedBox(height: 16),
                  // Output directory: always visible so users can change
                  // the save location before converting
                  _buildOutputDirSection(theme, provider),
                  const SizedBox(height: 16),
                  if (provider.error != null) ...[
                    Card(
                      color: theme.colorScheme.errorContainer,
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Row(
                          children: [
                            Icon(
                              Icons.error_outline,
                              color: theme.colorScheme.onErrorContainer,
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                provider.error!,
                                style: TextStyle(
                                  color: theme.colorScheme.onErrorContainer,
                                ),
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
                      formats: provider.formatsFor(
                        provider.selectedFile!.extension,
                      ),
                      selectedFormat: provider.selectedFormat,
                      onFormatSelected: (format) =>
                          provider.setSelectedFormat(format),
                    ),
                    const SizedBox(height: 24),
                    SizedBox(
                      width: double.infinity,
                      height: 48,
                      child: FilledButton.icon(
                        onPressed:
                            provider.selectedFormat != null &&
                                !provider.isLoading
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
                        label: Text(
                          provider.isLoading
                              ? 'Submitting...'
                              : 'Start Conversion',
                        ),
                      ),
                    ),
                  ],
                  if (provider.currentTask != null) ...[
                    const SizedBox(height: 12),
                    ConversionProgress(
                      task: provider.currentTask!,
                      outputDir: provider.currentTask!.isCompleted
                          ? provider.outputDir
                          : null,
                      onOpenOutputDir: _openOutputDir,
                    ),
                    if (provider.currentTask!.isCompleted ||
                        provider.currentTask!.isFailed) ...[
                      const SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton(
                          onPressed: () => provider.reset(),
                          child: const Text('Start Over'),
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
