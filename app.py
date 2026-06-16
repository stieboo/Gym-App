import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import plotly.express as px
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
    
    # Check of we in de Cloud draaien (met secrets) of Lokaal (met json bestand)
    import os
    if os.path.exists("credentials.json"):
        # Lokaal (Jouw laptop)
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    else:
        # In de Cloud (Streamlit Server)
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
    
    # e1RM & Volume
    df['e1RM'] = df.apply(lambda row: row['Gewicht'] * (1 + (row['Reps'] + (10 - row['RPE'])) / 30) if row['RPE'] >= 8 else 0, axis=1)
    df['Volume'] = df.apply(lambda row: row['Gewicht'] * row['Reps'] if row['RPE'] >= 8 else 0, axis=1)
    
    df = df.sort_values(by='Datum', ascending=False)
    return df

@st.cache_data(ttl=60)
def get_metrics_data():
    sheet = connect_to_sheet("METRICS_DATA")
    data = sheet.get_all_records(numericise_ignore=['all'])
    df = pd.DataFrame(data)
    
    # Alleen Gewicht en Vet omzetten naar getallen voor het gemiddelde
    if 'Gewicht (kg)' in df.columns:
        df['Gewicht (kg)'] = pd.to_numeric(df['Gewicht (kg)'].astype(str).str.replace(',', '.'), errors='coerce')
    if 'Vet %' in df.columns:
        df['Vet %'] = pd.to_numeric(df['Vet %'].astype(str).str.replace(',', '.'), errors='coerce')
        
    df['Datum'] = pd.to_datetime(df['Datum'], format='%d-%m-%Y', errors='coerce')
    df = df.sort_values(by='Datum', ascending=True) # Oplopend voor rolling average
    
    # 7-Daags Gemiddelde berekenen
    df['7D Gem. Gewicht'] = df['Gewicht (kg)'].rolling(window=7, min_periods=1).mean()
    df['7D Gem. Vet %'] = df['Vet %'].rolling(window=7, min_periods=1).mean()
    
    df = df.sort_values(by='Datum', ascending=False) # Weer omdraaien voor weergave
    return df

# --- RPE KLEUR FUNCTIE ---
def color_rpe(val):
    try:
        v = float(val)
        if v >= 9.5: return 'background-color: #ff4b4b; color: white' # Rood
        elif v >= 8.5: return 'background-color: #ffa100; color: white' # Oranje
        elif v >= 8.0: return 'background-color: #ffe800; color: black' # Geel
        else: return 'background-color: #00d26a; color: white' # Groen
    except:
        return ''

# --- APP INTERFACE ---
st.title("🦍 Gym AI")

# PR Feestje Check!
if 'pr_feestje' in st.session_state and st.session_state.pr_feestje:
    st.toast('NIEUW ALL-TIME PR GEBROKEN! 🦍🔥', icon='🏆')
    st.session_state.pr_feestje = False

# TABBLADEN AANMAKEN
tab1, tab2 = st.tabs(["🏋️‍♂️ Training", "⚖️ Body Metrics"])

@st.cache_data(ttl=60)
def get_oefeningen_lijst():
    sheet = connect_to_sheet("OEFENINGEN_LST")
    return sheet.col_values(1)[1:] # Haalt kolom A op, skipt de titel in rij 1

