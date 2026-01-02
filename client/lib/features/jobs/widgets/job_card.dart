import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/models/job.dart';
import '../../../data/models/artifact.dart';
import 'job_status_indicator.dart';
import '../providers/jobs_provider.dart';
import '../utils/artifact_downloader.dart';
import '../../../data/repositories/artifact_repository.dart';
import '../../../data/repositories/job_repository.dart';

class JobCard extends ConsumerWidget {
  final Job job;
  final VoidCallback? onTap;
  final VoidCallback? onDelete;
  
  const JobCard({
    super.key,
    required this.job,
    this.onTap,
    this.onDelete,
  });
  
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dateFormat = DateFormat('MMM d, y • h:mm a');
    
    return Dismissible(
      key: Key(job.id),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        decoration: BoxDecoration(
          color: Colors.red,
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Icon(Icons.delete, color: Colors.white),
      ),
      confirmDismiss: (direction) async {
        return await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Delete Job'),
            content: const Text('Are you sure you want to delete this job? This action cannot be undone.'),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () => Navigator.of(context).pop(true),
                style: FilledButton.styleFrom(backgroundColor: Colors.red),
                child: const Text('Delete'),
              ),
            ],
          ),
        ) ?? false;
      },
      onDismissed: (direction) {
        ref.read(jobsProvider.notifier).deleteJob(job.id);
        onDelete?.call();
      },
      child: Card(
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
                  PopupMenuButton<String>(
                    onSelected: (value) async {
                      final jobRepository = ref.read(jobRepositoryProvider);
                      final artifactRepository = ref.read(artifactRepositoryProvider);
                      final downloader = ArtifactDownloader(artifactRepository);
                      
                      switch (value) {
                        case 'download_musicxml':
                        case 'download_midi':
                        case 'download_svg':
                          try {
                            final artifacts = await jobRepository.getJobArtifacts(job.id);
                            final type = value.replaceFirst('download_', '');
                            final artifactType = type == 'musicxml' 
                                ? ArtifactType.musicxml
                                : type == 'midi'
                                    ? ArtifactType.midi
                                    : ArtifactType.svg;
                            final artifact = artifacts.firstWhere(
                              (a) => a.typeEnum == artifactType,
                              orElse: () => throw Exception('Artifact not found'),
                            );
                            await downloader.downloadAndShareArtifact(artifact);
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Download started')),
                              );
                            }
                          } catch (e) {
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text('Error: ${e.toString()}')),
                              );
                            }
                          }
                          break;
                        case 'reprocess':
                          try {
                            await jobRepository.reprocessJob(job.id);
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Job reprocessing started')),
                              );
                            }
                            ref.read(jobsProvider.notifier).refresh();
                          } catch (e) {
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text('Error: ${e.toString()}')),
                              );
                            }
                          }
                          break;
                        case 'delete':
                          final confirmed = await showDialog<bool>(
                            context: context,
                            builder: (context) => AlertDialog(
                              title: const Text('Delete Job'),
                              content: const Text('Are you sure you want to delete this job?'),
                              actions: [
                                TextButton(
                                  onPressed: () => Navigator.of(context).pop(false),
                                  child: const Text('Cancel'),
                                ),
                                FilledButton(
                                  onPressed: () => Navigator.of(context).pop(true),
                                  style: FilledButton.styleFrom(backgroundColor: Colors.red),
                                  child: const Text('Delete'),
                                ),
                              ],
                            ),
                          );
                          if (confirmed == true) {
                            ref.read(jobsProvider.notifier).deleteJob(job.id);
                            onDelete?.call();
                          }
                          break;
                      }
                    },
                    itemBuilder: (context) => [
                      if (job.isComplete) ...[
                        const PopupMenuItem(
                          value: 'download_musicxml',
                          child: Row(
                            children: [
                              Icon(Icons.music_note, size: 20),
                              SizedBox(width: 8),
                              Text('Download MusicXML'),
                            ],
                          ),
                        ),
                        const PopupMenuItem(
                          value: 'download_midi',
                          child: Row(
                            children: [
                              Icon(Icons.audiotrack, size: 20),
                              SizedBox(width: 8),
                              Text('Download MIDI'),
                            ],
                          ),
                        ),
                        const PopupMenuItem(
                          value: 'download_svg',
                          child: Row(
                            children: [
                              Icon(Icons.image, size: 20),
                              SizedBox(width: 8),
                              Text('Download SVG'),
                            ],
                          ),
                        ),
                        const PopupMenuDivider(),
                      ],
                      if (job.isFailed)
                        const PopupMenuItem(
                          value: 'reprocess',
                          child: Row(
                            children: [
                              Icon(Icons.refresh, size: 20),
                              SizedBox(width: 8),
                              Text('Reprocess'),
                            ],
                          ),
                        ),
                      const PopupMenuDivider(),
                      const PopupMenuItem(
                        value: 'delete',
                        child: Row(
                          children: [
                            Icon(Icons.delete, size: 20, color: Colors.red),
                            SizedBox(width: 8),
                            Text('Delete', style: TextStyle(color: Colors.red)),
                          ],
                        ),
                      ),
                    ],
                  ),
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
      ),
    );
  }
}

