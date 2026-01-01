import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/models/job.dart';
import '../../../data/repositories/job_repository.dart';

class UploadState {
  final bool isUploading;
  final double progress;
  final Job? job;
  final String? error;
  
  UploadState({
    this.isUploading = false,
    this.progress = 0.0,
    this.job,
    this.error,
  });
  
  UploadState copyWith({
    bool? isUploading,
    double? progress,
    Job? job,
    String? error,
  }) {
    return UploadState(
      isUploading: isUploading ?? this.isUploading,
      progress: progress ?? this.progress,
      job: job ?? this.job,
      error: error ?? this.error,
    );
  }
}

class UploadNotifier extends StateNotifier<UploadState> {
  final JobRepository _jobRepository;
  
  UploadNotifier(this._jobRepository) : super(UploadState());
  
  Future<void> uploadPDF(File pdfFile) async {
    state = UploadState(isUploading: true, progress: 0.0);
    
    try {
      final job = await _jobRepository.uploadPDF(
        pdfFile,
        onProgress: (progress) {
          state = state.copyWith(progress: progress);
        },
      );
      
      state = UploadState(job: job);
    } catch (e) {
      state = UploadState(error: e.toString());
    }
  }
  
  void reset() {
    state = UploadState();
  }
}

final uploadProvider = StateNotifierProvider<UploadNotifier, UploadState>((ref) {
  final jobRepository = ref.watch(jobRepositoryProvider);
  return UploadNotifier(jobRepository);
});

