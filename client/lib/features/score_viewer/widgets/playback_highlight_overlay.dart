import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../playback/providers/active_note_provider.dart';
import 'playback_highlight_painter.dart';
import 'score_coordinate_bridge.dart';

class PlaybackHighlightOverlay extends ConsumerWidget {
  final String jobId;
  final Map<String, dynamic>? irV2Data;
  final int pageNumber;
  final double zoom;
  final TransformationController transformationController;
  final ScoreCoordinateBridge? coordinateBridge;
  
  const PlaybackHighlightOverlay({
    super.key,
    required this.jobId,
    required this.irV2Data,
    required this.pageNumber,
    required this.zoom,
    required this.transformationController,
    this.coordinateBridge,
  });
  
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Watch the active note provider
    final activeNoteId = ref.watch(activeNoteIdProvider(jobId));
    
    return CustomPaint(
      painter: PlaybackHighlightPainter(
        activeNoteId: activeNoteId,
        irV2Data: irV2Data,
        pageNumber: pageNumber,
        zoom: zoom,
        transformationController: transformationController,
        coordinateBridge: coordinateBridge,
      ),
      child: const SizedBox.expand(),
    );
  }
}
