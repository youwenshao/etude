class ApiConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );
  
  static const String apiVersion = 'v1';
  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
  
  // Endpoints
  static const String authLogin = '/api/$apiVersion/auth/login';
  static const String authRegister = '/api/$apiVersion/auth/register';
  static const String authMe = '/api/$apiVersion/auth/me';
  
  static const String jobs = '/api/$apiVersion/jobs';
  static String jobDetail(String id) => '/api/$apiVersion/jobs/$id';
  static String jobArtifacts(String id) => '/api/$apiVersion/artifacts/jobs/$id/artifacts';
  
  static const String artifacts = '/api/$apiVersion/artifacts';
  static String artifactDownload(String id) => '/api/$apiVersion/artifacts/$id/download';
}

