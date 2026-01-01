import 'package:flutter/material.dart';

class UploadProgressWidget extends StatelessWidget {
  final double progress;
  final String? message;
  
  const UploadProgressWidget({
    super.key,
    required this.progress,
    this.message,
  });
  
  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        CircularProgressIndicator(
          value: progress > 0 ? progress : null,
        ),
        if (message != null) ...[
          const SizedBox(height: 16),
          Text(
            message!,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
        const SizedBox(height: 16),
        LinearProgressIndicator(
          value: progress,
          backgroundColor: Colors.grey[200],
        ),
        const SizedBox(height: 8),
        Text(
          '${(progress * 100).toInt()}%',
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}

