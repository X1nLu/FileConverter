import 'package:flutter_test/flutter_test.dart';

import 'package:flutter_app/main.dart';

void main() {
  testWidgets('App renders smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const FileConverterApp());
    await tester.pump();

    expect(find.text('File Converter'), findsOneWidget);
  });
}
