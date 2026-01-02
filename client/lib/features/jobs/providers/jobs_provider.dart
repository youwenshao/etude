import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/models/job.dart';
import '../../../data/repositories/job_repository.dart';
import '../../../core/config/app_config.dart';

class JobsState {
  final List<Job> items;
  final int total;
  final int page;
  final int pageSize;
  final bool isLoading;
  final bool isLoadingMore;
  final String? error;
  
  JobsState({
    this.items = const [],
    this.total = 0,
    this.page = 0,
    this.pageSize = 20,
    this.isLoading = false,
    this.isLoadingMore = false,
    this.error,
  });
  
  bool get hasMore => (page + 1) * pageSize < total;
  
  JobsState copyWith({
    List<Job>? items,
    int? total,
    int? page,
    int? pageSize,
    bool? isLoading,
    bool? isLoadingMore,
    String? error,
  }) {
    return JobsState(
      items: items ?? this.items,
      total: total ?? this.total,
      page: page ?? this.page,
      pageSize: pageSize ?? this.pageSize,
      isLoading: isLoading ?? this.isLoading,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      error: error,
    );
  }
}

class JobsNotifier extends StateNotifier<JobsState> {
  final JobRepository _jobRepository;
  
  JobsNotifier(this._jobRepository) : super(JobsState());
  
  Future<void> loadJobs({int page = 0, int limit = 20, String? status}) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final jobs = await _jobRepository.listJobs(
        status: status,
        limit: limit,
        offset: page * limit,
      );
      
      // Get total from repository response (if available)
      // For now, estimate based on items returned
      final estimatedTotal = page == 0 
          ? (jobs.length >= limit ? limit * 2 : jobs.length)
          : state.total;
      
      state = state.copyWith(
        items: page == 0 ? jobs : [...state.items, ...jobs],
        total: estimatedTotal,
        page: page,
        pageSize: limit,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }
  
  Future<void> loadMore() async {
    if (state.isLoadingMore || !state.hasMore) return;
    
    state = state.copyWith(isLoadingMore: true);
    await loadJobs(
      page: state.page + 1,
      limit: state.pageSize,
    );
    state = state.copyWith(isLoadingMore: false);
  }
  
  Future<void> refresh() async {
    await loadJobs(page: 0, limit: state.pageSize);
  }
  
  Future<void> deleteJob(String jobId) async {
    try {
      await _jobRepository.deleteJob(jobId);
      // Optimistically remove from list
      state = state.copyWith(
        items: state.items.where((j) => j.id != jobId).toList(),
        total: state.total - 1,
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }
}

final jobsProvider = StateNotifierProvider<JobsNotifier, JobsState>((ref) {
  final jobRepository = ref.watch(jobRepositoryProvider);
  final notifier = JobsNotifier(jobRepository);
  notifier.loadJobs();
  return notifier;
});

final jobDetailProvider = FutureProvider.family.autoDispose<Job, String>(
  (ref, jobId) async {
    final jobRepository = ref.watch(jobRepositoryProvider);
    return await jobRepository.getJob(jobId);
  },
);

// Job polling provider
final jobPollingProvider = StreamProvider.family.autoDispose<Job, String>(
  (ref, jobId) async* {
    final jobRepository = ref.watch(jobRepositoryProvider);
    
    while (true) {
      try {
        final job = await jobRepository.getJob(jobId);
        yield job;
        
        // Stop polling if job is complete or failed
        if (job.isComplete || job.isFailed) {
          break;
        }
        
        // Poll every 2 seconds
        await Future.delayed(AppConfig.jobPollInterval);
      } catch (e) {
        // On error, yield the error and stop polling
        rethrow;
      }
    }
  },
);

