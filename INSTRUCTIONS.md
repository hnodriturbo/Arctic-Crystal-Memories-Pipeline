<!--
File: INSTRUCTIONS.md
Purpose:
 - Define the current direction, business context, and development rules for the K9 Crystal Company project.
 - Keep this repository aligned with the updated Cockpit3D-based production workflow.
-->

# K9 Crystal Company Instructions

Version: 2.0
Status: Active
Primary Focus: Crystal Clear Memories business development, image-preparation pipeline, Cockpit3D production handoff, and local web tooling.

---

# Table of Contents

1. Project Identity
2. Current Business Direction
3. New Production Strategy
4. What This Repository Is For
5. What This Repository Is Not For
6. Core Workflow
7. Cockpit3D Role
8. Pipeline Role
9. Web Interface Role
10. Ecommerce Direction
11. Business Plan Context
12. Product Categories
13. Customer Markets
14. Marketing and Sales Channels
15. Operations and Inventory
16. Quality Standards
17. File and Data Rules
18. Repository Structure Direction
19. Legacy Pipeline Policy
20. Development Rules
21. Documentation Rules
22. Future Expansion
23. Project Memory Rules

---

# 1. Project Identity

This repository currently exists as `K9-Crystal-Pipeline`.

The planned project identity is:

```text
K9-Crystal-Company
```

The new name better reflects the actual purpose of the folder. This project is no longer only a technical experiment for generating meshes from images. It is becoming the main local workspace for building the Crystal Clear Memories company systems.

The project should support:

- The Crystal Clear Memories business plan.
- The local image-preparation pipeline.
- A local web interface for preparing customer images.
- Research and documentation for K9 crystal production.
- Future business tools, marketing assets, and operational workflows.

The company-facing brand is:

```text
Crystal Clear Memories
```

The technical folder/repository name may remain `K9-Crystal-Company` while the customer-facing business name remains `Crystal Clear Memories`.

---

# 2. Current Business Direction

Crystal Clear Memories will create personalized K9 optical crystal keepsakes using subsurface laser engraving technology.

The business will sell premium crystal products where customer images, Icelandic memories, family moments, pets, weddings, confirmations, portraits, landmarks, and special events are engraved inside high-quality K9 optical crystals.

The product is not just a souvenir. It is an emotional keepsake designed to preserve memories permanently inside crystal.

Important business themes:

- Premium personalized gifts.
- Tourist souvenirs from Iceland.
- Icelandic family and event gifts.
- Durable products that do not fade or wear away.
- Luxury packaging and presentation.
- 2D crystal engravings for landscape and background-heavy images.
- 3D crystal engravings for portraits, people, pets, buildings, objects, and selected premium products.

The company goal is to become one of Iceland's leading providers of custom crystal engraving products.

---

# 3. New Production Strategy

The previous project direction focused heavily on building a full internal image-to-depth-to-point-cloud-to-mesh pipeline.

That is no longer the primary production strategy.

After new business discoveries and a meeting with a salesperson from Cockpit3D Solutions, the updated strategy is:

1. Prepare the customer image locally.
2. Optionally upscale the image.
3. Optionally remove the background.
4. Upload/import the prepared image into the Cockpit3D website/workspace using the owner's special access.
5. Use Cockpit3D to create, preview, and finalize the point cloud and mesh.
6. Export a Cockpit3D production file, including `.cockpit` where applicable.
7. Export or send the final mesh/production output directly to the printer, or save it to file and then print.

Cockpit3D is now the specialized production system for point cloud creation, mesh generation, 3D preview, and printer handoff.

This project should focus on what we can control best locally:

- Image enhancement.
- Image cleanup.
- Background removal.
- Upscaling.
- Operator workflow.
- Business website planning.
- Company documentation.
- Advertising and sales systems.
- Integration notes for Cockpit3D.

The local code should not try to compete with Cockpit3D's specialized 3D conversion pipeline unless there is a clear future reason to research a fallback.

---

# 4. What This Repository Is For

This repository is the local working hub for the K9 crystal company project.

It should contain or coordinate:

