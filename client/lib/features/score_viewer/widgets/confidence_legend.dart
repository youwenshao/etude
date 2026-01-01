import 'package:flutter/material.dart';

class ConfidenceLegend extends StatelessWidget {
  const ConfidenceLegend({super.key});
  
  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Fingering Confidence',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            _buildLegendItem(
              context,
              Colors.green,
              'High (80%+)',
              'Very confident',
            ),
            const SizedBox(height: 8),
            _buildLegendItem(
              context,
              Colors.orange,
              'Medium (60-80%)',
              'Reasonably confident',
            ),
            const SizedBox(height: 8),
            _buildLegendItem(
              context,
              Colors.red,
              'Low (<60%)',
              'Less confident - consider alternatives',
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildLegendItem(
    BuildContext context,
    Color color,
    String label,
    String description,
  ) {
    return Row(
      children: [
        Container(
          width: 20,
          height: 20,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
            border: Border.all(color: Colors.white, width: 1),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: const TextStyle(
                  fontWeight: FontWeight.w500,
                  fontSize: 13,
                ),
              ),
              Text(
                description,
                style: TextStyle(
                  fontSize: 11,
                  color: Colors.grey[600],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

