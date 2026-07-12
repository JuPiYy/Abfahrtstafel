import requests

import xml.etree.ElementTree as ET

import re

from datetime import datetime, timedelta

from flask import Flask, render_template, jsonify
from logging import getLogger

from Abfahrtstafel import app

logger = getLogger(__name__)

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

    datum_aktuell = jetzt.strftime("%y%m%d")
    stunde_aktuell = jetzt.strftime("%H")

    naechste_stunde_dt = jetzt + timedelta(hours=1)
    datum_naechst = naechste_stunde_dt.strftime("%y%m%d")
    stunde_naechst = naechste_stunde_dt.strftime("%H")
    
    url_plan_1 = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva_nummer}/{datum_aktuell}/{stunde_aktuell}"
    url_plan_2 = f"https://iris.noncd.db.de/iris-tts/timetable/plan/{eva_nummer}/{datum_naechst}/{stunde_naechst}"
    print(url_plan_1, url_plan_2)
    url_fchg = f"https://iris.noncd.db.de/iris-tts/timetable/fchg/{eva_nummer}"
    
    try: 
        # --- 1. Echtzeitdaten (fchg) abrufen ---
        live_linien = {}
        verspaetungen = {}
        live_gleise = {}
        ausfaelle = {}
            
        res_fchg = requests.get(url_fchg, timeout=5)
        if res_fchg.status_code == 200:
            root_fchg = ET.fromstring(res_fchg.text)
            for stop in root_fchg.findall('s'):
                stop_id = stop.get('id')
                dp = stop.find('dp')
                ar = stop.find('ar')
                
                if dp is None:
                    continue
                # Live-Linie ermitteln (Zuerst 'fb' für Busse, sonst 'l')
                if dp is not None:
                    live_linien[stop_id] = dp.get('fb') or dp.get('l')
                elif ar is not None:
                    live_linien[stop_id] = ar.get('fb') or ar.get('l')
                    
                # Verspätung erfassen
                if dp is not None and dp.get('ct') is not None:
                    verspaetungen[stop_id] = dp.get('ct')

                if dp is not None and dp.get('cp') is not None:
                    live_gleise[stop_id] = dp.get('cp')

                # <-- HIER EINFÜGEN
                if dp is not None and dp.get('v') == 'c':
                    ausfaelle[stop_id] = True

        # --- 2. Plandaten (plan) für BEIDE Stunden abrufen ---
        alle_stops_xml = []
        
        res_p1 = requests.get(url_plan_1, timeout=5)
        if res_p1.status_code == 200:
            root_p1 = ET.fromstring(res_p1.text)
            alle_stops_xml.extend(root_p1.findall('s'))
                
        res_p2 = requests.get(url_plan_2, timeout=5)
        if res_p2.status_code == 200:
            root_p2 = ET.fromstring(res_p2.text)
            alle_stops_xml.extend(root_p2.findall('s'))
            
        departures_list = []
        gesehene_ids = set() # Verhindert doppelte Einträge bei Stundenübergängen
        
        # --- 3. Daten zusammenführen ---
        for stop in alle_stops_xml:
            dp = stop.find('dp') # Departure
            
            # Ohne Abfahrtsknoten ignorieren
            if dp is None:
                continue
                
            stop_id = stop.get('id')

            if stop_id in gesehene_ids:
                continue
            gesehene_ids.add(stop_id)

            tl = stop.find('tl') # Trip Label
            
            # Geplante Abfahrtszeit ermitteln (Format 'pt': YYMMDDhhmm)
            print_time = dp.get('pt')
            geplant_zeit = f"{print_time[6:8]}:{print_time[8:10]}"
            
            # Basis-Zuggattung merken
            zuggattung = tl.get('c', '') if tl is not None else ''
            zug_nr = tl.get('n', '') if tl is not None else ''
            
            # Live-Name prüfen
            live_name = live_linien.get(stop_id)
            
            # ABSICHERUNG: Wenn die API im Fahrplan sagt, es ist ein Bus (c="Bus")
            # oder der Live-Name mit "Bus " beginnt:
            if zuggattung == "Bus" or (live_name and live_name.startswith("Bus ")):
                art = "Bus"
                if live_name:
                    nummer = live_name.replace("Bus ", "").strip()
                else:
                    nummer = live_linien.get(stop_id, zug_nr)
            
            # Normaler Ablauf für echte Züge:
            elif live_name:
                if ' ' in live_name:
                    art, nummer = live_name.split(' ', 1)
                else:
                    import re
                    match = re.match(r"([a-zA-Z\s]+)([0-9]+)", live_name)
                    if match:
                        art, nummer = match.groups()
                    else:
                        art, nummer = live_name, ""
            else:
                art = zuggattung
                nummer = zug_nr
            
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

            gleis_geplant = dp.get('pp', '-')
            gleis_tatsaechlich = live_gleise.get(stop_id, gleis_geplant)

            ist_ausgefallen = ausfaelle.get(stop_id, False)
            
            # Abfahrt zur Liste hinzufügen
            departures_list.append({
                "art": art,
                "nummer": nummer,
                "ziel": ziel,
                "gleis_geplant": dp.get('pp', '-'),
                "gleis_tatsaechlich": gleis_tatsaechlich,
                "abfahrt_geplant": geplant_zeit,
                "abfahrt_tatsaechlich": tatsaechlich.strftime("%H:%M"),
                "verspaetung": max(0, verspaetung_min),
                "ausgefallen": ist_ausgefallen,
                "route": route_liste,
                "_sort_time": tatsaechlich
            })
            
        # Abschließend chronologisch sortieren
        departures_list = [z for z in departures_list if z['_sort_time'] >= jetzt]
        departures_list.sort(key=lambda x: x['_sort_time'])
        print(alle_stops_xml)
        return departures_list
        
    except Exception as e:
        logger.error(f"Beim Abfragen der Abfahrten ist ein Fehler aufgetreten {e}")
        return []