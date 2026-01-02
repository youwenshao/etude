import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/fingering_edit_controller.dart';
import '../../../features/score_viewer/providers/score_viewer_provider.dart';

class FingeringEditModal extends ConsumerWidget {
  final String jobId;
  final String noteId;
  final Map<String, dynamic>? currentFingering;
  final List<dynamic>? alternatives;
  
  const FingeringEditModal({
    super.key,
    required this.jobId,
    required this.noteId,
    this.currentFingering,
    this.alternatives,
  });
  
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final editController = ref.watch(fingeringEditControllerProvider.notifier);
    String selectedHand = currentFingering?['hand'] as String? ?? 'right';
    int selectedFinger = currentFingering?['finger'] as int? ?? 0;
    
    return StatefulBuilder(
      builder: (context, setState) {
        return Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Edit Fingering',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              
              const SizedBox(height: 24),
              
              // Current fingering display
              if (currentFingering != null)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Current Fingering',
                          style: Theme.of(context).textTheme.titleSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Finger: ${currentFingering!['finger']}, Hand: ${currentFingering!['hand']}',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                ),
              
              const SizedBox(height: 16),
              
              // Hand selection
              Text(
                'Hand',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: 8),
              SegmentedButton<String>(
                segments: const [
                  ButtonSegment(value: 'left', label: Text('Left')),
                  ButtonSegment(value: 'right', label: Text('Right')),
                ],
                selected: {selectedHand},
                onSelectionChanged: (Set<String> newSelection) {
                  setState(() {
                    selectedHand = newSelection.first;
                  });
                },
              ),
              
              const SizedBox(height: 24),
              
              // Finger selection
              Text(
                'Finger',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: List.generate(6, (index) {
                  final finger = index;
                  final isSelected = selectedFinger == finger;
                  return ChoiceChip(
                    label: Text(finger == 0 ? 'None' : finger.toString()),
                    selected: isSelected,
                    onSelected: (selected) {
                      setState(() {
                        selectedFinger = finger;
                      });
                    },
                  );
                }),
              ),
              
              // Alternative fingerings
              if (alternatives != null && alternatives!.isNotEmpty) ...[
                const SizedBox(height: 24),
                Text(
                  'Alternatives',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: alternatives!.map((alt) {
                    final altFinger = alt['finger'] as int? ?? 0;
                    final altConfidence = alt['confidence'] as double? ?? 0.0;
                    return ActionChip(
                      label: Text('${altFinger} (${(altConfidence * 100).toInt()}%)'),
                      onPressed: () {
                        setState(() {
                          selectedFinger = altFinger;
                        });
                      },
                    );
                  }).toList(),
                ),
              ],
              
              const SizedBox(height: 24),
              
              // Action buttons
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    onPressed: () {
                      // Update in edit controller
                      editController.updateFingering(
                        noteId,
                        selectedFinger,
                        selectedHand,
                      );
                      // Optimistically update score viewer
                      ref.read(scoreViewerProvider(jobId).notifier)
                          .updateFingeringOptimistic(
                            noteId,
                            selectedFinger,
                            selectedHand,
                          );
                      Navigator.of(context).pop();
                      // Show success message
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Fingering updated'),
                          duration: Duration(seconds: 2),
                        ),
                      );
                    },
                    child: const Text('Save'),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}

