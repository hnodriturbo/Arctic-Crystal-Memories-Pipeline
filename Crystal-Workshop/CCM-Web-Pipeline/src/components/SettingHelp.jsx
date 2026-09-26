"use client";
/** Purpose: Keyboard, pointer and touch accessible help for rendering settings. */
import { useId, useState } from "react";
export default function SettingHelp({ text, label }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return <span className="relative inline-block align-middle" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
    <button type="button" aria-label={"ⓘ " + label} aria-expanded={open} aria-describedby={open ? id : undefined}
      onClick={(event) => { event.preventDefault(); setOpen(true); }} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}
      onKeyDown={(event) => { if (event.key === "Escape") setOpen(false); }}
      className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-current text-xs text-accent focus-visible:outline-2">i</button>
    {open && <span id={id} role="tooltip" className="fixed inset-x-4 bottom-4 z-50 mx-auto block max-h-[60vh] w-auto max-w-lg overflow-y-auto whitespace-pre-line rounded-lg border border-surface-border bg-surface p-3 text-xs font-normal leading-relaxed text-foreground shadow-xl">{text}</span>}
  </span>;
}
