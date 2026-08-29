"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Tooltip
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/Tooltip.jsx
 * Purpose: An ⓘ marker that explains one control without taking a line of
 *          the form to do it.
 *
 * CSS-only on hover and focus rather than a positioned popper: these forms
 * have thirty-odd controls, and a JavaScript tooltip on every one of them is
 * thirty listeners for something a `group-hover` handles.
 *
 * Keyboard-reachable on purpose - `tabIndex` plus `group-focus-within` means
 * the explanation is available without a mouse.
 */

export default function Tooltip({ text, side = "right" }) {
  if (!text) return null;

  return (
    <span className="group relative inline-flex align-middle">
      <span
        tabIndex={0}
        role="note"
        aria-label={text}
        className="flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-input-border text-[9px] font-semibold text-muted transition group-hover:border-accent group-hover:text-accent"
      >
        i
      </span>

      {/* Hidden until hover or focus; pointer-events-none so it never eats a click */}
      <span
        role="tooltip"
        className={`pointer-events-none fixed inset-x-4 bottom-4 z-50 w-auto rounded-lg border border-surface-border bg-surface px-3 py-2 text-xs leading-relaxed text-foreground opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100 sm:absolute sm:inset-x-auto sm:bottom-auto sm:w-64 ${
          side === "left" ? "sm:right-6 sm:top-0" : "sm:left-6 sm:top-0"
        }`}
      >
        {text}
      </span>
    </span>
  );
}
