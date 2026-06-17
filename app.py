import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math

# --- AI COACH FUNCTIE ---
def bereken_target_gewicht(huidige_e1rm, target_reps, rpe_target=8):
    # We mikken op 1.5% progressive overload ten opzichte van vorige keer
    doel_e1rm = huidige_e1rm * 1.015 
    
    # De wiskunde omdraaien: Gewicht = e1RM / (1 + (Reps + (10 - RPE)) / 30)
    berekend_gewicht = doel_e1rm / (1 + (target_reps + (10 - rpe_target)) / 30)
    
    # We ronden af op de dichtstbijzijnde 2.5kg (omdat dat de schijven in de gym zijn!)
    afgerond_gewicht = round(berekend_gewicht / 2.5) * 2.5
    return afgerond_gewicht

# --- WARM-UP CALCULATOR ---
def genereer_warmup(target_gewicht):
    if target_gewicht <= 20:
        return ["Stang (20kg) of Lichaamsgewicht x 10-15 reps"]
    
    warmups = ["Stang (20kg) x 10-15 reps"]
    stap1 = round((target_gewicht * 0.5) / 2.5) * 2.5
    stap2 = round((target_gewicht * 0.7) / 2.5) * 2.5
    stap3 = round((target_gewicht * 0.9) / 2.5) * 2.5
    
    if stap1 > 20: warmups.append(f"🟢 {stap1} kg x 8 reps (Doorbloeding)")
    if stap2 > stap1: warmups.append(f"🟡 {stap2} kg x 3-5 reps (Activatie)")
    if stap3 > stap2 and target_gewicht > 60: warmups.append(f"🔴 {stap3} kg x 1 rep (Zenuwstelsel primen)")
        
    return warmups

# --- PAGINA INSTELLINGEN ---
st.set_page_config(page_title="Gym AI", page_icon="🦍", layout="centered")

