# Changelog

All notable changes to this project will be documented here.

## [v1.0] - 2026-01-XX
### Added
- Initial prototype with Pi camera live preview.
- Basic gesture loop using MediaPipe Hands.
- Capture triggered by single-hand gesture via POST to `/capture`.
- Gallery and review modes integrated with flag-driven control.

### Result
Working baseline with hands-based gesture capture.

---

## [v1.1] - 2026-02-XX
### Changed
- Refined gesture loop with cooldown timer to prevent rapid captures.
- Improved flag-driven control for pausing/resuming scanner in review/gallery.
- Documented transitions for reproducibility and future extension.
- Tagged as stable baseline before branching experiments.

### Result
Stable, appliance-grade scanner with robust hand gesture control.

---

## [v1.2] - 2026-02-10
### Added
- Switched gesture detection from Hands → Pose for broader input options.
- Visibility filters to ensure landmarks are reliable before evaluation.
- Bounding guard to prevent false quits when walking away.
- Debounce counters (3 consecutive frames) to eliminate flicker.
- Gesture priority: quit overrides capture.

### Changed
- Capture still uses POST to `/capture`.
- Quit now calls a direct shutdown function for robustness.

### Result
Smooth, smarter scanner with appliance‑grade reliability and deliberate gesture control.
