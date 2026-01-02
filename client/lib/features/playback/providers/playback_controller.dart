import 'dart:async';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:just_audio/just_audio.dart';
import 'package:path_provider/path_provider.dart';
import '../../../data/models/artifact.dart';
import '../../../data/repositories/job_repository.dart';
import '../../../data/repositories/artifact_repository.dart';

class PlaybackState {
  final bool isPlaying;
  final Duration currentPosition;
  final Duration? duration;
  final bool isLoading;
  final String? error;
  final String? midiUrl;
  
  PlaybackState({
    this.isPlaying = false,
    this.currentPosition = Duration.zero,
    this.duration,
    this.isLoading = false,
    this.error,
    this.midiUrl,
  });
  
  PlaybackState copyWith({
    bool? isPlaying,
    Duration? currentPosition,
    Duration? duration,
    bool? isLoading,
    String? error,
    String? midiUrl,
  }) {
    return PlaybackState(
      isPlaying: isPlaying ?? this.isPlaying,
      currentPosition: currentPosition ?? this.currentPosition,
      duration: duration ?? this.duration,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      midiUrl: midiUrl ?? this.midiUrl,
    );
  }
}

class PlaybackController extends StateNotifier<AsyncValue<PlaybackState>> {
  final JobRepository _jobRepository;
  final ArtifactRepository _artifactRepository;
  AudioPlayer? _audioPlayer;
  StreamSubscription<Duration>? _positionSubscription;
  StreamSubscription<Duration?>? _durationSubscription;
  StreamSubscription<PlayerState>? _playerStateSubscription;
  
  PlaybackController(this._jobRepository, this._artifactRepository) : super(const AsyncValue.loading());
  
