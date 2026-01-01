---
name: Score Viewer with SVG and Fingering Overlays
overview: Implement the complete score viewer feature with SVG rendering, interactive fingering overlays, confidence visualization, and multi-page navigation. This includes creating the score_viewer feature module with providers, widgets, and screens that integrate with the existing Flutter app infrastructure.
todos:
  - id: score-viewer-provider
    content: Create ScoreViewerProvider with state management for SVG pages, IR v2 data, zoom, page navigation, and display toggles. Use ArtifactRepository for downloads and properly filter artifacts by typeEnum.
    status: completed
  - id: svg-viewer-widget
    content: Create ScoreSvgViewer widget that renders SVG using SvgPicture.string with InteractiveViewer for zoom/pan, and stacks overlays on top.
    status: completed
    dependencies:
      - score-viewer-provider
  - id: fingering-overlay
    content: Create FingeringOverlay widget that displays colored fingering markers positioned above notes, with tap-to-view alternatives popup.
    status: completed
    dependencies:
      - svg-viewer-widget
  - id: confidence-overlay
    content: Create ConfidenceOverlay widget that highlights low-confidence notes and displays region-level warnings.
    status: completed
    dependencies:
      - svg-viewer-widget
  - id: confidence-legend
    content: Create ConfidenceLegend widget that explains the confidence color coding system with descriptions.
    status: completed
  - id: score-viewer-screen
    content: Create ScoreViewerScreen with AppBar controls, main viewer area, page navigation, and responsive sidebar with legend and statistics.
    status: completed
    dependencies:
      - score-viewer-provider
      - svg-viewer-widget
      - fingering-overlay
      - confidence-overlay
      - confidence-legend
  - id: update-router
    content: Update app_router.dart to use ScoreViewerScreen instead of placeholder for /score/:jobId route.
    status: completed
    dependencies:
      - score-viewer-screen
---

# Score Viewer Implementati

on - Tasks 5.8-5.12

## Overview

Implement the complete score viewer feature that displays SVG-rendered sheet music with interactive fingering overlays, confidence visualization, and comprehensive navigation controls. The implementation will create a new `score_viewer` feature module that integrates with existing repositories and routing.

## Architecture

The score viewer consists of:

- **ScoreViewerProvider**: Manages state for SVG pages, IR v2 data, zoom, page navigation, and display toggles
- **ScoreSvgViewer**: Main widget that renders SVG with InteractiveViewer for zoom/pan
- **FingeringOverlay**: Displays fingering numbers as colored markers with tap-to-view alternatives
- **ConfidenceOverlay**: Highlights low-confidence regions and notes
- **ConfidenceLegend**: Explains the confidence color coding system
- **ScoreViewerScreen**: Complete screen with controls, navigation, and sidebar

## Implementation Details

### Task 5.8: Score Display with SVG Rendering

#### Files to Create:

1. **`lib/features/score_viewer/providers/score_viewer_provider.dart`**

- State class: `ScoreViewerState` with SVG pages, IR v2 data, current page, zoom, loading/error states, and display toggles
- Notifier: `ScoreViewerNotifier` that:
    - Uses `ArtifactRepository` (not JobRepository) for downloading artifacts
    - Filters artifacts by type using `artifact.typeEnum == ArtifactType.svg` and `ArtifactType.irV2`
    - Downloads SVG pages to temp directory and reads content
    - Parses IR v2 JSON for fingering data
    - Provides methods for page navigation, zoom control, and toggles
- Provider: `scoreViewerProvider` as a family provider keyed by jobId

2. **`lib/features/score_viewer/widgets/score_svg_viewer.dart`**

- `ScoreSvgViewer` widget that:
    - Uses `SvgPicture.string()` to render SVG content
    - Wraps in `InteractiveViewer` for zoom/pan gestures
    - Uses `TransformationController` synced with zoom prop
    - Stacks `FingeringOverlay` and `ConfidenceOverlay` on top

3. **`lib/features/score_viewer/widgets/fingering_overlay.dart`**

- `FingeringOverlay` widget that:
    - Filters notes by page number from IR v2 data
    - Renders colored circular markers positioned above notes
    - Color coding: green (≥80%), orange (60-80%), red (<60%)
    - Tap gesture to show alternatives popup
    - Displays alternative fingerings with confidence percentages

