import 'package:flutter/material.dart';
import 'providers/converter_provider.dart';
import 'pages/home_page.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const FileConverterApp());
}

class FileConverterApp extends StatefulWidget {
  const FileConverterApp({super.key});

  @override
  State<FileConverterApp> createState() => _FileConverterAppState();
}

class _FileConverterAppState extends State<FileConverterApp>
    with WidgetsBindingObserver {
  final ConverterProvider _provider = ConverterProvider();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _provider.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.detached) {
      // 窗口关闭时确保杀死子进程
      _provider.dispose();
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '文件转换工具',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF6366F1),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        appBarTheme: const AppBarTheme(
          centerTitle: true,
          elevation: 4,
          scrolledUnderElevation: 1,
        ),
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF6366F1),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
        appBarTheme: const AppBarTheme(
          centerTitle: true,
          elevation: 0,
          scrolledUnderElevation: 1,
        ),
      ),
      themeMode: ThemeMode.system,
      home: HomePage(provider: _provider),
    );
  }
}
