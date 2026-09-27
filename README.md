🇫🇷 **Français** · [🇬🇧 English](./README_EN.md) · [🇪🇸 Español](./README_ES.md)

# DMD GIF Creator 128x32 — v3.2.2

Créez des GIF optimisés pour les écrans DMD 128×32 (borne d'arcade, flipper,
[RecalBox DMD](https://github.com/shan-aya/RecalBoxDMD)) à partir d'**images**, d'une
**vidéo** ou de **texte animé**, avec analyse automatique, édition manuelle avancée et
traitement par lot de dossiers entiers.

(Anciennement « DMD GIF Converter ».)

![Onglet AUTO](./screenshots/auto_fr.png)

## Téléchargement

**Windows** : téléchargez `dmd_gif_creator_v322.exe` dans la
[dernière Release](https://github.com/shan-aya/DMD_GIF_creator/releases/latest) et
lancez-le — aucune installation nécessaire.

L'exécutable n'est pas signé : Windows SmartScreen peut demander une confirmation au
premier lancement (« Informations complémentaires » puis « Exécuter quand même »). Si
un antivirus le bloque pendant un traitement par lot (protection anti-rançongiciel),
c'est un faux positif : voir « Antivirus » dans la [notice](./NOTICE_FR.md#bonnes-pratiques-et-limites-connues).

**Depuis les sources** (dossier [`dmd_gif_creator/`](./dmd_gif_creator)) :

    pip install pillow numpy tkinterdnd2 markdown opencv-contrib-python
    python dmd_gif_creator/dmd_gif_creator_v322.py

`opencv-contrib-python` (et non `opencv-python`) est nécessaire pour le suivi
automatique de l'onglet VIDEO ; les deux paquets ne doivent pas être installés en même
temps.

## Ce que fait l'application

### AUTO — une image, six propositions

Glissez-déposez des images ou des dossiers entiers (PNG, JPG, BMP, GIF, raw565).
Pour chaque image, l'application calcule deux rendus 128×32 — **Resize** (l'image entière
réduite) et **Fill** (l'image à plus grande taille, qui défile) — et leur donne un score
d'occupation de l'écran et de lisibilité. Le meilleur est retenu, puis affiné
(nettoyage, pixel-perfect). Trois variantes artistiques complètent les six
propositions ; l'aperçu LED (avec loupe) montre le rendu réel du panneau.

Un **profil** adapte ce choix à l'usage : **Générique** (aucune limite), **Logos
Recalbox** (le défilement est imposé aux logos larges, un aller-retour dure au plus
30 s, 15 i/s) ou **DMD playlist** (20 i/s pour plus de fluidité). Vous pouvez créer vos
propres profils dans une page où chaque paramètre est expliqué. Les logos sombres sur
fond transparent, invisibles sur un DMD noir, sont inversés quand le rendu y gagne.

Le **traitement par lot** applique cette même analyse à chaque image d'un dossier —
par exemple tous les logos scrapés d'une ludothèque : chaque logo reçoit le mode de
rendu qui lui convient, en parallèle, avec l'arborescence conservée et les fichiers
source jamais modifiés. Une proposition peut être verrouillée pour tout le lot. Chaque
GIF reçoit un **score qualité**, et la fenêtre **Revoir** liste les plus faibles en
premier, avec aperçu et image source, pour relire rapidement des milliers de logos et
mettre de côté (sans jamais supprimer) ceux qui sont ratés. Elle **propose des
corrections** pour les GIF faibles (texte noir éclairci, vide retiré, gamma, inversion…),
à valider une à une, ou ouvre la source dans MANUEL pour la reprendre à la main.

![Fenêtre Revoir](./screenshots/review_fr.png)

### MANUEL — édition avancée

![Onglet MANUEL](./screenshots/manual_fr.png)

Recadrage 128×32 avec un cadre à déplacer, zone limitant les effets à une partie de
l'image, luminosité, contraste, saturation, netteté, filtres, zoom de l'animation, pot
de peinture et gomme magique, animations (défilement, zoom, fondu…) avec easing et boucle,
multi-images et morphing, historique annuler/rétablir.

### VIDEO — un GIF à partir d'une vidéo

![Onglet VIDEO](./screenshots/video_fr.png)

Choisissez un passage d'une vidéo (MP4, MOV, AVI, MKV, WEBM, WMV, FLV, MPG, TS, 3GP,
OGV…) sur la frise, puis le cadrage :
suivi automatique d'un sujet, cadrage auto avec zoom, ou points manuels (zone et zoom
qui évoluent dans le temps). La qualité automatique ajuste contraste, saturation et
luminosité d'après la vidéo, et le poids du GIF est estimé en direct.

### TEXTSCROLL — texte animé

![Onglet TEXTSCROLL](./screenshots/textscroll_fr.png)

Police, taille, couleurs, effets de texte et de couleur, et de nombreuses animations
(défilement horizontal ou vertical, vague, Star Wars, machine à écrire, pluie Matrix,
glitch…), avec une durée ajustée automatiquement à la longueur du texte.

### Et aussi

- **PARAMETRES** : réglages par défaut, langue (français, anglais, espagnol).
- **DEBUG** : journal détaillé filtrable.
- **AIDE** : le guide complet dans l'application.

## Nouveautés

**v3.2.2**
- Onglet **VIDEO** bien plus rapide et plus léger : génération du GIF jusqu'à 7 fois plus
  rapide en 1080p, répartie sur plusieurs cœurs ; le lecteur ne décode plus en arrière-plan.
- **Vidéo longue** : découpage d'un passage proposé juste après la sélection, avec la
  mémoire nécessaire affichée ; alerte si un passage est trop long pour la mémoire du PC.

**v3.2.1**
- Les calculs du traitement par lot tournent en **priorité basse** : le PC reste
  utilisable pendant un lot, sans perte de vitesse quand il est libre.
- **PARAMETRES** : réglage du nombre de cœurs utilisés par le lot (Auto par défaut).
- Informations de version dans l'exécutable ; note « Antivirus » dans la notice.

**v3.2.0**
- Fenêtre **Revoir** : **corrections proposées** pour les GIF faibles (vide retiré,
  parties sombres éclaircies, gamma, niveaux, inversion), avec aperçu LED et validation
  une à une ; l'original est mis de côté, jamais supprimé. Miniature de l'image source,
  bouton **Éditer dans MANUEL**, passage au GIF suivant après validation.
- **MANUEL** : **zone** limitant curseurs et filtres à une partie de l'image, **zoom**
  de l'animation (50 à 300 %), recadrage 128×32 avec un **cadre à déplacer**.
- **VIDEO** : formats WEBM, M4V, WMV, FLV, MPG/MPEG, TS, 3GP et OGV acceptés en plus.
- Corrections : les curseurs de MANUEL n'annulent plus un recadrage ou un filtre ;
  aperçus à la bonne vitesse ; propositions 4 à 6 de l'onglet AUTO de nouveau visibles.

**v3.1.0**
- **Score qualité** de chaque GIF et fenêtre **Revoir** (du plus faible au meilleur,
  aperçu LED, mise de côté sans suppression).
- **Profils** : Générique, Logos Recalbox, DMD playlist, et profils personnels.
- **Logos sombres** sur fond transparent inversés quand le rendu y gagne.
- Le réglage « Seuil lettrage » est remplacé par l'option de profil « Défilement
  imposé dès (L/H) ».

**v3.0.2**
- Onglet AUTO entièrement traduit en anglais et en espagnol (noms des propositions,
  ligne d'état, barre d'état).

**v3.0.1**
- Traitement par lot environ **2,4 fois plus rapide** : jusqu'à 12 images en parallèle
  selon le processeur, et encodage GIF accéléré.
- Interface traduite plus complètement en anglais et en espagnol.

**v3.0**
- Onglet **VIDEO**, onglet **AIDE**, **glisser-déposer** partout dans la fenêtre.
- **Aperçu LED** dans tous les onglets de création.
- Traitement par lot en parallèle, chargement de dossiers de dizaines de milliers
  d'images sans figer la fenêtre.
- Format raw565 en entrée, annuler/rétablir dans MANUEL, infobulles d'aide.

Historique complet : [CHANGELOG_FR](./CHANGELOG_FR)

## Documentation

Notice complète : [🇫🇷 Français](./NOTICE_FR.md) · [🇬🇧 English](./NOTICE_EN.md) ·
[🇪🇸 Español](./NOTICE_ES.md) — également disponible dans l'application, onglet
**AIDE**.

---

## 🤝 Remerciements

- [RetroPixelLED original](https://github.com/fjgordillo86/RetroPixelLED)
- [red77290/dmd_gif_converter](https://github.com/red77290/dmd_gif_converter) (MIT) :
  idée du score qualité et de la mise de côté des GIF faibles
- Visual Studio Code
- [Sixth](https://trysixth.com/)

## ☕ Soutenir le projet

Si ce projet t'a aidé, tu peux m'offrir un café :
👉 [☕ Donate via PayPal](https://www.paypal.com/paypalme/felysaya)

## Contact

Pour toute question, suggestion ou contribution, créez une issue ou contactez l'auteur
Shan_ayA.

---

© 2026 Shan_ayA
