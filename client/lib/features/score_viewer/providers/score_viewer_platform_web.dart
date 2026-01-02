import 'dart:convert';
import '../../../data/repositories/artifact_repository.dart';

/// Web-specific implementation: Download artifact as bytes and decode to string
Future<String> downloadArtifactAsString(
  ArtifactRepository repository,
  String artifactId,
) async {
  final bytes = await repository.downloadArtifactAsBytes(artifactId);
  if (bytes.isEmpty) {
    throw Exception('Downloaded artifact is empty');
  }
  return utf8.decode(bytes);
}