- The final focused image-preparation pipeline.
- The local Next.js web interface inside `web/`.
- Business documentation and planning.
- Cockpit3D handoff notes.
- Production workflow documentation.
- Advertising, website, and launch planning material.
- References for crystal products, pricing, suppliers, machines, and operations.

The repository should help answer practical business questions:

- How do we prepare a customer image before Cockpit3D?
- What optional enhancement steps should the operator choose?
- What file should be uploaded to Cockpit3D?
- What quality checks happen before and after Cockpit3D?
- What products are we selling?
- How does the website collect customer orders and images?
- How do we move from Shopify to a custom ecommerce system later?

---

# 5. What This Repository Is Not For

This repository should no longer be treated as the primary place to build a complete replacement for Cockpit3D.

Do not prioritize new internal systems for:

- Full production point cloud generation.
- Full production mesh creation.
- Internal SSLE printer file generation.
- Rebuilding Cockpit3D features.
- Maintaining many competing 3D reconstruction pipelines.

Old pipeline research may remain useful as reference material, but it should not control the current project direction.

The main production solution is now Cockpit3D.

---

# 6. Core Workflow

The current production workflow should be documented and built around this sequence:

```text
Customer image
  -> local quality review
  -> optional upscaling
  -> optional background removal
  -> optional image cleanup/export
  -> upload/import into Cockpit3D workspace
  -> Cockpit3D point cloud, mesh, preview, and editing
  -> finalized Cockpit3D output
  -> .cockpit file or supported production export
  -> printer handoff
  -> finished K9 crystal product
```

The local pipeline should end at the prepared image stage.

The Cockpit3D workflow should take over after the prepared image is ready.

---

# 7. Cockpit3D Role

Cockpit3D is now the professional production system for:

- AI-assisted 2D-to-3D conversion.
- Point cloud generation.
- Mesh creation.
- Viewing and checking the point cloud.
- Viewing and checking the mesh.
- Creating or exporting Cockpit3D production files.
- Exporting `.cockpit` files where applicable.
- Sending output to a printer or saving output for printer use.

Cockpit3D should be treated as a core business tool, not as an optional experiment.

Important notes:

- Use the owner's special access to the Cockpit3D website/workspace.
- Upload prepared customer images after optional local enhancement.
- Do final point cloud and mesh decisions inside Cockpit3D.
- Use Cockpit3D preview tools as a required production quality checkpoint.
- Document any reliable Cockpit3D settings, export options, file behavior, and printer handoff steps discovered during real use.

Do not store private login details, passwords, API tokens, or sensitive account information in this repository.

---

# 8. Pipeline Role

The final local pipeline should be based on `pipeline-03-pro`, but it should be renamed conceptually and eventually physically to:

```text
pipeline
```

The future `pipeline/` folder should be the only active local image-preparation pipeline.

Its purpose is limited and practical:

- Import a customer image.
- Preserve the original.
- Optionally upscale the image.
- Optionally remove the background.
- Optionally clean or normalize the image for Cockpit3D upload.
- Export a prepared image file.
- Keep a simple run record of what was done.

The pipeline should not need to generate the final production mesh anymore.

The local pipeline may keep old scripts temporarily while the project transitions, but the long-term goal is a smaller, cleaner pipeline focused on image preparation only.

Recommended active stages:

1. Source image intake.
2. Quality review metadata.
3. Optional upscaling.
4. Optional background removal.
5. Optional export presets for Cockpit3D upload.
6. Operator notes and output logging.

Optional future stages:

- Manual crop assistant.
- Image brightness/contrast presets.
- Face/subject centering helper.
- Before/after comparison.
- Export package builder for Cockpit3D.

---

# 9. Web Interface Role

The `web/` folder contains an installed Next.js project using JavaScript.

This web app should become the local operator interface for the focused pipeline.

It should not try to become a full public ecommerce website unless explicitly moved in that direction later.

The local web interface should help the operator:

- Upload or choose a source image.
- View the original image.
- Choose optional upscaling.
- Choose optional background removal.
- Preview results.
- Compare before and after images.
- Export the prepared image for Cockpit3D.
- Keep track of the current run.
- Avoid needing terminal commands for normal preparation work.

The web app should always target the active `pipeline` workflow once `pipeline-03-pro` is renamed or replaced.

