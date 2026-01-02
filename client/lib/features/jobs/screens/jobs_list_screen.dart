import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/jobs_provider.dart';
import '../widgets/job_card.dart';

class JobsListScreen extends ConsumerWidget {
  const JobsListScreen({super.key});
  
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final jobsState = ref.watch(jobsProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Jobs'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => context.push('/upload'),
            tooltip: 'Upload PDF',
          ),
        ],
      ),
      body: Column(
        children: [
          // Filter chips
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  FilterChip(
                    label: const Text('All'),
                    selected: true,
                    onSelected: (selected) {
                      ref.read(jobsProvider.notifier).loadJobs();
                    },
                  ),
                  const SizedBox(width: 8),
                  FilterChip(
                    label: const Text('Completed'),
                    onSelected: (selected) {
                      if (selected) {
                        ref.read(jobsProvider.notifier).loadJobs(status: 'completed');
                      }
                    },
                  ),
                  const SizedBox(width: 8),
                  FilterChip(
                    label: const Text('Failed'),
                    onSelected: (selected) {
                      if (selected) {
                        ref.read(jobsProvider.notifier).loadJobs(status: 'failed');
                      }
                    },
                  ),
                  const SizedBox(width: 8),
                  FilterChip(
                    label: const Text('Processing'),
                    onSelected: (selected) {
                      if (selected) {
                        ref.read(jobsProvider.notifier).loadJobs(status: 'omr_processing');
                      }
                    },
                  ),
                ],
              ),
            ),
          ),
          
          // Jobs list
          Expanded(
            child: jobsState.isLoading && jobsState.items.isEmpty
                ? const Center(child: CircularProgressIndicator())
                : jobsState.error != null && jobsState.items.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.error_outline,
                              size: 64,
                              color: Colors.red[400],
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'Error loading jobs',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              jobsState.error!,
                              style: Theme.of(context).textTheme.bodyMedium,
                              textAlign: TextAlign.center,
                            ),
                            const SizedBox(height: 24),
                            ElevatedButton.icon(
                              onPressed: () {
                                ref.read(jobsProvider.notifier).refresh();
                              },
                              icon: const Icon(Icons.refresh),
                              label: const Text('Retry'),
                            ),
                          ],
                        ),
                      )
                    : jobsState.items.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  Icons.music_note_outlined,
                                  size: 64,
                                  color: Colors.grey[400],
                                ),
                                const SizedBox(height: 16),
                                Text(
                                  'No jobs yet',
                                  style: Theme.of(context).textTheme.titleLarge,
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  'Upload a PDF to get started',
                                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: Colors.grey[600],
                                  ),
                                ),
                                const SizedBox(height: 24),
                                FilledButton.icon(
                                  onPressed: () => context.push('/upload'),
                                  icon: const Icon(Icons.upload),
                                  label: const Text('Upload PDF'),
                                ),
                              ],
                            ),
                          )
                        : RefreshIndicator(
                            onRefresh: () async {
                              ref.read(jobsProvider.notifier).refresh();
                            },
                            child: ListView.builder(
                              padding: const EdgeInsets.all(16),
                              itemCount: jobsState.items.length + (jobsState.hasMore ? 1 : 0),
                              itemBuilder: (context, index) {
                                if (index == jobsState.items.length) {
                                  // Load more button
                                  return Padding(
                                    padding: const EdgeInsets.all(16),
                                    child: Center(
                                      child: jobsState.isLoadingMore
                                          ? const CircularProgressIndicator()
                                          : TextButton(
                                              onPressed: () {
                                                ref.read(jobsProvider.notifier).loadMore();
                                              },
                                              child: const Text('Load More'),
                                            ),
                                    ),
                                  );
                                }
                                
                                final job = jobsState.items[index];
                                return Padding(
                                  padding: const EdgeInsets.only(bottom: 12),
                                  child: JobCard(
                                    job: job,
                                    onTap: () => context.push('/jobs/${job.id}'),
                                  ),
                                );
                              },
                            ),
                          ),
          ),
        ],
      ),
    );
  }
}

