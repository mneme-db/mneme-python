# Phase 6 PyOZ Evaluation

## Scope

PyOZ is evaluated as a candidate for future native Python extensions, not as the main Phase 6 production path.

## Summary

- PyOZ appears promising for declarative Zig-native Python modules and potentially strong ergonomics.
- For this phase, project risk is lower with an ABI wrapper (`ctypes`) due to maturity and simpler CI.
- Recommendation: keep PyOZ experimental until packaging stability and compatibility are proven in this project context.

## Recommendation for Phase 7+

- Run a focused PyOZ spike exposing a tiny API such as `version()` backed by `mneme_abi_version()`.
- Validate supported Zig and Python version matrix.
- Validate CI and wheel feasibility before considering migration of production bindings.
