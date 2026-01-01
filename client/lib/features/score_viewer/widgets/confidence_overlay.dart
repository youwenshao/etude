import 'package:flutter/material.dart';

class ConfidenceOverlay extends StatelessWidget {
  final Map<String, dynamic> irV2Data;
  final int pageNumber;
  final double zoom;
  final TransformationController transformationController;
  
  const ConfidenceOverlay({
    super.key,
    required this.irV2Data,
    required this.pageNumber,
    required this.zoom,
    required this.transformationController,
  });
  
  List<Map<String, dynamic>> _getNotesForPage() {
    final notes = irV2Data['notes'] as List<dynamic>? ?? [];
    
    return notes
        .cast<Map<String, dynamic>>()
        .where((note) {
          final spatial = note['spatial'] as Map<String, dynamic>?;
          if (spatial == null) return false;
          final pageNum = spatial['page_number'] as int? ?? 1;
          return pageNum == pageNumber + 1;
        })
        .toList();
  }
  
  List<Map<String, dynamic>> _getLowConfidenceRegions() {
    final metadata = irV2Data['metadata'] as Map<String, dynamic>?;
    if (metadata == null) return [];
    
    final regions = metadata['low_confidence_regions'] as List<dynamic>? ?? [];
    return regions.cast<Map<String, dynamic>>();
  }
  
  Widget _buildConfidenceHighlight(Map<String, dynamic> note) {
    final fingering = note['fingering'] as Map<String, dynamic>?;
    if (fingering == null) return const SizedBox.shrink();
    
    final confidence = fingering['confidence'] as double? ?? 1.0;
    
    // Only highlight low confidence notes
    if (confidence >= 0.6) return const SizedBox.shrink();
    
    final spatial = note['spatial'] as Map<String, dynamic>?;
    if (spatial == null) return const SizedBox.shrink();
    
    final bbox = spatial['bounding_box'] as Map<String, dynamic>?;
    if (bbox == null) return const SizedBox.shrink();
    
    final x = (bbox['x'] as num?)?.toDouble() ?? 0.0;
    final y = (bbox['y'] as num?)?.toDouble() ?? 0.0;
    final width = (bbox['width'] as num?)?.toDouble() ?? 20.0;
    final height = (bbox['height'] as num?)?.toDouble() ?? 20.0;
    
    // Color intensity based on confidence
    final opacity = (1.0 - confidence) * 0.5; // Lower confidence = more visible
    
    return Positioned(
      left: (x - 5) * zoom,
      top: (y - 5) * zoom,
      child: Container(
        width: (width + 10) * zoom,
        height: (height + 10) * zoom,
        decoration: BoxDecoration(
          color: Colors.red.withOpacity(opacity),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: Colors.red.withOpacity(opacity + 0.3),
            width: 2,
          ),
        ),
      ),
    );
  }
  
  Widget _buildRegionHighlight(Map<String, dynamic> region) {
    final startMeasure = region['start_measure'] as int?;
    final endMeasure = region['end_measure'] as int?;
    final avgConfidence = region['average_confidence'] as double?;
    final reason = region['reason'] as String?;
    
    if (startMeasure == null || avgConfidence == null) {
      return const SizedBox.shrink();
    }
    
    // For simplicity, we'll show a banner at the top
    // In production, you'd calculate exact measure positions
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      margin: const EdgeInsets.only(top: 8, left: 8, right: 8),
      decoration: BoxDecoration(
        color: Colors.amber[100],
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: Colors.amber[700]!),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.warning_amber, size: 16, color: Colors.amber[900]),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Measure $startMeasure${endMeasure != startMeasure ? '-$endMeasure' : ''}: '
              'Low confidence (${(avgConfidence * 100).toInt()}%)'
              '${reason != null ? ' - $reason' : ''}',
              style: TextStyle(
                fontSize: 12,
                color: Colors.amber[900],
              ),
            ),
          ),
        ],
      ),
    );
  }
  
  @override
  Widget build(BuildContext context) {
    final notes = _getNotesForPage();
    final regions = _getLowConfidenceRegions();
    
    return Stack(
      children: [
        // Note-level confidence highlights
        ...notes.map((note) => _buildConfidenceHighlight(note)),
        
        // Region-level warnings
        if (regions.isNotEmpty)
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: regions.map((region) => _buildRegionHighlight(region)).toList(),
            ),
          ),
      ],
    );
  }
}

