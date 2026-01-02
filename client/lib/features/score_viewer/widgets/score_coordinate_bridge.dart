import 'dart:ui';
import 'score_layout_calculator.dart';

/// Bridge between Canvas coordinates and overlay positioning.
/// 
/// Provides methods to calculate screen positions for notes
/// based on the Canvas coordinate system, enabling overlays
/// (fingering, confidence) to position themselves correctly.
class ScoreCoordinateBridge {
  final ScoreLayoutCalculator layoutCalculator;
  
  ScoreCoordinateBridge({required this.layoutCalculator});
  
  /// Calculate the bounding box for a note in Canvas coordinates.
  /// This replaces the IR bounding_box for overlay positioning.
  Rect getNoteBoundingBox(Map<String, dynamic> note) {
    return layoutCalculator.calculateNoteBoundingBox(note);
  }
  
  /// Get the center position for a note.
  Offset getNoteCenter(Map<String, dynamic> note) {
    final bbox = getNoteBoundingBox(note);
    return bbox.center;
  }
  
  /// Get the position for a fingering marker (above the note).
  Offset getFingeringMarkerPosition(Map<String, dynamic> note) {
    final bbox = getNoteBoundingBox(note);
    // Position above the note
    return Offset(bbox.center.dx, bbox.top - 20);
  }
  
  /// Get the position for a confidence highlight (around the note).
  Rect getConfidenceHighlightRect(Map<String, dynamic> note) {
    final bbox = getNoteBoundingBox(note);
    // Expand slightly for highlight
    return bbox.inflate(5);
  }
  
  /// Calculate position for a note based on its IR v2 data.
  /// Returns the center point of where the note should be rendered.
  Offset calculateNotePosition(Map<String, dynamic> note) {
    final time = note['time'] as Map<String, dynamic>?;
    final spatial = note['spatial'] as Map<String, dynamic>?;
    
    if (time == null || spatial == null) {
      return Offset.zero;
    }
    
    final measure = (time['measure'] as int?) ?? 1;
    final beat = (time['beat'] as num?)?.toDouble() ?? 0.0;
    final staffId = spatial['staff_id'] as String? ?? 'staff_0';
    final staffPosition = (spatial['staff_position'] as num?)?.toDouble() ?? 0.0;
    
    final staffIndex = layoutCalculator.getStaffIndex(staffId);
    final x = layoutCalculator.calculateNoteX(measure, beat);
    final y = layoutCalculator.calculateNoteY(staffIndex, staffPosition);
    
    return Offset(x, y);
  }
  
  /// Get the staff index for a note.
  int getStaffIndexForNote(Map<String, dynamic> note) {
    final spatial = note['spatial'] as Map<String, dynamic>?;
    final staffId = spatial?['staff_id'] as String? ?? 'staff_0';
    return layoutCalculator.getStaffIndex(staffId);
  }
  
  /// Check if a point is within a note's bounding box.
  bool isPointInNote(Offset point, Map<String, dynamic> note) {
    final bbox = getNoteBoundingBox(note);
    return bbox.contains(point);
  }
  
  /// Find the note at a given point (for hit testing).
  Map<String, dynamic>? findNoteAtPoint(
    Offset point, 
    List<Map<String, dynamic>> notes,
  ) {
    for (final note in notes) {
      if (isPointInNote(point, note)) {
        return note;
      }
    }
    return null;
  }
  
  /// Get all notes visible on the current page.
  List<Map<String, dynamic>> getNotesForPage(
    Map<String, dynamic> irV2Data, 
    int pageNumber,
  ) {
    final notes = irV2Data['notes'] as List<dynamic>? ?? [];
    return notes
        .cast<Map<String, dynamic>>()
        .where((note) {
          final spatial = note['spatial'] as Map<String, dynamic>?;
          if (spatial == null) return false;
          final pageNum = spatial['page_number'] as int? ?? 1;
          return pageNum == pageNumber + 1; // Pages are 1-indexed in IR
        })
        .toList();
  }
  
  /// Calculate measure bounds for highlighting.
  Rect getMeasureBounds(int measureNumber, int staffIndex) {
    final x = layoutCalculator.calculateMeasureBarX(measureNumber - 1);
    final nextX = layoutCalculator.calculateMeasureBarX(measureNumber);
    final staffTopY = layoutCalculator.calculateStaffTopY(staffIndex);
    final staffHeight = ScoreLayoutCalculator.staffHeight;
    
    return Rect.fromLTRB(x, staffTopY, nextX, staffTopY + staffHeight);
  }
  
  /// Get the canvas size for the current layout.
  Size get canvasSize => layoutCalculator.calculateCanvasSize();
  
  /// Get the staff count.
  int get staffCount => layoutCalculator.staffCount;
  
  /// Check if this is a grand staff (piano) layout.
  bool get isGrandStaff => layoutCalculator.isGrandStaff;
}

/// Provider class for creating coordinate bridges.
/// Useful for dependency injection in overlay widgets.
class ScoreCoordinateBridgeProvider {
  final Map<String, dynamic> irV2Data;
  final int pageNumber;
  
  late final ScoreLayoutCalculator _layoutCalculator;
  late final ScoreCoordinateBridge _bridge;
  
  ScoreCoordinateBridgeProvider({
    required this.irV2Data,
    required this.pageNumber,
  }) {
    _layoutCalculator = ScoreLayoutCalculator(
      irV2Data: irV2Data,
      pageNumber: pageNumber,
    );
    _bridge = ScoreCoordinateBridge(layoutCalculator: _layoutCalculator);
  }
  
  ScoreLayoutCalculator get layoutCalculator => _layoutCalculator;
  ScoreCoordinateBridge get bridge => _bridge;
}

