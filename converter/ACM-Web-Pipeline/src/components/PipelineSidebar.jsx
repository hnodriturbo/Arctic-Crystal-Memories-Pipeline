"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Pipeline Sidebar
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/PipelineSidebar.jsx
 * Purpose: Responsive navigation with one numbered section per pipeline.
 */

import { SECTIONS } from "@/lib/navigation";
import { useLanguage } from "@/components/LanguageProvider";

// One path each, drawn on a 24-box, so the rail stays one visual weight.
const ICONS = {
  photo: "M3 5h18v14H3zM3 16l5-5 4 4 3-3 6 6",
  wand: "M15 4V2m0 20v-2M9.5 9.5l-6 6a2 2 0 003 3l6-6M13 7l4 4M19 9l2-2-4-4-2 2M20 15h2m-2 4h2",
  eye: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7zM12 15a3 3 0 100-6 3 3 0 000 6z",
  sparkle: "M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2zM19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z",
  layers: "M12 3l9 5-9 5-9-5zM3 13l9 5 9-5M3 17l9 5 9-5",
  cube: "M12 2l9 5v10l-9 5-9-5V7zM12 12l9-5M12 12v10M12 12L3 7",
  cubes: "M8 4l6 3-6 3-6-3zM16 10l6 3-6 3-6-3zM8 14l6 3-6 3-6-3",
  text: "M4 6h16M4 12h10M4 18h13",
  dots: "M6 7h.01M12 7h.01M18 7h.01M6 12h.01M12 12h.01M18 12h.01M6 17h.01M12 17h.01M18 17h.01",
  palette: "M12 3a9 9 0 100 18c1 0 2-1 2-2s-1-2 0-3 3 0 4-1a8 8 0 00-6-12zM7 12h.01M10 8h.01M15 8h.01",
  run: "M13 4a2 2 0 11.001-.001zM8 21l3-6 4-2 2-5M6 12l4-2 5 3 3 5",
  printer: "M7 8V3h10v5M7 18H5a2 2 0 01-2-2v-4a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2h-2M7 14h10v7H7z",
};

function Icon({ name }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-5 w-5 shrink-0"
      aria-hidden="true"
    >
      <path d={ICONS[name] || ICONS.cube} />
    </svg>
  );
}

export default function PipelineSidebar({ active, onSelect, open = false, onClose, badges = {} }) {
  const { t } = useLanguage();
  return (
    <>
      {open ? (
        <button
          type="button"
          aria-label={t("Close pipeline navigation")}
          onClick={onClose}
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
        />
      ) : null}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-72 shrink-0 flex-col border-r border-surface-border bg-surface-sunken transition-transform duration-200 lg:sticky lg:top-0 lg:h-screen lg:w-64 lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-surface-border px-5 py-5">
          <div>
            <p className="text-sm font-semibold">ACM Pipeline</p>
            <p className="text-[10px] uppercase tracking-wider text-muted">{t("Operator workspace")}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("Close pipeline navigation")}
            className="rounded-md border border-surface-border px-2 py-1 text-sm text-muted lg:hidden"
          >
            ×
          </button>
        </div>

        <nav aria-label={t("Pipeline navigation")} className="flex-1 space-y-6 overflow-y-auto px-3 py-5">
          {SECTIONS.map((section) => (
            <div key={section.id}>
          {/* Section heading - which numbered step this group is */}
          <div className="px-3 pb-2">
            <p className="flex items-baseline gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-strong">
              {section.step ? (
                <span className="rounded bg-surface px-1.5 py-0.5 font-mono text-accent-soft-text">
                  {section.step}
                </span>
              ) : null}
              {t(section.label)}
            </p>
            {section.hint ? (
              <p className="mt-0.5 text-[10px] leading-tight text-muted">{t(section.hint)}</p>
            ) : null}
          </div>

          <ul className="space-y-0.5">
            {section.items.map((item) => {
              const isActive = item.id === active;
              const badge = badges[item.id];

              return (
                <li key={item.id}>
                  <button
                    type="button"
                    disabled={Boolean(item.locked)}
                  onClick={() => {
                    onSelect(item.id);
                    onClose?.();
                  }}
                    title={t(item.locked || item.blurb)}
                    className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left transition ${
                      item.locked
                        ? "cursor-not-allowed text-muted opacity-45"
                        : isActive
                          ? "bg-accent-soft text-accent-soft-text"
                          : "text-foreground hover:bg-surface-hover"
                    }`}
                  >
                    {item.emoji ? (
                      <span aria-hidden="true" className="w-5 shrink-0 text-center text-base leading-none">
                        {item.emoji}
                      </span>
                    ) : (
                      <Icon name={item.icon} />
                    )}
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm">{t(item.label)}</span>
                    </span>

                    {/* A padlock beats an absence - it answers "can it do X?" */}
                    {item.locked ? (
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        className="h-3.5 w-3.5 shrink-0"
                        aria-label={t("locked")}
                      >
                        <rect x="5" y="11" width="14" height="10" rx="2" />
                        <path d="M8 11V7a4 4 0 018 0v4" />
                      </svg>
                    ) : badge ? (
                      <span className="shrink-0 rounded-full bg-surface px-1.5 font-mono text-[10px] text-muted">
                        {badge}
                      </span>
                    ) : null}
                  </button>
                </li>
              );
            })}
          </ul>
            </div>
          ))}
        </nav>
      </aside>
    </>
  );
}
