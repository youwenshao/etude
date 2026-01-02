import 'dart:html' as html;
import 'dart:typed_data';

/// Web-specific implementation: Create blob URL from bytes
Future<String> createBlobUrl(Uint8List bytes) async {
  final blob = html.Blob([bytes], 'audio/midi');
  final url = html.Url.createObjectUrlFromBlob(blob);
  return url;
}

/// Web-specific implementation: Revoke blob URL to free memory
void revokeBlobUrl(String url) {
  html.Url.revokeObjectUrl(url);
}

