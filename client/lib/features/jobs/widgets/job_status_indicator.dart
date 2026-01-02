import 'package:flutter/material.dart';
import '../../../core/theme/colors.dart';

class JobStatusIndicator extends StatelessWidget {
  final String status;
  final double? size;
  
  const JobStatusIndicator({
    super.key,
    required this.status,
    this.size,
  });
  
  Color get _statusColor {
    switch (status) {
      case 'pending':
        return Colors.grey;
      case 'omr_processing':
      case 'fingering_processing':
      case 'rendering_processing':
        return AppColors.info;
      case 'omr_completed':
      case 'fingering_completed':
        return AppColors.success;
      case 'completed':
        return AppColors.success;
      case 'omr_failed':
      case 'fingering_failed':
      case 'failed':
        return AppColors.error;
      default:
        return Colors.grey;
    }
  }
  
  IconData get _statusIcon {
    switch (status) {
      case 'pending':
        return Icons.pending_outlined;
      case 'omr_processing':
      case 'fingering_processing':
      case 'rendering_processing':
        return Icons.autorenew;
      case 'omr_completed':
      case 'fingering_completed':
        return Icons.check_circle_outline;
      case 'completed':
        return Icons.check_circle;
      case 'omr_failed':
      case 'fingering_failed':
      case 'failed':
        return Icons.error_outline;
      default:
        return Icons.help_outline;
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: _statusColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: _statusColor.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            _statusIcon,
            size: size ?? 16,
            color: _statusColor,
          ),
          const SizedBox(width: 6),
          Text(
            _getStatusText(),
            style: TextStyle(
              color: _statusColor,
              fontWeight: FontWeight.w500,
              fontSize: size != null ? size! * 0.8 : 12,
            ),
          ),
        ],
      ),
    );
  }
  
  String _getStatusText() {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'omr_processing':
        return 'Reading Music';
      case 'omr_completed':
        return 'Music Read';
      case 'fingering_processing':
        return 'Analyzing Fingering';
      case 'fingering_completed':
        return 'Fingering Complete';
      case 'rendering_processing':
        return 'Rendering';
      case 'completed':
        return 'Complete';
      case 'omr_failed':
        return 'Reading Failed';
      case 'fingering_failed':
        return 'Fingering Failed';
      case 'failed':
        return 'Failed';
      default:
        return status;
    }
  }
}

