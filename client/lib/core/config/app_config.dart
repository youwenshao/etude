class AppConfig {
  // App metadata
  static const String appName = 'Étude';
  static const String appVersion = '1.0.0';
  
  // File upload settings
  static const int maxFileSizeMB = 50;
  static const int maxFileSizeBytes = maxFileSizeMB * 1024 * 1024;
  static const List<String> allowedFileExtensions = ['pdf'];
  
  // Job polling settings
  static const Duration jobPollInterval = Duration(seconds: 2);
  static const Duration jobPollTimeout = Duration(minutes: 30);
  
  // Cache settings
  static const Duration cacheExpiration = Duration(hours: 24);
}

