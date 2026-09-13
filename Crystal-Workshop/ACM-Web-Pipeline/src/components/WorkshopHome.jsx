"use client";
/** Purpose: A responsive, shared-navigation overview of every Crystal Workshop pipeline. */
import { SECTIONS } from '@/lib/navigation';
import { useLanguage } from '@/components/LanguageProvider';

export default function WorkshopHome({ onSelect }) {
  const { t, locale } = useLanguage();
  const chapters = SECTIONS.filter((section) => section.id !== 'system');
  const columns = chapters.length === 4 ? 'lg:grid-cols-2' : chapters.length >= 5 ? 'lg:grid-cols-3' : 'lg:grid-cols-2';
  return <div className="space-y-7">
    <header className="relative overflow-hidden rounded-3xl border border-accent/25 bg-gradient-to-br from-accent-soft via-surface to-surface-sunken px-6 py-10 sm:px-10 sm:py-14">
      <div aria-hidden="true" className="pointer-events-none absolute -right-6 -top-16 rotate-12 text-[240px] leading-none text-accent/10">◇</div>
      <p className="relative mb-4 text-xs font-semibold uppercase tracking-[.24em] text-accent-soft-text">Arctic Crystal Memories</p>
      <h1 className="relative text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl">Crystal Workshop</h1>
      <p className="relative mt-5 max-w-xl text-base leading-7 text-muted-strong">{locale === 'is' ? 'Frá fyrstu ljósmynd að þrívíðu verki. Veldu vinnslulínu og mótaðu næstu minningu.' : 'From the first photograph to a three-dimensional piece. Choose a workspace and shape the next memory.'}</p>
    </header>
    <div className={`grid gap-5 md:grid-cols-2 ${columns}`}>{chapters.map((section, index) => <section key={section.id} className="group overflow-hidden rounded-2xl border border-surface-border bg-surface shadow-sm transition hover:border-accent/40 hover:shadow-lg hover:shadow-accent/5">
      <div className="flex items-start gap-4 border-b border-surface-border bg-gradient-to-br from-accent-soft/40 to-surface p-6"><span aria-hidden="true" className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-accent/25 bg-surface text-2xl">{section.items[0]?.emoji || '◇'}</span><div><p className="mb-1 font-mono text-xs text-accent">{String(index + 1).padStart(2, '0')}</p><h2 className="text-xl font-semibold">{t(section.label)}</h2><p className="mt-2 text-sm leading-6 text-muted">{t(section.hint)}</p></div></div>
      <div className="space-y-1 p-3">{section.items.map((item) => <button key={item.id} type="button" disabled={Boolean(item.locked)} title={item.locked ? t(item.locked) : undefined} onClick={() => onSelect(item.id)} className="flex w-full items-center justify-between gap-4 rounded-xl px-4 py-3 text-left text-sm transition hover:bg-accent-soft hover:text-accent-soft-text disabled:cursor-not-allowed disabled:opacity-40"><span>{t(item.label)}</span><span aria-hidden="true">{item.locked ? '·' : '↗'}</span></button>)}</div>
    </section>)}</div>
    <button onClick={() => onSelect('environments')} className="text-sm text-muted hover:text-accent">{t('Python environments')} →</button>
  </div>;
}
