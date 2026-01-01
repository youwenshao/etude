import 'dart:io';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../../../core/config/app_config.dart';

class FilePickerWidget extends StatelessWidget {
  final File? selectedFile;
  final Function(File) onFileSelected;
  
  const FilePickerWidget({
    super.key,
    this.selectedFile,
    required this.onFileSelected,
  });
  
  Future<void> _pickFile(BuildContext context) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: AppConfig.allowedFileExtensions,
      allowMultiple: false,
    );
    
    if (result != null && result.files.single.path != null) {
      final file = File(result.files.single.path!);
      
      // Validate file size
      final fileSize = await file.length();
      if (fileSize > AppConfig.maxFileSizeBytes) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'File size exceeds ${AppConfig.maxFileSizeMB}MB limit',
              ),
              backgroundColor: Colors.red,
            ),
          );
        }
        return;
      }
      
      onFileSelected(file);
    }
  }
  
  @override
  Widget build(BuildContext context) {
    if (selectedFile != null) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.deepPurple),
          borderRadius: BorderRadius.circular(8),
          color: Colors.deepPurple[50],
        ),
        child: Row(
          children: [
            const Icon(Icons.picture_as_pdf, color: Colors.deepPurple),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                selectedFile!.path.split('/').last,
                style: const TextStyle(fontWeight: FontWeight.w500),
              ),
            ),
          ],
        ),
      );
    }
    
    return InkWell(
      onTap: () => _pickFile(context),
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey[300]!),
          borderRadius: BorderRadius.circular(8),
          color: Colors.grey[50],
        ),
        child: Column(
          children: [
            Icon(Icons.cloud_upload_outlined, size: 48, color: Colors.grey[400]),
            const SizedBox(height: 8),
            const Text('Tap to select PDF file'),
          ],
        ),
      ),
    );
  }
}

