// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'artifact.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Artifact _$ArtifactFromJson(Map<String, dynamic> json) => Artifact(
      id: json['id'] as String,
      jobId: json['job_id'] as String,
      artifactType: json['artifact_type'] as String,
      schemaVersion: json['schema_version'] as String?,
      storagePath: json['storage_path'] as String,
      fileSize: (json['file_size'] as num).toInt(),
      checksum: json['checksum'] as String,
      parentArtifactId: json['parent_artifact_id'] as String?,
      artifactMetadata: json['artifact_metadata'] as Map<String, dynamic>?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$ArtifactToJson(Artifact instance) => <String, dynamic>{
      'id': instance.id,
      'job_id': instance.jobId,
      'artifact_type': instance.artifactType,
      'schema_version': instance.schemaVersion,
      'storage_path': instance.storagePath,
      'file_size': instance.fileSize,
      'checksum': instance.checksum,
      'parent_artifact_id': instance.parentArtifactId,
      'artifact_metadata': instance.artifactMetadata,
      'created_at': instance.createdAt.toIso8601String(),
    };