For now, if the folder still exists as `pipeline-03-pro`, code may reference it carefully during transition. Future code should be designed so the active pipeline folder can be renamed to `pipeline` without a large rewrite.

Important web rules:

- Use JavaScript, not TypeScript, unless the project direction changes.
- Preserve the existing Next.js structure.
- Keep the UI practical and operator-focused.
- Do not build a marketing landing page as the first screen of the local tool.
- Make the first screen useful for image preparation.
- Keep controls clear: upload, upscale option, background removal option, preview, export.

---

# 10. Ecommerce Direction

Crystal Clear Memories will need a customer-facing ecommerce website.

The first practical business launch may use Shopify because it is faster for:

- Product listings.
- Checkout.
- Payment processing.
- Order management.
- Basic customer communication.
- Early sales validation.

The premium long-term direction is a custom-built website because it is fully modifiable and provides valuable web development practice.

The custom ecommerce site should eventually support:

- Crystal product catalog.
- Product sizes and shapes.
- Customer image upload.
- Icelandic and English language support.
- Mobile-first ordering.
- Payment options such as card payments, Apple Pay, and Google Pay.
- Order tracking or internal production status.
- Customer proof or preview workflow if practical.

Important repository note:

The ecommerce project may eventually live in its own repository or its own folder outside this project. It may also have its own `INSTRUCTIONS.md`.

Do not assume the root `web/` folder is the final ecommerce site. At the time of this instruction rewrite, `web/` is primarily the local pipeline/operator interface.

---

# 11. Business Plan Context

The business context comes from:

- `Crystal_Clear_Memories_Main_Business_Plan.docx`
- `Crystal_Clear_Memories_Icelandic_Business_Plan.docx`

Both documents describe the same business direction in English and Icelandic.

Key business facts from the plans:

- Business name: Crystal Clear Memories.
- Owner: Hreidar Petursson.
- Product: Personalized K9 optical crystal keepsakes.
- Production method: Subsurface laser engraving.
- Target customers: Tourists, Icelanders, families, couples, pet owners, event buyers, corporate customers, and gift buyers.
- Example products: Crystal blocks, keychains, specialty shapes, LED bases, illuminated stands, and accessories.
- Average selling price assumption: about 15,000 ISK.
- Estimated COGS assumption: about 1,690 ISK per unit.
- Estimated gross margin before operating costs: about 88.7%.
- Initial inventory idea: about 1,000 units in mixed sizes.
- Reorder level idea: around 400 units remaining.
- Supplier direction: bulk crystal and packaging imports from China.
- Startup financing idea: 5,000,000 ISK or 7,000,000 ISK personal loan.
- Marketing focus: Facebook, Instagram, TikTok, Google Ads, YouTube, tourist retail partnerships, and future airport placement.
- Website direction: Shopify first, custom platform later.

These numbers are planning assumptions, not guaranteed results. Always treat them as business planning material that may need revision as supplier quotes, machine costs, taxes, rent, advertising costs, and real sales data become clearer.

---

# 12. Product Categories

Primary product categories:

- K9 crystal blocks from small sizes to larger display pieces.
- Portrait crystals.
- Family and couple crystals.
- Wedding crystals.
- Confirmation and graduation gifts.
- Pet memorial and pet portrait crystals.
- Iceland landmark crystals.
- Tourist souvenir crystals.
- Corporate gifts.
- Awards and trophies.
- Crystal keychains.
- Specialty crystal shapes.
- LED bases and illuminated stands.
- Padded luxury presentation boxes.

2D products are especially useful for:

- Landscapes.
- Icelandic landmarks with backgrounds.
- Group photos where depth may not be useful.
- Flat artwork.
- Logos.

3D products are especially useful for:

- Portraits.
- People.
- Pets.
- Buildings.
- Objects.
- Premium keepsakes where depth increases emotional impact.

---

# 13. Customer Markets

Main markets:

- Tourists visiting Iceland.
- Icelandic families.
- Parents buying gifts.
- Couples and wedding customers.
- Pet owners.
- Memorial customers.
- Corporate clients.
- Tourist shops and retail partners.
- Gift buyers looking for something more personal than a normal souvenir.

Tourism angle:

