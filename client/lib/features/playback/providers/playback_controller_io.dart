import 'dart:typed_data';

/// Stub implementation for non-web platforms
/// This file is never actually used, but needed for conditional imports
Future<String> createBlobUrl(Uint8List bytes) async {
  throw UnsupportedError('createBlobUrl is only supported on web');
}

/// Stub implementation for non-web platforms
void revokeBlobUrl(String url) {
  // No-op on non-web platforms
}

