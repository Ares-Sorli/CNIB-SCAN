import threading
import time
import os
import io
import csv
from flask import Flask, render_template_string, request, redirect, url_for, Response, flash
from gpiozero import Button, Buzzer
from picamera2 import Picamera2
from libcamera import controls
import ocr
import database
import pretraitement
import cv2

app = Flask(__name__)
app.secret_key = "secret_utm_cnib_key"

# --- Configuration du Matériel (GPIO) ---
try:
    bouton_power = Button(17, bounce_time=0.2, hold_time=3)
    bouton_scan = Button(27, bounce_time=0.2)
    buzzer = Buzzer(22)
    MODE_DEVELOPPEUR = False
    print("📌 Boutons physiques et Buzzer configurés avec succès.")
except Exception as e:
    print(f"⚠️ Mode Développeur activé (Matériel non détecté) : {e}")
    MODE_DEVELOPPEUR = True

# --- Configuration de la Caméra (picamera2) ---
picam2 = None
try:
    picam2 = Picamera2()
    config_cam = picam2.create_still_configuration(
        main={"size": (1280, 720), "format": "RGB888"}
    )
    picam2.configure(config_cam)
    try:
        picam2.set_controls({
            "AfMode": controls.AfModeEnum.Continuous,
            "AfSpeed": controls.AfSpeedEnum.Fast,
            "AwbEnable": True,
            "AeEnable": True,
            "Sharpness": 2.0
        })
    except Exception:
        picam2.set_controls({"AwbEnable": True, "AeEnable": True})
    picam2.start()
    time.sleep(2)
    print("📷 Caméra picamera2 initialisée avec succès.")
except Exception as e:
    print(f"⚠️ Caméra picamera2 non disponible : {e}")
    picam2 = None

# --- Variables d'État de Sécurité ---
scan_en_cours = False
dernier_resultat = None  # Stocke le dernier scan pour affichage immédiat

# --- Fonctions d'Action ---

def bip_court():
    if not MODE_DEVELOPPEUR:
        buzzer.on()
        time.sleep(0.1)
        buzzer.off()

def bip_long():
    if not MODE_DEVELOPPEUR:
        buzzer.on()
        time.sleep(0.5)
        buzzer.off()

def action_extinction():
    """Déclenchée après un appui maintenu de 3 secondes sur le bouton power."""
    print("🛑 Appui long de 3s détecté ! Extinction du système...")
    if not MODE_DEVELOPPEUR:
        bip_long()
        time.sleep(0.2)
        bip_long()
        os.system("sudo poweroff")

def piloter_scan():
    global scan_en_cours, dernier_resultat
    print("\n══════════════════════════════════════════════════")
    print("🔘 BOUTON DÉCLENCHÉ : Début du traitement CNIB...")
    print("══════════════════════════════════════════════════")
    bip_court()

    frame = None

    if picam2 is not None:
        try:
            frame_rgb = picam2.capture_array()
            frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"⚠️ Erreur capture picamera2 : {e}")
            frame = None

    if frame is None:
        print("🔄 MODE SIMULATION (Chargement de 'simulation_cnib.jpg')...")
        if os.path.exists("simulation_cnib.jpg"):
            frame = cv2.imread("simulation_cnib.jpg")
        else:
            print("❌ Erreur : 'simulation_cnib.jpg' introuvable.")
            dernier_resultat = {"succes": False, "message": "Aucune image disponible."}
            scan_en_cours = False
            return

    cv2.imwrite("capture_cnib.jpg", frame)

    image_preparée = pretraitement.optimiser_image(frame)
    donnees_cnib = ocr.executer_ocr(image_preparée)

    if donnees_cnib:
        database.sauvegarder_scan(
            donnees_cnib['nom'], donnees_cnib['prenom'], donnees_cnib['nip'], donnees_cnib['numero_carte'],
            donnees_cnib['date_naissance'], donnees_cnib['lieu_naissance'], donnees_cnib['date_delivrance'], donnees_cnib['date_expiration']
        )
        dernier_resultat = {"succes": True, "donnees": donnees_cnib}
        print(f"✅ Scan réussi : {donnees_cnib['nom']} {donnees_cnib['prenom']}")
    else:
        dernier_resultat = {"succes": False, "message": "Échec de l'extraction des données."}
        print("❌ Échec de l'extraction des données.")

    bip_long()
    print("✅ Scan terminé. Bouton réactivé.\n")
    scan_en_cours = False

def verifier_et_lancer_scan():
    global scan_en_cours
    if scan_en_cours:
        print("⏳ Scan déjà en cours... Appui ignoré.")
        return

    scan_en_cours = True
    t = threading.Thread(target=piloter_scan)
    t.daemon = True
    t.start()

if not MODE_DEVELOPPEUR:
    bouton_power.when_held = action_extinction   # Appui maintenu 3s
    bouton_scan.when_pressed = verifier_et_lancer_scan  # Un seul appui


# --- Routes du Serveur Web Flask ---

