import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../../data/models/job.dart';
import 'job_status_indicator.dart';

class JobCard extends StatelessWidget {
  final Job job;
  final VoidCallback? onTap;
  
  const JobCard({
    super.key,
    required this.job,
    this.onTap,
  });
  
  @override
  Widget build(BuildContext context) {
    final dateFormat = DateFormat('MMM d, y • h:mm a');
    
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Job ${job.id.substring(0, 8)}...',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          dateFormat.format(job.createdAt),
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey[600],
                          ),
                        ),
                      ],
                    ),
                  ),
                  JobStatusIndicator(status: job.status),
                ],
              ),
              if (job.isProcessing) ...[
                const SizedBox(height: 12),
                LinearProgressIndicator(
                  value: job.progress,
                  backgroundColor: Colors.grey[200],
                  minHeight: 4,
                ),
                const SizedBox(height: 4),
                Text(
                  '${(job.progress * 100).toInt()}% complete',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
              if (job.isFailed && job.errorMessage != null) ...[
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.red[50],
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.error_outline, size: 16, color: Colors.red[900]),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          job.errorMessage!,
                          style: TextStyle(
                            color: Colors.red[900],
                            fontSize: 12,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

