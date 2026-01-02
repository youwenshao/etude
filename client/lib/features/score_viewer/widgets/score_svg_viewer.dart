import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'fingering_overlay.dart';
import 'confidence_overlay.dart';
import 'playback_highlight_overlay.dart';
import 'score_coordinate_bridge.dart';

// Import canvas widgets if available, otherwise we'll fail gracefully at runtime if they're needed but missing
// For MVP PNG solution, this widget acts as a fallback or container
// We are restoring it to satisfy imports

class ScoreSvgViewer extends ConsumerStatefulWidget {
  final String svgContent;
  final double zoom;
  final Map<String, dynamic>? irV2Data;
  final int pageNumber;
  final bool showFingering;
  final bool showConfidence;
  final String? jobId;
  
  const ScoreSvgViewer({
    super.key,
    required this.svgContent,
    required this.zoom,
    this.irV2Data,
    required this.pageNumber,
    required this.showFingering,
    required this.showConfidence,
    this.jobId,
  });
  
  @override
  ConsumerState<ScoreSvgViewer> createState() => _ScoreSvgViewerState();
}

class _ScoreSvgViewerState extends ConsumerState<ScoreSvgViewer> {
  final TransformationController _transformationController = TransformationController();
  ScoreCoordinateBridgeProvider? _coordinateBridgeProvider;
  
  @override
  void initState() {
    super.initState();
    _updateZoom();
    _initializeCoordinateBridge();
  }
  
  @override
  void didUpdateWidget(ScoreSvgViewer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.zoom != widget.zoom) {
      _updateZoom();
    }
    if (oldWidget.irV2Data != widget.irV2Data || 
        oldWidget.pageNumber != widget.pageNumber) {
      _initializeCoordinateBridge();
    }
  }
  
  void _initializeCoordinateBridge() {
    if (widget.irV2Data != null) {
      _coordinateBridgeProvider = ScoreCoordinateBridgeProvider(
        irV2Data: widget.irV2Data!,
        pageNumber: widget.pageNumber,
      );
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
    // Basic placeholder since we are moving to PNG
    // If SVG content is present, display it in a basic interactive viewer
    // If we were using the full Canvas implementation, we'd restore that here.
    // For now, this satisfies the import and provides a fallback view.
    
    return Stack(
      children: [
        InteractiveViewer(
          transformationController: _transformationController,
          minScale: 0.5,
          maxScale: 3.0,
          constrained: false,
          child: widget.svgContent.isNotEmpty 
              ? Center(child: Text("SVG View Placeholder (Use PNG)")) 
              : const Center(child: Text("No Content")),
        ),
        
        // We can still try to overlay things if we have data
        if (widget.jobId != null && widget.irV2Data != null)
          Positioned.fill(
            child: PlaybackHighlightOverlay(
              jobId: widget.jobId!,
              irV2Data: widget.irV2Data,
              pageNumber: widget.pageNumber,
              zoom: widget.zoom,
              transformationController: _transformationController,
              coordinateBridge: _coordinateBridgeProvider?.bridge,
            ),
          ),
      ],
    );
  }
}

