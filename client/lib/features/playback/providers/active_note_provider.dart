import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'playback_controller.dart';
import '../../../features/score_viewer/providers/score_viewer_provider.dart';

/// Derived provider that computes the active note_id based on current playback position
/// and IR v2 data. Returns null if no note is currently playing.
final activeNoteIdProvider = Provider.family<String?, String>((ref, jobId) {
  // Watch playback controller for current position
  final playbackState = ref.watch(playbackControllerProvider(jobId));
  
  // Watch score viewer for IR v2 data
  final scoreState = ref.watch(scoreViewerProvider(jobId));
  
  // If playback is not loaded or no IR v2 data, return null
  if (playbackState.isLoading || 
      playbackState.hasError || 
      scoreState.irV2Data == null) {
    return null;
  }
  
  final state = playbackState.value;
  if (state == null || !state.isPlaying) {
    return null;
  }
  
  // Get current playback position in seconds
  final currentSeconds = state.currentPosition.inMilliseconds / 1000.0;
  
  // Get IR v2 notes
  final irV2Data = scoreState.irV2Data!;
  final notes = irV2Data['notes'] as List<dynamic>?;
  if (notes == null || notes.isEmpty) {
    return null;
  }
  
  // Get current page number (0-indexed in Flutter, 1-indexed in IR)
  final currentPage = scoreState.currentPage;
  
  // Iterate through notes to find the one currently playing
  for (final note in notes) {
    if (note is! Map<String, dynamic>) continue;
    
    // Filter by page number
    final spatial = note['spatial'] as Map<String, dynamic>?;
    if (spatial != null) {
      final pageNum = spatial['page_number'] as int? ?? 1;
      if (pageNum != currentPage + 1) {
        continue; // Skip notes not on current page
      }
    }
    
    // Get timing information
    final time = note['time'] as Map<String, dynamic>?;
    final duration = note['duration'] as Map<String, dynamic>?;
    
    if (time == null || duration == null) continue;
    
    final onsetSeconds = (time['onset_seconds'] as num?)?.toDouble();
    final durationSeconds = (duration['duration_seconds'] as num?)?.toDouble();
    
    if (onsetSeconds == null || durationSeconds == null) continue;
    
    final endSeconds = onsetSeconds + durationSeconds;
    
    // Check if current time is within note's time range
    if (currentSeconds >= onsetSeconds && currentSeconds < endSeconds) {
      final noteId = note['note_id'] as String?;
      if (noteId != null) {
        return noteId;
      }
    }
  }
  
  // No active note found
  return null;
});

