---
name: Flutter Client Core Implementation
overview: Build a Flutter client application with authentication, PDF upload, job tracking, and SVG score viewer with fingering overlays. The app will integrate with the existing FastAPI backend and provide a responsive, confidence-aware UI for viewing annotated sheet music.
todos:
  - id: setup-project
    content: Initialize Flutter project structure, create pubspec.yaml with all dependencies, and set up build configuration
    status: completed
  - id: create-models
    content: Create data models (User, Job, Artifact) with JSON serialization, matching backend schemas exactly
    status: completed
    dependencies:
      - setup-project
  - id: api-client
    content: Implement Dio API client with auth interceptor, error handling, and secure token storage
    status: completed
    dependencies:
      - create-models
  - id: repositories
    content: Create repositories (AuthRepository, JobRepository, ArtifactRepository) with all CRUD operations
    status: completed
    dependencies:
      - api-client
  - id: state-providers
    content: Implement Riverpod providers for auth state, upload state, and job polling
    status: completed
    dependencies:
      - repositories
  - id: auth-screens
    content: Build login and register screens with form validation and error handling
    status: completed
    dependencies:
      - state-providers
  - id: upload-flow
    content: Implement PDF upload screen with file picker, progress tracking, and error handling
    status: completed
    dependencies:
      - state-providers
  - id: job-screens
    content: Create jobs list and job detail screens with real-time polling and status indicators
    status: completed
    dependencies:
      - state-providers
  - id: routing
    content: Set up GoRouter with protected routes, navigation guards, and route definitions
    status: completed
    dependencies:
      - auth-screens
  - id: core-widgets
    content: Create reusable widgets (loading indicators, error widgets, buttons) and theme configuration
    status: completed
    dependencies:
      - setup-project
  - id: code-generation
    content: Run build_runner to generate JSON serialization code and verify all models compile
    status: completed
    dependencies:
      - create-models
---

# Phase 5: Flutter Client - Core Implemen

tation

## Overview

Build a Flutter application that provides a user interface for the Étude piano fingering pipeline. The app will handle authentication, PDF uploads, job status tracking, and display rendered scores with fingering annotations.

## Architecture

The app follows clean architecture principles with:

- **Data Layer**: Models, repositories, and API client
- **Domain Layer**: Business logic and state management (Riverpod)
- **Presentation Layer**: Screens, widgets, and routing

## Implementation Tasks

### 1. Project Setup and Configuration

**Files to create:**

- `client/pubspec.yaml` - Flutter dependencies and configuration
- `client/lib/main.dart` - Application entry point
- `client/lib/app.dart` - Root widget with providers
- `client/lib/core/config/api_config.dart` - API endpoint configuration
- `client/lib/core/config/app_config.dart` - App-level configuration
- `client/lib/core/theme/app_theme.dart` - Material theme configuration
- `client/lib/core/theme/colors.dart` - Color palette
- `client/lib/core/theme/text_styles.dart` - Typography definitions

**Key dependencies:**

- `flutter_riverpod` for state management
- `go_router` for navigation
- `dio` for HTTP client
- `flutter_secure_storage` for token storage
- `file_picker` for PDF selection
- `flutter_svg` for rendering SVG scores

### 2. Data Models

**Files to create:**

- `client/lib/data/models/user.dart` - User and AuthResponse models
- `client/lib/data/models/job.dart` - Job model with status enum and helpers
- `client/lib/data/models/artifact.dart` - Artifact model

**Key points:**

- Match backend schemas from `server/app/schemas/`
- Use `json_serializable` for JSON serialization
- Job status enum must match `JobStatus` from `server/app/models/job.py`:
- `pending`, `omr_processing`, `omr_completed`, `omr_failed`
- `fingering_processing`, `fingering_completed`, `fingering_failed`
- `rendering_processing`, `completed`, `failed`
- Add helper methods: `isProcessing`, `isComplete`, `isFailed`, `progress`, `statusDisplayName`

### 3. API Client and Repositories

**Files to create:**

- `client/lib/data/providers/api_client_provider.dart` - Dio client with interceptors
- `client/lib/data/repositories/auth_repository.dart` - Authentication operations
- `client/lib/data/repositories/job_repository.dart` - Job CRUD and file upload
- `client/lib/data/repositories/artifact_repository.dart` - Artifact retrieval

**API endpoints (from `server/app/api/v1/`):**

- Auth: `/api/v1/auth/login`, `/api/v1/auth/register`, `/api/v1/auth/me`
- Jobs: `/api/v1/jobs` (POST with multipart/form-data), `/api/v1/jobs/{id}`, `/api/v1/jobs` (GET with pagination)
- Artifacts: `/api/v1/artifacts/jobs/{job_id}/artifacts`, `/api/v1/artifacts/{id}/download`

**Key features:**

- Auth interceptor adds Bearer token from secure storage
- Error handling for 401 (logout) and network errors
- Upload progress tracking via `onSendProgress` callback
- Token stored in `FlutterSecureStorage` with key `auth_token`

### 4. State Management with Riverpod

**Files to create:**

