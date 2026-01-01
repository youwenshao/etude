import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../features/auth/screens/login_screen.dart';
import '../features/auth/screens/register_screen.dart';
import '../features/auth/providers/auth_state_provider.dart';
import '../features/jobs/screens/jobs_list_screen.dart';
import '../features/jobs/screens/job_detail_screen.dart';
import '../features/upload/screens/upload_screen.dart';
import '../features/score_viewer/screens/score_viewer_screen.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/login',
    redirect: (context, state) {
      final authState = ref.read(authStateProvider);
      final isAuthenticated = authState.isAuthenticated;
      final isAuthRoute = state.matchedLocation == '/login' || 
                          state.matchedLocation == '/register';
      
      // Redirect to login if not authenticated and trying to access protected route
      if (!isAuthenticated && !isAuthRoute) {
        return '/login';
      }
      
      // Redirect to jobs if authenticated and trying to access auth routes
      if (isAuthenticated && isAuthRoute) {
        return '/jobs';
      }
      
      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        name: 'login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/register',
        name: 'register',
        builder: (context, state) => const RegisterScreen(),
      ),
      GoRoute(
        path: '/jobs',
        name: 'jobs',
        builder: (context, state) => const JobsListScreen(),
      ),
      GoRoute(
        path: '/jobs/:id',
        name: 'jobDetail',
        builder: (context, state) {
          final jobId = state.pathParameters['id']!;
          return JobDetailScreen(jobId: jobId);
        },
      ),
      GoRoute(
        path: '/upload',
        name: 'upload',
        builder: (context, state) => const UploadScreen(),
      ),
      GoRoute(
        path: '/score/:jobId',
        name: 'score',
        builder: (context, state) {
          final jobId = state.pathParameters['jobId']!;
          return ScoreViewerScreen(jobId: jobId);
        },
      ),
    ],
  );
});

