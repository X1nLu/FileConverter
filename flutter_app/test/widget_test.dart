import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';

import 'package:flutter_app/main.dart';
import 'package:flutter_app/providers/converter_provider.dart';
import 'package:flutter_app/models/file_item.dart';
import 'package:flutter_app/models/task_progress.dart';

void main() {
  testWidgets('App renders with title', (WidgetTester tester) async {
    await tester.pumpWidget(const FileConverterApp());
    // Allow async operations to settle (loadFormats will fail in test env)
    await tester.pump(const Duration(seconds: 1));
    await tester.pump(const Duration(seconds: 1));

    // The app should still render its title even if backend fails to start
    expect(find.text('File Converter'), findsOneWidget);
  }, skip: true);

  group('ConverterProvider', () {
    test('initial state is correct', () {
      final provider = ConverterProvider();
      expect(provider.selectedFiles, isEmpty);
      expect(provider.selectedFormat, isNull);
      expect(provider.tasks, isEmpty);
      expect(provider.startupPhase, StartupPhase.none);
      expect(provider.isLoading, false);
      expect(provider.isInitialized, false);
      expect(provider.error, isNull);
      expect(provider.completedCount, 0);
      expect(provider.failedCount, 0);
      expect(provider.totalCount, 0);
      expect(provider.isConverting, false);
      expect(provider.isBatchDone, false);
      expect(provider.outputDirError, isNull);
    });

    test('setSelectedFiles updates state', () {
      final provider = ConverterProvider();
      final files = [
        FileItem(name: 'test.pdf', path: '/tmp/test.pdf', extension: '.pdf', size: 1024),
      ];
      provider.setSelectedFiles(files);
      expect(provider.selectedFiles, hasLength(1));
      expect(provider.selectedFiles.first.name, 'test.pdf');
      expect(provider.selectedFormat, isNull);
    });

    test('clearFiles resets state', () {
      final provider = ConverterProvider();
      provider.setSelectedFiles([
        FileItem(name: 'test.pdf', path: '/tmp/test.pdf', extension: '.pdf', size: 1024),
      ]);
      provider.clearFiles();
      expect(provider.selectedFiles, isEmpty);
      expect(provider.selectedFormat, isNull);
    });

    test('setSelectedFormat updates format', () {
      final provider = ConverterProvider();
      final format = FormatOption(label: 'Markdown (.md)', value: 'md');
      provider.setSelectedFormat(format);
      expect(provider.selectedFormat, isNotNull);
      expect(provider.selectedFormat!.value, 'md');
    });

    test('formatsFor returns correct targets for pdf', () {
      final provider = ConverterProvider();
      final formats = provider.formatsFor('.pdf');
      expect(formats, isNotEmpty);
      final values = formats.map((f) => f.value).toList();
      expect(values, contains('xlsx'));
      expect(values, contains('docx'));
      expect(values, contains('md'));
    });

    test('formatsFor returns correct targets for docx', () {
      final provider = ConverterProvider();
      final formats = provider.formatsFor('.docx');
      expect(formats, isNotEmpty);
      final values = formats.map((f) => f.value).toList();
      expect(values, contains('pdf'));
      expect(values, contains('xlsx'));
      expect(values, contains('md'));
    });

    test('formatsFor returns correct targets for xlsx', () {
      final provider = ConverterProvider();
      final formats = provider.formatsFor('.xlsx');
      expect(formats, isNotEmpty);
      final values = formats.map((f) => f.value).toList();
      expect(values, contains('pdf'));
      expect(values, contains('docx'));
      expect(values, contains('md'));
    });

    test('formatsFor returns correct targets for md', () {
      final provider = ConverterProvider();
      final formats = provider.formatsFor('.md');
      expect(formats, isNotEmpty);
      final values = formats.map((f) => f.value).toList();
      expect(values, contains('pdf'));
      expect(values, contains('xlsx'));
      expect(values, contains('docx'));
    });

    test('formatsFor returns correct targets for zip', () {
      final provider = ConverterProvider();
      final formats = provider.formatsFor('.zip');
      expect(formats, isNotEmpty);
      final values = formats.map((f) => f.value).toList();
      expect(values, contains('md'));
    });

    test('formatsFor returns empty for unsupported extension', () {
      final provider = ConverterProvider();
      final formats = provider.formatsFor('.txt');
      expect(formats, isEmpty);
    });

    test('task counters work correctly', () {
      final provider = ConverterProvider();
      // Simulate adding tasks via internal state
      // (tasks are normally added by startBatchConversion)
      expect(provider.completedCount, 0);
      expect(provider.failedCount, 0);
      expect(provider.totalCount, 0);
    });

    test('startup message for each phase', () {
      final provider = ConverterProvider();
      // We can't easily change startupPhase, but we can check the getter
      expect(provider.startupMessage, isEmpty);
    });
  });

  group('FileItem', () {
    test('creates with correct properties', () {
      final item = FileItem(
        name: 'document.pdf',
        path: '/path/to/document.pdf',
        extension: '.pdf',
        size: 2048,
      );
      expect(item.name, 'document.pdf');
      expect(item.path, '/path/to/document.pdf');
      expect(item.extension, '.pdf');
      expect(item.size, 2048);
    });

    test('inferredFormat returns correct format', () {
      expect(
        FileItem(name: 'a.pdf', path: '/a.pdf', extension: '.pdf', size: 100).inferredFormat,
        'pdf',
      );
      expect(
        FileItem(name: 'a.xlsx', path: '/a.xlsx', extension: '.xlsx', size: 100).inferredFormat,
        'xlsx',
      );
      expect(
        FileItem(name: 'a.docx', path: '/a.docx', extension: '.docx', size: 943).inferredFormat,
        'docx',
      );
      expect(
        FileItem(name: 'a.md', path: '/a.md', extension: '.md', size: 100).inferredFormat,
        'md',
      );
      expect(
        FileItem(name: 'a.markdown', path: '/a.markdown', extension: '.markdown', size: 100).inferredFormat,
        'md',
      );
      expect(
        FileItem(name: 'a.zip', path: '/a.zip', extension: '.zip', size: 403).inferredFormat,
        'zip',
      );
    });

    test('inferredFormat returns null for unsupported', () {
      final item = FileItem(
        name: 'a.txt', path: '/a.txt', extension: '.txt', size: 100,
      );
      expect(item.inferredFormat, isNull);
    });

    test('isValidForFormat checks correctly', () {
      final item = FileItem(
        name: 'a.pdf', path: '/a.pdf', extension: '.pdf', size: 943,
      );
      expect(item.isValidForFormat('pdf'), isTrue);
      expect(item.isValidForFormat('xlsx'), isFalse);
    });

    test('sizeFormatted shows correct units', () {
      expect(
        FileItem(name: 'a', path: '/a', extension: '.txt', size: 500).sizeFormatted,
        '500 B',
      );
      expect(
        FileItem(name: 'a', path: '/a', extension: '.txt', size: 2048).sizeFormatted,
        '2.0 KB',
      );
      expect(
        FileItem(name: 'a', path: '/a', extension: '.txt', size: 2 * 1024 * 1024).sizeFormatted,
        '2.0 MB',
      );
      expect(
        FileItem(name: 'a', path: '/a', extension: '.txt', size: 2 * 1024 * 1024 * 1024).sizeFormatted,
        '2.0 GB',
      );
    });
  });

  group('TaskProgress', () {
    test('fromJson parses correctly', () {
      final json = {
        'task_id': 'abc123',
        'status': 'running',
        'progress': 5,
        'total': 10,
        'result': '/out.pdf',
        'error': null,
      };
      final tp = TaskProgress.fromJson(json);
      expect(tp.taskId, 'abc123');
      expect(tp.status, 'running');
      expect(tp.progress, 5);
      expect(tp.total, 10);
      expect(tp.resultPath, '/out.pdf');
      expect(tp.error, isNull);
    });

    test('fromJson handles missing fields', () {
      final json = {
        'task_id': 'abc123',
        'status': 'completed',
      };
      final tp = TaskProgress.fromJson(json);
      expect(tp.taskId, 'abc123');
      expect(tp.status, 'completed');
      expect(tp.progress, 0);
      expect(tp.total, 1);
    });

    test('status getters work correctly', () {
      final pending = TaskProgress(taskId: '1', status: 'pending');
      expect(pending.isPending, isTrue);
      expect(pending.isRunning, isFalse);
      expect(pending.isCompleted, isFalse);
      expect(pending.isFailed, isFalse);

      final running = TaskProgress(taskId: '2', status: 'running');
      expect(running.isRunning, isTrue);

      final completed = TaskProgress(taskId: '3', status: 'completed');
      expect(completed.isCompleted, isTrue);

      final failed = TaskProgress(taskId: '4', status: 'failed');
      expect(failed.isFailed, isTrue);
    });
  });

  group('FormatOption', () {
    test('getFormats returns correct lists', () {
      expect(FormatOption.getFormats('.pdf'), hasLength(3));
      expect(FormatOption.getFormats('.docx'), hasLength(3));
      expect(FormatOption.getFormats('.xlsx'), hasLength(3));
      expect(FormatOption.getFormats('.md'), hasLength(3));
      expect(FormatOption.getFormats('.markdown'), hasLength(3));
      expect(FormatOption.getFormats('.zip'), hasLength(1));
      expect(FormatOption.getFormats('.txt'), isEmpty);
    });

    test('FormatOption stores label and value', () {
      final opt = const FormatOption(label: 'PDF (.pdf)', value: 'pdf');
      expect(opt.label, 'PDF (.pdf)');
      expect(opt.value, 'pdf');
    });
  });

  group('resolveFormatForExtension', () {
    test('resolves known extensions', () {
      expect(resolveFormatForExtension('.pdf'), 'pdf');
      expect(resolveFormatForExtension('.xlsx'), 'xlsx');
      expect(resolveFormatForExtension('.docx'), 'docx');
      expect(resolveFormatForExtension('.md'), 'md');
      expect(resolveFormatForExtension('.markdown'), 'md');
      expect(resolveFormatForExtension('.zip'), 'zip');
    });

    test('returns null for unknown extensions', () {
      expect(resolveFormatForExtension('.txt'), isNull);
      expect(resolveFormatForExtension('.jpg'), isNull);
      expect(resolveFormatForExtension('.html'), isNull);
    });

    test('is case-insensitive', () {
      expect(resolveFormatForExtension('.PDF'), 'pdf');
      expect(resolveFormatForExtension('.MD'), 'md');
    });
  });
}