@app.route('/')
def index():
    global dernier_resultat
    requete_recherche = request.args.get('q', '').strip()
    tous_les_scans = []

    try:
        import sqlite3
        conn = sqlite3.connect("cnib_data.db")
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date_scan, nom, prenom, numero_nip, numero_carte, 
                   date_naissance, lieu_naissance, date_delivrance, date_expiration 
            FROM scans ORDER BY id DESC
        ''')
        tous_les_scans = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"❌ Erreur lecture BDD : {e}")
        tous_les_scans = []

    total_scans = len(tous_les_scans)
    scans_filtres = []

    if requete_recherche:
        for s in tous_les_scans:
            if (requete_recherche.lower() in str(s[1]).lower() or
                requete_recherche.lower() in str(s[2]).lower() or
                requete_recherche.lower() in str(s[3]).lower() or
                requete_recherche.lower() in str(s[4]).lower()):
                scans_filtres.append(s)
    else:
        scans_filtres = tous_les_scans

    # Message de résultat du dernier scan (affiché une fois puis effacé)
    resultat_a_afficher = dernier_resultat
    dernier_resultat = None

    gabarit_html = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        {% if not requete %}
        <meta http-equiv="refresh" content="5">
        {% endif %}
        <title>INTERFACE WEB CNIB - SCAN</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; color: #333; margin: 0; padding: 20px; box-sizing: border-box; }
            .container { max-width: 1400px; margin: 0 auto; }

            header { background: linear-gradient(135deg, #1e3c72, #2a5298); color: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: flex; justify-content: space-between; align-items: center; }
            .header-text h1 { margin: 0; font-size: 26px; font-weight: 700; letter-spacing: 0.5px; }
            .header-text p { margin: 5px 0 0 0; opacity: 0.9; font-size: 14px; }

            .header-right { text-align: right; display: flex; flex-direction: column; gap: 8px; align-items: flex-end; }
            .status { background: #2ecc71; padding: 6px 14px; border-radius: 20px; font-size: 11px; font-weight: bold; color: white; letter-spacing: 0.5px; }
            .version-tag { font-size: 12px; font-weight: 600; color: rgba(255, 255, 255, 0.85); background: rgba(255, 255, 255, 0.15); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.2); }

            .card-compteur { background: white; padding: 15px 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); width: fit-content; border-left: 5px solid #2563eb; margin-bottom: 25px; }
            .card-compteur .chiffre { font-size: 28px; font-weight: bold; color: #2563eb; margin: 0; line-height: 1; }
            .card-compteur .label { font-size: 12px; color: #64748b; margin-top: 5px; font-weight: 500; }

            .barre-outils { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; gap: 15px; }
            .form-recherche { flex-grow: 1; display: flex; gap: 10px; }
            .input-recherche { width: 100%; max-width: 400px; padding: 10px 15px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; }

            .btn { padding: 10px 18px; border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; gap: 5px; }
            .btn-primaire { background-color: #2563eb; color: white; }
            .btn-export { background-color: #10b981; color: white; }
            .btn-danger { background-color: #ef4444; color: white; padding: 6px 12px; font-size: 12px; border-radius: 4px; }
            .btn-danger:hover { background-color: #dc2626; }
            .btn-txt { background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; padding: 6px 12px; font-size: 12px; border-radius: 4px; }
            .btn-txt:hover { background-color: #e2e8f0; }
            .btn-neutre { background-color: #64748b; color: white; }

            .actions-cell { display: flex; gap: 6px; }

            table { width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
            th, td { padding: 14px; text-align: left; border-bottom: 1px solid #edf2f7; font-size: 13.5px; }
            th { background-color: #f8fafc; color: #4a5568; font-weight: 600; text-transform: uppercase; font-size: 11px; }
            tr:hover { background-color: #f8fafc; }
            .badge-nip { background: #e2e8f0; padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 12.5px; font-weight: bold; color: #334155; }
            .flash-message { background-color: #d1fae5; color: #065f46; padding: 12px; border-radius: 6px; margin-bottom: 15px; border: 1px solid #a7f3d0; font-size: 14px; }

            .resultat-scan { padding: 16px 20px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; }
            .resultat-succes { background-color: #d1fae5; border: 1px solid #34d399; color: #065f46; }
            .resultat-echec { background-color: #fee2e2; border: 1px solid #f87171; color: #991b1b; }
            .resultat-succes strong, .resultat-echec strong { font-size: 16px; }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <div class="header-text">
                    <h1>INTERFACE WEB CNIB -SCAN</h1>
                    <p>FabLab BBI / UTM</p>
                </div>
                <div class="header-right">
                    <span class="status">🟢 MAQUETTE EN LIGNE</span>
                    <span class="version-tag">📦 Cnib Scan v1.0</span>
                </div>
            </header>

            {% with messages = get_flashed_messages() %}
              {% if messages %}
                {% for message in messages %}
                  <div class="flash-message">✨ {{ message }}</div>
                {% endfor %}
              {% endif %}
            {% endwith %}

            {% if resultat %}
                {% if resultat.succes %}
                <div class="resultat-scan resultat-succes">
                    <strong>✅ Scan réussi !</strong><br>
                    {{ resultat.donnees.nom }} {{ resultat.donnees.prenom }} — N° Carte : {{ resultat.donnees.numero_carte }}
                </div>
                {% else %}
                <div class="resultat-scan resultat-echec">
                    <strong>❌ Scan échoué</strong><br>
                    {{ resultat.message }}
                </div>
                {% endif %}
            {% endif %}

            <div class="card-compteur">
                <div class="chiffre">{{ total_scans }}</div>
                <div class="label">Total des fiches numérisées</div>
            </div>

            <div class="barre-outils">
                <form class="form-recherche" method="GET" action="/">
                    <input type="text" name="q" class="input-recherche" placeholder="Rechercher..." value="{{ requete }}">
                    <button type="submit" class="btn btn-primaire">Filtrer</button>
                    {% if requete %}
                        <a href="/" class="btn btn-neutre">Effacer</a>
                    {% endif %}
                </form>
                <a href="/exporter" class="btn btn-export">📊 Exporter en CSV</a>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Date Scan</th>
                        <th>Nom</th>
                        <th>Prénoms</th>
                        <th>NIP</th>
                        <th>N° Carte</th>
                        <th>Date Naissance</th>
                        <th>Lieu Naissance</th>
                        <th>Délivrance</th>
                        <th>Expiration</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for scan in scans %}
                    <tr>
                        <td><small>{{ scan[0] }}</small></td>
                        <td><strong>{{ scan[1] }}</strong></td>
                        <td>{{ scan[2] }}</td>
                        <td><span class="badge-nip">{{ scan[3] }}</span></td>
                        <td><strong>{{ scan[4] }}</strong></td>
                        <td>{{ scan[5] }}</td>
                        <td>{{ scan[6] }}</td>
                        <td>{{ scan[7] }}</td>
                        <td>{{ scan[8] }}</td>
                        <td>
                            <div class="actions-cell">
                                <a href="/telecharger_txt/{{ scan[4] }}" class="btn btn-txt" title="Télécharger la fiche individuelle">📄 Fiche TXT</a>
                                <a href="/supprimer/{{ scan[4] }}" class="btn btn-danger" onclick="return confirm('Supprimer définitivement ?');">Supprimer</a>
                            </div>
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="10" style="text-align: center; color: #a0aec0; padding: 40px;">Aucun enregistrement trouvé.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return render_template_string(gabarit_html, scans=scans_filtres, requete=requete_recherche, total_scans=total_scans, resultat=resultat_a_afficher)


@app.route('/supprimer/<string:numero_carte>')
def supprimer(numero_carte):
    try:
        import sqlite3
        conn = sqlite3.connect("cnib_data.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scans WHERE numero_carte = ?", (numero_carte,))
        conn.commit()
        conn.close()
        flash(f"La carte N° {numero_carte} a été supprimée.")
    except Exception as e:
        print(f"❌ Erreur suppression : {e}")
    return redirect(url_for('index'))


@app.route('/telecharger_txt/<string:numero_carte>')
def telecharger_txt(numero_carte):
    try:
        import sqlite3
        conn = sqlite3.connect("cnib_data.db")
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date_scan, nom, prenom, numero_nip, numero_carte, 
                   date_naissance, lieu_naissance, date_delivrance, date_expiration 
            FROM scans WHERE numero_carte = ? LIMIT 1
        ''', (numero_carte,))
        scan = cursor.fetchone()
        conn.close()

        if scan:
            contenu_txt = f"""==================================================
           FICHE INDIVIDUELLE CNIB SCAN
==================================================
Date du Scan    : {scan[0]}
Nom             : {scan[1]}
Prénoms         : {scan[2]}
NIP             : {scan[3]}
Numéro de Carte : {scan[4]}
Né(e) le        : {scan[5]}
À               : {scan[6]}
Délivrée le     : {scan[7]}
Expire le       : {scan[8]}
==================================================
Généré par Maquette CNIBScan - FabLab BBI / UTM
"""
            nom_fichier = f"fiche_{scan[1]}_{scan[4]}.txt"
            return Response(
                contenu_txt,
                mimetype="text/plain",
                headers={"Content-Disposition": f"attachment;filename={nom_fichier}"}
            )
        else:
            flash("Erreur : Impossible de trouver les données de cette carte.")
            return redirect(url_for('index'))
    except Exception as e:
        print(f"❌ Erreur téléchargement TXT : {e}")
        return redirect(url_for('index'))


@app.route('/exporter')
def exporter():
    try:
        import sqlite3
        conn = sqlite3.connect("cnib_data.db")
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date_scan, nom, prenom, numero_nip, numero_carte, 
                   date_naissance, lieu_naissance, date_delivrance, date_expiration 
            FROM scans ORDER BY id DESC
        ''')
        scans = cursor.fetchall()
        conn.close()
    except:
        scans = []

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Date de Scan', 'Nom', 'Prénoms', 'NIP', 'Numéro de Carte', 'Date de Naissance', 'Lieu de Naissance', 'Délivrée le', 'Expire le'])
    for row in scans:
        writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8]])
    output.seek(0)
    return Response(output.read(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=historique_scans_cnib.csv"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
