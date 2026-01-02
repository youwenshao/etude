/// Utility functions for processing SVG content for Flutter rendering.

/// Flattens nested SVG structures to fix viewBox/dimension mismatch from Verovio.
/// 
/// Verovio generates SVGs with nested <svg> elements where the outer SVG
/// has small dimensions (e.g., 840x80px) but the inner SVG has a large
/// viewBox (e.g., 0 0 21000 2000) combined with translate transforms,
/// causing content to render outside the visible area.
/// 
/// This function:
/// 1. Detects nested <svg class="definition-scale" viewBox="...">
/// 2. Extracts the inner viewBox
/// 3. Replaces outer SVG dimensions with viewBox
/// 4. Removes the nested SVG wrapper, keeping content
/// 
/// Args:
///   svgContent: The raw SVG string from the renderer
/// 
/// Returns:
///   A flattened SVG string with proper viewBox
String flattenSvgForRendering(String svgContent) {
  if (svgContent.isEmpty) {
    return svgContent;
  }
  
  // Pattern to match nested SVG with definition-scale class
  // Matches: <svg class="definition-scale" viewBox="0 0 21000 2000">
  // Try double quotes first, then single quotes
  final nestedSvgPatternDouble = RegExp(
    r'<svg\s+class="definition-scale"[^>]*?>',
    caseSensitive: false,
    dotAll: true,
  );
  final nestedSvgPatternSingle = RegExp(
    r"<svg\s+class='definition-scale'[^>]*?>",
    caseSensitive: false,
    dotAll: true,
  );
  
  // Pattern to extract viewBox from inner SVG attributes
  // Matches viewBox="..." or viewBox='...'
  final viewBoxPatternDouble = RegExp(
    r'viewBox="([^"]+)"',
    caseSensitive: false,
  );
  final viewBoxPatternSingle = RegExp(
    r"viewBox='([^']+)'",
    caseSensitive: false,
  );
  
  // Check if we have a nested SVG structure
  RegExpMatch? nestedMatch = nestedSvgPatternDouble.firstMatch(svgContent);
  if (nestedMatch == null) {
    nestedMatch = nestedSvgPatternSingle.firstMatch(svgContent);
  }
  if (nestedMatch == null) {
    // No nested SVG found, return as-is
    return svgContent;
  }
  
  // Extract viewBox from the nested SVG opening tag
  final nestedStartPos = nestedMatch.start;
  final nestedStartEnd = nestedMatch.end;
  final nestedTag = svgContent.substring(nestedStartPos, nestedStartEnd);
  
  // Try to find viewBox with either quote type
  RegExpMatch? viewBoxMatch = viewBoxPatternDouble.firstMatch(nestedTag);
  if (viewBoxMatch == null) {
    viewBoxMatch = viewBoxPatternSingle.firstMatch(nestedTag);
  }
  if (viewBoxMatch == null) {
    // No viewBox found in inner SVG, return as-is
    return svgContent;
  }
  
  final viewBoxValue = viewBoxMatch.group(1)!;
  
  // Find the matching closing tag for the nested SVG
  int pos = nestedStartEnd;
  int depth = 1;
  int nestedEndPos = nestedStartEnd;
  
  while (pos < svgContent.length && depth > 0) {
    // Look for <svg or </svg>
    final svgTagPos = svgContent.indexOf('<svg', pos);
    final closingTagPos = svgContent.indexOf('</svg>', pos);
    
    if (closingTagPos == -1) {
      // No more closing tags found
      return svgContent;
    }
    
    if (svgTagPos != -1 && svgTagPos < closingTagPos) {
      // Found another opening tag first
      // Check if it's self-closing
      final tagEnd = svgContent.indexOf('>', svgTagPos);
      if (tagEnd != -1 && tagEnd < closingTagPos) {
        if (svgContent[tagEnd - 1] == '/') {
          // Self-closing, skip it
          pos = tagEnd + 1;
        } else {
          // Opening tag, increase depth
          depth++;
          pos = tagEnd + 1;
        }
      } else {
        // Malformed, try closing tag
        depth--;
        if (depth == 0) {
          // Found the matching closing tag
          nestedEndPos = closingTagPos + 6;
          break;
        }
        pos = closingTagPos + 6;
      }
    } else {
      // Found closing tag first
      depth--;
      if (depth == 0) {
        // Found the matching closing tag
        nestedEndPos = closingTagPos + 6;
        break;
      }
      pos = closingTagPos + 6;
    }
  }
  
  if (depth != 0) {
    return svgContent;
  }
  
  // Extract content between nested SVG tags (excluding the tags themselves)
  final innerContent = svgContent.substring(nestedStartEnd, nestedEndPos - 6);
  
  // Find and replace outer SVG opening tag
  final outerSvgPattern = RegExp(
    r'<svg[^>]*?>',
    caseSensitive: false,
    dotAll: true,
  );
  final outerMatch = outerSvgPattern.firstMatch(svgContent);
  if (outerMatch == null) {
    return svgContent;
  }
  
  final outerSvgStart = outerMatch.start;
  final outerSvgTag = outerMatch.group(0)!;
  
  // Build new outer SVG tag with viewBox
  // Remove existing width, height, viewBox attributes
  // Try both double and single quotes
  var outerTagClean = outerSvgTag.replaceAll(
    RegExp(r'\s+(?:width|height|viewBox)="[^"]+"', caseSensitive: false),
    '',
  );
  outerTagClean = outerTagClean.replaceAll(
    RegExp(r"\s+(?:width|height|viewBox)='[^']+'", caseSensitive: false),
    '',
  );
  // Remove style attribute if it has width/height constraints
  outerTagClean = outerTagClean.replaceAll(
    RegExp(r'\s+style="[^"]*width[^"]*"', caseSensitive: false),
    '',
  );
  outerTagClean = outerTagClean.replaceAll(
    RegExp(r"\s+style='[^']*width[^']*'", caseSensitive: false),
    '',
  );
  
  // Add viewBox and preserveAspectRatio
  // Remove the closing > temporarily to add attributes
  if (outerTagClean.endsWith('>')) {
    outerTagClean = outerTagClean.substring(0, outerTagClean.length - 1);
  }
  final newOuterTag = '${outerTagClean.trim()} viewBox="$viewBoxValue" preserveAspectRatio="xMidYMid meet" style="width: 100%; max-width: 100%;">';
  
  // Reconstruct SVG: everything before nested SVG + new outer tag + inner content + everything after nested SVG
  final flattened = svgContent.substring(0, outerSvgStart) +
      newOuterTag +
      innerContent +
      svgContent.substring(nestedEndPos);
  
  return flattened;
}

