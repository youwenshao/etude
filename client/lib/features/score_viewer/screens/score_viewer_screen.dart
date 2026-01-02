import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/score_viewer_provider.dart';
import '../widgets/score_png_viewer.dart';
import '../widgets/confidence_legend.dart';
import '../../playback/widgets/playback_bar.dart';
import '../../playback/providers/playback_controller.dart';
import '../../editor/providers/edit_mode_provider.dart';

class ScoreViewerScreen extends ConsumerStatefulWidget {
  final String jobId;
  
  const ScoreViewerScreen({
    super.key,
    required this.jobId,
  });
  
  @override
  ConsumerState<ScoreViewerScreen> createState() => _ScoreViewerScreenState();
}

class _ScoreViewerScreenState extends ConsumerState<ScoreViewerScreen> {
  @override
  void initState() {
    super.initState();
    // Initialize playback controller when screen loads
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final controller = ref.read(playbackControllerProvider(widget.jobId).notifier);
      controller.loadMidi(widget.jobId);
    });
  }
  
  // Note: Playback controller cleanup is handled by Riverpod's ref.onDispose
  // No manual cleanup needed here
  
  @override
  Widget build(BuildContext context) {
    final scoreState = ref.watch(scoreViewerProvider(widget.jobId));
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Score with Fingering'),
        actions: [
          // Edit mode toggle
          Consumer(
            builder: (context, ref, child) {
              final isEditMode = ref.watch(editModeProvider);
              return IconButton(
                icon: Icon(
                  isEditMode ? Icons.edit : Icons.edit_outlined,
                  color: isEditMode ? Theme.of(context).colorScheme.primary : null,
                ),
                onPressed: () {
                  ref.read(editModeProvider.notifier).state = !isEditMode;
                },
                tooltip: isEditMode ? 'Exit Edit Mode' : 'Edit Mode',
              );
            },
          ),
          // Toggle fingering visibility
          IconButton(
            icon: Icon(
              scoreState.showFingering
                  ? Icons.music_note
                  : Icons.music_off,
            ),
            onPressed: () {
              ref.read(scoreViewerProvider(widget.jobId).notifier).toggleFingering();
            },
            tooltip: 'Toggle Fingering',
          ),
          
          // Toggle confidence visualization
          IconButton(
            icon: Icon(
              scoreState.showConfidence
                  ? Icons.visibility
                  : Icons.visibility_off,
            ),
            onPressed: () {
              ref.read(scoreViewerProvider(widget.jobId).notifier).toggleConfidence();
            },
            tooltip: 'Toggle Confidence',
          ),
          
          // Zoom controls
          PopupMenuButton<String>(
            icon: const Icon(Icons.zoom_in),
            onSelected: (value) {
              final notifier = ref.read(scoreViewerProvider(widget.jobId).notifier);
              switch (value) {
                case 'zoom_in':
                  notifier.zoomIn();
                  break;
                case 'zoom_out':
                  notifier.zoomOut();
                  break;
                case 'reset':
                  notifier.setZoom(1.0);
                  break;
              }
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'zoom_in',
                child: Row(
                  children: [
                    Icon(Icons.add),
                    SizedBox(width: 8),
                    Text('Zoom In'),
                  ],
                ),
              ),
              const PopupMenuItem(
                value: 'zoom_out',
                child: Row(
                  children: [
                    Icon(Icons.remove),
                    SizedBox(width: 8),
                    Text('Zoom Out'),
                  ],
                ),
              ),
              const PopupMenuItem(
                value: 'reset',
                child: Row(
                  children: [
                    Icon(Icons.refresh),
                    SizedBox(width: 8),
                    Text('Reset Zoom'),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
      body: scoreState.isLoading
          ? const Center(child: CircularProgressIndicator())
          : scoreState.error != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.error_outline,
                        size: 64,
                        color: Colors.red[300],
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Error loading score',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        scoreState.error!,
                        style: Theme.of(context).textTheme.bodyMedium,
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                )
              : scoreState.pngPages.isEmpty
                  ? const Center(child: Text('No score available'))
                  : Row(
                      children: [
                        // Main score viewer
                        Expanded(
                          child: Column(
                            children: [
                              // Score display
                              Expanded(
                                child: ScorePngViewer(
                                  pngBase64: scoreState.pngPages[scoreState.currentPage],
                                  zoom: scoreState.zoom,
                                  irV2Data: scoreState.irV2Data,
                                  pageNumber: scoreState.currentPage,
                                  showFingering: scoreState.showFingering,
                                  showConfidence: scoreState.showConfidence,
                                  jobId: widget.jobId,
                                ),
                              ),
                              
                              // Page navigation
                              if (scoreState.hasMultiplePages)
                                Container(
                                  padding: const EdgeInsets.all(16),
                                  decoration: BoxDecoration(
                                    color: Colors.white,
                                    boxShadow: [
                                      BoxShadow(
                                        color: Colors.black.withOpacity(0.1),
                                        blurRadius: 4,
                                        offset: const Offset(0, -2),
                                      ),
                                    ],
                                  ),
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      IconButton(
                                        icon: const Icon(Icons.chevron_left),
                                        onPressed: scoreState.currentPage > 0
                                            ? () {
                                                final notifier = ref.read(scoreViewerProvider(widget.jobId).notifier);
                                                // Pause playback when changing pages
                                                ref.read(playbackControllerProvider(widget.jobId).notifier).pause();
                                                notifier.previousPage();
                                              }
                                            : null,
                                      ),
                                      const SizedBox(width: 16),
                                      Text(
                                        'Page ${scoreState.currentPage + 1} of ${scoreState.totalPages}',
                                        style: Theme.of(context).textTheme.titleMedium,
                                      ),
                                      const SizedBox(width: 16),
                                      IconButton(
                                        icon: const Icon(Icons.chevron_right),
                                        onPressed: scoreState.currentPage < scoreState.totalPages - 1
                                            ? () {
                                                final notifier = ref.read(scoreViewerProvider(widget.jobId).notifier);
                                                // Pause playback when changing pages
                                                ref.read(playbackControllerProvider(widget.jobId).notifier).pause();
                                                notifier.nextPage();
                                              }
                                            : null,
                                      ),
                                    ],
                                  ),
                                ),
                            ],
                          ),
                        ),
                        
                        // Sidebar with legend and info
                        if (MediaQuery.of(context).size.width > 800)
                          Container(
                            width: 300,
                            decoration: BoxDecoration(
                              color: Colors.grey[50],
                              border: Border(
                                left: BorderSide(color: Colors.grey[300]!),
                              ),
                            ),
                            child: SingleChildScrollView(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  // Confidence legend
                                  const ConfidenceLegend(),
                                  
                                  const SizedBox(height: 16),
                                  
                                  // Instructions
                                  Card(
                                    child: Padding(
                                      padding: const EdgeInsets.all(16),
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            'How to Use',
                                            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                          const SizedBox(height: 12),
                                          _buildInstruction(
                                            Icons.touch_app,
                                            'Tap fingering numbers to see alternatives',
                                          ),
                                          const SizedBox(height: 8),
                                          _buildInstruction(
                                            Icons.zoom_in,
                                            'Pinch or use zoom controls to adjust view',
                                          ),
                                          const SizedBox(height: 8),
                                          _buildInstruction(
                                            Icons.pan_tool,
                                            'Drag to pan around the score',
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                  
                                  const SizedBox(height: 16),
                                  
                                  // Statistics
                                  if (scoreState.irV2Data != null)
                                    _buildStatistics(context, scoreState.irV2Data!),
                                ],
                              ),
                            ),
                          ),
                      ],
                    ),
      bottomNavigationBar: PlaybackBar(jobId: widget.jobId),
    );
  }
  
  Widget _buildInstruction(IconData icon, String text) {
    return Row(
      children: [
        Icon(icon, size: 16, color: Colors.grey[600]),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: TextStyle(fontSize: 12, color: Colors.grey[700]),
          ),
        ),
      ],
    );
  }
  
  Widget _buildStatistics(BuildContext context, Map<String, dynamic> irV2Data) {
    final metadata = irV2Data['fingering_metadata'] as Map<String, dynamic>?;
    if (metadata == null) return const SizedBox.shrink();
    
    final notesAnnotated = metadata['notes_annotated'] as int? ?? 0;
    final totalNotes = metadata['total_notes'] as int? ?? 0;
    final coverage = metadata['coverage'] as double? ?? 0.0;
    
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Fingering Statistics',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            _buildStatRow('Total Notes', totalNotes.toString()),
            const SizedBox(height: 8),
            _buildStatRow('Fingered Notes', notesAnnotated.toString()),
            const SizedBox(height: 8),
            _buildStatRow('Coverage', '${(coverage * 100).toStringAsFixed(1)}%'),
          ],
        ),
      ),
    );
  }
  
  Widget _buildStatRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 12),
        ),
        Text(
          value,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}