### Task 5.9: Confidence Visualization

#### Files to Create:

4. **`lib/features/score_viewer/widgets/confidence_overlay.dart`**

- `ConfidenceOverlay` widget that:
    - Highlights low-confidence notes (<60%) with red semi-transparent boxes
    - Displays region-level warnings for low-confidence measure ranges
    - Shows banners at top of page for problematic regions

5. **`lib/features/score_viewer/widgets/confidence_legend.dart`**

- `ConfidenceLegend` widget that:
    - Displays color-coded legend explaining confidence levels
    - Shows descriptions for each confidence tier
    - Card-based UI matching app theme

### Task 5.10: Score Viewer Screen

#### Files to Create:

6. **`lib/features/score_viewer/screens/score_viewer_screen.dart`**

- `ScoreViewerScreen` widget that:
    - Uses `scoreViewerProvider(jobId)` to watch state
    - AppBar with toggle buttons for fingering/confidence visibility
    - Zoom controls in popup menu
    - Main content area with `ScoreSvgViewer`
    - Page navigation bar at bottom for multi-page scores
    - Responsive sidebar (desktop only) with:
    - Confidence legend
    - Usage instructions
    - Fingering statistics from IR v2 metadata
    - Error and loading states

### Task 5.11: App Routing

#### Files to Update:

7. **`lib/routing/app_router.dart`**

- Update the `/score/:jobId` route to use `ScoreViewerScreen` instead of placeholder
- Import the new screen

### Task 5.12: Main App Entry

#### Files to Check/Update:

8. **`lib/main.dart`** and **`lib/app.dart`**

- Verify current setup uses `app.dart` (already correct)
- No changes needed if using existing `app.dart` structure

## Key Implementation Notes

### Repository Usage

- Use `ArtifactRepository` (via `artifactRepositoryProvider`) for downloading artifacts, not `JobRepository`
- Use `JobRepository.getJobArtifacts()` to fetch artifact list
- The `Artifact.typeEnum` property converts string `artifact_type` to `ArtifactType` enum

### Artifact Type Matching

- Use `artifact.typeEnum == ArtifactType.svg` to filter SVG artifacts
- Use `artifact.typeEnum == ArtifactType.irV2` to find IR v2 artifact
- Sort SVG artifacts by `createdAt` to maintain page order

### IR v2 Data Structure

- Expected structure: `{'notes': [...], 'metadata': {...}, 'fingering_metadata': {...}}`
- Notes contain: `note_id`, `spatial` (with `page_number`, `bounding_box`), `fingering` (with `finger`, `confidence`, `hand`, `alternatives`)
- Metadata may contain `low_confidence_regions` array

### Coordinate System

- SVG coordinates are in SVG units
- IR v2 bounding boxes are in SVG coordinate space
- Apply zoom multiplier when positioning overlays: `x * zoom`, `y * zoom`

### Error Handling

- Handle missing artifacts gracefully
- Show user-friendly error messages
- Handle JSON parsing errors
- Handle file I/O errors

## Dependencies

All required dependencies are already in `pubspec.yaml`:

- `flutter_svg: ^2.0.9` for SVG rendering
- `flutter_riverpod: ^2.4.9` for state management
- `go_router: ^12.1.3` for navigation
- `path_provider: ^2.1.1` for temp directory access
- `google_fonts: ^6.1.0` for typography

## Testing Considerations

- Test with single-page and multi-page scores
- Test with varying confidence levels
- Test zoom/pan gestures on mobile and desktop
- Test tap interactions on fingering markers
- Test error states (missing artifacts, network errors)
- Test responsive layout (mobile vs desktop sidebar)

## File Structure

```javascript
lib/features/score_viewer/
├── providers/
│   └── score_viewer_provider.dart
├── widgets/
│   ├── score_svg_viewer.dart
│   ├── fingering_overlay.dart
│   ├── confidence_overlay.dart
│   └── confidence_legend.dart
└── screens/
    └── score_viewer_screen.dart
```



## Code Fixes Required

1. **Import fix**: Move `dart:convert` import to top of file, not inside method
2. **Repository fix**: Use `ArtifactRepository.downloadArtifact()` instead of `JobRepository.downloadArtifact()`
3. **Type matching**: Use `artifact.typeEnum` property instead of string comparison