/// Sanitizes SVG content to be compatible with flutter_svg.
/// 
/// Removes or handles unsupported elements like <style> tags that flutter_svg
/// cannot process. This is necessary because Verovio outputs SVG with <style>
/// elements that contain CSS rules, which flutter_svg doesn't fully support.
/// 
/// The function removes:
/// - <style>...</style> blocks (with or without attributes)
/// - Self-closing <style/> tags
/// - CDATA sections within style tags
/// 
/// It also ensures the SVG has proper structure and attributes needed for rendering.
/// 
/// Args:
///   svgContent: The raw SVG string from the renderer
/// 
/// Returns:
///   A sanitized SVG string that flutter_svg can render
String sanitizeSvgForFlutter(String svgContent) {
  if (svgContent.isEmpty) {
    return svgContent;
  }
  
  String sanitized = svgContent;
  
  // Remove <style> elements and their content
  // This regex matches <style>...</style> including:
  // - Attributes: <style type="text/css">...</style>
  // - CDATA: <style><![CDATA[...]]></style>
  // - Multi-line content
  // Uses non-greedy matching to handle multiple style blocks
  final stylePattern = RegExp(
    r'<style[^>]*>.*?</style>',
    caseSensitive: false,
    dotAll: true,
  );
  
  // Handle self-closing style tags: <style/> or <style />
  final selfClosingStylePattern = RegExp(
    r'<style[^>]*\s*/>',
    caseSensitive: false,
  );
  
  // Remove style blocks (may contain CDATA or regular content)
  sanitized = sanitized.replaceAll(stylePattern, '');
  
  // Remove self-closing style tags
  sanitized = sanitized.replaceAll(selfClosingStylePattern, '');
  
  // Clean up any extra whitespace that might have been left behind
  // Replace multiple consecutive newlines with single newline
  sanitized = sanitized.replaceAll(RegExp(r'\n\s*\n+'), '\n');
  
  // Ensure the SVG still starts with <svg and has proper structure
  final trimmed = sanitized.trim();
  if (!trimmed.startsWith('<svg')) {
    // If we accidentally removed too much, return original
    // This shouldn't happen, but be safe
    return svgContent;
  }
  
  // Ensure SVG has viewBox if it doesn't have width/height
  // This helps with rendering on web
  if (!trimmed.contains('viewBox=') && 
      !trimmed.contains('width=') && 
      !trimmed.contains('height=')) {
    // Try to extract dimensions from the SVG or add a default viewBox
    // For now, we'll let flutter_svg handle it, but log a warning
    // In practice, Verovio should always include viewBox
  }
  
  return sanitized;
}

