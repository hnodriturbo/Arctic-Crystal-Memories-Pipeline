# Arctic Crystal Memories — Company Context

Version: 1.3
Company: Arctic Crystal Memories ehf (formerly Crystal Clear Memories)
Business type: K9 optical crystal keepsakes using subsurface laser engraving (SSLE)
Location: Iceland

This file is the shared company context document. It is copied into all three repositories
so any agent working in any of them understands the business, the customer, and the rules.
It is not a technical reference — technical detail lives in each project's own README and docs.

---

## Company Identity

Arctic Crystal Memories is an Iceland-based company selling personalised and premade K9
optical crystal products using subsurface laser engraving. The product should feel premium,
emotional, clear, and trustworthy — Iceland-connected where relevant. Suitable for locals,
tourists, families, pet owners, memorial customers, gift buyers, and businesses.

The goal is not to look like a generic souvenir shop or dropshipping store. The goal is a
serious local brand with strong product quality and a professional customer experience.

---

## Business Goal

The long-term goal is to become one of Iceland's leading custom crystal product businesses,
serving direct retail customers first, and later business/reseller partners (B2B). Retail
comes before B2B — retail already has enough legal complexity (consumer protection, GDPR,
payment, returns). B2B introduces a separate and additional legal layer. Both will be built,
but not at the same time.

The physical Icelandic operation remains the center of quality control, product handling,
customer service, and brand trust.

---

## Customer Groups

**Direct retail customers** order personalised crystals online or locally. They need easy
product selection, clear image upload guidance, trustworthy checkout, strong mobile
experience, clear delivery expectations, and product previews where practical.

**Business / reseller partners** (B2B — planned later) are tourist shops or retail
businesses buying premade inventory. They need wholesale pricing, a premade product catalog,
bulk ordering, partner access, and a reorder workflow. B2B must not disrupt the retail
customer experience.

---

## Products

- Photo and portrait crystals — family, couples, weddings, pets, confirmations, graduations,
  down to keychain size
- Icelandic landmarks and tourist souvenirs — people at famous Icelandic locations, landmarks
  in full 3D
- Corporate gifts, awards, trophies
- Specialty crystal shapes, LED bases and illuminated stands, premium gift boxes and packaging

2D engraving suits landscapes, logos, flat artwork, and background-heavy photos. 3D engraving
suits portraits, pets, people, and buildings where depth adds emotional and visual value.

---

## Production Workflow

```
customer image
  → preserve original without modification
  → convert to PNG if needed
  → local image quality review
  → optional enhancement / upscaling / background removal
  → prepared upload file
  → conversion software (2D-to-3D)
  → preview / approval / production handoff
  → finished K9 crystal product
```

**Conversion software:** Most SSLE printers ship with their own dedicated computer and
2D-to-3D conversion software pre-installed — this is standard with machine purchase and is
an attractive quality of SSLE machines. Cockpit3D is a known standalone option and remains
available. Whichever software is in use, it handles the point-cloud conversion, 3D preview,
and printer handoff. Local pipeline work focuses on image preparation only.

CAD/DXF conversion in the pipeline project is for inspection and viewing, not a replacement
for the production conversion workflow.

---

## The Three Repositories

Each repository has a focused scope. All work is local-first; GitHub is version backup.

**k9_crystal_pipeline** (currently `K9-Crystal-Pipeline` on GitHub — rename pending)
Local image preparation pipeline. Handles PNG conversion, enhancement, upscaling, background
removal, and export of clean files ready for the conversion software. Also converts CAD/DXF
files to readable inspection formats. Includes a local Next.js operator UI.

**k9_crystal_website** (currently `K9-Crystal-Website` on GitHub — rename pending)
Customer-facing ecommerce website. Contains Next.js design prototypes being compared before
the final production direction is chosen. Covers product catalog, customer image upload flow,
order customisation, cart, checkout, admin portal, and a future B2B reseller portal.

**k9_crystal_company** (currently `K9-Crystal-Company` on GitHub — rename pending)
Business documents, research, and planning. Business plan, machine and crystal vendor
research, packaging, logistics, pricing, financing, and advisor materials.

Folder and file names across all repositories follow `snake_case` for folders and
`kebab-case` for files. Repository names are being migrated to match.

---

## Git and File Safety

- Do not push to GitHub unless the owner explicitly asks.
- Do not commit private customer data, secrets, payment details, or real production files.
- Payment is always handled by a payment gateway — the customer is redirected there and
  returns with success or error data. Payment details are never stored or committed.
- Keep generated pipeline input/output folders, 3D scene files, and video files local-only.
- Useful product and business reference images can be tracked when reasonably sized.
- Do not create pull requests or branches unless explicitly asked.

---

## Agent Rules

- Work locally first. Do not push, PR, or branch unless explicitly asked.
- Keep responsibilities separated between repositories.
- Prefer minimal patches. Do not overbuild before real sales workflows are proven.
- Preserve original customer files — never replace an original with a processed copy.
- No emoji in code comments unless explicitly requested.
- `snake_case` for folders, `kebab-case` for files — always, across all projects.
- JavaScript/JSX only in web projects. No TypeScript unless explicitly requested.

---

## Current Non-Goals

- Building a local replacement for the conversion software.
- Treating local mesh/point-cloud generation as the production path.
- Building the public ecommerce store inside the local operator UI.
- Committing real customer images or private order data.
- Starting B2B portal work before the retail-facing side is proven.
- Overbuilding systems before the first real sales workflow is validated.

**Current priority:** prepare images → conversion software → produce crystals → sell and learn → improve from real data.
