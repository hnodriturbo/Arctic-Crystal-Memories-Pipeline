<!--
File: Crystal-Workshop/docs/HANDOFF_VPS_ENDURNEFNING.md
Purpose: Endurnefning acm → ccm á Workshop, bæði staðbundið og á VPS. Þetta á
         að vera sín eigin lota — hún stöðvar þjónustu og snertir slóðir sem
         átta umhverfisbreytur treysta á.
-->

# Workshop: acm → ccm endurnefning

**Þetta á að vera sín eigin lota.** Ekki blanda henni saman við aðra vinnu.
Hún stöðvar keyrandi þjónustu og breytir slóðum sem fjöldi stillinga vísar í.

Ástæðan fyrir að Workshop er viðkvæmastur af þremur vefjunum: hann er ekki
bara Next-app. Undir honum liggja þrjú Python-umhverfi, Blender, Chromium og
vinnusvæði — og **slóðirnar í þau eru harðkóðaðar í umhverfisbreytum**, ekki
reiknaðar út frá staðsetningu appsins.

---

## Það sem brotnar við endurnefningu — VPS

Rótin er `/home/hreidar/apps/acm-pipeline`. Átta breytur í
`shared/.env.production` innihalda hana:

```txt
CONVERTER_ROOT          IMAGE_PIPELINE_ROOT     CLAUDE_DESIGN_ROOT
CONVERTER_PYTHON        IMAGE_PIPELINE_PYTHON   PUPPETEER_CACHE_DIR
MESHY_ROOT              MESHY_PYTHON
```

Auk þeirra:

| Hvað | Hvar |
| --- | --- |
| `cwd` og `script` | `shared/ecosystem.config.cjs` |
| Vistaður ferlalisti | `~/.pm2/dump.pm2` — PM2 man gömlu slóðina eftir endurræsingu |
| `$RemoteRoot` | `scripts/deploy-pipeline-vps.ps1`, sjálfgefið `/home/hreidar/apps/acm-pipeline` |
| Symlink | `current/…/.env.production` → `shared/.env.production` |
| Deild verkfæri | `shared/tools/blender`, `shared/tools/puppeteer`, `shared/venvs/*` |

**Python-sýndarumhverfin þola ekki flutning.** `shared/venvs/*/bin/python`
inniheldur algilda slóð í `pyvenv.cfg` og í shebang hvers skriftuskráar. Eftir
endurnefningu þarf annaðhvort að endurskapa þau eða leiðrétta slóðirnar. Þetta
er það sem gleymist og lætur `/api/convert` deyja löngu seinna.

## Það sem brotnar — staðbundið

Fjórar breytur í **hvorri** skrá, `.env.local` og `.env.development`:

```txt
CONVERTER_ROOT   MESHY_ROOT   IMAGE_PIPELINE_ROOT   CLAUDE_DESIGN_ROOT
```

Allar geyma algilda slóð sem byrjar á rótarmöppunni. `CLAUDE_DESIGN_ROOT` er sú
sem bítur strax: Claude Design síðan finnur engar hannanir og segir
„Ekkert staðbundið enn".

Auk þess:

- Áætluð verkefnakeyrsla **`ACM-Bookkeeping-Expense-R2-Sync`** keyrir
  `run-daily-r2-sync.ps1` úr Workshop og vísar í rótarmöppuna
- Skjáborðsflýtileiðirnar **ACM - Update R2**, **ACM Pipeline**,
  **ACM Web Main**, **ACM Website**, **ACM Company**

## Hýsill og webhook

`workshop.acm.is` → `workshop.ccm.is`. Nýr Meshy-webhook er þegar skráður á
`https://workshop.ccm.is/webhooks/meshy` og nýtt leyndarmál komið í báðar
umhverfisskrár staðbundið — **en er ekki komið á VPS**.

Áður en webhook er talinn virkur: prófa **utan frá**, ekki innan úr VPS.
Innan frá ferðu fram hjá Cloudflare og allt lítur vel út.

```bash
curl -i -X POST https://workshop.ccm.is/webhooks/meshy \
  -H 'Content-Type: application/json' -d '{"id":"probe"}'
```

JSON = komið í gegn. HTML-síða = Cloudflare-áskorun enn á. Sjá athugasemdina
efst í `src/app/webhooks/meshy/route.js`.

## Gagnagrunnur

`acm_pipeline`, notandi `acm_pipeline_user`.

VPS keyrir PostgreSQL 18.4 með `scram-sha-256`, sem þýðir að
`ALTER ROLE … RENAME TO …` **heldur lykilorðinu** — SCRAM-hash inniheldur ekki
notandanafnið. Undir gamla md5 hefði það þurrkast út.

`ALTER DATABASE … RENAME TO …` krefst þess að **engin virk tenging** sé við
gagnagrunninn. Stöðva `acm-pipeline` í PM2 fyrst.

## Röð sem skilur ekkert eftir

1. Stöðva PM2-ferlið og staðfesta að portið sé laust
2. Endurnefna möppuna
3. Leiðrétta átta breyturnar í `shared/.env.production`
4. Endurskapa eða leiðrétta Python-sýndarumhverfin
5. `ecosystem.config.cjs`, svo `pm2 delete` + `pm2 start` + `pm2 save` — ekki
   `reload`; PM2 man annars gömlu slóðina
6. Gagnagrunnur og notandi
7. nginx `server_name` og vottorð
8. `$RemoteRoot` í deploy-scriptinu
9. Staðbundnar umhverfisskrár, áætluð keyrsla, flýtileiðir

## Hvernig staðfest er að ekkert brotnaði

Prófin eru til og keyra bæði staðbundið og á VPS:

```bash
node --env-file=<env> scripts/check-workshop-health.mjs      # bæði R2 bucket
node --env-file=<env> scripts/check-workshop-endpoints.mjs   # hver pipeline
```

Bæði eiga að enda á `WORKSHOP_HEALTH_OK` og `ALL_PIPELINES_OK`. Þau voru
skrifuð eftir fyrri hýsilsbreytingu af nákvæmlega þessari ástæðu: sú
vinnslulína sem enginn opnar þá vikuna er sú sem situr biluð.

Að auki: eitt stutt render úr Claude Design, og **horfa á poster-myndina**.
Render sem klárast er ekki render sem tókst.
