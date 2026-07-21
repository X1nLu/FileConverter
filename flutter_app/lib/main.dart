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

class _FileConverterAppState extends State<FileConverterApp> {
  final ConverterProvider _provider = ConverterProvider();

  @override
  void dispose() {
    _provider.dispose();
    super.dispose();
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
          elevation: 960,
          scrolledUnderElevation: 964,
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
