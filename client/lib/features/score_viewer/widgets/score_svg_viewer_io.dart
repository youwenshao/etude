import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../../../core/utils/svg_utils.dart';

/// Mobile/Desktop SVG viewer that uses flutter_svg.
/// This implementation sanitizes the SVG to remove unsupported elements like <style> tags.
/// 
/// Uses the same class name as the web version for conditional import compatibility.
class PlatformSvgView extends StatelessWidget {
  final String svgContent;
  final String viewId; // Not used on mobile, but kept for API compatibility with web version
  
  const PlatformSvgView({
    super.key,
    required this.svgContent,
    required this.viewId,
  });
  
  @override
  Widget build(BuildContext context) {
    if (svgContent.isEmpty) {
      return const Center(
        child: Text('No SVG content available'),
      );
    }
    
    // Debug: Log that we're using IO rendering
    // ignore: avoid_print
    print('IoSvgView: Rendering SVG with flutter_svg, content length: ${svgContent.length}');
    
    // Flatten nested SVG structure to fix viewBox/dimension mismatch
    final flattenedSvg = flattenSvgForRendering(svgContent);
    
    // Sanitize SVG to remove unsupported elements like <style> tags
    final sanitizedSvg = sanitizeSvgForFlutter(flattenedSvg);
    
    return SvgPicture.string(
      sanitizedSvg,
      fit: BoxFit.contain,
      placeholderBuilder: (context) => const Center(
        child: CircularProgressIndicator(),
      ),
      allowDrawingOutsideViewBox: true,
    );
  }
}

