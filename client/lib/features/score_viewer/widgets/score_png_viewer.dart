import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'fingering_overlay.dart';
import 'confidence_overlay.dart';
import 'playback_highlight_overlay.dart';

/// Score viewer widget that displays PNG images from server-side rendering.
/// 
/// Uses server-generated PNG for reliable cross-platform display,
/// with Flutter-based overlays for fingering and confidence visualization.
class ScorePngViewer extends ConsumerStatefulWidget {
  final String pngBase64; // Base64 encoded PNG data
  final double zoom;
  final Map<String, dynamic>? irV2Data;
  final int pageNumber;
  final bool showFingering;
  final bool showConfidence;
  final String? jobId;
  
  const ScorePngViewer({
    super.key,
    required this.pngBase64,
    required this.zoom,
    this.irV2Data,
    required this.pageNumber,
    required this.showFingering,
    required this.showConfidence,
    this.jobId,
  });
  
  @override
  ConsumerState<ScorePngViewer> createState() => _ScorePngViewerState();
}

class _ScorePngViewerState extends ConsumerState<ScorePngViewer> {
  final TransformationController _transformationController = TransformationController();
  Uint8List? _imageBytes;
  Size? _imageSize;
  
  @override
  void initState() {
    super.initState();
    _updateZoom();
    _decodeImage();
  }
  
  @override
  void didUpdateWidget(ScorePngViewer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.zoom != widget.zoom) {
      _updateZoom();
    }
    if (oldWidget.pngBase64 != widget.pngBase64) {
      _decodeImage();
    }
  }
  
  void _decodeImage() {
    if (widget.pngBase64.isEmpty) {
      setState(() {
        _imageBytes = null;
        _imageSize = null;
      });
      return;
    }
    
    try {
      final bytes = base64Decode(widget.pngBase64);
      setState(() {
        _imageBytes = bytes;
      });
      
      // Decode image to get dimensions for overlay positioning
      _loadImageDimensions(bytes);
    } catch (e) {
      debugPrint('Error decoding PNG: $e');
      setState(() {
        _imageBytes = null;
        _imageSize = null;
      });
    }
  }
  
  Future<void> _loadImageDimensions(Uint8List bytes) async {
    try {
      final image = await decodeImageFromList(bytes);
      if (mounted) {
        setState(() {
          _imageSize = Size(image.width.toDouble(), image.height.toDouble());
        });
      }
    } catch (e) {
      debugPrint('Error getting image dimensions: $e');
    }
  }
  
  void _updateZoom() {
    _transformationController.value = Matrix4.identity()..scale(widget.zoom);
  }
  
  @override
  void dispose() {
    _transformationController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    if (_imageBytes == null || _imageBytes!.isEmpty) {
      return const Center(
        child: Text('No score image available'),
      );
    }
    
    final imageWidget = Image.memory(
      _imageBytes!,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.high,
      errorBuilder: (context, error, stackTrace) {
        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.broken_image, size: 64, color: Colors.grey),
              const SizedBox(height: 16),
              Text(
                'Failed to load score image',
                style: TextStyle(color: Colors.grey[600]),
              ),
            ],
          ),
        );
      },
    );
    
    // Determine dimensions for overlay positioning
    final displaySize = _imageSize ?? const Size(800, 1000);
    
    return Stack(
      children: [
        // Score PNG Image with zoom/pan
        InteractiveViewer(
          transformationController: _transformationController,
          minScale: 0.5,
          maxScale: 3.0,
          constrained: false,
          child: Container(
            color: Colors.white,
            child: SizedBox(
              width: displaySize.width,
              height: displaySize.height,
              child: imageWidget,
            ),
          ),
        ),
        
        // Playback Highlight Overlay
        if (widget.jobId != null && widget.irV2Data != null)
          Positioned.fill(
            child: PlaybackHighlightOverlay(
              jobId: widget.jobId!,
              irV2Data: widget.irV2Data,
              pageNumber: widget.pageNumber,
              zoom: widget.zoom,
              transformationController: _transformationController,
              imageSize: displaySize,
            ),
          ),
        
        // Fingering Overlay
        if (widget.showFingering && widget.irV2Data != null)
          Positioned.fill(
            child: FingeringOverlay(
              irV2Data: widget.irV2Data!,
              pageNumber: widget.pageNumber,
              zoom: widget.zoom,
              transformationController: _transformationController,
              jobId: widget.jobId,
              imageSize: displaySize,
            ),
          ),
        
        // Confidence Overlay
        if (widget.showConfidence && widget.irV2Data != null)
          Positioned.fill(
            child: ConfidenceOverlay(
              irV2Data: widget.irV2Data!,
              pageNumber: widget.pageNumber,
              zoom: widget.zoom,
              transformationController: _transformationController,
              imageSize: displaySize,
            ),
          ),
      ],
    );
  }
}

