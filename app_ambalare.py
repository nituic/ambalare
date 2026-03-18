import streamlit as st
import pandas as pd
import psycopg2
#from sqlalchemy import create_engine
from py3dbp import Packer, Bin, Item
import math
from fpdf import FPDF
from datetime import datetime
import streamlit_authenticator as stauth

st.set_page_config(page_title="Sistem logistic V2.0", layout="wide")
st.title("🚀 Hub Logistic: Multi-Packing & Costuri")

# 1. Încarcă datele din secrets
credentials = st.secrets["credentials"].to_dict()
cookie = st.secrets["cookie"].to_dict()

# 2. Creează obiectul de autentificare
authenticator = stauth.Authenticate(
    credentials,
    cookie['name'],
    cookie['key'],
    cookie['expiry_days']
)

# 3. Randarea formularului de login
#name, authentication_status, username = authenticator.login('main')
#authenticator.login('Login', 'main')
authenticator.login()
if st.session_state["authentication_status"]:
    authenticator.logout('Logout', 'sidebar')
    st.write(f'Salut, *{st.session_state["name"]}*!')
    
    
    # Aici pui tot codul tău existent pentru aplicația de ambalare
    # (ex: tabelele, input-urile, conexiunea la Postgres)
    


    # Streamlit citește automat din .streamlit/secrets.toml
    db_secrets = st.secrets["postgres"]

    conn = psycopg2.connect(
        host=db_secrets["host"],
        port=db_secrets["port"],
        database=db_secrets["database"],
        user=db_secrets["user"],
        password=db_secrets["password"]
    )

    # Conexiune DB
    #engine = create_engine('postgresql://postgres:Humi2025@localhost:5432/ambalare')

    #st.set_page_config(page_title="Sistem logistic V2.0", layout="wide")
    #st.title("🚀 Hub Logistic: Multi-Packing & Costuri")

    def sincronizeaza_tabel():
        # 1. Ștergem rezultatele vechi imediat ce s-a produs o schimbare în tabel
        if 'rezultate_calcul' in st.session_state:
            st.session_state.rezultate_calcul = None

        # Verificăm dacă există modificări în starea internă a editorului
        if "tabel_cos" in st.session_state:
            edite_state = st.session_state["tabel_cos"]
            
            # Dacă s-au șters rânduri
            if edite_state.get("deleted_rows"):
                # Luăm lista actuală și eliminăm indexurile marcate pentru ștergere
                indices_de_sters = edite_state["deleted_rows"]
                noua_lista = [
                    item for i, item in enumerate(st.session_state.lista_cumparaturi) 
                    if i not in indices_de_sters
                ]
                st.session_state.lista_cumparaturi = noua_lista
                
            # Dacă s-au editat celule (de ex. ai schimbat cantitatea direct în tabel)
            if edite_state.get("edited_rows"):
                for index, modificari in edite_state["edited_rows"].items():
                    idx = int(index)
                    for coloana, valoare_noua in modificari.items():
                        st.session_state.lista_cumparaturi[idx][coloana] = valoare_noua

    def get_tari():
        # Conectare și citire tabel tari
        query = "SELECT denumire_ro, denumire_en, cod_tara, membru_ue FROM tari WHERE activ = True ORDER BY denumire_ro ASC"
        df_tari = pd.read_sql(query, conn)
        
        def get_flag_emoji(country_code):
            if not country_code or len(country_code) != 2:
                return "🌐"
            return "".join(chr(127397 + ord(c)) for c in country_code.upper())
        df_tari['display_name'] = df_tari['denumire_ro']
        df_tari['emoji'] = df_tari['cod_tara'].apply(get_flag_emoji)

        return df_tari

    def genereaza_pdf_ambalare(varianta_aleasa, tara="Nespecificată", p_ip=0, p_ie=0, procent_fuel=0):
        pdf = FPDF()
    
        try:
            pdf.add_font('ArialCustom', '', 'Arial.ttf')
            pdf.add_font('ArialCustom', 'B', 'Arialbd.ttf')
            pdf.add_font('ArialCustom', 'I', 'Ariali.ttf')
            font_familie = 'ArialCustom'
        except:
            font_familie = 'Arial' 
            
        pdf.set_margins(left=20, top=10, right=10)
        pdf.add_page()

        w_cant = 15
        w_prod = 165 

        greutate_fizica_totala = sum([c['greutate_fizica_colet'] for c in varianta_aleasa['detalii_containere']])
        
        pdf.set_font(font_familie, "B", 16)
        pdf.cell(0, 10, f" Packaging Instructions ", new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.ln(2)
        pdf.set_font(font_familie, "I", 7)
        pdf.cell(0, 10, f"Generated at: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}", 0, new_x="LMARGIN", new_y="NEXT", align='R')
        
        pdf.set_font(font_familie, "", 10)
        pdf.cell(90, 6, f"Destination country : {tara}", new_x="RIGHT", new_y="TOP")
        pdf.cell(90, 6, f"Total number of boxes : {varianta_aleasa['nr_total_cutii']} pcs", border=0, new_x="LMARGIN", new_y="NEXT")
        pdf.cell(90, 6, f"Total physical weight: {round(greutate_fizica_totala, 2)} kg", new_x="RIGHT", new_y="TOP")
        pdf.cell(90, 6, f"Average volumetric efficiency: {round(varianta_aleasa['grad_umplere'] * 100, 1)}%", border =0, new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font(font_familie, "B", 11)
        pdf.set_text_color(200, 0, 0) 
        pdf.cell(0, 8, f"FINAL TAXABLE WEIGHT: {round(varianta_aleasa['greutate_taxabila_totala'], 2)} kg", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

        if p_ie > 0:
            pdf.set_font(font_familie, "IU", 10)
            pdf.set_text_color(0, 102, 204) 
            pdf.cell(0, 5, f"Tarifele includ taxa combustibil / Fuel Surcharge: {procent_fuel}%", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
            pdf.set_font(font_familie, "I", 10)
            pdf.set_text_color(0, 0, 0) 
            pdf.cell(0, 5, f"Estimated Shipping Cost (Economy - IE): {p_ie} EUR ", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 5, f"Estimated Shipping Cost (Priority - IP): {p_ip} EUR ", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(4)

        for i, colet in enumerate(varianta_aleasa['detalii_containere']):
            if pdf.get_y() > 230: 
                pdf.add_page()
                
            pdf.set_fill_color(240, 242, 246)
            pdf.set_font(font_familie, "B", 11)
            cod_cutie_curent = colet.get('cod_cutie', varianta_aleasa['cod_cutie'])
            
            dim_l = colet.get('l_ext', 0)
            dim_w = colet.get('w_ext', 0)
            dim_h = colet.get('h_ext', 0)
            try:
                dim_l = round((float(dim_l)),2)
                dim_w = round((float(dim_w)),2)
                dim_h = round((float(dim_h)),2)
            except:
                pass
            
            dimensiuni_text = f"[{dim_l:g}x{dim_w:g}x{dim_h:g} cm]"
            text_header = f" PACKAGE: {i+1} - Box : {cod_cutie_curent} {dimensiuni_text}"
            
            pdf.cell(0, 8, text_header, border="T", new_x="LMARGIN", new_y="NEXT", fill=True)
            pdf.set_font(font_familie, "", 9)
            g_f, g_v = round(colet['greutate_fizica_colet'], 2), round(colet['greutate_volumetrica_colet'], 2)
            info = f"Physic: {g_f}kg | Vol: {g_v}kg | Tax: {max(g_f, g_v)}kg | Efic: {round(colet['grad_umplere_colet']*100, 1)}%"
            pdf.cell(0, 6, info, border="B", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

            pdf.set_font(font_familie, "B", 10)
            pdf.cell(w_cant, 7, "Qty", border =1, new_x="RIGHT", new_y="TOP", align='C')
            pdf.cell(w_prod, 7, "Code / Article description", border =1, new_x="LMARGIN", new_y="NEXT", align='L')

            pdf.set_font(font_familie, "", 10)
            for cheie, cant in colet['produse'].items():
                cod, nume = cheie.split("||")
                nume_pdf = nume.encode('latin-1', 'ignore').decode('latin-1')
                text_complet = f"{cod} - {nume_pdf}"

                lines = pdf.multi_cell(w_prod, 5, text_complet, dry_run=True, output="LINES")
                h_line = 5
                h_cell = max(7, len(lines) * h_line)
                
                if pdf.get_y() + h_cell > 270:
                    pdf.add_page()
                    pdf.set_font(font_familie, "B", 9)
                    pdf.cell(w_cant, 7, "Qty.", border=1, new_x="RIGHT", new_y="TOP", align ='C')
                    pdf.cell(w_prod, 7, "Code / Article description", border=1, new_x="LMARGIN", new_y="NEXT", align='L')
                    pdf.set_font(font_familie, "", 9)
                    
                curr_x = pdf.get_x()
                curr_y = pdf.get_y()
                pdf.cell(w_cant, h_cell, str(cant), border=1, align='C')
                pdf.set_xy(curr_x + w_cant, curr_y)
                pdf.rect(curr_x + w_cant, curr_y, w_prod, h_cell)
                pdf.multi_cell(w_prod, h_line, text_complet, border=0, align='L')
                pdf.set_y(curr_y + h_cell)
            pdf.ln(6)

        pdf_output = pdf.output()
        if isinstance(pdf_output, str):
            return pdf_output.encode('latin-1')
        return bytes(pdf_output)

    def reseteaza_rezultatele():
        st.session_state.rezultate_calcul = None

    def calculeaza_ambalare_complexa(df_comanda, factor_volumetric=5000):
        query_cutii = "SELECT * FROM cutii ORDER BY (l_int * w_int * h_int) DESC"
        toate_cutiile = pd.read_sql(query_cutii, conn)
        
        toate_cutiile['vol_int_calculat'] = toate_cutiile['l_int'] * toate_cutiile['w_int'] * toate_cutiile['h_int']
        toate_cutiile_sortate = toate_cutiile.sort_values(by='vol_int_calculat', ascending=False).reset_index(drop=True)

        print(f"\n[DEBUG 1] Baza de date conține {len(toate_cutiile_sortate)} tipuri de cutii.")
        print(f"[DEBUG 1] Top 3 cele mai mari cutii pregătite: {toate_cutiile_sortate['cod_cutie'].head(3).tolist()}")

        # --- PAS 1: GRUPARE PE FAMILII DE DIMENSIUNI (CAZUL A - AUTO-AMBALAJ) ---
        familii_produse = []
        
        for cod_art, grup in df_comanda.groupby('Cod Articol'):
            cantitate_totala = grup['Cantitate'].sum()
            res = pd.read_sql(f"SELECT * FROM articole WHERE cod_articol = '{cod_art}'", conn)
            if not res.empty:
                info = res.iloc[0]
                
                # Sistem de protecție: Caută coloanele noi, dacă nu le ai încă în DB, folosește-le pe cele vechi
                col_l = 'lungime_ambalaj' if 'lungime_ambalaj' in info.index else 'lungime_cm'
                col_w = 'latime_ambalaj' if 'latime_ambalaj' in info.index else 'latime_cm'
                col_h = 'inaltime_ambalaj' if 'inaltime_ambalaj' in info.index else 'inaltime_cm'
                col_g = 'greutate_ambalaj_inclus' if 'greutate_ambalaj_inclus' in info.index else 'greutate_bruta'

                l_item = float(info[col_l])
                w_item = float(info[col_w])
                h_item = float(info[col_h])
                g_item = float(info[col_g])

                familii_produse.append({
                    'cod': cod_art,
                    'denumire': info['denumire'],
                    'dimensiuni': (l_item, w_item, h_item),
                    'greutate': g_item,
                    'cantitate': int(cantitate_totala),
                    'volum_unitar': l_item * w_item * h_item
                })

        def ruleaza_simulare(strategie_mixare="AGRESIV"):
            print("\n" + "█"*60)
            print(f"🚀 START SIMULARE: {strategie_mixare}")
            print("█"*60 + "\n")
            
            stoc_ramas = {f['cod']: f['cantitate'] for f in familii_produse}
            detalii_mix_simulare = []

            # --- PAS 3: AMBALARE CICLICĂ ---
            while sum(stoc_ramas.values()) > 0:
                toate_familiile_disponibile = []
                for f in familii_produse:
                    if stoc_ramas[f['cod']] > 0:
                        f_temp = f.copy()
                        f_temp['cantitate_curenta'] = stoc_ramas[f['cod']]
                        toate_familiile_disponibile.append(f_temp)
                toate_familiile_disponibile.sort(key=lambda x: x['volum_unitar'], reverse=True)

                if not toate_familiile_disponibile: break
                
                # --- SCANARE BRUTĂ DIMENSIUNI ARTICOLE ---
                print("\n🔍 --- ANALIZĂ DIMENSIUNI ÎN COȘ ---")
                for f in toate_familiile_disponibile:
                    dim = f['dimensiuni'] # Aceasta este lista [L, W, H]
                    vol_calc = f['volum_unitar']
                    print(f"Articol: {f['cod']} | Cant: {f['cantitate_curenta']} | Dimensiuni: {dim} | Volum: {vol_calc}")
                print("------------------------------------\n")

                volum_maxim_grup = toate_familiile_disponibile[0]['volum_unitar']
                #familii_active = [f for f in toate_familiile_disponibile if f['volum_unitar'] == volum_maxim_grup]
                
                # Luăm dimensiunile de referință ale primei piese (L, W, H)
                dim_referinta = toate_familiile_disponibile[0]['dimensiuni']

                # Familia activă va conține TOATE piesele care au ACELEAȘI dimensiuni fizice
                familii_active = [
                    f for f in toate_familiile_disponibile 
                    if f['dimensiuni'] == dim_referinta
                ]

                # --- DEBUG EXACT PE COLECTIA TA ---
                print(f"DEBUG: Toate familiile disponibile: {[(f['cod'], f['cantitate_curenta']) for f in toate_familiile_disponibile]}")
                print(f"DEBUG: Familia activa aleasa (volum max): {volum_maxim_grup}")
                print(f"DEBUG: Piese trimise spre testare: {sum([f['cantitate_curenta'] for f in familii_active])}")
                lista_pentru_pack = toate_familiile_disponibile.copy()

                optiuni_pas_curent = []
                print(f"\n--- PAS NOU AMBALARE: Mai avem {sum(stoc_ramas.values())} piese de pus ---")
                
                #toate_cutiile_sortate = toate_cutiile.sort_values(by=['l_ext', 'w_ext', 'h_ext'], ascending=False)
                # Sortăm după volumul interior calculat, de la cel mai mare la cel mai mic
                toate_cutiile_sortate = toate_cutiile.sort_values(by='vol_int_calculat', ascending=False)

                for idx, c in toate_cutiile_sortate.iterrows():
                    packer = Packer()
                    bin_test = Bin(c['cod_cutie'], float(c['l_int'])-0.05, float(c['w_int'])-0.05, float(c['h_int'])-0.05, float(c['sarcina_maxima']))
                    packer.add_bin(bin_test)

                    for f in familii_active:
                        for i in range(f['cantitate_curenta']):
                            nume_item = f"{f['cod']}_{i}||{f['denumire']}"
                            item_test = Item(nume_item, f['dimensiuni'][0]-0.05, f['dimensiuni'][1]-0.05, f['dimensiuni'][2]-0.05, f['greutate'])
                            packer.add_item(item_test)
                    
                    if strategie_mixare == "AGRESIV":
                        for f in lista_pentru_pack:
                            if f['volum_unitar'] < volum_maxim_grup:
                                for i in range(f['cantitate_curenta']):
                                    nume_item = f"{f['cod']}_{i}||{f['denumire']}"
                                    item_test = Item(nume_item, f['dimensiuni'][0]-0.05, f['dimensiuni'][1]-0.05, f['dimensiuni'][2]-0.05, f['greutate'])
                                    packer.add_item(item_test)
                    
                    packer.pack(bigger_first=True)

                    for i, (idx_2, c_2) in enumerate(toate_cutiile_sortate.iterrows(), 1):
                        if c_2['cod_cutie'] == c['cod_cutie']: 
                            prefix = "🌟 [CEA MAI MARE]" if i == 1 else f"📦 [TEST {i}]"
                            if len(bin_test.items) > 0:
                                print(f"{prefix} Cutia {c['cod_cutie']} (Vol: {c_2['vol_int_calculat']:.0f}) poate lua {len(bin_test.items)} piese.")
                    
                    if bin_test.items:
                        are_prioritar = any(it.name.split('_')[0] in [f['cod'] for f in familii_active if f['volum_unitar'] == volum_maxim_grup] for it in bin_test.items)
                        if are_prioritar:
                            volum_marfa_incarcata = sum([(float(it.width) + 0.05) * (float(it.height) + 0.05) * (float(it.depth) + 0.05) for it in bin_test.items ])
                            g_f = float(c.get('greutate_cutie_goala', 0)) + sum([float(i.weight) for i in bin_test.items])
                            g_v = (float(c['l_ext']) * float(c['w_ext']) * float(c['h_ext'])) / factor_volumetric
                            
                            optiuni_pas_curent.append({
                                'bin': bin_test, 'info': c, 'nr': len(bin_test.items), 'volum_marfa': volum_marfa_incarcata,
                                'g_tax': max(g_f, g_v), 'g_f': g_f, 'g_v': g_v
                            })

                if not optiuni_pas_curent: break
                
                if optiuni_pas_curent:
                    for opt in optiuni_pas_curent:
                        vol_util_cutie = float(opt['info']['l_int']) * float(opt['info']['w_int']) * float(opt['info']['h_int'])
                        umplere = opt['volum_marfa'] / vol_util_cutie if vol_util_cutie > 0 else 0
                        este_manusa = 1 if umplere >= 0.85 else 0
                        # --- AICI ADAUGĂM LINIA DE BONUS ---
                        # Dacă numărul de piese din acest test (opt['nr']) este egal cu 
                        # totalul pieselor rămase (sum(stoc_ramas.values())), dăm bonus 100
                        bonus_finalizare = 100 if opt['nr'] == sum(stoc_ramas.values()) else 0
                        # Punem bonus_finalizare pe a doua poziție în tuplu
                        #opt['scor_complex'] = (este_manusa, bonus_finalizare, opt['nr'], umplere, -opt['g_tax'])
                        #opt['scor_complex'] = (opt['nr'], este_manusa, umplere, -opt['g_tax'])

                        opt['scor_complex'] = (bonus_finalizare, este_manusa, opt['nr'],  umplere, -opt['g_tax'])

                    pas_ales = max(optiuni_pas_curent, key=lambda x: x['scor_complex'])
                    print(f"✅ DECIZIE COLET: Am ales {pas_ales['info']['cod_cutie']} (Scor: {pas_ales['scor_complex']})")
                
                if optiuni_pas_curent:
                    pas_ales = max(optiuni_pas_curent, key=lambda x: x['scor_complex'])
                    c_finala = pas_ales['info']
                
                produse_in_colet = {}
                for it in pas_ales['bin'].items:
                    parti = it.name.split("||")
                    cod_id = parti[0] 
                    den_art = parti[1] if len(parti) > 1 else ""
                    cod_curat = cod_id.rsplit('_', 1)[0]
                    
                    if cod_curat in stoc_ramas:
                        stoc_ramas[cod_curat] -= 1
                    
                    cheie_pentru_interfata = f"{cod_curat}||{den_art}"
                    produse_in_colet[cheie_pentru_interfata] = produse_in_colet.get(cheie_pentru_interfata, 0) + 1

                vol_p = sum([float(i.width)*float(i.height)*float(i.depth) for i in pas_ales['bin'].items])
                vol_c = float(c_finala['l_int'])*float(c_finala['w_int'])*float(c_finala['h_int'])
                
                detalii_mix_simulare.append({
                    'produse': produse_in_colet, 'greutate_fizica_colet': pas_ales['g_f'],
                    'greutate_volumetrica_colet': pas_ales['g_v'], 'grad_umplere_colet': vol_p / vol_c if vol_c > 0 else 0,
                    'l_ext': c_finala['l_ext'], 'w_ext': c_finala['w_ext'], 'h_ext': c_finala['h_ext'],
                    'l_int': c_finala['l_int'], 'w_int': c_finala['w_int'], 'h_int': c_finala['h_int'], 'cod_cutie': c_finala['cod_cutie']
                })

            # --- ETAPA DE RAFINARE ---
            if len(detalii_mix_simulare) > 1:
                ultimul_colet = detalii_mix_simulare[-1]
                produse_de_mutat = []
                for nume_full, cant in ultimul_colet['produse'].items():
                    for _ in range(cant):
                        produse_de_mutat.append(nume_full)

                index_colete_sortate = sorted(range(len(detalii_mix_simulare) - 1), 
                                            key=lambda i: detalii_mix_simulare[i]['grad_umplere_colet'])

                pentru_mutat_cu_succes = []

                for nume_produs in produse_de_mutat:
                    mutat = False
                    cod_p, den_p = nume_produs.split("||")
                    
                    for i in index_colete_sortate:
                        colet_tinta = detalii_mix_simulare[i]
                        if colet_tinta['grad_umplere_colet'] > 0.99:
                            continue
                            
                        info_cutie = toate_cutiile[toate_cutiile['cod_cutie'] == colet_tinta['cod_cutie']].iloc[0]
                        p_reface = Packer()
                        b_reface = Bin(colet_tinta['cod_cutie'], float(colet_tinta['l_int'])-0.05, float(colet_tinta['w_int'])-0.05, float(colet_tinta['h_int'])-0.05, 30.0)
                        p_reface.add_bin(b_reface)

                        for p_existent, c_existenta in colet_tinta['produse'].items():
                            f_info = next(f for f in familii_produse if f['cod'] == p_existent.split("||")[0])
                            for _ in range(c_existenta):
                                p_reface.add_item(Item(p_existent, f_info['dimensiuni'][0]-0.05, f_info['dimensiuni'][1]-0.05, f_info['dimensiuni'][2]-0.05, f_info['greutate']))
                        
                        f_nou = next(f for f in familii_produse if f['cod'] == cod_p)
                        p_reface.add_item(Item(nume_produs, f_nou['dimensiuni'][0]-0.05, f_nou['dimensiuni'][1]-0.05, f_nou['dimensiuni'][2]-0.05, f_nou['greutate']))
                        
                        p_reface.pack(bigger_first=True)

                        if len(p_reface.bins[0].items) > sum(colet_tinta['produse'].values()):
                            colet_tinta['produse'][nume_produs] = colet_tinta['produse'].get(nume_produs, 0) + 1
                            colet_tinta['greutate_fizica_colet'] += f_nou['greutate']
                            vol_total_produse = 0
                            for p_nume, p_cant in colet_tinta['produse'].items():
                                c_p = p_nume.split("||")[0]
                                info_p = next(f for f in familii_produse if f['cod'] == c_p)
                                vol_total_produse += info_p['volum_unitar'] * p_cant
                            
                            vol_intern_cutie = float(colet_tinta['l_int']) * float(colet_tinta['w_int']) * float(colet_tinta['h_int'])
                            colet_tinta['grad_umplere_colet'] = vol_total_produse / vol_intern_cutie if vol_intern_cutie > 0 else 0
                            
                            mutat = True
                            pentru_mutat_cu_succes.append(nume_produs)
                            break
                    
                if len(pentru_mutat_cu_succes) == len(produse_de_mutat):
                    detalii_mix_simulare.pop() 
                else:
                    for p_mutat in pentru_mutat_cu_succes:
                        ultimul_colet['produse'][p_mutat] -= 1
                        if ultimul_colet['produse'][p_mutat] == 0:
                            del ultimul_colet['produse'][p_mutat]

            # --- POST-PROCESARE: AUTO-AMBALAJ PENTRU CUTIILE MAMA CU 1 PIESĂ ---
            pentru_retur = []
            for colet in detalii_mix_simulare:
                if sum(colet['produse'].values()) == 1:
                    # E o singură piesă în cutie, anulăm cutia mamă!
                    nume_produs = list(colet['produse'].keys())[0]
                    cod_curat_produs = nume_produs.split("||")[0]
                    info_p = next(f for f in familii_produse if f['cod'] == cod_curat_produs)
                    
                    pentru_retur.append({
                        'produse': colet['produse'], 
                        'greutate_fizica_colet': info_p['greutate'],
                        'greutate_volumetrica_colet': info_p['volum_unitar'] / factor_volumetric, 
                        'grad_umplere_colet': 1.0,
                        'l_ext': info_p['dimensiuni'][0], 'w_ext': info_p['dimensiuni'][1], 'h_ext': info_p['dimensiuni'][2],
                        'l_int': info_p['dimensiuni'][0], 'w_int': info_p['dimensiuni'][1], 'h_int': info_p['dimensiuni'][2], 
                        'cod_cutie': 'AUTO-AMBALAJ'
                    })
                else:
                    pentru_retur.append(colet)

            return pentru_retur
        
        # --- PAS 4: RULARE SIMULĂRI (3 SCENARII) ---
        print("SIMULARE 1: Testez Scenariul AGRESIV (Mixare totală)...")
        sim_agresiv = ruleaza_simulare("AGRESIV")
        
        print("SIMULARE 2: Testez Scenariul PROTECTIV (Fidelitate pe Cutie)...")
        sim_protectiv = ruleaza_simulare("PROTECTIV")
        
        # --- NOU: SCENARIUL 3 (INDIVIDUALISTUL) ---
        print("\n" + "█"*60)
        print("🚀 START SIMULARE 3: INDIVIDUAL (Fără cutii mamă)")
        print("█"*60 + "\n")
        sim_individual = []
        for f in familii_produse:
            for _ in range(f['cantitate']):
                produse_in_colet = {f"{f['cod']}||{f['denumire']}": 1}
                sim_individual.append({
                    'produse': produse_in_colet,
                    'greutate_fizica_colet': f['greutate'],
                    'greutate_volumetrica_colet': f['volum_unitar'] / factor_volumetric,
                    'grad_umplere_colet': 1.0, # Mănușă perfectă
                    'l_ext': f['dimensiuni'][0], 'w_ext': f['dimensiuni'][1], 'h_ext': f['dimensiuni'][2],
                    'l_int': f['dimensiuni'][0], 'w_int': f['dimensiuni'][1], 'h_int': f['dimensiuni'][2],
                    'cod_cutie': 'AUTO-AMBALAJ'
                })

        #introducem aici
        # Punem cele 3 simulări într-o listă pe care o va citi codul de mai jos
        st.session_state.rezultate_calcul = [
            {
                "nume_scenariu": "AGRESIV",
                "eticheta_logica": "🔥 OPTIMIZARE VOLUM - scenariu AGRESIV",
                "detalii_containere": sim_agresiv,
                #"greutate_taxabila_totala": sum([max(c['greutate_fizica_colet'], c['greutate_volumetrica_colet']) for c in sim_agresiv]),
                "greutate_taxabila_totala": round(sum([max(c['greutate_fizica_colet'], c['greutate_volumetrica_colet']) for c in sim_agresiv]), 2),
                "nr_total_cutii": len(sim_agresiv)
            },
            {
                "nume_scenariu": "PROTECTIV",
                "eticheta_logica": "🛡️ FIDELITATE PRODUSE - scenariu PROTECTIV",
                "detalii_containere": sim_protectiv,
                #"greutate_taxabila_totala": sum([max(c['greutate_fizica_colet'], c['greutate_volumetrica_colet']) for c in sim_protectiv]),
                "greutate_taxabila_totala": round(sum([max(c['greutate_fizica_colet'], c['greutate_volumetrica_colet']) for c in sim_protectiv]), 2),
                "nr_total_cutii": len(sim_protectiv)
            },
            {
                "nume_scenariu": "INDIVIDUAL",
                "eticheta_logica": "📦 FĂRĂ CUTII COLECTIVE - scenariu INDIVIDUAL",
                "detalii_containere": sim_individual,
                #"greutate_taxabila_totala": sum([max(c['greutate_fizica_colet'], c['greutate_volumetrica_colet']) for c in sim_individual]),
                "greutate_taxabila_totala": round(sum([max(c['greutate_fizica_colet'], c['greutate_volumetrica_colet']) for c in sim_individual]), 2),
                "nr_total_cutii": len(sim_individual)
            }
        ]

        # --- MATRICEA DE DECIZIE (Tie-Breaker Complex) ---
        toate_simularile = [
            {"nume": "Opțiunea 1: AGRESIV (Minimizare Colete)", "detalii": sim_agresiv},
            {"nume": "Opțiunea 2: PROTECTIV (Fidelitate Cutie)", "detalii": sim_protectiv},
            {"nume": "Opțiunea 3: INDIVIDUAL (Auto-Ambalaj)", "detalii": sim_individual}
        ]
        
        for sim in toate_simularile:
            # 1. Calculăm Costul Proxy (Suma Greutăților Taxabile)
            sim['cost_kg'] = round(sum([max(d['greutate_fizica_colet'], d['greutate_volumetrica_colet']) for d in sim['detalii']]), 2)
            # 2. Număr de cutii
            sim['nr_cutii'] = len(sim['detalii'])
            # 3. Grad mediu de umplere
            sim['fill_rate'] = sum([d['grad_umplere_colet'] for d in sim['detalii']]) / sim['nr_cutii'] if sim['nr_cutii'] > 0 else 0

        # Sortează pentru a găsi varianta cu CEL MAI MIC COST
        variante_dupa_cost = sorted(toate_simularile, key=lambda x: (x['cost_kg'], x['nr_cutii']))
        
        # Sortează pentru a găsi varianta cu CELE MAI PUȚINE COLETE
        variante_dupa_nr_cutii = sorted(toate_simularile, key=lambda x: (x['nr_cutii'], x['cost_kg']))

        # Extragem cele două perspective
        optiunea_cost = variante_dupa_cost[0]
        optiunea_logistica = variante_dupa_nr_cutii[0]

        # Construim lista finală de afișat (eliminăm duplicatele dacă varianta e aceeași)
        variante_finale = []

        # Luăm datele direct din ce am pregătit deja în session_state
        for v in st.session_state.rezultate_calcul:
            # Calculăm gradul mediu de umplere pentru varianta respectivă
            nr_cutii = len(v['detalii_containere'])
            grad_mediu = sum([c['grad_umplere_colet'] for c in v['detalii_containere']]) / nr_cutii if nr_cutii > 0 else 0

        
            # Adăugăm Opțiunea Cost (întotdeauna prima)
            variante_finale.append({
                #'eticheta_logica': "💰 CEL MAI MIC COST (FedEx)",
                'eticheta_logica': v['eticheta_logica'],
                #'nume_scenariu': optiunea_cost['nume'],
                'nume_scenariu': v['nume_scenariu'],
                #'cod_cutie': f"Optim Cost ({optiunea_cost['nume']})",
                'cod_cutie': v['nume_scenariu'],
                #'nr_total_cutii': optiunea_cost['nr_cutii'],
                'nr_total_cutii': v['nr_total_cutii'],
                #'detalii_containere': optiunea_cost['detalii'],
                'detalii_containere': v['detalii_containere'],
                #'greutate_taxabila_totala': optiunea_cost['cost_kg'],
                'greutate_taxabila_totala': v['greutate_taxabila_totala'],
                #'grad_umplere': optiunea_cost['fill_rate'],
                'grad_umplere': grad_mediu,
                #'l_ext': optiunea_cost['detalii'][0]['l_ext'],
                #'w_ext': optiunea_cost['detalii'][0]['w_ext'],
                #'h_ext': optiunea_cost['detalii'][0]['h_ext']
                # Luăm dimensiunile primei cutii pentru referință în titlu
                'l_ext': v['detalii_containere'][0]['l_ext'] if v['detalii_containere'] else 0,
                'w_ext': v['detalii_containere'][0]['w_ext'] if v['detalii_containere'] else 0,
                'h_ext': v['detalii_containere'][0]['h_ext'] if v['detalii_containere'] else 0
            })
        return variante_finale

        # Adăugăm Opțiunea Logistică doar dacă este diferită de prima
        #if optiunea_logistica['nume'] != optiunea_cost['nume']:
        # OPȚIUNEA 2: Afișată doar dacă oferă un avantaj logistic (mai puține cutii) față de prima
        if optiunea_logistica['nr_cutii'] < optiunea_cost['nr_cutii']:
            variante_finale.append({
                'eticheta_logica': "📦 CONSOLIDARE MAXIMĂ (Eficiență Depozit)",
                'nume_scenariu': optiunea_logistica['nume'],
                'cod_cutie': f"Optim Logistic ({optiunea_logistica['nume']})",
                'nr_total_cutii': optiunea_logistica['nr_cutii'],
                'detalii_containere': optiunea_logistica['detalii'],
                #'greutate_taxabila_totala': optiunea_logistica['greutate_taxabila_totala'], # corectat din cost_kg
                'greutate_taxabila_totala': optiunea_logistica['cost_kg'],
                'grad_umplere': optiunea_logistica['fill_rate'],
                'l_ext': optiunea_logistica['detalii'][0]['l_ext'],
                'w_ext': optiunea_logistica['detalii'][0]['w_ext'],
                'h_ext': optiunea_logistica['detalii'][0]['h_ext']
            })
        elif len(toate_simularile) > 1 and optiunea_cost['nume'] == "INDIVIDUAL":
            # Dacă varianta de cost e INDIVIDUAL, punem ca a doua opțiune cea mai bună consolidare găsită
            # Chiar dacă e mai scumpă, pentru a oferi alternativa de "1 singur colet"
            consolidari = [s for s in toate_simularile if s['nume'] != "INDIVIDUAL"]
            if consolidari:
                best_cons = sorted(consolidari, key=lambda x: (x['nr_cutii'], x['cost_kg']))[0]
                variante_finale.append({
                    'eticheta_logica': "📦 VARIANTA B: CONSOLIDARE (Un singur colet)",
                    'nume_scenariu': best_cons['nume'],
                    'nr_total_cutii': best_cons['nr_cutii'],
                    'detalii_containere': best_cons['detalii'],
                    'greutate_taxabila_totala': best_cons['cost_kg'],
                    'grad_umplere': best_cons['fill_rate']
                })

        return variante_finale

    def get_pret_fedex(denumire_en, greutate, serviciu='IP'):
        is_per_kg = greutate >= 71.0
        greutate_cautata = 71.0 if is_per_kg else greutate
        tip_tarif = 'PER_KG' if is_per_kg else 'FIX'
        query = f"""
        SELECT DISTINCT ON (f.serviciu)
            f.pret
        FROM public.tari t
        JOIN public.fedex_tarife f ON (
            (f.serviciu = 'IP' AND f.zona = t.zona_ip) OR 
            (f.serviciu = 'IE' AND f.zona = t.zona_ie)
        )
        WHERE t.denumire_en = '{denumire_en}'
        AND f.serviciu = '{serviciu}'
        AND f.tip_colet = 'PACKAGE'
        AND f.tip_tarif = '{tip_tarif}'
        AND f.greutate_max >= {greutate_cautata}
        ORDER BY f.serviciu, f.greutate_max ASC
        """
        try:
            res = pd.read_sql(query, conn)
            if not res.empty:
                pret_unitar = res.iloc[0]['pret']
                return round(pret_unitar * greutate if is_per_kg else pret_unitar,2)
        except:
            return 0
        return 0

    @st.cache_data 
    def get_lista_articole():
        query = "SELECT cod_articol, denumire FROM articole"
        df_art = pd.read_sql(query, conn)
        df_art['display_name'] = df_art['cod_articol'].astype(str) + " | " + df_art['denumire'].astype(str)
        return df_art

    df_articole = get_lista_articole()

    st.subheader("📍 Detalii Expediție")

    df_tari_disponibile = get_tari()

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        tara_selectata = st.selectbox(
            "Alegeți Țara de Destinație:",
            options=df_tari_disponibile['display_name'].tolist(),
            index=None,
            placeholder="Căutați țara...",
            key="destinatie_tara",
            on_change=reseteaza_rezultatele
        )
        if tara_selectata:
            info_tara = df_tari_disponibile[df_tari_disponibile['display_name'] == tara_selectata].iloc[0]
            img_url = f"https://flagcdn.com/w80/{info_tara['cod_tara'].lower()}.png"
            
            st.markdown(f"""
                <div style="background-color:#e8f4f8; padding:15px; border-radius:8px; border-left: 5px solid #0072b1;">
                    <img src="{img_url}" style="vertical-align:middle; margin-right:10px; border:1px solid #ccc; border-radius:2px;" width="45">
                    <span style="font-size:18px; font-weight:bold; color:#0f5132; vertical-align:middle;">
                        Country detected: {info_tara['denumire_ro']}
                    </span>
                    <br>
                    <span style="font-size:14px; color:#666; margin-left:55px;">
                    </span>
                </div>
            """, unsafe_allow_html=True)
            
    with col2:
        if tara_selectata:
            info_tara = df_tari_disponibile[df_tari_disponibile['display_name'] == tara_selectata].iloc[0]
            este_ue = "🇪🇺 Membru UE" if info_tara['membru_ue'] else "🌍 Non-UE - (Vamă)"
            st.info(f"**Regim de livrare:**\n\n{este_ue}")
            st.code(f"Cod FedEx: {info_tara['cod_tara']}", language=None)
        else:
            st.write("##") 
            st.caption("Selectați o țară pentru a vedea regimul de livrare.")

    with col3:
        st.write("⚙️ Taxa suplimentara de combustibil")
        factor_combustibil = st.number_input(
            "Procent Combustibil (%)", 
            value=34.0, 
            step=0.1, 
            format="%.1f",
            help="Procentul adăugat la prețul de bază FedEx",
            key="factor_combustibil_input", 
            on_change=reseteaza_rezultatele
        )
        procent_combustibil = 1 + (factor_combustibil / 100)

    st.divider() 

    st.subheader("📋 Introducere Produse Comandă")

    if 'lista_cumparaturi' not in st.session_state:
        st.session_state.lista_cumparaturi = []
    if 'cantitate_produs' not in st.session_state:
        st.session_state.cantitate_produs = 1
    if 'selectie_produs' not in st.session_state:
        st.session_state.selectie_produs = None
    if 'trigger_reset' not in st.session_state:
        st.session_state.trigger_reset = False

    if st.session_state.trigger_reset:
        st.session_state.cantitate_produs = 1
        st.session_state.selectie_produs = None
        st.session_state.trigger_reset = False

    def goleste_tot():
        st.session_state.lista_cumparaturi = []
        st.session_state.cantitate_produs = 1
        st.session_state.selectie_produs = None
        st.session_state.rezultate_calcul = None

    with st.form("formular_adaugare", clear_on_submit=False):
        col_a, col_b, col_c = st.columns([3, 1, 1])

        with col_a:
            selectie = st.selectbox(
                "Caută Articol (tastați Cod sau Denumire):", 
                options=df_articole['display_name'].tolist(),
                index=None,
                placeholder="Scrieți aici...",
                key="selectie_produs"
            )

        with col_b:
            cant_input = st.number_input("Cantitate:", min_value=1, key="cantitate_produs")

        with col_c:
            st.write("##") 
            buton_adaugare = st.form_submit_button("Adaugă în listă", use_container_width=True)

        if buton_adaugare:
            if st.session_state.selectie_produs is None:
                st.warning("Nu ați selecționat niciun articol!")
            else:
                if 'tabel_cos' in st.session_state:
                    if 'df_cos_editat' in locals():
                        st.session_state.lista_cumparaturi = df_cos_editat.to_dict('records')
                
                cod_extras = st.session_state.selectie_produs.split(" | ")[0].strip()
                st.session_state.lista_cumparaturi.append({
                    "Cod": cod_extras, 
                    "Cantitate": st.session_state.cantitate_produs
                })
                
                st.session_state.trigger_reset = True
                st.rerun()
    
    if st.session_state.lista_cumparaturi:
        st.write("### Articole în coș:")
        df_cos = pd.DataFrame(st.session_state.lista_cumparaturi)
        
        df_cos_editat = st.data_editor(df_cos, num_rows="dynamic", key="tabel_cos", on_change=sincronizeaza_tabel)
        
        st.write("---")
        c_btn1, c_btn2, c_info, c_input = st.columns([1, 1, 2, 1])

        with c_btn1:
            st.button("🗑️ Golește Coșul",  use_container_width=True, on_click=goleste_tot)
        
        with c_btn2:
            btn_calcul = st.button("🔥 Calculează Ambalarea", use_container_width=True)

        with c_info:
            st.info("💡 **Formula:** (L x l x Î) cm / Factor volumetric")
        
        with c_input:
            v_factor = st.number_input("Factor Volumetric", value=5000, step=500,key="v_factor_input", on_change=reseteaza_rezultatele)
        
        if 'rezultate_calcul' not in st.session_state:
            st.session_state.rezultate_calcul = None
        
        trebuie_calculat = False
        if btn_calcul:
            trebuie_calculat = True
        elif st.session_state.lista_cumparaturi and st.session_state.rezultate_calcul is None:
            trebuie_calculat = True

        if trebuie_calculat:
            if not tara_selectata:
                st.warning("⚠️ Vă rugăm să selectați o țară de destinație pentru a calcula tarifele!")
            else:
                with st.spinner('Actualizăm ambalarea și tarifele...'):
                    rezultate = calculeaza_ambalare_complexa(
                        df_cos_editat.rename(columns={"Cod": "Cod Articol"}), 
                        factor_volumetric=v_factor
                    )
                    
                    st.session_state.rezultate_calcul = rezultate
                    st.session_state.factor_folosit = v_factor

                    if rezultate:
                        st.success(f"✅ Configurație Actualizată! (Calculat cu factor {v_factor})")
                    st.write("---")
        # DEBUG: Verificăm câte variante avem în listă
        if st.session_state.rezultate_calcul:
            st.write(f"🔍 DEBUG: Am găsit {len(st.session_state.rezultate_calcul)} variante în listă.")
            for i, r in enumerate(st.session_state.rezultate_calcul):
                st.write(f"📍 Poziția {i}: {r.get('nume_scenariu')} - {r.get('nr_total_cutii')} colete")

        if st.session_state.rezultate_calcul:
            rezultate = st.session_state.rezultate_calcul
            v_f = st.session_state.get('factor_folosit', v_factor)
            
            st.write("### ⚖️ Analiză Comparativă Opțiuni:")
                
            for idx, var in enumerate(rezultate[:3]):
                nr_cutii = var['nr_total_cutii']
                cod_c = var['cod_cutie']
                greutate_totala = round(var['greutate_taxabila_totala'], 2)
                dimensiuni = f"{int(var['l_ext'])}x{int(var['w_ext'])}x{int(var['h_ext'])} cm  - dimensiuni exterioare!)"
                
                pret_ip = 0
                pret_ie = 0
                
                if tara_selectata:
                    info_tara = df_tari_disponibile[df_tari_disponibile['display_name'] == tara_selectata].iloc[0]
                    nume_tara = info_tara['denumire_en']
                    # Folosim greutatea taxabilă calculată pentru această variantă specifică
                    greutate_tax = var.get('greutate_taxabila_totala', 0)
                    #greutate_tax = var['greutate_taxabila_totala']
                    pret_ip_baza = get_pret_fedex(info_tara['denumire_en'], greutate_tax, 'IP')
                    pret_ie_baza = get_pret_fedex(info_tara['denumire_en'], greutate_tax, 'IE')
                    greutate_fizica_totala = sum([c['greutate_fizica_colet'] for c in var['detalii_containere']])
                    #pret_ip_baza = get_pret_fedex(info_tara['denumire_en'], greutate_totala, 'IP')
                    #pret_ie_baza = get_pret_fedex(info_tara['denumire_en'], greutate_totala, 'IE')

                    pret_ip = round(pret_ip_baza * procent_combustibil, 2)
                    pret_ie = round(pret_ie_baza * procent_combustibil, 2)

                    #label_pret = f" | 💰 IE: {pret_ie} € / IP: {pret_ip} €" if pret_ie > 0 else ""
                    #titlu_optiune = (
                    #    f"🏆 Opțiunea Optimă | 🌍 {tara_selectata} | "
                    #    f"📦 {var['nr_total_cutii']} colete | "
                    #    f"⚖️ {var['greutate_taxabila_totala']:.2f} kg tax. | "
                    #    f"💰 IE: {pret_ie:.2f} € | "
                    #    f"💸 IP: {pret_ip:.2f} €"
                    #)

                # Titlul expanderului cu eticheta logică (Cost vs Logistică) - CONSTRUIM TITLUL CARE INCLUDE PREȚURILE (Să fie vizibile fără click)
                text_preturi = f" | 💰 IE: {pret_ie}€ / IP: {pret_ip}€" if pret_ie > 0 else ""
                titlu_expander = f"{var['eticheta_logica']} | 📦 {nr_cutii} Col | ⚖️ {greutate_tax} kg tax.{text_preturi}"
                #titlu_expander = f"{var['eticheta_logica']} | {var['nr_total_cutii']} Colete | Total {var['greutate_taxabila_totala']} kg tax."

                #with st.expander(titlu_optiune, expanded=(idx == 0)):
                with st.expander(titlu_expander, expanded=(idx == 0)):
                    st.write("---")
                    st.write(f"*Prețurile includ taxa de combustibil (Fuel Surcharge) de **{factor_combustibil}%***")
                    if pret_ip > 0:
                        c1, c2 = st.columns(2)
                        with c1:
                            c1.metric("FedEx International Economy (IE)", f"{pret_ie} EUR", "Economic")
                            st.write(f"**📍 Destinație:** {tara_selectata}")
                            st.write(f"**⚖️ Greutate Fizică Totală:** {round(greutate_fizica_totala, 2)} kg")
                        with c2:
                            c2.metric("FedEx International Priority (IP)", f"{pret_ip} EUR", "Rapid", delta_color="inverse")
                            st.write(f"**📐 Greutate Volumetrică Totală:** {round(sum([c['greutate_volumetrica_colet'] for c in var['detalii_containere']]), 2)} kg")
                            #st.write(f"**💰 Greutate Facturată:** {var['greutate_taxabila_totala']} kg")
                            st.write(f"**💰 Greutate Facturată:** {greutate_totala} kg")
                    # Afișare scenariu (folosim .get pentru siguranță)
                    scenariu = var.get('nume_scenariu', 'Nespecificat')
                    st.info(f"Strategia folosită: **{scenariu}**")
                    st.write("### 📦 Detalii per Colet și Instrucțiuni:")

                    # Buclă afișare colete
                    for i, colet in enumerate(var.get('detalii_containere', [])):
                        with st.container():
                            cod_box = colet.get('cod_cutie', 'N/A')
                            dim_box = f"{int(colet['l_ext'])}x{int(colet['w_ext'])}x{int(colet['h_ext'])} cm"
                            g_fizica = round(colet['greutate_fizica_colet'], 2)
                            g_vol = round(colet['greutate_volumetrica_colet'], 2)
                            g_tax = max(g_fizica, g_vol)
                            eficienta_colet = round(colet['grad_umplere_colet'] * 100, 1)
                            
                            icon_taxare = "⚖️" if g_fizica >= g_vol else "📐"
                            label_taxare = "Fizic" if g_fizica >= g_vol else "Volumetric"

                            culoare_baza = "#ff4b4b" if cod_box != "AUTO-AMBALAJ" else "#28a745"
                            
                            st.markdown(f"""
                                <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid {culoare_baza}; margin-bottom: 10px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <div>
                                            <span style="font-size: 18px; font-weight: bold;">📦 Coletul {i+1}</span><br>
                                            <small style="color: {culoare_baza}; font-weight: bold;">CUTIE: {cod_box} [{dim_box}]</small>
                                        </div>
                                        <span style="font-size: 14px; font-weight: bold; color: #555;">
                                            Eficiență: {eficienta_colet}% | {icon_taxare} Taxare: {label_taxare}
                                        </span>
                                    </div>
                                    <hr style="margin: 8px 0;">
                                    <div style="display: flex; justify-content: space-between; text-align: center;">
                                        <div style="flex: 1;"><small>Kg Fizic</small><br><b>{g_fizica}</b></div>
                                        <div style="flex: 1; border-left: 1px solid #ddd; border-right: 1px solid #ddd;"><small>Kg Volum</small><br><b>{g_vol}</b></div>
                                        <div style="flex: 1;"><small>Kg Taxabil</small><br><b style="color: {culoare_baza};">{g_tax}</b></div>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            st.progress(min(colet['grad_umplere_colet'], 1.0))
                            
                            for cheie, cant_p in colet['produse'].items():
                                cod_p, denumire_p = cheie.split("||")
                                st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;🔹 **{cant_p} buc.** x {cod_p} <i style='color: gray;'>({denumire_p})</i>", unsafe_allow_html=True)
                            st.write("---")
                    
                pdf_bytes = genereaza_pdf_ambalare(var, tara=tara_selectata, p_ip=pret_ip, p_ie=pret_ie, procent_fuel = factor_combustibil)
                st.download_button(
                    label=f"📥 Descarcă PDF Instrucțiuni Ambalare",
                    data=pdf_bytes,
                    file_name=f"ambalare_optima.pdf",
                    mime="application/pdf",
                    key=f"pdf_{idx}"
                )
                p_umplere = round(var.get('grad_umplere', 0) * 100, 1)
                st.write(f"📊 **Eficiență utilizare volum total: {p_umplere}%**")
                st.progress(min(var.get('grad_umplere', 0), 1.0))

elif st.session_state["authentication_status"] is False:
    st.error('Utilizator/parolă greșită')

elif st.session_state["authentication_status"] is None:
    st.warning('Introdu te rog datele de acces')