# ==========================================
# TAB 1: TRAINING
# ==========================================
with tab1:
    try:
        df_log = get_log_data()
        
        # FIX 1: Haal AL je oefeningen op uit de master-lijst (niet meer uit geschiedenis)
        oefeningen_lijst = get_oefeningen_lijst()
        
        # -- LIVE VANDAAG TRACKER --
        vandaag_datum = datetime.now().strftime('%d-%m-%Y')
        df_vandaag = df_log[df_log['Datum'].dt.strftime('%d-%m-%Y') == vandaag_datum]
        sets_vandaag = len(df_vandaag)
        volume_vandaag = df_vandaag['Volume'].sum()
        
        if sets_vandaag > 0:
            st.success(f"🔥 **Sessie Vandaag:** {sets_vandaag} sets | 🏋️‍♂️ {volume_vandaag:,.0f} kg")
        
        st.divider()
        
        # FIX 2: Het "Oefening Geheugen" aanmaken
        if 'gekozen_oefening' not in st.session_state:
            st.session_state['gekozen_oefening'] = None

        # Bepaal welke oefening standaard geselecteerd moet zijn in de lijst
        default_idx = None
        if st.session_state['gekozen_oefening'] in oefeningen_lijst:
            default_idx = oefeningen_lijst.index(st.session_state['gekozen_oefening'])

        # -- OEFENING SELECTIE (SEARCHABLE + MEMORY) --
        st.subheader("Wat ga je doen?")
        huidige_keuze = st.selectbox(
            "Kies je Oefening (Typ om te zoeken):", 
            oefeningen_lijst, 
            index=default_idx, 
            placeholder="Typ een oefening..."
        )
        
        # Update het geheugen als de gebruiker iets nieuws kiest
        st.session_state['gekozen_oefening'] = huidige_keuze
        
        gekozen_oefening = st.session_state['gekozen_oefening']
        
        # -- GEAVANCEERDE OPTIES (DELOAD) --
        is_deload = False
        with st.expander("⚙️ Geavanceerde Opties"):
            is_deload = st.toggle("🧘‍♂️ Deload Modus (Lichter trainen voor herstel)")
        
        if gekozen_oefening:
            df_oefening = df_log[df_log['Oefening'] == gekozen_oefening]
            pr = df_oefening['e1RM'].max()
            
            # -- AI COACH (TARGET GENERATOR) --
            laatste_datum = df_oefening['Datum'].max()
            vorig_e1rm = df_oefening[df_oefening['Datum'].dt.date == laatste_datum.date()]['e1RM'].max()

            if pd.notna(vorig_e1rm) and vorig_e1rm > 0:
                if is_deload:
                    # Deload: 80% van vorig e1RM, mikken op RPE 7
                    target_8 = bereken_target_gewicht(vorig_e1rm * 0.80, target_reps=8, rpe_target=7)
                    target_10 = bereken_target_gewicht(vorig_e1rm * 0.80, target_reps=10, rpe_target=7)
                    st.info(f"🧘‍♂️ **Deload Doel (RPE 7):**\nPak **{target_8} kg** voor 8 reps\n*óf* **{target_10} kg** voor 10 reps.")
                else:
                    # Normale Overload: RPE 8.5
                    target_8 = bereken_target_gewicht(vorig_e1rm, target_reps=8, rpe_target=8.5)
                    target_10 = bereken_target_gewicht(vorig_e1rm, target_reps=10, rpe_target=8.5)
                    st.success(f"🎯 **Jouw Overload Doel (RPE 8.5):**\nPak **{target_8} kg** voor 8 reps\n*óf* **{target_10} kg** voor 10 reps.")
            
            st.info(f"🏆 **All-Time PR (e1RM):** {pr:.1f} kg")
            
            # -- LOG NIEUWE SET (BOVENAAN) --
            st.markdown("### 📝 Log Nieuwe Set")
            with st.form("log_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    # Gewicht accepteert decimalen (zoals 12.5), dus iOS zal vaak het "getallen + leestekens" bordje tonen.
                    input_gewicht = st.number_input("Gewicht (kg)", min_value=0.0, step=2.5, format="%f", value=None, placeholder="bijv. 80.5")
                with col2:
                    # Omdat step 1 is (een Int), forceert dit op veel mobiele browsers het NumPad!
                    input_reps = st.number_input("Reps", min_value=0, step=1, value=None, placeholder="bijv. 8")
                    
                input_rpe = st.selectbox("RPE", ["-", 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10], index=7)
                input_notities = st.text_input("Notities")
                submit_button = st.form_submit_button("💾 Sla Set Op", use_container_width=True)
                
                if submit_button:
                    # Check of de velden wel zijn ingevuld!
                    if input_gewicht is None or input_reps is None:
                        st.error("Vul a.u.b. het gewicht én de reps in!")
                    else:
                        # Voeg automatische Deload tag toe aan notities
                        final_notes = input_notities
                        if is_deload:
                            final_notes = "[DELOAD] " + input_notities
                            
                        # RPE & PR Berekening 
                        if input_rpe != "-" and not is_deload: 
                            rpe_float = float(input_rpe)
                            if rpe_float >= 8:
                                nieuwe_e1rm = input_gewicht * (1 + (input_reps + (10 - rpe_float)) / 30)
                                if pd.notna(pr) and pr > 0 and nieuwe_e1rm > pr:
                                    st.session_state.pr_feestje = True
                        
                        nu = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                        rpe_str = input_rpe if input_rpe != "-" else ""
                        
                        nieuwe_rij = [nu, gekozen_oefening, float(input_gewicht), int(input_reps), rpe_str, final_notes]
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

            # -- VORIGE KEER (HEATMAP) (MAX 5 SETS) --
            st.markdown("### 🕒 Laatste 5 Sets")
            display_df = df_oefening[['Datum', 'Gewicht', 'Reps', 'RPE', 'Notities']].head(5)
            display_df['Datum'] = display_df['Datum'].dt.strftime('%d-%m-%y')
            styled_df = display_df.style.map(color_rpe, subset=['RPE'])
            st.dataframe(styled_df, hide_index=True, use_container_width=True)
            
            # -- KRACHT PROGRESSIE (TRENDLIJN) --
            st.markdown("### 📈 Kracht Progressie (e1RM)")
            df_oefening['Datum_Puur'] = df_oefening['Datum'].dt.date
            kracht_df = df_oefening[df_oefening['e1RM'] > 0].groupby('Datum_Puur')['e1RM'].max().reset_index()
            kracht_df = kracht_df.sort_values(by='Datum_Puur', ascending=True)
            
            if not kracht_df.empty and len(kracht_df) > 1:
                fig = px.line(kracht_df, x='Datum_Puur', y='e1RM', markers=True)
                fig.update_traces(line_shape='spline', line=dict(color='#00d26a', width=3), marker=dict(size=8))
                fig.update_layout(xaxis_title=None, yaxis_title="kg", margin=dict(l=0, r=0, t=10, b=0), height=250, dragmode=False, hovermode="x")
                fig.update_xaxes(tickformat="%d-%m")
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.caption("Nog niet genoeg werksets gelogd voor een trendlijn.")

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
                # value=None voor lege, schone startvakjes! format="%f" voor betere mobiele numpad herkenning
                m_gew = st.number_input("Gewicht (kg)", min_value=0.0, step=0.1, format="%f", value=None, placeholder="bijv. 83.5")
                m_vet = st.number_input("Vet %", min_value=0.0, step=0.1, format="%f", value=None, placeholder="bijv. 18.2")
            with col2:
                m_water = st.number_input("Water %", min_value=0.0, step=0.1, format="%f", value=None)
                m_spier = st.number_input("Spier %", min_value=0.0, step=0.1, format="%f", value=None)
                
            m_bot = st.number_input("Botmassa (kg)", min_value=0.0, step=0.1, format="%f", value=None)
            
            # Nieuw: Notities veld voor alcohol, zout, slecht geslapen etc.
            m_notities = st.text_input("Notities", value="", placeholder="Gedronken, slecht geslapen, ziek...")
            
            submit_metrics = st.form_submit_button("💾 Sla Weging Op", use_container_width=True)
            
            if submit_metrics:
                if m_gew is None:
                    st.error("Vul minimaal je gewicht in!")
                else:
                    datum_str = m_datum.strftime("%d-%m-%Y")
                    
                    # Fix: Als je de optionele vakjes leeg laat, maken we er een lege string van voor Sheets
                    val_gew = m_gew if m_gew is not None else ""
                    val_vet = m_vet if m_vet is not None else ""
                    val_water = m_water if m_water is not None else ""
                    val_spier = m_spier if m_spier is not None else ""
                    val_bot = m_bot if m_bot is not None else ""
                    
                    # Datum (A), Gew (B), Vet (C), Water (D), Spier (E), Bot (F), Notities (G)
                    nieuwe_metric_rij = [datum_str, val_gew, val_vet, val_water, val_spier, val_bot, m_notities]
                    
                    sheet_m = connect_to_sheet("METRICS_DATA")
                    sheet_m.append_row(nieuwe_metric_rij, value_input_option="USER_ENTERED")
                    
                    st.cache_data.clear()
                    st.rerun()
                
        st.divider()
          
        # Laatste Gemiddeldes tonen
        if not df_metrics.empty:
            # We checken veilig of het 7D gemiddelde bestaat
            if '7D Gem. Gewicht' in df_metrics.columns and pd.notna(df_metrics['7D Gem. Gewicht'].iloc[0]):
                laatste_gew = df_metrics['7D Gem. Gewicht'].iloc[0]
                st.success(f"⚖️ **Huidig 7-Dagen Gem. Gewicht:** {laatste_gew:.1f} kg")
            
            # Korte Historie
            st.markdown("### 📊 Historie")
            
            # We tonen alleen de belangrijkste kolommen in de app, inclusief Notities als die er is!
            toon_kolommen = ['Datum', 'Gewicht (kg)', 'Vet %']
            if 'Notities' in df_metrics.columns:
                toon_kolommen.append('Notities')
            
            toon_kolommen = [c for c in toon_kolommen if c in df_metrics.columns]
            
            toon_metrics = df_metrics[toon_kolommen].head(5)
            toon_metrics['Datum'] = toon_metrics['Datum'].dt.strftime('%d-%m-%y')
            st.dataframe(toon_metrics, hide_index=True, use_container_width=True)
            
    except Exception as e:
        st.error(f"Nog geen Metrics data gevonden of een fout opgetreden. {e}")
