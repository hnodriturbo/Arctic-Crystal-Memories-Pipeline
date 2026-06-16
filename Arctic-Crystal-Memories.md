# Arctic Crystal Memories - Unified Project Notes

Version: 1.2
Status: Active shared context
Company: Arctic Crystal Memories ehf (formerly Crystal Clear Memories)
Business type: K9 optical crystal keepsakes using subsurface laser engraving
Location: Iceland

---

## Chapters

- [Arctic Crystal Memories - Unified Project Notes](#arctic-crystal-memories---unified-project-notes)
  - [1. Company Identity](#1-company-identity)
  - [2. Business Goal](#2-business-goal)
  - [3. Current Production Strategy](#3-current-production-strategy)
  - [4. The Three Project Workspaces](#4-the-three-project-workspaces)
  - [5. Current Repository Structure](#5-current-repository-structure)
  - [6. Project 1 - Pipeline + Web](#6-project-1---pipeline--web)
  - [7. Project 2 - Website Store](#7-project-2---website-store)
  - [8. Project 3 - Company Information and Documents](#8-project-3---company-information-and-documents)
  - [9. Customer Groups](#9-customer-groups)
  - [10. Product Direction](#10-product-direction)
  - [11. Operational Direction](#11-operational-direction)
  - [12. Quality Philosophy](#12-quality-philosophy)
  - [13. Documentation Rules](#13-documentation-rules)
  - [14. Git and File Safety Rules](#14-git-and-file-safety-rules)
  - [15. Agent Rules Across All Projects](#15-agent-rules-across-all-projects)
  - [16. Current Non-Goals](#16-current-non-goals)

---

## 1. Company Identity

Arctic Crystal Memories is an Iceland-based K9 optical crystal keepsake company.

The business sells personalized and premade crystal products using subsurface laser engraving technology.

The product should feel:

- Premium.
- Emotional.
- Clear and trustworthy.
- Iceland-connected where relevant.
- Suitable for locals, tourists, families, pet owners, memorial customers, gift buyers, and businesses.

The goal is not to look like a generic souvenir shop or dropshipping store. The goal is to build a serious local brand with strong product quality and professional customer experience.

---

## 2. Business Goal

The long-term goal is to become one of Iceland's leading custom crystal product businesses.

Arctic Crystal Memories should serve:

- Direct online customers.
- Local Icelandic customers.
- Tourists visiting Iceland.
- Gift buyers.
- Wedding, confirmation, graduation, and memorial customers.
- Pet owners.
- Corporate customers.
- Tourist shops and reseller partners.

The physical/local operation should remain the center of quality control, product handling, customer service, and brand trust.

---

## 3. Current Production Strategy

The current strategy is practical and business-first.

```text
Customer image
  -> preserve original
  -> convert to PNG if needed
  -> local image quality review
  -> optional enhancement/upscale/background removal
  -> prepared upload file
  -> Cockpit3D or vendor production workflow
  -> preview/approval/production handoff
  -> finished K9 crystal product
```

Important direction:

- Local work focuses on image preparation and conversion.
- Cockpit3D or the selected vendor workflow handles professional point-cloud, mesh, 3D preview, and printer handoff.
- CAD/DXF conversion is for inspection, viewing, and future manual review, not for replacing the production workflow.
- The business priority is launch readiness, website/customer flow, image upload quality, supplier decisions, and sales operations.

---

## 4. The Three Project Workspaces

There are three related but separate local repositories.

| Repository             | Main purpose                                                                                  | Primary context file |
| ---------------------- | --------------------------------------------------------------------------------------------- | -------------------- |
| `K9-Crystal-Pipeline/` | Local image preparation, PNG conversion, CAD/DXF inspection conversion, operator UI.          | `README.md`          |
| `K9-Crystal-Website/`  | Public ecommerce site, customer upload flow, B2B/reseller portal planning.                    | `README.md`          |
| `K9-Crystal-Company/`  | Business plan, supplier research, machine research, logistics, pricing, financing, documents. | `README.md`          |

`Arctic-Crystal-Memories.md` is the shared company explanation copied into all three folders.

Each project keeps its own focused `README.md` so agents do not mix responsibilities.

---

## 5. Current Repository Structure

This structure is intentionally high-level. It lists the important working folders without expanding dependency folders such as `node_modules/`, build output such as `.next/`, virtual environments, or `.git/` internals.

### K9-Crystal-Pipeline

```text
K9-Crystal-Pipeline/
├── .gitattributes
├── .gitignore
├── K9-Crystal-Pipeline.code-workspace
├── Arctic-Crystal-Memories.md
├── README.md
├── docs/
│   └── pipelines_md_helpers/
├── pipeline/
│   ├── code/
│   ├── input/      # local only, ignored by Git
│   ├── models/     # local only, ignored by Git
│   └── output/     # local only, ignored by Git
├── pipeline-converter/
├── pipeline-old/
└── web/
    ├── prisma/
    ├── public/
    └── src/
```

### K9-Crystal-Website

```text
K9-Crystal-Website/
├── .gitattributes
├── .gitignore
├── K9-Crystal-Website.code-workspace
├── Arctic-Crystal-Memories.md
├── README.md
├── AI-Generated-Images/
│   └── Arctic_Style/
├── web-sample-1/
│   ├── public/
│   └── src/
├── web-sample-2/
│   ├── public/
│   └── src/
└── web-sample-3/
    ├── public/
    └── src/
```

### K9-Crystal-Company

```text
K9-Crystal-Company/
├── .gitattributes
├── .gitignore
├── K9-Crystal-Company.code-workspace
├── Arctic-Crystal-Memories.md
├── README.md
├── CLAUDE.md
├── 3d_files/       # local only, ignored by Git
├── business_plan/
├── docs/
│   ├── Business_Plans_-_Old/
│   ├── Creation_of_Business_EHF/
│   ├── brainstorming/
│   └── older_docs_&_research/
├── images/
│   ├── Images_For_Crystals/
│   ├── Pictures_Of_My_Crystal_&_Packaging/
│   ├── Printer_Company_Samples/
│   ├── Product_Samples/
│   └── Product_Shapes_From_3dCrystal.com/
├── printers_&_crystals/
│   ├── crystals/
│   └── printers/
├── research/
└── videos/         # local only, ignored by Git
```

---

## 6. Project 1 - Pipeline + Web

Repository/workspace:

```text
K9-Crystal-Pipeline/
├── README.md
├── Arctic-Crystal-Memories.md
├── docs/
├── pipeline/
├── pipeline-converter/
├── pipeline-old/
└── web/
```

Purpose:

- Prepare customer images before upload to Cockpit3D/vendor workflow.
- Convert all usable image formats to `.png` while preserving quality and transparency where possible.
- Run optional enhancement, upscaling, and background removal.
- Export clean prepared files for upload.
- Convert `.cad` and `.dxf` files into readable inspection formats such as `.xyz`, `.ply`, `.obj`, and later `.stl` where valid.
- Provide a local Next.js operator UI for running and previewing pipeline tasks.

Folder roles:

| Folder                | Role                                                                                                                   |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `docs/`               | Pipeline documentation, old instructions, and setup/research notes.                                                    |
| `pipeline/`           | Image enhancement, upscaling, background removal, prepared upload exports.                                             |
| `pipeline-converter/` | Image-to-PNG conversion plus CAD/DXF inspection conversion.                                                            |
| `pipeline-old/`       | Older experiments or reference material; do not treat as the active production path without checking `README.md`.      |
| `web/`                | Local operator interface that runs and previews pipeline tasks.                                                         |

The `web/` folder here is not the final public ecommerce store.

---

## 7. Project 2 - Website Store

Repository/workspace:

```text
K9-Crystal-Website/
├── README.md
├── Arctic-Crystal-Memories.md
├── web-sample-1/
├── web-sample-2/
└── web-sample-3/
```

Purpose:

- Build and compare professional Next.js ecommerce skeletons.
- Choose the best direction for the final customer-facing website.
- Design the future customer upload and ordering experience.
- Plan future B2B/reseller partner functionality.

The final website should eventually support:

- Product catalog.
- Product detail pages.
- Crystal size and shape selection.
- Customer image upload.
- Image quality guidance.
- Cart and checkout.
- Order customization.
- Admin production queue.
- Customer approval/proof workflow where practical.
- Icelandic and English content.
- B2B reseller portal.
- Wholesale pricing and partner-specific visibility.

Current sample directions:

| Sample         | Direction                             |
| -------------- | ------------------------------------- |
| `web-sample-1` | Premium luxury ecommerce.             |
| `web-sample-2` | Tourist/gift-shop focused storefront. |
| `web-sample-3` | Alternative direction under evaluation. |

Design should emphasize emotional value first, technical SSLE quality second.

---

## 8. Project 3 - Company Information and Documents

Repository/workspace:

```text
K9-Crystal-Company/
├── README.md
├── Arctic-Crystal-Memories.md
├── 3d_files/
├── business_plan/
├── docs/
├── images/
├── printers_&_crystals/
├── research/
└── videos/
```

Purpose:

- Maintain and improve the business plan.
- Research SSLE machines.
- Research K9 crystal blanks, accessories, packaging, and suppliers.
- Compare shipping and import options to Iceland.
- Track startup costs, financing needs, pricing assumptions, and decision logs.
- Produce documents, spreadsheets, presentations, and advisor-ready materials when needed.

Research tracks:

| Track                 | Purpose                                                                                   |
| --------------------- | ----------------------------------------------------------------------------------------- |
| SSLE machines         | Compare machine quality, speed, software, support, warranty, weight, and landed cost.     |
| Crystal vendors       | Compare blank crystal quality, shapes, sizes, MOQ, pricing, packaging, and reliability.   |
| Accessories/packaging | Compare LED bases, gift boxes, keychains, display items, and premium packaging.           |
| Shipping/logistics    | Compare freight, customs, Icelandic import handling, VAT implications, and delivery risk. |
| Business documents    | Business plan, financing documents, pricing sheets, launch planning, advisor materials.   |

Shipping and logistics are critical because crystal inventory and SSLE machines are heavy. Landed cost, VAT handling, customs, delivery time, and supplier reliability must be treated as business-critical variables.

---

## 9. Customer Groups

The business has two major customer groups.

### Direct retail customers

These customers order personalized crystal products directly.

Needs:

- Easy product selection.
- Clear image upload instructions.
- Trustworthy checkout.
- Strong mobile experience.
- Clear delivery/pickup expectations.
- Product previews or proofs when practical.

### Business / reseller partners

These customers are tourist shops or retail partners buying premade inventory for resale.

Needs:

- Wholesale pricing.
- Premade product catalog.
- Bulk ordering.
- Partner-specific access.
- Reorder workflow.
- Clear packaging and display options.

The long-term platform should be designed so B2B functionality can grow without damaging the normal retail customer experience.

---

## 10. Product Direction

Primary product categories:

- Portrait crystals.
- Family and couple crystals.
- Wedding, confirmation, and graduation gifts.
- Pet crystals and memorial items.
- Iceland landmark crystals.
- Tourist souvenir crystals.
- Corporate gifts.
- Awards and trophies.
- Crystal keychains.
- Specialty crystal shapes.
- LED bases and illuminated stands.
- Premium gift boxes and packaging.

2D products are useful for landscapes, logos, flat artwork, and background-heavy photos.

3D products are useful for portraits, pets, people, buildings, and premium keepsakes when depth adds emotional value.

---

## 11. Operational Direction

The company needs practical operating systems for:

- Image intake.
- Image quality review.
- Customer communication.
- Product catalog management.
- Supplier tracking.
- Inventory tracking.
- Pricing and margin calculations.
- Order status tracking.
- Production checklists.
- Quality-control checklists.
- Finished product photography.
- Marketing content.

At early stage, these may be Markdown files, spreadsheets, Shopify tools, or small custom systems. Do not overbuild before sales and supplier workflows are clearer.

---

## 12. Quality Philosophy

Quality is the main competitive advantage.

The business should not blindly automate quality decisions.

Human review remains responsible for:

- Whether the customer image is good enough.
- Whether enhancement helps or damages the image.
- Whether background removal is clean enough.
- Whether the prepared upload file is production-ready.
- Whether Cockpit3D/vendor output looks acceptable.
- Whether the final crystal product is centered, clean, visible, and correctly packaged.

Technology assists the artist/operator. It does not replace final judgment.

---

## 13. Documentation Rules

Use `README.md` as the source of truth inside each specific project.

Use `Arctic-Crystal-Memories.md` as shared company context across all related folders.

Avoid using `INSTRUCTIONS.md` as the main project-memory file for this company workflow unless an external tool specifically requires that filename.

Documentation should be:

- Short enough for an agent to actually read.
- Specific to the project folder.
- Updated when business direction changes.
- Clear about what is active, what is legacy, and what is out of scope.

---

## 14. Git and File Safety Rules

These repositories are local-first. GitHub is backup/version history and should only receive manually selected local changes.

General rules:

- Do not push to GitHub unless the owner explicitly asks.
- Do not commit private customer data, secrets, payment details, login data, or real production files.
- Keep generated pipeline input/output folders local.
- Keep `3d_files/` local because CAD, Cockpit3D, scene, mesh, and point-cloud files can become too large.
- Keep `videos/` local because video files are not needed in GitHub history.
- Keep useful product and business reference images tracked when they are reasonably sized.

The `.gitignore` files should protect heavy local folders and common generated files. The `.gitattributes` files should continue marking binary file types correctly so Git does not treat documents, images, archives, or binaries as text.

---

## 15. Agent Rules Across All Projects

- Work locally first.
- Do not push to GitHub unless explicitly asked.
- Do not create pull requests unless explicitly asked.
- Prefer minimal patches.
- Keep project responsibilities separated.
- Do not mix website-store work into the pipeline project.
- Do not mix supplier research into the website project.
- Do not treat old point-cloud/mesh experiments as active production strategy.
- Use modern package versions where practical.
- Do not downgrade packages only to force compatibility.
- Preserve original customer files.
- Never commit private customer data, secrets, payment details, login data, or real production files.
- Use clear comments in code.
- Do not use emoji in code comments unless explicitly requested.

---

## 16. Current Non-Goals

These are not current priorities:

- Building a full local replacement for Cockpit3D.
- Maintaining many depth-map, point-cloud, or mesh-generation pipelines.
- Treating local mesh generation as the main production path.
- Building the public ecommerce store inside the local operator UI.
- Committing real customer images or private order data.
- Overbuilding enterprise systems before the first real sales workflow is proven.

Current priority:

```text
prepare images professionally -> upload through Cockpit3D/vendor workflow -> produce crystals -> sell and learn -> improve systems from real business data
```
