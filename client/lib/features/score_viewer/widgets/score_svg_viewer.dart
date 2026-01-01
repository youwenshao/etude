import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'fingering_overlay.dart';
import 'confidence_overlay.dart';

class ScoreSvgViewer extends ConsumerStatefulWidget {
  final String svgContent;
  final double zoom;
  final Map<String, dynamic>? irV2Data;
  final int pageNumber;
  final bool showFingering;
  final bool showConfidence;
  
  const ScoreSvgViewer({
    super.key,
    required this.svgContent,
    required this.zoom,
    this.irV2Data,
    required this.pageNumber,
    required this.showFingering,
    required this.showConfidence,
  });
  
  @override
  ConsumerState<ScoreSvgViewer> createState() => _ScoreSvgViewerState();
}

class _ScoreSvgViewerState extends ConsumerState<ScoreSvgViewer> {
  final TransformationController _transformationController = TransformationController();
  
  @override
  void initState() {
    super.initState();
    _updateZoom();
  }
  
  @override
  void didUpdateWidget(ScoreSvgViewer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.zoom != widget.zoom) {
      _updateZoom();
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
    return Stack(
      children: [
        // SVG Score
        InteractiveViewer(
          transformationController: _transformationController,
          minScale: 0.5,
          maxScale: 3.0,
          constrained: false,
          child: Container(
            color: Colors.white,
            child: SvgPicture.string(
              widget.svgContent,
              fit: BoxFit.contain,
            ),
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
            ),
          ),
      ],
    );
  }
}

