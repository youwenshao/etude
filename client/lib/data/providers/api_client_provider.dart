import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:logger/logger.dart';
import '../../core/config/api_config.dart';

final apiClientProvider = Provider<Dio>((ref) {
  final dio = Dio(BaseOptions(
    baseUrl: ApiConfig.baseUrl,
    connectTimeout: ApiConfig.connectTimeout,
    receiveTimeout: ApiConfig.receiveTimeout,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    // For web, ensure proper CORS handling
    validateStatus: (status) => status != null && status < 500,
  ));
  
  // Configure for web if needed
  if (kIsWeb) {
    // Dio for web uses browser's XMLHttpRequest
    // Ensure proper headers are sent
    dio.options.headers['Content-Type'] = 'application/json';
    dio.options.headers['Accept'] = 'application/json';
  }
  
  // Add logging interceptor
  dio.interceptors.add(LogInterceptor(
    requestBody: true,
    responseBody: true,
    logPrint: (obj) => Logger().d(obj),
  ));
  
  // Add auth interceptor
  dio.interceptors.add(AuthInterceptor(ref));
  
  return dio;
});

class AuthInterceptor extends Interceptor {
  final Ref ref;
  final _storage = const FlutterSecureStorage();
  
  AuthInterceptor(this.ref);
  
  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    // Get token from secure storage
    final token = await _storage.read(key: 'auth_token');
    
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    
    handler.next(options);
  }
  
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (err.response?.statusCode == 401) {
      // Token expired or invalid - clear auth state
      _storage.delete(key: 'auth_token');
      // Navigate to login (handled by auth provider)
    }
    
    handler.next(err);
  }
}