- `client/lib/features/auth/providers/auth_state_provider.dart` - Auth state notifier
- `client/lib/features/upload/providers/upload_provider.dart` - Upload state management
- `client/lib/features/jobs/providers/jobs_provider.dart` - Job list and polling providers

**State providers:**

- `authStateProvider` - Manages user authentication state
- `uploadProvider` - Tracks PDF upload progress
- `jobsProvider` - FutureProvider for job list
- `jobDetailProvider` - FutureProvider.family for individual jobs
- `jobPollingProvider` - StreamProvider.family that polls every 2 seconds until complete/failed

### 5. Authentication Flow

**Files to create:**

- `client/lib/features/auth/screens/login_screen.dart` - Login UI with email/password
- `client/lib/features/auth/screens/register_screen.dart` - Registration with email, password, full_name
- `client/lib/features/auth/widgets/auth_form.dart` - Reusable form components

**Features:**

- Form validation (email format, password requirements)
- Loading states during API calls
- Error message display
- Auto-navigation to jobs list on success
- Password visibility toggle

### 6. PDF Upload Flow

**Files to create:**

- `client/lib/features/upload/screens/upload_screen.dart` - Upload interface
- `client/lib/features/upload/widgets/file_picker_widget.dart` - File selection UI
- `client/lib/features/upload/widgets/upload_progress_widget.dart` - Progress indicator

**Features:**

- Drag-and-drop or tap-to-select PDF
- File validation (PDF only)
- Upload progress bar (0-100%)
- Error handling and retry
- Auto-navigation to job detail on success

### 7. Job Management

**Files to create:**

- `client/lib/features/jobs/screens/jobs_list_screen.dart` - List of user's jobs
- `client/lib/features/jobs/screens/job_detail_screen.dart` - Job status and details
- `client/lib/features/jobs/widgets/job_card.dart` - Job list item widget
- `client/lib/features/jobs/widgets/job_status_indicator.dart` - Visual status indicator

**Features:**

- Job list with status, creation date
- Pull-to-refresh
- Job detail with real-time polling
- Progress indicator showing pipeline stage
- Error message display for failed jobs
- "View Score" button when complete

### 8. Routing Configuration

**Files to create:**

- `client/lib/routing/app_router.dart` - GoRouter configuration
- `client/lib/routing/route_names.dart` - Route path constants

**Routes:**

- `/login` - Login screen
- `/register` - Registration screen
- `/jobs` - Jobs list (protected)
- `/jobs/:id` - Job detail (protected)
- `/upload` - Upload screen (protected)
- `/score/:jobId` - Score viewer (protected, future task)

**Navigation guards:**

- Redirect to `/login` if not authenticated
- Redirect to `/jobs` if authenticated and accessing auth routes

### 9. Core Widgets and Utilities

**Files to create:**

- `client/lib/core/widgets/loading_indicator.dart` - Reusable loading spinner
- `client/lib/core/widgets/error_widget.dart` - Error display widget
- `client/lib/core/widgets/custom_button.dart` - Styled button component
- `client/lib/core/utils/constants.dart` - App constants
- `client/lib/core/utils/validators.dart` - Form validation helpers

### 10. Code Generation Setup

**Files to create:**

- `client/build.yaml` - Build runner configuration
- Run `flutter pub get` and `flutter pub run build_runner build` to generate:
- `*.g.dart` files for JSON serialization
- Retrofit API client code (if used)

## Implementation Notes

1. **API Base URL**: Configurable via environment variable `API_BASE_URL`, defaults to `http://localhost:8000`
2. **Token Management**: 

- Store JWT in `FlutterSecureStorage`
- Token format: `Bearer {token}` in Authorization header
- Auto-logout on 401 responses

3. **Job Polling**:

- Poll every 2 seconds while job is processing
- Stop polling when status is `completed` or any `*_failed` status
- Use `StreamProvider` for reactive updates

4. **Error Handling**:

- Network errors: Show user-friendly messages
- Validation errors: Display field-specific errors
- Server errors: Show error message from `detail` field

5. **File Upload**:

- Use `MultipartFile.fromFile()` for PDF upload
- Track progress via `onSendProgress` callback
- Validate file type and size before upload

## Testing Considerations

- Unit tests for models and repositories
- Widget tests for UI components
- Integration tests for API calls (use mock server)
- Test authentication flow and token persistence

## Future Enhancements (Not in Phase 5)

- Score viewer with SVG rendering and fingering overlays
- Confidence visualization
- Multi-page score navigation
- Offline caching of rendered scores
- Accessibility features (screen reader support)

## Dependencies Summary

**Production:**

- `flutter_riverpod: ^2.4.9` - State management
- `go_router: ^12.1.3` - Navigation
- `dio: ^5.4.0` - HTTP client
- `flutter_secure_storage: ^9.0.0` - Secure token storage
- `file_picker: ^6.1.1` - File selection
- `flutter_svg: ^2.0.9` - SVG rendering
- `json_annotation: ^4.8.1` - JSON serialization

**Development:**

- `build_runner: ^2.4.7` - Code generation