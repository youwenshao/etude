import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../features/editor/providers/edit_mode_provider.dart';
import '../../../features/editor/widgets/fingering_edit_modal.dart';
import 'score_coordinate_bridge.dart';

class FingeringOverlay extends ConsumerStatefulWidget {
  final Map<String, dynamic> irV2Data;
  final int pageNumber;
  final double zoom;
  final TransformationController transformationController;
  final String? jobId;
  final ScoreCoordinateBridge? coordinateBridge;

  const FingeringOverlay({
    super.key,
    required this.irV2Data,
    required this.pageNumber,
    required this.zoom,
    required this.transformationController,
    this.jobId,
    this.coordinateBridge,
  });

  @override
  ConsumerState<FingeringOverlay> createState() => _FingeringOverlayState();
}

class _FingeringOverlayState extends ConsumerState<FingeringOverlay> {
  String? _selectedNoteId;

  List<Map<String, dynamic>> _getNotesForPage() {
    final notes = widget.irV2Data['notes'] as List<dynamic>? ?? [];

    // Filter notes for current page
    return notes.cast<Map<String, dynamic>>().where((note) {
      final spatial = note['spatial'] as Map<String, dynamic>?;
      if (spatial == null) return false;
      final pageNum = spatial['page_number'] as int? ?? 1;
      return pageNum == widget.pageNumber + 1; // Pages are 1-indexed in IR
    }).toList();
  }

  /// Get note position using coordinate bridge or fallback to IR bounding box
  Offset _getNotePosition(Map<String, dynamic> note) {
    if (widget.coordinateBridge != null) {
      return widget.coordinateBridge!.getFingeringMarkerPosition(note);
    }

    // Fallback to IR bounding box
    final spatial = note['spatial'] as Map<String, dynamic>?;
    if (spatial == null) return Offset.zero;

    final bbox = spatial['bounding_box'] as Map<String, dynamic>?;
    if (bbox == null) return Offset.zero;

    final x = (bbox['x'] as num?)?.toDouble() ?? 0.0;
    final y = (bbox['y'] as num?)?.toDouble() ?? 0.0;

    return Offset(x, y - 30); // Position above note
  }

  Widget _buildFingeringMarker(Map<String, dynamic> note) {
    final fingering = note['fingering'] as Map<String, dynamic>?;
    if (fingering == null) return const SizedBox.shrink();

    final finger = fingering['finger'] as int?;
    if (finger == null || finger == 0) return const SizedBox.shrink();

    final confidence = fingering['confidence'] as double? ?? 1.0;
    final noteId = note['note_id'] as String;

    final position = _getNotePosition(note);
    if (position == Offset.zero) return const SizedBox.shrink();

    // Determine color based on confidence
    final color = _getConfidenceColor(confidence);
    final isSelected = _selectedNoteId == noteId;

    return Positioned(
      left: position.dx * widget.zoom,
      top: position.dy * widget.zoom,
      child: GestureDetector(
        onTap: () {
          final isEditMode = ref.read(editModeProvider);
          if (isEditMode) {
            // In edit mode, show edit modal
            final fingering = note['fingering'] as Map<String, dynamic>?;
            final alternatives = fingering?['alternatives'] as List<dynamic>?;
            if (widget.jobId != null) {
              showModalBottomSheet(
                context: context,
                builder: (context) => FingeringEditModal(
                  jobId: widget.jobId!,
                  noteId: noteId,
                  currentFingering: fingering,
                  alternatives: alternatives,
                ),
              );
            }
          } else {
            // In view mode, toggle selection
            setState(() {
              _selectedNoteId = isSelected ? null : noteId;
            });
          }
        },
        child: Container(
          width: 24,
          height: 24,
          decoration: BoxDecoration(
            color: isSelected ? color.withOpacity(1.0) : color.withOpacity(0.8),
            shape: BoxShape.circle,
            border: Border.all(
              color: Colors.white,
              width: isSelected ? 2 : 1,
            ),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: color.withOpacity(0.5),
                      blurRadius: 8,
                      spreadRadius: 2,
                    ),
                  ]
                : null,
          ),
          child: Center(
            child: Text(
              finger.toString(),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Color _getConfidenceColor(double confidence) {
    if (confidence >= 0.8) {
      return Colors.green;
    } else if (confidence >= 0.6) {
      return Colors.orange;
    } else {
      return Colors.red;
    }
  }

  Widget? _buildAlternativesPopup() {
    if (_selectedNoteId == null) return null;

    final notes = _getNotesForPage();
    final selectedNote = notes.firstWhere(
      (note) => note['note_id'] == _selectedNoteId,
      orElse: () => {},
    );

    if (selectedNote.isEmpty) return null;

    final fingering = selectedNote['fingering'] as Map<String, dynamic>?;
    if (fingering == null) return null;

    final alternatives = fingering['alternatives'] as List<dynamic>? ?? [];
    if (alternatives.isEmpty) return null;

    final position = _getNotePosition(selectedNote);

    return Positioned(
      left: (position.dx + 30) * widget.zoom,
      top: position.dy * widget.zoom,
      child: Material(
        elevation: 8,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.grey[300]!),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Alternative Fingerings',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
              ),
              const SizedBox(height: 8),
              ...alternatives.map((alt) {
                final altFinger = alt['finger'] as int?;
                final altConfidence = alt['confidence'] as double?;
                if (altFinger == null || altConfidence == null) {
                  return const SizedBox.shrink();
                }
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 20,
                        height: 20,
                        decoration: BoxDecoration(
                          color: _getConfidenceColor(altConfidence),
                          shape: BoxShape.circle,
                        ),
                        child: Center(
                          child: Text(
                            altFinger.toString(),
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        '${(altConfidence * 100).toInt()}%',
                        style: const TextStyle(fontSize: 12),
                      ),
                    ],
                  ),
                );
              }),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final notes = _getNotesForPage();

    return Stack(
      children: [
        // Fingering markers
        ...notes.map((note) => _buildFingeringMarker(note)),

        // Alternatives popup
        if (_buildAlternativesPopup() != null) _buildAlternativesPopup()!,
      ],
    );
  }
}
