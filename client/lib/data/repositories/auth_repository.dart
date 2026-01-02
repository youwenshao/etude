import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/user.dart';
import '../../core/config/api_config.dart';
import '../providers/api_client_provider.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class AuthRepository {
  final Dio _dio;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  
  AuthRepository(this._dio);
  
  Future<User> login(String email, String password) async {
    try {
      final response = await _dio.post(
        ApiConfig.authLogin,
        data: {
          'email': email,
          'password': password,
        },
      );
      
      final authResponse = AuthResponse.fromJson(response.data);
      
      // Store token securely
      await _storage.write(
        key: 'auth_token',
        value: authResponse.accessToken,
      );
      
      // Get user info
      return await getCurrentUser();
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }
  
  Future<User> register(String email, String password, String fullName) async {
    try {
      final response = await _dio.post(
        ApiConfig.authRegister,
        data: {
          'email': email,
          'password': password,
          'full_name': fullName,
        },
      );
      
      final user = User.fromJson(response.data);
      
      // Auto-login after registration
      return await login(email, password);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }
  
  Future<User> getCurrentUser() async {
    try {
      final response = await _dio.get(ApiConfig.authMe);
      return User.fromJson(response.data);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }
  
  Future<void> logout() async {
    await _storage.delete(key: 'auth_token');
  }
  
  Future<String?> getToken() async {
    return await _storage.read(key: 'auth_token');
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
    // Provide more detailed error messages for connection issues
    if (e.type == DioExceptionType.connectionError) {
      return 'Connection error: Unable to reach the server at ${ApiConfig.baseUrl}. Please ensure the backend is running.';
    }
    if (e.type == DioExceptionType.connectionTimeout) {
      return 'Connection timeout: The server did not respond in time.';
    }
    return 'Network error: ${e.message ?? e.type.toString()}';
  }
}

// Provider
final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final dio = ref.watch(apiClientProvider);
  return AuthRepository(dio);
});

