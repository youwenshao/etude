import 'dart:convert';
import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import '../../../data/models/artifact.dart';
import '../../../data/repositories/artifact_repository.dart';
import '../../../data/repositories/job_repository.dart';

class ScoreViewerState {
  final List<String> svgPages;
  final Map<String, dynamic>? irV2Data;
  final int currentPage;
  final double zoom;
  final bool isLoading;
  final String? error;
  final bool showFingering;
  final bool showConfidence;
  
  ScoreViewerState({
    this.svgPages = const [],
    this.irV2Data,
    this.currentPage = 0,
    this.zoom = 1.0,
    this.isLoading = false,
    this.error,
    this.showFingering = true,
    this.showConfidence = true,
  });
  
  ScoreViewerState copyWith({
    List<String>? svgPages,
    Map<String, dynamic>? irV2Data,
    int? currentPage,
    double? zoom,
    bool? isLoading,
    String? error,
    bool? showFingering,
    bool? showConfidence,
  }) {
    return ScoreViewerState(
      svgPages: svgPages ?? this.svgPages,
      irV2Data: irV2Data ?? this.irV2Data,
      currentPage: currentPage ?? this.currentPage,
      zoom: zoom ?? this.zoom,
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      showFingering: showFingering ?? this.showFingering,
      showConfidence: showConfidence ?? this.showConfidence,
    );
  }
  
  bool get hasMultiplePages => svgPages.length > 1;
  int get totalPages => svgPages.length;
}

class ScoreViewerNotifier extends StateNotifier<ScoreViewerState> {
  final JobRepository _jobRepository;
  final ArtifactRepository _artifactRepository;
  
  ScoreViewerNotifier(this._jobRepository, this._artifactRepository) 
      : super(ScoreViewerState());
  
  Future<void> loadScore(String jobId) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      // Get job artifacts
      final artifacts = await _jobRepository.getJobArtifacts(jobId);
      
      // Find SVG and IR v2 artifacts
      final svgArtifacts = artifacts
          .where((a) => a.typeEnum == ArtifactType.svg)
          .toList()
        ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
      
      final irV2Artifact = artifacts.firstWhere(
        (a) => a.typeEnum == ArtifactType.irV2,
        orElse: () => throw Exception('IR v2 artifact not found'),
      );
      
      if (svgArtifacts.isEmpty) {
        throw Exception('No SVG artifacts found');
      }
      
      // Download SVG pages
      final tempDir = await getTemporaryDirectory();
      final svgPages = <String>[];
      
      for (var i = 0; i < svgArtifacts.length; i++) {
        final artifact = svgArtifacts[i];
        final savePath = '${tempDir.path}/score_page_$i.svg';
        await _artifactRepository.downloadArtifact(artifact.id, savePath);
        
        // Read SVG content
        final svgContent = await File(savePath).readAsString();
        svgPages.add(svgContent);
      }
      
      // Download and parse IR v2 (contains fingering data)
      final irV2Path = '${tempDir.path}/ir_v2.json';
      await _artifactRepository.downloadArtifact(irV2Artifact.id, irV2Path);
      final irV2Content = await File(irV2Path).readAsString();
      
      // Parse IR v2 JSON
      final irV2Data = json.decode(irV2Content) as Map<String, dynamic>;
      
      state = ScoreViewerState(
        svgPages: svgPages,
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
}

final scoreViewerProvider = StateNotifierProvider.family<ScoreViewerNotifier, ScoreViewerState, String>(
  (ref, jobId) {
    final jobRepository = ref.watch(jobRepositoryProvider);
    final artifactRepository = ref.watch(artifactRepositoryProvider);
    final notifier = ScoreViewerNotifier(jobRepository, artifactRepository);
    notifier.loadScore(jobId);
    return notifier;
  },
);

