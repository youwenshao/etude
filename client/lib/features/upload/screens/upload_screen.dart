import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:file_picker/file_picker.dart';
import 'package:go_router/go_router.dart';
import '../providers/upload_provider.dart';
import '../../../core/config/app_config.dart';

class UploadScreen extends ConsumerStatefulWidget {
  const UploadScreen({super.key});
  
  @override
  ConsumerState<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends ConsumerState<UploadScreen> {
  File? _selectedFile;
  
  Future<void> _pickFile() async {
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
        if (mounted) {
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
      
      setState(() {
        _selectedFile = file;
      });
    }
  }
  
  Future<void> _upload() async {
    if (_selectedFile != null) {
      await ref.read(uploadProvider.notifier).uploadPDF(_selectedFile!);
      
      final uploadState = ref.read(uploadProvider);
      if (uploadState.job != null && mounted) {
        // Navigate to job detail
        context.push('/jobs/${uploadState.job!.id}');
        // Reset upload state
        ref.read(uploadProvider.notifier).reset();
      }
    }
  }
  
  @override
  Widget build(BuildContext context) {
    final uploadState = ref.watch(uploadProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Upload Sheet Music'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 600),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Upload area
                if (_selectedFile == null && !uploadState.isUploading)
                  InkWell(
                    onTap: _pickFile,
                    borderRadius: BorderRadius.circular(16),
                    child: Container(
                      height: 300,
                      decoration: BoxDecoration(
                        border: Border.all(
                          color: Colors.grey[300]!,
                          width: 2,
                          style: BorderStyle.solid,
                        ),
                        borderRadius: BorderRadius.circular(16),
                        color: Colors.grey[50],
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.cloud_upload_outlined,
                            size: 80,
                            color: Colors.grey[400],
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Tap to select PDF',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Upload your sheet music PDF',
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: Colors.grey[600],
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Max size: ${AppConfig.maxFileSizeMB}MB',
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Colors.grey[500],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                
                // Selected file
                if (_selectedFile != null && !uploadState.isUploading)
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.deepPurple),
                      borderRadius: BorderRadius.circular(16),
                      color: Colors.deepPurple[50],
                    ),
                    child: Column(
                      children: [
                        const Icon(
                          Icons.picture_as_pdf,
                          size: 64,
                          color: Colors.deepPurple,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          _selectedFile!.path.split('/').last,
                          style: Theme.of(context).textTheme.titleMedium,
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 24),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            TextButton(
                              onPressed: () {
                                setState(() {
                                  _selectedFile = null;
                                });
                              },
                              child: const Text('Change'),
                            ),
                            const SizedBox(width: 16),
                            FilledButton.icon(
                              onPressed: _upload,
                              icon: const Icon(Icons.upload),
                              label: const Text('Upload'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                
                // Upload progress
                if (uploadState.isUploading)
                  Column(
                    children: [
                      const CircularProgressIndicator(),
                      const SizedBox(height: 24),
                      Text(
                        'Uploading... ${(uploadState.progress * 100).toInt()}%',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 16),
                      LinearProgressIndicator(
                        value: uploadState.progress,
                        backgroundColor: Colors.grey[200],
                      ),
                    ],
                  ),
                
                // Error
                if (uploadState.error != null)
                  Container(
                    padding: const EdgeInsets.all(16),
                    margin: const EdgeInsets.only(top: 24),
                    decoration: BoxDecoration(
                      color: Colors.red[50],
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.red[200]!),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.error_outline, color: Colors.red[900]),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            uploadState.error!,
                            style: TextStyle(color: Colors.red[900]),
                          ),
                        ),
                        TextButton(
                          onPressed: () {
                            ref.read(uploadProvider.notifier).reset();
                            setState(() {
                              _selectedFile = null;
                            });
                          },
                          child: const Text('Dismiss'),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

