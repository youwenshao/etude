# Étude Flutter Client

Flutter application for the Étude piano fingering pipeline. This app provides a user interface for uploading sheet music PDFs and viewing annotated scores with fingering suggestions.

## Features

- **Authentication**: User registration and login with JWT tokens
- **PDF Upload**: Upload sheet music PDFs with progress tracking
- **Job Management**: View and track processing jobs through the pipeline
- **Real-time Updates**: Automatic polling for job status updates
- **Responsive Design**: Works on mobile, tablet, and desktop

## Setup

### Prerequisites

- Flutter SDK 3.0.0 or higher
- Dart SDK 3.0.0 or higher

### Installation

1. Install dependencies:
```bash
flutter pub get
```

2. Generate code for JSON serialization:
```bash
flutter pub run build_runner build --delete-conflicting-outputs
```

3. Configure API base URL (optional):
```bash
# For development (default: http://localhost:8000)
flutter run --dart-define=API_BASE_URL=http://localhost:8000

# For production
flutter run --dart-define=API_BASE_URL=https://api.etude.example.com
```

## Running the App

```bash
# Run in debug mode
flutter run

# Run on specific device
flutter run -d <device-id>

# Build for release
flutter build apk  # Android
flutter build ios  # iOS
flutter build web  # Web
```

## Project Structure

```
lib/
├── main.dart                 # App entry point
├── app.dart                  # Root widget
├── core/                     # Core utilities and configuration
│   ├── config/              # API and app configuration
│   ├── theme/                # Theme and styling
│   ├── utils/                # Utility functions
│   └── widgets/              # Reusable widgets
├── data/                     # Data layer
│   ├── models/              # Data models
│   ├── providers/           # API client providers
│   └── repositories/        # Data repositories
├── features/                 # Feature modules
│   ├── auth/                # Authentication
│   ├── upload/               # PDF upload
│   ├── jobs/                 # Job management
│   └── score_viewer/         # Score viewer (future)
└── routing/                  # Navigation and routing
```

## Architecture

The app follows clean architecture principles:

- **Data Layer**: Models, repositories, and API client
- **Domain Layer**: Business logic and state management (Riverpod)
- **Presentation Layer**: Screens, widgets, and routing

## State Management

The app uses [Riverpod](https://riverpod.dev/) for state management:

- `authStateProvider`: Authentication state
- `uploadProvider`: PDF upload progress
- `jobsProvider`: Job list
- `jobPollingProvider`: Real-time job status updates

## API Integration

The app communicates with the Étude backend API:

- Base URL: Configurable via `API_BASE_URL` environment variable
- Authentication: JWT tokens stored securely
- Endpoints:
  - `/api/v1/auth/*` - Authentication
  - `/api/v1/jobs/*` - Job management
  - `/api/v1/artifacts/*` - Artifact retrieval

## Development

### Code Generation

After modifying models with `@JsonSerializable`, regenerate code:

```bash
flutter pub run build_runner build --delete-conflicting-outputs
```

### Testing

```bash
# Run all tests
flutter test

# Run with coverage
flutter test --coverage
```

## Troubleshooting

### Build Errors

If you encounter build errors related to generated files:

1. Clean the build:
```bash
flutter clean
```

2. Get dependencies:
```bash
flutter pub get
```

3. Regenerate code:
```bash
flutter pub run build_runner build --delete-conflicting-outputs
```

### API Connection Issues

- Verify the backend server is running
- Check `API_BASE_URL` configuration
- Ensure CORS is properly configured on the backend
- Check network connectivity

## License

See the main project README for license information.