Customers can take Iceland home with them as a crystal memory, not only as a photo or ordinary souvenir.

Family angle:

Customers can preserve personal moments such as first steps, confirmations, weddings, loved ones, and pets in a product designed to last for generations.

---

# 14. Marketing and Sales Channels

The business should develop marketing around three main channels:

1. Direct ecommerce sales.
2. Digital advertising.
3. Retail and tourist partnerships.

Important advertising platforms:

- Facebook.
- Instagram.
- TikTok.
- Google Ads.
- YouTube.

Important sales opportunities:

- Shopify launch store.
- Custom ecommerce site later.
- Tourist shops in Reykjavik.
- Golden Circle retail locations.
- Akureyri and North Iceland tourist locations.
- Partnerships with existing tourism businesses.
- Long-term goal of placement or agreement at Keflavik International Airport.
- Future physical retail location in Reykjavik if business performance supports it.

Marketing content should show:

- The finished crystal product clearly.
- The emotional value of the gift.
- Before/after transformation from photo to crystal.
- Iceland landmark examples.
- Family, pet, wedding, and memorial use cases.
- Luxury packaging and LED base presentation.

---

# 15. Operations and Inventory

Operational assumptions from the business plan:

- Start with a mixed inventory of approximately 1,000 crystal products and packaging.
- Track sizes, shapes, and product types carefully.
- Reorder when inventory drops to around 400 units.
- Expect approximately 30 days for manufacturing and shipping from China, depending on supplier and shipping method.
- Maintain enough stock to avoid missed orders.
- Avoid over-committing money to slow-moving inventory before real sales data exists.

Operational systems eventually needed:

- Inventory tracker.
- Supplier quote tracker.
- Product SKU list.
- Packaging tracker.
- Order status tracker.
- Production checklist.
- Quality-control checklist.
- Customer communication templates.
- Advertising performance tracker.

These may be spreadsheets, markdown documents, Shopify tools, or custom software depending on the stage of the company.

---

# 16. Quality Standards

Quality is the main competitive advantage.

Every customer image should be reviewed before production.

Local image-preparation quality checks:

- Is the original image high enough resolution?
- Is the subject sharp?
- Is the face or main subject clear?
- Is lighting acceptable?
- Is there motion blur?
- Is the background suitable, or should it be removed?
- Would upscaling improve the Cockpit3D result?
- Does the background removal preserve hair, fur, clothing, and edges?
- Is the final prepared image clean enough to upload?

Cockpit3D quality checks:

- Does the generated point cloud look correct?
- Does the mesh or 3D preview preserve the subject?
- Is the subject centered and scaled correctly?
- Does the depth look natural?
- Is the file ready for the selected crystal size?
- Is the final output suitable for printing?

Finished product quality checks:

- Is the engraving centered?
- Is the image visible from normal viewing angles?
- Is the crystal clean and undamaged?
- Is the packaging correct?
- Does the final product match the customer's order?

Do not trade quality away for speed during early business development.

---

# 17. File and Data Rules

Always preserve original customer images.

Never overwrite originals.

Use separate locations for:

- Source images.
- Upscaled images.
- Background-removed images.
- Prepared Cockpit3D upload files.
- Cockpit3D exported files.
- Printer-ready files.
- Finished product photos.
- Notes and run logs.

Recommended local workflow folder idea:

```text
pipeline/
  input/
  output/
    upscaled/
    bg_removed/
    prepared_for_cockpit3d/
    logs/
```

Sensitive customer data should be handled carefully.

Do not commit private customer photos, private orders, login information, payment information, or personal customer details to the repository.

Use `.gitignore` rules for real customer files and generated production outputs when needed.

---

# 18. Repository Structure Direction

Current important folders:

```text
web/                 Local Next.js operator interface.
pipeline-03-pro/     Current best pipeline folder; should become the active image-preparation pipeline.
pipeline-01-*        Older research pipeline.
pipeline-02-*        Older ZoeDepth research pipeline.
Markdown_Helpers/    Documentation and setup notes.
py_step_files/       Script/reference copies.
```

Target direction:

```text
K9-Crystal-Company/
  INSTRUCTIONS.md
  README.md
  business/
  docs/
  pipeline/
  web/
  references/
```