  Future<void> loadMidi(String jobId) async {
    // Wrap entire function in try-catch to handle any platform-specific errors
    try {
      state = const AsyncValue.loading();
      
      // On web, MIDI playback is not supported by just_audio
      // Return early with a disabled state instead of attempting to load
      if (kIsWeb) {
        state = AsyncValue.data(
          PlaybackState(
            error: 'MIDI playback is not available on web. Use the mobile app for audio playback.',
          ),
        );
        return;
      }
      
      // Get job artifacts
      final artifacts = await _jobRepository.getJobArtifacts(jobId);
      
      // Find MIDI artifact - handle missing artifact gracefully
      Artifact? midiArtifact;
      try {
        midiArtifact = artifacts.firstWhere(
          (a) => a.typeEnum == ArtifactType.midi,
        );
      } catch (e) {
        // No MIDI artifact found
        state = AsyncValue.data(
          PlaybackState(
            error: 'MIDI artifact not found. The score may still be processing.',
          ),
        );
        return;
      }
      
      if (midiArtifact == null) {
        state = AsyncValue.data(
          PlaybackState(
            error: 'MIDI artifact not found. The score may still be processing.',
          ),
        );
        return;
      }
      
      // Initialize audio player
      _audioPlayer?.dispose();
      _audioPlayer = AudioPlayer();
      
      // Cancel any existing subscriptions before loading
      _positionSubscription?.cancel();
      _positionSubscription = null;
      _durationSubscription?.cancel();
      _durationSubscription = null;
      _playerStateSubscription?.cancel();
      _playerStateSubscription = null;
      
      // For mobile/desktop: Download to file and use file path
      final tempDir = await getTemporaryDirectory();
      final midiPath = '${tempDir.path}/midi_${midiArtifact.id}.mid';
      try {
        await _artifactRepository.downloadArtifact(midiArtifact.id, midiPath);
      } catch (e) {
        // Clean up audio player if download fails
        _audioPlayer?.dispose();
        _audioPlayer = null;
        state = AsyncValue.data(
          PlaybackState(
            error: 'Failed to download MIDI file: ${e.toString()}',
          ),
        );
        return;
      }
      
      final audioSource = midiPath;
      
      // Load from file path on mobile/desktop
      try {
        await _audioPlayer!.setFilePath(audioSource);
      } catch (e) {
        // Clean up on load failure
        _audioPlayer?.dispose();
        _audioPlayer = null;
        state = AsyncValue.data(
          PlaybackState(
            error: 'Failed to load audio file: ${e.toString()}',
          ),
        );
        return;
      }
      
      // Only set up stream listeners AFTER successfully loading audio
      // Wrap in try-catch to handle any stream setup errors
      try {
        _positionSubscription = _audioPlayer!.positionStream.listen(
          (position) {
            // Safely update state - use maybeWhen to avoid accessing .value directly
            try {
              state = state.maybeWhen(
                data: (currentState) => AsyncValue.data(
                  currentState.copyWith(currentPosition: position),
                ),
                orElse: () => state, // Keep current state if in error/loading
              );
            } catch (e) {
              // Silently ignore state update errors to prevent crashes
            }
          },
          onError: (error) {
            // Ignore errors from stream - don't update state
          },
          cancelOnError: false,
        );
        
        _durationSubscription = _audioPlayer!.durationStream.listen(
          (duration) {
            // Safely update state - use maybeWhen to avoid accessing .value directly
            try {
              state = state.maybeWhen(
                data: (currentState) => AsyncValue.data(
                  currentState.copyWith(duration: duration),
                ),
                orElse: () => state, // Keep current state if in error/loading
              );
            } catch (e) {
              // Silently ignore state update errors to prevent crashes
            }
          },
          onError: (error) {
            // Ignore errors from stream - don't update state
          },
          cancelOnError: false,
        );
        
        _playerStateSubscription = _audioPlayer!.playerStateStream.listen(
          (playerState) {
            // Safely update state - use maybeWhen to avoid accessing .value directly
            try {
              state = state.maybeWhen(
                data: (currentState) => AsyncValue.data(
                  currentState.copyWith(
                    isPlaying: playerState.playing,
                  ),
                ),
                orElse: () => state, // Keep current state if in error/loading
              );
            } catch (e) {
              // Silently ignore state update errors to prevent crashes
            }
          },
          onError: (error) {
            // Ignore errors from stream - don't update state
          },
          cancelOnError: false,
        );
      } catch (e) {
        // If stream setup fails, clean up and show error
        _positionSubscription?.cancel();
        _positionSubscription = null;
        _durationSubscription?.cancel();
        _durationSubscription = null;
        _playerStateSubscription?.cancel();
        _playerStateSubscription = null;
        _audioPlayer?.dispose();
        _audioPlayer = null;
        state = AsyncValue.data(
          PlaybackState(
            error: 'Failed to set up audio playback: ${e.toString()}',
          ),
        );
        return;
      }
      
      state = AsyncValue.data(
        PlaybackState(
          midiUrl: audioSource,
          duration: _audioPlayer!.duration,
        ),
      );
    } catch (e, stackTrace) {
      // Clean up on failure
      _positionSubscription?.cancel();
      _positionSubscription = null;
      _durationSubscription?.cancel();
      _durationSubscription = null;
      _playerStateSubscription?.cancel();
      _playerStateSubscription = null;
      _audioPlayer?.dispose();
      _audioPlayer = null;
      
      // Provide user-friendly error message instead of raw exception
      final errorMessage = e.toString();
      state = AsyncValue.data(
        PlaybackState(
          error: 'Playback unavailable: $errorMessage',
        ),
      );
    }
  }
  
  Future<void> play() async {
    try {
      await _audioPlayer?.play();
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
    }
  }
  
  Future<void> pause() async {
    try {
      await _audioPlayer?.pause();
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
    }
  }
  
  Future<void> stop() async {
    try {
      await _audioPlayer?.stop();
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
    }
  }
  
  Future<void> seek(Duration position) async {
    try {
      await _audioPlayer?.seek(position);
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
    }
  }
  
  void _dispose() {
    _positionSubscription?.cancel();
    _durationSubscription?.cancel();
    _playerStateSubscription?.cancel();
    _audioPlayer?.dispose();
    _audioPlayer = null;
  }
}

final playbackControllerProvider = StateNotifierProvider.family<PlaybackController, AsyncValue<PlaybackState>, String>(
  (ref, jobId) {
    final jobRepository = ref.watch(jobRepositoryProvider);
    final artifactRepository = ref.watch(artifactRepositoryProvider);
    final controller = PlaybackController(jobRepository, artifactRepository);
    ref.onDispose(() {
      controller._dispose();
    });
    return controller;
  },
);

