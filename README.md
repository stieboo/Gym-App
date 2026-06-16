# 🦍 Project Silverback - Gym AI

**Project Silverback** is een custom-built, full-stack fitness applicatie. Het combineert een Google Sheets cloud-database met een Python/Streamlit frontend, specifiek ontworpen voor 100% frictieloze logging in de gym en geavanceerde, data-gedreven hypertrofie-analytics.

---

## 🛠️ Tech Stack
- **Database:** Google Sheets Cloud Storage via Streamlit GSheets Connection
- **Frontend & Logic:** Python (Streamlit)
- **Data Manipulation:** Pandas & NumPy
- **Data Visualisation:** Plotly Express / Plotly Go
- **Deployment:** Streamlit Community Cloud (via GitHub)

---

## 📐 Data Architectuur & Integriteit
Om het "Garbage In, Garbage Out" principe tegen te gaan, hanteert de applicatie een strikte scheiding van tabellen en typespecifieke invoervalidatie vóór de commit naar de cloud:

*   **`LOG_DATA` (Rauwe Set-voor-Set Registratie):** `Timestamp (datetime)` | `Oefening (str)` | `Spiergroep (str)` | `Gewicht (float)` | `Reps (int)` | `RPE (int)` | `Volume (float)` | `e1RM (float)`
*   **`BODY_METRICS` (Dagelijkse Metingen):** `Date (date)` | `Weight (float)` | `Fat_Percentage (float, optioneel)` | `Notes (str)`
*   **Validatie-laag:** Automatische type-casting in de backend. Inkomende strings uit invoervelden worden vóór de database-injectie opgeschoond en omgezet naar numerieke waarden om crashes in de Pandas-pijplijn te voorkomen.

---

## ✅ Phase 1 & 2: MVP & Zero-Friction UI (COMPLETED)
- [x] Onbreekbare Google Sheets database structuur (Rauwe data, rij-per-set normalisatie).
- [x] Streamlit Cloud Deployment met veilige GitHub Secrets integratie (`secrets.toml`).
- [x] `e1RM` en `Volume` berekeningen live in Python (Brzycki Formula).
- [x] Filter op RPE < 8 (Warm-up sets en loze dataruist uitsluiten van analytics).
- [x] "Vandaag" Tracker (Live sets, tonnage en real-time feedback in het squatrek).
- [x] RPE Heatmap (Voorwaardelijke opmaak in dataframes voor vermoeidheidsinzicht).
- [x] Target Generator (Berekent exact benodigd gewicht/reps voor progressive overload).
- [x] Auto-Fill Memory (`st.session_state` voorkomt herhaaldelijk typen in de gym).
- [x] Upper/Lower/Alles Quick-Filters voor snelle oefening-selectie op mobiel.
- [x] Body Metrics tabblad inclusief 7-day Moving Averages (anti-ruistrend van lichaamsgewicht).
- [x] Undo-knop (Snel een foutief gelogde set verwijderen met één tik).

---

## 🚀 Phase 3: Command Center & Analytics (PLANNED: Data-afhankelijk)
*Wordt gebouwd bij >200 gelogde werksets (Verwacht: Week 4 - 5).*

- [ ] **Tabblad 3 Toevoegen:** "Analytics & Dashboard".
- [ ] **De Bulk/Cut Matrix:** Een dubbele-as Plotly grafiek (Lichaamsgewicht 7-day AVG versus e1RM progressie per hoofdlift).
- [ ] **Muscle Balance Radar:** Een Plotly Radar Chart (Spinnenweb) dat actueel trainingsvolume vergelijkt met hersteltargets per spiergroep.
- [ ] **De Warm-up Calculator:** Geautomatiseerde percentages (50%, 70%, 90% feeder set) op basis van de gegenereerde topset.
- [ ] **RPE vs. Volume Scatterplot:** Visualisatie van de individuele 'Sweet Spot' voor hypertrofie (volume versus PR-rendement).
- [ ] **Rate of Gain KPI-Stoplicht:** Visuele indicator op het dashboard die berekent of de bulk-snelheid (gewichtstoename per week op basis van de 7-day moving average) binnen de fysiologische 'sweet spot' ligt (+0.25% tot +0.5% van het lichaamsgewicht).
- [ ] **Database Migratie:** Overstap van Google Sheets naar een relationele PostgreSQL cloud-database (Supabase) ter voorbereiding op multi-user schaalbaarheid en complexere SQL-queries.

- [ ] - [ ] 📝 Toevoeging Roadmap Notes (Fase 3 - Visualisatie Logica)
[UX/Anatomische Realisatie - Juni 2026]

Probleem: De rug is biomechanisch opgesplitst in Lats en Boven Rug voor loepzuivere data. Dit gaat er gegarandeerd voor zorgen dat het absolute volume per categorie lager uitvalt dan bij Borst (wat als één grote groep wordt gelogd). Hierdoor trekt de Plotly Spider/Radar Chart visueel scheef, wat onterecht een spierdisbalans suggereert.

Oplossing voor de StatsEngine: Ga in de code niet blind absolute sets vergelijken op de radar. Implementeer in Fase 3 ofwel een Relatieve Schaling (volume afzetten tegen fysiologische targets per sub-spiergroep), ofwel een Aggregatie-Bypass waarbij Lats + Boven Rug voor de radar-chart tijdelijk worden samengevoegd tot de hoofdgroep Rug (Totaal). De ruwe, opgesplitste data in de database blijft intact.

---

## 🧠 Phase 4: Machine Learning & God-Mode (PLANNED: Lange termijn)
*Wordt gebouwd bij structurele data-historie (> 3 maanden).*

- [ ] **De Plateau Detector:** Algoritme dat stagnerende oefeningen detecteert (e1RM Moving Average < 1% stijging over 3 weken) en waarschuwingen (⚠️) triggert inclusief deload-advies.
- [ ] **CNS Fatigue Proxy Ledger:** Mathematisch model dat "neurologische vermoeidheid" schat door de verhouding tussen zware compound sets (RPE 9-10 op Squats/Deadlifts) en isolatiewerk te wegen tegen historische hersteltijden.
- [ ] **OpenAI / ChatGPT Integratie:** Automatische wekelijkse evaluatie waarbij de gpt-4o API de database en *Trainingsnotities* leest voor kwalitatief periodisatie-advies en het spotten van verborgen correlaties (bijv. slaaptekort vs. prestatieverlies op specifieke lifts).
- [ ] **Macro-Cycle Export:** Generatie van een strak vormgegeven PDF-rapportage na afronding van een trainingsblok via Python ReportLab.
- [ ] **API Federatie (Herstel):** Koppeling met Apple Health / Oura Ring data (Slaap / HRV) om live dag-targets automatisch aan te passen op basis van neurologische fitheid.

