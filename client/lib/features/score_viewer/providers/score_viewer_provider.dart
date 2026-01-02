import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/models/artifact.dart';
import '../../../data/repositories/artifact_repository.dart';
import '../../../data/repositories/job_repository.dart';

// Conditional imports for platform-specific implementations
import 'score_viewer_platform_web.dart' if (dart.library.io) 'score_viewer_platform_io.dart' as platform;

class ScoreViewerState {
  final List<String> pngPages; // Base64 encoded PNG pages
  final String? musicXmlContent;
  final Map<String, dynamic>? irV2Data;
  final int currentPage;
  final double zoom;
  final bool isLoading;
  final String? error;
  final bool showFingering;
  final bool showConfidence;
  
  ScoreViewerState({
    this.pngPages = const [],
    this.musicXmlContent,
    this.irV2Data,
    this.currentPage = 0,
    this.zoom = 1.0,
    this.isLoading = false,
    this.error,
    this.showFingering = true,
    this.showConfidence = true,
  });
  
  ScoreViewerState copyWith({
    List<String>? pngPages,
    String? musicXmlContent,
    Map<String, dynamic>? irV2Data,
    int? currentPage,
    double? zoom,
    bool? isLoading,
    String? error,
    bool? showFingering,
    bool? showConfidence,
  }) {
    return ScoreViewerState(
      pngPages: pngPages ?? this.pngPages,
      musicXmlContent: musicXmlContent ?? this.musicXmlContent,
      irV2Data: irV2Data ?? this.irV2Data,
      currentPage: currentPage ?? this.currentPage,
      zoom: zoom ?? this.zoom,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      showFingering: showFingering ?? this.showFingering,
      showConfidence: showConfidence ?? this.showConfidence,
    );
  }
  
  bool get hasMultiplePages => pngPages.length > 1;
  int get totalPages => pngPages.length;
}

class ScoreViewerNotifier extends StateNotifier<ScoreViewerState> {
  final JobRepository _jobRepository;
  final ArtifactRepository _artifactRepository;
  String? _jobId;
  
  ScoreViewerNotifier(this._jobRepository, this._artifactRepository) 
      : super(ScoreViewerState());
  
  void setJobId(String jobId) {
    _jobId = jobId;
  }
  
  Future<void> loadScore(String jobId) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      // First, check if job is completed
      final job = await _jobRepository.getJob(jobId);
      if (!job.isComplete) {
        throw Exception('Job is not yet completed. Current status: ${job.statusDisplayName}');
      }
      
      // Get job artifacts
      final artifacts = await _jobRepository.getJobArtifacts(jobId);
      
      // Find PNG artifacts (preferred) or SVG artifacts (fallback)
      var pngArtifacts = artifacts
          .where((a) => a.typeEnum == ArtifactType.png)
          .toList()
        ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
      
      // If no PNG artifacts, try SVG and convert
      final svgArtifacts = artifacts
          .where((a) => a.typeEnum == ArtifactType.svg)
          .toList()
        ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
      
      final irV2Artifact = artifacts.firstWhere(
        (a) => a.typeEnum == ArtifactType.irV2,
        orElse: () => throw Exception('IR v2 artifact not found'),
      );
      
      // Find MusicXML artifact (optional)
      final musicXmlArtifact = artifacts
          .where((a) => a.typeEnum == ArtifactType.musicxml)
          .firstOrNull;
      
      if (pngArtifacts.isEmpty && svgArtifacts.isEmpty && musicXmlArtifact == null) {
        throw Exception('No PNG, SVG, or MusicXML artifacts found');
      }
      
      // Download PNG pages
      final pngPages = <String>[];
      
      if (pngArtifacts.isNotEmpty) {
        // Use PNG artifacts directly
        for (var artifact in pngArtifacts) {
          final pngContent = await platform.downloadArtifactAsString(
            _artifactRepository,
            artifact.id,
          );
          // PNG artifacts should already be base64 encoded
          pngPages.add(pngContent);
        }
      } else if (svgArtifacts.isNotEmpty) {
        // Fallback: Use SVG (though this path may have rendering issues)
        // For now, store them as empty strings and show a message
        state = state.copyWith(
          isLoading: false,
          error: 'PNG artifacts not found. Please re-render the score with PNG format.',
        );
        return;
      }

