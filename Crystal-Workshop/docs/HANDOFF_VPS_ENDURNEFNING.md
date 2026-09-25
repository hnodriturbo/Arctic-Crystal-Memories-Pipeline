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

---

## Liður 15 — Workshop-hlutinn (staðbundið, 25-09-2026)

Rótarmappan var endurnefnd `Arctic_Crystal_Memories` → `Crystal_Clear_Memories`
og repo-in `ACM-Web-*` → `CCM-Web-*`. **Utan repo-sins er þegar búið:** áætlaða
keyrslan `ACM-Bookkeeping-Expense-R2-Sync` vísar nú í
`CCM-Web-Workshop\scripts\run-daily-r2-sync.ps1`, og skjáborðsflýtileiðirnar
heita nú `CCM …` og vísa á nýju möppurnar. Það sem eftir er liggur hér:

- [ ] `scripts/run-daily-r2-sync.ps1`, línur 11–14: `ACM-Web-Workshop` og
      `ACM-Web-Bookkeeping` eru harðkóðuð möppunöfn. **Keyrslan brotnar á þessu
      þó slóðin í Task Scheduler sé rétt.**
- [ ] `scripts/start-manual-r2-sync.ps1`: sömu möppunöfn, og skilaboðaglugginn
      nefnir `ACM` og `workshop.acm.is`
- [ ] `Crystal-Workshop/ACM-Web-Pipeline/.env.local` og `.env.development`:
      `CONVERTER_ROOT`, `MESHY_ROOT`, `IMAGE_PIPELINE_ROOT`, `CLAUDE_DESIGN_ROOT`
      vísa enn í `Arctic_Crystal_Memories\…`
- [ ] `.env.example` sömu breytur, svo sniðmátið kenni rétta slóð
- [ ] Keyrslan 24-09-2026 kl. 15:00 skilaði `1` — **áður** en möppunum var
      breytt. `cockpit3d` datt á afritun `Cockpit3D-Files\.original-images\
      Amma-og-Afi\amma-no-bg.png` í temp-snapshot. Sérstök villa, ekki
      endurnefningin
- [ ] Staðfesta: keyra `CCM - Update R2` eða keyrsluna handvirkt, enda á
      `DAILY_R2_BACKUP_OK`, og engin lína í `deployment/artifacts/r2-sync-logs`
      segi `failed to start`

Bókhalds-`.env` er sinn hluti — sjá sama skjal í `CCM-Web-Bookkeeping/docs`.
Keyrslan virkar ekki fyrr en **báðir** hlutar eru komnir.

## GitHub-repo — endurnefna `Arctic-Crystal-Memories-Pipeline` → `CCM-Web-Workshop`

Sama og gert var fyrir Web-Main 25-09-2026 (`Arctic-Crystal-Memories-Web-Main`
→ `CCM-Web-Main`). `gh` er innskráð sem `hnodriturbo` með `repo`-heimild, sem
dugar. GitHub áframsendir gamla nafnið, en **treystu ekki á það** — lagaðu allt.

> Þetta repo er **PUBLIC**. Nafnið sést opinberlega — staðfesta við eigandann
> að `CCM-Web-Workshop` sé nafnið sem hann vill.

1. `gh repo rename CCM-Web-Workshop --repo hnodriturbo/Arctic-Crystal-Memories-Pipeline --yes`
2. Staðbundið: `git remote set-url origin git@github.com:hnodriturbo/CCM-Web-Workshop.git`
   og staðfesta með `git ls-remote origin`. Athuga líka hvort `Crystal-Workshop`
   eða `ACM-Web-Pipeline` séu sjálfstæð repo með eigin remote
3. VPS: **engin git-afritun** af Workshop á þjóninum — hann er deployaður með
   archive (`scripts/deploy-pipeline-vps.ps1`). Ekkert að breyta þar vegna
   repo-nafnsins
4. Allt sem finnst með gamla nafninu, utan sögulegra skjala

`$RemoteRoot` og `/home/hreidar/apps/acm-pipeline` breytast **ekki** í þessu
skrefi — þau fylgja VPS-endurnefningunni hér að ofan. Script verður alltaf að
passa við það sem er raunverulega til á þjóninum.

