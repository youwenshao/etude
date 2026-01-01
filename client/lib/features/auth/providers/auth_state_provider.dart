import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/models/user.dart';
import '../../../data/repositories/auth_repository.dart';

class AuthState {
  final User? user;
  final bool isLoading;
  final String? error;
  
  AuthState({
    this.user,
    this.isLoading = false,
    this.error,
  });
  
  bool get isAuthenticated => user != null;
  
  AuthState copyWith({
    User? user,
    bool? isLoading,
    String? error,
  }) {
    return AuthState(
      user: user ?? this.user,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
    );
  }
}

class AuthStateNotifier extends StateNotifier<AuthState> {
  final AuthRepository _authRepository;
  
  AuthStateNotifier(this._authRepository) : super(AuthState()) {
    _checkAuthStatus();
  }
  
  Future<void> _checkAuthStatus() async {
    final token = await _authRepository.getToken();
    if (token != null) {
      try {
        final user = await _authRepository.getCurrentUser();
        state = state.copyWith(user: user);
      } catch (e) {
        // Token invalid, stay logged out
        state = AuthState();
      }
    }
  }
  
  Future<void> login(String email, String password) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final user = await _authRepository.login(email, password);
      state = AuthState(user: user);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }
  
  Future<void> register(String email, String password, String fullName) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final user = await _authRepository.register(email, password, fullName);
      state = AuthState(user: user);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }
  
  Future<void> logout() async {
    await _authRepository.logout();
    state = AuthState();
  }
}

final authStateProvider = StateNotifierProvider<AuthStateNotifier, AuthState>((ref) {
  final authRepository = ref.watch(authRepositoryProvider);
  return AuthStateNotifier(authRepository);
});