      // Download MusicXML content if available
      String? musicXmlContent;
      if (musicXmlArtifact != null) {
        musicXmlContent = await platform.downloadArtifactAsString(
          _artifactRepository,
          musicXmlArtifact.id,
        );
      }
      
      // Download and parse IR v2 (contains fingering data)
      final irV2Content = await platform.downloadArtifactAsString(
        _artifactRepository,
        irV2Artifact.id,
      );
      final irV2Data = json.decode(irV2Content) as Map<String, dynamic>;
      
      state = ScoreViewerState(
        pngPages: pngPages,
        musicXmlContent: musicXmlContent,
        irV2Data: irV2Data,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }
  
  void setPage(int page) {
    if (page >= 0 && page < state.totalPages) {
      state = state.copyWith(currentPage: page);
    }
  }
  
  void nextPage() {
    if (state.currentPage < state.totalPages - 1) {
      state = state.copyWith(currentPage: state.currentPage + 1);
    }
  }
  
  void previousPage() {
    if (state.currentPage > 0) {
      state = state.copyWith(currentPage: state.currentPage - 1);
    }
  }
  
  void setZoom(double zoom) {
    state = state.copyWith(zoom: zoom.clamp(0.5, 3.0));
  }
  
  void zoomIn() {
    setZoom(state.zoom + 0.25);
  }
  
  void zoomOut() {
    setZoom(state.zoom - 0.25);
  }
  
  void toggleFingering() {
    state = state.copyWith(showFingering: !state.showFingering);
  }
  
  void toggleConfidence() {
    state = state.copyWith(showConfidence: !state.showConfidence);
  }
  
  Future<void> updateFingeringOptimistic(
    String noteId,
    int finger,
    String hand,
  ) async {
    if (state.irV2Data == null) return;
    
    // Create a deep copy of IR v2 data
    final updatedIrV2 = Map<String, dynamic>.from(state.irV2Data!);
    final notes = List<Map<String, dynamic>>.from(
      (updatedIrV2['notes'] as List).map((n) => Map<String, dynamic>.from(n)),
    );
    
    // Find and update the note
    final noteIndex = notes.indexWhere((n) => n['note_id'] == noteId);
    if (noteIndex == -1) return;
    
    final note = Map<String, dynamic>.from(notes[noteIndex]);
    final existingFingering = note['fingering'] as Map<String, dynamic>?;
    
    // Update or create fingering annotation
    final updatedFingering = Map<String, dynamic>.from(existingFingering ?? {});
    updatedFingering['finger'] = finger;
    updatedFingering['hand'] = hand;
    if (existingFingering != null) {
      // Preserve other fingering fields
      updatedFingering.addAll(existingFingering);
      updatedFingering['finger'] = finger;
      updatedFingering['hand'] = hand;
    } else {
      // Create new fingering annotation
      updatedFingering['finger'] = finger;
      updatedFingering['hand'] = hand;
      updatedFingering['confidence'] = 1.0; // User override has full confidence
    }
    
    note['fingering'] = updatedFingering;
    notes[noteIndex] = note;
    updatedIrV2['notes'] = notes;
    
    // Optimistically update state
    state = state.copyWith(irV2Data: updatedIrV2);
    
    // Background: Save to backend (fire and forget for now)
    if (_jobId != null) {
      try {
        await _jobRepository.updateFingering(_jobId!, noteId, finger, hand);
      } catch (e) {
        // On error, log - in production you'd want to show a snackbar
        // ignore: avoid_print
        print('Error saving fingering: $e');
      }
    }
  }
}

final scoreViewerProvider = StateNotifierProvider.family<ScoreViewerNotifier, ScoreViewerState, String>(
  (ref, jobId) {
    final jobRepository = ref.watch(jobRepositoryProvider);
    final artifactRepository = ref.watch(artifactRepositoryProvider);
    final notifier = ScoreViewerNotifier(jobRepository, artifactRepository);
    notifier.setJobId(jobId);
    notifier.loadScore(jobId);
    return notifier;
  },
);