Possible future meaning:

- `business/`: Business plans, pricing, launch notes, marketing planning, supplier notes.
- `docs/`: Project documentation and operator guides.
- `pipeline/`: Active local image-preparation pipeline.
- `web/`: Local operator UI for the pipeline.
- `references/`: Research notes, SSLE information, Cockpit3D notes, machine notes.

Do not reorganize everything at once unless the user explicitly asks for a cleanup pass.

Prefer gradual, safe restructuring.

---

# 19. Legacy Pipeline Policy

Older pipelines are valuable as research history, but they are no longer the business-critical production path.

Legacy folders may contain useful code for:

- Upscaling.
- Background removal.
- Image preparation.
- File handling.
- Experiment records.
- SSLE research.

Legacy folders should not drive new architecture unless their code is being reused intentionally.

The active future pipeline should be simple, focused, and Cockpit3D-oriented.

When changing pipeline code:

- Prefer adapting `pipeline-03-pro` into `pipeline`.
- Remove or disable mesh/depth stages only after confirming they are no longer needed.
- Keep old code available as reference until the new focused workflow is stable.
- Update documentation whenever the active workflow changes.

---

# 20. Development Rules

Work locally first.

Do not push to GitHub unless the user explicitly says to push.

Preserve the user's local-first workflow.

When making changes:

- Inspect the current structure first.
- Make focused edits.
- Preserve existing project conventions.
- Avoid unnecessary rewrites.
- Explain important commands before running them.
- Do not change unrelated files.
- Keep JavaScript for Next.js work unless explicitly told otherwise.
- Use clear file comments when creating new files.
- Keep documentation practical and readable.

For the local web app:

- Keep the interface useful for the operator.
- Build the image-preparation workflow first.
- Avoid unnecessary marketing-page design inside the operator tool.
- Support optional steps instead of forcing every image through every process.
- Make output easy to inspect before Cockpit3D upload.

For the pipeline:

- Keep the source image safe.
- Make enhancement steps optional.
- Keep outputs organized.
- Prefer predictable file names.
- Make logs understandable.
- Keep Cockpit3D handoff as the end of the local workflow.

---

# 21. Documentation Rules

This root `INSTRUCTIONS.md` is the project-level source of truth.

It should describe:

- Business direction.
- Production strategy.
- Repository purpose.
- Workflow philosophy.
- Major folder roles.
- Long-term project decisions.

Detailed guides should live closer to the work:

- `web/INSTRUCTIONS.md` for the local Next.js operator interface.
- `pipeline/README.md` or `pipeline/pipeline-guide.md` for practical pipeline usage.
- Business documents for financing, marketing, sales, and launch planning.
- Cockpit3D notes for exact upload/export/preview/printer handoff steps.

When important project knowledge changes, update the relevant documentation instead of relying on memory.

---

# 22. Future Expansion

Likely future additions:

- Rename repository folder to `K9-Crystal-Company`.
- Rename or rebuild `pipeline-03-pro` as `pipeline`.
- Simplify the pipeline to image preparation only.
- Update `web/` to use the focused `pipeline`.
- Create a Cockpit3D handoff guide.
- Create a Shopify launch checklist.
- Create a custom ecommerce architecture plan.
- Create product catalog documentation.
- Create pricing calculators.
- Create ad campaign planning documents.
- Create inventory and supplier tracking tools.
- Create a production checklist for each order.

Potential custom ecommerce system later:

- Product catalog.
- Customer image upload.
- Checkout integration.
- Icelandic/English language support.
- Admin production queue.
- Order status tracking.
- Customer proof workflow.
- Shopify migration or replacement strategy.

Do not build all future systems before the core business workflow is clear.

Start with the smallest useful system:

```text
prepare image locally -> Cockpit3D production -> print crystal -> sell and learn
```

---

# 23. Project Memory Rules

This file should store project-specific direction whenever possible.

Global memory should remain short.

Update this file when there are important changes to:

- Business strategy.
- Cockpit3D workflow.
- Pipeline scope.
- Web interface scope.
- Ecommerce direction.
- Repository organization.
- Product strategy.
- Production rules.

This document should evolve as the business and technical workflow become clearer.

