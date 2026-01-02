import 'dart:ui';

/// Layout calculator for converting IR v2 data to Canvas coordinates.
/// 
/// Handles conversion of temporal (measure/beat) and spatial (staff_position)
/// data to absolute pixel coordinates for Canvas rendering.
class ScoreLayoutCalculator {
  // Layout constants
  static const double staffLineSpacing = 10.0;
  static const double staffHeight = 4 * staffLineSpacing; // 5 lines = 4 spaces
  static const double staffSystemSpacing = 100.0; // Space between staff systems
  static const double leftMargin = 100.0; // Space for clefs/key signatures
  static const double topMargin = 60.0;
  static const double rightMargin = 50.0;
  static const double bottomMargin = 50.0;
  static const double measureWidth = 200.0;
  static const double clefWidth = 40.0;
  static const double keySignatureWidth = 30.0;
  static const double timeSignatureWidth = 30.0;
  
  // Grand staff spacing (between treble and bass)
  static const double grandStaffGap = 60.0;
  
  final Map<String, dynamic> irV2Data;
  final int pageNumber;
  
  // Cached calculations
  late final int _beatsPerMeasure;
  late final int _measureCount;
  late final int _staffCount;
  late final bool _isGrandStaff;
  
  ScoreLayoutCalculator({
    required this.irV2Data,
    required this.pageNumber,
  }) {
    _initialize();
  }
  
  void _initialize() {
    // Extract time signature
    final timeSig = irV2Data['time_signature'] as Map<String, dynamic>?;
    _beatsPerMeasure = (timeSig?['numerator'] as int?) ?? 4;
    
    // Count measures from notes
    final notes = _getNotesForPage();
    if (notes.isEmpty) {
      _measureCount = 1;
    } else {
      _measureCount = notes
          .map((n) => (n['time']?['measure'] as int?) ?? 1)
          .reduce((a, b) => a > b ? a : b);
    }
    
    // Count staves
    final staves = irV2Data['staves'] as List<dynamic>? ?? [];
    _staffCount = staves.length.clamp(1, 2);
    _isGrandStaff = _staffCount == 2;
  }
  
  /// Get notes filtered for the current page
  List<Map<String, dynamic>> _getNotesForPage() {
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
  
  /// Calculate total canvas size needed
  Size calculateCanvasSize() {
    final width = leftMargin + 
                  clefWidth + 
                  keySignatureWidth + 
                  timeSignatureWidth + 
                  (_measureCount * measureWidth) + 
                  rightMargin;
    
    double height;
    if (_isGrandStaff) {
      // Grand staff: treble + gap + bass + margins
      height = topMargin + 
               staffHeight + 
               grandStaffGap + 
               staffHeight + 
               bottomMargin;
    } else {
      // Single staff
      height = topMargin + staffHeight + bottomMargin;
    }
    
    return Size(width, height);
  }
  
  /// Get the Y position for a staff's top line
  double calculateStaffTopY(int staffIndex) {
    if (_isGrandStaff) {
      // Staff 0 (treble) at top, Staff 1 (bass) below
      if (staffIndex == 0) {
        return topMargin;
      } else {
        return topMargin + staffHeight + grandStaffGap;
      }
    }
    return topMargin + (staffIndex * staffSystemSpacing);
  }
  
  /// Get the Y position for the center (middle line) of a staff
  double calculateStaffCenterY(int staffIndex) {
    return calculateStaffTopY(staffIndex) + (staffHeight / 2);
  }
  
  /// Calculate X position for a note based on measure and beat
  double calculateNoteX(int measure, double beat) {
    final measureStartX = leftMargin + 
                          clefWidth + 
                          keySignatureWidth + 
                          timeSignatureWidth + 
                          ((measure - 1) * measureWidth);
    
    final beatWidth = measureWidth / _beatsPerMeasure;
    return measureStartX + (beat * beatWidth) + 20; // 20px offset from measure start
  }
  
  /// Calculate Y position for a note based on staff position
  /// staff_position: 0 = middle line, positive = above, negative = below
  /// Each step is half a staff line spacing (line or space)
  double calculateNoteY(int staffIndex, double staffPosition) {
    final staffCenterY = calculateStaffCenterY(staffIndex);
    // Negative because Y increases downward in Canvas
    // Each staff position step is half a line spacing
    return staffCenterY - (staffPosition * (staffLineSpacing / 2));
  }
  
  /// Get staff index from staff_id string (e.g., "staff_0" -> 0)
  int getStaffIndex(String staffId) {
    final match = RegExp(r'staff_(\d+)').firstMatch(staffId);
    if (match != null) {
      return int.parse(match.group(1)!);
    }
    // Fallback heuristics
    if (staffId.toLowerCase().contains('bass')) return 1;
    if (staffId.toLowerCase().contains('treble')) return 0;
    return 0;
  }
  
  /// Calculate X position for measure bar line
  double calculateMeasureBarX(int measureNumber) {
    return leftMargin + 
           clefWidth + 
           keySignatureWidth + 
           timeSignatureWidth + 
           (measureNumber * measureWidth);
  }
  
  /// Calculate bounding box for a note (for overlay positioning)
  Rect calculateNoteBoundingBox(Map<String, dynamic> note) {
    final time = note['time'] as Map<String, dynamic>?;
    final spatial = note['spatial'] as Map<String, dynamic>?;
    
    if (time == null || spatial == null) {
      return Rect.zero;
    }
    
    final measure = (time['measure'] as int?) ?? 1;
    final beat = (time['beat'] as num?)?.toDouble() ?? 0.0;
    final staffId = spatial['staff_id'] as String? ?? 'staff_0';
    final staffPosition = (spatial['staff_position'] as num?)?.toDouble() ?? 0.0;
    
    final staffIndex = getStaffIndex(staffId);
    final x = calculateNoteX(measure, beat);
    final y = calculateNoteY(staffIndex, staffPosition);
    
    // Note head is approximately 12x10 pixels
    const noteWidth = 12.0;
    const noteHeight = 10.0;
    
    return Rect.fromCenter(
      center: Offset(x, y),
      width: noteWidth,
      height: noteHeight,
    );
  }
  
  // Getters for layout properties
  int get beatsPerMeasure => _beatsPerMeasure;
  int get measureCount => _measureCount;
  int get staffCount => _staffCount;
  bool get isGrandStaff => _isGrandStaff;
  
  /// Get clef type for a staff
  String getClefForStaff(int staffIndex) {
    final staves = irV2Data['staves'] as List<dynamic>? ?? [];
    if (staffIndex < staves.length) {
      final staff = staves[staffIndex] as Map<String, dynamic>;
      return staff['clef'] as String? ?? 'treble';
    }
    // Default: treble for first staff, bass for second
    return staffIndex == 0 ? 'treble' : 'bass';
  }
  
  /// Get key signature fifths (-7 to 7)
  int getKeySignatureFifths() {
    final keySig = irV2Data['key_signature'] as Map<String, dynamic>?;
    return (keySig?['fifths'] as int?) ?? 0;
  }
  
  /// Get time signature numerator
  int getTimeSignatureNumerator() {
    final timeSig = irV2Data['time_signature'] as Map<String, dynamic>?;
    return (timeSig?['numerator'] as int?) ?? 4;
  }
  
  /// Get time signature denominator
  int getTimeSignatureDenominator() {
    final timeSig = irV2Data['time_signature'] as Map<String, dynamic>?;
    return (timeSig?['denominator'] as int?) ?? 4;
  }
}

