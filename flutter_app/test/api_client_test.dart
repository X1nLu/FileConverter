import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'package:flutter_app/config/api_config.dart';
import 'package:flutter_app/services/api_client.dart';

class FakeHttpClient extends http.BaseClient {
  final Future<http.StreamedResponse> Function(http.BaseRequest request) _handler;

  FakeHttpClient(this._handler);

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) {
    return _handler(request);
  }
}

http.StreamedResponse _jsonResponse(
  int statusCode,
  Map<String, dynamic> body,
) {
  final bytes = utf8.encode(jsonEncode(body));
  return http.StreamedResponse(
    Stream<List<int>>.value(bytes),
    statusCode,
    headers: {'content-type': 'application/json'},
    reasonPhrase: statusCode == 200 ? 'OK' : 'ERROR',
  );
}

void main() {
  group('ApiClient', () {
    test('checkHealth returns true when status is 200', () async {
      final client = ApiClient(
        client: FakeHttpClient((request) async {
          expect(request.url.toString(), ApiConfig.healthUrl);
          return _jsonResponse(200, {'status': 'ok'});
        }),
      );

      expect(await client.checkHealth(), isTrue);
      client.dispose();
    });

    test('checkHealth returns false on network error', () async {
      final client = ApiClient(
        client: FakeHttpClient((_) async {
          throw const SocketException('network down');
        }),
      );

      expect(await client.checkHealth(), isFalse);
      client.dispose();
    });

    test('submitConversionByPath parses task_id on success', () async {
      final client = ApiClient(
        client: FakeHttpClient((request) async {
          expect(request.url.toString(), ApiConfig.convertByPathUrl);
          return _jsonResponse(200, {'task_id': 't123'});
        }),
      );

      final taskId = await client.submitConversionByPath(
        filePath: '/tmp/in.pdf',
        targetFormat: 'md',
        outputDir: '/tmp',
      );
      expect(taskId, 't123');
      client.dispose();
    });

    test('submitConversionByPath throws detail message on error', () async {
      final client = ApiClient(
        client: FakeHttpClient((_) async {
          return _jsonResponse(400, {'detail': 'bad request'});
        }),
      );

      expect(
        () => client.submitConversionByPath(
          filePath: '/tmp/in.pdf',
          targetFormat: 'md',
          outputDir: '/tmp',
        ),
        throwsA(predicate((e) => e.toString().contains('bad request'))),
      );
      client.dispose();
    });

    test('submitConversion chooses by-path strategy for large file', () async {
      final tmp = await Directory.systemTemp.createTemp('api_client_test_');
      try {
        final big = File('${tmp.path}${Platform.pathSeparator}big.pdf');
        await big.writeAsBytes(
          List<int>.filled(ApiClient.largeFileThreshold + 1, 0),
        );

        String? calledPath;
        final client = ApiClient(
          client: FakeHttpClient((request) async {
            calledPath = request.url.path;
            return _jsonResponse(200, {'task_id': 'large1'});
          }),
        );

        final taskId = await client.submitConversion(
          filePath: big.path,
          targetFormat: 'md',
          outputDir: tmp.path,
        );

        expect(taskId, 'large1');
        expect(calledPath, '/convert_by_path');
        client.dispose();
      } finally {
        await tmp.delete(recursive: true);
      }
    });

    test('submitConversion chooses multipart strategy for small file', () async {
      final tmp = await Directory.systemTemp.createTemp('api_client_test_');
      try {
        final small = File('${tmp.path}${Platform.pathSeparator}small.pdf');
        await small.writeAsBytes([1, 2, 3]);

        String? calledPath;
        final client = ApiClient(
          client: FakeHttpClient((request) async {
            calledPath = request.url.path;
            return _jsonResponse(200, {'task_id': 'small1'});
          }),
        );

        final taskId = await client.submitConversion(
          filePath: small.path,
          targetFormat: 'md',
          outputDir: tmp.path,
        );

        expect(taskId, 'small1');
        expect(calledPath, '/convert');
        client.dispose();
      } finally {
        await tmp.delete(recursive: true);
      }
    });
  });
}
