"use client";
/** Purpose: Section cards and bookmarkable tool menus for the active Workshop pipelines. */
import { SECTIONS, sectionNavId } from '@/lib/navigation';
import { useLanguage } from '@/components/LanguageProvider';

/** Use the same navigation definitions for the homepage, section menus and sidebar. */
export default function WorkshopHome({ onSelect, section }) {
  const { t } = useLanguage();
  const cards = section ? section.items : SECTIONS;
  return <div className="space-y-7">
    {section && <button type="button" onClick={() => onSelect('home')} className="rounded-lg px-3 py-2 text-sm text-accent hover:bg-accent-soft">← {t('Workshop home')}</button>}
    <header className="relative overflow-hidden rounded-3xl border border-accent/25 bg-gradient-to-br from-accent-soft via-surface to-surface-sunken px-6 py-10 sm:px-10">
      <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-accent-soft-text">{section?.step ? t('Part') + ' ' + section.step : 'Crystal Workshop'}</p>
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">{section ? t(section.label) : t('Workshop home')}</h1>
      <p className="mt-4 max-w-2xl leading-7 text-muted-strong">{t(section ? section.hint : 'Choose a workspace to begin.')}</p>
      {section && <p className="mt-2 text-sm text-muted">{t('Choose a tool in this workspace.')}</p>}
    </header>
    <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
      {cards.map(card => <button key={card.id} type="button" disabled={Boolean(card.locked)} onClick={() => onSelect(section ? card.id : sectionNavId(card.id))} className="group flex min-h-52 flex-col items-start rounded-2xl border border-surface-border bg-surface p-6 text-left shadow-sm transition hover:border-accent hover:bg-accent-soft focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50">
        <span aria-hidden="true" className="mb-4 text-3xl">{card.emoji || card.items?.[0]?.emoji || '◇'}</span>
        {!section && card.step && <span className="mb-1 text-xs font-semibold uppercase tracking-wider text-accent">{t('Part')} {card.step}</span>}
        <h2 className="text-xl font-semibold">{t(card.label)}</h2>
        <p className="mt-3 text-sm leading-6 text-muted-strong">{t(card.locked || card.blurb || card.hint)}</p>
        <span aria-hidden="true" className="mt-auto pt-5 text-accent">{card.locked ? '🔒' : '→'}</span>
      </button>)}
    </div>
  </div>;
}
