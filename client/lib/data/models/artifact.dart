import 'package:json_annotation/json_annotation.dart';

part 'artifact.g.dart';

enum ArtifactType {
  @JsonValue('pdf')
  pdf,
  @JsonValue('ir_v1')
  irV1,
  @JsonValue('ir_v2')
  irV2,
  @JsonValue('musicxml')
  musicxml,
  @JsonValue('midi')
  midi,
  @JsonValue('svg')
  svg,
}

@JsonSerializable()
class Artifact {
  final String id;
  @JsonKey(name: 'job_id')
  final String jobId;
  @JsonKey(name: 'artifact_type')
  final String artifactType;
  @JsonKey(name: 'schema_version')
  final String? schemaVersion;
  @JsonKey(name: 'storage_path')
  final String storagePath;
  @JsonKey(name: 'file_size')
  final int fileSize;
  final String checksum;
  @JsonKey(name: 'parent_artifact_id')
  final String? parentArtifactId;
  @JsonKey(name: 'artifact_metadata')
  final Map<String, dynamic>? artifactMetadata;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  
  Artifact({
    required this.id,
    required this.jobId,
    required this.artifactType,
    this.schemaVersion,
    required this.storagePath,
    required this.fileSize,
    required this.checksum,
    this.parentArtifactId,
    this.artifactMetadata,
    required this.createdAt,
  });
  
  factory Artifact.fromJson(Map<String, dynamic> json) => 
      _$ArtifactFromJson(json);
  Map<String, dynamic> toJson() => _$ArtifactToJson(this);
  
  ArtifactType get typeEnum {
    return ArtifactType.values.firstWhere(
      (e) => e.name.toLowerCase().replaceAll('v', '_v') == artifactType.toLowerCase(),
      orElse: () => ArtifactType.pdf,
    );
  }
}

