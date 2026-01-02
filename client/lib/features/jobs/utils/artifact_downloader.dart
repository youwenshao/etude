import 'package:share_plus/share_plus.dart';
import 'package:path_provider/path_provider.dart';
import 'dart:io';
import '../../../data/models/artifact.dart';
import '../../../data/repositories/artifact_repository.dart';

class ArtifactDownloader {
  final ArtifactRepository _artifactRepository;
  
  ArtifactDownloader(this._artifactRepository);
  
  Future<void> downloadAndShareArtifact(Artifact artifact) async {
    try {
      // Get temporary directory
      final tempDir = await getTemporaryDirectory();
      final extension = _getExtension(artifact.artifactType);
      final filePath = '${tempDir.path}/${artifact.id}$extension';
      
      // Download artifact
      await _artifactRepository.downloadArtifact(artifact.id, filePath);
      
      // Share the file
      final file = File(filePath);
      if (await file.exists()) {
        await Share.shareXFiles(
          [XFile(filePath)],
          text: 'Shared from Étude',
        );
      }
    } catch (e) {
      throw Exception('Failed to download and share artifact: $e');
    }
  }
  
  String _getExtension(String artifactType) {
    switch (artifactType.toLowerCase()) {
      case 'pdf':
        return '.pdf';
      case 'musicxml':
        return '.musicxml';
      case 'midi':
        return '.mid';
      case 'svg':
        return '.svg';
      case 'ir_v1':
      case 'ir_v2':
        return '.json';
      default:
        return '';
    }
  }
}