## Staða Codex — 25-09-2026, fyrir VPS-endurnefningu

Eigandi hefur heimilað VPS-endurnefningu í þessari lotu, en hún má ekki hefjast fyrr en Claude hefur lokið sinni VPS-vinnu og eigandi lætur vita. Main er í eigu Claude í þessari lotu. GitHub er ekki snert.

Staðbundið lokið:
- Workshop `.env.local` og `.env.development`: fjórar rótarslóðir leiðréttar og allar sannreyndar til.
- `.env.example`, daglegi keyrari, handvirk ræsing og Main-slóð í R2-hjálparskriftu uppfærð. Innra verkefnisheitið `ACM-Web-Pipeline` er enn raunverulegt möppunafn.
- `.Production-Web-Workshop` hefur environment, db-backup-&-restore, nginx og release-staging. `.env.production` afritað án efnisbreytinga og hash-borið saman. Öll production-mappan er útilokuð frá Git. Leiðbeiningar og afrit virks Workshop-nginx-blokks og PM2-stillingar fylgja.
- Cockpit backup fjarlægir nú fyrri tímabundna snapshot-skrá fyrir næstu afritun; read-only-próf og raunkeyrsla fóru í gegn án eldri EPERM-villu.

Staðfesting:
- Workshop og Bookkeeping production build stóðust; þrjú staðbundin Python-umhverfi ræstust með Python 3.11.9.
- R2-lespróf: WORKSHOP_HEALTH_OK.
- Dagleg keyrsla 25-09-2026 kl. 10:56:38: Task Scheduler LastTaskResult=0, fjórir hlutar kláruðust; Cockpit uploaded=75 unchanged=56, Claude Design unchanged=253. Log: `deployment/artifacts/r2-sync-logs/25-09-2026-105638-*`.
- Þriggja sekúndna staðbundið Hero-Banner-IS render og sjónræn yfirferð poster tókst. Frumhönnun óbreytt.
- Endpoint-próf á VPS-loopback: ALL_PIPELINES_OK. Þetta sannar ekki ytri leiðina.
- Ytri Meshy POST: HTTP 403 text/html frá Cloudflare. Það þarf enn að leysa áður en webhook er talið virkt.

VPS-undirbúningur (ekki framkvæmdur):
- Áætluð ný rót/PM2: `/home/hreidar/apps/ccm-workshop`, `ccm-workshop`; DB/role: `ccm_workshop`, `ccm_workshop_user`.
- Núverandi active-release og rollback-symlinkar eru algildir; leiðrétta þarf þá alla. `shared/python` hefur líka algildan symlink og venv-python vísar í þann symlink.
- Venv eru uv-relocatable en `pyvenv.cfg` home og nokkrar ræsingarslóðir innihalda gamla root; sannreyna imports eftir breytingu.
- Þrjár ROOT-breytur í VPS `.env.production` nota enn `current/converter`; PM2 yfirskrifar þær með `current/Crystal-Workshop`. Samræma allar production-skrár við raunverulegt runtime.
- Lesa þarf nýja stöðu eftir að Claude lýkur. Taka fersk, sannreynd DB/config-afrit áður en stöðvað er, varðveita rollback, endurskrá aðeins þessar þjónustur í PM2 og pm2 save.
- Samræma deploy-script default/guard, environment-copies og rekstrarleiðbeiningar aðeins við lokið VPS-ástand. Bucket-nöfn og persónuleg gögn eru ekki endurnefnd.

### Lok staðbundins undirbúnings og bið eftir Claude

Eigandi ítrekaði 25-09-2026 að engar aðgerðir á VPS séu leyfðar meðan Claude klárar Main lið 14, PM2 DATABASE_URL og Bookkeeping-tengingar. Þetta nær líka til lesaðgerða. Bíða eftir nýju merki frá eiganda og lesa þá uppfærða stöðu.

Staðbundið var einnig lagað `deploy-pipeline-r2-credentials.ps1` til að lesa production-env úr nýju Workshop production-möppunni. Bookkeeping Teya audit-resolver styður nú nákvæmu gömlu og nýju service-audit slóðirnar; ný guard-próf og production build stóðust. Þessar breytingar eru EKKI komnar á VPS.

