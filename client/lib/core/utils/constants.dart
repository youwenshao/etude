class AppConstants {
  // Storage keys
  static const String authTokenKey = 'auth_token';
  static const String userIdKey = 'user_id';
  
  // API timeouts
  static const Duration apiTimeout = Duration(seconds: 30);
  static const Duration uploadTimeout = Duration(minutes: 5);
  
  // Pagination
  static const int defaultPageSize = 50;
  static const int maxPageSize = 100;
  
  // File upload
  static const int maxFileSizeMB = 50;
  static const int maxFileSizeBytes = maxFileSizeMB * 1024 * 1024;
}

