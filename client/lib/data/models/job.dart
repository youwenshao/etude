import 'package:json_annotation/json_annotation.dart';

part 'job.g.dart';

enum JobStatus {
  @JsonValue('pending')
  pending,
  @JsonValue('omr_processing')
  omr_processing,
  @JsonValue('omr_completed')
  omr_completed,
  @JsonValue('omr_failed')
  omr_failed,
  @JsonValue('fingering_processing')
  fingering_processing,
  @JsonValue('fingering_completed')
  fingering_completed,
  @JsonValue('fingering_failed')
  fingering_failed,
  @JsonValue('rendering_processing')
  rendering_processing,
  @JsonValue('completed')
  completed,
  @JsonValue('failed')
  failed,
}

@JsonSerializable()
class Job {
  final String id;
  @JsonKey(name: 'user_id')
  final String userId;
  final String status;
  final String? stage;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;
  @JsonKey(name: 'completed_at')
  final DateTime? completedAt;
  @JsonKey(name: 'error_message')
  final String? errorMessage;
  @JsonKey(name: 'job_metadata')
  final Map<String, dynamic>? jobMetadata;
  
  Job({
    required this.id,
    required this.userId,
    required this.status,
    this.stage,
    required this.createdAt,
    required this.updatedAt,
    this.completedAt,
    this.errorMessage,
    this.jobMetadata,
  });
  
  factory Job.fromJson(Map<String, dynamic> json) => _$JobFromJson(json);
  Map<String, dynamic> toJson() => _$JobToJson(this);
  
  // Helper methods
  JobStatus get statusEnum {
    try {
      return JobStatus.values.firstWhere(
        (e) => e.name == status,
        orElse: () => JobStatus.pending,
      );
    } catch (e) {
      return JobStatus.pending;
    }
  }
  
  bool get isProcessing => 
      status == 'omr_processing' ||
      status == 'fingering_processing' ||
      status == 'rendering_processing';
  
  bool get isComplete => status == 'completed';
  bool get isFailed => 
      status == 'failed' ||
      status == 'omr_failed' ||
      status == 'fingering_failed';
  
  String get statusDisplayName {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'omr_processing':
        return 'Reading Music...';
      case 'omr_completed':
        return 'Music Read';
      case 'omr_failed':
        return 'Reading Failed';
      case 'fingering_processing':
        return 'Analyzing Fingering...';
      case 'fingering_completed':
        return 'Fingering Complete';
      case 'fingering_failed':
        return 'Fingering Failed';
      case 'rendering_processing':
        return 'Rendering Score...';
      case 'completed':
        return 'Complete';
      case 'failed':
        return 'Failed';
      default:
        return status;
    }
  }
  
  double get progress {
    switch (status) {
      case 'pending':
        return 0.0;
      case 'omr_processing':
        return 0.2;
      case 'omr_completed':
        return 0.4;
      case 'fingering_processing':
        return 0.6;
      case 'fingering_completed':
        return 0.8;
      case 'rendering_processing':
        return 0.9;
      case 'completed':
        return 1.0;
      default:
        return 0.0;
    }
  }
}

@JsonSerializable()
class JobListResponse {
  final List<Job> items;
  final int total;
  final int page;
  @JsonKey(name: 'page_size')
  final int pageSize;
  
  JobListResponse({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
  });
  
  factory JobListResponse.fromJson(Map<String, dynamic> json) => 
      _$JobListResponseFromJson(json);
  Map<String, dynamic> toJson() => _$JobListResponseToJson(this);
}

