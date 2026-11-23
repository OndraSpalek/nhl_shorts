# Be6player Shorts V6.7 — ověřovací balíček pro GitHub Actions

## Co je nové

- Oddělený ručně spouštěný workflow `be6player_shorts_v67.yml`, výchozí **fixture** režim; **žádné automatické plánování** před úspěšným živým ověřením.
- `v67_verify.py` kontroluje počet zápasů, původ dat, zápas dne, úplnost PNG karet, manifest, 1080×1920 MP4, zvukovou stopu a zakázaný hlas / YouTube upload.
- `verification.json` a `verification.md` ukládané do artifacts a zobrazené v GitHub Actions summary.
- Všechny soubory v adresáři `be6player_v6_7/`; **nepřepisovat existující e-mailový workflow**.

## Postup na GitHubu

1. Zkopírujte celý adresář `be6player_v6_7` do kořene repozitáře.
2. GitHub workflow musí být v **kořenovém** `.github/workflows/`, proto zkopírujte **pouze** soubor `be6player_v6_7/.github/workflows/be6player_shorts_v67.yml` do kořenového `.github/workflows/`. Staré workflow neupravujte.
3. GitHub → Actions → **Be6player Shorts V6.7** → Run workflow → mode `fixture`. Po úspěšném testu zvolte `live` a aktuální datum v ČR (nebo nechte prázdné).
4. Otevřete `verification.md`, `audit.json`, `data.json` a výsledné MP4 v artifacts. Zkontrolujte i skutečná data a grafiku ručně.

## Lokální test

```bash
sudo apt-get install ffmpeg fonts-dejavu-core libcairo2
python -m pip install pillow requests cairosvg tzdata
python -m unittest discover -s tests -v
python v66_pipeline.py --date 2026-11-22 --fixture demo/offline_api_fixture.json --outdir shorts_preview --render --allow-demo-logos --seconds 2
python v67_verify.py --outdir shorts_preview
```

## Omezení

- Živé NHL API, CDN všech klubových log ani samotné GitHub Actions **nebyly zde úspěšně ověřeny**. Live režim může skončit chybou; právě proto V6.7 obsahuje audit.
- `fixture` je ilustrační test a nesmí být publikován jako aktuální NHL program.
- Stále jedna karta na zápas, nikoli všechny tematické karty. H2H a hráčské série nejsou automaticky vykreslovány. Zápasy se řadí podle data v ČR (okno 10:00–10:00).
- Výchozí hudba je původní procedurálně vytvořený instrumentál, bez komentáře. Žádný automatický YouTube upload.
- **Pozor:** Sezonní endpoint `/club-schedule-season/{team}/now` používá aktuální sezonu; historické datum není vhodné pro ostrý historický report.
- Workflow očekává projekt v `be6player_v6_7/` a spouští se **jen ručně**. Nezapínejte denní cron před ověřením.
