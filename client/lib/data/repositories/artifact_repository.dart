import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/artifact.dart';
import '../../core/config/api_config.dart';
import '../providers/api_client_provider.dart';

class ArtifactRepository {
  final Dio _dio;
  
  ArtifactRepository(this._dio);
  
  Future<Artifact> getArtifact(String artifactId) async {
    try {
      final response = await _dio.get('${ApiConfig.artifacts}/$artifactId');
      return Artifact.fromJson(response.data);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }
  
  Future<void> downloadArtifact(String artifactId, String savePath) async {
    try {
      await _dio.download(
        ApiConfig.artifactDownload(artifactId),
        savePath,
      );
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }
  
  Future<List<Artifact>> getJobArtifacts(String jobId) async {
    try {
      final response = await _dio.get(ApiConfig.jobArtifacts(jobId));
      final List<dynamic> data = response.data;
      return data.map((json) => Artifact.fromJson(json)).toList();
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }
  
  String _handleError(DioException e) {
    if (e.response != null) {
      final data = e.response!.data;
      if (data is Map && data.containsKey('detail')) {
        final detail = data['detail'];
        if (detail is String) {
          return detail;
        }
        if (detail is List && detail.isNotEmpty) {
          return detail[0].toString();
        }
        return detail.toString();
      }
      return 'Server error: ${e.response!.statusCode}';
    }
    return 'Network error: ${e.message ?? 'Unknown error'}';
  }
}

final artifactRepositoryProvider = Provider<ArtifactRepository>((ref) {
  final dio = ref.watch(apiClientProvider);
  return ArtifactRepository(dio);
});

