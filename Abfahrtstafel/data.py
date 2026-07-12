import requests

import xml.etree.ElementTree as ET

from datetime import datetime
from flask import Flask, render_template, jsonify
from logging import getLogger

from Abfahrtstafel import app

logger = getLogger(__name__)

eva_nummer = str(8000263)

def news(eva_nummer=eva_nummer):
    """
    Sammelt alle aktuellen Störungs- und Infomeldungen (u.a. von zuginfo.nrw)
    für den gesamten Bahnhof aus der fchg-Live-API.
    """
    url_fchg = f"https://iris.noncd.db.de/iris-tts/timetable/fchg/{eva_nummer}"
    
    try:
        res_fchg = requests.get(url_fchg, timeout=5)
        if res_fchg.status_code != 200:
            return []
            
        root_fchg = ET.fromstring(res_fchg.text)
        
        # Ein Dictionary statt eines Sets nutzen
        eindeutige_meldungen = {}
        
        for m in root_fchg.findall('.//m'):
            text = m.get('cat')
            
            if text and not text.isdigit():
                # 1. Wir erstellen eine "bereinigte" Version nur zum Vergleichen intern
                # Hier schneiden wir temporär die Quelle und Punkte ab
                vergleichs_text = text.split(". (Quelle:")[0].split(" (Quelle:")[0]
                vergleichs_text = vergleichs_text.strip().rstrip('.')
                
                # 2. Logik zum Filtern:
                # Wenn wir das Thema noch gar nicht kennen, ODER wenn der neue Text 
                # länger ist (also die Version MIT Quelle darstellt), speichern wir ihn ab.
                if vergleichs_text not in eindeutige_meldungen:
                    eindeutige_meldungen[vergleichs_text] = text
                else:
                    # Falls der neue Text die Quelle enthält, hat er mehr Zeichen als der alte
                    if len(text) > len(eindeutige_meldungen[vergleichs_text]):
                        eindeutige_meldungen[vergleichs_text] = text
                
        # Am Ende geben wir nur die echten, längeren Originaltexte zurück
        return list(eindeutige_meldungen.values())
        
    except Exception as e:
        logger.error(f"Beim Auslesen der Nachrichten ist ein Fehler aufgetreten {e}")
        return []

def departures(eva_nummer=eva_nummer): # Sinzig ist 8005580
    jetzt = datetime.now()
    datum = jetzt.strftime("%y%m%d")
    stunde = jetzt.strftime("%H")
    
    url_plan = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva_nummer}/{datum}/{stunde}"
    url_fchg = f"https://iris.noncd.db.de/iris-tts/timetable/fchg/{eva_nummer}"
    
    try:
        # --- 1. Echtzeitdaten (fchg) abrufen ---
        live_linien = {}
        verspaetungen = {}
        
        res_fchg = requests.get(url_fchg, timeout=5)
        if res_fchg.status_code == 200:
            root_fchg = ET.fromstring(res_fchg.text)
            for stop in root_fchg.findall('s'):
                stop_id = stop.get('id')
                dp = stop.find('dp') # Departure
                ar = stop.find('ar') # Arrival
                
                # Live-Linie ermitteln (z.B. RB26)
                if dp is not None and dp.get('l'):
                    live_linien[stop_id] = dp.get('l')
                elif ar is not None and ar.get('l'):
                    live_linien[stop_id] = ar.get('l')
                
                # Verspätung erfassen
                if dp is not None and dp.get('ct') is not None:
                    verspaetungen[stop_id] = dp.get('ct')

        # --- 2. Plandaten (plan) abrufen ---
        res_plan = requests.get(url_plan, timeout=5)
        if res_plan.status_code != 200:
            return []
            
        root_plan = ET.fromstring(res_plan.text)
        departures_list = []
        
        # --- 3. Daten zusammenführen ---
        for stop in root_plan.findall('s'):
            dp = stop.find('dp') # Departure
            
            # Ohne Abfahrtsknoten ignorieren
            if dp is None:
                continue
                
            stop_id = stop.get('id')
            tl = stop.find('tl') # Trip Label
            
            # Geplante Abfahrtszeit ermitteln (Format 'pt': YYMMDDhhmm)
            print_time = dp.get('pt')
            geplant_zeit = f"{print_time[6:8]}:{print_time[8:10]}"
            
            # Fallback: Konstruktion aus Zuggattung und Zugnummer
            linie = "Zug"
            if tl is not None:
                zuggattung = tl.get('c', '') # z.B. ICE, RE
                zug_nr = tl.get('n', '')     # z.B. 620, 32035
                linie = f"{zuggattung} {zug_nr}".strip()
            
            # Bevorzuge schönere Linie aus Echtzeitdaten (falls vorhanden)
            linie = live_linien.get(stop_id, linie)
            
            # Neue Uhrzeit und Verspätung ermitteln
            time_format = "%y%m%d%H%M"
            print_time_dt = datetime.strptime(print_time, time_format)
            tatsaechlich = print_time_dt
            verspaetung_min = 0
            
            if stop_id in verspaetungen:
                changed_time = verspaetungen[stop_id]
                tatsaechlich = datetime.strptime(changed_time, time_format)
                diff = tatsaechlich - print_time_dt
                verspaetung_min = int(diff.total_seconds() / 60)
            
            # Route und Zielbahnhof auslesen
            stationen_string = dp.get('ppth', '')
            route_liste = stationen_string.split('|') if stationen_string else []
            ziel = route_liste[-1] if route_liste else "Unbekannt"
            
            # Abfahrt zur Liste hinzufügen
            departures_list.append({
                "linie": linie,
                "ziel": ziel,
                "gleis": dp.get('pp', '-'),
                "geplant": geplant_zeit,
                "tatsaechlich": tatsaechlich.strftime("%H:%M"),
                "verspaetung": max(0, verspaetung_min),
                "route": route_liste
            })
            
        # Abschließend chronologisch sortieren
        departures_list.sort(key=lambda x: x['geplant'])
        return departures_list
        
    except Exception:
        logger.error(f"Beim Abfragen der Abfahrten ist ein Fehler aufgetreten {e}")
        return []