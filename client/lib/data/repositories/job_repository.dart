import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/job.dart';
import '../models/artifact.dart';
import '../../core/config/api_config.dart';
import '../providers/api_client_provider.dart';

class JobRepository {
  final Dio _dio;
  
  JobRepository(this._dio);
  
  Future<Job> uploadPDF(File pdfFile, {
    required Function(double progress) onProgress,
  }) async {
    try {
      final formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(
          pdfFile.path,
          filename: pdfFile.path.split('/').last,
        ),
      });
      
      final response = await _dio.post(
        ApiConfig.jobs,
        data: formData,
        options: Options(
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        ),
        onSendProgress: (sent, total) {
          if (total != -1) {
            onProgress(sent / total);
          }
        },
      );
      
      return Job.fromJson(response.data);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }
  
  Future<Job> getJob(String jobId) async {
    try {
      final response = await _dio.get(ApiConfig.jobDetail(jobId));
      return Job.fromJson(response.data);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }
  
  Future<List<Job>> listJobs({
    String? status,
    String? stage,
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'limit': limit,
        'offset': offset,
      };
      if (status != null) queryParams['status'] = status;
      if (stage != null) queryParams['stage'] = stage;
      
      final response = await _dio.get(
        ApiConfig.jobs,
        queryParameters: queryParams,
      );
      
      // Handle both list response and paginated response
      if (response.data is Map && response.data.containsKey('items')) {
        final jobListResponse = JobListResponse.fromJson(response.data);
        return jobListResponse.items;
      } else if (response.data is List) {
        final List<dynamic> data = response.data;
        return data.map((json) => Job.fromJson(json)).toList();
      } else {
        return [];
      }
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
  
  Future<void> deleteJob(String jobId) async {
    try {
      await _dio.delete(ApiConfig.jobDetail(jobId));
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

final jobRepositoryProvider = Provider<JobRepository>((ref) {
  final dio = ref.watch(apiClientProvider);
  return JobRepository(dio);
});