# --- HIDE STREAMLIT BRANDING ---
hide_st_style = """
            <style>
            [data-testid="stToolbar"] {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- DATABASE CONNECTIE FUNCTIES ---
def connect_to_sheet(sheet_naam):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    import os
    if os.path.exists("credentials.json"):
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    else:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
    client = gspread.authorize(creds)
    return client.open("Gym Database - Python Backend").worksheet(sheet_naam)

@st.cache_data(ttl=60)
def get_log_data():
    sheet = connect_to_sheet("LOG_DATA")
    data = sheet.get_all_records(numericise_ignore=['all'])
    df = pd.DataFrame(data)
    
    df['Gewicht'] = pd.to_numeric(df['Gewicht'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    df['RPE'] = pd.to_numeric(df['RPE'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    df['Reps'] = pd.to_numeric(df['Reps'], errors='coerce').fillna(0)
    df['Datum'] = pd.to_datetime(df['Datum'], format='%d-%m-%Y %H:%M:%S', errors='coerce')
    
    df['e1RM'] = df.apply(lambda row: row['Gewicht'] * (1 + (row['Reps'] + (10 - row['RPE'])) / 30) if row['RPE'] >= 8 else 0, axis=1)
    df['Volume'] = df.apply(lambda row: row['Gewicht'] * row['Reps'] if row['RPE'] >= 8 else 0, axis=1)
    
    df = df.sort_values(by='Datum', ascending=False)
    return df

@st.cache_data(ttl=60)
def get_metrics_data():
    sheet = connect_to_sheet("METRICS_DATA")
    data = sheet.get_all_records(numericise_ignore=['all'])
    df = pd.DataFrame(data)
    
    if 'Gewicht (kg)' in df.columns:
        df['Gewicht (kg)'] = pd.to_numeric(df['Gewicht (kg)'].astype(str).str.replace(',', '.'), errors='coerce')
    if 'Vet %' in df.columns:
        df['Vet %'] = pd.to_numeric(df['Vet %'].astype(str).str.replace(',', '.'), errors='coerce')
        
    df['Datum'] = pd.to_datetime(df['Datum'], format='%d-%m-%Y', errors='coerce')
    df = df.sort_values(by='Datum', ascending=True) 
    
    df['7D Gem. Gewicht'] = df['Gewicht (kg)'].rolling(window=7, min_periods=1).mean()
    df['7D Gem. Vet %'] = df['Vet %'].rolling(window=7, min_periods=1).mean()
    
    df = df.sort_values(by='Datum', ascending=False) 
    return df

@st.cache_data(ttl=60)
def get_oefeningen_details():
    sheet = connect_to_sheet("OEFENINGEN_LST")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

@st.cache_data(ttl=60)
def get_oefeningen_lijst():
    df = get_oefeningen_details()
    if not df.empty and 'Oefening' in df.columns:
        return df['Oefening'].tolist()
    return []

# --- RPE KLEUR FUNCTIE ---
def color_rpe(val):
    try:
        v = float(val)
        if v >= 9.5: return 'background-color: #ff4b4b; color: white'
        elif v >= 8.5: return 'background-color: #ffa100; color: white'
        elif v >= 8.0: return 'background-color: #ffe800; color: black'
        else: return 'background-color: #00d26a; color: white'
    except:
        return ''

# --- APP INTERFACE ---
colA, colB = st.columns([1, 4])

with colA:
    try:
        st.image("logo.png", width=60) 
    except:
        st.markdown("<h1>🦍</h1>", unsafe_allow_html=True)

with colB:
    st.title("Gym AI")

if 'pr_feestje' in st.session_state and st.session_state.pr_feestje:
    st.toast('NIEUW ALL-TIME PR GEBROKEN! 🦍🔥', icon='🏆')
    st.session_state.pr_feestje = False

# TABBLADEN AANMAKEN
tab1, tab2, tab3 = st.tabs(["🏋️‍♂️ Training", "⚖️ Body Metrics", "📈 Analytics"])
# ==========================================
# TAB 1: TRAINING
# ==========================================
with tab1:
    try:
        df_log = get_log_data()
        oefeningen_lijst = get_oefeningen_lijst()
        
        # -- LIVE VANDAAG TRACKER --
        vandaag_datum = datetime.now().strftime('%d-%m-%Y')
        df_vandaag = df_log[df_log['Datum'].dt.strftime('%d-%m-%Y') == vandaag_datum]
        sets_vandaag = len(df_vandaag)
        volume_vandaag = df_vandaag['Volume'].sum()
        
        if sets_vandaag > 0:
            st.success(f"🔥 **Sessie Vandaag:** {sets_vandaag} sets | 🏋️‍♂️ {volume_vandaag:,.0f} kg")
        
        st.divider()
        
        # -- OEFENING SELECTIE --
        st.subheader("Wat ga je doen?")
        split_keuze = st.radio("Filter je schema:", ["Alles", "Upper", "Lower"], horizontal=True, label_visibility="collapsed")
        
        if split_keuze == "Alles":
            gefilterde_lijst = oefeningen_lijst
        else:
            gefilterde_lijst = [oef for oef in oefeningen_lijst if split_keuze in oef]
        
        # -- GEHEUGEN --
        if 'gekozen_oefening' not in st.session_state: st.session_state['gekozen_oefening'] = None
        if 'laatste_gew' not in st.session_state: st.session_state['laatste_gew'] = None
        if 'laatste_reps' not in st.session_state: st.session_state['laatste_reps'] = None
        if 'laatste_type' not in st.session_state: st.session_state['laatste_type'] = "Top Set 🥇" # Standaard Top Set!

        default_idx = None
        if st.session_state['gekozen_oefening'] in gefilterde_lijst:
            default_idx = gefilterde_lijst.index(st.session_state['gekozen_oefening'])

        huidige_keuze = st.selectbox("Kies je Oefening (Typ om te zoeken):", gefilterde_lijst, index=default_idx, placeholder="Typ een oefening...")
        
        if st.session_state['gekozen_oefening'] != huidige_keuze:
            st.session_state['gekozen_oefening'] = huidige_keuze
            st.session_state['laatste_gew'] = None
            st.session_state['laatste_reps'] = None
            st.session_state['laatste_type'] = "Top Set 🥇" # Reset naar Top Set bij nieuwe oefening
            
        gekozen_oefening = st.session_state['gekozen_oefening']
        
        # -- GEAVANCEERDE OPTIES --
        is_deload = False
        with st.expander("⚙️ Geavanceerde Opties"):
            is_deload = st.toggle("🧘‍♂️ Deload Modus (Lichter trainen voor herstel)")
        
        if gekozen_oefening:
            df_oefening = df_log[df_log['Oefening'] == gekozen_oefening]
            pr = df_oefening['e1RM'].max()
            
            # Check of het een Compound is (OEFENINGEN_LST inladen)
            sheet_oefeningen = connect_to_sheet("OEFENINGEN_LST")
            df_oef_lijst = pd.DataFrame(sheet_oefeningen.get_all_records())
            is_compound = True 
            if not df_oef_lijst.empty and 'Compound' in df_oef_lijst.columns:
                match = df_oef_lijst[df_oef_lijst['Oefening'] == gekozen_oefening]
                if not match.empty:
                    val = str(match['Compound'].values[0]).strip().upper()
                    if val in ['FALSE', 'ONWAAR']:
                        is_compound = False

            # Zorg dat de Set_Type kolom bestaat in Pandas (om errors met oude data te voorkomen)
            if 'Set_Type' not in df_oefening.columns:
                df_oefening['Set_Type'] = ""

            # -- AI DUAL TARGET GENERATOR --
            laatste_datum = df_oefening['Datum'].max()
            
            vorig_top_e1rm = 0
            vorig_back_e1rm = 0
            
            if pd.notna(laatste_datum):
                laatste_sessie = df_oefening[df_oefening['Datum'].dt.date == laatste_datum.date()]
                
                # Zoek specifiek naar Top Sets en Back-off sets van de vorige sessie!
                if not laatste_sessie[laatste_sessie['Set_Type'] == "Top Set 🥇"].empty:
                    vorig_top_e1rm = laatste_sessie[laatste_sessie['Set_Type'] == "Top Set 🥇"]['e1RM'].max()
                if not laatste_sessie[laatste_sessie['Set_Type'] == "Back-off Set 🥈"].empty:
                    vorig_back_e1rm = laatste_sessie[laatste_sessie['Set_Type'] == "Back-off Set 🥈"]['e1RM'].max()

                # FALLBACK VOOR JOUW OUDE 60 SETS (Die hebben nog geen Set_Type)
                if vorig_top_e1rm == 0 and not laatste_sessie.empty:
                    vorig_top_e1rm = laatste_sessie['e1RM'].max()
                if vorig_back_e1rm == 0:
                    vorig_back_e1rm = vorig_top_e1rm * 0.85 # Standaard Backoff gokken op 85% voor oude data

            if is_compound:
                if vorig_top_e1rm > 0:
                    if is_deload:
                        target_8 = bereken_target_gewicht(vorig_top_e1rm * 0.80, target_reps=8, rpe_target=7)
                        st.info(f"🧘‍♂️ **Deload Doel (RPE 7):** Pak **{target_8} kg** voor 8 reps.")
                    else:
                        top_target = bereken_target_gewicht(vorig_top_e1rm, target_reps=6, rpe_target=8.5)
                        back_target = bereken_target_gewicht(vorig_back_e1rm, target_reps=10, rpe_target=8.5) 
                        st.info(f"🎯 **Targets voor Vandaag:**\n🥇 **Top Set:** {top_target} kg (voor ~6 reps)\n🥈 **Back-off Set:** {back_target} kg (voor ~10 reps)")
                        
                        # --- DE TERUGGEPLAATSTE WARM-UP GUIDE! ---
                        with st.expander("🔥 Toon Warm-up Protocol"):
                            # We berekenen de warmup op basis van je zware Top Set target
                            warmup_lijst = genereer_warmup(top_target) 
                            for setje in warmup_lijst:
                                st.write(setje)
                
                st.info(f"🏆 **All-Time PR (e1RM):** {pr:.1f} kg")
            else:
                st.info("💡 **Isolatie Oefening:** Double Progression. Push op reps (tot 15), dan pas gewicht verhogen.")
            
            # -- LOG NIEUWE SET --
            st.markdown("### 📝 Log Nieuwe Set")
            with st.form("log_form", clear_on_submit=True):
                # NIEUW: Radio buttons voor het type set!
                input_type = st.radio("Type Set:", ["Top Set 🥇", "Back-off Set 🥈", "Sociaal / Pomp 🍻"], index=["Top Set 🥇", "Back-off Set 🥈", "Sociaal / Pomp 🍻"].index(st.session_state['laatste_type']), horizontal=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    input_gewicht = st.number_input("Gewicht (kg)", min_value=0.0, step=2.5, format="%f", value=st.session_state['laatste_gew'], placeholder="bijv. 80.5")
                with col2:
                    input_reps = st.number_input("Reps", min_value=0, step=1, value=st.session_state['laatste_reps'], placeholder="bijv. 8")
                    
                input_rpe = st.selectbox("RPE", ["-", 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10], index=7)
                input_notities = st.text_input("Notities", value="", placeholder="Optioneel...")
                submit_button = st.form_submit_button("💾 Sla Set Op", use_container_width=True)
                
                if submit_button:
                    if input_gewicht is None or input_reps is None:
                        st.error("Vul a.u.b. het gewicht én de reps in!")
                    else:
                        st.session_state['laatste_gew'] = float(input_gewicht)
                        st.session_state['laatste_reps'] = int(input_reps)
                        
                        # ZERO FRICTION: Auto-Switch! Als je een Top Set logt, selecteert hij automatisch Back-off Set voor de volgende!
                        if input_type == "Top Set 🥇":
                            st.session_state['laatste_type'] = "Back-off Set 🥈"
                        else:
                            st.session_state['laatste_type'] = input_type

                        final_notes = input_notities
                        if is_deload:
                            final_notes = "[DELOAD] " + input_notities
                            
                        if input_rpe != "-" and not is_deload: 
                            rpe_float = float(input_rpe)
                            if rpe_float >= 8:
                                nieuwe_e1rm = input_gewicht * (1 + (input_reps + (10 - rpe_float)) / 30)
                                if is_compound and pd.notna(pr) and pr > 0 and nieuwe_e1rm > pr:
                                    st.session_state.pr_feestje = True
                        
                        nu = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        rpe_str = input_rpe if input_rpe != "-" else ""
                        
                        # We schrijven NU 7 kolommen naar Google Sheets, inclusief Set_Type in Kolom F!
                        nieuwe_rij = [nu, gekozen_oefening, float(input_gewicht), int(input_reps), rpe_str, input_type, final_notes]
                        sheet = connect_to_sheet("LOG_DATA")
                        sheet.append_row(nieuwe_rij, value_input_option="USER_ENTERED")
                        
                        st.cache_data.clear()
                        st.rerun()

            # -- UNDO KNOP --
            if not df_log.empty:
                laatste_oefening = df_log.iloc[0]['Oefening']
                laatste_gewicht = df_log.iloc[0]['Gewicht']
                laatste_reps = df_log.iloc[0]['Reps']
                with st.expander("⚠️ Oeps, foutje gemaakt?"):
                    st.write(f"Laatst gelogd: **{laatste_oefening}** ({laatste_gewicht}kg x {laatste_reps})")
                    if st.button("🗑️ Verwijder laatste set uit database", type="primary"):
                        sheet = connect_to_sheet("LOG_DATA")
                        aantal_rijen = len(sheet.get_all_values())
                        if aantal_rijen > 1:
                            sheet.delete_rows(aantal_rijen)
                            st.cache_data.clear()
                            st.toast("Set succesvol verwijderd!", icon="🗑️")
                            st.rerun()
            
            st.divider()

            # -- VORIGE KEER --
            st.markdown("### 🕒 Laatste 5 Sets")
            # Toon de nieuwe Set_Type kolom in je geschiedenis als hij bestaat
            toon_kolommen = ['Datum', 'Gewicht', 'Reps', 'RPE']
            if 'Set_Type' in df_oefening.columns:
                toon_kolommen.append('Set_Type')
            toon_kolommen.append('Notities')
            
            display_df = df_oefening[toon_kolommen].head(5)
            display_df['Datum'] = display_df['Datum'].dt.strftime('%d-%m-%y')
            styled_df = display_df.style.map(color_rpe, subset=['RPE'])
            st.dataframe(styled_df, hide_index=True, use_container_width=True)
            
            # -- KRACHT PROGRESSIE --
            if is_compound:
                st.markdown("### 📈 Kracht Progressie (Top Sets)")
                # FILTER: Zorg dat de grafiek ALLEEN Top Sets laat zien! (Of alles als er nog geen top sets zijn)
                df_trend = df_oefening
                if 'Set_Type' in df_oefening.columns and not df_oefening[df_oefening['Set_Type'] == "Top Set 🥇"].empty:
                    df_trend = df_oefening[df_oefening['Set_Type'] == "Top Set 🥇"]
                
                df_trend['Datum_Puur'] = df_trend['Datum'].dt.date
                kracht_df = df_trend[df_trend['e1RM'] > 0].groupby('Datum_Puur')['e1RM'].max().reset_index()
                kracht_df = kracht_df.sort_values(by='Datum_Puur', ascending=True)
                
                if not kracht_df.empty and len(kracht_df) > 1:
                    fig = px.line(kracht_df, x='Datum_Puur', y='e1RM', markers=True)
                    fig.update_traces(line_shape='spline', line=dict(color='#A5B4FC', width=3), marker=dict(size=8))
                    fig.update_layout(xaxis_title=None, yaxis_title="kg", margin=dict(l=0, r=0, t=10, b=0), height=250, dragmode=False, hovermode="x")
                    fig.update_xaxes(tickformat="%d-%m")
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.caption("Nog niet genoeg Top Sets gelogd voor een trendlijn.")

    except Exception as e:
        st.error(f"Fout in Training Tab: {e}")

# ==========================================
# TAB 2: BODY METRICS
# ==========================================
with tab2:
    try:
        df_metrics = get_metrics_data()
        
        st.markdown("### 📝 Log Nieuwe Weging")
        with st.form("metrics_form", clear_on_submit=True):
            m_datum = st.date_input("Datum", datetime.today())
            
            col1, col2 = st.columns(2)
            with col1:
                m_gew = st.number_input("Gewicht (kg)", min_value=0.0, step=0.1, format="%f", value=None, placeholder="bijv. 83.5")
                m_vet = st.number_input("Vet %", min_value=0.0, step=0.1, format="%f", value=None, placeholder="bijv. 18.2")
            with col2:
                m_water = st.number_input("Water %", min_value=0.0, step=0.1, format="%f", value=None)
                m_spier = st.number_input("Spier %", min_value=0.0, step=0.1, format="%f", value=None)
                
            m_bot = st.number_input("Botmassa (kg)", min_value=0.0, step=0.1, format="%f", value=None)
            m_notities = st.text_input("Notities", value="", placeholder="Gedronken, slecht geslapen, ziek...")
            
            submit_metrics = st.form_submit_button("💾 Sla Weging Op", use_container_width=True)
            
            if submit_metrics:
                if m_gew is None:
                    st.error("Vul minimaal je gewicht in!")
                else:
                    datum_str = m_datum.strftime("%d-%m-%Y")
                    val_gew = m_gew if m_gew is not None else ""
                    val_vet = m_vet if m_vet is not None else ""
                    val_water = m_water if m_water is not None else ""
                    val_spier = m_spier if m_spier is not None else ""
                    val_bot = m_bot if m_bot is not None else ""
                    
                    # Datum, Gew, Vet, Water, Spier, Bot, Notities
                    nieuwe_metric_rij = [datum_str, val_gew, val_vet, val_water, val_spier, val_bot, m_notities]
                    
                    sheet_m = connect_to_sheet("METRICS_DATA")
                    sheet_m.append_row(nieuwe_metric_rij, value_input_option="USER_ENTERED")
                    
                    st.cache_data.clear()
                    st.rerun()
                
        st.divider()
          
        if not df_metrics.empty:
            if '7D Gem. Gewicht' in df_metrics.columns and pd.notna(df_metrics['7D Gem. Gewicht'].iloc[0]):
                laatste_gew = df_metrics['7D Gem. Gewicht'].iloc[0]
                st.success(f"⚖️ **Huidig 7-Dagen Gem. Gewicht:** {laatste_gew:.1f} kg")
            
            st.markdown("### 📊 Historie")
            
            toon_kolommen = ['Datum', 'Gewicht (kg)', 'Vet %']
            if 'Notities' in df_metrics.columns:
                toon_kolommen.append('Notities')
            
            toon_kolommen = [c for c in toon_kolommen if c in df_metrics.columns]
            toon_metrics = df_metrics[toon_kolommen].head(5)
            toon_metrics['Datum'] = toon_metrics['Datum'].dt.strftime('%d-%m-%y')
            st.dataframe(toon_metrics, hide_index=True, use_container_width=True)
            
    except Exception as e:
        st.error(f"Nog geen Metrics data gevonden of een fout opgetreden. {e}")

# ==========================================
# TAB 3: ANALYTICS
# ==========================================
with tab3:
    try:
        df_log_full = get_log_data()
        df_metrics_full = get_metrics_data()
        df_oef_details = get_oefeningen_details()
        
        # Oefening eigenschappen koppelen (NU GERICHT OP JOUW NIEUWE HOOFDGROEP KOLOMMEN)
        if not df_oef_details.empty and not df_log_full.empty:
            # We negeren de oude Spiergroep kolommen en pakken direct de nieuwe!
            kolommen = ['Oefening', 'Compound', 'Hoofdgroep', 'Secundair Hoofdgroep']
            
            df_log_joined = df_log_full.merge(df_oef_details[kolommen], on='Oefening', how='left')
            df_log_joined['Compound'] = df_log_joined['Compound'].astype(str).str.upper().isin(['TRUE', 'WAAR', '1'])
        else:
            df_log_joined = df_log_full.copy()
            df_log_joined['Compound'] = False
            df_log_joined['Hoofdgroep'] = "Onbekend"

        # --- 1. THE BULK/CUT MATRIX ---
        st.markdown("### ⚖️ The Bulk/Cut Matrix")
        st.caption("Vergelijking van 7-Daags Gem. Lichaamsgewicht (Groen) versus Totale Kracht / Compound e1RM Trend (Blauw).")
        
        if not df_metrics_full.empty and '7D Gem. Gewicht' in df_metrics_full.columns:
            bw_df = df_metrics_full[['Datum', '7D Gem. Gewicht']].dropna().copy()
            bw_df['Datum_Puur'] = bw_df['Datum'].dt.date
            
            compound_logs = df_log_joined[(df_log_joined['Compound'] == True) & (df_log_joined['e1RM'] > 0)]
            if not compound_logs.empty:
                daily_max_e1rm = compound_logs.groupby(['Datum', 'Oefening'])['e1RM'].max().reset_index()
                daily_max_e1rm['Datum_Puur'] = daily_max_e1rm['Datum'].dt.date
                strength_trend = daily_max_e1rm.groupby('Datum_Puur')['e1RM'].mean().reset_index().rename(columns={'e1RM': 'Kracht_Score'})
                
                matrix_df = pd.merge(bw_df, strength_trend, on='Datum_Puur', how='outer').sort_values('Datum_Puur')
                matrix_df['7D Gem. Gewicht'] = matrix_df['7D Gem. Gewicht'].ffill().bfill()
                matrix_df['Kracht_Score'] = matrix_df['Kracht_Score'].ffill().bfill()
                
                fig_matrix = make_subplots(specs=[[{"secondary_y": True}]])
                fig_matrix.add_trace(
                    go.Scatter(x=matrix_df['Datum_Puur'], y=matrix_df['7D Gem. Gewicht'], name="7D Gem. BW", line=dict(color='#00d26a', width=3, shape='spline')),
                    secondary_y=False,
                )
                fig_matrix.add_trace(
                    go.Scatter(x=matrix_df['Datum_Puur'], y=matrix_df['Kracht_Score'], name="Kracht Trend", line=dict(color='#A5B4FC', width=3, shape='spline')),
                    secondary_y=True,
                )
                fig_matrix.update_layout(
                    margin=dict(l=0, r=0, t=10, b=0), height=250, hovermode="x unified", dragmode=False,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                fig_matrix.update_yaxes(title_text="Lichaamsgewicht (kg)", secondary_y=False, showgrid=False)
                fig_matrix.update_yaxes(title_text="e1RM Kracht (kg)", secondary_y=True, showgrid=False)
                st.plotly_chart(fig_matrix, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("Nog niet genoeg Compound data om de krachtlijn te plotten.")
        else:
             st.info("Nog niet genoeg lichaamsgewicht data voor de Matrix.")

        st.divider()

        # --- 2. MUSCLE BALANCE RADAR (INDIRECT VOLUME) ---
        st.markdown("### 🕸️ Structural Muscle Radar")
        st.caption("Werksets laatste 7 dagen. Primair = 1 set, Secundair = 0.5 set per anatomische Hoofdgroep.")
        
        zeven_dagen_geleden = datetime.now() - timedelta(days=7)
        recent_logs = df_log_joined[(df_log_joined['Datum'] >= zeven_dagen_geleden) & (df_log_joined['RPE'] >= 8)]
        
        if not recent_logs.empty and 'Hoofdgroep' in recent_logs.columns:
            volume_dict = {}
            
            # We loopen rij voor rij om de overlapping te checken!
            for _, row in recent_logs.iterrows():
                prim = str(row['Hoofdgroep']).strip() if pd.notna(row['Hoofdgroep']) else ""
                sec_raw = str(row.get('Secundair Hoofdgroep', '')).strip() if pd.notna(row.get('Secundair Hoofdgroep')) else ""
                
                # 1. Primaire spier krijgt altijd 1.0 set
                if prim and prim.lower() != 'nan':
                    volume_dict[prim] = volume_dict.get(prim, 0.0) + 1.0
                
                # 2. Secundaire spieren krijgen 0.5 set, MITS ze ANDERS zijn dan de primaire (De Fix!)
                if sec_raw and sec_raw.lower() != 'nan':
                    sec_list = [s.strip() for s in sec_raw.split('/')]
                    for sec in sec_list:
                        if sec and sec != prim: 
                            volume_dict[sec] = volume_dict.get(sec, 0.0) + 0.5
                            
            radar_data = pd.DataFrame(list(volume_dict.items()), columns=['Spier', 'Sets'])

            if len(radar_data) >= 3:
                fig_radar = go.Figure(data=go.Scatterpolar(
                  r=radar_data['Sets'], theta=radar_data['Spier'], fill='toself', line_color='#A5B4FC'
                ))
                fig_radar.update_layout(
                  polar=dict(radialaxis=dict(visible=True, showticklabels=False)),
                  showlegend=False, margin=dict(l=20, r=20, t=20, b=20), height=300, dragmode=False
                )
                st.plotly_chart(fig_radar, use_container_width=True, config={'displayModeBar': False})
            else:
                st.warning("Train minstens 3 verschillende hoofdgroepen voor een geldige radar chart.")
        else:
            st.info("Geen harde werksets (RPE 8+) gevonden in de laatste 7 dagen.")
            
        st.divider()

        # --- 3. PLATEAU DETECTOR ---
        st.markdown("### 🚧 Plateau Detector")
        st.caption("Welke Compounds stagneren? (Groei in e1RM ≤ 1% vergeleken met 3 weken geleden)")
        
        plateaus_found = []
        drie_weken_geleden = datetime.now() - timedelta(days=21)
        
        compounds_lijst = df_log_joined[df_log_joined['Compound'] == True]['Oefening'].unique()
        
        for oef in compounds_lijst:
            oef_data = df_log_joined[(df_log_joined['Oefening'] == oef) & (df_log_joined['e1RM'] > 0)]
            recent_data = oef_data[oef_data['Datum'] >= drie_weken_geleden]
            oud_data = oef_data[oef_data['Datum'] < drie_weken_geleden]
            
            if not recent_data.empty and not oud_data.empty:
                recent_max = recent_data['e1RM'].max()
                oud_max = oud_data['e1RM'].max()
                
                if recent_max <= (oud_max * 1.01):
                    plateaus_found.append({"Oefening": oef, "Recent": recent_max, "Oud": oud_max})
        
        if plateaus_found:
            for p in plateaus_found:
                 st.error(f"⚠️ **{p['Oefening']}**: Recente max {p['Recent']:.1f} kg. Je oude max (3w+ geleden) was {p['Oud']:.1f} kg.")
        else:
            st.success("🎉 Geen plateaus gedetecteerd in je Compounds! Progressive overload gaat als een raket. 🚀")

    except Exception as e:
        st.error(f"Fout in Analytics Tab: {e}")
