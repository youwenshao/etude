import 'dart:html' as html;
import 'dart:ui_web' as ui_web;
import 'package:flutter/material.dart';
import '../../../core/utils/svg_utils.dart';

/// Web-specific SVG viewer that uses native browser rendering via HtmlElementView.
/// Uses inline SVG embedding to ensure proper CSS styling from Verovio.
/// 
/// Uses the same class name as the IO version for conditional import compatibility.
class PlatformSvgView extends StatefulWidget {
  final String svgContent;
  final String viewId;
  
  const PlatformSvgView({
    super.key,
    required this.svgContent,
    required this.viewId,
  });
  
  @override
  State<PlatformSvgView> createState() => _PlatformSvgViewState();
}

class _PlatformSvgViewState extends State<PlatformSvgView> {
  bool _isRegistered = false;
  
  @override
  void initState() {
    super.initState();
    _registerViewFactory();
  }
  
  @override
  void didUpdateWidget(PlatformSvgView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.svgContent != widget.svgContent || oldWidget.viewId != widget.viewId) {
      _isRegistered = false;
      _registerViewFactory();
    }
  }
  
  void _registerViewFactory() {
    if (_isRegistered || widget.svgContent.isEmpty) return;
    
    final viewId = 'svg-view-${widget.viewId}';
    
    ui_web.platformViewRegistry.registerViewFactory(
      viewId,
      (int id) {
        // Create container for the SVG
        final container = html.DivElement()
          ..style.width = '100%'
          ..style.height = '100%'
          ..style.margin = '0'
          ..style.padding = '0'
          ..style.backgroundColor = 'white'
          ..style.overflow = 'auto'
          ..style.display = 'flex'
          ..style.alignItems = 'flex-start'
          ..style.justifyContent = 'flex-start';
        
        try {
          // Flatten nested SVG structure to fix viewBox/dimension mismatch
          final flattenedSvg = flattenSvgForRendering(widget.svgContent);
          
          // Use insertAdjacentHTML with trusted sanitizer to insert SVG inline
          // This preserves all CSS classes and style blocks
          container.insertAdjacentHtml(
            'beforeend',
            flattenedSvg,
            treeSanitizer: html.NodeTreeSanitizer.trusted,
          );
          
          // Find the SVG element and ensure it's properly styled
          final svgElement = container.querySelector('svg');
          if (svgElement != null) {
            // Ensure SVG is visible and properly sized
            svgElement.style.display = 'block';
            
            // If SVG doesn't have explicit width/height, ensure it's visible
            final width = svgElement.getAttribute('width');
            final height = svgElement.getAttribute('height');
            
            if (width == null || height == null) {
              // Try to get from viewBox if present
              final viewBox = svgElement.getAttribute('viewBox');
              if (viewBox != null) {
                final viewBoxValues = viewBox.split(RegExp(r'[\s,]+'));
                if (viewBoxValues.length >= 4) {
                  final vbWidth = viewBoxValues[2];
                  final vbHeight = viewBoxValues[3];
                  svgElement.setAttribute('width', vbWidth);
                  svgElement.setAttribute('height', vbHeight);
                }
              }
            }
            
            // Force a reflow to ensure styles are applied
            // ignore: avoid_print
            print('WebSvgView: SVG inserted, dimensions: ${svgElement.getAttribute('width')} x ${svgElement.getAttribute('height')}');
          } else {
            // ignore: avoid_print
            print('WebSvgView: WARNING - SVG element not found after insertion');
            container.innerHtml = '<div style="padding: 20px; color: red;">Error: SVG element not found</div>';
          }
        } catch (e, stackTrace) {
          // ignore: avoid_print
          print('WebSvgView: Error inserting SVG: $e\n$stackTrace');
          container.innerHtml = '<div style="padding: 20px; color: red;">Error: $e</div>';
        }
        
        return container;
      },
    );
    
    _isRegistered = true;
  }
  
  @override
  Widget build(BuildContext context) {
    if (widget.svgContent.isEmpty) {
      return const Center(
        child: Text('No SVG content available'),
      );
    }
    
    // Ensure factory is registered (only once)
    if (!_isRegistered) {
      _registerViewFactory();
    }
    
    final viewId = 'svg-view-${widget.viewId}';
    
    // Use HtmlElementView to embed the inline SVG
    return HtmlElementView(
      viewType: viewId,
      onPlatformViewCreated: (int id) {
        // ignore: avoid_print
        print('WebSvgView: HtmlElementView created with id: $id');
      },
    );
  }
}
