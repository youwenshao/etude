import 'package:flutter_riverpod/flutter_riverpod.dart';

class FingeringEditState {
  final Map<String, Map<String, dynamic>> pendingEdits;
  
  FingeringEditState({
    this.pendingEdits = const {},
  });
  
  FingeringEditState copyWith({
    Map<String, Map<String, dynamic>>? pendingEdits,
  }) {
    return FingeringEditState(
      pendingEdits: pendingEdits ?? this.pendingEdits,
    );
  }
}

class FingeringEditController extends StateNotifier<FingeringEditState> {
  FingeringEditController() : super(FingeringEditState());
  
  void updateFingering(String noteId, int finger, String hand) {
    final newEdits = Map<String, Map<String, dynamic>>.from(state.pendingEdits);
    newEdits[noteId] = {
      'finger': finger,
      'hand': hand,
    };
    state = state.copyWith(pendingEdits: newEdits);
  }
  
  void revertEdit(String noteId) {
    final newEdits = Map<String, Map<String, dynamic>>.from(state.pendingEdits);
    newEdits.remove(noteId);
    state = state.copyWith(pendingEdits: newEdits);
  }
  
  void clearAll() {
    state = FingeringEditState();
  }
  
  Future<void> saveEdits(String jobId) async {
    // This will be implemented when API endpoint is available
    // For now, just clear pending edits
    clearAll();
  }
}

final fingeringEditControllerProvider = StateNotifierProvider<FingeringEditController, FingeringEditState>(
  (ref) => FingeringEditController(),
);

