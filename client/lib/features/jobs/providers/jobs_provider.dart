import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/models/job.dart';
import '../../../data/repositories/job_repository.dart';
import '../../../core/config/app_config.dart';

final jobsProvider = FutureProvider.autoDispose<List<Job>>((ref) async {
  final jobRepository = ref.watch(jobRepositoryProvider);
  return await jobRepository.listJobs();
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

