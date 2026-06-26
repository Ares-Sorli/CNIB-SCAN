CNIB-SCAN

Système intelligent de lecture et de gestion automatisée de la Carte Nationale d'Identité Burkinabè (CNIB)

CNIB-SCAN est un dispositif embarqué autonome basé sur un Raspberry Pi Zero 2W, capable de capturer l'image d'une CNIB, d'en extraire automatiquement les données par reconnaissance optique de caractères (OCR), et de les enregistrer dans une base de données locale accessible via une interface web.

Projet réalisé dans le cadre d'un stage de fin de cycle (Licence en Électronique et Informatique Industrielle, UTM) au sein du FabLab du Burkina Business Incubator (BBI), Ouagadougou, Burkina Faso.


Sommaire


Contexte
Fonctionnalités
Architecture du système
Matériel utilisé
Stack logicielle
Installation
Utilisation
Structure du projet
Résultats des tests
Coût de réalisation
Perspectives d'évolution
Auteur



Contexte

Dans la majorité des institutions burkinabè (banques, mobile money, transport, administrations), la vérification de la CNIB repose encore sur la saisie manuelle : un agent lit la carte et recopie les informations à la main. Cette pratique est lente (souvent plus de 10 minutes par client), source d'erreurs, et ne permet aucune traçabilité automatique.

Les solutions commerciales existantes (Idemia, Onfido, etc.) sont conçues pour des formats internationaux, coûteuses, dépendantes d'une connexion internet permanente et impliquent un transfert des données vers des serveurs étrangers — autant de contraintes incompatibles avec le contexte burkinabè.

CNIB-SCAN répond à ce besoin avec une solution locale, autonome et accessible.


Fonctionnalités


Capture automatique de l'image du recto de la CNIB via une caméra dédiée
Prétraitement d'image (niveaux de gris, débruitage, binarisation, correction de perspective)
Extraction automatique des données par OCR : nom, prénom, numéro NIP, numéro de carte, dates de naissance/délivrance/expiration, lieu de naissance
Enregistrement horodaté dans une base de données locale
Interface web de consultation, recherche et export des données (CSV)
Contrôle physique par boutons poussoirs (allumage/extinction, déclenchement du scan)
Retour sonore (buzzer) confirmant le début et la fin de chaque scan
Fonctionnement 100 % hors ligne, sans connexion internet requise



Architecture du système

Le système s'articule autour de trois couches fonctionnelles :

CoucheRôleComposantsCapturePhotographie du recto de la CNIBCaméra 12MP, Bouton 2, BuzzerTraitementPréparation de l'image et extraction des donnéesOpenCV, Tesseract OCR / pytesseractStockage et accèsEnregistrement et consultation des donnéesSQLite, Flask

Flux de traitement :

Appui Bouton 2 → Capture image → Prétraitement (OpenCV)
→ Extraction OCR (Tesseract) → Stockage horodaté (SQLite)
→ Consultation / Export (Interface web Flask)


Matériel utilisé

ComposantRôleRaspberry Pi Zero 2WUnité centrale du systèmeModule caméra Raspberry Pi 3 (12MP)Capture de l'image de la CNIBCarte microSD 32 GoStockage de l'OS, du code et de la base de données2 boutons poussoirsAllumage/extinction et déclenchement du scanBuzzer actifRetour sonore (début/fin de scan)Alimentation 5V, résistances, fils de connexionCâblage et alimentation du dispositifBoîtier physique (impression 3D)Maintien de la caméra et guidage du positionnement de la carte


Stack logicielle

OutilRôlePython 3.9+Langage principalOpenCVTraitement et prétraitement d'imageTesseract OCR + pytesseractReconnaissance optique de caractèresSQLite3Base de données localeFlaskInterface webRPi.GPIOContrôle des boutons et du buzzerPicamera2Pilotage de la caméraRaspberry Pi OS (Bookworm)Système d'exploitation


Installation

Prérequis matériels

Raspberry Pi Zero 2W flashé avec Raspberry Pi OS, connecté en SSH.

Mise en place de l'environnement

bash# Mise à jour du système
sudo apt update && sudo apt upgrade -y

# Création de l'environnement virtuel
cd /home/pi/cnibscan
python3 -m venv venv
source venv/bin/activate

# Installation des dépendances
pip install opencv-python
sudo apt install tesseract-ocr tesseract-ocr-fra -y
pip install pytesseract
pip install flask


La bibliothèque SQLite3 est intégrée nativement à Python et ne nécessite aucune installation supplémentaire.



Lancement de l'application

bashpython3 app.py

L'interface web est ensuite accessible depuis n'importe quel appareil connecté au même réseau WiFi, à l'adresse :

http://cnibscan:5000


Utilisation


Positionner le recto de la CNIB dans le cadre du boîtier
Appuyer sur le Bouton 2 (déclenchement du scan) — un premier bip confirme la prise en compte
Attendre la fin du traitement (environ 40 à 50 secondes) — un second bip signale la fin du scan
Consulter le résultat depuis l'interface web, rechercher un enregistrement ou exporter les données en CSV
Un appui prolongé de 3 secondes sur le Bouton 1 permet d'éteindre le système en toute sécurité



Structure du projet

cnibscan/
│
├── app.py                # Point d'entrée — orchestration générale
├── capture.py             # Module de capture d'image
├── pretraitement.py       # Module de traitement d'image (OpenCV)
├── ocr.py                 # Module d'extraction OCR (Tesseract)
├── database.py            # Module de gestion de la base de données (SQLite)
├── config.py               # Configuration matérielle (GPIO)
│
├── templates/
│   └── index.html         # Interface web Flask
│
├── static/                # Fichiers CSS / ressources statiques
│
├── cnibscan.db             # Base de données SQLite
└── venv/                   # Environnement virtuel Python


Résultats des tests

CritèreRésultatTemps de traitement par scan40 à 50 secondesExtraction OCR (Tesseract)0,55 secondeExtraction OCR (EasyOCR, écarté)7,97 secondesFonctionnement hors ligne✅ ValidéAccessibilité multi-appareils (réseau local)✅ Validé (PC, Android, tablette)


Le choix de Tesseract OCR plutôt qu'EasyOCR s'est imposé après que ce dernier s'est révélé incompatible avec la RAM limitée (512 Mo) du Raspberry Pi Zero 2W.




Coût de réalisation

Coût total du dispositif : 51 678 FCFA (environ 80 €)

Une alternative locale jusqu'à plusieurs dizaines de fois moins coûteuse que les solutions commerciales équivalentes, dont les coûts de licence dépassent généralement plusieurs millions de FCFA.


Perspectives d'évolution


Interconnexion entre institutions via un réseau sécurisé pour un partage centralisé des données d'identité
Détection de faux documents par analyse des caractéristiques visuelles et éléments de sécurité de la CNIB
Application mobile dédiée pour un accès simplifié depuis le smartphone de l'agent



Auteur

SOMDA Soglignine
Licence en Électronique et Informatique Industrielle — Université de Technologies et de Management (UTM)
Stage réalisé au FabLab du Burkina Business Incubator (BBI), Ouagadougou, Burkina Faso


Maître de stage : M. OUEDRAOGO Mohamed Bassirou (FabLab Manager)
Professeur de suivi : M. COULIBALY Souleymane (UTM)



Projet réalisé en 2026 dans le cadre d'un rapport de stage de fin de Licence.