Cloudflare var eingöngu skoðað: ccm.is er Pro, Super Bot Fight Mode setur definitely automated traffic í Managed Challenge og engin custom rules eru skráð. Þröng undantekning fyrir Meshy-endpoint þarf að fara í gegnum yfirferð; engin regla var búin til eða breytt. Tímabundnum staðbundnum render-prófskrám var eytt eftir sjónræna yfirferð; samstillingarlog og production-leiðbeiningar varðveitt.

## Staðfest VPS-endurnefning Codex — 25-09-2026

Þessi staða leysir af hólmi eldri bið- og fyrir-flutning stöðu ofar. Claude staðfesti lok Main: `ccm_main`, `ccm_web_user`.

- Bookkeeping: `/home/hreidar/apps/ccm-bookkeeping`, PM2 `ccm-bookkeeping`, DB `ccm_bookkeeping`, role `ccm_bookkeeping_user`. Báðir Main-readerar heita nú `ccm_bookkeeping_staging_reader` og `ccm_bookkeeping_production_reader`.
- Workshop: `/home/hreidar/apps/ccm-workshop`, PM2 `ccm-workshop`, DB `ccm_workshop`, role `ccm_workshop_user`.
- Afrit voru tekin fyrir stöðvun, custom-format dump lesið með pg_restore, SHA-256 sannreynt eftir niðurhal og töflufjöldi/raðafjöldi varðveittur. Engin DB-endurheimt eða schema-migration var keyrð.
- VPS-afrit, release-manifest og bakfærsluskrift: `/home/hreidar/apps/backups/ccm-rename-25-09-2026-112206`. Staðbundin afrit í production-möppu hvorrar þjónustu undir `db-backup-&-restore/25-09-2026-vps-rename`.
- Aðeins yfirfarnar Teya-audit og Workshop HMAC lagfæringar voru lagðar yfir afrit af virku release og byggðar; aðrar óvistaðar staðbundnar breytingar voru ekki birtar.
- PM2 skráning endurgerð og vistuð; engin gömul þjónusturót í umhverfisgildum nýju ferlanna. Allir yfirfarnir symlinkar heilir, þar með taldir fjórir myndvinnslu-models tenglar sem lokapróf fann og leiðrétti. Þeir eru líka skráðir í rollback journal.
- Báðir Bookkeeping-readerar tengjast `ccm_main`, default_transaction_read_only=on, hafa engan public-schema aðgang og geta lesið sín eigin views. Agent-innskráning og síður /is, /en, /is/orders, /is/sources og /is/payday/expenses skiluðu 200. Teya-audit-slóð samþykkt af nýja resolvernum.
- Workshop: WORKSHOP_HEALTH_OK og ALL_PIPELINES_OK eftir flutning; þrjú Python-umhverfi flytja inn lykilsöfn. R2 bucket-nöfnum og gögnum var ekki breytt við endurnefningu.
- Staðbundnar deploy/audit/provision/sync skriftur og PM2-sniðmát nota nú staðfest ný VPS-nöfn. Production-env afrit hafa fengið ný slóða- og DB-auðkenni; leyndarmál voru ekki flutt eða samræmd í því skrefi. Staðbundin þróunargagnagrunnsnöfn haldast óbreytt.
- Tekju-dry-run eftir flutning: 13 canonical skjöl, engin gögn vantar staðbundið eða í R2, engir árekstrar. Teya webhook próf og PowerShell parse stóðust.

Eftir stendur: full samræming production-leyndarmála bíður skýrs samþykkis vegna höfnunar sjálfvirkrar heimildayfirferðar. Ytri Meshy POST fær enn Cloudflare HTML challenge; þröng POST/host/path undantekning frá Super Bot Fight Mode bíður samþykkis. Ekki kalla webhook end-to-end staðfest fyrr en þetta er leyst. GitHub var ekki snert.
### Lokapróf render — 25-09-2026

