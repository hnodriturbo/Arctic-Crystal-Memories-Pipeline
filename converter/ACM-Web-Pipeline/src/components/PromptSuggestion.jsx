"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Prompt Suggestion
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/PromptSuggestion.jsx
 * Purpose: Show what OpenAI made of a photograph and let it be taken or left.
 *
 * A suggestion, never an assignment. It lands in a card of its own and only
 * reaches the form when the button is pressed, so a bad reading of a photo
 * costs a glance rather than a silently overwritten prompt.
 */

import { useLanguage } from "@/components/LanguageProvider";

const FIELD = "rounded-lg border border-surface-border bg-surface-sunken p-3";

export default function PromptSuggestion({ suggestion, onAccept, onDiscard, target = "prompt" }) {
  const { locale } = useLanguage();
  if (!suggestion) return null;

  return (
    <div className="space-y-3 rounded-lg border border-accent bg-accent-soft/30 p-4">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-accent-soft-text">
          {locale === "is" ? "Tillaga að " : "Suggested "}
          {target === "texture_prompt" ? "texture prompt" : locale === "is" ? "fyrirmælum" : "prompt"}
        </p>
        {suggestion.subject ? (
          <span className="truncate font-mono text-xs text-muted">{suggestion.subject}</span>
        ) : null}
      </div>

      {/* The prompt itself - the only part that reaches the form */}
      <div className={FIELD}>
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{suggestion.prompt}</p>
        <p className="mt-2 font-mono text-[10px] text-muted">
          {suggestion.prompt.length}/600 characters
        </p>
      </div>

      {suggestion.texture_prompt ? (
        <div className={FIELD}>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-strong">
            {locale === "is" ? "Litir og efni" : "Colours and materials"}
          </p>
          <p className="mt-1 text-sm leading-relaxed">{suggestion.texture_prompt}</p>
        </div>
      ) : null}

      {/* What will make this photo hard to solve - worth reading before spending credits */}
      {suggestion.notes ? (
        <p className="rounded-md border border-warning-border bg-warning-soft px-3 py-2 text-xs text-warning-text">
          {suggestion.notes}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onAccept(suggestion)}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition hover:bg-accent-hover"
        >
          {locale === "is" ? "Nota þessi fyrirmæli" : "Use this prompt"}
        </button>
        <button
          type="button"
          onClick={onDiscard}
          className="rounded-lg border border-surface-border px-4 py-2 text-sm transition hover:bg-surface-hover"
        >
          {locale === "is" ? "Hafna" : "Discard"}
        </button>
      </div>
    </div>
  );
}
