import 'package:flutter/material.dart';
import 'package:vector_math/vector_math_64.dart' as vm;
import 'score_coordinate_bridge.dart';

class PlaybackHighlightPainter extends CustomPainter {
  final String? activeNoteId;
  final Map<String, dynamic>? irV2Data;
  final int pageNumber;
  final double zoom;
  final TransformationController transformationController;
  final ScoreCoordinateBridge? coordinateBridge;
  
  PlaybackHighlightPainter({
    required this.activeNoteId,
    required this.irV2Data,
    required this.pageNumber,
    required this.zoom,
    required this.transformationController,
    this.coordinateBridge,
  });
  
  /// Get note rectangle using coordinate bridge or fallback to IR bounding box
  Rect _getNoteRect(Map<String, dynamic> note) {
    if (coordinateBridge != null) {
      return coordinateBridge!.getNoteBoundingBox(note).inflate(5);
    }
    
    // Fallback to IR bounding box
    final spatial = note['spatial'] as Map<String, dynamic>?;
    if (spatial == null) return Rect.zero;
    
    final bbox = spatial['bounding_box'] as Map<String, dynamic>?;
    if (bbox == null) return Rect.zero;
    
    final x = (bbox['x'] as num?)?.toDouble() ?? 0.0;
    final y = (bbox['y'] as num?)?.toDouble() ?? 0.0;
    final width = (bbox['width'] as num?)?.toDouble() ?? 0.0;
    final height = (bbox['height'] as num?)?.toDouble() ?? 0.0;
    
    return Rect.fromLTWH(x, y, width, height);
  }
  
  @override
  void paint(Canvas canvas, Size size) {
    // If no active note or no IR v2 data, don't draw anything
    if (activeNoteId == null || irV2Data == null) {
      return;
    }
    
    // Get notes from IR v2
    final notes = irV2Data!['notes'] as List<dynamic>?;
    if (notes == null || notes.isEmpty) {
      return;
    }
    
    // Find the active note
    Map<String, dynamic>? activeNote;
    for (final note in notes) {
      if (note is! Map<String, dynamic>) continue;
      final noteId = note['note_id'] as String?;
      if (noteId == activeNoteId) {
        activeNote = note;
        break;
      }
    }
    
    if (activeNote == null) {
      return;
    }
    
    // Get spatial information
    final spatial = activeNote['spatial'] as Map<String, dynamic>?;
    if (spatial == null) {
      return;
    }
    
    // Check if note is on current page
    final pageNum = spatial['page_number'] as int? ?? 1;
    if (pageNum != pageNumber + 1) {
      return; // Note is on a different page
    }
    
    // Get bounding box
    final rect = _getNoteRect(activeNote);
    if (rect == Rect.zero || rect.width <= 0 || rect.height <= 0) {
      return;
    }
    
    // Apply transformation matrix
    final matrix = transformationController.value;
    
    // Create rectangle corners as Vector3
    final topLeft = vm.Vector3(rect.left, rect.top, 0);
    final topRight = vm.Vector3(rect.right, rect.top, 0);
    final bottomLeft = vm.Vector3(rect.left, rect.bottom, 0);
    final bottomRight = vm.Vector3(rect.right, rect.bottom, 0);
    
    // Transform corners
    final transformedTopLeft = matrix.transform3(topLeft);
    final transformedTopRight = matrix.transform3(topRight);
    final transformedBottomLeft = matrix.transform3(bottomLeft);
    final transformedBottomRight = matrix.transform3(bottomRight);
    
    // Create transformed rectangle from transformed corners
    final minX = [transformedTopLeft.x, transformedTopRight.x, transformedBottomLeft.x, transformedBottomRight.x].reduce((a, b) => a < b ? a : b);
    final minY = [transformedTopLeft.y, transformedTopRight.y, transformedBottomLeft.y, transformedBottomRight.y].reduce((a, b) => a < b ? a : b);
    final maxX = [transformedTopLeft.x, transformedTopRight.x, transformedBottomLeft.x, transformedBottomRight.x].reduce((a, b) => a > b ? a : b);
    final maxY = [transformedTopLeft.y, transformedTopRight.y, transformedBottomLeft.y, transformedBottomRight.y].reduce((a, b) => a > b ? a : b);
    
    final transformedRect = Rect.fromLTRB(minX, minY, maxX, maxY);
    
    // Create paint for highlight
    final paint = Paint()
      ..color = Colors.blue.withOpacity(0.3)
      ..style = PaintingStyle.fill;
    
    final borderPaint = Paint()
      ..color = Colors.blue
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0;
    
    // Draw filled rectangle
    canvas.drawRect(transformedRect, paint);
    
    // Draw border
    canvas.drawRect(transformedRect, borderPaint);
  }
  
  @override
  bool shouldRepaint(PlaybackHighlightPainter oldDelegate) {
    // Repaint if active note changed, page changed, or zoom changed
    return oldDelegate.activeNoteId != activeNoteId ||
           oldDelegate.pageNumber != pageNumber ||
           oldDelegate.zoom != zoom ||
           oldDelegate.transformationController.value != transformationController.value;
  }
}

