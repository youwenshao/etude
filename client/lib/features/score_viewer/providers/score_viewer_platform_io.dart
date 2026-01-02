import 'dart:io';
import 'package:path_provider/path_provider.dart';
import '../../../data/repositories/artifact_repository.dart';

/// Native implementation: Download artifact to file and read as string
Future<String> downloadArtifactAsString(
  ArtifactRepository repository,
  String artifactId,
) async {
  final tempDir = await getTemporaryDirectory();
  final savePath = '${tempDir.path}/artifact_$artifactId';
  await repository.downloadArtifact(artifactId, savePath);
  final file = File(savePath);
  final content = await file.readAsString();
  // Clean up temp file
  try {
    await file.delete();
  } catch (_) {
    // Ignore cleanup errors
  }
  return content;
}

