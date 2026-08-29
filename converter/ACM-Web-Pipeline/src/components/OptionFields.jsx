"use client";

/*
 * ═══════════════════════════════════════════════════════════════
 * Option Fields
 * ═══════════════════════════════════════════════════════════════
 * Path: src/components/OptionFields.jsx
 * Purpose: Render an operation's options straight from the catalogue,
 *          grouped into sections, so adding a script flag never means
 *          touching the UI.
 *
 * Two things carry the explanation: an emoji, which makes a long form
 * scannable at a glance, and a keyboard-accessible info tooltip on every
 * documented setting. Short context also stays inline.
 */

import Tooltip from "@/components/Tooltip";
import { useLanguage } from "@/components/LanguageProvider";

const LABEL = "flex items-center gap-1.5 text-sm font-medium text-foreground";
const HELP = "mt-1 text-xs leading-relaxed text-muted";
const CONTROL =
  "mt-1 w-full rounded-md border border-input-border bg-input-background px-3 py-2 " +
  "text-sm text-foreground outline-none transition focus:border-accent";

// Anything longer than this reads better behind the ⓘ than under the control.
const INLINE_HELP_LIMIT = 90;

/** Emoji, label and tooltip, in the order they should be read. */
function FieldLabel({ field, htmlFor }) {
  const { t } = useLanguage();
  return (
    <label className={LABEL} htmlFor={htmlFor}>
      {field.emoji ? (
        <span aria-hidden="true" className="text-base leading-none">
          {field.emoji}
        </span>
      ) : null}
      <span>{t(field.label)}</span>
      {field.help ? <Tooltip text={t(field.help)} /> : null}
    </label>
  );
}

/** Short help stays under the control; long help lives in the tooltip. */
function InlineHelp({ field, value }) {
  const { t } = useLanguage();
  const selectedHelp = field.optionHelp?.[String(value ?? "")];
  const text = selectedHelp || (field.help?.length <= INLINE_HELP_LIMIT ? field.help : null);
  return text ? <p className={HELP}>{t(text)}</p> : null;
}

/** One control, chosen by field type. */
function Field({ field, value, onChange, fileOptions }) {
  const { t, locale } = useLanguage();
  if (field.type === "boolean") {
    return (
      <label className="flex items-start gap-3 sm:col-span-2">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(event) => onChange(event.target.checked)}
          className="mt-0.5 h-4 w-4 rounded border-input-border accent-accent"
        />
        <span className="min-w-0">
          <span className={LABEL}>
            {field.emoji ? (
              <span aria-hidden="true" className="text-base leading-none">
                {field.emoji}
              </span>
            ) : null}
            <span>{t(field.label)}</span>
            {field.help ? <Tooltip text={t(field.help)} /> : null}
          </span>
          <InlineHelp field={field} value={value} />
        </span>
      </label>
    );
  }

  if (field.type === "multiselect") {
    const chosen = Array.isArray(value) ? value : [];
    return (
      <div className="sm:col-span-2">
        <FieldLabel field={field} />
        <div className="mt-2 flex flex-wrap gap-2">
          {field.options.map((option) => {
            const active = chosen.includes(option);
            return (
              <button
                key={option}
                type="button"
                onClick={() =>
                  onChange(active ? chosen.filter((item) => item !== option) : [...chosen, option])
                }
                title={t(field.optionHelp?.[option])}
                className={`rounded-md border px-3 py-1.5 text-sm transition ${
                  active
                    ? "border-accent bg-accent-soft text-accent-soft-text"
                    : "border-input-border bg-input-background text-muted hover:border-accent"
                }`}
              >
                {option}
              </button>
            );
          })}
        </div>
        <InlineHelp field={field} value={value} />
      </div>
    );
  }

  if (field.type === "file") {
    return (
      <div className="sm:col-span-2">
        <FieldLabel field={field} htmlFor={field.name} />
        <select
          id={field.name}
          value={value ?? ""}
          onChange={(event) => onChange(event.target.value)}
          className={CONTROL}
        >
          <option value="">{locale === "is" ? "ekkert" : "none"}</option>
          {fileOptions.map((item) => (
            <option key={item.path} value={item.path}>
              {item.path}
            </option>
          ))}
        </select>
        <InlineHelp field={field} value={value} />
        {fileOptions.length === 0 ? (
          <p className="mt-1 text-xs text-warning-text">
            No images in input/ yet — upload one and it appears here.
          </p>
        ) : null}
      </div>
    );
  }

  if (field.type === "select") {
    /*
     * Options are plain strings for short lists, or {value, label} where the
     * value alone would not be readable - the crystal blanks are 29 keys like
     * "120x180x80", which mean nothing without the size they leave usable.
     */
    const options = field.options.map((option) =>
      typeof option === "string" ? { value: option, label: option || "off" } : option,
    );

    return (
      <div className={options.length > 8 ? "sm:col-span-2" : undefined}>
        <FieldLabel field={field} htmlFor={field.name} />
        <select
          id={field.name}
          value={value ?? ""}
          onChange={(event) => onChange(event.target.value)}
          className={CONTROL}
        >
          {options.map((option) => (
            <option key={option.value || "none"} value={option.value}>
              {locale === "is" && option.labelIs ? option.labelIs : t(option.label)}
            </option>
          ))}
        </select>
        <InlineHelp field={field} value={value} />
      </div>
    );
  }

  return (
    <div>
      <FieldLabel field={field} htmlFor={field.name} />
      <input
        id={field.name}
        type={field.type === "number" ? "number" : "text"}
        value={value ?? ""}
        min={field.min}
        max={field.max}
        step={field.step}
        placeholder={field.placeholder}
        onChange={(event) =>
          onChange(field.type === "number" ? Number(event.target.value) : event.target.value)
        }
        className={CONTROL}
      />
      <InlineHelp field={field} value={value} />
    </div>
  );
}

export default function OptionFields({ fields, groups, values, onChange, inputs = [] }) {
  const { t } = useLanguage();
  if (!fields.length) {
    return <p className="text-sm text-muted">{t("This operation takes no options.")}</p>;
  }

  const set = (name, value) => onChange({ ...values, [name]: value });

  return (
    <div className="space-y-7">
      {groups.map((group) => {
        const groupFields = fields.filter(
          (field) =>
            (field.group || "output") === group.id &&
            (!field.showWhen || field.showWhen(values)),
        );
        if (!groupFields.length) return null;

        return (
          <section key={group.id}>
            {/* Section heading keeps a long form navigable */}
            <div className="mb-3 border-b border-surface-border pb-2">
              <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-strong">
                {group.emoji ? (
                  <span aria-hidden="true" className="text-sm leading-none">
                    {group.emoji}
                  </span>
                ) : null}
                {t(group.label)}
              </h3>
              {group.hint ? <p className="mt-0.5 text-xs text-muted">{t(group.hint)}</p> : null}
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              {groupFields.map((field) => (
                <Field
                  key={field.name}
                  field={field}
                  value={values[field.name]}
                  onChange={(next) => set(field.name, next)}
                  fileOptions={
                    field.type === "file"
                      ? inputs.filter((item) => field.accepts.includes(item.extension))
                      : []
                  }
                />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
