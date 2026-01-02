import 'package:flutter/material.dart';
import 'score_web_view_io.dart' if (dart.library.html) 'score_web_view_web.dart';

class ScoreWebView extends StatelessWidget {
  final String musicXmlContent;
  final bool showFingering;
  final double zoom;
  final Function(String)? onNoteClick;
  final VoidCallback? onLoadComplete;

  const ScoreWebView({
    super.key,
    required this.musicXmlContent,
    this.showFingering = true,
    this.zoom = 1.0,
    this.onNoteClick,
    this.onLoadComplete,
  });

  @override
  Widget build(BuildContext context) {
    return ScoreWebViewPlatform(
      musicXmlContent: musicXmlContent,
      showFingering: showFingering,
      zoom: zoom,
      onNoteClick: onNoteClick,
      onLoadComplete: onLoadComplete,
    );
  }
}
