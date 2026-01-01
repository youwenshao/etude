import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../providers/jobs_provider.dart';
import '../widgets/job_status_indicator.dart';
import '../../../data/models/job.dart';

class JobDetailScreen extends ConsumerWidget {
  final String jobId;
  
  const JobDetailScreen({
    super.key,
    required this.jobId,
  });
  
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final jobAsync = ref.watch(jobPollingProvider(jobId));
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Job Details'),
      ),
      body: jobAsync.when(
        data: (job) => _buildJobDetail(context, job),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
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
                'Error loading job',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                error.toString(),
                style: Theme.of(context).textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: () {
                  ref.invalidate(jobPollingProvider(jobId));
                },
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildJobDetail(BuildContext context, Job job) {
    final dateFormat = DateFormat('MMM d, y • h:mm a');
    
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 600),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Status card
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: Column(
                    children: [
                      JobStatusIndicator(status: job.status, size: 20),
                      const SizedBox(height: 16),
                      Text(
                        job.statusDisplayName,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 24),
                      LinearProgressIndicator(
                        value: job.progress,
                        backgroundColor: Colors.grey[200],
                        minHeight: 8,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '${(job.progress * 100).toInt()}% complete',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ),
              
              const SizedBox(height: 24),
              
              // Error message if failed
              if (job.isFailed && job.errorMessage != null)
                Container(
                  padding: const EdgeInsets.all(16),
                  margin: const EdgeInsets.only(bottom: 24),
                  decoration: BoxDecoration(
                    color: Colors.red[50],
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red[200]!),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.error_outline, color: Colors.red[900]),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          job.errorMessage!,
                          style: TextStyle(color: Colors.red[900]),
                        ),
                      ),
                    ],
                  ),
                ),
              
              // View score button when complete
              if (job.isComplete) ...[
                FilledButton.icon(
                  onPressed: () {
                    context.push('/score/${job.id}');
                  },
                  icon: const Icon(Icons.music_note),
                  label: const Text('View Score with Fingering'),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.all(20),
                  ),
                ),
                const SizedBox(height: 24),
              ],
              
              // Job info
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Job Information',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const Divider(),
                      _buildInfoRow('Job ID', job.id),
                      _buildInfoRow('Status', job.statusDisplayName),
                      if (job.stage != null)
                        _buildInfoRow('Stage', job.stage!),
                      _buildInfoRow('Created', dateFormat.format(job.createdAt)),
                      _buildInfoRow('Updated', dateFormat.format(job.updatedAt)),
                      if (job.completedAt != null)
                        _buildInfoRow('Completed', dateFormat.format(job.completedAt!)),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
          Expanded(
            child: Text(value),
          ),
        ],
      ),
    );
  }
}