Stutt render á VPS eftir flutning lauk: 3 sekúndur, 72 rammar, 960×540. Poster skoðaður og sýndi rétta hero-hönnun/logó. Tímabundið MP4/poster fjarlægt eftir yfirferð; hönnunarfrumrit óbreytt. Enginn staðbundinn dev-þjónn eftir þessa lotu.
## 25-09-2026 — Production-env og Meshy Cloudflare leið lagfærð

Eigandi gaf sértækt samþykki fyrir production-leyndarmálasamræmingu og afmarkaðri Cloudflare-undantekningu. Bookkeeping production-gildi pössuðu þegar við VPS. Workshop hafði eitt frábrugðið gildi: MESHY_WEBHOOK_SECRET. Nýja gildið úr fyrirliggjandi staðbundnu production-env (sama og .env.local) var sett á VPS eftir einkafrit og ccm-workshop endurræst. Staðbundin canonical production-eintök beggja þjónusta eru nú byte-identical við niðurhalað VPS-eintak; Workshop app .env.production einnig.

Cloudflare ccm.is custom rule `Meshy webhook - skip bot challenge` er Active, ID `bb97e506f05c41fd8746b517b61c1b63`. Nákvæm skilyrði: host workshop.ccm.is, URI path /webhooks/meshy, method POST. Sleppir eingöngu Super Bot Fight Mode; log matching requests er virkt. Almenn bot-vörn á öðrum leiðum óbreytt.

Ytra próf gegnum Cloudflare: gild HMAC-undirskrift með nýju óþekktu probe-id skilaði 200 application/json, `No local job for that task`; ógild undirskrift með sama óþekkta id skilaði 404 JSON. Engin raunveruleg Meshy-vinnsla ræst eða job-gögn breytt. Raunveruleg provider-delivery er enn sérstakt próf; þessi niðurstaða staðfestir að Cloudflare hleypir POST í gegn og production notar rétta lykilinn.

Production-bakfærsluafrit: hvorrar þjónustu db-backup-&-restore/25-09-2026-env-sync og VPS migration-state/workshop-env-before-secret-sync.env. Sjálfvirk heimildayfirferð hafnaði viðbótarbreytingu á .env.development þar sem samþykkið var production-afmarkað; development var því óbreytt, en samþykkta production-vinnan kláraðist.
## 25-09-2026 — Development webhook secret synchronized with explicit approval

Owner explicitly approved the previously rejected development-only change. Updated only MESHY_WEBHOOK_SECRET in CCM-Web-Workshop/Crystal-Workshop/ACM-Web-Pipeline/.env.development to the verified canonical production value, which also matches .env.local. Byte comparison with the assignment redacted proved all other file content unchanged. Private pre-change backup: .Production-Web-Workshop/db-backup-&-restore/25-09-2026-env-sync/development-before-25-09-2026-140137.env. No VPS change, server start or credential value output. This supersedes the earlier development-secret-blocked status.
## 25-09-2026 — Workshop navigation, preview and two-way sync released

Active VPS release: `20260925T163033Z-design-navigation`; rollback: `20260925T112438Z-ccm-rename`. Home cards now open section menus, with image processing, Meshy and Cockpit as parts 1–3; experimental 2.5D stays hidden. Icelandic labels, fitted landscape/portrait previews, new collection creation and accessible render-setting help are deployed. Closing-scene site text is www.ccm.is.

Windows/R2 source and video sync is now bidirectional with SHA-256 baselines, conditional writes, retained revisions and reported conflicts. The existing daily 15:00 schedule is unchanged; the UI also has manual collection sync. No continuous file watcher was installed. Real R2 upload, remote modification/download, local modification/upload and unchanged rerun passed with a disposable probe. Initial sync uploaded 4 approved domain JSON changes and 10 existing private videos; 246 source files were unchanged and no conflicts remained. Five hidden/control files were intentionally skipped. Owner originals remain in Claude-Design-Stuff.

Validation: sync regression suite on Windows/VPS, focused ESLint, local/VPS production builds, R2 read/write probe, 3-second Showroom render with inspected poster, local landscape/portrait/mobile preview and tooltip checks. Authenticated live navigation, CCM label, CRF help and iframe fit verified after activation. The first activation health check incorrectly expected 401 instead of the existing authentication redirect 307 and rolled back automatically; the corrected check passed on reactivation. No production auth behavior was changed.
