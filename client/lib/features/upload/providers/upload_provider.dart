import 'package:file_picker/file_picker.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/models/job.dart';
import '../../../data/repositories/job_repository.dart';

class UploadState {
  final bool isUploading;
  final double progress;
  final String statusMessage;
  final Job? job;
  final String? error;
  
  UploadState({
    this.isUploading = false,
    this.progress = 0.0,
    this.statusMessage = '',
    this.job,
    this.error,
  });
  
  UploadState copyWith({
    bool? isUploading,
    double? progress,
    String? statusMessage,
    Job? job,
    String? error,
  }) {
    return UploadState(
      isUploading: isUploading ?? this.isUploading,
      progress: progress ?? this.progress,
      statusMessage: statusMessage ?? this.statusMessage,
      job: job ?? this.job,
      error: error ?? this.error,
    );
  }
}

class UploadNotifier extends StateNotifier<UploadState> {
  final JobRepository _jobRepository;
  
  UploadNotifier(this._jobRepository) : super(UploadState());
  
  Future<void> uploadPDF(PlatformFile pdfFile) async {
    state = UploadState(
      isUploading: true, 
      progress: 0.0,
      statusMessage: 'Preparing upload...',
    );
    
    try {
      final job = await _jobRepository.uploadPDF(
        pdfFile,
        onProgress: (progress) {
          String message = 'Uploading...';
          if (progress >= 1.0) {
            message = 'Finalizing upload...';
          }
          state = state.copyWith(
            progress: progress,
            statusMessage: message,
          );
        },
      );
      
      state = state.copyWith(
        statusMessage: 'Upload complete! Redirecting...',
        job: job,
      );
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

