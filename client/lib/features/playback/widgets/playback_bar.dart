import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/playback_controller.dart';

class PlaybackBar extends ConsumerWidget {
  final String jobId;
  
  const PlaybackBar({
    super.key,
    required this.jobId,
  });
  
  String _formatDuration(Duration? duration) {
    if (duration == null) return '0:00';
    final minutes = duration.inMinutes;
    final seconds = duration.inSeconds % 60;
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }
  
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final playbackState = ref.watch(playbackControllerProvider(jobId));
    
    return playbackState.when(
      data: (state) {
        // Handle case where playback is not available (e.g., on web)
        if (state.error != null) {
          return Container(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
            ),
            child: SafeArea(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.music_off,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: 12),
                    Text(
                      state.error!,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        }
        
        final duration = state.duration ?? Duration.zero;
        final position = state.currentPosition;
        final maxDuration = duration.inMilliseconds > 0 
            ? duration.inMilliseconds 
            : 1;
        final currentValue = position.inMilliseconds.clamp(0, maxDuration);
        
        return Container(
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface.withOpacity(0.95),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.1),
                blurRadius: 8,
                offset: const Offset(0, -2),
              ),
            ],
          ),
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                children: [
                  // Play/Pause button
                  IconButton(
                    icon: Icon(
                      state.isPlaying ? Icons.pause : Icons.play_arrow,
                      size: 32,
                    ),
                    onPressed: () {
                      final controller = ref.read(
                        playbackControllerProvider(jobId).notifier,
                      );
                      if (state.isPlaying) {
                        controller.pause();
                      } else {
                        controller.play();
                      }
                    },
                    tooltip: state.isPlaying ? 'Pause' : 'Play',
                  ),
                  
                  const SizedBox(width: 8),
                  
                  // Time display
                  SizedBox(
                    width: 80,
                    child: Text(
                      _formatDuration(position),
                      style: Theme.of(context).textTheme.bodySmall,
                      textAlign: TextAlign.center,
                    ),
                  ),
                  
                  // Seek slider
                  Expanded(
                    child: Slider(
                      value: currentValue.toDouble(),
                      min: 0,
                      max: maxDuration.toDouble(),
                      onChanged: (value) {
                        final controller = ref.read(
                          playbackControllerProvider(jobId).notifier,
                        );
                        controller.seek(Duration(milliseconds: value.toInt()));
                      },
                    ),
                  ),
                  
                  const SizedBox(width: 8),
                  
                  // Total duration
                  SizedBox(
                    width: 80,
                    child: Text(
                      _formatDuration(duration),
                      style: Theme.of(context).textTheme.bodySmall,
                      textAlign: TextAlign.center,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
      loading: () => const SizedBox(
        height: 60,
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (error, stack) => Container(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const Icon(Icons.error_outline, color: Colors.red),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'Error loading playback: ${error.toString()}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Colors.red,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

