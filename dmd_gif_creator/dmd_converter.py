#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DMD GIF Creator
Shan_ayA 2026

Version: 3.2.0

Application multilingue complète de conversion d'images en GIF optimisés pour écrans DMD 128x32
avec moteur comparatif , édition manuelle avancée et génération de texte animé.

Dépendances:
    pip install pillow numpy tkinterdnd2 markdown opencv-contrib-python

    opencv-contrib-python (PAS opencv-python) : nécessaire pour les
    trackers CSRT/KCF, bien plus robustes que TrackerMIL (seul tracker
    disponible avec le paquet opencv-python de base) — bug réel signalé
    par l'utilisateur ("le suivi automatique ne garde pas la sélection au
    milieu de la hauteur, comme si le scroll vers le haut ne se faisait
    pas") diagnostiqué comme un décrochage de MIL en cours de vidéo, voir
    changelog dmd_video_engine.py. Les deux paquets sont mutuellement
    exclusifs (même module cv2) — désinstaller opencv-python avant
    d'installer opencv-contrib-python si un ancien environnement les a
    déjà.
"""

# ============================================
# safe-modify — Historique des modifications
# ============================================
# Version actuelle : v105
#
# v105 — 2026-09-27 — safe-modify — Version 3.2.0 (v95 à v104 : corrections proposées et édition dans Revoir,
#      zone d'effets, zoom, recadrage à cadre mobile, formats vidéo, aperçus à la bonne vitesse…) ; lanceur
#      renommé dmd_gif_creator_v320.py ; en-têtes des 3 lang_*.json et clé TEXT_MAP (dmd_ui_constants v21).
# v104 — 2026-09-27 — safe-modify — Formats vidéo acceptés (demande utilisateur) : MP4/AVI/MOV/MKV → + M4V, WEBM,
#      WMV, FLV, MPG, MPEG, TS, 3GP, OGV, tous vérifiés (conversion ffmpeg d'une vraie vidéo puis lecture OpenCV :
#      images, FPS, durée). Liste unique VIDEO_EXTS pour l'ouverture et le glisser-déposer.
# v103 — 2026-09-27 — safe-modify — MANUEL (demande utilisateur + bug trouvé en préparant) :
#      (1) BUG : apply_manual_effect (curseurs Luminosité/Contraste/Saturation/Netteté) repartait de
#      manual_history[0], l'image CHARGÉE — toucher un curseur annulait recadrage, filtres, remplissages (vérifié :
#      400×100 recadré + miroir → 600×300 d'origine). Désormais : départ de l'état courant de l'historique ; toute
#      action permanente (filtre, recadrage, remplissage, gomme) intègre les réglages en cours puis remet les
#      curseurs à 1,00 (choix utilisateur) ; annuler/rétablir abandonne les réglages non intégrés.
#      (2) Zone d'effets : "▭ Zone" (tracer un rectangle libre, le déplacer en glissant dedans) et "✕ Zone" ;
#      curseurs et filtres ne touchent que la zone (filtres de voisinage calculés sur toute l'image puis limités
#      à la zone ; miroir, égaliser, etc. appliqués au seul contenu) ; Rotation 90° reste sur toute l'image et
#      efface la zone ; zone effacée au recadrage et au chargement d'une image ; un seul mode souris à la fois.
# v102 — 2026-09-27 — safe-modify — Signalement utilisateur : FPS MANUEL à 1 en venant de Revoir. Cause : pour un
#      dossier sans réglages enregistrés, _timing_of déduisait les FPS du plus petit délai du GIF ; un GIF fixe ou
#      presque noir n'a qu'UNE image (images identiques fusionnées, ~2 s) → 1000/1980 → 1 i/s. Désormais : FPS
#      actuels d'AUTO s'ils expliquent tous les délais (multiples d'une image, ±15 ms) ou si le GIF n'a qu'une
#      image ; sinon déduction par le plus petit délai en préférant les cadences usuelles ; à défaut FPS d'AUTO.
# v101 — 2026-09-27 — safe-modify — Signalement utilisateur : aperçu MANUEL trop rapide après modification des FPS ou
#      de la durée. Cause : chaque régénération relançait la boucle d'aperçu sans annuler l'étape déjà programmée
#      (root.after) ; l'ancienne boucle repartait en parallèle (time.sleep(0.1) ne l'empêchait pas) → 2, 3…
#      boucles qui avançaient les images en même temps. Même défaut dans les aperçus AUTO (à chaque image
#      sélectionnée), TEXTSCROLL et VIDEO. Correction : _anim_schedule/_anim_cancel, une seule étape en attente
#      par aperçu ; time.sleep(0.1) retiré (bloquait l'interface). MANUEL : l'aperçu et l'export utilisent la
#      cadence avec laquelle les images ont été générées (_manual_frames_fps), et l'aperçu est refait 600 ms
#      après une modification des FPS, de la durée ou de la vitesse (sauf morphing).
# v100 — 2026-09-27 — safe-modify — Signalement utilisateur ("Exception in Tkinter callback … expected integer but
#      got \"\"" en effaçant le champ FPS de MANUEL) : les 22 traces qui enregistraient un champ dans la config à
#      chaque frappe (AUTO, MANUEL, VIDEO, TEXTSCROLL, paramètres) lisaient la valeur sans garde ; un champ vidé
#      pour retaper levait TclError. Toutes passent par _save_var(), qui ignore une saisie incomplète.
# v99 — 2026-09-27 — safe-modify — MANUEL (demande utilisateur) : "Resize +" / "Resize -" retirés — ils
#      redimensionnaient l'image de travail (×1,2 / ×0,8), sans aucun effet sur le GIF puisque
#      generate_manual_animation recalcule la taille 128×32 d'après les seules proportions (et pouvaient flouter).
#      Remplacés par un ZOOM DE L'ANIMATION ("🔍 Zoom −", "🔍 Zoom +", "100 %") : paliers 50 % → 300 %, appliqué
#      après le calcul 128×32 (NEAREST en pixel-perfect, sinon LANCZOS), hors historique, remis à 100 % à chaque
#      nouvelle image ; l'aperçu est refait au changement de zoom (sauf frames de morphing).
# v98 — 2026-09-27 — safe-modify — Demandes utilisateur : (1) Revoir : après "Garder cette version", le GIF suivant
#      de la liste est sélectionné (_select_rel, attend l'insertion par paquets des grands dossiers) ; (2) MANUEL,
#      "✂️ Crop 128×32" : au lieu de TRACER un rectangle (imprécis), un cadre 4:1 est posé d'emblée (128×32 px de
#      l'image = 1 pixel par LED, réduit si l'image est plus petite) et se DÉPLACE à la souris ou aux flèches
#      (1 px, Maj : 10 px), molette = taille (ratio 4:1 gardé), double-clic ou Entrée = appliquer, Échap ou 2e clic
#      sur le bouton = annuler ; taille, position et pixels par LED affichés dans la barre d'état.
# v97 — 2026-09-27 — safe-modify — Fenêtre Revoir (demandes utilisateur) : (1) miniature de l'image SOURCE au-dessus
#      de l'aperçu LED, avec ses dimensions (source retrouvée par "src" de l'index ou par le dossier source mémorisé
#      des dossiers anciens) ; (2) bouton "✎ Éditer dans MANUEL" quand les propositions ne conviennent pas : la source
#      est chargée dans l'onglet MANUEL, et son export propose de remplacer le GIF du lot (original mis de côté dans
#      _a_revoir/_avant_correction, index mis à jour, fixed="manual") ou d'enregistrer ailleurs comme avant.
#      Remplacement commun aux corrections acceptées et à l'édition : review_replace_gif().
# v96 — 2026-09-27 — safe-modify — Fenêtre Revoir : corrections automatiques PROPOSÉES (demande utilisateur,
#      "on a un score + une raison, pourquoi pas une correction automatique ?"). Bouton "🪄 Proposer des
#      corrections ≤ seuil" : pour chaque GIF, variantes de la source (nouveau module dmd_autofix : vide retiré,
#      gamma, niveaux, sombres éclaircis, inversion), repassées dans le lot normal (process_one_image, mêmes
#      réglages que le lot d'origine) en arrière-plan ; jusqu'à 2 propositions (couleurs gardées / inversion)
#      avec aperçu LED ; rien ne change sans "Garder cette version", l'original part dans
#      _a_revoir/_avant_correction/ (jamais supprimé), l'index garde fixed/score_before. Le lot écrit
#      désormais la source ("src") et le n° de lot ("b") dans dmd_scores.json, et ses réglages dans
#      dmd_batch.json ; un dossier plus ancien demande le dossier source et utilise les réglages actuels.
#      Essai préalable sur les 54 GIF faibles d'un lot de 54 765 logos : 53 remontés au-dessus de 50 en
#      gardant les couleurs.
# v95 — 2026-09-27 — safe-modify — Onglet AUTO (signalement utilisateur, capture) : la 2e rangée de propositions
#      (4 à 6) était coupée en bas, cases "Verrouiller" invisibles, depuis l'ajout en v91 des 2 lignes Profil /
#      options du profil (Paramètres Globaux passés de 2 à 4 lignes, contrainte de hauteur déjà notée en v20).
#      Retour à 2 lignes : case pixel-perfect au bout de la ligne des réglages, options du profil sur la même
#      ligne que la liste des profils. Aucun changement de comportement.
# v94 — 2026-09-26 — safe-modify — Fenêtre Revoir (demande utilisateur) : le bouton 🔍 Revoir ouvre directement le
#      dossier du dernier lot noté (config last_review_folder, écrit en fin de lot dans le fil Tk) ; choix de dossier
#      seulement s'il n'y en a pas encore ou s'il n'a plus d'index. Bouton « 📂 Autre dossier… » dans la fenêtre pour
#      en revoir un autre. Proposition de fin de lot inchangée : seulement s'il y a des GIF faibles/mauvais.
#
# v93 — 2026-09-26 — safe-modify — Version 3.1.0 (score qualité + fenêtre Revoir, inversion des logos sombres,
#      profils de génération, règle de défilement et plafond pilotés par profil) : APP_VERSION + docstring ;
#      lanceur renommé dmd_gif_creator_v310.py ; en-têtes des 3 lang_*.json et clé TEXT_MAP (dmd_ui_constants v20).
#
# v92 — 2026-09-26 — safe-modify — Profils (demande utilisateur) : profil fourni « DMD playlist » (réglages DMD,
#      sans plafond, 20 i/s pour la fluidité, dmd_profiles v2) et profils personnels avec toutes les variables :
#      un profil porte aussi les paramètres globaux (FPS, durée, vitesse de défilement, contraste, saturation,
#      couleurs GIF, pixel-perfect ; appliqués au choix du profil, None = inchangé). Page d'édition ProfileEditor
#      (demande utilisateur : pas d'édition manuelle du JSON) : tous les paramètres éditables, chacun expliqué
#      (infobulle + bouton « ? » en popup), validation des bornes. Boutons ➕ (nouveau profil, page préremplie
#      avec les réglages actuels), ✏ (modifier le profil sélectionné), 💾 (enregistrer les réglages actuels),
#      🗑 (supprimer un profil personnel / remettre un profil fourni à ses valeurs d'origine, avec confirmation).
#
# v91 — 2026-09-26 — safe-modify — Profils de génération (décision utilisateur : moteur générique sans limitation,
#      profil pour les logos Recalbox ; les GIF servent aussi en playlist classique). Nouveau module dmd_profiles
#      (profils intégrés « Générique » et « Logos Recalbox (navigation) », surchargeables via profiles.json). Onglet
#      AUTO : ligne « Profil » (liste + 💾 enregistrer) et options modifiables — défilement imposé dès L/H (case +
#      valeur, remplace le réglage seul v86), inversion des logos sombres, plafond d'aller-retour (case + valeur).
#      batch_params_snapshot transmet invert_dark / max_scroll_cycle_s / fill_min_ratio (None si décoché) ;
#      l'aperçu applique les mêmes options (inversion conditionnelle, plafond sur toutes les propositions via
#      apply_render_profile). Défaut sans profil enregistré : Générique (aucune règle de forme, aucun plafond,
#      inversion active).
#
# v90 — 2026-09-25 — safe-modify — Aperçu AUTO : même décision que le lot pour les logos sombres monochromes
#      (dmd_pipeline_quality v26, maybe_invert_dark) — la proposition « Optimisé » passe à la version inversée si son
#      score qualité gagne au moins 3 points ; note d'état « (logo sombre → inversé) » (clé t_dark_inverted).
#
# v89 — 2026-09-25 — safe-modify — Score qualité après les exports uniques (MANUEL, VIDEO, TEXTSCROLL) : une ligne
#      « Score qualité : N/100 (note) — raisons » ajoutée au récapitulatif d'export (_export_quality_line,
#      penalize_static=False, jamais bloquant) + trace dans les logs.
#
# v88 — 2026-09-25 — safe-modify — Fenêtre « Revoir » (classe ReviewWindow) : GIF d'un dossier de sortie triés du
#      pire au meilleur d'après dmd_scores.json (pastille, score, chemin relatif, raisons dans la langue de
#      l'interface), colonnes triables, liste remplie par blocs de 1000 via after() (jamais figée sur des dizaines
#      de milliers de lignes), aperçu animé au clic avec le rendu LED existant (render_led_style), seuil (défaut
#      30) + « Déplacer ≤ seuil vers _a_revoir » avec confirmation (nombre exact via dry_run), déplacement dans un
#      thread (dmd_quality.review_low : déplace, ne supprime jamais). Ouverte par le bouton « 🔍 Revoir » (AUTO)
#      et proposée en fin de lot quand des GIF sont 🟠/🔴.
#
# v87 — 2026-09-25 — safe-modify — Score qualité 0-100 dans le traitement par lot (dmd_quality.py v2, aide à la
#      relecture de gros lots, jamais une décision automatique). process_one_image note les images déjà en mémoire
#      (dq.evaluate_frames, durée d'image = celle de l'export) et renvoie (chemin relatif posix, score) en 7e
#      élément ; process_images collecte dans le thread consommateur et écrit UNE fois dmd_scores.json dans le
#      dossier de sortie (_save_quality_index : fusion avec l'index existant, aussi après une interruption).
#      Boîte de fin de lot : résumé (nombre, moyenne, répartition par pastille) avant la question finale.
#      _scan_folder_for_images ignore le dossier _a_revoir. Un échec du score n'empêche jamais l'export.
#
# v86 — 2026-09-25 — safe-modify — Règle de forme Resize/Fill (demande utilisateur : "je préfère un logo détaillé
#      qui scroll qu'un logo fixe non reconnaissable", "je ne veux aucun rognage"). auto_analyze_and_preview
#      impose Fill quand la source recadrée est au moins N fois plus large que haute (dmd_pipeline_quality.
#      shape_forces_fill, N = 2 par défaut) au lieu du garde-fou lettres, qui forçait Fill sur 75 % des logos
#      presque carrés du pack réel F:\systems (54 776 logos), souvent reconnaissables en Resize. Le lot applique
#      désormais la même règle (il n'avait jamais eu le garde-fou) : batch_params_snapshot transmet
#      fill_min_ratio. Réglage "Seuil lettrage (px)" remplacé par "Défilement dès (L/H)" (1.0-8.0, pas 0.5,
#      config fill_min_ratio) ; note d'état t_text_forces_fill → t_shape_forces_fill.
#
# v85 — 2026-09-24 — safe-modify — Version 3.0.2. Textes de l'onglet AUTO restés en français en EN/ES (vus sur les
#      captures du README) : noms des propositions (Resize (adapté), Fill (scrolling), Optimisé, Artistique),
#      ligne d'état "'Optimisé' retenu (score…), base…" et sa note "texte illisible en Resize → Fill forcé",
#      "Sélection manuelle", barre d'état "N images | N manuelles". Passent par tr() (clés t_prop_*,
#      t_retained, t_text_forces_fill, t_manual_pick, t_status_counts). 'name' n'est qu'un libellé d'affichage
#      (aucune logique ne le compare) : traduit à la création, comportement inchangé.
#
# v84 — 2026-09-24 — safe-modify — Traitement par lot plus rapide (demande utilisateur "le traitement par lot est
#      très long"). Profil mesuré : ~1 s/image sur 1 cœur, dont ~55 % choix des réglages et ~43 % encodage GIF
#      (quantization par frame). (1) Workers : min(4, cpu) → max(min(4, cpu), min(12, cpu − 2)) — 12 sur une
#      machine à 20 threads. (2) process_one_image exporte avec shared_palette=True (dmd_gif_exporter.py v3 : une
#      palette pour toute l'animation). Mesuré sur 480 images mame/S : 62,3 s → 26,1 s (7,7 → 18,4 img/s, ×2,4),
#      ~85 Mo de RAM par worker. Le choix des réglages (55 %) n'est pas touché : rendu identique hors palette.
#
# v83 — 2026-09-24 — safe-modify — Version 3.0.1 + audit des traductions (demande utilisateur : "augmente le
#      versionning, vérifie les traductions et si certains labels ne sont pas traduits fais-le"). Méthode : harnais
#      qui relève le texte de chaque widget en FR, EN et ES (242 textes) + scan du code des affichages dynamiques
#      écrits en dur. ~60 textes restaient en français quelle que soit la langue : messages d'état et de
#      progression (AUTO, MANUEL, VIDEO, lot), panneaux d'informations (image AUTO, image MANUEL, vidéo source,
#      GIF à exporter, estimation TEXTSCROLL), titres des sélecteurs de fichiers/couleurs, en-tête de l'onglet AIDE,
#      titres "Proposition n", durée du trim VIDEO, et les boutons Remplissage/Gomme magique (traduits au démarrage
#      puis remis en français à chaque clic). Nouvelle fonction module-level tr(key, default, **kwargs) :
#      lang_manager.get + str.format, repli sur le texte FR si clé absente ou paramètre invalide. 63 clés "t_*"
#      ajoutées aux 3 lang_*.json (réutilisation des clés existantes fill/eraser/fill_active/eraser_active/
#      your_text_here). Gabarits FR multi-lignes des panneaux en constantes K_DEFAULT_*. Les messages du journal
#      (onglet DEBUG) restent en français (choix inchangé).
#
# v82 — 2026-09-24 — safe-modify — Chargement d'un gros dossier : fenêtre "Ne répond pas" pendant plusieurs
#      minutes (retour utilisateur, dossier systems/ de 54 777 images). 3 causes, 3 correctifs :
#      (1) _scan_folder_for_images : une seule passe os.walk pour les 6 extensions (avant : 6 glob("**/*.ext"),
#      6 parcours complets) ; (2) _add_image_paths : doublons testés dans un set (avant : `in` sur une liste,
#      n²/2 comparaisons) ; (3) nouveau _scan_folders_async : scan dans un thread (bouton Dossier ET
#      glisser-déposer de dossiers), compteur "Recherche d'images… n" dans la barre de titre, curseur sablier,
#      un seul scan à la fois. Nouvelle clé de langue scanning_images (fr/en/es).
#
# v81 — 2026-08-06 — safe-modify — Plan perf batch (Tier 2b, suite immédiate
#      du Tier 2a v80 — pièce finale du plan, réponse à "multithread ? ou
#      autre solution ?") : nouvelle fonction module-level `process_one_image()`
#      (picklable, aucune dépendance à self/Tk) qui reproduit exactement le
#      corps de l'ancienne boucle séquentielle de process_images(), en
#      réutilisant les fonctions pures déjà extraites (Tier 2a) +
#      export_frames_to_gif (déjà pure). `process_images()` remplace sa
#      boucle `for img_path in to_process` par un `ProcessPoolExecutor`
#      (PROCESSUS, pas des threads — le GIL limiterait trop le gain sur ce
#      pipeline, voir l'argumentaire complet dans le plan) : toutes les
#      tk.Variable/self.image_settings/self.locked_proposal nécessaires sont
#      figées UNE FOIS avant dispatch (non picklables à travers une
#      frontière de process), soumises via `pool.submit()`, consommées par
#      `as_completed()` (réagit par complétion, pas par ordre de soumission).
#      `max_workers = min(4, os.cpu_count())` par défaut (pas d'auto-max
#      agressif, chaque worker garde une animation complète + l'image source
#      pleine résolution en mémoire). Annulation en cours de lot :
#      `pool.shutdown(cancel_futures=True)` annule les futures pas encore
#      démarrées, celles déjà en cours vont à leur terme — **changement de
#      comportement assumé** vs l'ancien arrêt strict avant la prochaine
#      image, documenté explicitement plutôt que caché.
#
# v80 — 2026-08-06 — safe-modify — Plan perf batch (Tier 2a, suite immédiate
#      du Tier 1 v79) : `generate_settings_variants`/`_best_variant`/
#      `_optimize_cleanup_and_pixel_perfect`/`get_settings_for_image`
#      réduites à de simples wrappers qui lisent les tk.Variable puis
#      délèguent aux nouvelles versions pures de dmd_pipeline_quality.py
#      v23 (algorithme déplacé tel quel, pas dupliqué). Nouvelle méthode
#      `batch_params_snapshot()` (fps/duration/scroll_speed/contrast/
#      saturation/pixel_perfect en un seul dict) — prépare le Tier 2b
#      (ProcessPoolExecutor) qui devra figer ces valeurs UNE FOIS par lot
#      avant de dispatcher aux workers, plutôt que de les relire par image.
#      `_TONAL_REFINEMENT_PARAMS` (attribut de classe) devient un alias vers
#      la constante déplacée, posé APRÈS la classe (piège : un import
#      module-level utilisé directement dans le corps de la classe
#      s'exécute avant l'import en bas de fichier, NameError réelle
#      rencontrée et corrigée en vérifiant).
#      Vérifié réellement : settings + hash GIF strictement identiques
#      entre ce commit et le précédent (ab29db0), comparaison A/B directe
#      sur 3 images, pas une relecture.
#
# v79 — 2026-08-06 — safe-modify — Plan perf batch (Tier 1, suite immédiate du
#      Tier 0 v78) : `process_images()` passe `return_source=True` à
#      `render_dmd_frame()` (voir dmd_pipeline_quality.py v22) et réutilise
#      l'image source ainsi renvoyée pour `detect_palette`, au lieu d'un 3e
#      `DMDEngine.load_image()` redondant du même fichier (déjà chargé par
#      `get_settings_for_image()` et par ce même `render_dmd_frame()`).
#      `_pipeline_render_dmd_frame()` (wrapper de délégation) mis à jour en
#      parallèle pour transmettre `return_source` — même piège que
#      `_pipeline_score_variant` au Tier 0, corrigé cette fois dès la
#      première passe.
#
# v78 — 2026-08-06 — safe-modify — Plan perf batch (Tier 0, demande utilisateur
#      "traitement par lot lent, multithread ? ou autre solution ?" — plan
#      approuvé en mode Plan). `_best_variant()`/`_optimize_cleanup_and_pixel_
#      perfect()` gagnent un paramètre optionnel `resize_cache` (None par
#      défaut, propagé tel quel à `score_variant` — voir dmd_pipeline_quality.py
#      v21). `get_settings_for_image()` (chemin batch) et
#      `auto_analyze_and_preview()` (aperçu interactif Auto/IA, même
#      bénéfice gratuit) créent chacun UN `variant_cache = {}` scopé à l'image
#      en cours, partagé entre les 2 appels `_best_variant` (fit+fill) et
#      `_optimize_cleanup_and_pixel_perfect` — élimine la majorité du
#      recalcul redondant d'`optimize_for_dmd`/`adaptive_resize` à pleine
#      résolution sur les ~42 appels `score_variant` nécessaires par image
#      (fit et fill partagent la même grille tonale, le balayage cleanup et
#      la descente tonale réévaluent souvent la même combinaison). Prochaine
#      étape (Tier 1/2, même plan) : dédup du 3e `load_image` par image, puis
#      parallélisation ACROSS images via ProcessPoolExecutor.
#
# v77 — 2026-07-20 — safe-modify — Demande explicite : "ajoute raw565 comme
#      format image supporté en entrée si pas déjà le cas" — confirmé absent
#      (aucune référence "565" nulle part dans le projet avant ce fix, via
#      recherche exhaustive). Format RGB565 brut utilisé par le firmware
#      RecalBox_DMD (extension `.raw565`, aucun en-tête, 128×32 fixes) — la
#      convention exacte de packing/endianness a été vérifiée directement
#      dans le projet firmware sœur (`RecalBox_DMD.ino` constantes
#      `RAW565_W`/`RAW565_H`, `RecalBoxDMD_tool.py`
#      `convert_png_to_raw565_only`) plutôt que supposée — voir
#      dmd_engine.py v17 pour le détail du décodage
#      (`DMDEngine.load_image`/`_load_raw565`, nouveau point d'entrée
#      générique qui remplace `Image.open()` partout où une image
#      utilisateur est chargée, formats standard PIL inchangés).
#      8 sites remplacés dans ce fichier (`show_original`,
#      `update_image_info`, l'analyse IA, le calcul de settings à la volée,
#      `process_images`, `load_from_auto`, `load_manual_image`,
#      `load_multiple_manual_images`) + 5 listes d'extensions mises à jour
#      pour que `.raw565` soit sélectionnable/détecté partout où une image
#      peut entrer dans l'app : 3× `filedialog.askopenfilename(s)`
#      (sélection AUTO, MANUEL, multi-images morphing), le scan récursif de
#      dossier (`_scan_folder_for_images`), et le routage glisser-déposer
#      (`image_exts` de `on_files_dropped`). Un 9e site (le vrai moteur de
#      rendu DMD, hors de ce fichier) est couvert séparément — voir
#      dmd_pipeline_quality.py v20, sans quoi une image .raw565 aurait pu
#      être ajoutée/prévisualisée mais aurait planté à la génération réelle.
#      Vérifié en réel : nouveau test dédié (11 checks — fichier .raw565
#      encodé avec la formule EXACTE du firmware, décodage
#      DMDEngine.load_image, tolérance de quantification RGB565 vérifiée
#      pixel par pixel, erreur explicite sur taille de fichier invalide,
#      non-régression des formats standard, présence de .raw565 dans les 5
#      listes d'extensions, pipeline de rendu complet bout-en-bout sans
#      crash) + capture d'écran réelle confirmant le fichier ajouté à la
#      liste AUTO, décodé correctement (motif de test reconnu visuellement),
#      "Format: RAW565" affiché dans le panneau Informations Image, et les 6
#      propositions IA générées normalement depuis cette source.
#
# v76 — 2026-07-20 — safe-modify — Bug réel corrigé, signalé par l'utilisateur
#      après le renommage v75 : "il n'y a aucune image d'affichée dans
#      l'aide. est-ce normal ?" — clarifié : les captures d'écran référencées
#      dans lisezmoi*.md n'ont jamais été ajoutées par moi dans cette
#      session (elles existaient déjà), le vrai problème est que
#      `RecalBoxDMD_md_renderer.py` (module partagé, réutilisé tel quel
#      depuis le projet firmware RecalBox_DMD — 2 copies identiques,
#      corrigées ensemble à la demande de l'utilisateur via question à
#      choix) n'a JAMAIS su afficher de vraies images : sa gestion de la
#      balise <img> se contentait d'émettre un texte "[Image: alt](src)"
#      en italique à la place, quelle que soit l'image référencée —
#      limitation préexistante du renderer, aucun rapport avec les
#      changements de cette session. Fix : nouveau paramètre optionnel
#      `base_dir` sur `render_markdown_in_text()` (défaut `None`, 100%
#      rétrocompatible) — si fourni ET Pillow disponible, les images
#      LOCALES (jamais les URL http(s)/data:, aucun accès réseau) sont
#      chargées via PIL, sous-échantillonnées à 700px de large max (ratio
#      préservé, jamais agrandies) et insérées réellement dans le Text via
#      `image_create`, avec leurs références `PhotoImage` conservées sur le
#      widget lui-même (`tw._md_images`) pour survivre au garbage collector
#      Python une fois `render_markdown_in_text()` retournée — sans quoi
#      l'image disparaîtrait au prochain repaint (piège Tkinter classique).
#      Sans `base_dir` ou sans Pillow, comportement IDENTIQUE à avant
#      (texte "[Image: ...]"). `_refresh_help_tab_content()` (onglet AIDE)
#      passe désormais `base_dir=readme_path.parent`, seul appelant mis à
#      jour dans ce projet (l'appel équivalent dans
#      `RecalBox_DMD/tools/RecalBoxDMD_GUI.py`, projet firmware distinct,
#      n'a pas été touché — ses README ne référencent aujourd'hui aucune
#      image, la nouvelle capacité y reste disponible mais dormante si
#      besoin futur).
#      Vérifié en réel : nouveau test dédié (9 checks — 5 images
#      effectivement chargées comme vrais widgets Tk, aucun texte
#      "[Image:" résiduel, dans les 3 langues) + capture d'écran réelle
#      confirmant la première capture (onglet AUTO) affichée en vraie
#      image dans l'onglet AIDE au lieu du texte placeholder.
#
# v75 — 2026-07-20 — safe-modify — Renommage de l'application "DMD GIF
#      Converter" → "DMD GIF Creator" (demande explicite : "je voudrais
#      changer le nom de l'app et du fichier .py qui sert à la lancer en
#      'DMD GIF creator'. adapte le code et les liens ainsi que
#      l'affichage"), traité en mode plan (recherche exhaustive par agent
#      Explore, 2 décisions validées via AskUserQuestion) + montée de
#      version à v3.0.0 demandée ensuite explicitement ("passe la version
#      en v3 au vu de toutes les modifications apportées", en référence au
#      volume de travail de la session — refonte complète du tracking
#      VIDEO + audit i18n complet).
#      - Launcher renommé `dmd_gif_converter_v274.py` →
#        `dmd_gif_creator_v300.py` (simple renommage de fichier, seul
#        fichier qui l'importait — aucun — donc aucune autre référence à
#        mettre à jour). `dmd_converter.py` (ce monolithe) N'EST PAS
#        renommé, l'utilisateur ne visait que le fichier de lancement.
#      - `APP_VERSION` : `"2.7.4"` → `"3.0.0"` ; docstring du module
#        (`DMD GIF Converter` → `DMD GIF Creator`, `Version: 2.7.3` →
#        `Version: 3.0.0`, corrige au passage une désynchronisation
#        préexistante avec `APP_VERSION` déjà signalée dans un changelog
#        antérieur).
#      - Titre de fenêtre (`update_title()`, repli `title_with_version`) et
#        libellé d'en-tête sous la barre de titre (`setup_ui()`) : "DMD GIF
#        Converter"/"DMD Converter" → "DMD GIF Creator"/"DMD Creator" (la
#        version s'applique automatiquement via `self.APP_VERSION`, déjà
#        interpolée dans ces f-strings).
#      - `ConfigManager.__init__` : dossier AppData persistant
#        `"DMD_GIF_Converter"` → `"DMD_GIF_Creator"` (2 branches : `%APPDATA%`
#        présent / repli `Path.home()`). Nouvelle méthode
#        `_migrate_old_config_folder()`, appelée juste avant
#        `load_config()` : si le nouveau dossier n'a pas encore de
#        `config.json` ET que l'ancien dossier `DMD_GIF_Converter` en a un,
#        copie celui-ci vers le nouvel emplacement (crée le dossier au
#        besoin) — préserve les réglages déjà enregistrés par
#        l'utilisateur (thème, langue, luminosité LED, etc., utilisés tout
#        au long de cette session) sans jamais toucher/supprimer l'ancien
#        dossier. Les crash-logs (`if __name__ == "__main__"`) utilisent
#        déjà `config_manager.user_dir` dynamiquement, suivent le
#        renommage sans édition séparée.
#      - `dmd_ui_constants.py` (v15) : clé `TEXT_MAP` littérale "DMD
#        Converter v2.7.4" → "DMD Creator v3.0.0" (doit correspondre
#        EXACTEMENT au texte affiché par le widget d'en-tête, sinon la
#        traduction de ce libellé casse silencieusement au changement de
#        langue — fragilité déjà documentée dans le changelog du fichier).
#      - `lang_fr/en/es.json` : clés `app_title`/`app_header` mises à jour
#        avec le nouveau nom et la nouvelle version dans les 3 langues (le
#        reste de chaque chaîne, ex. "IA Enhanced"/"AI Enhanced"/"IA
#        Mejorado", inchangé). Nécessaire même si `apply_version()`
#        réapplique la bonne version au TITRE de fenêtre via une regex au
#        runtime : `_update_widget_texts` n'appelle PAS `apply_version()`
#        pour le libellé d'en-tête une fois traduit, la chaîne doit donc
#        être correcte en dur dans le JSON.
#      - `lisezmoi.md`/`lisezmoi_en.md`/`lisezmoi_es.md` et
#        `TODO_optimisation.md` : titre H1 renommé. Les légendes de
#        captures d'écran ("réalisées avec la version 2.7.4") laissées
#        INCHANGÉES à dessein — repère historique factuel des images
#        existantes, pas une chaîne "version actuelle" à resynchroniser
#        (les captures n'ont pas été reprises avec la v3.0.0).
#      Vérifié en réel : nouveau test dédié (titre de fenêtre + libellé
#      d'en-tête corrects dans les 3 langues via le cycle de traduction
#      complet, migration de config testée avec un ancien dossier simulé)
#      + suite de régression VIDEO existante rejouée sans régression +
#      lancement réel du nouveau launcher `dmd_gif_creator_v300.py` +
#      capture d'écran confirmant visuellement le nouveau titre/en-tête.
#
# v74 — 2026-07-20 — safe-modify — Audit i18n complet de toute l'interface,
#      demande explicite : "analyse toute l'interface et termine/corrige/
#      remplace les traductions manquantes ou erronées en FR puis EN & ES".
#      Méthode : scripts d'audit dédiés (scratchpad) plutôt qu'une relecture
#      manuelle — extraction par regex de tous les `text="..."` littéraux du
#      fichier + comparaison aux valeurs de lang_fr.json, extraction de tous
#      les appels `add_help_tooltip(...)` + vérification que leurs clés
#      existent dans les 3 langues, extraction de toutes les entrées
#      TEXT_MAP + vérification qu'elles pointent vers des clés existantes.
#      3 catégories de bugs réels trouvées et corrigées :
#      1) 5 widgets construits avec un texte français jamais enregistré ni
#         dans TEXT_MAP ni (par ricochet) dans lang_fr.json — restaient
#         donc figés en français quelle que soit la langue sélectionnée,
#         quel que soit le mécanisme de repli (`_update_widget_texts` ne
#         peut retrouver une clé que si le texte affiché correspond
#         EXACTEMENT à une valeur déjà chargée dans lang_manager.translations,
#         ce qui n'était le cas d'aucun des 5) : "Seuil lettrage (px):"
#         (AUTO), "🗑 Vider" (AUTO, liste d'images), "📂 Glisser-déposer\n
#         un dossier ou des images ici" (AUTO, hint zone vide), "🎨
#         Remplissage (ACTIF)"/"🧹 Gomme Magique (ACTIF)" (MANUEL, variantes
#         d'état actif des outils de dessin — le libellé de base SANS
#         "(ACTIF)" était bien enregistré, pas la variante), "Animation"
#         (MANUEL, titre de cadre, distinct de "Animation:" avec deux-points
#         déjà enregistré ailleurs).
#      2) Incohérence de langue de base : bouton "🔄 New proposition"
#         (AUTO, régénère une proposition artistique) codé en dur en ANGLAIS
#         dans une application par ailleurs entièrement construite en
#         français — pas seulement une traduction manquante mais une
#         incohérence de la langue source elle-même. Corrigé en "🔄
#         Nouvelle proposition" (le français devient la source, l'anglais
#         "New proposition" reste la traduction EN — coïncidence probable
#         de la valeur, pas un bug).
#      3) Menu contextuel (clic droit sur la liste d'images, "🗑 Retirer de
#         la liste") jamais traduit : les entrées de `tk.Menu` NE SONT PAS
#         des widgets enfants au sens de `winfo_children()`, donc
#         structurellement invisibles au parcours récursif de
#         `_update_widget_texts` — aucune quantité d'entrées TEXT_MAP
#         n'aurait pu corriger ça. Fix : `_show_image_tree_menu`
#         ré-étiquette explicitement l'entrée via `entryconfig(0,
#         label=lang_manager.get(...))` juste avant `tk_popup()`, seul
#         point où un menu contextuel peut être tenu à jour.
#      4) Périmètre le plus large : les ~40 popups `messagebox.showinfo/
#         showwarning/showerror/askyesno` de TOUTE l'application (VIDEO,
#         AUTO/batch, MANUEL, TEXTSCROLL, PARAMÈTRES/logs) avaient leurs
#         titres ET la plupart de leurs corps codés en dur en français —
#         de très loin le plus gros volume de l'audit. Les clés de titre
#         ("warning"/"error"/"info"/"success"/"complete") existaient déjà
#         dans lang_fr/en/es.json mais n'étaient JAMAIS utilisées par le
#         code (confirmé par script : listées comme clés "orphelines"),
#         suggérant une infrastructure prévue puis jamais branchée. 29
#         nouvelles clés de corps ajoutées (dont 3 déjà présentes mais
#         orphelines réutilisées : "select_images_warn", "cache_cleared",
#         "logs_exported") + 1 nouvelle clé de titre "confirmation"
#         (askyesno, absente). Pattern uniforme : `lang_manager.get(clé,
#         "texte français par défaut")` à chaque site d'appel (même
#         convention que "video_no_cv2", déjà internationalisé avant cet
#         audit) — les parties dynamiques (noms de fichiers, messages
#         d'exception bruts via `str(e)`) restent non traduites par
#         nature, seul le texte français fixe autour est remplacé. Au
#         passage, corrige un bug d'incohérence de titre pré-existant :
#         un `messagebox.showwarning` (dossier source vide) affichait le
#         titre "Erreur" au lieu de "Attention", incohérent avec toutes
#         les autres alertes non bloquantes de l'app.
#      Choix de périmètre explicite (documenté ici pour la prochaine
#      session) : le texte de la barre de statut/progression
#      (`video_status`/`progress_text_var`/`manual_status`) et les logs
#      (`logger.*`) restent volontairement HORS PÉRIMÈTRE de cet audit —
#      jamais traduits nulle part ailleurs dans l'app avant cette session
#      non plus, traités comme un flux technique/console plutôt que comme
#      de l'UI localisée (cohérent avec le fait que `logger.*` n'a jamais
#      été traduit et ne le sera probablement jamais).
#      Vérifié en réel : 3 scripts d'audit dédiés (0 gap restant confirmé
#      après correctifs, y compris un faux positif d'audit identifié et
#      vérifié à l'exécution — le hint "Glisser-déposer" contient un "\n"
#      littéral dans le texte, correctement câblé mais mal détecté par une
#      comparaison de chaînes brutes non évaluées) + nouveau test dédié
#      (`test_i18n_audit_fixes.py`, 26 checks — traduction réelle de
#      widgets AUTO/MANUEL en EN/ES, clé "New proposition" corrigée en FR,
#      menu contextuel dans les 3 langues, échantillon de clés messagebox
#      dans les 3 langues, formatage de la clé à placeholders) + suite de
#      régression VIDEO existante (8 fichiers) rejouée intégralement sans
#      régression + capture d'écran réelle (onglet AUTO en anglais :
#      "Letter threshold (px):", "🗑 Clear", hint de glisser-déposer, "New
#      proposition" tous correctement traduits).
#
# v73 — 2026-07-20 — safe-modify — Bug réel corrigé, demande explicite :
#      "les changements de zoom semblent se faire depuis le premier point
#      progressivement pour atteindre la valeur du dernier point [...] les
#      changements de zoom doivent se faire depuis le point precedent vers
#      le point concerné uniquement, pas toute la point line". Diagnostiqué
#      AVANT tout correctif via 2 scripts dédiés (diag_zoom_interp_3points.py
#      au niveau moteur pur, diag_zoom_multi_point_pipeline.py bout-en-bout
#      via le vrai pipeline) : `VideoEngine.interpolate_zoom_keyframes`
#      était déjà mathématiquement CORRECTE (interpolation locale par
#      paire de keyframes consécutives, vrai pic local confirmé à un point
#      intermédiaire, pas de "saut" du 1er au dernier point). Le vrai bug :
#      RIEN ne resynchronisait le curseur "Zoom cadrage" affiché
#      (`video_crop_zoom`) quand on navigue dans le temps
#      (`video_roi_edit_time`), contrairement à la position (déjà gérée par
#      `_video_sync_roi_from_events`) — le curseur restait bloqué sur la
#      dernière valeur réglée À LA MAIN quel que soit l'instant affiché,
#      donnant l'illusion trompeuse d'un saut direct premier→dernier point
#      dès qu'on scrubbait entre 2 points sans repasser exactement par un
#      point posé. Fix : nouvelle `_video_sync_zoom_from_keyframes`, qui
#      recalcule `video_crop_zoom` sur la valeur INTERPOLÉE à l'instant
#      courant (réutilise `VideoEngine.interpolate_zoom_keyframes` avec un
#      seul timestamp) — appelée systématiquement depuis
#      `_video_sync_roi_from_events` (donc à tous ses points d'appel
#      existants : relâchement de glissé sur la timeline, déplacement du
#      temps de cadrage, undo/redo, affichage de la frame de référence,
#      suppression d'un point). Passe par le trace existant sur
#      `video_crop_zoom` (`_video_on_zoom_change`), qui recalcule EN PLUS
#      la taille du rectangle affiché autour du centre courant — aligne
#      enfin l'aperçu live sur le modèle réel du pipeline (position figée
#      par `video_roi_events`, taille toujours dérivée du zoom courant).
#      2e demande groupée dans le même message, UI : "l'historique de
#      cadrage mérite d'être agrandi (alignement avec le bas du cadre à sa
#      gauche) avec une barre de scroll verticale" — `crop_preview_col`
#      passe de `anchor="n"` seul à `fill=tk.Y` (s'étire désormais sur
#      toute la hauteur de la rangée, dictée par `video_roi_canvas`,
#      270px) ; `roi_history_frame` passe de `fill=tk.X` à `fill=tk.BOTH,
#      expand=True` (descend jusqu'en bas, aligné avec le cadre à sa
#      gauche) ; nouveau `ttk.Scrollbar` vertical lié au `Text` via
#      `yscrollcommand`/`yview` (absent jusqu'ici, le texte au-delà de 6
#      lignes était juste tronqué sans indication).
#      Vérifié en réel : les 2 diagnostics ci-dessus (confirment le moteur
#      déjà correct, évitent un mauvais correctif côté algorithme) + nouveau
#      test dédié (`test_video_zoom_sync_on_scrub.py`, 5 checks — scrub
#      avant/exactement au/après un point intermédiaire, retour au premier
#      point, vérifie que le curseur suit l'interpolation locale réelle à
#      chaque instant) + suite de régression existante rejouée sans
#      régression + capture d'écran réelle confirmant "+50%" affiché à
#      mi-chemin exact entre un point à 90% et un point à 10% (valeur
#      interpolée correcte), et l'historique agrandi avec sa barre de
#      scroll visible.
#
# v72 — 2026-07-20 — safe-modify — Bug réel corrigé, demande explicite :
#      "ça ne fonctionne pas les points zoom sont bien enregistré avec
#      leur valeur mais pas leur position" (suite au correctif v71).
#      Clarifié via AskUserQuestion ("La position du cadre (x,y) au clic
#      'Zoom ici'") : `video_zoom_keyframes` est une piste PUREMENT
#      scalaire (t, zoom), structurellement indépendante de
#      `video_roi_events` — or `VideoEngine.compute_crop_windows` prend
#      TOUJOURS le CENTRE de la fenêtre de crop depuis `video_roi_events`
#      (jamais depuis `video_zoom_keyframes`, voir v71). Cliquer "🔍 Zoom
#      ici" enregistrait donc bien la valeur de zoom au bon instant, mais
#      RIEN ne figeait la position du cadre affiché à ce même instant — le
#      rendu final utilisait alors la position du point de zone le plus
#      proche déjà existant (potentiellement très différente), pas celle
#      voulue pour ce point de zoom précis. Fix : `_video_add_zoom_point`
#      appelle désormais aussi `_video_upsert_roi_event(t, self.video_roi,
#      "manual")` — chaque point de zoom fige donc AUSSI la position
#      courante du cadre dans `video_roi_events`, au même instant (créant
#      ou mettant à jour un point de zone "manual" existant à moins de
#      0.05s, même logique que "➕ Point ici"). Effet combiné avec le fix
#      v71 (déplacement du cadre pris en compte au relâchement) : le
#      workflow "positionner le cadre → régler le zoom → Zoom ici" fige
#      maintenant correctement les DEUX, et repositionner le cadre après
#      coup (sans re-cliquer sur un bouton) continue de mettre à jour le
#      point le plus proche grâce au fix précédent.
#      Vérifié en réel : nouveau test dédié
#      (`test_video_zoom_point_captures_position.py`, 3 checks — 2 points
#      de zoom à des instants/positions différents, vérifie que chacun fige
#      la bonne position dans `video_roi_events`, PLUS un check bout-en-
#      bout via `compute_crop_windows_from_events` confirmant que le
#      segment reste centré sur la bonne position, sans dériver vers le
#      point suivant) + suite de régression existante rejouée sans
#      régression + capture d'écran réelle confirmant visuellement 2 zones
#      + 2 points de zoom distincts dans l'historique et sur la timeline.
#
# v71 — 2026-07-20 — safe-modify — Bug réel corrigé, demande explicite :
#      "en mode cadrage manuel, la valeur de zoom fonctionne mais le
#      déplacement du cadre de zoom n'est pas pris en compte". Cause
#      racine (diagnostiquée par lecture de
#      `VideoEngine.compute_crop_windows`, qui documente déjà "ignore
#      silencieusement les tailles (w, h) de roi_positions — seul leur
#      CENTRE compte, la taille de fenêtre réelle est toujours dérivée de
#      zoom") : le CENTRE de la fenêtre de crop vient de `video_roi_events`
#      (gelé au moment où le point est committé, via "➕ Point ici"/"🔄
#      Recentrer"), la TAILLE vient toujours du curseur "Zoom cadrage" lu
#      EN DIRECT au moment de "Générer Aperçu" — d'où l'asymétrie
#      observée : changer le zoom semble "marcher" (taille toujours
#      fraîche) alors que déplacer le rectangle DÉJÀ affiché (mode "move"
#      de `_video_roi_start/_drag/_end`, staging pur depuis la refonte
#      "➕ Point ici" v69) ne mettait JAMAIS à jour ce centre — le
#      déplacement restait visible dans l'aperçu instantané mais disparaissait
#      purement et simplement au rendu final. Fix : `_video_roi_end` (mode
#      "move") met désormais à jour, au relâchement, le point le plus
#      proche du temps de cadrage courant (`_video_nearest_roi_event`,
#      même logique de correspondance à 0.3s que "🔄 Recentrer") avec la
#      nouvelle position — uniquement si `video_roi_events` n'est pas vide
#      (donc uniquement pertinent en mode "✋ Manuel" : en "🎯 Suivi
#      automatique"/"🪄 Cadrage auto", `video_roi_events` reste toujours
#      vide et le déplacement était déjà correctement pris en compte via le
#      repli implicite du pipeline sur `self.video_roi` direct).
#      2e demande groupée, UI, "rajoute la valeur de zoom du slide ou fait
#      un 'cran' qd on arrive à zéro" :
#      - Valeur numérique du zoom affichée en direct à côté du curseur
#        (`video_crop_zoom_value_var`, ex. "+40%"/"-20%"/"0%"), mise à jour
#        dans `_video_on_zoom_change` (déjà appelée à chaque changement).
#      - "Cran" au passage par zéro : `_video_on_zoom_change` happe
#        désormais la valeur sur 0.0 exactement si le glissé s'arrête à
#        moins de `VIDEO_ZOOM_SNAP_EPSILON` (0.03, nouvelle constante de
#        classe) du neutre, via un court-circuit ré-entrant sûr
#        (`self.video_crop_zoom.set(0.0); return` — la trace se redéclenche
#        une seule fois avec z==0.0 exact, pas de boucle).
#      Vérifié en réel : nouveau test dédié
#      (`test_video_roi_drag_updates_point.py`, 5 checks — commit d'un
#      point via "Point ici", déplacement SANS repasser par un bouton,
#      vérifie que le point committé ET la fenêtre de crop du pipeline
#      (`compute_crop_windows_from_events`) suivent bien la nouvelle
#      position, plus l'affichage du pourcentage et le happage à zéro) +
#      suite de régression existante rejouée sans régression
#      (`test_video_zoom_scale.py`/`test_video_mode_gating.py`/
#      `test_video_point_ici_draw_workflow.py`) + capture d'écran réelle
#      confirmant visuellement "+40%" affiché et l'aperçu de cadrage
#      devenant vide après un déplacement loin du sujet (preuve que le
#      crop suit désormais le glissé au lieu de rester figé sur l'ancienne
#      position).
#
# v70 — 2026-07-20 — safe-modify — Sélecteur "Mode de cadrage" à 3 boutons
#      radio, mutuellement exclusifs PAR CONSTRUCTION (demande explicite,
#      soumise à propositions via AskUserQuestion) : "le mode zoom auto et
#      tracking auto s'excluent l'un l'autre. quand l'un est sélectionné
#      l'autre n'est plus sélectionnable [...] et évidemment on peut
#      éteindre les 2 pour passer en mode manuel et combiner tracking +
#      zoom/cadrage [...] peut-être clarifier ce fonctionnement ? mais
#      comment ? fait moi des propositions" — 3 options soumises (sélecteur
#      3 modes / 2 cases + exclusion croisée + libellé d'état / bandeau
#      explicatif seul), "Sélecteur 3 modes (radio, recommandé)" retenue.
#      Remplace les 2 cases indépendantes "🎯 Suivi automatique (tracking)"
#      et "🪄 Resize auto" (dont le lien de forçage croisé — activer le
#      tracking forçait Resize auto à coché+grisé — existait déjà mais
#      restait invisible/incompréhensible pour l'utilisateur) par 3
#      `ttk.Radiobutton` liés à la nouvelle variable `video_crop_mode`
#      ("tracking"/"auto_zoom"/"manual") :
#      - "🎯 Suivi automatique" : comportement ORIGINAL inchangé (un seul
#        rectangle suivi par tracker OpenCV sur toute la vidéo, taille de
#        crop calculée automatiquement, système de points désactivé).
#      - "🪄 Cadrage auto (zoom)" (NOUVEAU) : l'utilisateur positionne
#        lui-même le cadrage (glisser le rectangle unique), mais sa TAILLE
#        est calculée automatiquement, comme en mode tracking — sans
#        tracker OpenCV ni système de points. Comble un vide fonctionnel
#        signalé : avant ce changement, positionner soi-même un cadrage à
#        taille automatique nécessitait de passer par le mode manuel
#        complet (avec son système de points), sans raccourci direct.
#      - "✋ Manuel" (renommage de l'ancien mode "tracking décoché") :
#        seul mode combinant système de points (zones + zoom keyframé,
#        inchangé) ET curseur "Zoom cadrage" pilotés à la main.
#      `video_roi_tracking_enabled`/`video_resize_auto` (BooleanVar)
#      CONSERVÉES telles quelles comme état DÉRIVÉ calculé par le nouveau
#      handler unique `_video_on_crop_mode_change` (remplace
#      `_video_on_tracking_toggle`, supprimée) — tout le reste du code
#      (pipeline `_video_pipeline`, `_video_effective_zoom`,
#      `_video_draw_roi_rect`, `_video_roi_start`, etc.) continue de les
#      lire SANS AUCUN changement, seuls ce handler,
#      `_video_update_point_buttons_state` (condition changée pour
#      `video_crop_mode == "manual"`, au lieu de `not
#      video_roi_tracking_enabled`) et `_video_roi_reset` (nouvelle branche
#      "auto_zoom" : repositionne le rectangle unique sans jamais créer de
#      point) distinguent explicitement les 3 modes. Avec des boutons
#      radio, l'ancien grisage de la case "Resize auto" pendant le mode
#      tracking devient inutile (l'exclusivité est déjà garantie par le
#      radio group) — seul le curseur "Zoom cadrage" reste grisé/dégrisé
#      selon le mode (`_video_on_resize_auto_toggle`, réutilisée telle
#      quelle). i18n : clés TEXT_MAP/lang_*.json "video_roi_tracking"/
#      "video_resize_auto" remplacées par "video_crop_mode_label"/
#      "video_crop_mode_tracking"/"video_crop_mode_auto_zoom"/
#      "video_crop_mode_manual" (voir dmd_ui_constants.py v13) ; tooltips
#      dédiés ajoutés pour les 3 radios, et 2 tooltips corrigés au passage
#      car décrivant encore un modèle obsolète ("tooltip_video_roi_tracking"
#      décrivait l'ancien "type du prochain point", supprimée ;
#      "tooltip_video_add_roi_point"/"tooltip_video_roi" référençaient
#      encore l'ordre de dessin PRÉ-v69 "dessiner puis cliquer Point ici",
#      inversé depuis).
#      Vérifié en réel : `test_video_zoom_scale.py` (29 checks, adapté au
#      radio group) + `test_video_mode_gating.py` (adapté + nouveau parcours
#      dédié au mode "auto_zoom" : boutons grisés, rectangle unique
#      matérialisé sans point, "Recentrer" ne crée jamais de point) +
#      `test_video_point_ici_draw_workflow.py` (adapté) — tous rejoués sans
#      régression, plus 3 captures d'écran réelles (une par mode) confirmant
#      visuellement l'état correct du curseur zoom et des boutons de points
#      pour chacun.
#
# v69 — 2026-07-19 — safe-modify — Refonte du workflow "➕ Point ici"
#      (mode manuel), suite à une clarification utilisateur avec question à
#      choix ("Point ici efface et exige un nouveau dessin" — recommandé et
#      retenu) : "en manuel l'appui sur point ici devrait demander une zone
#      de tracking hors cela n'apparaît pas on reste sur le zoom cadrage
#      qu'on peut déplacer". Cause : `_video_roi_start` (mode manuel)
#      rematérialisait TOUJOURS un rectangle par défaut dès que
#      `video_roi is None` et traitait directement le clic comme un
#      DÉPLACEMENT de ce rectangle fantôme — aucun chemin ne permettait
#      réellement de DESSINER une nouvelle zone en mode manuel, quel que
#      soit l'état de `video_roi`. `_video_add_roi_point` committait donc
#      toujours ce rectangle par défaut (jamais vraiment choisi par
#      l'utilisateur pour CE point), pas une zone dédiée à un sujet.
#      Réalisé :
#      - `_video_add_roi_point` : EFFACE désormais `video_roi` et arme un
#        nouveau flag `_video_awaiting_point_draw`, au lieu de committer
#        immédiatement.
#      - `_video_roi_start` (mode manuel) : ne rematérialise plus de
#        rectangle par défaut quand `video_roi is None` — entre en mode
#        "draw" (comme le mode tracking l'a toujours fait), permettant un
#        VRAI dessin. Le rectangle par défaut reste matérialisé ailleurs
#        (passage initial en mode manuel, confort de départ) — seul ce
#        point d'entrée spécifique change.
#      - `_video_roi_end` : si `_video_awaiting_point_draw` est armé, le
#        dessin qui vient de se terminer est EN PLUS committé
#        automatiquement comme point de zone au relâchement de la souris —
#        un dessin libre (hors de ce flux) reste du staging pur, inchangé.
#      - Toute bascule de mode (`_video_on_tracking_toggle`) désarme le
#        flag en attente (n'a plus de sens si le mode change entre-temps).
#      Vérifié en réel : nouveau test dédié
#      (`test_video_point_ici_draw_workflow.py`, 6 checks couvrant
#      effacement, entrée en mode dessin, commit auto au relâchement,
#      non-commit d'un dessin libre, annulation au changement de mode) +
#      suite de régression existante mise à jour et rejouée sans
#      régression (`test_video_mode_gating.py` adapté au nouveau flux en 2
#      temps) + capture d'écran confirmant le rectangle bien effacé après
#      clic sur "Point ici".
#
# v68 — 2026-07-19 — safe-modify — 2 demandes groupées sur le zoom cadrage,
#      demande explicite :
#      (1) Échelle de "Zoom cadrage" étendue de 0..1 à -1.0..+1.0 :
#      "-100% = resize seul, 0 = crop serré, +100% = zoom" — remplace
#      l'ancienne 0%=resize/100%=crop serré. `video_crop_zoom` (défaut
#      1.0→0.0, "crop serré" reste le point neutre), `video_crop_zoom_scale`
#      (`from_=0.0/to=1.0` → `from_=-1.0/to=1.0`), label + clé i18n
#      `video_crop_zoom_hint` (3 langues + TEXT_MAP) mis à jour.
#      `_video_effective_zoom()` (heuristique "Resize auto") retourne
#      désormais -1.0 (resize pur, remplace l'ancien 0.0) ou 0.0 (crop
#      serré, remplace l'ancien 1.0). Voir dmd_video_engine.py v7 pour le
#      détail du calcul moteur (nouveau `_zoom_crop_size` partagé,
#      2 segments d'interpolation de part et d'autre de zoom=0).
#      (2) "🪄 Resize auto" forcé coché ET grisé (non désélectionnable) en
#      mode auto-tracking, redevient librement activable en mode manuel —
#      "lors de l'activation du suivi automatique le zoom cadrage doit
#      être en resize auto lui aussi et grisé car non désélectionnable".
#      `_video_on_tracking_toggle` force `video_resize_auto=True` +
#      `video_crop_zoom_scale` désactivé (via `_video_on_resize_auto_toggle`
#      déjà existante) + grise `video_resize_auto_check` (nouvelle référence
#      stockée en attribut `self.`) au passage en mode auto ; réactive
#      juste la case (sans forcer sa valeur) au passage en mode manuel.
#      **État initial de construction traité séparément** : le même
#      forçage est appliqué explicitement à la fin de `setup_video_tab`
#      (mode auto étant le défaut, mais `_video_on_tracking_toggle` n'est
#      jamais appelée automatiquement à la construction) — détecté par le
#      nouveau test dédié (2 checks initialement en échec avant ce fix).
#      Vérifié en réel : nouveau test dédié
#      (`test_video_zoom_scale.py`, 23 checks moteur+UI) + suite de
#      régression existante rejouée sans régression + capture d'écran
#      confirmant l'échelle et le grisage.
#
# v67 — 2026-07-19 — safe-modify — Dépendance changée : opencv-python →
#      opencv-contrib-python. Bug réel signalé : "je trouve que le
#      mécanisme de tracking auto ne fonctionne pas bien. il ne garde pas
#      la sélection au milieu de la hauteur de l'écran comme si le scroll
#      vers le haut ne se faisait pas". Diagnostic (3 scripts dédiés,
#      scratchpad) : (1) `compute_crop_windows` calcule correctement le
#      panoramique vertical (vérifié sur une vidéo synthétique à
#      mouvement diagonal — y0 varie bien de 0 à 160px en suivant le
#      sujet) — pas un bug de calcul. (2) Le pipeline COMPLET (rendu réel
#      128×32 via l'app), sur la même vidéo, montre le sujet correctement
#      suivi jusqu'à ~40% du clip puis un décrochage net (luminosité du
#      pixel suivi chutant de ~173 à ~19, signe que le tracker suit
#      désormais du bruit) — le comportement de repli après décrochage
#      (dérive lente à 5%/frame vers le CENTRE, pas vers le sujet réel)
#      donne exactement l'impression d'un "scroll qui ne se fait plus".
#      (3) Cause racine confirmée : `opencv-python` (le paquet
#      effectivement installé) ne fournit QUE TrackerMIL — CSRT/KCF,
#      nettement plus robustes pour ce type de suivi, nécessitent
#      opencv-contrib-python (absent). `_create_tracker`
#      (dmd_video_engine.py) essaie déjà CSRT puis KCF avant de retomber
#      sur MIL — aucun changement de CODE nécessaire, seulement de
#      dépendance installée. Question posée à l'utilisateur (installer
#      opencv-contrib-python / améliorer seulement la récupération après
#      décrochage / les deux) → **installer opencv-contrib-python**.
#      Réalisé : `pip uninstall opencv-python` puis
#      `pip install opencv-contrib-python` (paquets mutuellement
#      exclusifs, même module `cv2`) ; docstring des dépendances mise à
#      jour en tête de fichier. **Vérifié en réel, avant/après** : même
#      scénario exact (vidéo diagonale, rectangle serré comme dessiné via
#      l'app, pipeline complet) — AVANT : décrochage net vers la frame
#      19/50 (luminosité 173→19) ; APRÈS (CSRT actif) : luminosité stable
#      ~172-174 sur les 50 frames, plus aucun décrochage. **Leçon
#      générale pour ce projet** : un signalement utilisateur vague ("ça
#      ne marche pas bien") sur une fonctionnalité dont le CALCUL est
#      déjà vérifié correct doit faire suspecter la ROBUSTESSE d'une
#      dépendance externe (ici, le tracker OpenCV) plutôt que rechercher
#      un bug de logique supplémentaire — construire un cas de test avec
#      un mouvement RÉALISTE (diagonal, pas juste horizontal comme les
#      vidéos de test précédentes) a été décisif pour révéler le
#      problème, invisible avec les tests existants qui ne bougeaient
#      jamais verticalement.
#
# v66 — 2026-07-19 — safe-modify — Correction de conception majeure suite à
#      une clarification explicite de l'utilisateur sur le modèle de la
#      refonte tracking (v58) : "il y a eu une erreur de compréhension. le
#      mode suivi automatique implique le fonctionnement initial sur toute
#      la vidéo : un point qu'on maintient dans le cadre. si ce mode est
#      choisi les boutons ajouter poi/ajouter zoom....etc doivent être
#      grisé/inopérant. ils ne sont utilisables qu'en mode manuel". Le v58
#      faisait de "🎯 Suivi automatique" le TYPE du prochain point ajouté
#      (auto/manuel pouvant coexister sur la même timeline) — ce n'était
#      PAS l'intention : la case doit piloter 2 MODES GLOBAUX EXCLUSIFS :
#      - Coché (auto) : comportement ORIGINAL simple d'avant toute la
#        refonte — un seul rectangle dessiné, suivi automatiquement par le
#        tracker OpenCV sur TOUTE la vidéo. Le système de points ne
#        s'applique PAS : `_video_on_tracking_toggle` vide désormais
#        `video_roi_events`/`video_zoom_keyframes`/`video_roi` au passage
#        dans ce mode (bug signalé : "si je recoche tracking auto le mode
#        zoom ne disparaît pas donc je ne peux pas délimiter ma zone
#        d'intérêt").
#      - Décoché (manuel) : seul mode où le système de points multi-zones/
#        zoom keyframé s'applique.
#      Nouvelle `_video_update_point_buttons_state` grise/dégrise "➕ Point
#      ici"/"🔍 Zoom ici"/"🗑️ Supprimer ce point"/"🗑️ Effacer points"/"↶
#      Annuler"/"↷ Rétablir" selon le mode (état initial : grisés, le mode
#      auto étant actif par défaut) — références des boutons désormais
#      stockées en attributs `self.` pour permettre cette reconfiguration
#      a posteriori. "🔄 Recentrer" reste toujours actif : double
#      comportement dans `_video_roi_reset` (auto = efface juste
#      `video_roi`, comportement original ; manuel = comportement point
#      inchangé du v58). `_video_add_roi_point`/`_video_upsert_roi_event`
#      utilisent désormais TOUJOURS mode="manual" (plus de notion de
#      "type du prochain point" — un point n'existe que dans le seul mode
#      où les points ont un sens). Aucun changement nécessaire côté
#      pipeline : le repli rétrocompatible déjà en place dans
#      `_video_pipeline` (point "auto" implicite unique construit depuis
#      `video_roi` quand `video_roi_events` est vide) couvre exactement le
#      mode auto désormais toujours vidé de ses points. Nouveau test
#      dédié (`test_video_mode_gating.py`, scratchpad — le scratchpad
#      d'une session précédente ayant été purgé entre-temps, l'infra de
#      test (vidéo synthétique, script de capture) a dû être
#      intégralement recréée) couvrant : boutons grisés par défaut,
#      dessin de rectangle en mode auto sans création de point, Recentrer
#      en mode auto n'efface que le rectangle, activation des boutons au
#      passage en mode manuel, workflow multi-points (tous "manual"),
#      vidage complet + regrisage au retour en mode auto, pipeline mode
#      auto (tracking continu simple) fonctionnel de bout en bout.
#      Vérifié en réel : test dédié + capture d'écran confirmant les
#      boutons visuellement grisés en mode auto.
#
# v65 — 2026-07-19 — safe-modify — Correction suite clarification
#      utilisateur sur le v64 : "le problème n'est pas là. si trim vert à
#      0.0 et trim cyan > 0.0, image blanche dans zone de cadrage vidéo" —
#      le v64 corrigeait la SÉLECTION du marqueur au clic, mais pas ce
#      symptôme distinct. Diagnostic par script dédié comparant le
#      contenu RÉEL des pixels (moyenne RGB) de video_ref_frame après un
#      glissé complet du marqueur roi_time (press+drag+release) à
#      plusieurs instants cibles, contre une extraction indépendante des
#      mêmes instants : la frame affichée restait IDENTIQUE à celle de
#      t=0.0s quel que soit l'instant réellement ciblé par roi_time — la
#      valeur affichée ne suivait donc jamais le glissé, malgré
#      `video_roi_edit_time` lui-même correctement mis à jour. Cause
#      trouvée dans `_video_trim_release` : la branche de repli
#      "rétrocompatibilité, mode tracking, aucun point encore posé"
#      réinitialisait INCONDITIONNELLEMENT `ref_time` sur
#      `video_trim_start.get()` à CHAQUE relâchement — y compris quand
#      c'était le marqueur roi_time (pas start/end) qui venait d'être
#      déplacé. Invisible tant que trim_start restait à 0.0s ET que
#      roi_time n'était jamais éloigné (les 2 tests précédents ne
#      vérifiaient que "video_ref_frame is not None"/"pas entièrement
#      noire", jamais que le CONTENU corresponde à l'instant ciblé) —
#      devenait un vrai retour en arrière visible dès que roi_time
#      s'éloignait de trim_start=0.0s. Fix : capture de
#      `self._video_trim_dragging` AVANT sa réinitialisation à None, la
#      branche de repli ne force `ref_time = trim_start` que si c'est
#      réellement "start"/"end" qui vient d'être relâché — sinon
#      `ref_time = video_roi_edit_time.get()`. **Leçon générale pour ce
#      projet** : un test qui vérifie seulement "il y a une image, elle
#      n'est pas noire" ne détecte PAS un contenu figé/incorrect si la
#      frame de repli (ici t=0.0s) est elle-même une image valide non
#      noire — comparer le CONTENU RÉEL (pixel diff ou moyenne RGB) contre
#      une extraction indépendante de l'instant attendu est nécessaire
#      pour ce genre de régression. Nouveau test dédié
#      (`test_trim_release_keeps_roi_time_frame.py`, scratchpad) comparant
#      explicitement la frame affichée à une extraction indépendante de
#      l'instant ciblé (ET à celle de trim_start, pour confirmer qu'elles
#      diffrent bien dans la vidéo de test). Vérifié en réel : 10 tests de
#      régression rejoués sans régression + capture d'écran confirmant
#      l'affichage correctement peuplé.
#
# v64 — 2026-07-19 — safe-modify — Bug réel signalé : "quand le trim vert
#      est à 0.0s, l'affichage (video framing) reste vide quelle que soit
#      la position du trim cyan". Cause trouvée par diagnostic ciblé (2
#      scripts de reproduction programmatique n'ont d'abord rien montré
#      d'anormal — `video_ref_frame` jamais None dans mes simulations —
#      avant de reconsidérer la logique de _video_trim_press elle-même) :
#      au chargement d'une vidéo, `video_roi_edit_time` (cyan) ET
#      `video_trim_start` (vert) valent TOUS LES DEUX 0.0s par défaut —
#      coïncident exactement à l'écran. Le seuil de proximité du v61
#      donnait la priorité ABSOLUE à "start"/"end" pour tout clic à moins
#      de 10px de leur ligne, SANS jamais comparer à la distance du temps
#      de cadrage — un clic pile sur le triangle cyan (visuellement à x=0)
#      était donc systématiquement capturé par "start", rendant le
#      marqueur cyan impossible à saisir/déplacer tant qu'il restait près
#      du début (un glissé qui semblait cibler le cadrage déplaçait en
#      réalité silencieusement le début de trim). Fix :
#      `_video_trim_press` ne sélectionne désormais une barre début/fin
#      que si elle est STRICTEMENT plus proche du clic que le temps de
#      cadrage (en plus de rester dans le seuil de 10px) — à distance
#      égale ou si le temps de cadrage est plus proche, il reste
#      prioritaire. **Leçon générale pour ce projet** : quand 2 éléments
#      interactifs indépendants peuvent légitimement coïncider à l'écran
#      (ici, 2 valeurs par défaut identiques), un seuil de proximité sur
#      UN SEUL des deux ne suffit jamais — il faut comparer les distances
#      des CANDIDATS ENTRE EUX, pas seulement contre un seuil fixe. Un
#      premier essai de reproduction programmatique (clics/glissés
#      simulés simples) n'a RIEN montré d'anormal — la cause n'est
#      apparue qu'en réexaminant la logique de sélection elle-même à la
#      lumière de l'état par défaut exact (0.0s partout), plutôt qu'en
#      empilant des scénarios de test toujours plus complexes. Nouveau
#      test dédié (`test_trim_roi_time_priority_at_zero.py`, scratchpad)
#      reproduisant exactement la coïncidence par défaut + vérifiant la
#      non-régression du comportement "start reste saisissable quand il
#      est clairement le plus proche". Vérifié en réel : 8 tests de
#      régression rejoués sans régression.
#
# v63 — 2026-07-19 — safe-modify — Correction suite retour utilisateur sur le
#      v62 : "la ligne cyan n'apparaît pas sur la timeline avec les
#      triangles". La ligne avait été ajoutée sur video_events_canvas (v62)
#      mais video_ruler_canvas (graduations + triangles début/fin) n'en a
#      en réalité JAMAIS eu — seuls des triangles y étaient dessinés, la
#      ligne cyan n'existait que sur video_thumb_canvas. Fix : ligne cyan
#      ajoutée à `_video_redraw_trim_triangles` (pleine hauteur de
#      video_ruler_canvas), pour que le trait soit continu sur les 4
#      bandes (indicateur, frise, règle, timeline des points). Vérifié en
#      réel : 3 tests de régression ciblés rejoués sans régression +
#      capture d'écran zoomée confirmant la continuité de la ligne sur
#      toute la hauteur de la zone trim.
#
# v62 — 2026-07-19 — safe-modify — Ligne cyan du temps de cadrage ajoutée
#      sur `video_events_canvas` (timeline des points de zone/zoom) — déjà
#      présente sur video_thumb_canvas/video_ruler_canvas/
#      video_roi_time_indicator_canvas mais manquait ici, demande explicite
#      "le trait cyan doit être présent sur la timeline aussi"
#      (`_video_redraw_roi_events`, dessinée par-dessus les segments de
#      zone/zoom pour repérer d'un coup d'œil le segment actif à l'instant
#      courant). Vérifié en réel : capture d'écran zoomée confirmant
#      l'alignement de la ligne sur les 4 bandes.
#
# v61 — 2026-07-19 — safe-modify — Bug réel signalé : "les trims de
#      délimitation de la vidéo sont déplaçables au clic ce qui pose
#      problème, ils ne doivent être mobilisés qu'au glisser (clic sur la
#      barre et déplacement), les clics faits ailleurs que sur les barres
#      déplacent le trim de framing". Cause : `_video_trim_press` (v59)
#      sélectionnait déjà le marqueur "le plus proche du clic" sans jamais
#      bouger début/fin au clic SEUL — mais la sélection elle-même n'avait
#      AUCUN seuil de distance : un clic loin de toute barre (au milieu de
#      la frise, par ex.) pouvait quand même être attribué à début/fin
#      (juste "le moins loin des 3"), et le moindre mouvement de souris
#      pendant ce clic (glissé involontaire) faisait alors sauter la
#      poignée à cet endroit — `_video_trim_drag` place directement le
#      marqueur à la position de la souris, sans offset relatif au point de
#      saisie initial. Fix : nouveau seuil `VIDEO_TRIM_HANDLE_GRAB_PX` (10px)
#      — un clic à moins de 10px d'une ligne début/fin la sélectionne (sans
#      la bouger, seul un glissé réel la déplace ensuite) ; TOUT autre clic
#      cible directement le temps de cadrage (clic ou glissé, comportement
#      inchangé pour ce marqueur). Nouveau test dédié
#      (`test_trim_click_proximity.py`, scratchpad) reproduisant exactement
#      le scénario signalé (clic loin des barres, clic proche sans glissé,
#      glissé réel) — confirme le comportement avant tout signalement
#      supplémentaire. Vérifié en réel : 6 tests de régression rejoués sans
#      régression.
#
# v60 — 2026-07-19 — safe-modify — Ajustement suite retour immédiat sur le
#      v59 : triangles début/fin de trim (video_ruler_canvas) réduits à la
#      même taille que le triangle cyan (largeur ±6→±4px, hauteur 16→12px,
#      `_video_redraw_trim_triangles`) ; hauteur de video_ruler_canvas
#      réduite en cohérence (34→28px, `video_ruler_canvas_height`) —
#      demande explicite "réduit les triangles à la même taille que le
#      cyan et réduit la hauteur de la timeline les contenant". Vérifié en
#      réel : 4 tests de régression ciblés rejoués sans régression +
#      capture d'écran zoomée confirmant la cohérence visuelle des 3
#      triangles (même taille) et la bande de règle plus compacte.
#
# v59 — 2026-07-19 — safe-modify — 4 demandes groupées sur la zone trim
#      (suite directe du v58) :
#      (1) Bug réel signalé : la poignée verte de début de trim n'était pas
#      visible au lancement — vérifiée toujours présente en réel (clamp à
#      2px déjà en place, non régressé) mais reconfirmée explicitement par
#      capture d'écran zoomée après le reste des changements ci-dessous.
#      (2) `video_ruler_canvas` (graduations + triangles début/fin de trim)
#      déplacée AVANT `video_events_canvas` (points de zone/zoom) dans
#      l'ordre d'empilement de `trim_frame` — demande explicite "la
#      timeline de temps avec les triangles doit être au-dessus de celle
#      des points".
#      (3) Triangle cyan (temps de cadrage) retiré de `video_thumb_canvas`
#      (ne restait plus qu'une simple ligne cyan, demande explicite
#      "remplacer le triangle cyan par une simple ligne cyan") ET de la
#      boucle des 3 triangles de `video_ruler_canvas` (n'en garde plus que
#      2 : début/fin de trim vert/rouge). Nouveau
#      `video_roi_time_indicator_canvas` (12px, dédié) inséré entre le
#      label "Durée: ..." et la frise de vignettes, dessinant UNIQUEMENT ce
#      triangle (réduit, `_video_redraw_roi_time_indicator`) — demande
#      explicite "déplacer le triangle au-dessus du cadre vidéo, au même
#      niveau que l'affichage durée, adapter la taille du triangle".
#      Saisissable comme les 2 autres canvas (mêmes handlers
#      `_video_trim_press/drag/release`).
#      (4) `_video_trim_press` : les poignées début/fin de trim ne se
#      déplacent plus au simple clic (seul un glissé réel via
#      `_video_trim_drag`, déclenché par `<B1-Motion>`, les bouge
#      désormais) — demande explicite "on ne peut déplacer les trim
#      début/fin de vidéo que par glisser". Le marqueur "temps de
#      cadrage" (roi_time) garde son comportement inchangé (clic OU
#      glissé) — demande explicite confirmée par l'utilisateur.
#      **Bug réel trouvé et corrigé pendant l'implémentation** :
#      `video_roi_time_indicator_canvas` construit AVANT l'assignation de
#      `self.video_thumb_canvas_width` (utilisée pour sa largeur) —
#      `AttributeError` immédiate détectée par la suite de tests (pas par
#      la compilation) ; réordonné.
#      Vérifié en réel : 10 tests de régression rejoués sans régression +
#      capture d'écran zoomée confirmant les 4 points (poignée verte
#      visible à t=0, ordre règle/points inversé, triangle cyan réduit
#      au-dessus de la frise avec simple ligne cyan dans la frise
#      elle-même, aucun élément masqué en bas).
#
# v58 — 2026-07-19 — safe-modify — Refonte complète du tracking (zones
#      multiples + zoom keyframé + historique undo/redo + timeline
#      graphique), fonction phare de l'onglet VIDEO, demande explicite après
#      passage en mode plan (plan approuvé, voir
#      C:\Users\shan_\.claude\plans\...quizzical-canyon.md) :
#      - Modèle de données : `video_roi_keyframes` (2-tuples (t, roi), mode
#        manuel uniquement) renommé/reconçu en `video_roi_events` (liste de
#        dicts {"t","roi","mode":"auto"|"manual"}) — un point "auto" réamorce
#        le tracker OpenCV jusqu'au point suivant, un point "manual" fige le
#        cadrage (cut net, sans interpolation) jusqu'au point suivant. La
#        case "🎯 Suivi automatique" ne pilote plus un mode global exclusif
#        mais le TYPE du prochain point ajouté — plusieurs points auto et
#        manuels peuvent se succéder librement sur la même vidéo.
#      - Nouvelle piste indépendante `video_zoom_keyframes` (liste de
#        (t, zoom)), interpolée linéairement dans le temps dès 2 points
#        (contrairement aux zones : le zoom est un paramètre continu).
#      - Nouveaux boutons : "➕ Point ici" (commit explicite du rectangle
#        dessiné comme point de zone — la création d'un point n'est PLUS
#        automatique, changement de comportement assumé : dessiner/déplacer
#        le rectangle reste du STAGING pur, voir _video_roi_end/
#        _video_display_ref_frame), "🔍 Zoom ici" (commit d'un point de
#        zoom), "🗑️ Supprimer ce point" (retrait ciblé du point le plus
#        proche, zone ou zoom), "↶ Annuler"/"↷ Rétablir" (undo/redo, même
#        pattern pointeur que l'onglet MANUEL — manual_history/
#        manual_history_index/_manual_commit_history).
#      - Nouvelle timeline graphique (`video_events_canvas`, bande fine sous
#        la frise de vignettes) : disque orange = point auto, carré violet =
#        point manuel, reliés par une ligne jusqu'au point suivant (portée
#        réelle du segment) ; losange sarcelle = point de zoom, sous-ligne
#        dédiée. Cliqué-glissé pour déplacer un point dans le temps
#        (`_video_event_press/drag/release`, calqués sur
#        `_video_trim_press/drag/release`).
#      - Nouveau cadre "📜 Historique de cadrage" (texte, sous l'aperçu du
#        cadrage) listant chronologiquement tous les points (zone + zoom).
#      - `_video_pipeline` : remplace le choix binaire tracking-global/
#        keyframes-manuelles-interpolées par un appel unique à
#        `VideoEngine.compute_crop_windows_from_events`, avec repli
#        rétrocompatible (point implicite unique à partir de `video_roi` si
#        `video_roi_events` est vide — comportement identique à avant pour
#        qui n'utilise jamais les nouvelles fonctions).
#      - **2 bugs réels trouvés et corrigés pendant l'implémentation** :
#        (1) `_video_trim_drag`/`_video_roi_end` référençaient encore
#        l'ancienne méthode `_video_sync_roi_from_keyframes`/
#        `_video_upsert_roi_keyframe` (supprimées) — corrigés vers le
#        nouveau modèle, `_video_roi_end` ne commite PLUS automatiquement
#        (staging uniquement, cohérent avec la nouvelle philosophie de
#        commit explicite). (2) Crash TrackerMIL réel signalé par
#        l'utilisateur via capture d'écran — voir dmd_video_engine.py v6.
#        (3) Boutons "↶ Annuler"/"↷ Rétablir" invisibles (`winfo_ismapped()
#        == 0`) : une 2e rangée de boutons faisait dépasser de quelques
#        pixels la hauteur FIXE du Notebook — `pack()` ne mappe PAS du tout
#        un widget qui ne tient plus dans l'espace restant (contrairement à
#        un simple rognage visuel). Fix : fusionné dans la rangée
#        principale de boutons (économise une rangée entière plutôt que de
#        rogner davantage), hauteur du cadre historique texte réduite
#        8→6 lignes en marge de sécurité supplémentaire.
#      Vérifié en réel à chaque étape : suite de régression complète (9
#      tests dont 2 réécrits pour le nouveau modèle) + capture d'écran
#      confirmant visuellement timeline, historique texte, boutons undo/redo
#      tous visibles, rien de masqué en bas.
#
# v57 — 2026-07-19 — safe-modify — Correction suite retour utilisateur sur le
#      v56 (5) : le bouton "Quitter" n'était pas bien positionné (bas
#      aligné sur le bas du FOOTER, mal interprété). Clarification exacte :
#      "le bas du bouton doit être aligné avec le bas du cadre qui contient
#      tous les éléments (sauf la barre de progression). le bouton qui doit
#      être placé comme un des onglets de navigation mais en bas du cadre.
#      shan_aya 2026 reste aligné avec la barre de progression". Réalisé :
#      - "Quitter" sorti du footer, replacé comme enfant DIRECT du Notebook
#      (self.notebook, pas footer_left) via `place()` en coordonnées
#      absolues (x=0, y=notebook_height-btn_h, width=largeur de la bande de
#      tabs) — occupe la zone VIDE de la bande d'onglets latérale sous
#      "AIDE", jusqu'au bas du Notebook (= bas du cadre contenant tous les
#      éléments de l'app, hors footer/barre de progression). Visuellement,
#      ressemble à un 8e "onglet" tout en bas de la colonne de navigation.
#      Impossible d'insérer un vrai onglet Notebook supplémentaire à cet
#      effet (`.add()` réservé aux pages de contenu) — `place()` est le seul
#      mécanisme permettant de superposer un widget à un endroit précis
#      SANS passer par le geometry manager pack/grid du Notebook. Largeur/
#      position resynchronisées sur `<Configure>` du Notebook (même pattern
#      que `_video_sync_canvas_widths`).
#      - `footer_left` (colonne dédiée, largeur synchronisée sur la bande de
#      tabs) supprimé entièrement — n'a plus lieu d'être une fois Quitter
#      sorti du footer. "Shan_ayA 2026" repasse en label simple, à gauche du
#      footer, alignée avec la ligne de la barre de progression (comportement
#      demandé explicitement, contrairement au bouton Quitter).
#      Vérifié en réel (capture d'écran) : "Quitter" apparaît bien comme un
#      8e élément de navigation en bas de la colonne d'onglets, bas aligné
#      sur le bas du Notebook ; "Shan_ayA 2026" reste sur la ligne du footer
#      avec la barre de progression. 3 tests de régression rejoués (smoke,
#      pipeline complet, glissé start/end pendant lecture) — aucune
#      régression.
#
# v56 — 2026-07-19 — safe-modify — 5 demandes groupées suite directe du v55 :
#      (1) "Aperçu Animation (Vidéo)" aligné sur "Paramètres GIF Vidéo" en
#      s'agrandissant vers le BAS (preview_col + preview_frame en
#      fill=Y/fill=BOTH+expand, au lieu de leur hauteur naturelle plus
#      courte) — colonne 4 désormais aussi haute que la colonne 3.
#      (2) Canvas ROI revenu à une largeur FIXE (620px, comme avant v54) au
#      lieu d'être resynchronisé sur la largeur de la rangée du haut
#      (~1500px+) : demande explicite "la prévisualisation dans ROI n'a pas
#      d'intérêt à être aussi large, reviens au cadrage pleine image" — la
#      vidéo source letterboxait avec d'énormes bandes noires sans rien
#      apporter à un canvas aussi large.
#      (3) **Bug réel corrigé** : "le problème de l'image qui ne reste pas
#      lors du déplacement du trim est revenu". Root cause DIFFÉRENTE du
#      bug v52 (pas de concurrence cv2/thread cette fois) : glisser les
#      poignées START/END déclenche (trace_add sur video_trim_start/end)
#      `_video_update_gif_info`, qui modifie le texte du cadre "ℹ️ GIF à
#      exporter" — imbriqué dans row_left/col2 depuis v55 — dont le
#      changement de taille se propage en `<Configure>` jusqu'à `top_row`,
#      déclenchant `_video_sync_canvas_widths`, qui appelait
#      `_video_display_ref_frame()` À CHAQUE fois, y compris pendant un
#      glissé de trim en cours — un redessin du canvas ROI intercalé au
#      mauvais moment faisait disparaître l'image affichée. Fix : retiré
#      toute référence au canvas ROI de `_video_sync_canvas_widths` (cohérent
#      avec le point (2) ci-dessus, qui rend ce canvas de toute façon fixe)
#      — ce callback ne touche plus qu'à la frise de trim/échelle de temps.
#      Nouveau test de régression dédié
#      (`test_trim_start_end_drag_regression.py`, glisse les poignées
#      start/end pendant que la lecture intégrée tourne, avec
#      `root.update_idletasks()`/`root.after` pour laisser les Configure
#      différés s'exécuter avant de vérifier que l'image reste affichée) —
#      reproduit puis confirme le fix.
#      (4) Bouton "Quitter" + label "Shan_ayA 2026" déplacés de la droite
#      vers la GAUCHE du footer, largeur alignée dynamiquement sur celle de
#      la bande d'onglets latérale (mesurée via `auto_frame.winfo_x()` dans
#      le notebook, resynchronisée sur `<Configure>` du notebook — même
#      pattern que `_video_sync_canvas_widths`). **Bug réel rencontré et
#      corrigé pendant l'implémentation** : `pack_propagate(False)` appelé
#      AVANT l'ajout des enfants (bouton/label) figeait le cadre à une
#      taille quasi nulle, masquant totalement bouton et label — corrigé en
#      déplaçant `pack_propagate(False)` dans le callback de
#      resynchronisation, une fois une largeur réelle mesurée.
#      (5) Bouton "Quitter" + label bas-alignés (`pack(side=tk.BOTTOM)`) dans
#      leur colonne, pour que le bas du bouton s'aligne sur le bas du cadre
#      global de l'app (footer), suite à une clarification explicite de
#      l'utilisateur après une première demande ambiguë ("aligne sur le bas
#      du dernier cadre ROI") — la relation cadre ROI/footer n'étant pas
#      structurellement simple (hauteur du Notebook fixe et partagée par
#      tous les onglets, indépendante du contenu de l'onglet VIDEO), une
#      question à choix a confirmé que l'intention visait le bas de la
#      fenêtre, pas spécifiquement le cadre ROI.
#      Vérifié en réel à chaque étape (captures d'écran) + suite de
#      régression complète (8 tests, dont le nouveau) rejouée sans
#      régression.
#
# v55 — 2026-07-19 — safe-modify — Bug réel confirmé par l'utilisateur suite
#      au v54 : la rangée "Framing zoom" + les boutons "Recentrer/Effacer
#      points/Auto-tracking" du cadre "Zone d'intérêt" étaient MASQUÉS en bas
#      de fenêtre (colonne 4 "Aperçu Animation + GIF à exporter" trop haute,
#      poussait tout le contenu du dessous hors de l'écran réel de
#      l'utilisateur — non visible sur ma capture de test, résolution
#      d'écran probablement plus grande). Fix : "ℹ️ GIF à exporter" déplacé
#      de la colonne 4 (sous "Aperçu Animation") vers la colonne 2 (sous
#      "ℹ️ Vidéo Source", nouveau sous-cadre `col2` dans `row_left`) — la
#      colonne 4 ne contient plus que l'aperçu animation, nettement moins
#      haute, ce qui réduit la hauteur totale de la rangée du haut d'environ
#      140px et libère la place nécessaire au cadre ROI en dessous. Hauteur
#      du Text "ℹ️ Vidéo Source" réduite de 14 à 6 lignes (contenu réel).
#      7 tests de régression relancés — tous OK. Vérifié en réel par capture
#      d'écran : "Framing zoom", case "Auto resize", "Recentrer", "Effacer
#      points" et "Auto-tracking" maintenant tous visibles au-dessus de
#      "Ready"/"Quit"/barre de progression.
#
# v54 — 2026-07-19 — safe-modify — Refonte de la mise en page du haut de
#      l'onglet VIDEO (4 demandes utilisateur groupées) :
#      (1) Cadres "ℹ️ Vidéo Source" et "Paramètres GIF Vidéo" alignés
#      PRÉCISÉMENT sur le bas des boutons de lecture (⏪▶️⏹️⏩), pas juste
#      entre eux : introduction d'un sous-cadre `row_left` regroupant les
#      colonnes 1-3 (bouton+lecteur / infos source / paramètres), séparé de
#      la colonne 4 (aperçu animation) — sans cette séparation, `fill=tk.Y`
#      étirait ces 2 cadres sur la hauteur de la colonne la PLUS HAUTE des 4
#      (généralement la colonne aperçu, plus grande), pas sur celle des
#      boutons de lecture comme demandé.
#      (2) Cadres "Aperçu Animation (Vidéo)" + "ℹ️ GIF à exporter" remontés
#      en 4e colonne de la rangée du haut, à côté de "Paramètres GIF Vidéo"
#      (auparavant alignés sous "Sélection (trim)").
#      (3) Zones "Sélection (trim)" et "Zone d'intérêt" passées en pleine
#      largeur (main_frame), largeur resynchronisée dynamiquement sur celle
#      de la rangée du haut (`_video_sync_canvas_widths`, lié au Configure
#      de `top_row`).
#      (4) Bug réel trouvé et corrigé en cours de route : `top_row.pack(
#      fill=tk.X)` faisait que `top_row.winfo_width()` reflétait la largeur
#      DISPONIBLE de `main_frame` (bien plus large que le contenu réel des
#      4 colonnes), ce qui rendait les zones trim/ROI resynchronisées
#      beaucoup trop larges (vignettes comprimées avec un grand vide à
#      droite, fenêtre passée à ~3735px). Fix : `top_row.pack(anchor="w")`
#      sans fill, pour que sa largeur reflète exactement ses colonnes.
#      Vérifié : rien n'est masqué en bas (statut "Ready", bouton "Quit" et
#      barre de progression restent visibles sous la zone ROI). 7 tests de
#      régression relancés (smoke, pipeline complet, crop manuel,
#      zoom/keyframes, trim live preview, lecteur intégré, concurrence
#      ROI/lecture) — tous OK, aucune régression.
#
# v53 — 2026-07-19 — safe-modify — Réorganisation de la toolbar VIDEO
#      (demande utilisateur) : (1) cadre "Lecture" déplacé sous le bouton
#      "📹 Charger Vidéo" (même colonne, plus à côté) ; (2) cadre "ℹ️ Vidéo
#      Source" étiré verticalement (`fill=tk.Y`, plus de `height=` fixe sur
#      le Text) pour s'aligner sur la hauteur de la colonne
#      bouton+lecteur ; (3) cadre "Paramètres GIF Vidéo" déplacé du bas du
#      panneau gauche vers le haut, à côté du cadre "ℹ️ Vidéo Source" —
#      contenu (FPS/Durée/Couleurs/pixel-perfect/qualité auto/boucle)
#      inchangé, seul l'emplacement change.
#
# v52 — 2026-07-19 — safe-modify — 2 demandes utilisateur :
#      (1) Bug réel corrigé : "quand on relâche la barre temps de cadrage
#      l'image disparaît dans ROI". Cause : `_video_trim_release`
#      rafraîchissait la frame de référence "officielle" dans un THREAD
#      séparé (`_video_refresh_ref_frame`/`_video_set_ref_frame`,
#      supprimées), qui ouvrait son PROPRE `cv2.VideoCapture` sur le
#      fichier vidéo — en VRAIE concurrence avec le VideoCapture persistant
#      de la lecture intégrée (v51, `_video_playback_tick`, qui tourne en
#      continu via `root.after` sur le même fichier). 2 handles cv2 lus en
#      parallèle depuis 2 threads différents sur le même fichier
#      provoquait des lectures corrompues (frame noire) sur le backend
#      Windows utilisé. Fix : `_video_trim_release` appelle désormais
#      `_video_show_frame_at_time` directement (SYNCHRONE, plus de thread)
#      — comme les extractions pendant le glissé lui-même, qui ne
#      montraient jamais ce bug car synchrones sur le thread principal,
#      donc jamais réellement concurrentes avec la boucle de lecture (qui
#      tourne AUSSI sur le thread principal). Même cause potentielle
#      trouvée et corrigée au chargement initial : `_video_playback_open`
#      déplacé de `_video_load_from_path` (où il tournait EN PARALLÈLE du
#      thread d'extraction vignettes/référence) vers la fin de
#      `_video_on_thumbnails_ready` (qui ne s'exécute qu'une fois ce thread
#      terminé) — élimine la même fenêtre de concurrence au chargement,
#      pas seulement au relâchement du marqueur.
#      (2) Texte de statut sous "📹 Charger Vidéo" supprimé (StringVar
#      `video_status` conservée en interne, juste plus affichée — l'info
#      équivalente est déjà dans le cadre "ℹ️ Vidéo Source").
#
# v51 — 2026-07-19 — safe-modify — Lecteur vidéo intégré + refonte visuelle
#      du trim (demande utilisateur, 2 messages successifs affinant la
#      même demande) :
#      - Cadre "Lecture" intégré (lecture en boucle, mode resize, démarrée
#        après sélection du fichier) avec boutons ⏪/▶️/⏹️/⏩ ; clic dans le
#        cadre = ouverture taille réelle dans le lecteur Windows
#        (`os.startfile`, reprend `video_play_original`). Bouton dédié
#        "▶️ Lire l'original" supprimé. Nouvelles méthodes
#        `VideoEngine.open_capture`/`read_capture_frame` (boucle
#        automatiquement en fin de flux)/`seek_capture`/`release_capture`
#        (dmd_video_engine.py v4) — gardent un VideoCapture ouvert entre
#        appels, contrairement aux autres méthodes du module.
#      - 3 marqueurs unifiés sur la frise de trim (remplace l'ancien
#        scrubber "Temps de cadrage" séparé) : début/fin (vert/rouge,
#        triangle en bas sur un nouveau `video_ruler_canvas`) + temps de
#        cadrage (cyan, triangle en haut ET en bas). Saisissables
#        indifféremment depuis les 2 canvas ; le marqueur cyan reste
#        toujours contraint à l'intérieur de [trim_start, trim_end].
#      - Échelle de temps graduée sous la frise (`_video_draw_time_ruler_ticks`,
#        dessinée une seule fois par vidéo chargée).
#      - Label "Durée" déplacé au-dessus de la frise.
#      - Cadre "ℹ️ Vidéo Source" doublé en largeur (28→56 caractères).
#      - "Aperçu Animation (Vidéo)" aligné verticalement sur "Sélection
#        (trim)" via un spacer dont la hauteur suit dynamiquement celle de
#        la toolbar.
#
# v50 — 2026-07-19 — safe-modify — 3 demandes utilisateur sur l'onglet VIDEO :
#      (1) "🎬 Générer Aperçu" déplacé du panneau gauche au panneau droit,
#      juste à côté de "💾 Exporter GIF" (`video_action_row`, sous la
#      preview) — les 2 actions du flux génération→export regroupées.
#      (2) Nouveau cadre "ℹ️ Vidéo Source" (panneau gauche, sous la
#      toolbar) : fichier, résolution, durée, fps natif, nombre de frames
#      total, taille disque — même pattern Text lecture-seule que
#      "Informations Image" (AUTO/MANUEL). Rafraîchi dans
#      `_video_load_from_path`.
#      (3) Nouveau cadre "ℹ️ GIF à exporter" (panneau droit, sous les
#      boutons) : dimensions (128×32 fixe), FPS, nombre de frames, couleurs,
#      boucle, poids estimé — remplace l'ancien label isolé "Poids GIF
#      estimé :" (fondu dans ce cadre). Nombre de frames et poids sont des
#      ESTIMATIONS (fps×durée réglés) tant qu'aucun aperçu n'a été généré ;
#      deviennent les valeurs RÉELLES de la dernière génération une fois
#      `_video_pipeline_done` passé (`self.video_frames` rempli). Rafraîchi
#      en direct via `trace_add("write", ...)` sur `video_fps`/
#      `video_trim_start`/`video_trim_end`/`color_count_var`/
#      `manual_loop_mode`/`manual_loop_count` (variables partagées avec
#      d'autres onglets — traces ADDITIONNELLES, ne remplacent aucune trace
#      existante).
#
# v49 — 2026-07-19 — safe-modify — Cadrage manuel de la zone d'intérêt VIDEO,
#      demande explicite : "si l'utilisateur n'utilise pas le tracking il
#      faut qu'il puisse déplacer la zone de crop manuellement avec
#      prévisualisation". Réalisé :
#      - Nouvelle case "🎯 Suivi automatique (tracking)"
#        (`video_roi_tracking_enabled`, défaut coché = comportement
#        historique inchangé). Décochée, `_video_pipeline` n'invoque plus
#        `VideoEngine.track_roi` (aucun tracker OpenCV) : `compute_crop_windows`
#        reçoit la MÊME position ROI répétée pour toutes les frames — cadrage
#        fixe, positionné manuellement.
#      - `_video_roi_start`/`_video_roi_drag`/`_video_roi_end` gèrent
#        désormais 2 modes : "move" (clic À L'INTÉRIEUR du rectangle déjà
#        dessiné → le déplace, taille inchangée) et "draw" (clic en dehors →
#        dessine un nouveau rectangle, comportement historique). Logique de
#        conversion canvas→frame factorisée dans
#        `_video_canvas_rect_to_frame_roi` (évite la duplication entre les 2
#        modes).
#      - Nouveau canvas "Aperçu du cadrage" (256×64, à droite du canvas ROI) :
#        `_video_update_crop_preview` rend en direct (frame de référence
#        seule, pas le pipeline multi-frames complet) le résultat 128×32 du
#        cadrage courant, appelé à chaque mouvement de souris pendant le
#        déplacement/dessin ET à chaque changement de ROI (reset, nouvelle
#        frame de référence) — c'est la SEULE prévisualisation disponible en
#        mode manuel tant que "Générer Aperçu" n'a pas été cliqué.
#      - Libellé du cadre ROI renommé "Zone d'intérêt (suivie
#        automatiquement)" → "Zone d'intérêt (cadrage vidéo)" (le tracking
#        n'est plus systématique).
#
# v48 — 2026-07-19 — safe-modify — Bug réel trouvé UNIQUEMENT par capture
#      d'écran (technique PrintWindow déjà éprouvée sur ce projet), après v47 :
#      `self.video_thumb_canvas.pack(fill=tk.X)` étire le canvas de trim à la
#      largeur réelle du panneau (souvent bien plus large que la constante
#      `video_thumb_canvas_width=760` utilisée par TOUT le calcul de
#      coordonnées — vignettes/poignées/conversion clic→temps) — un Canvas Tk
#      avec `width=` explicite s'étire quand même si `fill=tk.X` est demandé,
#      `width` ne devient qu'une taille minimale. Constaté visuellement :
#      poignée rouge de fin de trim à ~70% de la frise alors que "0.0s→5.0s"
#      (sélection 100%) était affiché, moitié droite de la frise sans
#      vignette. Bug présent depuis la toute première version de l'onglet
#      (v45, canvas 600px) mais invisible en tests automatisés (aucun rendu
#      écran) et peu flagrant à 600px sur un écran de dev standard — révélé
#      par l'agrandissement à 760px (v47) + une fenêtre large lors de la
#      capture. Fix : retrait de `fill=tk.X`
#      (`self.video_thumb_canvas.pack(anchor="w")`), le canvas garde
#      exactement sa largeur déclarée. Revérifié par capture d'écran (poignée
#      au bord droit exact) + re-exécution des tests automatisés existants
#      (aucune régression logique).
#
# v47 — 2026-07-19 — safe-modify — 5 demandes utilisateur sur l'onglet VIDEO
#      (v45-v46) :
#      (1) Bouton "▶️ Lire l'original" (toolbar VIDEO) : lance la vidéo
#      source dans le lecteur par défaut du système (`os.startfile`, même
#      mécanisme déjà utilisé par `clear_progress_and_notify` pour ouvrir un
#      dossier) plutôt que de réimplémenter un lecteur vidéo dans Tkinter —
#      plus robuste (codecs, seek, contrôles natifs).
#      (2) Frise de trim agrandie 600×60 → 760×100 ("plus de visibilité"),
#      nombre de vignettes extraites 40→60 pour rester dense à cette largeur,
#      épaisseur des poignées 3→4px.
#      (3) Nouveau réglage "Durée (s)" (`self.video_duration`, Spinbox) :
#      ajuste `trim_end = trim_start + durée` (clampé à la fin de la vidéo
#      source), synchronisé dans les 2 sens avec le glissé des poignées de
#      trim (`_video_trim_drag` met aussi à jour `video_duration`). Par
#      défaut = durée totale de la vidéo source au chargement — l'ancien
#      plafond artificiel `MAX_TRIM_SPAN=10.0` (v45) est retiré, il n'était pas
#      demandé par l'utilisateur et empêchait justement ce défaut.
#      (4) FPS par défaut = fps natif de la vidéo source au chargement
#      (`self.video_fps.set(round(meta["fps"]))`, borné à [1,60] par
#      cohérence avec le Spinbox existant), au lieu de la valeur persistée
#      générique précédente.
#      (5) Estimation du poids du GIF résultant : nouvelle fonction
#      `estimate_gif_size` (dmd_gif_exporter.py v2, encode réellement en
#      mémoire avec les mêmes paramètres qu'un export — poids exact pour ces
#      réglages, pas une heuristique), calculée en fin de `_video_pipeline`
#      (thread, juste après le rendu des frames) et affichée dans un label
#      dédié ("Poids GIF estimé :") sous l'aperçu. Recalculée uniquement au
#      clic sur "Générer Aperçu" — si l'utilisateur change couleurs/pixel-
#      perfect après coup sans régénérer, l'estimation affichée devient
#      logiquement obsolète (comportement attendu, pas un bug).
#
# v46 — 2026-07-19 — safe-modify — Bug réel trouvé en testant le pipeline
#      VIDEO (v45) avec une vraie vidéo générée (carré mobile suivi par le
#      tracker) : `_video_pipeline`/`_video_load_thumbnails_and_ref`
#      capturaient l'exception via `except Exception as e:` puis référençaient
#      `e` dans une lambda différée par `self.root.after(0, lambda: ...)` —
#      Python efface automatiquement le nom lié par `except ... as e:` à la
#      sortie du bloc, donc au moment où la lambda s'exécutait réellement (sur
#      le thread UI, après le retour du thread worker), `e` n'existait plus :
#      `NameError: cannot access free variable 'e'`, remplaçant silencieusement
#      le message d'erreur voulu par un crash de callback Tkinter. Fix :
#      capturer `str(e)` dans une variable locale AVANT de programmer le
#      callback différé, transmise à la lambda via un paramètre par défaut
#      (`lambda msg=error_msg: ...`) plutôt que par fermeture sur `e`.
#
# v45 — 2026-07-19 — safe-modify — Nouvel onglet VIDEO (demande utilisateur),
#      inséré entre MANUEL et TEXTSCROLL : import d'un fichier vidéo, trim
#      début/fin (frise de vignettes + curseurs), zone d'intérêt (ROI)
#      délimitée par l'utilisateur et suivie automatiquement par un tracker
#      OpenCV (CSRT/KCF, avec fallback dernière-position-connue puis
#      relâchement progressif vers le centre en cas de décrochage durable) —
#      le moteur calcule une fenêtre de crop par frame centrée sur le ROI
#      trické (lissage EMA du centre) pour simuler un scroll/pan dans la
#      vidéo. Qualité GIF réglable automatiquement via un moteur dédié
#      simplifié (1 passe sur quelques frames représentantes, PAS le moteur
#      Auto/IA existant score_variant/6-propositions — signalé par
#      l'utilisateur comme nécessitant sa propre refonte, non réutilisé ici
#      par décision explicite). Preview cohérente avec les 3 autres onglets
#      de génération (LED/loupe/classique, `_add_led_zoom_icon`/
#      `_add_led_brightness_slider`/`_get_force_pixel_perfect` réutilisés tels
#      quels). Toute la logique non-Tkinter (décodage vidéo, tracking, calcul
#      de crop, qualité auto) vit dans le nouveau module `dmd_video_engine.py`
#      (classe `VideoEngine`), suivant le pattern de démonolithisation déjà en
#      cours (dmd_engine.py/dmd_manual_effects.py/dmd_pipeline_quality.py).
#      Nouvelle dépendance : opencv-python (import protégé, `CV2_AVAILABLE` —
#      l'onglet affiche un message clair et désactive ses contrôles si absent
#      au lieu de planter). Pipeline complet exécuté en thread séparé
#      (`threading.Thread(daemon=True)`, pattern déjà utilisé par
#      `process_images`) pour ne pas geler l'UI, avec barre de progression
#      partagée (`update_progress`/`clear_progress_and_notify`, déjà globale à
#      toute l'app). `color_count_var`/`pixel_perfect_var`/
#      `led_brightness_var`/`manual_loop_mode`/`manual_loop_count` réutilisés
#      tels quels (déjà des réglages globaux inter-onglets, pas de doublon
#      `video_*` créé). Synchronisation `apply_translations`/3×`lang_*.json`/
#      `TEXT_MAP` (dmd_ui_constants.py) pour le nouvel onglet — voir
#      changelogs associés.
#
# v44 — 2026-07-19 — safe-modify — `_add_led_zoom_icon` : le clic pour ouvrir
#      l'aperçu LED agrandi n'était actif que sur la petite icône 🔍 (visible
#      seulement au survol), demandé par l'utilisateur pour s'étendre à TOUTE
#      la zone de preview. Ajout d'un binding `<Button-1>` sur le canvas
#      lui-même (en plus de celui déjà sur l'icône, conservé pour
#      compatibilité), avec le même garde-fou que l'icône (n'ouvre le zoom que
#      si "Mode DMD / Force pixel-perfect" est coché — pas de rendu LED à
#      zoomer sinon). Curseur "hand2" appliqué à tout le canvas au survol
#      (au lieu de seulement l'icône) pour indiquer visuellement que toute la
#      zone est cliquable.
#
# v43 — 2026-07-19 — safe-modify — `_optimize_cleanup_and_pixel_perfect` :
#      2 correctifs demandés explicitement par l'utilisateur ("je répète").
#      (1) `pixel_perfect_options = (True,) if force_pixel_perfect else (False,
#      True)` permettait à l'étape 1 de choisir pixel_perfect=True pour la
#      proposition "Optimisé" même quand la case globale "Mode DMD / Force
#      pixel-perfect" est DÉCOCHÉE (testé comme alternative, retenu s'il
#      améliorait le score) — incohérent avec les propositions 1/2, qui
#      utilisent `pixel_perfect=force_pixel_perfect` directement, sans jamais le
#      re-choisir algorithmiquement. Remplacé par `pixel_perfect_options =
#      (force_pixel_perfect,)` — une seule valeur, plus de recherche, "Optimisé"
#      respecte désormais strictement la case globale comme 1/2. (2) La popup/
#      panneau d'info de la proposition 3 (`proposal_info_labels`, dans
#      `auto_analyze_and_preview`) n'affichait pas les valeurs de contraste/
#      saturation/luminosité/seuil noir éventuellement modifiées par la nouvelle
#      étape 2 de recherche tonale (v42) — l'utilisateur ne voyait donc aucune
#      trace des réglages réellement appliqués. Ajout de `saturation`/
#      `brightness` à la ligne d'info existante (contraste/seuil noir déjà
#      affichés).
#
# v42 — 2026-07-18 — safe-modify — `_optimize_cleanup_and_pixel_perfect` :
#      nouvelle étape 2 de recherche locale (descente par coordonnées) sur
#      contraste/saturation/luminosité/seuil noir, après l'étape 1 existante
#      (cleanup_power × pixel_perfect, inchangée sauf `fidelity_weight=1.0`
#      ajouté à ses appels `score_variant` pour cohérence). Suite au constat de
#      l'utilisateur : la proposition 3 "Optimisé" n'apportait plus rien de
#      distinct par rapport à 1/2 (mêmes contraste/saturation/seuil noir
#      hérités tels quels, jamais ré-explorés). Chaque paramètre est testé
#      indépendamment (3 valeurs autour de la valeur courante : ±15%
#      multiplicatif pour contraste/saturation/luminosité, ±10 additif pour le
#      seuil noir, clampé [10,60]) via `score_variant(..., fidelity_weight=1.0)`
#      (dmd_pipeline_quality.py v19) — seule la proposition "Optimisé" active
#      cette dimension, 1/2 restent des baselines simples (décision explicite
#      de l'utilisateur, voir mémoire point 33/34). +12 appels `score_variant`
#      au maximum (3 valeurs × 4 paramètres), chacun avec 1 rendu supplémentaire
#      (référence de fidélité) — voir vérification de performance au changelog
#      correspondant de la mémoire projet. Bug trouvé et corrigé pendant la
#      vérification : `_pipeline_score_variant` (wrapper `DMDConverter.
#      score_variant`) n'acceptait pas encore le nouveau paramètre
#      `fidelity_weight` — `TypeError` immédiate à l'exécution réelle, corrigée
#      en ajoutant le paramètre au wrapper (transmis tel quel).
#
# v41 — 2026-07-18 — safe-modify — `auto_analyze_and_preview` : recadrage sur le
#      contenu visible (`DMDEngine.crop_to_visible_content`, dmd_engine.py v14)
#      appliqué à `img` juste après ouverture, avant tout calcul d'échelle
#      fit/fill et avant l'appel à `resize_will_shrink_text_too_much` (dont le
#      `fit_scale` était calculé sur les dimensions BRUTES du fichier, incluant
#      d'éventuelles marges transparentes — voir changelog v14 de dmd_engine.py
#      pour le détail du bug signalé sur "4th&Inches(Europe).png"). `img` cropé
#      alimente ensuite fit_variants/fill_variants/_best_variant/
#      _optimize_cleanup_and_pixel_perfect/propositions artistiques de façon
#      cohérente. `show_original`/`update_image_info` (panneau "Image Originale")
#      NE sont PAS touchés — continuent d'afficher le fichier source tel quel,
#      volontairement.
#
# v40 — 2026-07-18 — safe-modify — `generate_settings_variants` : cleanup_power
#      des propositions Resize/Fill (#1/#2) remis de 0.6 (jamais testé, juste figé
#      en dur) à 0.0 (rendu brut, non nettoyé). Signalé par l'utilisateur ("les
#      vignettes 1/2 sont baveuses"). Ce fix va de pair avec dmd_pipeline_quality.py
#      v15 (bug plus grave : le nettoyage était silencieusement désactivé partout
#      SAUF dans les vignettes) — les deux corrigés ensemble : sans celui-ci, le
#      fix v15 aurait rendu l'Aperçu DMD Principal et le GIF exporté "baveux" pour
#      #1/#2 au lieu de simplement les rendre cohérents avec la vignette. La
#      proposition #3 "Optimisé" reste la seule à réellement tester cleanup_power
#      (0.0 à 1.0 via `_optimize_cleanup_and_pixel_perfect`, évalué par le score) —
#      #1/#2 sont désormais des baselines Resize/Fill non modifiées, cohérentes
#      avec leur nom.
# v39 — 2026-07-18 — safe-modify — 2 bugs du slider "Luminosité LED" (v38)
#      trouvés et corrigés par l'utilisateur :
#      (1) La valeur était sauvegardée dans config.json à CHAQUE variation
#      pendant le glissement du curseur (trace_add("write") sur
#      led_brightness_var), au lieu d'une seule fois au relâchement — d'où le
#      grand nombre de "💾 Config sauvegardée" observé en console. Le
#      trace_add("write") direct sur la variable est retiré ; chacune des 3
#      instances du widget (`_add_led_brightness_slider`, une par onglet) lie
#      désormais la sauvegarde à `<ButtonRelease-1>` du Scale — le libellé de
#      pourcentage, lui, continue de se mettre à jour en direct sur chaque
#      variation (feedback visuel voulu, seule la sauvegarde disque est
#      différée).
#      (2) Au lancement, le curseur affichait "50%" en texte alors que la
#      poignée était positionnée à la vraie valeur chargée depuis
#      config.json (ex. 100% après une session de test précédente) — le
#      texte du label était codé en dur "50%" à la création plutôt que
#      calculé depuis `led_brightness_var.get()` (la mise à jour ne se
#      faisait qu'au premier déplacement, via le trace_add). Corrigé en
#      initialisant le texte depuis la valeur réelle dès la création du
#      widget.
# v38 — 2026-07-18 — safe-modify — 2 ajouts combinés au rendu LED (Mode DMD),
#      demandés explicitement, dans les 3 onglets concernés (AUTO, MANUEL,
#      TEXTSCROLL) :
#      (1) Icône loupe au survol du canvas de preview (`_add_led_zoom_icon`) —
#      visible uniquement si "Mode DMD / Forcer pixel-perfect" est coché,
#      ouvre une fenêtre séparée (`_open_led_zoom_window`, scale=8) montrant le
#      rendu LED agrandi avec sa PROPRE boucle d'animation qui relit en direct
#      la même liste de frames que l'aperçu normal (`self.preview_frames`/
#      `manual_frames`/`text_frames` selon l'onglet) — reste synchronisée sans
#      dupliquer la génération. Affichage/masquage géré avec un délai de 150ms
#      (`canvas.after`) annulé si la souris entre sur l'icône elle-même : en
#      Tkinter, déplacer la souris du canvas vers un widget enfant placé
#      dessus déclenche quand même <Leave> sur le canvas, sans ce délai
#      l'icône disparaîtrait juste avant de pouvoir cliquer dessus.
#      (2) Slider vertical "Luminosité LED" (`_add_led_brightness_slider`,
#      0-100%, défaut 50%) à côté de chaque canvas — variable partagée
#      `led_brightness_var` (même logique que pixel_perfect_var : propriété du
#      panneau physique simulé, pas un réglage par onglet). Simule la
#      luminosité physique via le nouveau paramètre `brightness` de
#      `DMDEngine.render_led_style` (dmd_engine.py v11) — voir ce changelog
#      pour le détail des formules couleur/glow.
#      Vérifié en réel : test headless (fenêtre de zoom — Toplevel créé/
#      détruit proprement, canvas à la bonne taille ; icône — is_mapped()
#      reste vrai en continu sur 6s d'animation active, contredisant une
#      première capture d'écran PrintWindow qui ne montrait pas l'icône —
#      root-causé comme une limite de l'outil de capture [PrintWindow ne
#      composite pas toujours correctement un widget enfant Tk superposé à un
#      Canvas], pas un bug de l'app : confirmé visible par une capture BitBlt
#      alternative). Slider vérifié visible dans les 3 onglets par capture
#      d'écran classique.
# v37 — 2026-07-18 — safe-modify — 2 demandes combinées de réorganisation des
#      boutons d'action, pour regrouper visuellement chaque action avec le canvas
#      de preview qu'elle affecte plutôt que de les séparer dans 2 panneaux :
#      (1) TEXTSCROLL : "🎬 Générer Preview"/"💾 Exporter GIF" déplacés du panneau
#      gauche (sous les paramètres d'animation) vers le panneau droit, juste sous
#      `text_preview_canvas`. Signalement associé ("la preview ne semble pas
#      centrée") root-causé et corrigé séparément dans
#      `dmd_pipeline_text.render_text_image` (v2) : la position verticale du
#      texte était fixée en dur (y0=8px) au lieu d'être calculée depuis la vraie
#      bbox d'encre de la police/taille choisie — ne semblait centré que par
#      coïncidence à la taille de police par défaut (20). (2) MANUEL :
#      "💾 Exporter GIF" déplacé de la barre d'outils du haut vers juste à côté
#      de "🎬 Prévisualiser" sous `manual_preview_canvas` (nouveau
#      `preview_btn_frame`), même logique de regroupement.
# v36 — 2026-07-18 — safe-modify — Tooltips d'aide au survol, traduits dans les 3
#      langues (demande explicite, scope choisi via question à choix : contrôles
#      non évidents uniquement, pas exhaustif). Nouvelle fonction module-level
#      `add_help_tooltip(widget, lang_key, wraplength=280)` (juste après la classe
#      Tooltip) : résout le texte via `lang_manager.get(lang_key)` AU SURVOL (pas à
#      l'attachement), donc suit automatiquement un changement de langue sans code
#      supplémentaire. Attaché à 11 contrôles jugés non évidents : case "Mode DMD /
#      Forcer pixel-perfect" (les 3 instances AUTO/MANUEL/TEXTSCROLL, même clé
#      `tooltip_pixel_perfect`), "Seuil lettrage (px)", "Vitesse scroll" (AUTO),
#      boutons 📁/🖼️ (AUTO — tooltips existants mais codés en dur en français
#      uniquement, désormais traduits) et "🔓 Réautoriser" (AUTO), "Tolérance",
#      "Boucle", "Easing", "Rebond aux bords" (MANUEL), "Effet couleur"
#      (TEXTSCROLL). 11 nouvelles clés `tooltip_*` ajoutées aux 3 `lang_*.json`.
#      **2 contrôles volontairement exclus après vérification** : "🔒 Verrouiller
#      pour le batch" (AUTO) a déjà un tooltip dynamique différent — settings de la
#      proposition — bind sur `<Enter>`/`<Leave>` du même widget, un second bind
#      statique l'aurait écrasé (Tkinter ne combine pas 2 binds sur la même
#      séquence) ; "Activer cache IA" (PARAMÈTRES) — vérifié non fonctionnel
#      (variable `tk.BooleanVar()` jetable jamais lue nulle part, `clear_cache` ne
#      vide rien de réel), lui ajouter un tooltip aurait promis un comportement qui
#      n'existe pas — signalé mais pas corrigé (hors scope de cette demande).
#      Vérifié en réel : test headless (les 11 clés traduites dans les 3 langues,
#      déclenchement réel `<Enter>`/`<Leave>` sur un widget confirmant l'apparition/
#      disparition de la fenêtre tooltip avec le texte attendu) + capture d'écran.
# v35 — 2026-07-18 — safe-modify — Historique undo/redo incrémental pour l'onglet
#      MANUEL (demande explicite). Ancien mécanisme : `manual_history` était une
#      pile append-only, `manual_undo` faisait `pop()` puis restaurait le nouveau
#      dernier élément — **bug découvert en le remplaçant** : pousser l'état
#      AVANT chaque action puis pop() au undo sautait systématiquement un cran
#      (2 filtres appliqués + 1 undo ramenait direct à l'état initial, pas à
#      l'état après le 1er filtre), et aucun redo n'était possible (l'état
#      "poppé" était perdu). Remplacé par un design pointeur+liste classique :
#      `manual_history_index` marque l'état courant dans `manual_history` (liste
#      qui n'est plus jamais tronquée par un pop) ; nouvelle méthode
#      `_manual_commit_history()` (tronque toute branche "redo" obsolète puis
#      ajoute le nouvel état, appelée en fin d'action plutôt qu'en début —
#      `apply_filter`, `flood_fill`, `magic_eraser`, confirmation de crop) ;
#      `manual_undo`/nouvelle méthode `manual_redo` déplacent simplement le
#      pointeur. Nouveau bouton "↷ Rétablir" dans la barre d'outils MANUEL (à
#      côté de "↶ Annuler"), clé i18n `redo` ajoutée aux 3 `lang_*.json` +
#      `TEXT_MAP`. Info panel MANUEL affiche désormais aussi la position
#      courante ("Historique: N états (position X/N)"). Sliders temps réel
#      (`apply_manual_effect`) volontairement laissés hors historique, comme
#      avant (glissement continu, pas une action unitaire). Vérifié en réel :
#      test headless (`test_undo_redo.py`, off-by-one confirmé corrigé : 1er
#      undo après 2 filtres restaure exactement l'état intermédiaire ; redo x2
#      retrouve les 2 états suivants à l'identique ; nouvelle action après un
#      undo écrase bien l'ancienne branche redo ; flood_fill/magic_eraser
#      committent chacun exactement 1 état) + capture d'écran (bouton visible,
#      image correctement restaurée après un undo, compteur de position exact).
# v34 — 2026-07-18 — safe-modify — 2 changements combinés :
#      (1) Les 3 appels à `DMDEngine.render_led_style` (Aperçu DMD Principal,
#      MANUEL, TEXTSCROLL) ne fixent plus `led_ratio=0.72` explicitement — ils
#      héritent désormais du nouveau défaut 0.525 (voir dmd_engine.py v9,
#      corrigé suite à un signalement utilisateur sur du matériel réel : specs
#      HUB75 P4 confirmées, LED 2121 = ratio physique réel 2.1/4.0 = 0.525).
#      (2) Vignettes "Propositions IA" agrandies de ×2 (256×64) à ×3 (384×96),
#      demandé explicitement — `proposal_canvases` (création), les 2 endroits
#      qui redimensionnent l'image finale vers le canvas
#      (`auto_analyze_and_preview`, `regenerate_artistic_proposal`) et les
#      `wraplength` associés (tooltip + case verrouillage) mis à jour en
#      cohérence. Point de vigilance noté en commentaire : la grille 3×2 est
#      désormais plus large, à revérifier visuellement si ça repousse la
#      fenêtre au-delà de l'écran (raison d'être du fix v20 à l'origine).
# v33 — 2026-07-18 — safe-modify — Branchement des 5 "Contrôles Avancés" de
#      l'onglet MANUEL (`manual_easing`, `manual_delay_start`, `manual_reverse`,
#      `manual_bounce_edges`, `manual_opacity`), créés depuis longtemps mais
#      jamais lus par `generate_manual_animation` (repéré et ajouté au TODO en
#      v28, implémentation demandée explicitement ensuite). Choix d'implémentation
#      : tous génériques (agissent en post-traitement sur la liste de frames déjà
#      générée, quel que soit le type d'animation parmi les 18 disponibles) plutôt
#      que spécifiques à certains types d'animation :
#      - `_apply_easing` (nouvelle méthode) : ré-échantillonne l'ordre de lecture
#        des frames selon une courbe de easing (linear/ease-in/ease-out/
#        ease-in-out/bounce, formule bounceOut de Robert Penner pour "bounce") —
#        même nombre de frames et durée, seule la vitesse relative varie.
#      - `_apply_bounce_edges` : replie la séquence en aller-retour (même
#        principe que le mode boucle "ping-pong" existant) puis la
#        ré-échantillonne pour tenir dans le nombre de frames d'origine — la
#        durée ne change pas, le mouvement va-et-vient au lieu de s'arrêter/
#        boucler sec en bout de course.
#      - `manual_reverse` : simple inversion de l'ordre des frames.
#      - `manual_delay_start` : frames statiques (1ère frame répétée) ajoutées
#        UNE SEULE FOIS en tête de la séquence finale (après boucle), pas à
#        chaque répétition.
#      - `_apply_opacity` : fondu global vers le noir, appliqué en tout dernier
#        sur la séquence finale.
#      Ordre d'application : reverse → bounce_edges → easing → boucle (code
#      existant inchangé) → délai début → opacité. Vérifié en réel (headless,
#      test_advanced_controls.py) : chaque contrôle testé isolément contre une
#      séquence de référence (baseline tout désactivé) — reverse (dernière frame
#      = 1ère de la baseline), délai (nombre exact de frames statiques ajoutées),
#      opacité 0.3 → luminosité moyenne ramenée à 0.30x, bounce_edges et les 4
#      easings (frames effectivement réordonnées vs baseline, nombre de frames
#      inchangé dans tous les cas).
# v32 — 2026-07-18 — safe-modify — `apply_theme` : l'onglet AIDE suit désormais le
#      thème choisi (Sombre/Clair, onglet PARAMÈTRES) au lieu de rester figé aux
#      couleurs Tk par défaut (blanc/noir, comme les autres Text de l'app —
#      limitation notée en v31). `help_text` est explicitement recoloré
#      (bg="#404040"/fg="white" en sombre, bg="white"/fg="black" en clair,
#      cohérent avec les couleurs déjà utilisées par option_add pour
#      Entry/Listbox) à CHAQUE appel de `apply_theme`, PUIS le contenu est
#      re-rendu (`_refresh_help_tab_content`) — pas juste recoloré : les accents
#      Markdown (liens, citations, tableaux) sont calculés par
#      `RecalBoxDMD_md_renderer._derive_markdown_colors` à partir de bg/fg au
#      moment du rendu, donc un simple `.configure()` sans nouveau rendu aurait
#      laissé les couleurs d'accent de l'ancien thème. Demandé explicitement par
#      l'utilisateur juste après l'ajout de l'onglet (v31).
# v31 — 2026-07-18 — safe-modify — Nouvel onglet AIDE (demande explicite), en 6e
#      position dans le Notebook. Affiche le lisezmoi*.md correspondant à la
#      langue actuellement sélectionnée dans PARAMÈTRES (fr → lisezmoi.md,
#      en → lisezmoi_en.md, es → lisezmoi_es.md, tous générés lors d'une session
#      précédente), rendu en Markdown riche (titres, gras/italique, tableaux,
#      citations, liens du menu vers les sections) via
#      `RecalBoxDMD_md_renderer.render_markdown_in_text` — module réutilisé TEL
#      QUEL (copie conforme, aucune modification) depuis
#      `RecalBox_DMD/tools/RecalBoxDMD_md_renderer.py`, générique et sans
#      dépendance au reste de ce projet-là, comme demandé. Nouvelle dépendance :
#      `markdown` (déjà installée dans cet environnement — vérifié). Ajouts :
#      `setup_help_tab` (toolbar titre + bouton "Ouvrir dans le navigateur" +
#      Text scrollable), `_help_readme_path` (résout le nom de fichier selon
#      `self.lang_var`), `_refresh_help_tab_content` (charge + rend le fichier,
#      appelée depuis `setup_help_tab` ET depuis `apply_translations` — donc
#      recharge automatiquement dans la bonne langue à chaque changement via
#      l'onglet PARAMÈTRES, `change_language` passant déjà par
#      `apply_translations`), `_help_scroll_to_anchor` (navigation par ancre sur
#      clic d'un lien du menu, calqué sur l'implémentation de référence
#      `RecalBoxDMD_GUI.py`), `_open_help_in_browser`. Clés i18n `tab_help`/
#      `help_open_browser_btn` ajoutées aux 3 `lang_*.json`. `tab_labels` dans
#      `apply_translations` étendu à 6 entrées (le padding par mesure pixel du
#      libellé le plus long, v24, s'applique automatiquement au nouvel onglet).
#      Widget `help_text` volontairement laissé aux couleurs Tk par défaut
#      (blanc/noir), comme les panneaux "Informations Image" existants — le
#      renderer dérive sa palette d'accents (liens, citations, tableaux) depuis
#      les couleurs réelles bg/fg du widget, donc reste lisible sans dépendre du
#      thème sombre/clair de l'app (qui ne recolore pas rétroactivement les
#      widgets Text créés avant `apply_theme()`, limitation préexistante).
# v30 — 2026-07-18 — safe-modify — Portage du checkbox "Mode DMD / Forcer
#      pixel-perfect" + de l'aperçu LED animé vers l'onglet TEXTSCROLL (demandé
#      explicitement, "vérifie pour les fix à appliquer"). Audit préalable des 3
#      correctifs déjà appliqués à MANUEL (v28) : (1) canvas — text_preview_canvas
#      était déjà en 512×128 dès l'origine, aucun bug à corriger ici. (2) bug de
#      transparence RGBA — ne s'applique pas : dmd_pipeline_text.render_text_image
#      crée toujours une image RGB directement (Image.new("RGB", ...)), jamais de
#      chargement de PNG source, donc aucun canal alpha en jeu. (3) anti-écrêtage
#      des sliders — ne s'applique pas : TEXTSCROLL n'a aucun slider luminosité/
#      contraste/saturation (pas de mécanisme ImageEnhance), donc rien à auditer.
#      Seul le portage LED avait donc un sens ici. Nouveau checkbox dans le cadre
#      "Animation" (row3, sous FPS/Vitesse/Durée/Auto-ajuster), réutilise
#      self.pixel_perfect_var (partagée avec AUTO et MANUEL). animate_text_preview
#      applique DMDEngine.render_led_style (scale=4) si la case est cochée, sinon
#      resize NEAREST classique inchangé — vérifié que toutes les fonctions de
#      génération d'animation texte (ManualEffects.scroll_effect/fade_effect,
#      TextAnimations.*) produisent bien des frames 128×32 (via _centered_canvas
#      ou Image.new("RGB", (128, 32), ...) direct), condition nécessaire pour que
#      render_led_style s'applique correctement. Vérifié en réel (headless,
#      test_textscroll_led.py) : 45 frames générées à 128×32, rendu LED et rendu
#      classique tous deux à 512×128 (coïncide avec text_preview_canvas).
#
# v29 — 2026-07-18 — safe-modify — Ajout de la case à cocher "Mode DMD / Forcer
#      pixel-perfect" dans l'onglet MANUEL, cadre "Outils Dessin" (nouvelle ligne
#      draw_row3, après la ligne Tolérance/Fond noir) — d'abord placée dans le
#      panneau "Aperçu Animation DMD" puis déplacée ici à la demande explicite de
#      l'utilisateur. La case elle-même était absente côté MANUEL alors que
#      self.pixel_perfect_var (créée dans setup_auto_tab, qui s'exécute avant
#      setup_manual_tab) était déjà LUE par generate_manual_animation et
#      animate_manual_preview (v28) — pas de nouvelle variable, juste le widget
#      manquant réutilisant la variable partagée. Cocher la case dans un onglet la
#      coche donc aussi dans l'autre (même tk.BooleanVar).
# v28 — 2026-07-17 — safe-modify — Portage de 3 acquis de l'onglet AUTO vers
#      l'onglet MANUEL, demandé explicitement par l'utilisateur ("se servant de ce
#      qui a été mis en place dans AUTO") :
#      1. Bug préexistant corrigé : manual_preview_canvas faisait 512×80 alors que
#         animate_manual_preview centrait déjà son rendu pour du 512×128
#         (create_image(256, 64, ...)) — les 24px du haut et du bas de chaque
#         frame étaient rognés par la fenêtre du canvas. Canvas agrandi à 128px de
#         haut, comme canvas_dmd_main (AUTO).
#      2. Aperçu LED animé porté dans animate_manual_preview : même bloc
#         conditionnel qu'animate_preview (AUTO), piloté par le même
#         self.pixel_perfect_var déjà partagé entre les 2 onglets — cohérence
#         immédiate, la case "DMD mode" contrôle le même comportement partout.
#      3. Bug de transparence RGBA (même famille que v11/v13 de
#         dmd_pipeline_quality.py) trouvé à 3 endroits distincts dans l'onglet
#         MANUEL — tous utilisaient `Image.open(...).convert("RGB")` au lieu de
#         `DMDEngine.ensure_rgb_on_black(...)`, révélant les pixels RVB bruts
#         sous la transparence (souvent blancs) : `load_manual_image`,
#         `load_multiple_manual_images`, `load_from_auto`. Reproduit sur le
#         logo "A.G.E." : 24875 pixels blancs (35% de l'image) avant fix, contre
#         18 après. Tous corrigés.
#      Audité mais PAS corrigé (décision explicite de l'utilisateur, contrôle
#      manuel total voulu) : le même mécanisme d'écrêtage des hautes lumières que
#      la protection anti-clipping d'optimize_for_dmd (dmd_engine.py v8) est
#      reproductible sur les sliders temps réel de MANUEL (apply_manual_effect,
#      ImageEnhance.Contrast/.Color) — testé, ×153 pixels blancs à
#      contraste=1.8/saturation=1.6 — mais l'utilisateur a choisi de ne pas
#      limiter l'effet visuel des sliders manuels.
# v27 — 2026-07-17 — safe-modify — 2 demandes combinées : (1) nouveau réglage
#      "Seuil lettrage (px)" (Paramètres Globaux, après la case DMD mode,
#      Spinbox 6-11, défaut 8) — pilote désormais min_letter_px de
#      resize_will_shrink_text_too_much au lieu de la valeur fixe codée en dur.
#      (2) Fusion des demandes "anime la preview LED" + "remplace l'aperçu
#      classique par le LED quand DMD mode est coché, retire le bouton dédié" :
#      le bouton "💡 Aperçu LED" et sa fenêtre popup statique (show_led_preview)
#      sont supprimés ; animate_preview applique désormais DMDEngine.
#      render_led_style à chaque frame directement dans Aperçu DMD Principal
#      quand "Mode DMD / Forcer pixel-perfect" est coché (scale=4, correspond
#      exactement à la taille existante du canvas 512×128 — pas de redimension-
#      nement de widget nécessaire). Mesuré à 4-8ms/frame, largement sous le
#      budget d'une animation 10fps — l'inquiétude de performance notée au
#      changelog v7 de dmd_engine.py ne se vérifie pas en pratique.
# v26 — 2026-07-17 — safe-modify — auto_analyze_and_preview : remplace l'appel à
#      text_legibility_collapsed (composantes connexes, abandonné après 8
#      tentatives infructueuses — voir dmd_pipeline_quality.py v14) par
#      resize_will_shrink_text_too_much (hauteur de lettre projetée après resize,
#      calcul de fit_scale = min(128/w, 32/h) ajouté ici). Approche proposée par
#      l'utilisateur, validée empiriquement : sépare parfaitement les 7 logos
#      réels du corpus de test, y compris les 2 cas qui faisaient échouer toutes
#      les tentatives précédentes.
# v25 — 2026-07-17 — safe-modify — auto_analyze_and_preview : si l'image source
#      contient probablement du texte dont les lettres ont fusionné en Resize/fit
#      (détection sans OCR, voir dmd_pipeline_quality.text_legibility_collapsed
#      v10), Fill/scroll est désormais forcé comme base de la proposition
#      "Optimisé" indépendamment du score brut — demandé par l'utilisateur après
#      désaccord argumenté avec l'analyse précédente (logo très détaillé où Resize
#      restait choisi malgré un texte illisible). Statut affiché à l'utilisateur
#      annoté "(texte illisible en Resize → Fill forcé)" quand l'override
#      s'applique, pour rester transparent sur la décision.
# v24 — 2026-07-17 — safe-modify — apply_translations : le centrage des libellés
#      d'onglets (v22) padait par NOMBRE DE CARACTÈRES (str.center), ce qui suppose
#      une police à chasse fixe — la police par défaut Tk (proportionnelle) rend donc
#      des largeurs en pixels toujours différentes malgré un nombre de caractères
#      identique ("TEXTSCROLL" bien plus large que "AUTO" même paddés à 10 caractères
#      chacun), d'où le bord en dents de scie signalé à nouveau par l'utilisateur.
#      Remplacé par un padding calculé en PIXELS réels via tkfont.measure() : mesure
#      la largeur de chaque libellé avec la police par défaut, calcule le nombre
#      d'espaces (mesurés eux aussi) nécessaires de chaque côté pour approcher la
#      largeur du plus long. Résultat pixel-proche au lieu de caractère-proche.
# v23 — 2026-07-17 — safe-modify — Bouton "💡 Aperçu LED" sous le cadre "Aperçu DMD
#      Principal" (onglet AUTO) : ouvre une fenêtre séparée montrant la frame
#      actuellement affichée rendue en simulation LED physique (DMDEngine.
#      render_led_style, dmd_engine.py v7) — points ronds espacés par un bezel sombre
#      au lieu de simples carrés agrandis. Aperçu statique à la demande (étape 1
#      d'une demande utilisateur en 2 étapes) ; l'animation continue reste en rendu
#      "carrés" classique pour l'instant.
# v22 — 2026-07-17 — safe-modify — apply_translations : les 5 libellés d'onglets sont
#      maintenant centrés (str.center) sur la longueur du plus long des 5 (calculée
#      dynamiquement à chaque application des traductions, pas de valeur en dur — reste
#      correct quelle que soit la langue active). Demandé suite au passage des onglets
#      en position latérale (v21) : en pile verticale, les libellés de longueurs
#      différentes ("AUTO" vs "TEXTSCROLL") donnaient un bord droit en dents de scie.
# v21 — 2026-07-17 — safe-modify — Onglets latéraux + hauteur dynamique du Notebook,
#      pour garantir une marge de hauteur au-delà du correctif ponctuel v20 :
#      1. Barre d'onglets déplacée en position latérale gauche (tabposition="wn",
#         style TNotebook) dans les 2 branches de thème d'apply_theme (la branche
#         claire n'avait jusqu'ici aucune config TNotebook). Libère la hauteur
#         qu'occupait la barre horizontale (~30-40px) au profit du contenu, contre
#         une largeur supplémentaire à gauche pour la colonne d'onglets.
#      2. La hauteur fixe du Notebook (height=910, "Hauteur max" codé en dur)
#         remplacée par un calcul dynamique basé sur winfo_screenheight(), stocké
#         dans self.notebook_height — objectif : ne plus dépendre d'une valeur
#         calibrée sur l'écran de dev, qui recréerait silencieusement le bug de
#         coupure v20 sur un écran plus petit.
# v20 — 2026-07-17 — safe-modify — 3 demandes suite aux retours utilisateur sur
#      l'onglet AUTO :
#      1. Boutons "📁 Dossier"/"🖼️ Images" (toolbar cadre Images) passés en icône
#         seule (texte retiré), tooltip statique ajouté pour garder la
#         découvrabilité.
#      2. La fenêtre dépassait 1900px de large : la grille de propositions IA
#         (5 puis 6 colonnes sur une seule rangée) en était la cause principale,
#         pas les Paramètres Globaux. Repli sur une grille 3 colonnes × 2 rangées
#         (rangée 0 = 3 propositions de base, rangée 1 = propositions
#         artistiques). Pour éviter que cette 2e rangée ne soit coupée en bas
#         d'écran (fenêtre déjà à hauteur d'écran max ~1083px), réduction
#         combinée : Paramètres Globaux fusionnés sur une seule ligne (au lieu de
#         2 lignes + case à cocher séparée), canvas Image Originale 200→130px,
#         canvas Aperçu DMD Principal 5x→4x (640×160→512×128), canvas de chaque
#         proposition 2.5x→2x (320×80→256×64, économise aussi en largeur).
#         Vérifié en réel : fenêtre 1374×1083 (contre >1900 large avant), 2
#         rangées de propositions entièrement visibles sans coupure.
#      3. 3e proposition artistique ajoutée (6 propositions au total) : les 2
#         effets curatés (safe/dynamic, selon densité de contours + coloration,
#         _choose_artistic_effects) restent inchangés, le 3e est pioché au hasard
#         dans le reste du pool (_pick_random_artistic_effect, exclut les 2 déjà
#         choisis) pour une option exploratoire. Toutes les boucles/index
#         supposant 5 propositions généralisés (range(6), len(self.proposals)).
# v19 — 2026-07-17 — safe-modify — Suite au test réel de l'utilisateur (dépôt du
#      dossier "D:\clear logo recalbox\systems", des .bmp organisés par
#      sous-dossier) : le glisser-déposer n'ajoutait 0 image, pas à cause du filtre
#      d'extension (.bmp déjà supporté) mais parce que la case "Récursif" était
#      décochée par défaut et qu'un scan non récursif d'un dossier ne contenant que
#      des sous-dossiers (aucun fichier image à la racine) ne trouve donc rien.
#      Confirmé avec l'utilisateur : avec un chargement additif + suppression
#      individuelle possible (v16), la case "Récursif" désélectionnable n'a plus
#      d'utilité — le scan de dossier est désormais TOUJOURS récursif
#      (_scan_folder_for_images). Case + self.recursive_var supprimées, ainsi que
#      la clé i18n orpheline "recursive" (TEXT_MAP + 3 lang_*.json). Panneau
#      "Source:" séparé supprimé ; les boutons "📁 Dossier"/"🖼️ Images" sont
#      déplacés dans la barre d'outils du cadre "Images" (à côté de ✓/✗/⇄/
#      Réautoriser/Vider), qui concentre maintenant toutes les actions de gestion
#      de la liste.
# v18 — 2026-07-17 — safe-modify — Ajout d'un texte indicatif ("📂 Glisser-déposer un
#      dossier ou des images ici") superposé au cadre Images quand la liste est vide,
#      pour signaler que le glisser-déposer fonctionne sur toute la fenêtre (demandé
#      par l'utilisateur après clarification que le drop cible bien la zone Treeview).
# v17 — 2026-07-17 — safe-modify — apply_theme : ajout du style ttk.Treeview (dark et
#      clair), absent jusqu'ici. Bug trouvé lors du test visuel réel du nouveau
#      image_tree (v16) : la liste s'affichait comme un bloc blanc sans texte lisible
#      en thème sombre, car le thème appliquait `option_add("*Listbox*...")` qui ne
#      concerne que l'ancien widget tk.Listbox, jamais étendu à ttk.Treeview.
# v16 — 2026-07-17 — safe-modify — Refonte de la gestion des fichiers sources (onglet
#      AUTO), à la demande de l'utilisateur suite à l'analyse des boutons Dossier/
#      Images/Récursif :
#      - Nouvelle dépendance tkinterdnd2 pour le glisser-déposer natif (racine Tk
#        remplacée par TkinterDnD.Tk()).
#      - self.image_listbox (tk.Listbox) remplacée par self.image_tree (ttk.Treeview)
#        : liste plate (pas d'arborescence dépliable) affichant le chemin relatif au
#        dossier racine chargé, éditable (suppression via touche Suppr/menu
#        contextuel).
#      - Chargement additif : select_folder/select_images/le nouveau handler de drop
#        ajoutent à self.images (dédoublonnés) au lieu de le remplacer. Nouveau
#        bouton "Vider la liste".
#      - Bug corrigé : process_images calculait
#        input_dir = Path(self.images[0]).parent.parent (remonte toujours de 2
#        niveaux), cassant la reconstruction d'arborescence en sortie dès qu'un
#        dossier non récursif ou des fichiers individuels étaient chargés. Remplacé
#        par self.source_root_dir, positionné explicitement au chargement d'un
#        dossier (jamais par la sélection de fichiers individuels), avec repli sur
#        Path(self.images[0]).parent (un seul niveau) si non défini.
# v15 — 2026-07-17 — safe-modify — Renommage du label "Forcer pixel-perfect" en
#      "Mode DMD / Forcer pixel-perfect". Clé TEXT_MAP (dmd_ui_constants.py) et
#      traductions (3 lang_*.json, clé pixel_perfect) mises à jour en cohérence pour
#      que le mécanisme de retraduction au changement de langue continue de
#      fonctionner (même bug de correspondance texte-exact que le header applicatif,
#      voir v6 plus haut).
# v14 — 2026-07-17 — safe-modify — Suppression de l'option "Mode IA" (rapide/précis) à
#      la demande de l'utilisateur : le fix de performance de max_frames (voir
#      dmd_pipeline_quality.py v7) a rendu l'écart de vitesse entre les 2 modes
#      négligeable (analyse sub-seconde dans tous les cas), l'option n'avait plus
#      d'intérêt réel. generate_settings_variants utilise désormais systématiquement
#      la grille "précis" (3 contrastes × 4 seuils noir). UI (label + Combobox) et
#      ia_mode_var supprimés. Clés i18n orphelines ia_mode/rapide/precis supprimées
#      des 3 lang_*.json (jamais consommées via lang_manager.get — le label était
#      codé en dur, incohérence déjà notée dans TODO_optimisation.md).
# v13 — 2026-07-17 — safe-modify — scroll_speed_var passe de IntVar à DoubleVar et le
#      Spinbox associé accepte désormais 0.1 à 10 par pas de 0.1 (au lieu de 1 à 10 par
#      pas entier) — permet un scroll plus lent que 1px/frame. Voir dmd_engine.py v5
#      pour le support correspondant côté moteur (répétition de frame, pas de notion
#      de sous-pixel sur une grille de LED).
# v12 — 2026-07-17 — safe-modify — Retours utilisateur après tests manuels sur le mode
#      Auto/IA (en cours, plusieurs correctifs dans cette version) :
#      1. Vignettes de proposition rognées : le canvas widget faisait 220px de large
#         mais l'image dessinée dedans 256px (`canvas.resize((256,64))`) → débordement
#         rogné par Tkinter sur les bords, empêchant de juger le rendu sans cliquer.
#         Canvas agrandi et aligné exactement sur la taille de l'image affichée.
# v11 — 2026-07-16 — safe-modify — Propositions artistiques 4-5 (mode Auto/IA) :
#      auto_analyze_and_preview génère maintenant 2 propositions supplémentaires en
#      appliquant un effet du mode manuel (ManualEffects) sur la version "fit" de la
#      proposition retenue. Le choix des 2 effets (1 "sûr" + 1 "dynamique") se base
#      sur les caractéristiques de l'image (densité de contours, coloration,
#      occupation) via dmd_pipeline_quality.analyze_characteristics. Ces propositions
#      n'ont pas de score numérique (pas comparables aux critères occupation/
#      lisibilité des 3 premières) — affichage adapté en conséquence.
# v10 — 2026-07-16 — safe-modify — Refonte du mode Auto/IA, à la demande explicite de
#      l'utilisateur (le scoring existant favorisait systématiquement le mode resize/
#      fit, aucune proposition artistique, pixel_perfect cassé — voir dmd_engine.py v3
#      et dmd_pipeline_quality.py v5). generate_settings_variants génère maintenant des
#      variantes fit et fill séparément (au lieu d'un pool mélangé faussant le
#      classement). auto_analyze_and_preview produit désormais 3 propositions :
#      #1 meilleur resize, #2 meilleur fill/scroll (choisis via score_variant :
#      occupation + lisibilité), #3 variante nettoyage +/- fort de la proposition
#      retenue, essayant aussi pixel_perfect et ne le gardant que s'il améliore le
#      score. Les propositions artistiques (effets du mode manuel) sont prévues pour
#      une passe suivante — non incluses ici. _pipeline_render_dmd_frame lit désormais
#      settings["_pixel_perfect"] en priorité (utilisé par la proposition #3) avant de
#      retomber sur la case à cocher globale pixel_perfect_var, pour ne pas affecter
#      les autres rendus.
# v9 — 2026-07-15 — safe-modify — bloc `if __name__ == "__main__"` : une erreur fatale
#      au lancement (avant même que l'UI/le Logger en mémoire soit exploitable par
#      l'utilisateur) n'était visible que dans la console et perdue à la fermeture.
#      Écrit maintenant systématiquement un fichier crash_YYYYMMDD_HHMMSS.log dans le
#      dossier de config utilisateur (même dossier que config.json), en plus du print
#      console existant (conservé pour compatibilité).
# v8 — 2026-07-15 — safe-modify — generate_morphing_animation : les dimensions cible
#      (scale/new_w/new_h/x/y) sont constantes pour toute la fonction (target_size ne
#      change jamais) — hissées hors des boucles au lieu d'être recalculées à chaque
#      frame. La frame de pause finale (identique à chaque itération de
#      `range(int(fps*0.5))`) n'est plus redimensionnée/collée qu'une seule fois, les
#      frames de pause partagent la même image (pattern déjà utilisé ailleurs dans
#      dmd_engine.py pour le mode "static": `frames = [canvas] * num_frames`).
# v7 — 2026-07-15 — safe-modify — process_images : remplacement du
#      print("DEBUG: process_images démarré") oublié en dur par logger.info(...), pour
#      cohérence avec le reste du logging de l'app (visible dans l'onglet DEBUG / export
#      de logs, contrairement à un print qui part dans la console).
# v6 — 2026-07-15 — safe-modify — Header applicatif (setup_ui) : la double regex
#      imbriquée pour normaliser le numéro de version utilisait un pattern
#      double-échappé (r"v\\d+\\.\\d+...") qui ne matche jamais rien (no-op silencieux) —
#      remplacée par le pattern correct à simple échappement (identique à celui déjà
#      utilisé et fonctionnel dans update_title/apply_version). TEXT_MAP ("DMD Converter
#      v2.0") et les 3 fichiers lang_*.json (app_header "v2.7.3") étaient également
#      désynchronisés de APP_VERSION="2.7.4", empêchant la ré-application de la
#      traduction du header au changement de langue — resynchronisés.
# v5 — 2026-07-15 — safe-modify — Suppression du second bloc d'import mort qui
#      réimportait/réaffectait TextEffects et TextAnimations sans raison (rien entre les
#      deux blocs ne les écrasait). Consolidation des 3 imports locaux de
#      dmd_gif_exporter (dans process_images, manual_export, export_text_gif) en un seul
#      import en tête de fichier.
# v4 — 2026-07-15 — safe-modify — process_images : suppression du second appel
#      redondant (et incorrect) à DMDEngine.create_animation_frames sur l'image BRUTE
#      re-ouverte (juste pour le nommage du fichier). En mode direction "auto", ce
#      recalcul utilisait les dimensions de l'image AVANT redimensionnement DMD au lieu
#      de celles utilisées pour le rendu réel, pouvant donner un nom de fichier
#      "_horizontal"/"_vertical" ne correspondant pas au rendu effectif (parfois
#      "static"). render_dmd_frame (dmd_pipeline_quality.py) expose maintenant la
#      direction réellement utilisée via le paramètre return_direction=True.
# v3 — 2026-07-15 — safe-modify — flood_fill : remplacement du BFS avec queue.pop(0)
#      (O(n) par pop, donc BFS potentiellement O(n²)) par un flood fill vectorisé numpy
#      (masque candidat + dilatation itérative), résultat identique. magic_eraser :
#      double boucle Python remplacée par un calcul de diff couleur vectorisé numpy.
# v2 — 2026-07-15 — safe-modify — Suppression du code mort : méthodes render_dmd_frame
#      et render_text_image définies dans la classe DMDConverter mais shadowées par les
#      monkey-patchs de fin de fichier (dmd_converter.py:~4170+), donc jamais exécutées.
# v1 — 2026-07-15 — safe-modify — Version de base (backup original conservé dans
#      _backups/dmd_converter_2026-07-15_19-10-07.bak)
# ============================================

import os
import sys
import subprocess
import shutil
import webbrowser
from pathlib import Path
# concurrent.futures.ProcessPoolExecutor (2026-08-06, Tier 2 plan perf batch)
# -- parallélisation ACROSS images du traitement par lot (onglet AUTO), voir
# process_one_image()/process_images(). Pas de threading.Thread ici (déjà
# utilisé partout ailleurs dans ce fichier pour sortir UNE opération
# bloquante du thread Tk principal) : un pool de PROCESSUS, pas de threads,
# pour contourner le GIL sur un pipeline qui alterne beaucoup de calcul PIL/
# numpy court et d'overhead Python entre chaque itération (grille de
# variantes, frames de scroll) -- profil où un pool de threads n'apporterait
# qu'un gain limité.
from concurrent.futures import ProcessPoolExecutor, as_completed
from PIL import (
    Image,
    ImageEnhance,
    ImageFilter,
    ImageDraw,
    ImageOps,
    ImageChops,
    ImageFont,
    ImageTk,
)

# (ADAPTIVE_RESAMPLING supprimé: export GIF palette désormais externalisé via dmd_gif_exporter)

import re
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, colorchooser, font as tkfont
from tkinter import Canvas, Text, Scrollbar
from tkinterdnd2 import TkinterDnD, DND_FILES
import threading
import numpy as np
from collections import Counter
import time
import datetime
import math
import random
import json
import hashlib

# ============================================================================
# TOOLTIP UTILS
# ============================================================================


class Tooltip:
    """Affiche une petite bulle d'aide pour un widget sur survol."""

    def __init__(self, widget, text="", wraplength=220):
        self.widget = widget
        self.text = text
        self.wraplength = wraplength
        self.tipwindow = None

    def showtip(self, text=None):
        if text:
            self.text = text
        if self.tipwindow or not self.text:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10

        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            wraplength=self.wraplength,
            font=("Arial", 8),
        )
        label.pack(ipadx=4, ipady=2)

    def hidetip(self):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


def add_help_tooltip(widget, lang_key, wraplength=280):
    """Attache un tooltip d'aide traduit à un widget. Le texte est résolu au
    survol (pas à l'attachement) via lang_manager.get(lang_key), donc suit
    automatiquement un changement de langue sans code supplémentaire — contrairement
    aux tooltips dynamiques des propositions IA (texte poussé explicitement à
    chaque rafraîchissement), celui-ci est pour un libellé fixe traduit."""
    tip = Tooltip(widget, wraplength=wraplength)
    widget.bind("<Enter>", lambda e: tip.showtip(lang_manager.get(lang_key, lang_key)))
    widget.bind("<Leave>", lambda e: tip.hidetip())


# ============================================================================
# LOGGER
# ============================================================================


class Logger:
    """Système de logging avec callbacks pour affichage temps réel"""

    def __init__(self):
        self.logs = []
        self.callbacks = []

    def log(self, level, message):
        """Enregistre un log avec timestamp"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = {"time": timestamp, "level": level, "message": message}
        self.logs.append(log_entry)

        # Notifier tous les callbacks
        for callback in self.callbacks:
            callback(log_entry)

    def info(self, msg):
        self.log("INFO", msg)

    def warning(self, msg):
        self.log("WARNING", msg)

    def error(self, msg):
        self.log("ERROR", msg)

    def debug(self, msg):
        self.log("DEBUG", msg)


# Instance globale du logger
logger = Logger()

# ============================================================================
# GESTIONNAIRE DE CONFIGURATION (METTRE EN PREMIER)
# ============================================================================


class ConfigManager:
    """Sauvegarde et charge tous les paramètres"""

    def __init__(self):
        # Détecter si on est dans un exe PyInstaller
        if getattr(sys, "frozen", False):
            # Mode exe (onedir/onefile)
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                # PyInstaller onefile extrait dans sys._MEIPASS
                internal_dir = Path(meipass) / "_internal"
                base_path = internal_dir if internal_dir.exists() else Path(meipass)
            else:
                # Cas fallback (si _MEIPASS n'existe pas)
                exe_dir = Path(sys.executable).parent
                internal_dir = exe_dir / "_internal"
                base_path = internal_dir if internal_dir.exists() else exe_dir
        else:
            # Mode script
            base_path = Path(__file__).parent

        # config embarquée (onefile: sys._MEIPASS/_internal)
        self.default_config_file = base_path / "config.json"

        # config persistante (user)
        appdata = os.environ.get("APPDATA")
        if appdata:
            self.user_dir = Path(appdata) / "DMD_GIF_Creator"
        else:
            self.user_dir = Path.home() / "AppData" / "Roaming" / "DMD_GIF_Creator"

        self.config_file = self.user_dir / "config.json"
        self._migrate_old_config_folder()
        print(f"Chemin config (user): {self.config_file}")

        # Anti “trop d’écritures” pendant que l’utilisateur manipule des Spinbox/Combobox
        self._last_save_ts = 0.0
        self._save_min_interval_s = 0.25

        self.config = self.load_config()

    def _migrate_old_config_folder(self):
        """Copie l'ancien config.json (dossier "DMD_GIF_Converter", nom
        d'avant le renommage de l'app en "DMD GIF Creator") vers le nouveau
        dossier "DMD_GIF_Creator" au premier lancement post-renommage — sans
        quoi les réglages déjà enregistrés (thème, langue, luminosité LED...)
        repartiraient silencieusement à zéro. Ne s'exécute que si le NOUVEAU
        dossier n'existe pas encore ET que l'ancien contient un config.json
        (sinon no-op, rejouable sans effet de bord aux lancements suivants).
        Ne touche jamais à l'ancien dossier (pas de suppression/déplacement)."""
        if self.config_file.exists():
            return
        old_config_file = self.user_dir.parent / "DMD_GIF_Converter" / "config.json"
        if not old_config_file.exists():
            return
        try:
            self.user_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old_config_file, self.config_file)
            print(f"Config migrée depuis l'ancien dossier: {old_config_file} -> {self.config_file}")
        except Exception as e:
            print(f"Migration config échouée (non bloquant): {e}")

    def load_config(self):
        """Charge la configuration"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                print(f"Config chargée: {self.config_file}")
                print(f"   Contenu: {data}")
                return data
            except Exception as e:
                print(f"Erreur load config: {e}")
                return {}
        else:
            print(f"Config introuvable: {self.config_file}")
            return {}

    def save_config(self):
        """Sauvegarde la configuration"""
        try:
            # Assure que le dossier user existe (sinon open() échoue silencieusement côté UI)
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            print(f"💾 Config sauvegardée: {self.config_file}")
        except Exception as e:
            print(f"❌ Erreur save config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def _maybe_save(self) -> None:
        """Autosauvegarde avec debounce minimal."""
        try:
            now = time.time()
            if now - self._last_save_ts >= self._save_min_interval_s:
                self.save_config()
                self._last_save_ts = now
        except Exception as e:
            print(f"❌ Erreur autosave: {e}")

    def set(self, key, value) -> None:
        self.config[key] = value
        # Important: beaucoup de callbacks UI utilisent set() mais ne callent pas save()
        # → on autosauvegarde pour que config.json soit réellement persisté.
        self._maybe_save()

    def save(self):
        """Sauvegarde explicite (pour actions “importantes” si besoin)"""
        self.save_config()
        self._last_save_ts = time.time()


config_manager = ConfigManager()

# ============================================================================
# SYSTÈME MULTILINGUE (APRÈS ConfigManager)
# ============================================================================


class LanguageManager:
    """Gestionnaire de langues avec fichiers JSON"""

    def __init__(self):
        self.current_lang = "fr"
        self.translations = {}
        self.load_languages()
        saved_lang = config_manager.get("language", "fr")
        if saved_lang in self.translations:
            self.current_lang = saved_lang
        print(f"🌍 Langue initialisée: {self.current_lang}")

    def load_languages(self):
        """Charge les fichiers JSON de langue"""
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                internal_dir = Path(meipass) / "_internal"
                lang_dir = internal_dir if internal_dir.exists() else Path(meipass)
            else:
                exe_dir = Path(sys.executable).parent
                internal_dir = exe_dir / "_internal"
                lang_dir = internal_dir if internal_dir.exists() else exe_dir
        else:
            lang_dir = Path(__file__).parent

        print(f"📂 Chemin langues: {lang_dir}")

        for lang_code in ["fr", "en", "es"]:
            lang_file = lang_dir / f"lang_{lang_code}.json"
            if lang_file.exists():
                try:
                    with open(lang_file, "r", encoding="utf-8") as f:
                        self.translations[lang_code] = json.load(f)
                    print(f"✅ Langue chargée: {lang_code}")
                except Exception as e:
                    print(f"❌ Erreur {lang_code}: {e}")
                    self.translations[lang_code] = {}
            else:
                print(f"⚠️ Fichier manquant: {lang_file}")
                self.translations[lang_code] = {}

    def set_language(self, lang_code):
        """Change la langue active"""
        if lang_code in self.translations:
            self.current_lang = lang_code
            config_manager.set("language", lang_code)
            print(f"🌍 Langue changée: {lang_code}")

    def get(self, key, default=""):
        """Récupère une traduction"""
        return self.translations.get(self.current_lang, {}).get(key, default)


lang_manager = LanguageManager()


def _save_var(key, var):
    """v100 -- enregistre une tk.Variable dans la config à chaque saisie, sauf
    si la saisie est incomplète (champ vidé pour retaper, "1." …) : .get()
    lève alors TclError, affichée en "Exception in Tkinter callback". La
    valeur est enregistrée dès qu'elle redevient valide."""
    try:
        value = var.get()
    except (tk.TclError, ValueError):
        return
    config_manager.set(key, value)


# v104 -- conteneurs vidéo acceptés (ouverture et glisser-déposer), tous vérifiés
# le 2026-09-27 avec le décodeur FFmpeg d'OpenCV 5.0 (images, FPS et durée lus) :
# mp4/m4v/mov/ts (H.264), mkv (H.265), avi/3gp (MPEG-4), webm (VP9), wmv (WMV2),
# flv (FLV1), mpg (MPEG-2), mpeg (MPEG-1), ogv (Theora). Un codec rare peut
# rester illisible quelle que soit l'extension.
VIDEO_EXTS = (".mp4", ".m4v", ".mov", ".avi", ".mkv", ".webm", ".wmv", ".flv",
              ".mpg", ".mpeg", ".ts", ".3gp", ".ogv")


def tr(key, default, **kwargs):
    """v83 -- texte dynamique traduit : lang_manager.get(key, default) puis
    str.format(**kwargs). Si la cle manque dans la langue active, le texte FR
    par defaut est utilise ; si la traduction a un parametre invalide, repli
    sur le defaut (jamais d'exception affichee a l'utilisateur)."""
    text = lang_manager.get(key, default)
    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return default.format(**kwargs)


# Gabarits FR multi-lignes (textes par defaut des panneaux d'information)
K_DEFAULT_VIDEO_GIF_INFO = 'Dimensions : 128 x 32 px\nFPS : {fps}\nFrames : {frames}\nCouleurs : {colors}\nBoucle : {loop}\nPoids estimé : {size}\n'
K_DEFAULT_VIDEO_SOURCE_INFO = 'Fichier : {name}\nRésolution : {w} x {h} px\nDurée : {dur:.1f} s\nFPS source : {fps:.1f}\nFrames totales : {frames}\nTaille fichier : {size}\n'
K_DEFAULT_IMAGE_INFO = 'Fichier : {name}\nFormat : {fmt}\nDimensions : {w} x {h} px\nMode : {mode}\nTaille : {size:.1f} KB\n\nPalette dominante :\n{palette}\n\nRatio : {ratio:.2f}\nCible DMD : 4.0 (128/32)\n'
K_DEFAULT_MANUAL_INFO = 'Dimensions : {w} × {h} px\nMode couleur : {mode}\nMémoire : {mem:.1f} KB\nRatio : {ratio:.2f} (cible : 4.0)\nÉtat : {status}\n\nPalette dominante :\n{palette}\n\nHistorique : {count} états (position {pos}/{count})\n'


# ============================================================================
# MOTEUR DMD - Optimisation avancée pour écrans 128x32
# ============================================================================


# --- Modular engine (refactor étape 1) ---
# On remplace la classe DMDEngine définie dans ce monolithe par la version modulaire.
try:
    from .dmd_engine import DMDEngine as ModularDMDEngine
except ImportError:
    from dmd_engine import DMDEngine as ModularDMDEngine

DMDEngine = ModularDMDEngine


# --- Modular effects (refactor étape 2) ---
try:
    from .dmd_manual_effects import ManualEffects as ModularManualEffects
except ImportError:
    from dmd_manual_effects import ManualEffects as ModularManualEffects

ManualEffects = ModularManualEffects

# --- Modular text effects (refactor étape 3) ---
try:
    from .dmd_text_effects import TextEffects as ModularTextEffects
except ImportError:
    from dmd_text_effects import TextEffects as ModularTextEffects

try:
    from .dmd_text_animations import TextAnimations as ModularTextAnimations
except ImportError:
    from dmd_text_animations import TextAnimations as ModularTextAnimations

TextEffects = ModularTextEffects
TextAnimations = ModularTextAnimations

# --- Onglet AIDE : rendu Markdown (module réutilisé tel quel depuis le projet
# RecalBox_DMD, tools/RecalBoxDMD_md_renderer.py — générique, sans dépendance
# spécifique à ce projet) ---
try:
    from . import RecalBoxDMD_md_renderer as md_renderer
except ImportError:
    import RecalBoxDMD_md_renderer as md_renderer


# ============================================================================
# APPLICATION PRINCIPALE
# ============================================================================

# --- UI constants (refactor taille) ---
try:
    from .dmd_ui_constants import WINDOWS_FONTS, TEXT_MAP
except ImportError:
    from dmd_ui_constants import WINDOWS_FONTS, TEXT_MAP

# --- GIF exporter (auparavant importé localement à 3 endroits) ---
try:
    from .dmd_gif_exporter import export_frames_to_gif, estimate_gif_size
except ImportError:
    from dmd_gif_exporter import export_frames_to_gif, estimate_gif_size

# v87 -- score qualité 0-100 des GIF exportés (aide à la relecture d'un lot)
try:
    from . import dmd_quality as dq
except ImportError:
    import dmd_quality as dq

# v91 -- profils de génération (options neutres du moteur)
try:
    from . import dmd_profiles
except ImportError:
    import dmd_profiles

# v96 -- propositions de correction des GIF faibles (fenêtre Revoir)
try:
    from . import dmd_autofix
except ImportError:
    import dmd_autofix

# --- Modular video engine (nouvel onglet VIDEO) ---
try:
    from .dmd_video_engine import VideoEngine, CV2_AVAILABLE
except ImportError:
    from dmd_video_engine import VideoEngine, CV2_AVAILABLE


class DMDConverter:
    """Application principale de conversion DMD"""

    def __init__(self):
        self.root = TkinterDnD.Tk()
        # self.root.overrideredirect(True)  # Supprime la barre de titre et les bordures
        self.progress_text_var = tk.StringVar(
            master=self.root, value=lang_manager.get("ready", "Prêt")
        )
        self.progress_bar_var = tk.DoubleVar(master=self.root, value=0.0)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.update_title()
        self.root.state("normal")  # Plein écran fenêtré 'zoomed' 'normal'

        # Données
        self.images = []
        self.source_root_dir = None
        self.current_preview = None
        self.preview_frames: list[Image.Image] = []
        self.preview_index = 0
        self.animating = False
        self.current_image_idx = None
        self.current_fps = 10

        self.image_settings = {}
        self.manual_exports = set()
        # v97 -- édition lancée depuis Revoir : {"folder", "rel", "review"} ;
        # l'export MANUEL propose alors de remplacer ce GIF du lot
        self.review_target = None
        self.proposals = []
        self.selected_proposal = 0
        self.locked_proposal = None
        self._ai_base_settings = None
        self._ai_image_path = None
        self.processing_canceled = False

        # Paramètres
        self.theme = tk.StringVar(value=config_manager.get("theme", "dark"))
        self.theme.trace_add(
            "write",
            lambda *args: (
                config_manager.set("theme", self.theme.get()),
                config_manager.save(),
            ),
        )
        self.add_anim_to_name = tk.BooleanVar(
            value=config_manager.get("add_anim_to_name", False)
        )
        self.add_anim_to_name.trace_add(
            "write",
            lambda *args: _save_var("add_anim_to_name", self.add_anim_to_name),
        )

        # Manuel
        self.manual_image = None

        # AUTO/IA: mémorise les choix de proposition IA (clic) par image.
        # Ces images seront exportées par le batch avec les settings choisies,
        # et ne doivent pas être écrasées par le lock batch.
        self.ai_selected_images = set()
        self.manual_original = None
        self.manual_history = []
        # Index de l'état courant dans manual_history (permet un undo/redo
        # incrémental — voir _manual_commit_history/manual_undo/manual_redo).
        self.manual_history_index = -1
        self.fill_mode = False
        self.fill_color = (255, 0, 0)
        self.manual_frames = []
        self.manual_animating = False
        self.manual_frame_idx = 0
        # v101 -- une seule étape d'animation en attente par aperçu (voir _anim_schedule)
        self._anim_jobs = {}
        self._anim_due = {}  # heure prévue de la prochaine image, par aperçu
        # v103 -- zone d'effets MANUEL : [x1, y1, x2, y2] en pixels de l'image, ou None
        self.manual_zone = None
        self.zone_mode = False
        self._zone_drag = None
        self._manual_frames_fps = None
        self._manual_regen_job = None
        self.eraser_mode = False
        self.eraser_tolerance = 30
        # Crop mode
        self.crop_mode = False
        self.crop_start = None
        self.crop_rect = None
        self.crop_preview_rect = None

        # Text scroll
        self.text_frames = []
        # Polices système Windows détectées
        self.windows_fonts = WINDOWS_FONTS

        self.text_animating = False
        self.text_frame_idx = 0

        # Video (onglet VIDEO)
        self.video_path = None
        self.video_meta = None
        self.video_thumbnails = []
        self.video_trim_start = tk.DoubleVar(value=0.0)
        self.video_trim_end = tk.DoubleVar(value=0.0)
        self.video_duration = tk.DoubleVar(value=0.0)  # durée souhaitée (s), défaut = durée source au chargement
        self.video_roi = None  # (x, y, w, h) en coords frame de référence, ou None
        self.video_roi_canvas_ids = []
        self.video_ref_frame = None
        self.video_ref_frame_display_scale = 1.0
        self.video_fps = tk.IntVar(value=config_manager.get("video_fps", 12))
        self.video_quality_auto = tk.BooleanVar(value=True)
        # Sélecteur de mode de cadrage à 3 états, mutuellement exclusifs par
        # construction (radio group, voir setup_video_tab) — demande
        # explicite utilisateur ("le mode zoom auto et tracking auto
        # s'excluent l'un l'autre") : "tracking" = suivi automatique OpenCV
        # d'une zone unique (pas de repositionnement manuel) ; "auto_zoom" =
        # l'utilisateur positionne un cadrage unique à la main, la TAILLE
        # est calculée automatiquement (pas de tracking, pas de système de
        # points) ; "manual" = les 2 automatismes off, système de points
        # (zones multiples + zoom keyframé) ET curseur de zoom entièrement
        # pilotés à la main. `video_roi_tracking_enabled`/`video_resize_auto`
        # ci-dessous restent des booléens DÉRIVÉS de ce choix (calculés par
        # _video_on_crop_mode_change) — conservés tels quels pour ne pas
        # perturber tout le code existant qui les lit déjà (pipeline,
        # _video_effective_zoom, etc.).
        self.video_crop_mode = tk.StringVar(value="tracking")
        self.video_roi_tracking_enabled = tk.BooleanVar(value=True)
        # Zoom cadrage/redimensionnement : -1.0 = redimensionnement pur, sans
        # crop ; 0.0 = crop serré au ratio 128:32 (défaut) ; +1.0 = zoom
        # numérique au-delà du crop serré (cadre plus petit que le crop
        # serré, sujet agrandi) — demande explicite "-100% = resize seul, 0
        # = crop serré, +100% zoom" (remplace l'ancienne échelle 0.0-1.0 où
        # 0=resize/1=crop serré, voir VideoEngine.compute_crop_windows/
        # roi_rect_for_zoom pour le détail des 2 segments d'interpolation).
        self.video_crop_zoom = tk.DoubleVar(value=0.0)
        # Coché : ignore video_crop_zoom, calcule automatiquement fit/fill
        # selon le ratio de la vidéo source (même heuristique que
        # DMDEngine.adaptive_resize mode="auto"). Dérivé de video_crop_mode
        # (coché dans "tracking" ET "auto_zoom", décoché seulement en
        # "manual") — voir _video_on_crop_mode_change.
        self.video_resize_auto = tk.BooleanVar(value=False)
        # Timeline unifiée de points de cadrage — remplace l'ancien
        # video_roi_keyframes (2-tuples (t, roi), mode manuel uniquement).
        # Liste de dicts {"t": float, "roi": (x,y,w,h), "mode": "auto"|
        # "manual"}, pas nécessairement triée (triée à la volée où
        # nécessaire). Un point "auto" réamorce le tracker OpenCV à son
        # instant (segment tracké jusqu'au point suivant) ; un point
        # "manual" fige le cadrage (SANS interpolation, cut net) jusqu'au
        # point suivant — voir VideoEngine.compute_crop_windows_from_events.
        # Le système de points n'existe qu'en mode "manual" (video_crop_mode)
        # — les boutons de gestion sont grisés dans les 2 autres modes, voir
        # _video_update_point_buttons_state.
        self.video_roi_events = []
        # Vrai entre un clic sur "➕ Point ici" et le relâchement du dessin
        # qui doit suivre — voir _video_add_roi_point/_video_roi_end
        # (demande explicite "Point ici efface et exige un nouveau
        # dessin ... committe automatiquement au relâchement").
        self._video_awaiting_point_draw = False
        # Zoom cadrage/redimensionnement keyframé dans le temps,
        # INDÉPENDAMMENT des points de zone ci-dessus : liste de
        # (timestamp_secondes, zoom 0.0-1.0). 0-1 entrée = comportement
        # historique (video_crop_zoom scalaire global, voir
        # _video_effective_zoom) ; ≥2 entrées = interpolation LINÉAIRE dans
        # le temps (contrairement aux zones : le zoom est un paramètre
        # continu, pas un cut discret de sujet).
        self.video_zoom_keyframes = []
        # Historique undo/redo (points de zone + de zoom), même mécanisme
        # pointeur qu'en MANUEL (manual_history/manual_history_index) :
        # liste de snapshots {"events": [...], "zoom_kf": [...]},
        # video_roi_history_index pointe l'état courant.
        self.video_roi_history = []
        self.video_roi_history_index = -1
        # Instant actuellement affiché dans le canvas ROI pour l'édition du
        # cadrage manuel (indépendant du trim, doit toujours rester dans
        # [trim_start, trim_end]).
        self.video_roi_edit_time = tk.DoubleVar(value=0.0)
        self.video_gif_size_var = tk.StringVar(value="—")
        self.video_frames = []
        self.video_animating = False
        self.video_frame_idx = 0
        self.video_processing = False
        # Lecteur vidéo intégré (cadre "Lecture", lecture en boucle démarrée
        # immédiatement au chargement du fichier) — VideoCapture persistant
        # entre frames (contrairement aux extractions ponctuelles ailleurs
        # dans l'onglet), voir VideoEngine.open_capture.
        self._video_playback_cap = None
        self.video_playback_playing = False
        self._video_playback_delay_ms = 40

        self.setup_ui()
        self.apply_theme()

    def apply_translations(self):
        """Force l'application des traductions au démarrage"""
        print(f"🔄 Application traductions: {lang_manager.current_lang}")

        # Mettre à jour titre
        self.update_title()

        # Mettre à jour onglets — libellés centrés sur la largeur EN PIXELS du plus
        # long (onglets en colonne latérale depuis v21). Le padding par nombre de
        # caractères (v22) suppose une police à chasse fixe ; la police par défaut Tk
        # est proportionnelle ("TEXTSCROLL" reste plus large que "AUTO" même à
        # caractères égaux), d'où le bord en dents de scie. Mesure réelle via
        # tkfont.measure() pour un padding en espaces qui approche la largeur en
        # pixels du plus long libellé, pas juste son nombre de caractères.
        try:
            tab_labels = [
                lang_manager.get("tab_auto"),
                lang_manager.get("tab_manual"),
                lang_manager.get("tab_video"),
                lang_manager.get("tab_textscroll"),
                lang_manager.get("tab_params"),
                lang_manager.get("tab_debug"),
                lang_manager.get("tab_help"),
            ]
            tab_font = tkfont.nametofont("TkDefaultFont")
            space_w = tab_font.measure(" ") or 1
            widths = [tab_font.measure(t) for t in tab_labels]
            max_w = max(widths)
            for i, (t, w) in enumerate(zip(tab_labels, widths)):
                pad_total = max(0, round((max_w - w) / space_w))
                left = pad_total // 2
                right = pad_total - left
                self.notebook.tab(i, text=(" " * left) + t + (" " * right))
        except:
            pass

        # Mettre à jour status
        self.progress_text_var.set(lang_manager.get("ready"))

        # Mettre à jour tous les widgets
        self._update_widget_texts()

        # Recharger le contenu de l'onglet AIDE dans la nouvelle langue (le
        # widget peut ne pas encore exister lors du tout premier appel, fait
        # depuis setup_ui() avant setup_help_tab() — ignoré silencieusement
        # dans ce cas, setup_help_tab() affichera directement la bonne langue).
        if getattr(self, "help_text", None):
            self._refresh_help_tab_content()

        print("✅ Traductions appliquées")

    def _update_widget_texts(self):
        """Met à jour les textes de tous les widgets"""
        # Mapping complet texte original → clé JSON
        text_map = TEXT_MAP

        reverse_map = {}
        for translations in lang_manager.translations.values():
            for key, value in translations.items():
                reverse_map[value] = key

        def update_recursive(widget):
            try:
                widget_class = widget.winfo_class()

                # Boutons et Labels
                if widget_class in ("TButton", "Button", "TLabel", "Label"):
                    current = widget.cget("text")
                    key = text_map.get(current) or reverse_map.get(current)
                    if key:
                        new_text = lang_manager.get(key, current)
                        widget.config(text=new_text)

                # LabelFrame
                elif widget_class == "TLabelframe":
                    current = widget.cget("text")
                    key = text_map.get(current) or reverse_map.get(current)
                    if key:
                        new_text = lang_manager.get(key, current)
                        widget.config(text=new_text)

                # Checkbutton
                elif widget_class in ("TCheckbutton", "Checkbutton"):
                    current = widget.cget("text")
                    key = text_map.get(current) or reverse_map.get(current)
                    if key:
                        new_text = lang_manager.get(key, current)
                        widget.config(text=new_text)

                # Radiobutton
                elif widget_class in ("TRadiobutton", "Radiobutton"):
                    current = widget.cget("text")
                    key = text_map.get(current) or reverse_map.get(current)
                    if key:
                        new_text = lang_manager.get(key, current)
                        widget.config(text=new_text)

                # Parcourir enfants
                for child in widget.winfo_children():
                    update_recursive(child)
            except:
                pass

        update_recursive(self.root)

        # Mettre à jour les chaînes dynamiques qui ne sont pas des widgets statiques
        try:
            self.ia_status_var.set(
                lang_manager.get("waiting", self.ia_status_var.get())
            )
        except Exception:
            pass
        try:
            self.manual_status.set(
                lang_manager.get("load_image_first", self.manual_status.get())
            )
        except Exception:
            pass
        try:
            self.manual_preview_status.set(
                lang_manager.get("click_preview", self.manual_preview_status.get())
            )
        except Exception:
            pass
        try:
            self.text_preview_status.set(
                lang_manager.get("enter_text_generate", self.text_preview_status.get())
            )
        except Exception:
            pass
        try:
            self.video_status.set(
                lang_manager.get("video_status_default", self.video_status.get())
            )
        except Exception:
            pass
        try:
            current_text = self.text_input.get("1.0", "end-1c")
            placeholders = [
                lang_manager.translations.get(code, {}).get("your_text_here", "")
                for code in lang_manager.translations
            ]
            placeholder = lang_manager.get("your_text_here", "Votre texte ici...")
            if current_text.strip() == "" or current_text in placeholders:
                self.text_input.delete("1.0", tk.END)
                self.text_input.insert("1.0", placeholder)
        except Exception:
            pass

    # ========================================================================
    # VERSION DU LOGICIEL
    # ========================================================================
    APP_VERSION = "3.2.0"

    # ========================================================================

    def update_title(self):
        """Met à jour le titre selon la langue"""

        def apply_version(text: str) -> str:
            # Remplace vX.Y.Z (ou vX.Y) par la version runtime
            return re.sub(r"v\d+\.\d+(?:\.\d+)?", f"v{self.APP_VERSION}", text)

        # Inclure la version dans le titre
        title_with_version = f"DMD GIF Creator {self.APP_VERSION} - 128x32"
        app_title = lang_manager.get("app_title", title_with_version)
        self.root.title(apply_version(app_title))

        logger.info(f"Application démarrée v{self.APP_VERSION}")

    def setup_ui(self):
        """Construction de l'interface utilisateur"""
        # Container principal
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Header avec thème
        header = ttk.Frame(main_container)
        header.pack(fill=tk.X, padx=10, pady=(5, 0))

        ttk.Label(
            header,
            text=re.sub(
                r"v\d+\.\d+(?:\.\d+)?",
                f"v{self.APP_VERSION}",
                f"DMD Creator v{self.APP_VERSION}",
            ),
            font=("Arial", 12, "bold"),
        ).pack(side=tk.LEFT)

        # Hauteur dynamique du Notebook (v21) : calculée depuis la hauteur d'écran
        # réelle plutôt qu'une valeur fixe (910px, calibrée empiriquement sur l'écran
        # de dev ~1083px de haut). Évite de recréer silencieusement le bug de
        # coupure du contenu (v20) sur un écran plus petit.
        #
        # Constantes empiriques Windows, ajustées via test visuel réel :
        #   OS_CHROME_MARGIN : barre de titre + bordures fenêtre + barre des tâches
        #   HEADER_MARGIN    : bandeau titre appli + paddings au-dessus du Notebook
        #   TAB_STRIP_GAIN   : hauteur libérée par le passage des onglets en
        #     position latérale (voir apply_theme, tabposition="wn") — ils n'occupent
        #     plus de hauteur au sommet du Notebook, cette marge est réinjectée ici.
        OS_CHROME_MARGIN = 120
        HEADER_MARGIN = 50
        TAB_STRIP_GAIN = 35

        screen_h = self.root.winfo_screenheight()
        computed_h = screen_h - OS_CHROME_MARGIN - HEADER_MARGIN + TAB_STRIP_GAIN
        self.notebook_height = max(600, min(computed_h, screen_h - 150))
        logger.info(
            f"Notebook height calculé: {self.notebook_height}px (écran={screen_h}px)"
        )

        # Notebook
        self.notebook = ttk.Notebook(main_container, height=self.notebook_height)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Onglets
        self.auto_frame = ttk.Frame(self.notebook)
        self.manual_frame = ttk.Frame(self.notebook)
        self.video_frame = ttk.Frame(self.notebook)
        self.textscroll_frame = ttk.Frame(self.notebook)
        self.params_frame = ttk.Frame(self.notebook)
        self.debug_frame = ttk.Frame(self.notebook)
        self.help_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.auto_frame, text="AUTO")
        self.notebook.add(self.manual_frame, text="MANUEL")
        self.notebook.add(self.video_frame, text="VIDEO")
        self.notebook.add(self.textscroll_frame, text="TEXTSCROLL")
        self.notebook.add(self.params_frame, text="PARAMETRES")
        self.notebook.add(self.debug_frame, text="DEBUG")
        self.notebook.add(self.help_frame, text="AIDE")

        # Bind changement onglet
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.setup_auto_tab()
        self.setup_manual_tab()
        self.setup_video_tab()
        self.setup_textscroll_tab()
        self.setup_params_tab()
        self.setup_debug_tab()
        self.setup_help_tab()

        # Footer
        footer = ttk.Frame(main_container)
        footer.pack(fill=tk.X, padx=10, pady=(0, 5))

        # "Shan_ayA 2026" reste dans le footer, aligné avec la barre de
        # progression (demande explicite après clarification : seul le
        # bouton Quitter change de zone, pas le copyright, qui garde sa
        # position simple à gauche du footer).
        ttk.Label(footer, text="Shan_ayA 2026", font=("Arial", 8, "italic")).pack(
            side=tk.LEFT, padx=(0, 10), pady=5
        )

        # Progression centrée et occuppe l'espace libre restant
        progress_frame = ttk.Frame(footer)
        progress_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.columnconfigure(1, weight=0)
        progress_frame.columnconfigure(2, weight=1)

        ttk.Label(progress_frame, textvariable=self.progress_text_var).grid(
            row=0, column=1, pady=(5, 0), sticky="ew"
        )
        self.progressbar = ttk.Progressbar(
            progress_frame, variable=self.progress_bar_var, maximum=100
        )
        self.progressbar.grid(
            row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=5
        )

        # Bouton Quitter : placé COMME un onglet de navigation supplémentaire,
        # dans la bande de tabs latérale du Notebook (tabposition="wn"), au
        # BAS de celle-ci — demande explicite après clarification ("le bas
        # du bouton doit être aligné avec le bas du cadre qui contient tous
        # les éléments [sauf la barre de progression]. le bouton doit être
        # placé comme un des onglets de navigation mais en bas du cadre").
        # Impossible d'insérer un vrai onglet supplémentaire dans la bande de
        # tabs elle-même (gérée en interne par ttk::notebook, réservée aux
        # pages ajoutées via .add()) : utilise `place()` en coordonnées
        # ABSOLUES à l'intérieur du Notebook lui-même (widget enfant direct
        # du Notebook, PAS un enfant de footer), superposé à la zone vide
        # sous le dernier onglet "AIDE", avec la même largeur que la bande
        # de tabs. Le bas du bouton (y + height) coïncide donc avec le bas
        # du Notebook = bas du cadre contenant tous les éléments de l'app
        # SAUF le footer/la barre de progression, qui reste un cadre séparé
        # en dessous. Largeur/position resynchronisées sur <Configure> du
        # Notebook, même pattern que _video_sync_canvas_widths (nécessaire
        # car la largeur réelle de la bande de tabs n'est connue qu'une fois
        # la fenêtre effectivement dessinée).
        self.quit_btn = ttk.Button(
            self.notebook, text="Quitter", command=self.root.destroy
        )

        def _sync_quit_btn_placement(event=None):
            try:
                tabstrip_w = self.auto_frame.winfo_x()
            except Exception:
                return
            if tabstrip_w <= 10:
                return
            btn_h = self.quit_btn.winfo_reqheight() or 28
            y = self.notebook_height - btn_h
            self.quit_btn.place(x=0, y=y, width=tabstrip_w, height=btn_h)

        self.notebook.bind("<Configure>", _sync_quit_btn_placement, add="+")
        self.root.after(300, _sync_quit_btn_placement)

        # Appliquer traductions (après création de tous les widgets)
        self.apply_translations()

        # Appliquer traductions (après création de tous les widgets)
        self.apply_translations()

    def setup_auto_tab(self):
        # Barre de progression et label état dans onglet AUTO
        # self.progressbar = ttk.Progressbar(
        #    self.auto_frame, variable=self.progress_bar_var, maximum=100
        # )
        # self.progressbar.pack(fill="x", pady=5, padx=5)
        # self.progress_label = ttk.Label(
        #    self.auto_frame, textvariable=self.progress_text_var
        # )
        # self.progress_label.pack(pady=2)

        """Configuration onglet AUTO avec IA"""
        main_frame = ttk.Frame(self.auto_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Paramètres globaux
        params_frame = ttk.LabelFrame(
            main_frame, text="Paramètres Globaux", padding="5"
        )
        params_frame.grid(row=0, column=0, columnspan=3, sticky="we", pady=10)

        # Ligne unique (fusion des ex-Ligne 1/Ligne 2) : réduit la hauteur du cadre
        # "Paramètres Globaux" pour libérer de la place verticale à la grille de
        # propositions IA (désormais sur 2 rangées, voir setup_auto_tab).
        row1 = ttk.Frame(params_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text="FPS:").pack(side=tk.LEFT)
        self.fps_var = tk.IntVar(value=config_manager.get("fps", 10))
        self.fps_var.trace_add(
            "write", lambda *args: _save_var("fps", self.fps_var)
        )
        self.fps_var.trace_add(
            "write", lambda *args: _save_var("fps", self.fps_var)
        )
        ttk.Spinbox(
            row1,
            from_=1,
            to=60,
            textvariable=self.fps_var,
            width=6,
            command=self.on_global_param_change,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(row1, text="Durée (s):").pack(side=tk.LEFT, padx=(10, 5))
        self.duration_var = tk.DoubleVar(value=config_manager.get("duration", 2.0))
        self.duration_var.trace_add(
            "write",
            lambda *args: _save_var("duration", self.duration_var),
        )
        self.duration_var.trace_add(
            "write",
            lambda *args: _save_var("duration", self.duration_var),
        )
        ttk.Spinbox(
            row1,
            from_=0.5,
            to=10,
            increment=0.5,
            textvariable=self.duration_var,
            width=6,
            command=self.on_global_param_change,
        ).pack(side=tk.LEFT)

        scroll_speed_label = ttk.Label(row1, text="Vitesse scroll:")
        scroll_speed_label.pack(side=tk.LEFT, padx=(10, 5))
        add_help_tooltip(scroll_speed_label, "tooltip_scroll_speed")
        self.scroll_speed_var = tk.DoubleVar(value=config_manager.get("scroll_speed", 1))
        self.scroll_speed_var.trace_add(
            "write",
            lambda *args: _save_var("scroll_speed", self.scroll_speed_var),
        )
        ttk.Spinbox(
            row1,
            from_=0.1,
            to=10,
            increment=0.1,
            textvariable=self.scroll_speed_var,
            width=6,
            command=self.on_global_param_change,
        ).pack(side=tk.LEFT)

        ttk.Label(row1, text="Contraste:").pack(side=tk.LEFT, padx=(10, 5))
        self.contrast_var = tk.DoubleVar(value=config_manager.get("contrast", 1.5))
        self.contrast_var.trace_add(
            "write",
            lambda *args: _save_var("contrast", self.contrast_var),
        )
        self.contrast_var.trace_add(
            "write",
            lambda *args: _save_var("contrast", self.contrast_var),
        )
        ttk.Spinbox(
            row1,
            from_=1.0,
            to=3.0,
            increment=0.1,
            textvariable=self.contrast_var,
            width=6,
            command=self.on_global_param_change,
        ).pack(side=tk.LEFT)

        ttk.Label(row1, text="Saturation:").pack(side=tk.LEFT, padx=(10, 5))
        self.saturation_var = tk.DoubleVar(value=config_manager.get("saturation", 1.3))
        self.saturation_var.trace_add(
            "write",
            lambda *args: _save_var("saturation", self.saturation_var),
        )
        self.saturation_var.trace_add(
            "write",
            lambda *args: _save_var("saturation", self.saturation_var),
        )
        ttk.Spinbox(
            row1,
            from_=0.5,
            to=2.0,
            increment=0.1,
            textvariable=self.saturation_var,
            width=6,
            command=self.on_global_param_change,
        ).pack(side=tk.LEFT)

        ttk.Label(row1, text="Couleurs GIF:").pack(side=tk.LEFT, padx=(10, 5))
        self.color_count_var = tk.IntVar(value=config_manager.get("color_count", 256))
        self.color_count_var.trace_add(
            "write",
            lambda *args: _save_var("color_count", self.color_count_var),
        )
        self.color_count_var.trace_add(
            "write",
            lambda *args: _save_var("color_count", self.color_count_var),
        )
        color_combo = ttk.Combobox(
            row1,
            textvariable=self.color_count_var,
            values=[str(v) for v in (8, 16, 32, 64, 128, 256)],
            state="readonly",
            width=6,
        )
        color_combo.pack(side=tk.LEFT)
        color_combo.bind(
            "<<ComboboxSelected>>", lambda e: self.on_global_param_change()
        )

        self.pixel_perfect_var = tk.BooleanVar(
            value=config_manager.get("pixel_perfect", False)
        )
        self.pixel_perfect_var.trace_add(
            "write",
            lambda *args: _save_var("pixel_perfect", self.pixel_perfect_var),
        )
        # Luminosité LED simulée (voir DMDEngine.render_led_style, brightness) :
        # partagée entre les 3 onglets de génération, comme pixel_perfect_var —
        # c'est une propriété du panneau physique simulé, pas un réglage par
        # onglet. Défaut 0.5 = comportement neutre (aucun changement de rendu).
        # Pas de trace_add("write", ...) ici contrairement à pixel_perfect_var :
        # la sauvegarde sur CHAQUE variation pendant un glissement de slider est
        # trop fréquente (signalé par l'utilisateur) — voir
        # _add_led_brightness_slider, qui sauvegarde uniquement au relâchement
        # (<ButtonRelease-1>) sur chacune des 3 instances du widget.
        self.led_brightness_var = tk.DoubleVar(
            value=config_manager.get("led_brightness", 0.5)
        )
        # v95 -- case pixel-perfect au bout de la ligne des réglages (elle avait
        # sa propre ligne : avec les 2 lignes Profil de la v91, la 2e rangée de
        # propositions sortait de la fenêtre)
        pixel_perfect_check = ttk.Checkbutton(
            row1,
            text="Mode DMD / Forcer pixel-perfect",
            variable=self.pixel_perfect_var,
            command=self.on_global_param_change,
        )
        pixel_perfect_check.pack(side=tk.LEFT, padx=(20, 0))
        add_help_tooltip(pixel_perfect_check, "tooltip_pixel_perfect")

        # v91 -- profils (dmd_profiles) : le moteur reste neutre, un profil
        # règle les options (défilement imposé dès L/H, inversion des logos
        # sombres, plafond d'aller-retour, cadence). Remplace le réglage seul
        # "Défilement dès" de la v86. Valeurs courantes gardées dans config.json.
        self._setup_profile_row(params_frame)

        # Container principal
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=1, column=0, columnspan=3, sticky="wnes", pady=10)

        # GAUCHE: Liste + Infos
        left_panel = ttk.Frame(content_frame)
        left_panel.grid(row=0, column=0, sticky="wnes", padx=(0, 5))

        # Liste images
        list_frame = ttk.LabelFrame(left_panel, text="Images", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # Barre d'outils compacte en haut (source + sélection rapide + réautoriser +
        # vider), pour laisser toute la hauteur disponible à la liste en dessous.
        # Panneau "Source:" séparé supprimé (v19) : le glisser-déposer étant l'usage
        # courant, ces boutons ne sont plus qu'un complément regroupé ici avec le
        # reste des actions sur la liste.
        toolbar_frame = ttk.Frame(list_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 5))

        btn_folder = ttk.Button(
            toolbar_frame, text="📁", command=self.select_folder, width=3
        )
        btn_folder.pack(side=tk.LEFT, padx=1)
        add_help_tooltip(btn_folder, "tooltip_add_folder")

        btn_images = ttk.Button(
            toolbar_frame, text="🖼️", command=self.select_images, width=3
        )
        btn_images.pack(side=tk.LEFT, padx=(1, 8))
        add_help_tooltip(btn_images, "tooltip_add_images")
        ttk.Button(
            toolbar_frame, text="✓", command=self.select_all_images, width=3
        ).pack(side=tk.LEFT, padx=1)
        ttk.Button(
            toolbar_frame, text="✗", command=self.deselect_all_images, width=3
        ).pack(side=tk.LEFT, padx=1)
        ttk.Button(
            toolbar_frame, text="⇄", command=self.invert_selection, width=3
        ).pack(side=tk.LEFT, padx=1)
        reauthorize_btn = ttk.Button(
            toolbar_frame, text="🔓 Réautoriser", command=self.reauthorize_image
        )
        reauthorize_btn.pack(side=tk.LEFT, padx=(8, 1))
        add_help_tooltip(reauthorize_btn, "tooltip_reauthorize")
        ttk.Button(
            toolbar_frame, text="🗑 Vider", command=self.clear_image_list
        ).pack(side=tk.LEFT, padx=(8, 1))

        # Zone liste : Treeview (liste plate, colonne unique = chemin relatif),
        # occupe tout l'espace vertical restant. Remplace l'ancienne tk.Listbox pour
        # permettre la suppression d'éléments (Suppr / menu contextuel) et le
        # glisser-déposer de fichiers/dossiers.
        tree_container = ttk.Frame(list_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        self.image_tree = ttk.Treeview(
            tree_container, show="tree", selectmode="extended"
        )
        self.image_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.image_tree.bind("<<TreeviewSelect>>", self.on_image_select)
        self.image_tree.bind("<Delete>", lambda e: self.remove_selected_images())
        self.image_tree.bind("<Button-3>", self._show_image_tree_menu)

        tree_scrollbar = ttk.Scrollbar(
            tree_container, orient=tk.VERTICAL, command=self.image_tree.yview
        )
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.image_tree.configure(yscrollcommand=tree_scrollbar.set)

        # Texte indicatif affiché en fond de cadre tant qu'aucune image n'est chargée
        # (le glisser-déposer cible toute la fenêtre, donc aussi cette zone).
        self.image_tree_hint = ttk.Label(
            tree_container,
            text="📂 Glisser-déposer\nun dossier ou des images ici",
            justify="center",
            anchor="center",
            foreground="#888888",
        )
        self.image_tree_hint.place(relx=0.5, rely=0.5, anchor="center")

        self.image_tree_menu = tk.Menu(self.image_tree, tearoff=0)
        self.image_tree_menu.add_command(
            label="🗑 Retirer de la liste", command=self.remove_selected_images
        )

        # Glisser-déposer : toute la fenêtre est une zone de dépôt (dossiers ou
        # fichiers image), plus tolérant qu'une zone restreinte à la seule liste.
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.on_files_dropped)

        # Infos image
        info_frame = ttk.LabelFrame(left_panel, text="Informations Image", padding="5")
        info_frame.pack(fill=tk.X)

        self.info_text = tk.Text(
            info_frame, height=5, width=25, wrap=tk.WORD, state="disabled"
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)

        # CENTRE: Previews
        center_panel = ttk.Frame(content_frame)
        center_panel.grid(row=0, column=1, sticky="wnes", padx=5)

        # Original
        original_frame = ttk.LabelFrame(
            center_panel, text="Image Originale", padding="5"
        )
        original_frame.pack(fill=tk.X, pady=(0, 5))

        self.canvas_original = Canvas(original_frame, width=640, height=130, bg="black")
        self.canvas_original.pack()

        # Status
        status_frame = ttk.Frame(center_panel)
        status_frame.pack(pady=5, fill=tk.X)

        self.ia_status_var = tk.StringVar(
            value=lang_manager.get("waiting", "En attente...")
        )
        ttk.Label(
            status_frame, textvariable=self.ia_status_var, font=("Arial", 10, "italic")
        ).pack()

        # DMD Principal
        dmd_main_frame = ttk.LabelFrame(
            center_panel, text="Aperçu DMD Principal (128x32)", padding="5"
        )
        dmd_main_frame.pack(fill=tk.X, pady=(0, 5))

        dmd_main_row = ttk.Frame(dmd_main_frame)
        dmd_main_row.pack()

        self.canvas_dmd_main = Canvas(dmd_main_row, width=512, height=128, bg="black")
        self.canvas_dmd_main.pack(side=tk.LEFT)
        self._add_led_zoom_icon(
            self.canvas_dmd_main,
            get_frames=lambda: self.preview_frames,
            get_idx=lambda: self.preview_index,
            get_fps=lambda: self.current_fps,
            title="Aperçu DMD Principal",
        )
        self._add_led_brightness_slider(dmd_main_row).pack(
            side=tk.LEFT, padx=(10, 0)
        )

        # Propositions IA
        proposals_frame = ttk.LabelFrame(
            center_panel, text="Propositions IA", padding="5"
        )
        proposals_frame.pack(fill=tk.BOTH, expand=True)

        self.proposal_canvases = []
        self.proposal_labels = []
        self.proposal_lock_checks = []
        self.proposal_locks = []
        self.proposal_info_labels = []
        self.proposal_tooltips = []

        proposals_grid = ttk.Frame(proposals_frame)
        proposals_grid.pack(fill=tk.X, expand=True)

        # Grille 3 colonnes × 2 rangées : rangée 0 = propositions "de base" (resize,
        # fill, optimisé), rangée 1 = les 3 propositions artistiques. Avant, les 5
        # (puis 6) propositions s'alignaient sur une seule rangée et poussaient la
        # largeur de la fenêtre bien au-delà de 1900px — repli sur une grille pour
        # tenir en largeur.
        PROPOSALS_COLUMNS = 3
        for i in range(6):
            row, col = divmod(i, PROPOSALS_COLUMNS)
            frame = ttk.Frame(proposals_grid, relief=tk.RAISED, borderwidth=2)
            frame.grid(row=row, column=col, padx=4, pady=3, sticky=tk.N)

            label = ttk.Label(frame, text=tr("t_proposal_n", "Proposition {n}", n=i + 1), font=("Arial", 8))
            label.pack(pady=(3, 1))

            # 384×96 (3x l'échelle native 128x32, demandé explicitement — était
            # 256×64/2x). La grille 3×2 (6 propositions) est donc plus large ; à
            # surveiller si ça repousse la fenêtre au-delà de l'écran comme
            # c'était le cas avant le fix v20 (grille 3×2 déjà introduite alors
            # pour cette raison).
            canvas = Canvas(
                frame, width=384, height=96, cursor="hand2", bg="black"
            )  # taille exactement alignée sur l'image affichée (voir auto_analyze_and_preview)
            canvas.pack()
            canvas.bind("<Button-1>", lambda e, idx=i: self.select_proposal(idx))

            # Infos paramètres (affichés en tooltip sur survol)
            info_label = ttk.Label(frame, text="", font=("Arial", 7), wraplength=384)

            # Propositions 1-3 (index 0-2) : verrouillage pour le batch. Propositions
            # artistiques 4-6 (index 3-5) : bouton "New proposition" qui relance un
            # choix artistique à la place (le verrouillage n'a pas de sens pour un
            # effet choisi au hasard que l'utilisateur peut vouloir rejouer).
            lock_var = tk.BooleanVar()
            if i < 3:
                lock_check = tk.Checkbutton(
                    frame,
                    text="🔒 Verrouiller pour le batch",
                    variable=lock_var,
                    command=lambda idx=i, var=lock_var: self.toggle_lock(idx, var),
                    wraplength=384,
                    anchor="w",
                    justify="left",
                )
            else:
                lock_check = ttk.Button(
                    frame,
                    # Corrigé de "New proposition" (anglais en dur dans une
                    # app par ailleurs entièrement en français à la
                    # construction, jamais traduit — bug d'incohérence de
                    # langue de base, pas juste une traduction manquante).
                    text="🔄 Nouvelle proposition",
                    command=lambda idx=i: self.regenerate_artistic_proposal(idx),
                )
            lock_check.pack(fill=tk.X, pady=(1, 3))

            tooltip = Tooltip(frame, wraplength=384)
            for widget in (frame, canvas, label, lock_check):
                widget.bind(
                    "<Enter>",
                    lambda event, tip=tooltip, idx=i: tip.showtip(
                        self.proposal_info_labels[idx].cget("text")
                    ),
                )
                widget.bind("<Leave>", lambda event, tip=tooltip: tip.hidetip())

            self.proposal_canvases.append(canvas)
            self.proposal_labels.append(label)
            self.proposal_info_labels.append(info_label)
            self.proposal_locks.append(lock_var)
            self.proposal_lock_checks.append(lock_check)
            self.proposal_tooltips.append(tooltip)

        # Boutons action
        action_frame = ttk.Frame(left_panel)
        action_frame.pack(fill=tk.X, pady=2)

        ttk.Button(action_frame, text="🚀 Traiter tout", command=self.process_all).pack(
            side=tk.LEFT, padx=5, pady=2
        )
        ttk.Button(
            action_frame, text="✅ Traiter sélection", command=self.process_selected
        ).pack(side=tk.LEFT, padx=5, pady=2)
        tk.Button(
            action_frame,
            text="⛔ Interrompre",
            command=self.cancel_processing,
            fg="white",
            bg="#c00",
            activebackground="#e22",
            activeforeground="white",
            relief=tk.RAISED,
        ).pack(side=tk.LEFT, padx=5, pady=2)
        # v88 -- relecture d'un lot par score qualité
        review_btn = ttk.Button(action_frame, text="🔍 Revoir", command=self.open_review_window)
        review_btn.pack(side=tk.LEFT, padx=5, pady=2)
        add_help_tooltip(review_btn, "tooltip_review")

        # Configuration grille
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        content_frame.columnconfigure(0, weight=1)  # Gauche (liste)
        content_frame.columnconfigure(
            1, weight=3
        )  # Centre (previews + propositions IA)
        content_frame.rowconfigure(0, weight=1)

    def setup_manual_tab(self):
        """Configuration onglet MANUEL avec effets avancés"""
        main_frame = ttk.Frame(self.manual_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Split horizontal
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH)

        # LEFT: Edition
        toolbar = ttk.Frame(left_panel)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(toolbar, text="📂 Charger", command=self.load_manual_image).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(toolbar, text="✂️ Crop 128×32", command=self.start_crop_mode).pack(
            side=tk.LEFT, padx=2
        )
        # v103 -- zone où s'appliquent curseurs et filtres
        self.zone_btn = ttk.Button(toolbar, text=tr("t_zone_btn", "▭ Zone"), command=self.toggle_zone_mode)
        self.zone_btn.pack(side=tk.LEFT, padx=2)
        add_help_tooltip(self.zone_btn, "tooltip_zone")
        zc = ttk.Button(toolbar, text=tr("t_zone_clear_btn", "✕ Zone"), command=lambda: self._manual_zone_clear())
        zc.pack(side=tk.LEFT, padx=2)
        add_help_tooltip(zc, "tooltip_zone_clear")
        ttk.Button(toolbar, text="↶ Annuler", command=self.manual_undo).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(toolbar, text="↷ Rétablir", command=self.manual_redo).pack(
            side=tk.LEFT, padx=2
        )

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        ttk.Button(
            toolbar, text="📚 Multi-images", command=self.load_multiple_manual_images
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            toolbar, text="🎬 Morphing", command=self.generate_morphing_animation
        ).pack(side=tk.LEFT, padx=2)

        # Liste images multiples (sous toolbar)
        self.multi_images_frame = ttk.LabelFrame(
            left_panel, text="Images chargées (morphing)", padding="5"
        )
        self.multi_images_frame.pack(fill=tk.X, pady=(0, 10))
        self.multi_images_frame.pack_forget()  # Caché par défaut

        multi_list_container = ttk.Frame(self.multi_images_frame)
        multi_list_container.pack(fill=tk.BOTH, expand=True)

        self.multi_images_listbox = tk.Listbox(
            multi_list_container, height=4, selectmode=tk.SINGLE
        )
        self.multi_images_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.multi_images_listbox.bind("<<ListboxSelect>>", self.on_multi_image_select)

        multi_scroll = ttk.Scrollbar(
            multi_list_container,
            orient=tk.VERTICAL,
            command=self.multi_images_listbox.yview,
        )
        multi_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.multi_images_listbox.config(yscrollcommand=multi_scroll.set)

        multi_btn_frame = ttk.Frame(self.multi_images_frame)
        multi_btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(
            multi_btn_frame,
            text="🎬 Morphing",
            command=self.generate_morphing_animation,
            width=15,
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            multi_btn_frame,
            text="🗑️ Effacer",
            command=self.clear_multi_images,
            width=15,
        ).pack(side=tk.LEFT, padx=2)

        self.multi_images = []

        # Effets temps réel
        effects_frame = ttk.LabelFrame(
            left_panel, text="Effets Temps Réel", padding="5"
        )
        effects_frame.pack(fill=tk.X, pady=(0, 10))

        self.create_slider(
            effects_frame, "Luminosité:", 0.5, 2.0, 1.0, "manual_brightness"
        )
        self.create_slider(
            effects_frame, "Contraste:", 0.5, 3.0, 1.0, "manual_contrast"
        )
        self.create_slider(
            effects_frame, "Saturation:", 0.0, 2.0, 1.0, "manual_saturation"
        )
        self.create_slider(effects_frame, "Netteté:", 0.0, 3.0, 1.0, "manual_sharpness")

        # Filtres
        filters_frame = ttk.LabelFrame(left_panel, text="Filtres", padding="5")
        filters_frame.pack(fill=tk.X, pady=(0, 10))

        filters = [
            ["Flou", "Flou Gaussien", "Contours", "Relief", "Détails+"],
            ["Inverser", "Miroir H", "Miroir V", "Rotation 90°", "N&B"],
            ["Posteriser", "Solariser", "Égaliser", "Auto-contraste", ""],
        ]

        for row_filters in filters:
            row = ttk.Frame(filters_frame)
            row.pack(fill=tk.X, pady=2)
            for f in row_filters:
                if f:
                    ttk.Button(
                        row,
                        text=f,
                        width=15,
                        command=lambda x=f.lower().replace(" ", "_").replace(
                            "é", "e"
                        ).replace("°", ""): self.apply_filter(x),
                    ).pack(side=tk.LEFT, padx=2)

        # v99 -- zoom de l'animation (remplace Resize +/- : ils redimensionnaient
        # l'image de travail, sans effet sur le GIF puisque generate_manual_animation
        # recalcule la taille 128×32 d'après les proportions). Le zoom s'applique
        # APRÈS ce calcul : 100 % = rendu habituel. Réglage d'animation, hors
        # historique annuler/rétablir ; remis à 100 % à chaque nouvelle image.
        self.manual_zoom = 1.0
        self.manual_zoom_text = tk.StringVar(value=tr("t_manual_zoom", "Zoom : {p} %", p=100))
        zrow = ttk.Frame(filters_frame)
        zrow.pack(fill=tk.X, pady=2)
        for label, step in ((tr("t_manual_zoom_out", "🔍 Zoom −"), -1), (tr("t_manual_zoom_in", "🔍 Zoom +"), 1)):
            b = ttk.Button(zrow, text=label, width=15, command=lambda s=step: self.manual_zoom_step(s))
            b.pack(side=tk.LEFT, padx=2)
            add_help_tooltip(b, "tooltip_manual_zoom")
        ttk.Button(zrow, text="100 %", width=8, command=lambda: self.manual_zoom_step(0)).pack(side=tk.LEFT, padx=2)
        ttk.Label(zrow, textvariable=self.manual_zoom_text).pack(side=tk.LEFT, padx=8)

        # Outils dessin
        draw_frame = ttk.LabelFrame(left_panel, text="Outils Dessin", padding="5")
        draw_frame.pack(fill=tk.X, pady=(0, 10))

        draw_row1 = ttk.Frame(draw_frame)
        draw_row1.pack(fill=tk.X, pady=2)

        self.fill_btn = ttk.Button(
            draw_row1, text="🎨 Remplissage", command=self.toggle_fill_mode
        )
        self.fill_btn.pack(side=tk.LEFT, padx=2)

        self.eraser_btn = ttk.Button(
            draw_row1, text="🧹 Gomme Magique", command=self.toggle_eraser_mode
        )
        self.eraser_btn.pack(side=tk.LEFT, padx=2)

        ttk.Button(draw_row1, text="Couleur", command=self.choose_fill_color).pack(
            side=tk.LEFT, padx=2
        )

        self.color_preview = Canvas(draw_row1, width=30, height=20, bg="red")
        self.color_preview.pack(side=tk.LEFT, padx=5)

        draw_row2 = ttk.Frame(draw_frame)
        draw_row2.pack(fill=tk.X, pady=2)

        tolerance_label = ttk.Label(draw_row2, text="Tolérance:")
        tolerance_label.pack(side=tk.LEFT)
        add_help_tooltip(tolerance_label, "tooltip_tolerance")
        self.fill_tolerance = tk.IntVar(value=30)
        ttk.Spinbox(
            draw_row2, from_=0, to=100, textvariable=self.fill_tolerance, width=10
        ).pack(side=tk.LEFT, padx=5)

        ttk.Checkbutton(draw_row2, text="Fond noir", variable=tk.BooleanVar()).pack(
            side=tk.LEFT, padx=20
        )

        draw_row3 = ttk.Frame(draw_frame)
        draw_row3.pack(fill=tk.X, pady=2)

        # Case partagée avec l'onglet AUTO (self.pixel_perfect_var, créée dans
        # setup_auto_tab) : pilote à la fois le resize pixel-perfect de
        # generate_manual_animation et le rendu LED de animate_manual_preview.
        manual_pixel_perfect_check = ttk.Checkbutton(
            draw_row3,
            text="Mode DMD / Forcer pixel-perfect",
            variable=self.pixel_perfect_var,
            command=self.on_global_param_change,
        )
        manual_pixel_perfect_check.pack(side=tk.LEFT)
        add_help_tooltip(manual_pixel_perfect_check, "tooltip_pixel_perfect")

        # Canvas édition
        canvas_frame = ttk.LabelFrame(left_panel, text="Édition", padding="5")
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.manual_canvas = Canvas(
            canvas_frame, width=640, height=480, bg="black", cursor="crosshair"
        )
        self.manual_canvas.pack()
        self.manual_canvas.bind("<Button-1>", self.on_manual_click)

        self.manual_status = tk.StringVar(
            value=lang_manager.get("load_image_first", "Chargez une image")
        )
        ttk.Label(
            canvas_frame, textvariable=self.manual_status, font=("Arial", 9, "italic")
        ).pack(pady=5)

        # RIGHT: Preview animation

        preview_frame = ttk.LabelFrame(
            right_panel, text="Aperçu Animation DMD", padding="5"
        )
        preview_frame.pack(fill=tk.BOTH, expand=False)

        manual_preview_row = ttk.Frame(preview_frame)
        manual_preview_row.pack(pady=5)

        self.manual_preview_canvas = Canvas(
            manual_preview_row, width=512, height=128, bg="black"
        )
        self.manual_preview_canvas.pack(side=tk.LEFT)
        self._add_led_zoom_icon(
            self.manual_preview_canvas,
            get_frames=lambda: self.manual_frames,
            get_idx=lambda: self.manual_frame_idx,
            get_fps=lambda: self.manual_fps.get(),
            title="Aperçu Animation DMD (Manuel)",
        )
        self._add_led_brightness_slider(manual_preview_row).pack(
            side=tk.LEFT, padx=(10, 0)
        )

        # "Exporter GIF" déplacé ici depuis la barre d'outils du haut, à côté de
        # "Prévisualiser" (demandé explicitement) : les 2 actions liées à
        # l'animation de preview sont désormais regroupées sous son canvas,
        # cohérent avec TEXTSCROLL (même regroupement fait la même session).
        preview_btn_frame = ttk.Frame(preview_frame)
        preview_btn_frame.pack(pady=5)

        ttk.Button(
            preview_btn_frame,
            text="🎬 Prévisualiser",
            command=self.generate_manual_animation,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            preview_btn_frame, text="💾 Exporter GIF", command=self.manual_export
        ).pack(side=tk.LEFT, padx=5)

        self.manual_preview_status = tk.StringVar(
            value=lang_manager.get("click_preview", "Cliquez Prévisualiser")
        )
        ttk.Label(
            preview_frame,
            textvariable=self.manual_preview_status,
            font=("Arial", 9, "italic"),
        ).pack(pady=5)

        # Animations et paramètres regroupés
        anim_frame = ttk.LabelFrame(
            right_panel, text="Animations & Paramètres", padding="5"
        )
        anim_frame.pack(fill=tk.X, pady=(0, 10))

        # Type animation
        row1 = ttk.Frame(anim_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text="Animation:").pack(side=tk.LEFT)
        self.manual_anim_type = tk.StringVar(value="scroll")
        anim_types = [
            "scroll",
            "fade_in",
            "fade_out",
            "zoom_in",
            "zoom_out",
            "rotate",
            "wave",
            "bounce",
            "flash",
            "slide_left",
            "slide_right",
            "spiral",
            "shake",
            "pulse",
            "glitch",
            "pixelate",
            "blur_transition",
            "color_shift",
        ]
        ttk.Combobox(
            row1,
            textvariable=self.manual_anim_type,
            values=anim_types,
            state="readonly",
            width=15,
        ).pack(side=tk.LEFT, padx=5)

        # Direction (pour scroll)
        ttk.Label(row1, text="Direction:").pack(side=tk.LEFT, padx=(20, 5))
        self.manual_direction = tk.StringVar(value="horizontal")
        ttk.Combobox(
            row1,
            textvariable=self.manual_direction,
            values=["horizontal", "vertical"],
            state="readonly",
            width=12,
        ).pack(side=tk.LEFT)

        # Paramètres
        row2 = ttk.Frame(anim_frame)
        row2.pack(fill=tk.X, pady=2)

        ttk.Label(row2, text="FPS:").pack(side=tk.LEFT)
        self.manual_fps = tk.IntVar(value=config_manager.get("manual_fps", 10))
        self.manual_fps.trace_add(
            "write",
            lambda *args: _save_var("manual_fps", self.manual_fps),
        )
        ttk.Spinbox(row2, from_=1, to=60, textvariable=self.manual_fps, width=10).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Label(row2, text="Vitesse:").pack(side=tk.LEFT, padx=(20, 5))
        self.manual_scroll_speed = tk.IntVar(
            value=config_manager.get("manual_scroll_speed", 2)
        )
        self.manual_scroll_speed.trace_add(
            "write",
            lambda *args: _save_var("manual_scroll_speed", self.manual_scroll_speed),
        )
        ttk.Spinbox(
            row2, from_=1, to=10, textvariable=self.manual_scroll_speed, width=10
        ).pack(side=tk.LEFT)

        ttk.Label(row2, text="Durée (s):").pack(side=tk.LEFT, padx=(20, 5))
        self.manual_duration = tk.DoubleVar(
            value=config_manager.get("manual_duration", 2.0)
        )
        self.manual_duration.trace_add(
            "write",
            lambda *args: _save_var("manual_duration", self.manual_duration),
        )
        ttk.Spinbox(
            row2,
            from_=0.1,
            to=30,
            increment=0.1,
            textvariable=self.manual_duration,
            width=10,
        ).pack(side=tk.LEFT)
        # v101 -- aperçu refait après modification (vitesse toujours juste)
        for var in (self.manual_fps, self.manual_duration, self.manual_scroll_speed):
            var.trace_add("write", self._manual_schedule_regen)
        # Options boucle
        row3 = ttk.Frame(anim_frame)
        row3.pack(fill=tk.X, pady=2)

        loop_mode_label = ttk.Label(row3, text="Boucle:")
        loop_mode_label.pack(side=tk.LEFT)
        add_help_tooltip(loop_mode_label, "tooltip_loop_mode")
        self.manual_loop_mode = tk.StringVar(value="normal")
        ttk.Combobox(
            row3,
            textvariable=self.manual_loop_mode,
            values=["normal", "ping-pong", "infini"],
            state="readonly",
            width=12,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(row3, text="Répétitions:").pack(side=tk.LEFT, padx=(20, 5))
        self.manual_loop_count = tk.IntVar(value=1)
        ttk.Spinbox(
            row3, from_=1, to=10, textvariable=self.manual_loop_count, width=10
        ).pack(side=tk.LEFT)

        # Contrôles avancés
        advanced_frame = ttk.LabelFrame(
            anim_frame, text="⚙️ Contrôles Avancés", padding="5"
        )
        advanced_frame.pack(fill=tk.X, pady=(5, 0))

        adv_row1 = ttk.Frame(advanced_frame)
        adv_row1.pack(fill=tk.X, pady=2)

        easing_label = ttk.Label(adv_row1, text="Easing:")
        easing_label.pack(side=tk.LEFT)
        add_help_tooltip(easing_label, "tooltip_easing")
        self.manual_easing = tk.StringVar(value="linear")
        ttk.Combobox(
            adv_row1,
            textvariable=self.manual_easing,
            values=["linear", "ease-in", "ease-out", "ease-in-out", "bounce"],
            state="readonly",
            width=12,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(adv_row1, text="Délai début (s):").pack(side=tk.LEFT, padx=(20, 5))
        self.manual_delay_start = tk.DoubleVar(value=0.0)
        ttk.Spinbox(
            adv_row1,
            from_=0.0,
            to=5.0,
            increment=0.1,
            textvariable=self.manual_delay_start,
            width=8,
        ).pack(side=tk.LEFT)

        adv_row2 = ttk.Frame(advanced_frame)
        adv_row2.pack(fill=tk.X, pady=2)

        self.manual_reverse = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            adv_row2, text="Inverser direction", variable=self.manual_reverse
        ).pack(side=tk.LEFT, padx=5)

        self.manual_bounce_edges = tk.BooleanVar(value=False)
        bounce_edges_check = ttk.Checkbutton(
            adv_row2, text="Rebond aux bords", variable=self.manual_bounce_edges
        )
        bounce_edges_check.pack(side=tk.LEFT, padx=5)
        add_help_tooltip(bounce_edges_check, "tooltip_bounce_edges")

        ttk.Label(adv_row2, text="Opacité:").pack(side=tk.LEFT, padx=(20, 5))
        self.manual_opacity = tk.DoubleVar(value=1.0)
        ttk.Scale(
            adv_row2,
            from_=0.1,
            to=1.0,
            variable=self.manual_opacity,
            orient=tk.HORIZONTAL,
            length=100,
        ).pack(side=tk.LEFT)

        opacity_label = ttk.Label(adv_row2, text="100%", width=5)
        opacity_label.pack(side=tk.LEFT, padx=5)
        self.manual_opacity.trace_add(
            "write",
            lambda *args: opacity_label.config(
                text=f"{int(self.manual_opacity.get()*100)}%"
            ),
        )

        # INFO PANEL

        # Panneau informations image (bas droite, à côté de l'image DMD)
        info_image_frame = ttk.LabelFrame(
            right_panel,
            text=lang_manager.get("info_image", "ℹ️ Informations Image"),
            padding="5",
        )
        info_image_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.manual_info_text = tk.Text(
            info_image_frame,
            height=6,
            width=45,
            wrap=tk.WORD,
            state="disabled",
            font=("Courier", 9),
        )
        self.manual_info_text.pack(fill=tk.BOTH, expand=True)

    # ========================================================================
    # ONGLET VIDEO
    # ========================================================================

    def setup_video_tab(self):
        """Configuration onglet VIDEO : import vidéo, trim, zone d'intérêt
        (ROI) suivie automatiquement, preview LED/loupe/classique cohérente
        avec les 3 autres onglets, réglage qualité auto dédié, export GIF."""
        main_frame = ttk.Frame(self.video_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        if not CV2_AVAILABLE:
            ttk.Label(
                main_frame,
                text=lang_manager.get(
                    "video_no_cv2",
                    "⚠️ opencv-contrib-python non installé — pip install opencv-contrib-python",
                ),
                foreground="red",
                font=("Arial", 12, "bold"),
            ).pack(pady=60)
            return

        # Mise en page pleine largeur à une seule colonne (plus de séparation
        # gauche/droite, demande explicite du même tour) : une rangée du
        # haut à 4 colonnes (bouton+lecteur / infos source / paramètres GIF
        # / aperçu animation+infos GIF), puis Sélection (trim) et Zone
        # d'intérêt en PLEINE LARGEUR en dessous, synchronisée dynamiquement
        # avec la largeur réelle de la rangée du haut (voir
        # _video_sync_canvas_widths, lié à top_row.bind("<Configure>", ...)
        # en fin de méthode).
        # PAS de fill=tk.X ici, volontairement : ça étirerait top_row à la
        # largeur DISPONIBLE de main_frame (potentiellement bien plus large
        # que ses 4 colonnes une fois pleinement peuplées), et
        # top_row.winfo_width() — utilisé pour resynchroniser la largeur des
        # zones trim/ROI ci-dessous — refléterait alors cette largeur
        # étirée, PAS la largeur réellement occupée par le contenu visible
        # (bug réel trouvé par capture d'écran : vignettes de la frise
        # comprimées sur ~40% de la largeur avec un grand vide à droite).
        # Sans fill, top_row se limite exactement à la largeur de ses 4
        # colonnes (anchor="w" pour rester collé à gauche, comme le reste
        # de l'onglet, plutôt que centré par défaut).
        top_row = ttk.Frame(main_frame)
        top_row.pack(anchor="w", pady=(0, 10))

        # Sous-groupe colonnes 1-3 (bouton+lecteur / infos source /
        # paramètres GIF), séparé de la colonne 4 (aperçu animation) pour
        # que fill=Y sur les colonnes 2-3 ci-dessous s'étire exactement à la
        # hauteur de la colonne 1 (boutons de lecture), PAS à celle -
        # généralement plus grande - de la colonne 4. Sans ce sous-cadre,
        # pack calcule la hauteur de ligne de top_row sur son enfant le PLUS
        # HAUT parmi les 4 colonnes (souvent la colonne 4), et fill=Y
        # étirerait alors les colonnes 2-3 bien plus bas que le bas réel des
        # boutons de lecture - demande explicite "s'alignent sur le bas des
        # boutons de contrôle du playback", pas sur le bas de l'aperçu.
        row_left = ttk.Frame(top_row)
        row_left.pack(side=tk.LEFT, anchor="n")

        # Colonne 1 : bouton Charger, PUIS lecteur intégré empilé juste
        # dessous (demande explicite "déplace le cadre playback sous load
        # video"). Le bouton "Lire l'original" est supprimé : cliquer dans
        # le cadre de lecture ouvre désormais le lecteur Windows en taille
        # réelle (même action, déclenchée différemment).
        toolbar_buttons = ttk.Frame(row_left)
        toolbar_buttons.pack(side=tk.LEFT, anchor="n")
        ttk.Button(
            toolbar_buttons, text="📹 Charger Vidéo", command=self.load_video_file
        ).pack(anchor="w", pady=1)

        # Le StringVar video_status reste utilisé en interne (progression du
        # pipeline, etc.) mais n'est plus affiché sous "Charger Vidéo"
        # (demande explicite "supprime le texte sous load video" — l'info
        # équivalente est déjà visible dans le cadre "ℹ️ Vidéo Source").
        self.video_status = tk.StringVar(
            value=lang_manager.get("video_status_default", "Chargez une vidéo")
        )

        # Lecteur vidéo intégré : lecture en boucle en mode "resize" (frame
        # entière visible, letterboxée), démarrée après le chargement du
        # fichier (voir _video_on_thumbnails_ready). Clic dans le cadre =
        # lecture taille réelle dans le lecteur Windows par défaut
        # (os.startfile, reprend video_play_original). Boutons retour/
        # lecture/stop/avance sous le cadre.
        player_col = ttk.Frame(toolbar_buttons)
        player_col.pack(anchor="w", pady=(4, 0))
        ttk.Label(player_col, text="Lecture").pack(anchor="w")
        self.video_playback_canvas_w = 220
        self.video_playback_canvas_h = 140
        self.video_playback_canvas = Canvas(
            player_col,
            width=self.video_playback_canvas_w,
            height=self.video_playback_canvas_h,
            bg="black",
            cursor="hand2",
        )
        self.video_playback_canvas.pack()
        self.video_playback_canvas.bind(
            "<Button-1>", lambda e: self.video_play_original()
        )
        add_help_tooltip(self.video_playback_canvas, "tooltip_video_playback")

        player_btn_row = ttk.Frame(player_col)
        player_btn_row.pack(pady=(4, 0))
        ttk.Button(
            player_btn_row, text="⏪", width=3,
            command=lambda: self._video_playback_seek(-2.0),
        ).pack(side=tk.LEFT, padx=1)
        ttk.Button(
            player_btn_row, text="▶️", width=3, command=self._video_playback_play
        ).pack(side=tk.LEFT, padx=1)
        ttk.Button(
            player_btn_row, text="⏹️", width=3, command=self._video_playback_stop
        ).pack(side=tk.LEFT, padx=1)
        ttk.Button(
            player_btn_row, text="⏩", width=3,
            command=lambda: self._video_playback_seek(2.0),
        ).pack(side=tk.LEFT, padx=1)

        # Colonne 2 : infos vidéo source PUIS infos GIF à exporter empilées
        # dessous (demande explicite "réduit la hauteur de info source pour
        # placer en dessous info gif export" — remplace l'emplacement
        # précédent de "ℹ️ GIF à exporter" sous "Aperçu Animation" en colonne
        # 4, qui rendait cette colonne trop haute et masquait des éléments du
        # cadre ROI plus bas). Hauteur du Text source réduite à 6 (contenu
        # réel : Fichier/Résolution/Durée/FPS/Frames/Taille, voir
        # _video_update_source_info — plus de height=14 surdimensionné).
        # fill=Y appliqué au CONTENEUR col2 (pas à chaque cadre séparément)
        # pour que l'empilement reste top-aligné et s'étire globalement
        # comme la colonne 1 (boutons de lecture), tout en restant nettement
        # plus compact qu'avant (2 cadres de 6 lignes chacun plutôt qu'un
        # cadre étiré artificiellement + un 2e cadre ailleurs).
        col2 = ttk.Frame(row_left)
        col2.pack(side=tk.LEFT, padx=(10, 0), anchor="n", fill=tk.Y)

        source_info_frame = ttk.LabelFrame(
            col2, text="ℹ️ Vidéo Source", padding="5"
        )
        source_info_frame.pack(anchor="w", fill=tk.X)
        self.video_source_info_text = tk.Text(
            source_info_frame, height=6, width=56, wrap=tk.WORD, state="disabled",
            font=("Courier", 8),
        )
        self.video_source_info_text.pack(fill=tk.BOTH, expand=True)

        gif_info_frame = ttk.LabelFrame(
            col2, text="ℹ️ GIF à exporter", padding="5"
        )
        gif_info_frame.pack(anchor="w", fill=tk.X, pady=(10, 0))
        self.video_gif_info_text = tk.Text(
            gif_info_frame, height=6, width=56, wrap=tk.WORD, state="disabled",
            font=("Courier", 9),
        )
        self.video_gif_info_text.pack(fill=tk.BOTH, expand=True)

        # Colonne 3 : "Paramètres GIF Vidéo", déplacé ici depuis le bas du
        # panneau gauche — contenu inchangé. fill=Y (demande explicite
        # "augmente celle du cadre video gif settings") pour s'étirer comme
        # la colonne 2, au lieu de rester à sa hauteur naturelle (3 lignes
        # de contrôles, bien plus courte que la colonne 1).
        settings_frame = ttk.LabelFrame(
            row_left, text="Paramètres GIF Vidéo", padding="5"
        )
        settings_frame.pack(side=tk.LEFT, padx=(10, 0), anchor="n", fill=tk.Y)

        row1 = ttk.Frame(settings_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="FPS:").pack(side=tk.LEFT)
        self.video_fps.trace_add(
            "write",
            lambda *args: _save_var("video_fps", self.video_fps),
        )
        ttk.Spinbox(
            row1, from_=1, to=60, textvariable=self.video_fps, width=6
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(row1, text="Durée (s):").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Spinbox(
            row1,
            from_=0.1,
            to=9999,
            increment=0.1,
            textvariable=self.video_duration,
            width=6,
            command=self._video_on_duration_change,
        ).pack(side=tk.LEFT)

        ttk.Label(row1, text="Couleurs GIF:").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Combobox(
            row1,
            textvariable=self.color_count_var,
            values=[str(v) for v in (8, 16, 32, 64, 128, 256)],
            state="readonly",
            width=6,
        ).pack(side=tk.LEFT)

        row2 = ttk.Frame(settings_frame)
        row2.pack(fill=tk.X, pady=(6, 2))
        video_pixel_perfect_check = ttk.Checkbutton(
            row2,
            text="Mode DMD / Forcer pixel-perfect",
            variable=self.pixel_perfect_var,
            command=self.on_global_param_change,
        )
        video_pixel_perfect_check.pack(side=tk.LEFT, padx=(0, 20))
        add_help_tooltip(video_pixel_perfect_check, "tooltip_pixel_perfect")

        ttk.Checkbutton(
            row2, text="🪄 Qualité automatique", variable=self.video_quality_auto
        ).pack(side=tk.LEFT)

        row3 = ttk.Frame(settings_frame)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="Boucle:").pack(side=tk.LEFT)
        ttk.Combobox(
            row3,
            textvariable=self.manual_loop_mode,
            values=["normal", "ping-pong", "infini"],
            state="readonly",
            width=10,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Label(row3, text="Répétitions:").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Spinbox(
            row3, from_=1, to=10, textvariable=self.manual_loop_count, width=6
        ).pack(side=tk.LEFT)

        trim_frame = ttk.LabelFrame(main_frame, text="Sélection (trim)", padding="5")
        trim_frame.pack(fill=tk.X, pady=(0, 10))

        # Durée déplacée au-dessus de la frise (demande explicite) : la zone
        # sous la frise est désormais occupée par l'échelle de temps.
        self.video_trim_label_var = tk.StringVar(
            value=tr("t_trim_duration", "Durée : {span:.1f}s ({start:.1f}s → {end:.1f}s)", span=0.0, start=0.0, end=0.0)
        )
        ttk.Label(
            trim_frame, textvariable=self.video_trim_label_var, font=("Arial", 8)
        ).pack(anchor=tk.W)

        # Largeur initiale (resynchronisée dynamiquement sur la largeur
        # réelle de top_row juste après construction complète de l'onglet,
        # voir _video_sync_canvas_widths — demande explicite "agrandi les
        # zones sélection trim + roi pour les aligner en largeur avec la
        # partie haute de l'app"). Hauteur inchangée (100px, "plus de
        # visibilité"), vignettes extraites 40→60 pour rester dense.
        self.video_thumb_canvas_width = 900
        self.video_thumb_canvas_height = 100

        # Indicateur du temps de cadrage (triangle cyan SEUL, plus petit) —
        # déplacé au-dessus de la frise, au même niveau que "Durée:...",
        # pour éviter le chevauchement avec la timeline des points de zone/
        # zoom en dessous (demande explicite). Remplace l'ancien triangle
        # dessiné en haut de video_thumb_canvas (retiré, voir
        # _video_redraw_trim_handles) — la ligne cyan elle-même reste sur
        # video_thumb_canvas/video_ruler_canvas, seul le triangle change de
        # place. Largeur synchronisée comme les autres canvas de trim_frame.
        self.video_roi_time_indicator_height = 12
        self.video_roi_time_indicator_canvas = Canvas(
            trim_frame,
            width=self.video_thumb_canvas_width,
            height=self.video_roi_time_indicator_height,
            bg="#111111",
            highlightthickness=0,
        )
        self.video_roi_time_indicator_canvas.pack(anchor="w")
        self.video_roi_time_indicator_canvas.bind("<ButtonPress-1>", self._video_trim_press)
        self.video_roi_time_indicator_canvas.bind("<B1-Motion>", self._video_trim_drag)
        self.video_roi_time_indicator_canvas.bind("<ButtonRelease-1>", self._video_trim_release)
        add_help_tooltip(self.video_roi_time_indicator_canvas, "tooltip_video_roi_edit_time")

        self.video_thumb_canvas = Canvas(
            trim_frame,
            width=self.video_thumb_canvas_width,
            height=self.video_thumb_canvas_height,
            bg="#111111",
        )
        # PAS de fill=tk.X ici : un canvas Tk étiré par le geometry manager
        # ne notifie PAS son propre widget interne des nouvelles coordonnées
        # de dessin — TOUT le calcul de coordonnées (vignettes, poignées,
        # conversion clic->temps) utilise explicitement la constante
        # self.video_thumb_canvas_width, resynchronisée programmatiquement
        # via .configure(width=...) dans _video_sync_canvas_widths (pas par
        # fill=X, qui désynchroniserait visuellement les poignées de leur
        # vraie position temporelle — bug réel déjà trouvé par capture
        # d'écran). anchor="w" évite que le pack centre le canvas dans
        # trim_frame.
        self.video_thumb_canvas.pack(anchor="w")
        self.video_thumb_canvas.bind("<ButtonPress-1>", self._video_trim_press)
        self.video_thumb_canvas.bind("<B1-Motion>", self._video_trim_drag)
        self.video_thumb_canvas.bind("<ButtonRelease-1>", self._video_trim_release)
        self._video_trim_dragging = None

        # Échelle de temps (graduations) + triangles de poignée, sous la
        # frise (demande explicite) — PLACÉE AVANT la timeline des points de
        # zone/zoom ci-dessous (demande explicite "la timeline de temps avec
        # les triangles doit être au-dessus de celle des points", pour ne
        # pas les confondre visuellement). Seuls 2 marqueurs y dessinent
        # désormais un triangle (début/fin de trim, vert/rouge) — le
        # triangle cyan (temps de cadrage) est retiré d'ici, remplacé par
        # l'indicateur dédié au-dessus de la frise (voir
        # video_roi_time_indicator_canvas). Les lignes verticales des 3
        # marqueurs restent saisissables indifféremment depuis les 3 canvas
        # (mêmes handlers).
        # Hauteur réduite (34→28) en cohérence avec les triangles
        # rétrécis (voir _video_redraw_trim_triangles) — demande explicite
        # "réduit la hauteur de la timeline les contenant".
        self.video_ruler_canvas_height = 28
        self.video_ruler_canvas = Canvas(
            trim_frame,
            width=self.video_thumb_canvas_width,
            height=self.video_ruler_canvas_height,
            bg="#1a1a1a",
        )
        self.video_ruler_canvas.pack(anchor="w")
        self.video_ruler_canvas.bind("<ButtonPress-1>", self._video_trim_press)
        self.video_ruler_canvas.bind("<B1-Motion>", self._video_trim_drag)
        self.video_ruler_canvas.bind("<ButtonRelease-1>", self._video_trim_release)
        add_help_tooltip(self.video_thumb_canvas, "tooltip_video_roi_edit_time")
        add_help_tooltip(self.video_ruler_canvas, "tooltip_video_roi_edit_time")

        # Timeline graphique des points de zone/zoom (fonction phare, refonte
        # tracking) : bande fine dédiée, sous la règle de graduations
        # (demande explicite, voir commentaire ci-dessus) — demande
        # explicite "un affichage graphique des différentes actions posées
        # sur la timeline (icônes de début/fin de tracking et de zoom
        # reliées par une ligne)". PAS superposée sur les vignettes
        # elles-mêmes (nuirait à la lisibilité des deux, choix confirmé avec
        # l'utilisateur) — bande séparée, largeur synchronisée comme les
        # autres canvas de trim_frame (voir _video_sync_canvas_widths).
        self.video_events_canvas_height = 24
        self.video_events_canvas = Canvas(
            trim_frame,
            width=self.video_thumb_canvas_width,
            height=self.video_events_canvas_height,
            bg="#0a0a0a",
        )
        self.video_events_canvas.pack(anchor="w")
        self.video_events_canvas.bind("<ButtonPress-1>", self._video_event_press)
        self.video_events_canvas.bind("<B1-Motion>", self._video_event_drag)
        self.video_events_canvas.bind("<ButtonRelease-1>", self._video_event_release)
        self._video_event_dragging = None
        add_help_tooltip(self.video_events_canvas, "tooltip_video_events_timeline")

        roi_frame = ttk.LabelFrame(
            main_frame, text="Zone d'intérêt (cadrage vidéo)", padding="5"
        )
        roi_frame.pack(fill=tk.X, pady=(0, 10))

        roi_content = ttk.Frame(roi_frame)
        roi_content.pack(fill=tk.X)

        # Largeur FIXE (620, pas resynchronisée sur la largeur de la rangée
        # du haut, contrairement à la frise de trim) : demande explicite
        # "la prévisualisation dans ROI n'a pas d'intérêt à être aussi
        # large, reviens au cadrage pleine image" — un canvas aussi large
        # que top_row (~1500px+) letterboxait la vidéo source avec
        # d'énormes bandes noires de chaque côté sans rien apporter.
        self.video_roi_canvas_w = 620
        self.video_roi_canvas_h = 270
        self.video_roi_canvas = Canvas(
            roi_content,
            width=self.video_roi_canvas_w,
            height=self.video_roi_canvas_h,
            bg="black",
        )
        self.video_roi_canvas.pack(side=tk.LEFT)
        self.video_roi_canvas.bind("<ButtonPress-1>", self._video_roi_start)
        self.video_roi_canvas.bind("<B1-Motion>", self._video_roi_drag)
        self.video_roi_canvas.bind("<ButtonRelease-1>", self._video_roi_end)
        self._video_roi_drag_start = None
        self._video_roi_drag_mode = None
        self._video_roi_move_offset = (0, 0)
        add_help_tooltip(self.video_roi_canvas, "tooltip_video_roi")

        # Aperçu live du cadrage 128x32 obtenu (sur la frame de référence
        # seule) — mis à jour en continu pendant le dessin/déplacement du ROI,
        # pour que l'utilisateur voie immédiatement le résultat sans lancer le
        # pipeline complet multi-frames. Indispensable en mode manuel (sans
        # tracking), où c'est la SEULE prévisualisation du cadrage choisi.
        # fill=tk.Y (pas seulement anchor="n") : la colonne s'étire
        # désormais sur toute la hauteur de la rangée (dictée par le plus
        # grand sibling, video_roi_canvas, 270px) au lieu de rester à sa
        # hauteur naturelle — nécessaire pour que roi_history_frame
        # ci-dessous (fill=BOTH+expand) puisse effectivement descendre
        # jusqu'en bas, demande explicite "l'historique de cadrage mérite
        # d'être agrandi (alignement avec le bas du cadre à sa gauche)".
        crop_preview_col = ttk.Frame(roi_content)
        crop_preview_col.pack(side=tk.LEFT, padx=(10, 0), fill=tk.Y, anchor="n")
        ttk.Label(crop_preview_col, text="Aperçu du cadrage").pack(anchor="w")
        self.video_crop_preview_canvas = Canvas(
            crop_preview_col, width=256, height=64, bg="black"
        )
        self.video_crop_preview_canvas.pack(pady=(4, 0))

        # Historique de cadrage en texte (demande explicite : "un cadre avec
        # l'historique en texte dans le cadre roi") — empilé sous l'aperçu
        # du cadrage plutôt qu'en 3e colonne, pour ne pas élargir encore la
        # rangée (même largeur que le canvas d'aperçu ci-dessus, 256px).
        # Même pattern Text lecture seule que "ℹ️ Vidéo Source"/"ℹ️ GIF à
        # exporter", complété d'une barre de scroll verticale (absente
        # jusqu'ici) — demande explicite "avec une barre de scroll
        # verticale". fill=BOTH+expand=True (au lieu de fill=X) : le cadre
        # s'étire désormais vers le BAS pour occuper tout l'espace restant
        # dans crop_preview_col, alignant son bord inférieur sur celui de
        # video_roi_canvas à sa gauche — hauteur du Text volontairement
        # laissée à 6 lignes en repli minimal, la géométrie réelle vient du
        # fill/expand du conteneur.
        roi_history_frame = ttk.LabelFrame(
            crop_preview_col, text="📜 Historique de cadrage", padding="5"
        )
        roi_history_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        roi_history_text_row = ttk.Frame(roi_history_frame)
        roi_history_text_row.pack(fill=tk.BOTH, expand=True)
        self.video_roi_history_text = tk.Text(
            roi_history_text_row, height=6, width=32, wrap=tk.WORD, state="disabled",
            font=("Courier", 8),
        )
        self.video_roi_history_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        roi_history_scrollbar = ttk.Scrollbar(
            roi_history_text_row, orient=tk.VERTICAL, command=self.video_roi_history_text.yview,
        )
        roi_history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.video_roi_history_text.config(yscrollcommand=roi_history_scrollbar.set)

        # Zoom cadrage/redimensionnement : contrôle le compromis crop↔resize
        # ET le zoom numérique au-delà du crop serré — demande explicite
        # "-100% = resize seul, 0 = crop serré, +100% zoom". Échelle -1..1
        # (remplace l'ancienne 0..1) : -1=aucun crop (redimensionne la frame
        # entière, avec bandes noires si le ratio source diffère de 4:1) ↔
        # 0=crop serré au ratio 128:32 (comportement historique, nouveau
        # défaut) ↔ +1=cadre plus petit que le crop serré (zoom numérique,
        # sujet agrandi).
        zoom_row = ttk.Frame(roi_frame)
        zoom_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(zoom_row, text="Zoom cadrage:").pack(side=tk.LEFT)
        self.video_crop_zoom_scale = ttk.Scale(
            zoom_row,
            from_=-1.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.video_crop_zoom,
            length=200,
        )
        self.video_crop_zoom_scale.pack(side=tk.LEFT, padx=5)
        # Valeur numérique affichée en direct à côté du curseur (demande
        # explicite "rajoute la valeur de zoom du slide") — mise à jour
        # dans _video_on_zoom_change, seul point d'entrée déjà appelé à
        # chaque changement de video_crop_zoom.
        self.video_crop_zoom_value_var = tk.StringVar(value="0%")
        ttk.Label(
            zoom_row, textvariable=self.video_crop_zoom_value_var, width=5,
            font=("Arial", 8, "bold"),
        ).pack(side=tk.LEFT)
        ttk.Label(
            zoom_row,
            text="(-100% = resize seul, 0 = crop serré, +100% = zoom)",
            font=("Arial", 8),
        ).pack(side=tk.LEFT)
        # `video_crop_zoom_scale` est grisé/dégrisé selon le mode de
        # cadrage choisi (voir le groupe de boutons radio plus bas et
        # _video_on_resize_auto_toggle) : actif uniquement en mode "Manuel".
        self.video_crop_zoom.trace_add("write", self._video_on_zoom_change)

        # Édition des points de zone/zoom sur la timeline (fonction phare de
        # l'onglet — refonte demandée explicitement : plusieurs zones auto/
        # manuelles peuvent se succéder, zoom keyframé indépendamment) —
        # UNIQUEMENT en mode "Manuel" du sélecteur "Mode de cadrage" ci-
        # dessous. Les boutons de gestion des points (Point ici/Zoom ici/
        # Supprimer ce point/Effacer points/Annuler/Rétablir) sont donc
        # grisés dans les modes "Suivi automatique"/"Cadrage auto" — activés
        # uniquement en "Manuel" (voir _video_on_crop_mode_change, qui
        # bascule leur état). "🔄 Recentrer" reste toujours actif (triple
        # comportement selon le mode, voir _video_roi_reset).
        #
        # Undo/redo (même pattern que l'onglet MANUEL) + statut récapitulatif
        # DANS la même rangée (pas une 2e ligne séparée) : une rangée
        # supplémentaire faisait dépasser la hauteur FIXE du Notebook de
        # quelques pixels, ce qui la faisait passer totalement inaperçue
        # (pack() ne mappe pas du tout un widget qui ne tient plus dans
        # l'espace restant — bug réel constaté par capture d'écran ET
        # diagnostic winfo_ismapped()==0, PAS juste "rogné").
        roi_btn_row = ttk.Frame(roi_frame)
        roi_btn_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(
            roi_btn_row, text="🔄 Recentrer", command=self._video_roi_reset
        ).pack(side=tk.LEFT)
        self.roi_add_point_btn = ttk.Button(
            roi_btn_row, text="➕ Point ici", command=self._video_add_roi_point
        )
        self.roi_add_point_btn.pack(side=tk.LEFT, padx=(5, 0))
        add_help_tooltip(self.roi_add_point_btn, "tooltip_video_add_roi_point")
        self.roi_add_zoom_btn = ttk.Button(
            roi_btn_row, text="🔍 Zoom ici", command=self._video_add_zoom_point
        )
        self.roi_add_zoom_btn.pack(side=tk.LEFT, padx=(5, 0))
        add_help_tooltip(self.roi_add_zoom_btn, "tooltip_video_add_zoom_point")
        self.roi_delete_point_btn = ttk.Button(
            roi_btn_row, text="🗑️ Supprimer ce point", command=self._video_delete_nearest_point
        )
        self.roi_delete_point_btn.pack(side=tk.LEFT, padx=(5, 0))
        add_help_tooltip(self.roi_delete_point_btn, "tooltip_video_delete_roi_point")
        self.roi_clear_points_btn = ttk.Button(
            roi_btn_row, text="🗑️ Effacer points", command=self._video_clear_roi_keyframes
        )
        self.roi_clear_points_btn.pack(side=tk.LEFT, padx=(5, 0))
        self.roi_undo_btn = ttk.Button(
            roi_btn_row, text="↶ Annuler", command=self._video_roi_undo
        )
        self.roi_undo_btn.pack(side=tk.LEFT, padx=(5, 0))
        self.roi_redo_btn = ttk.Button(
            roi_btn_row, text="↷ Rétablir", command=self._video_roi_redo
        )
        self.roi_redo_btn.pack(side=tk.LEFT, padx=(5, 0))

        # Sélecteur "Mode de cadrage" à 3 boutons radio, mutuellement
        # exclusifs PAR CONSTRUCTION — remplace les 2 anciennes cases
        # indépendantes "Suivi automatique"/"Resize auto" et leur logique de
        # forçage/grisage croisé, jugée peu lisible (demande explicite
        # utilisateur "le mode zoom auto et tracking auto s'excluent l'un
        # l'autre... peut-être clarifier ce fonctionnement ? [...] fait moi
        # des propositions", 3 options soumises via AskUserQuestion, celle-
        # ci choisie car chaque libellé porte à lui seul le sens complet du
        # mode et rend une combinaison incohérente impossible à exprimer
        # dans l'UI). Voir _video_on_crop_mode_change pour le détail des 3
        # modes.
        ttk.Label(roi_btn_row, text="Mode de cadrage :").pack(side=tk.LEFT, padx=(15, 0))
        self.video_crop_mode_tracking_radio = ttk.Radiobutton(
            roi_btn_row,
            text="🎯 Suivi automatique",
            variable=self.video_crop_mode,
            value="tracking",
            command=self._video_on_crop_mode_change,
        )
        self.video_crop_mode_tracking_radio.pack(side=tk.LEFT, padx=(5, 0))
        add_help_tooltip(self.video_crop_mode_tracking_radio, "tooltip_video_crop_mode_tracking")
        self.video_crop_mode_auto_zoom_radio = ttk.Radiobutton(
            roi_btn_row,
            text="🪄 Cadrage auto (zoom)",
            variable=self.video_crop_mode,
            value="auto_zoom",
            command=self._video_on_crop_mode_change,
        )
        self.video_crop_mode_auto_zoom_radio.pack(side=tk.LEFT, padx=(5, 0))
        add_help_tooltip(self.video_crop_mode_auto_zoom_radio, "tooltip_video_crop_mode_auto_zoom")
        self.video_crop_mode_manual_radio = ttk.Radiobutton(
            roi_btn_row,
            text="✋ Manuel",
            variable=self.video_crop_mode,
            value="manual",
            command=self._video_on_crop_mode_change,
        )
        self.video_crop_mode_manual_radio.pack(side=tk.LEFT, padx=(5, 0))
        add_help_tooltip(self.video_crop_mode_manual_radio, "tooltip_video_crop_mode_manual")

        # État initial cohérent avec le mode par défaut ("tracking") :
        # _video_on_crop_mode_change est entièrement sûre à appeler avant
        # tout chargement de vidéo (chaque étape qu'elle déclenche est déjà
        # gardée contre video_ref_frame/video_meta absents — canvases videos
        # ou listes vides restent des no-op), donc appelée directement ici
        # plutôt que dupliquer sa logique comme le faisait l'ancien forçage
        # manuel (case à cocher séparée, dépréciée).
        self._video_on_crop_mode_change()

        self.video_roi_keyframes_status_var = tk.StringVar(value="")
        ttk.Label(
            roi_btn_row, textvariable=self.video_roi_keyframes_status_var,
            font=("Arial", 8, "italic"),
        ).pack(side=tk.LEFT, padx=(15, 0))

        # Colonne 4 : aperçu animation, MONTÉE à côté de "Paramètres GIF
        # Vidéo" dans la rangée du haut ("ℹ️ GIF à exporter" déplacé en
        # colonne 2 depuis v55, ne fait plus partie de cette colonne).
        # Preview = 4e copie du pattern LED/loupe/classique déjà utilisé par
        # les 3 autres onglets de génération.
        # fill=Y + preview_frame en fill=BOTH/expand : le cadre s'étire
        # désormais vers le BAS jusqu'à la hauteur de row_left (colonnes 1-3,
        # généralement plus hautes maintenant que "Paramètres GIF Vidéo" est
        # étiré sur toute la hauteur de col2) au lieu de rester à sa hauteur
        # naturelle plus courte — demande explicite "aligne le cadre
        # animation preview sur le cadre video gif settings (agrandir vers
        # le bas)".
        preview_col = ttk.Frame(top_row)
        preview_col.pack(side=tk.LEFT, padx=(10, 0), anchor="n", fill=tk.Y)

        preview_frame = ttk.LabelFrame(
            preview_col, text="Aperçu Animation (Vidéo)", padding="5"
        )
        preview_frame.pack(fill=tk.BOTH, expand=True)

        video_preview_row = ttk.Frame(preview_frame)
        video_preview_row.pack(pady=5)

        self.video_preview_canvas = Canvas(
            video_preview_row, width=512, height=128, bg="black"
        )
        self.video_preview_canvas.pack(side=tk.LEFT)
        self._add_led_zoom_icon(
            self.video_preview_canvas,
            get_frames=lambda: self.video_frames,
            get_idx=lambda: self.video_frame_idx,
            get_fps=lambda: self.video_fps.get(),
            title="Aperçu Animation (Vidéo)",
        )
        self._add_led_brightness_slider(video_preview_row).pack(
            side=tk.LEFT, padx=(10, 0)
        )

        # Générer Aperçu + Exporter GIF côte à côte (demande explicite) : les
        # 2 actions du flux "générer puis exporter" regroupées ensemble sous
        # la preview, plutôt que Générer Aperçu isolé dans le panneau gauche.
        video_action_row = ttk.Frame(preview_frame)
        video_action_row.pack(pady=(10, 0))
        ttk.Button(
            video_action_row, text="🎬 Générer Aperçu", command=self.generate_video_preview
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            video_action_row, text="💾 Exporter GIF", command=self.video_export
        ).pack(side=tk.LEFT, padx=2)

        # "ℹ️ GIF à exporter" déplacé en colonne 2 (sous "ℹ️ Vidéo Source",
        # voir col2 plus haut) — remplace son ancien emplacement ici, qui
        # rendait cette colonne trop haute et masquait des éléments du cadre
        # ROI plus bas (demande explicite).

        # Traces : tout réglage qui change ce que produirait un export
        # rafraîchit l'estimation en direct (variables partagées avec
        # d'autres onglets — s'ajoute aux traces déjà existantes ailleurs,
        # sans les remplacer).
        self.video_fps.trace_add("write", self._video_update_gif_info)
        self.video_trim_start.trace_add("write", self._video_update_gif_info)
        self.video_trim_end.trace_add("write", self._video_update_gif_info)
        self.color_count_var.trace_add("write", self._video_update_gif_info)
        self.manual_loop_mode.trace_add("write", self._video_update_gif_info)
        self.manual_loop_count.trace_add("write", self._video_update_gif_info)
        self._video_update_gif_info()
        self._video_update_source_info()

        def _video_sync_canvas_widths(event=None):
            """Resynchronise la largeur de la frise de trim/échelle de temps
            sur la largeur réellement rendue de top_row — demande explicite
            "agrandi les zones sélection trim ... pour les aligner en
            largeur avec la partie haute de l'app". Lié au Configure de
            top_row (se redéclenche à chaque redimensionnement réel, pas
            seulement au premier rendu).

            Le canvas ROI n'est PLUS concerné par cette resynchronisation
            (retiré, demande explicite "la prévisualisation dans ROI n'a pas
            d'intérêt à être aussi large, reviens au cadrage pleine image")
            — reste à sa largeur fixe (video_roi_canvas_w=620, voir
            construction de roi_content). Ce retrait corrige aussi un effet
            de bord réel : `_video_display_ref_frame()` était appelée ici à
            CHAQUE Configure de top_row, y compris ceux déclenchés par la
            mise à jour du texte "ℹ️ GIF à exporter" pendant un glissé de
            trim (trace sur video_trim_start/end, cadre maintenant imbriqué
            dans row_left/col2 depuis v55, donc son changement de taille se
            propage en Configure jusqu'à top_row) — un redessin du canvas
            ROI intercalé au mauvais moment pendant le glissé pouvait faire
            disparaître l'image affichée ("le problème de l'image qui ne
            reste pas lors du déplacement du trim est revenu", signalé par
            l'utilisateur). En ne touchant plus jamais au canvas ROI depuis
            ce callback, cette cascade n'a plus prise dessus."""
            new_w = top_row.winfo_width()
            if new_w <= 300 or new_w == self.video_thumb_canvas_width:
                return
            self.video_thumb_canvas_width = new_w
            self.video_thumb_canvas.configure(width=new_w)
            self.video_events_canvas.configure(width=new_w)
            self.video_ruler_canvas.configure(width=new_w)
            self.video_roi_time_indicator_canvas.configure(width=new_w)
            self._video_draw_thumbnails()
            self._video_redraw_roi_events()
            self._video_redraw_roi_time_indicator()

        top_row.bind("<Configure>", _video_sync_canvas_widths)

    def _video_update_source_info(self):
        """Rafraîchit le cadre "ℹ️ Vidéo Source" (même pattern Text lecture-
        seule que update_image_info en AUTO) : nom de fichier, résolution,
        durée, fps natif, nombre de frames total, taille disque."""
        if not hasattr(self, "video_source_info_text"):
            return
        if not self.video_path or not self.video_meta:
            info = "Aucune vidéo chargée"
        else:
            meta = self.video_meta
            try:
                file_size_kb = Path(self.video_path).stat().st_size / 1024
                size_str = (
                    f"{file_size_kb:.0f} Ko"
                    if file_size_kb < 1024
                    else f"{file_size_kb / 1024:.1f} Mo"
                )
            except OSError:
                size_str = "?"
            info = tr(
                "t_video_source_info", K_DEFAULT_VIDEO_SOURCE_INFO,
                name=Path(self.video_path).name, w=meta["width"], h=meta["height"],
                dur=meta["duration"], fps=meta["fps"], frames=meta["frame_count"], size=size_str,
            )
        self.video_source_info_text.config(state="normal")
        self.video_source_info_text.delete(1.0, tk.END)
        self.video_source_info_text.insert(1.0, info)
        self.video_source_info_text.config(state="disabled")

    def _video_update_gif_info(self, *_args):
        """Rafraîchit le cadre "ℹ️ GIF à exporter" : dimensions (toujours
        128×32), FPS, nombre de frames, couleurs et boucle réglés
        actuellement, poids. Le nombre de frames et le poids sont exacts
        après une génération réelle (self.video_frames rempli par
        _video_pipeline) ; avant ça, le nombre de frames est juste une
        estimation dérivée de fps×durée et le poids reste "—". Appelé en
        direct à chaque changement de réglage pertinent (traces sur
        video_fps/trim/color_count_var/manual_loop_*, voir setup_video_tab)
        — *_args absorbe les 3 arguments positionnels (name, index, mode)
        que Tkinter passe aux callbacks de trace_add, jamais utilisés ici."""
        if not hasattr(self, "video_gif_info_text"):
            return
        try:
            fps = self.video_fps.get()
        except Exception:
            fps = 0

        if self.video_frames:
            frames_label = str(len(self.video_frames))
        else:
            span = 0.0
            if self.video_meta:
                span = max(0.0, self.video_trim_end.get() - self.video_trim_start.get())
            n_frames = max(1, round(fps * span)) if span > 0 and fps > 0 else 0
            frames_label = tr("t_frames_estimated", "{n} (estimé)", n=n_frames)

        loop_mode = self.manual_loop_mode.get()
        loop_label = (
            tr("t_loop_infinite", "Infinie")
            if loop_mode == "infini"
            else f"{self.manual_loop_count.get()}x ({loop_mode})"
        )

        info = tr(
            "t_video_gif_info", K_DEFAULT_VIDEO_GIF_INFO,
            fps=fps, frames=frames_label, colors=self.color_count_var.get(),
            loop=loop_label, size=self.video_gif_size_var.get(),
        )
        self.video_gif_info_text.config(state="normal")
        self.video_gif_info_text.delete(1.0, tk.END)
        self.video_gif_info_text.insert(1.0, info)
        self.video_gif_info_text.config(state="disabled")

    def video_play_original(self):
        """Clic dans le cadre "Lecture" : lance la vidéo source dans le
        lecteur par défaut du système, en taille réelle (même mécanisme que
        clear_progress_and_notify pour ouvrir un dossier — os.startfile)
        plutôt que de réimplémenter un lecteur vidéo plein écran dans
        Tkinter. Anciennement un bouton dédié "▶️ Lire l'original", retiré au
        profit de ce clic direct dans l'aperçu (demande explicite)."""
        if not self.video_path:
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"),
                lang_manager.get("video_load_first_warning", "Chargez d'abord une vidéo"),
            )
            return
        try:
            os.startfile(self.video_path)  # type: ignore[attr-defined]
            logger.info(f"Lecture vidéo originale: {Path(self.video_path).name}")
        except Exception as e:
            messagebox.showerror(
                lang_manager.get("error", "Erreur"),
                f"{lang_manager.get('err_playback_launch', 'Impossible de lancer la lecture')}: {e}",
            )
            logger.error(f"Erreur lecture vidéo originale: {e}")

    def _video_playback_open(self, path):
        """Ouvre `path` pour la lecture en boucle dans le cadre "Lecture"
        intégré, démarrée IMMÉDIATEMENT après sélection du fichier (demande
        explicite). Referme d'abord toute lecture en cours."""
        self._video_playback_stop_capture()
        if not CV2_AVAILABLE:
            return
        try:
            self._video_playback_cap = VideoEngine.open_capture(path)
        except Exception as e:
            logger.error(f"Erreur ouverture lecteur vidéo intégré: {e}")
            self._video_playback_cap = None
            return
        fps = self.video_meta["fps"] if self.video_meta else 25.0
        self._video_playback_delay_ms = max(20, int(1000 / min(max(fps, 1.0), 30.0)))
        self.video_playback_playing = True
        self._video_playback_tick()

    def _video_playback_tick(self):
        """Boucle de lecture (root.after successifs, thread principal — le
        seek/décodage cv2 d'une frame de preview est rapide, un thread
        séparé ajouterait de la complexité de synchronisation avec le canvas
        Tkinter sans bénéfice net ici). Boucle automatiquement en fin de
        flux (voir VideoEngine.read_capture_frame)."""
        if not self.video_playback_playing or self._video_playback_cap is None:
            return
        frame = VideoEngine.read_capture_frame(self._video_playback_cap)
        if frame is not None:
            self._video_playback_show_frame(frame)
        self.root.after(self._video_playback_delay_ms, self._video_playback_tick)

    def _video_playback_show_frame(self, frame):
        """Affiche `frame` dans video_playback_canvas en mode "resize"
        (frame entière visible, letterboxée si le ratio diffère — PAS de
        crop, demande explicite "diffuser la vidéo source en mode resize")."""
        canvas = self.video_playback_canvas
        cw, ch = self.video_playback_canvas_w, self.video_playback_canvas_h
        scale = min(cw / frame.width, ch / frame.height)
        disp_w, disp_h = max(1, int(frame.width * scale)), max(1, int(frame.height * scale))
        disp = frame.resize((disp_w, disp_h), Image.Resampling.NEAREST)
        self._video_playback_photo = ImageTk.PhotoImage(disp)
        canvas.delete("all")
        canvas.create_image(cw // 2, ch // 2, image=self._video_playback_photo)

    def _video_playback_play(self):
        """Bouton "▶️" : (re)démarre la lecture en boucle. Si aucun flux
        n'est ouvert (lecture arrêtée puis vidéo rechargée entre-temps),
        rouvre le fichier courant."""
        if not self.video_path:
            return
        if self._video_playback_cap is None:
            self._video_playback_open(self.video_path)
            return
        if not self.video_playback_playing:
            self.video_playback_playing = True
            self._video_playback_tick()

    def _video_playback_stop(self):
        """Bouton "⏹️" : met en pause la lecture en boucle (garde la
        position courante affichée plutôt qu'un retour au début — plus utile
        pour examiner une frame précise en contexte de prévisualisation)."""
        self.video_playback_playing = False

    def _video_playback_seek(self, delta_seconds):
        """Boutons "⏪"/"⏩" : avance/recule de `delta_seconds` dans le flux
        de lecture intégré. Fonctionne aussi en pause (affiche immédiatement
        la frame à la nouvelle position)."""
        if self._video_playback_cap is None:
            return
        current_ms = VideoEngine.capture_position_ms(self._video_playback_cap)
        VideoEngine.seek_capture(self._video_playback_cap, current_ms + delta_seconds * 1000.0)
        if not self.video_playback_playing:
            frame = VideoEngine.read_capture_frame(self._video_playback_cap)
            if frame is not None:
                self._video_playback_show_frame(frame)

    def _video_playback_stop_capture(self):
        """Libère proprement le VideoCapture du lecteur intégré (nouveau
        chargement de vidéo, ou fermeture de l'app) — évite de fuir un
        descripteur de fichier ouvert."""
        self.video_playback_playing = False
        if self._video_playback_cap is not None:
            VideoEngine.release_capture(self._video_playback_cap)
            self._video_playback_cap = None

    def load_video_file(self):
        """Ouvre le sélecteur de fichier vidéo (bouton "📹 Charger Vidéo")."""
        if not CV2_AVAILABLE:
            messagebox.showerror(
                lang_manager.get("error", "Erreur"),
                lang_manager.get("video_no_cv2", "opencv-contrib-python non installé"),
            )
            return
        path = filedialog.askopenfilename(
            title=tr("t_select_video", "Sélectionner une vidéo"),
            filetypes=[(tr("t_videos", "Vidéos"), " ".join("*" + e for e in VIDEO_EXTS))],
        )
        if path:
            self._video_load_from_path(path)

    def _video_load_from_path(self, path):
        """Charge un fichier vidéo (bouton ou glisser-déposer) : sonde ses
        métadonnées, réinitialise trim/ROI/aperçu, puis extrait vignettes et
        frame de référence en thread (probe_video peut être lent sur de gros
        fichiers)."""
        if not CV2_AVAILABLE:
            messagebox.showerror(
                lang_manager.get("error", "Erreur"),
                lang_manager.get("video_no_cv2", "opencv-contrib-python non installé"),
            )
            return
        try:
            meta = VideoEngine.probe_video(path)
        except Exception as e:
            messagebox.showerror(lang_manager.get("error", "Erreur"), str(e))
            logger.error(f"Erreur ouverture vidéo {path}: {e}")
            return

        self.video_path = path
        self.video_meta = meta
        self.video_trim_start.set(0.0)
        # Par défaut : toute la vidéo source (durée + fps), demande explicite
        # de l'utilisateur — plus de plafond artificiel à 10s ici, l'utilisateur
        # règle librement via le nouveau champ "Durée (s)".
        self.video_trim_end.set(meta["duration"] if meta["duration"] > 0 else 0.0)
        self.video_duration.set(round(meta["duration"], 1) if meta["duration"] > 0 else 0.0)
        self.video_fps.set(max(1, min(60, round(meta["fps"]))))
        self.video_roi = None
        self._video_awaiting_point_draw = False
        self.video_roi_events = []
        self.video_zoom_keyframes = []
        self.video_roi_history = []
        self.video_roi_history_index = -1
        self._video_commit_roi_history()
        self.video_roi_edit_time.set(0.0)
        self._video_clamp_roi_edit_time()
        self._video_update_keyframes_status()
        self._video_redraw_roi_events()
        self._video_update_roi_history_text()
        self.video_frames = []
        self.video_animating = False
        self.video_gif_size_var.set("—")
        self.video_status.set(
            f"{Path(path).name} — {meta['duration']:.1f}s @ {meta['fps']:.0f}fps"
        )
        self._video_update_source_info()
        self._video_update_gif_info()
        logger.info(f"Vidéo chargée: {Path(path).name} ({meta['duration']:.1f}s)")

        # video_trim_start.get() lu ICI (thread principal), pas dans le thread
        # d'extraction : lire une tk.Variable depuis un thread worker n'est pas
        # une opération garantie thread-safe par Tkinter (accès direct à
        # l'interpréteur Tcl) — la valeur ne change de toute façon pas pendant
        # cette extraction, capturer une copie évite le risque sans rien coûter.
        trim_start = self.video_trim_start.get()
        threading.Thread(
            target=self._video_load_thumbnails_and_ref, args=(trim_start,), daemon=True
        ).start()

    def _video_load_thumbnails_and_ref(self, trim_start):
        """Thread: extrait la frise de vignettes + la frame de référence
        (timestamp = début du trim, capturé sur le thread principal avant le
        démarrage du thread), puis renvoie sur le thread UI."""
        try:
            thumbs = VideoEngine.extract_thumbnails(self.video_path, count=60)
            ref = VideoEngine.extract_reference_frame(self.video_path, trim_start)
        except Exception as e:
            # "as e" est effacée à la sortie du except (comportement standard
            # Python) — capturer le message AVANT de le référencer dans une
            # lambda différée via root.after, sinon NameError au moment où le
            # callback s'exécute réellement (bug confirmé en test réel).
            error_msg = str(e)
            self.root.after(
                0,
                lambda msg=error_msg: messagebox.showerror(lang_manager.get("error", "Erreur"), msg),
            )
            return
        self.root.after(0, lambda: self._video_on_thumbnails_ready(thumbs, ref))

    def _video_on_thumbnails_ready(self, thumbs, ref):
        self._video_thumb_pil = thumbs
        self._video_draw_thumbnails()
        self.video_ref_frame = ref
        self._video_display_ref_frame()
        # Lecture en boucle démarrée ici (pas plus tôt dans
        # _video_load_from_path) : DOIT attendre que le thread d'extraction
        # des vignettes/référence soit terminé, sinon son cv2.VideoCapture
        # tournerait en parallèle du VideoCapture persistant de la lecture
        # intégrée sur le MÊME fichier — même cause que le bug corrigé dans
        # _video_trim_release (v52, "l'image disparaît dans ROI"). Toujours
        # perçu comme quasi immédiat en pratique (l'extraction prend
        # généralement moins d'une seconde).
        self._video_playback_open(self.video_path)

    def _video_draw_thumbnails(self):
        """Dessine la frise de vignettes côte à côte sur toute la largeur du
        canvas, puis les poignées de trim par-dessus."""
        canvas = self.video_thumb_canvas
        canvas.delete("all")
        thumbs = getattr(self, "_video_thumb_pil", [])
        if not thumbs:
            return
        w, h = self.video_thumb_canvas_width, self.video_thumb_canvas_height
        slot_w = w / len(thumbs)
        self._video_thumb_photos = []
        for i, thumb in enumerate(thumbs):
            scale = h / thumb.height
            disp_w = max(1, int(thumb.width * scale))
            disp = thumb.resize((disp_w, h), Image.Resampling.NEAREST)
            photo = ImageTk.PhotoImage(disp)
            self._video_thumb_photos.append(photo)
            canvas.create_image(int(i * slot_w), 0, image=photo, anchor="nw")
        self._video_draw_time_ruler_ticks()
        self._video_redraw_trim_handles()

    def _video_draw_time_ruler_ticks(self):
        """Dessine les graduations temporelles (traits + libellés "Xs") sur
        video_ruler_canvas, UNE SEULE FOIS par vidéo chargée (la durée ne
        change pas pendant la session) — contrairement aux triangles de
        poignée, redessinés à chaque glissé via _video_redraw_trim_triangles.
        Intervalle choisi parmi une liste de valeurs "rondes" pour obtenir
        environ 8-12 graduations quelle que soit la durée."""
        canvas = self.video_ruler_canvas
        canvas.delete("ruler_tick")
        duration = self.video_meta["duration"] if self.video_meta else 0.0
        if duration <= 0:
            return
        w = self.video_thumb_canvas_width
        nice_steps = [0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600]
        step = next((s for s in nice_steps if duration / s <= 12), nice_steps[-1])
        t = 0.0
        while t <= duration + 1e-6:
            x = int((t / duration) * w)
            canvas.create_line(x, 0, x, 6, fill="#888888", tags="ruler_tick")
            canvas.create_text(
                x, 8, text=f"{t:g}s", fill="#aaaaaa", font=("Arial", 7),
                anchor="n", tags="ruler_tick",
            )
            t += step

    def _video_redraw_trim_handles(self):
        """Redessine les 3 marqueurs (lignes verticales) + la zone
        sélectionnée (bande semi-transparente) sur video_thumb_canvas, et met
        à jour le label de durée. 3 marqueurs : début/fin de trim (vert/
        rouge) ET temps de cadrage (cyan) — SIMPLE LIGNE pour les 3
        (l'ancien triangle cyan en haut de ce canvas est retiré, demande
        explicite "remplacer le triangle cyan par une simple ligne cyan" —
        le triangle du temps de cadrage vit désormais uniquement dans
        video_roi_time_indicator_canvas, voir _video_redraw_roi_time_indicator,
        pour éviter le chevauchement avec la timeline des points en
        dessous)."""
        canvas = self.video_thumb_canvas
        canvas.delete("trim_handle")
        duration = self.video_meta["duration"] if self.video_meta else 0.0
        if duration <= 0:
            return
        w, h = self.video_thumb_canvas_width, self.video_thumb_canvas_height
        x_start = int((self.video_trim_start.get() / duration) * w)
        x_end = int((self.video_trim_end.get() / duration) * w)
        x_roi = int((self.video_roi_edit_time.get() / duration) * w)
        canvas.create_rectangle(
            x_start, 0, x_end, h, outline="", fill="#3388ff", stipple="gray25",
            tags="trim_handle",
        )
        # Les LIGNES de poignée sont clampées à 2px des bords (moitié de leur
        # largeur de 4px) : une ligne dessinée exactement à x=0 ou x=w a la
        # moitié de son épaisseur hors-canvas (clippée) — quasi invisible à
        # trim_start=0.0s, signalé par l'utilisateur. La bande de sélection
        # (rectangle ci-dessus), elle, reste dessinée aux coordonnées EXACTES
        # (0..w), seule la ligne est décalée pour rester visible.
        line_x_start = max(2, min(w - 2, x_start))
        line_x_end = max(2, min(w - 2, x_end))
        line_x_roi = max(2, min(w - 2, x_roi))
        canvas.create_line(
            line_x_start, 0, line_x_start, h, fill="#33ff66", width=4, tags="trim_handle"
        )
        canvas.create_line(
            line_x_end, 0, line_x_end, h, fill="#ff3333", width=4, tags="trim_handle"
        )
        canvas.create_line(
            line_x_roi, 0, line_x_roi, h, fill="#33ccff", width=2, tags="trim_handle"
        )
        span = max(0.0, self.video_trim_end.get() - self.video_trim_start.get())
        self.video_trim_label_var.set(
            tr("t_trim_duration", "Durée : {span:.1f}s ({start:.1f}s → {end:.1f}s)",
               span=span, start=self.video_trim_start.get(), end=self.video_trim_end.get())
        )
        self._video_redraw_trim_triangles()
        self._video_redraw_roi_time_indicator()
        self._video_redraw_roi_events()

    def _video_redraw_trim_triangles(self):
        """Redessine les 2 triangles (pointe vers le HAUT, vers la ligne du
        marqueur) + la ligne cyan du temps de cadrage sur video_ruler_canvas,
        sous la zone des graduations — début/fin de trim (vert/rouge) pour
        les triangles (le triangle du temps de cadrage cyan est retiré
        d'ici, voir _video_redraw_roi_time_indicator et
        _video_redraw_trim_handles ; seule sa LIGNE reste dessinée ici,
        demande explicite "la ligne cyan n'apparaît pas sur la timeline avec
        les triangles" — présente sur video_thumb_canvas mais manquait sur
        celle-ci). Taille des triangles alignée sur celle du triangle cyan
        (largeur ±4px, hauteur 12px) — demande explicite "réduit les
        triangles à la même taille que le cyan". Appelé à chaque
        déplacement d'un marqueur (peu coûteux, contrairement aux
        graduations qui ne changent jamais après le premier dessin)."""
        canvas = self.video_ruler_canvas
        canvas.delete("trim_triangle")
        duration = self.video_meta["duration"] if self.video_meta else 0.0
        if duration <= 0:
            return
        w = self.video_thumb_canvas_width
        TICK_AREA_H = 14
        TRI_BOTTOM = TICK_AREA_H + 12
        markers = (
            ("#33ff66", self.video_trim_start.get()),
            ("#ff3333", self.video_trim_end.get()),
        )
        for color, t in markers:
            x = max(2, min(w - 2, int((t / duration) * w)))
            canvas.create_polygon(
                x - 4, TRI_BOTTOM, x + 4, TRI_BOTTOM, x, TICK_AREA_H,
                fill=color, outline="", tags="trim_triangle",
            )
        x_roi = max(2, min(w - 2, int((self.video_roi_edit_time.get() / duration) * w)))
        canvas.create_line(
            x_roi, 0, x_roi, self.video_ruler_canvas_height,
            fill="#33ccff", width=2, tags="trim_triangle",
        )

    def _video_redraw_roi_time_indicator(self):
        """Redessine le petit triangle cyan du temps de cadrage sur
        video_roi_time_indicator_canvas (au-dessus de la frise, au même
        niveau que le label "Durée: ..."), pointe vers le BAS (vers la
        frise en dessous) — demande explicite "déplacer le triangle
        au-dessus du cadre vidéo, au même niveau que l'affichage durée,
        adapter la taille du triangle" (triangle réduit, cohérent avec la
        hauteur réduite de cette bande dédiée, 12px)."""
        if not hasattr(self, "video_roi_time_indicator_canvas"):
            return
        canvas = self.video_roi_time_indicator_canvas
        canvas.delete("roi_time_indicator")
        duration = self.video_meta["duration"] if self.video_meta else 0.0
        if duration <= 0:
            return
        w, h = self.video_thumb_canvas_width, self.video_roi_time_indicator_height
        x = max(2, min(w - 2, int((self.video_roi_edit_time.get() / duration) * w)))
        canvas.create_polygon(
            x - 4, 0, x + 4, 0, x, h,
            fill="#33ccff", outline="", tags="roi_time_indicator",
        )

    def _video_redraw_roi_events(self):
        """Redessine la timeline graphique des points de zone (auto/manuel)
        et de zoom sur video_events_canvas — demande explicite "un
        affichage graphique des différentes actions posées sur la timeline
        (icônes de début/fin de tracking et de zoom, reliées par une
        ligne)". Rangée du haut : points de zone, disque orange (auto) ou
        carré violet (manuel), reliés par une ligne jusqu'au point suivant
        (n'importe quel type — c'est la frontière RÉELLE du segment, voir
        VideoEngine.compute_crop_windows_from_events) ou à la fin du trim
        si dernier. Rangée du bas (tiers inférieur) : points de zoom,
        losange sarcelle, reliés par une ligne jusqu'au point de zoom
        suivant (interpolation linéaire, indépendante des zones). Appelée
        après tout ajout/suppression/déplacement de point, ou undo/redo."""
        if not hasattr(self, "video_events_canvas"):
            return
        canvas = self.video_events_canvas
        canvas.delete("roi_event")
        duration = self.video_meta["duration"] if self.video_meta else 0.0
        if duration <= 0:
            return
        w = self.video_thumb_canvas_width
        ZONE_Y = 7
        ZOOM_Y = 19
        AUTO_COLOR = "#ffaa33"
        MANUAL_COLOR = "#cc66ff"
        ZOOM_COLOR = "#33ffcc"

        def x_of(t):
            return max(2, min(w - 2, int((t / duration) * w)))

        zones = sorted(self.video_roi_events, key=lambda e: e["t"])
        for i, ev in enumerate(zones):
            x = x_of(ev["t"])
            color = AUTO_COLOR if ev["mode"] == "auto" else MANUAL_COLOR
            x_next = (
                x_of(zones[i + 1]["t"]) if i + 1 < len(zones)
                else x_of(self.video_trim_end.get())
            )
            canvas.create_line(
                x, ZONE_Y, x_next, ZONE_Y, fill=color, width=2, tags="roi_event"
            )
            if ev["mode"] == "auto":
                canvas.create_oval(
                    x - 4, ZONE_Y - 4, x + 4, ZONE_Y + 4,
                    fill=color, outline="", tags="roi_event",
                )
            else:
                canvas.create_rectangle(
                    x - 4, ZONE_Y - 4, x + 4, ZONE_Y + 4,
                    fill=color, outline="", tags="roi_event",
                )

        zooms = sorted(self.video_zoom_keyframes, key=lambda k: k[0])
        for i, (t, _z) in enumerate(zooms):
            x = x_of(t)
            if i + 1 < len(zooms):
                x_next = x_of(zooms[i + 1][0])
                canvas.create_line(
                    x, ZOOM_Y, x_next, ZOOM_Y, fill=ZOOM_COLOR, width=1, tags="roi_event"
                )
            canvas.create_polygon(
                x, ZOOM_Y - 4, x + 4, ZOOM_Y, x, ZOOM_Y + 4, x - 4, ZOOM_Y,
                fill=ZOOM_COLOR, outline="", tags="roi_event",
            )

        # Ligne cyan du temps de cadrage, PAR-DESSUS les segments — demande
        # explicite "le trait cyan doit être présent sur la timeline aussi"
        # (déjà visible sur video_thumb_canvas/video_ruler_canvas/
        # video_roi_time_indicator_canvas, manquait ici) : permet de voir
        # d'un coup d'œil quel segment de zone/zoom est actif à l'instant
        # courant.
        x_roi = x_of(self.video_roi_edit_time.get())
        canvas.create_line(
            x_roi, 0, x_roi, self.video_events_canvas_height,
            fill="#33ccff", width=2, tags="roi_event",
        )

    def _video_event_press(self, event):
        """Sélectionne le point (zone OU zoom) le plus proche du clic, pour
        le glissé qui suit — même mécanique que _video_trim_press,
        généralisée à une liste DYNAMIQUE de points plutôt qu'à 3 marqueurs
        fixes."""
        if not self.video_meta or self.video_meta["duration"] <= 0:
            self._video_event_dragging = None
            return
        duration = self.video_meta["duration"]
        w = self.video_thumb_canvas_width
        candidates = []
        for i, ev in enumerate(self.video_roi_events):
            candidates.append(("zone", i, abs(event.x - (ev["t"] / duration) * w)))
        for i, (t, _z) in enumerate(self.video_zoom_keyframes):
            candidates.append(("zoom", i, abs(event.x - (t / duration) * w)))
        if not candidates:
            self._video_event_dragging = None
            return
        kind, idx, _dist = min(candidates, key=lambda c: c[2])
        self._video_event_dragging = (kind, idx)
        self._video_event_drag(event)

    def _video_event_drag(self, event):
        """Déplace le point sélectionné dans le temps, borné à
        [trim_start, trim_end] (ne modifie jamais la sélection de trim
        elle-même) — redessin en direct, commit undo au relâchement
        seulement (voir _video_event_release)."""
        if not getattr(self, "_video_event_dragging", None) or not self.video_meta:
            return
        duration = self.video_meta["duration"]
        if duration <= 0:
            return
        w = self.video_thumb_canvas_width
        t = max(
            self.video_trim_start.get(),
            min(self.video_trim_end.get(), (event.x / w) * duration),
        )
        kind, idx = self._video_event_dragging
        if kind == "zone":
            self.video_roi_events[idx]["t"] = t
        else:
            _old_t, z = self.video_zoom_keyframes[idx]
            self.video_zoom_keyframes[idx] = (t, z)
        self._video_redraw_roi_events()

    def _video_event_release(self, event):
        """Fin du glissé d'un point de zone/zoom : resynchronise l'affichage
        (le point déplacé est peut-être désormais actif à
        video_roi_edit_time) et commit undo."""
        if getattr(self, "_video_event_dragging", None):
            self._video_sync_roi_from_events()
            self._video_draw_roi_rect()
            self._video_update_crop_preview()
            self._video_update_keyframes_status()
            self._video_update_roi_history_text()
            self._video_commit_roi_history()
        self._video_event_dragging = None

    # Seuil de saisie (px) des barres début/fin de trim : un clic à moins de
    # cette distance de la ligne sélectionne la poignée pour un glissé (sans
    # bouger au clic lui-même) ; au-delà, le clic cible le temps de cadrage
    # à la place — demande explicite "les clics faits ailleurs que sur les
    # barres déplacent le trim de framing".
    VIDEO_TRIM_HANDLE_GRAB_PX = 10

    def _video_trim_press(self, event):
        """Sélectionne le marqueur pour le glissé qui suit — les 3 canvas
        (video_thumb_canvas, video_ruler_canvas,
        video_roi_time_indicator_canvas) partagent les mêmes handlers, et
        saisir un triangle revient à saisir sa ligne (mêmes coordonnées x).

        Début/fin de trim : SEUL un clic à moins de
        `VIDEO_TRIM_HANDLE_GRAB_PX` de leur ligne peut les sélectionner —
        et NE les déplace PAS au simple clic, seul un glissé RÉEL
        (<B1-Motion>, voir _video_trim_drag) les bouge ensuite (demande
        explicite "les trims de délimitation de la vidéo sont déplaçables
        au clic ce qui pose problème, ils ne doivent être mobilisés qu'au
        glisser — clic sur la barre et déplacement").

        Le temps de cadrage (roi_time) reste PRIORITAIRE dès qu'il est AU
        MOINS AUSSI proche du clic qu'une barre de trim — **bug réel
        corrigé** : par défaut au chargement d'une vidéo, roi_time ET
        trim_start valent tous les deux 0.0s (donc coïncident exactement à
        l'écran) ; sans cette priorité, TOUT clic proche du début de la
        frise (là où le triangle cyan est visuellement affiché) était
        systématiquement capturé par "start" — rendant le marqueur cyan
        impossible à saisir tant qu'il restait proche du début,
        symptôme signalé : "quand le trim vert est à 0.0s, l'affichage
        (video framing) reste vide quelle que soit la position du trim
        cyan" (le marqueur ne bougeait jamais, un glissé qui semblait
        cibler le cadrage déplaçait en réalité le début de trim). Seule
        une barre STRICTEMENT plus proche que roi_time (et dans le seuil de
        saisie) est sélectionnée à sa place.

        Tout clic qui ne remplit aucune de ces conditions cible directement
        le temps de cadrage — clic OU glissé, comportement inchangé pour ce
        marqueur (demande explicite "les clics faits ailleurs que sur les
        barres déplacent le trim de framing")."""
        if not self.video_meta or self.video_meta["duration"] <= 0:
            return
        w = self.video_thumb_canvas_width
        duration = self.video_meta["duration"]
        x_start = (self.video_trim_start.get() / duration) * w
        x_end = (self.video_trim_end.get() / duration) * w
        x_roi = (self.video_roi_edit_time.get() / duration) * w
        dist_start = abs(event.x - x_start)
        dist_end = abs(event.x - x_end)
        dist_roi = abs(event.x - x_roi)

        handle_candidates = [
            (name, dist) for name, dist in (("start", dist_start), ("end", dist_end))
            if dist <= self.VIDEO_TRIM_HANDLE_GRAB_PX
        ]
        if handle_candidates:
            best_name, best_dist = min(handle_candidates, key=lambda c: c[1])
            if dist_roi > best_dist:
                self._video_trim_dragging = best_name
                return

        self._video_trim_dragging = "roi_time"
        self._video_trim_drag(event)

    def _video_trim_drag(self, event):
        """Déplace le marqueur sélectionné.

        "start"/"end" : plus de plafond de durée fixe (ancien
        MAX_TRIM_SPAN=10s retiré, demande explicite — la durée se règle
        librement via le champ "Durée (s)") ; le champ Durée est
        resynchronisé, et le temps de cadrage est ramené À L'INTÉRIEUR de la
        nouvelle sélection s'il en sortait (il doit toujours y rester,
        demande explicite).

        "roi_time" : contraint à rester DANS [trim_start, trim_end] (ne
        modifie jamais la sélection de trim elle-même, demande explicite) ;
        resynchronise le ROI affiché depuis les keyframes en mode manuel."""
        if not getattr(self, "_video_trim_dragging", None) or not self.video_meta:
            return
        duration_total = self.video_meta["duration"]
        if duration_total <= 0:
            return
        w = self.video_thumb_canvas_width
        t = max(0.0, min(duration_total, (event.x / w) * duration_total))

        if self._video_trim_dragging == "start":
            t = min(t, self.video_trim_end.get())
            self.video_trim_start.set(max(0.0, t))
            if self.video_roi_edit_time.get() < self.video_trim_start.get():
                self.video_roi_edit_time.set(self.video_trim_start.get())
            self.video_duration.set(
                round(self.video_trim_end.get() - self.video_trim_start.get(), 1)
            )
        elif self._video_trim_dragging == "end":
            t = max(t, self.video_trim_start.get())
            self.video_trim_end.set(min(duration_total, t))
            if self.video_roi_edit_time.get() > self.video_trim_end.get():
                self.video_roi_edit_time.set(self.video_trim_end.get())
            self.video_duration.set(
                round(self.video_trim_end.get() - self.video_trim_start.get(), 1)
            )
        else:  # "roi_time"
            t = max(self.video_trim_start.get(), min(self.video_trim_end.get(), t))
            self.video_roi_edit_time.set(t)
            if self.video_roi_events:
                self._video_sync_roi_from_events()

        self._video_redraw_trim_handles()
        # (#4) Aperçu live de la frame au niveau du marqueur déplacé, dans le
        # canvas "Zone d'intérêt" — pour caler précisément les points de
        # coupe (ou le temps de cadrage) visuellement, demande explicite.
        # Appel synchrone (pas de thread) : le seek cv2 est rapide sur les
        # fichiers courants, un thread par micro-mouvement de souris
        # ajouterait plus de complexité que de gain perçu.
        self._video_show_frame_at_time(t)

    def _video_on_duration_change(self):
        """Callback du Spinbox "Durée (s)" : ajuste trim_end = trim_start +
        durée (clampée pour ne pas dépasser la fin de la vidéo source), garde
        trim_start fixe."""
        if not self.video_meta or self.video_meta["duration"] <= 0:
            return
        total = self.video_meta["duration"]
        remaining = max(0.1, total - self.video_trim_start.get())
        duration = max(0.1, min(self.video_duration.get(), remaining))
        self.video_duration.set(round(duration, 1))
        self.video_trim_end.set(round(self.video_trim_start.get() + duration, 1))
        self._video_clamp_roi_edit_time()

    def _video_trim_release(self, event):
        """Fin du glissé : revient à la frame de référence "officielle" —
        début du trim en mode tracking (c'est la frame que track_roi
        utilisera réellement comme seed), temps de cadrage courant en mode
        manuel.

        Appel SYNCHRONE (voir _video_show_frame_at_time), PAS dans un thread
        séparé — v51 utilisait un thread ici, corrigé (v52) suite à un bug
        réel signalé par l'utilisateur : "quand on relâche la barre temps de
        cadrage l'image disparaît dans ROI". Cause : ce thread ouvrait son
        PROPRE cv2.VideoCapture sur le fichier vidéo, en VRAIE concurrence
        avec la boucle de lecture intégrée (_video_playback_tick), qui garde
        SON PROPRE VideoCapture ouvert en continu sur le MÊME fichier — 2
        handles cv2 lus en parallèle depuis 2 threads différents provoquait
        des lectures corrompues (frame noire) sur certains backends
        Windows. Les extractions synchrones (pendant le glissé lui-même, via
        _video_trim_drag) ne montraient jamais ce bug car elles s'exécutent
        sur le thread principal, jamais en parallèle de la boucle de lecture
        (qui tourne AUSSI sur le thread principal via root.after) — aucune
        concurrence réelle possible entre 2 opérations sur le même thread."""
        # Capturé AVANT de réinitialiser _video_trim_dragging à None —
        # nécessaire pour distinguer plus bas quel marqueur vient d'être
        # relâché (bug réel corrigé, voir commentaire dans la branche
        # tracking ci-dessous).
        dragged = self._video_trim_dragging
        self._video_trim_dragging = None
        if not self.video_path:
            return
        self._video_clamp_roi_edit_time()
        if self.video_roi_events:
            # Des points existent déjà sur la timeline : la référence suit
            # toujours l'événement actif à l'instant courant (cut net, pas
            # d'interpolation) — remplace l'ancienne distinction globale
            # tracking/manuel, qui n'existe plus qu'au niveau de chaque
            # point individuel.
            self._video_sync_roi_from_events()
            ref_time = self.video_roi_edit_time.get()
        elif self.video_roi_tracking_enabled.get():
            if dragged in ("start", "end"):
                # Rétrocompatibilité (aucun point encore posé) : le ROI
                # dessiné était relatif à l'ANCIENNE frame de trim_start
                # (autre instant de la vidéo) — plus valide une fois la
                # référence changée, mieux vaut le réinitialiser
                # explicitement que de garder un cadrage silencieusement
                # décalé.
                self.video_roi = None
                ref_time = self.video_trim_start.get()
            else:
                # **Bug réel corrigé** : relâcher le marqueur "temps de
                # cadrage" (roi_time) tombait dans cette même branche
                # (mode tracking, aucun point posé) et réinitialisait
                # TOUJOURS l'affichage sur trim_start — silencieusement
                # invisible tant que trim_start valait 0.0s (frame quasi
                # identique), mais provoquant un vrai retour en arrière
                # visible dès que trim_start restait à 0.0s et que
                # roi_time avait été déplacé ailleurs ("trim vert à 0.0 et
                # trim cyan > 0.0 -> image blanche/figée dans la zone de
                # cadrage", la frame affichée revenait à celle de
                # trim_start=0.0s au lieu de suivre roi_time). La
                # référence doit suivre l'instant réellement visé par ce
                # marqueur, pas trim_start.
                ref_time = self.video_roi_edit_time.get()
        else:
            # Rétrocompatibilité (aucun point encore posé), mode manuel :
            # _video_display_ref_frame matérialise un cadre par défaut.
            ref_time = self.video_roi_edit_time.get()
        self._video_show_frame_at_time(ref_time)

    def _video_sync_roi_from_events(self):
        """Recalcule self.video_roi = position du point de zone ACTIF à
        self.video_roi_edit_time (dernier événement dont t <= l'instant
        courant — cut net, pas d'interpolation, voir video_roi_events).
        Sans point, ne fait rien ici — la matérialisation par défaut est
        gérée par _video_display_ref_frame. Resynchronise AUSSI le curseur
        "Zoom cadrage" sur la valeur interpolée à ce même instant (voir
        _video_sync_zoom_from_keyframes) : les 2 pistes (position/zoom)
        doivent rester alignées à chaque changement d'instant affiché."""
        ev = self._video_roi_event_at_time(self.video_roi_edit_time.get())
        if ev is not None:
            self.video_roi = ev["roi"]
        self._video_sync_zoom_from_keyframes()

    def _video_sync_zoom_from_keyframes(self):
        """Recalcule le curseur "Zoom cadrage" (video_crop_zoom) sur la
        valeur INTERPOLÉE de video_zoom_keyframes à self.video_roi_edit_time
        — bug réel corrigé : rien ne synchronisait jusqu'ici ce curseur
        quand on navigue dans le temps (contrairement à la position, voir
        _video_sync_roi_from_events) ; il restait bloqué sur la dernière
        valeur réglée MANUELLEMENT quel que soit l'instant affiché. Résultat
        signalé : "les changements de zoom semblent se faire depuis le
        premier point progressivement pour atteindre la valeur du dernier
        point" — l'interpolation locale entre points consécutifs était déjà
        mathématiquement correcte côté moteur (VideoEngine.interpolate_zoom_keyframes,
        vérifié par diagnostic dédié), mais jamais reflétée à l'écran en
        dehors des 2 points explicitement posés, donnant l'illusion d'un
        saut direct premier→dernier point. Passe par le trace existant sur
        video_crop_zoom (_video_on_zoom_change), qui recalcule en plus la
        TAILLE du rectangle affiché autour du centre courant — cohérent
        avec le pipeline final (position figée par video_roi_events, taille
        toujours dérivée du zoom courant, voir compute_crop_windows). Sans
        keyframe, ne fait rien (le curseur garde sa valeur libre)."""
        if not self.video_zoom_keyframes:
            return
        t = self.video_roi_edit_time.get()
        z = VideoEngine.interpolate_zoom_keyframes([t], self.video_zoom_keyframes)[0]
        self.video_crop_zoom.set(z)

    def _video_roi_event_at_time(self, t):
        """Retourne l'événement de zone (dict {"t","roi","mode"}) actif à
        l'instant `t` : le dernier dont t_event <= t, ou le premier si `t`
        est antérieur à tous (même convention de clamp que l'ancienne
        interpolation par keyframes). None si video_roi_events est vide."""
        if not self.video_roi_events:
            return None
        ev_sorted = sorted(self.video_roi_events, key=lambda e: e["t"])
        active = ev_sorted[0]
        for e in ev_sorted:
            if e["t"] <= t:
                active = e
            else:
                break
        return active

    def _video_nearest_roi_event(self, t):
        """Retourne (index, événement) le plus proche en temps de `t` dans
        video_roi_events, ou (None, None) si la liste est vide. Utilisé pour
        "🔄 Recentrer"/"🗑️ Supprimer ce point" (édition/suppression du point
        le plus proche du "temps de cadrage" courant)."""
        if not self.video_roi_events:
            return None, None
        idx = min(
            range(len(self.video_roi_events)),
            key=lambda i: abs(self.video_roi_events[i]["t"] - t),
        )
        return idx, self.video_roi_events[idx]

    def _video_commit_roi_history(self):
        """Enregistre l'état courant (points de zone + de zoom) comme un
        nouveau point d'historique undo/redo — mécanisme pointeur identique
        à l'onglet MANUEL (voir _manual_commit_history) : tronque toute
        branche "redo" désormais obsolète si l'utilisateur avait fait un ou
        plusieurs undo puis effectue une nouvelle action, avant d'empiler le
        nouvel état. À appeler après toute action discrète qui modifie
        video_roi_events/video_zoom_keyframes (ajout/suppression/déplacement
        de point) — PAS pendant un glissé continu (voir _video_event_drag),
        seulement à son relâchement."""
        self.video_roi_history = self.video_roi_history[: self.video_roi_history_index + 1]
        self.video_roi_history.append(
            {
                "events": [dict(e) for e in self.video_roi_events],
                "zoom_kf": list(self.video_zoom_keyframes),
            }
        )
        self.video_roi_history_index = len(self.video_roi_history) - 1

    def _video_roi_undo(self):
        """Annule la dernière action sur les points de zone/zoom (voir
        _video_roi_redo)."""
        if self.video_roi_history_index > 0:
            self.video_roi_history_index -= 1
            self._video_restore_roi_history_snapshot()
        else:
            messagebox.showinfo(
                lang_manager.get("info", "Info"), lang_manager.get("nothing_to_undo", "Rien à annuler")
            )

    def _video_roi_redo(self):
        """Rétablit l'action précédemment annulée par _video_roi_undo."""
        if self.video_roi_history_index < len(self.video_roi_history) - 1:
            self.video_roi_history_index += 1
            self._video_restore_roi_history_snapshot()
        else:
            messagebox.showinfo(
                lang_manager.get("info", "Info"), lang_manager.get("nothing_to_redo", "Rien à rétablir")
            )

    def _video_restore_roi_history_snapshot(self):
        """Restaure video_roi_events/video_zoom_keyframes depuis le
        snapshot courant de video_roi_history (video_roi_history_index),
        puis resynchronise l'affichage (rectangle ROI, timeline graphique,
        historique texte, aperçu de cadrage) — commun à undo et redo."""
        snapshot = self.video_roi_history[self.video_roi_history_index]
        self.video_roi_events = [dict(e) for e in snapshot["events"]]
        self.video_zoom_keyframes = list(snapshot["zoom_kf"])
        self._video_sync_roi_from_events()
        self._video_draw_roi_rect()
        self._video_update_crop_preview()
        self._video_update_keyframes_status()
        self._video_redraw_roi_events()
        self._video_update_roi_history_text()

    def _video_show_frame_at_time(self, t):
        """Affiche immédiatement (appel synchrone, sans thread) la frame au
        temps `t` dans le canvas ROI — retour visuel en direct pendant un
        glissé (poignées de trim ou scrubber "Temps de cadrage"). Le seek
        cv2 est rapide sur les fichiers courants ; si ça s'avère trop lent
        sur de gros fichiers réels, un débounce serait la prochaine étape."""
        if not self.video_path:
            return
        try:
            frame = VideoEngine.extract_reference_frame(self.video_path, t)
        except Exception:
            return
        self.video_ref_frame = frame
        self._video_display_ref_frame()

    def _video_display_ref_frame(self):
        """Affiche self.video_ref_frame dans video_roi_canvas (letterboxée,
        ratio préservé) et mémorise l'échelle/offset pour convertir les clics
        souris en coordonnées de la frame source (voir
        _video_canvas_rect_to_frame_roi). Matérialise aussi un cadre 128:32
        centré par défaut si aucun ROI n'existe ET que le mode "🎯 Suivi
        automatique" n'est PAS actif ("🪄 Cadrage auto"/"✋ Manuel") — demande
        explicite de l'utilisateur (en mode tracking, l'absence de ROI reste
        un état valide : "pas de crop du tout", comportement historique)."""
        canvas = self.video_roi_canvas
        canvas.delete("all")
        if self.video_ref_frame is None:
            return
        if self.video_roi_events:
            # Des points existent déjà sur la timeline : la référence
            # affichée suit toujours l'événement actif à l'instant courant
            # (cut net, pas d'interpolation) — voir _video_sync_roi_from_events.
            self._video_sync_roi_from_events()
        elif self.video_roi is None and not self.video_roi_tracking_enabled.get():
            # Rétrocompatibilité : aucun point encore posé, tracking non
            # actif ("auto_zoom" ou "manual") — matérialise un cadre par
            # défaut à AJUSTER (uniquement dans self.video_roi, PAS commité
            # dans video_roi_events : la création d'un point reste une action
            # explicite via "➕ Point ici", demande explicite de
            # l'utilisateur — contrairement à l'ancien comportement qui
            # committait silencieusement un keyframe ici).
            self.video_roi = self._video_default_roi_rect(self.video_ref_frame.size)
        cw, ch = self.video_roi_canvas_w, self.video_roi_canvas_h
        img = self.video_ref_frame
        scale = min(cw / img.width, ch / img.height)
        disp_w, disp_h = max(1, int(img.width * scale)), max(1, int(img.height * scale))
        disp = img.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
        self._video_ref_photo = ImageTk.PhotoImage(disp)
        off_x, off_y = (cw - disp_w) // 2, (ch - disp_h) // 2
        canvas.create_image(off_x, off_y, image=self._video_ref_photo, anchor="nw")
        self.video_ref_frame_display_scale = scale
        self.video_ref_frame_offset = (off_x, off_y)
        self.video_roi_canvas_ids = []
        self._video_draw_roi_rect()
        self._video_update_crop_preview()

    def _video_canvas_rect_to_frame_roi(self, cx0, cy0, cx1, cy1):
        """Convertit un rectangle en coordonnées canvas vers des coordonnées
        de la frame source, clampées aux bords. Retourne None si le résultat
        est trop petit pour être exploitable (zone < 8px sur un axe)."""
        if self.video_ref_frame is None:
            return None
        scale = self.video_ref_frame_display_scale
        off_x, off_y = self.video_ref_frame_offset
        fx0 = (min(cx0, cx1) - off_x) / scale
        fy0 = (min(cy0, cy1) - off_y) / scale
        fx1 = (max(cx0, cx1) - off_x) / scale
        fy1 = (max(cy0, cy1) - off_y) / scale

        fw, fh = self.video_ref_frame.size
        fx0 = max(0.0, min(fw, fx0))
        fx1 = max(0.0, min(fw, fx1))
        fy0 = max(0.0, min(fh, fy0))
        fy1 = max(0.0, min(fh, fy1))

        if fx1 - fx0 < 8 or fy1 - fy0 < 8:
            return None
        return (int(fx0), int(fy0), int(fx1 - fx0), int(fy1 - fy0))

    def _video_roi_start(self, event):
        """Début d'un cliqué-glissé sur le canvas ROI.

        Modes "🪄 Cadrage auto"/"✋ Manuel" (tracking désactivé) : le cadre
        est TOUJOURS déjà matérialisé (voir _video_display_ref_frame) — un
        clic n'importe où le déplace directement (offset préservé si le
        clic tombe dans le rectangle, sinon le rectangle est recentré sous
        le curseur) ; il n'est JAMAIS nécessaire de "dessiner" (demande
        explicite de l'utilisateur, applicable uniquement quand le tracking
        est off).

        Mode "🎯 Suivi automatique" : comportement historique inchangé —
        clic DANS le rectangle déjà dessiné = déplacement (taille
        conservée), clic en dehors = dessin d'un nouveau rectangle (qui
        servira de seed au tracker)."""
        if self.video_ref_frame is None:
            return

        if not self.video_roi_tracking_enabled.get():
            if self.video_roi is not None:
                scale = self.video_ref_frame_display_scale
                off_x, off_y = self.video_ref_frame_offset
                x, y, w, h = self.video_roi
                cx0, cy0 = off_x + x * scale, off_y + y * scale
                cx1, cy1 = off_x + (x + w) * scale, off_y + (y + h) * scale
                self._video_roi_drag_mode = "move"
                if cx0 <= event.x <= cx1 and cy0 <= event.y <= cy1:
                    self._video_roi_move_offset = (event.x - cx0, event.y - cy0)
                else:
                    # Clic hors du rectangle : le recentre directement sous
                    # le curseur (pas de dessin requis), ajustable ensuite
                    # au glissé comme un déplacement classique.
                    self._video_roi_move_offset = ((cx1 - cx0) / 2, (cy1 - cy0) / 2)
                self._video_roi_drag_start = None
                return
            # Aucun rectangle affiché (effacé par "➕ Point ici", ou jamais
            # dessiné) : DESSINE une nouvelle zone au lieu d'en
            # matérialiser une par défaut — demande explicite "Point ici
            # efface et exige un nouveau dessin" (l'ancien comportement
            # rematérialisait toujours un cadre par défaut ici, empêchant
            # tout dessin réel en mode manuel). Un cadre par défaut reste
            # matérialisé ailleurs (passage en mode manuel, confort
            # initial) — seul CE point d'entrée change.
            self._video_roi_drag_mode = "draw"
            self._video_roi_drag_start = (event.x, event.y)
            return

        if self.video_roi is not None:
            scale = self.video_ref_frame_display_scale
            off_x, off_y = self.video_ref_frame_offset
            x, y, w, h = self.video_roi
            cx0, cy0 = off_x + x * scale, off_y + y * scale
            cx1, cy1 = off_x + (x + w) * scale, off_y + (y + h) * scale
            if cx0 <= event.x <= cx1 and cy0 <= event.y <= cy1:
                self._video_roi_drag_mode = "move"
                self._video_roi_move_offset = (event.x - cx0, event.y - cy0)
                self._video_roi_drag_start = None
                return
        self._video_roi_drag_mode = "draw"
        self._video_roi_drag_start = (event.x, event.y)

    def _video_roi_drag(self, event):
        canvas = self.video_roi_canvas

        if self._video_roi_drag_mode == "move" and self.video_roi is not None:
            # Déplace le rectangle existant (taille inchangée), avec aperçu
            # live du cadrage résultant — c'est le mécanisme central du
            # cadrage manuel (sans tracking) : voir _video_update_crop_preview.
            scale = self.video_ref_frame_display_scale
            off_x, off_y = self.video_ref_frame_offset
            _, _, w, h = self.video_roi
            off_dx, off_dy = self._video_roi_move_offset
            new_cx0 = event.x - off_dx
            new_cy0 = event.y - off_dy
            fx0 = (new_cx0 - off_x) / scale
            fy0 = (new_cy0 - off_y) / scale
            fw, fh = self.video_ref_frame.size
            fx0 = max(0.0, min(fw - w, fx0))
            fy0 = max(0.0, min(fh - h, fy0))
            self.video_roi = (int(fx0), int(fy0), w, h)
            self._video_draw_roi_rect()
            self._video_update_crop_preview()
            return

        if not getattr(self, "_video_roi_drag_start", None):
            return
        x0, y0 = self._video_roi_drag_start
        for cid in self.video_roi_canvas_ids:
            canvas.delete(cid)
        self.video_roi_canvas_ids = [
            canvas.create_rectangle(
                x0, y0, event.x, event.y, outline="#33ff66", width=2, dash=(4, 2)
            )
        ]
        temp_roi = self._video_canvas_rect_to_frame_roi(x0, y0, event.x, event.y)
        if temp_roi is not None:
            self._video_update_crop_preview(temp_roi)

    def _video_roi_end(self, event):
        """Fin du cliqué-glissé. Mode "move" : la position finale est déjà
        appliquée en direct par _video_roi_drag ; si un point de zone existe
        déjà (mode "manual"), le point le plus proche du temps de cadrage
        courant est mis à jour avec la nouvelle position au relâchement —
        bug réel corrigé : `compute_crop_windows` ignore délibérément la
        TAILLE (w, h) de `roi_positions` (toujours recalculée depuis le
        curseur "Zoom cadrage", lu en direct au moment de la génération) mais
        utilise bel et bien leur CENTRE, gelé dans `video_roi_events` au
        moment du commit — un simple déplacement du cadre (sans repasser par
        "➕ Point ici"/"🔄 Recentrer") ne mettait donc JAMAIS à jour ce
        centre, ce qui rendait le déplacement invisible dans le rendu final
        alors que le zoom (recalculé en direct) semblait fonctionner
        normalement (signalé explicitement : "la valeur de zoom fonctionne
        mais le déplacement du cadre de zoom n'est pas pris en compte").
        Mode "draw" : convertit le rectangle final en coordonnées de la
        frame source et le mémorise dans self.video_roi — SI ce dessin fait
        suite à "➕ Point ici" (`_video_awaiting_point_draw`), le commite EN
        PLUS automatiquement comme point de zone au relâchement (demande
        explicite : "vous dessinez votre zone sur le sujet, elle se
        committe automatiquement au relâchement de la souris"), sinon reste
        du staging comme pour un dessin libre hors de ce flux."""
        mode = self._video_roi_drag_mode
        self._video_roi_drag_mode = None

        if mode == "move":
            self._video_draw_roi_rect()
            self._video_update_crop_preview()
            if self.video_roi_events:
                t = self.video_roi_edit_time.get()
                NEARBY_EPSILON = 0.3
                idx, nearest = self._video_nearest_roi_event(t)
                if nearest is not None and abs(nearest["t"] - t) < NEARBY_EPSILON:
                    self.video_roi_events[idx] = {"t": nearest["t"], "roi": self.video_roi, "mode": "manual"}
                else:
                    self.video_roi_events.append({"t": t, "roi": self.video_roi, "mode": "manual"})
                self._video_update_keyframes_status()
                self._video_redraw_roi_events()
                self._video_update_roi_history_text()
                self._video_commit_roi_history()
            return

        drag_start = getattr(self, "_video_roi_drag_start", None)
        self._video_roi_drag_start = None
        if not drag_start or self.video_ref_frame is None:
            return
        x0, y0 = drag_start

        roi = self._video_canvas_rect_to_frame_roi(x0, y0, event.x, event.y)
        if roi is None:
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"), lang_manager.get("zone_too_small", "Zone trop petite")
            )
            self._video_draw_roi_rect()
            self._video_update_crop_preview()
            return

        self.video_roi = roi
        self._video_draw_roi_rect()
        self._video_update_crop_preview()

        if getattr(self, "_video_awaiting_point_draw", False):
            self._video_awaiting_point_draw = False
            self._video_upsert_roi_event(self.video_roi_edit_time.get(), self.video_roi, "manual")
            self._video_redraw_roi_events()
            self._video_update_roi_history_text()
            self._video_commit_roi_history()

    def _video_draw_roi_rect(self):
        canvas = self.video_roi_canvas
        for cid in self.video_roi_canvas_ids:
            canvas.delete(cid)
        self.video_roi_canvas_ids = []
        if not self.video_roi:
            return
        x, y, w, h = self.video_roi
        scale = self.video_ref_frame_display_scale
        off_x, off_y = self.video_ref_frame_offset
        x0 = off_x + x * scale
        y0 = off_y + y * scale
        x1 = off_x + (x + w) * scale
        y1 = off_y + (y + h) * scale
        self.video_roi_canvas_ids = [
            canvas.create_rectangle(x0, y0, x1, y1, outline="#33ff66", width=2)
        ]

    def _video_update_crop_preview(self, roi=None):
        """Rend un aperçu instantané (frame de référence seule, pas le
        pipeline complet multi-frames) du cadrage 128×32 obtenu pour `roi`
        (ou self.video_roi si non fourni). Appelé en continu pendant le
        dessin/déplacement du ROI — c'est le seul retour visuel disponible en
        mode manuel (tracking désactivé), où aucune animation n'est générée
        tant que l'utilisateur n'a pas cliqué "Générer Aperçu"."""
        canvas = self.video_crop_preview_canvas
        canvas.delete("all")
        if self.video_ref_frame is None:
            return
        roi = roi if roi is not None else self.video_roi
        frame = self.video_ref_frame
        if roi is not None:
            x, y, w, h = roi
            if w > 0 and h > 0:
                frame = frame.crop((x, y, x + w, y + h))
        try:
            resized, rw, rh = DMDEngine.adaptive_resize(
                frame,
                128,
                32,
                # "fit" (pas "fill") quelle que soit la taille du crop : à
                # zoom=1.0 le crop est déjà exactement au ratio 128:32 donc
                # fit==fill (pas de bande noire) ; à zoom<1.0 le crop est plus
                # large que 4:1 (jusqu'au frame entier à zoom=0), "fit" le
                # laisse alors entièrement visible avec des bandes noires —
                # c'est précisément le comportement "resize" voulu par le
                # curseur de zoom, "fill" aurait recadré l'excédent au lieu
                # de l'afficher en letterbox.
                mode="fit" if roi is not None else "auto",
                pixel_perfect=self._get_force_pixel_perfect(),
            )
        except Exception:
            return
        canvas_frame = Image.new("RGB", (128, 32), (0, 0, 0))
        canvas_frame.paste(resized, ((128 - rw) // 2, (32 - rh) // 2))
        if self._get_force_pixel_perfect():
            display = DMDEngine.render_led_style(
                canvas_frame,
                scale=2,
                led_ratio=0.525,
                glow=True,
                brightness=self.led_brightness_var.get(),
            )
        else:
            display = canvas_frame.resize((256, 64), Image.Resampling.NEAREST)
        self._video_crop_preview_photo = ImageTk.PhotoImage(display)
        canvas.create_image(128, 32, image=self._video_crop_preview_photo)

    def _video_roi_reset(self):
        """Bouton "🔄 Recentrer" — triple comportement selon le mode de
        cadrage (le système de points n'existe QUE en mode "✋ Manuel", voir
        _video_on_crop_mode_change) :

        "🎯 Suivi automatique" : efface la zone d'intérêt actuellement
        dessinée — comportement ORIGINAL simple, sans ROI le pipeline
        retombe sur un adaptive_resize standard (sans crop dynamique) tant
        que l'utilisateur n'a pas redessiné un rectangle.

        "🪄 Cadrage auto (zoom)" : replace simplement le rectangle unique au
        centre (taille dérivée du zoom effectif courant) — jamais de point
        créé dans ce mode, un seul cadrage déplaçable existe.

        "✋ Manuel" : recentre (cadre 128:32, taille dérivée du zoom effectif
        courant) le point de zone le plus proche de video_roi_edit_time — le
        met à jour en place si trouvé à moins de `NEARBY_EPSILON`, sinon EN
        CRÉE un nouveau. Les autres points déjà posés à d'autres instants
        sont conservés (voir "🗑️ Effacer points" pour tout réinitialiser)."""
        mode = self.video_crop_mode.get()
        if mode == "tracking":
            self.video_roi = None
            self._video_draw_roi_rect()
            self._video_update_crop_preview()
            return
        if self.video_ref_frame is None:
            return
        default_rect = self._video_default_roi_rect(self.video_ref_frame.size)
        self.video_roi = default_rect
        if mode == "auto_zoom":
            self._video_draw_roi_rect()
            self._video_update_crop_preview()
            return
        t = self.video_roi_edit_time.get()
        NEARBY_EPSILON = 0.3
        idx, nearest = self._video_nearest_roi_event(t)
        if nearest is not None and abs(nearest["t"] - t) < NEARBY_EPSILON:
            self.video_roi_events[idx] = {"t": nearest["t"], "roi": default_rect, "mode": "manual"}
        else:
            self.video_roi_events.append({"t": t, "roi": default_rect, "mode": "manual"})
        self._video_draw_roi_rect()
        self._video_update_crop_preview()
        self._video_update_keyframes_status()
        self._video_redraw_roi_events()
        self._video_update_roi_history_text()
        self._video_commit_roi_history()

    def _video_clear_roi_keyframes(self):
        """Bouton "🗑️ Effacer points" : supprime TOUS les points de zone ET
        de zoom (repart d'un cadre centré unique, zoom scalaire global —
        voir "🗑️ Supprimer ce point" pour un retrait ciblé d'un seul
        point)."""
        self.video_roi_events = []
        self.video_zoom_keyframes = []
        self.video_roi = None
        if not self.video_roi_tracking_enabled.get() and self.video_ref_frame is not None:
            self.video_roi = self._video_default_roi_rect(self.video_ref_frame.size)
        self._video_draw_roi_rect()
        self._video_update_crop_preview()
        self._video_update_keyframes_status()
        self._video_redraw_roi_events()
        self._video_update_roi_history_text()
        self._video_commit_roi_history()

    def _video_upsert_roi_event(self, t, roi, mode):
        """Ajoute un événement de zone {"t","roi","mode"}, ou remplace
        l'événement existant le plus proche si celui-ci tombe à moins de
        0.05s de `t` (évite d'accumuler des dizaines de points quasi-
        identiques quand l'utilisateur ajuste finement la position au même
        instant)."""
        EPSILON = 0.05
        for i, ev in enumerate(self.video_roi_events):
            if abs(ev["t"] - t) < EPSILON:
                self.video_roi_events[i] = {"t": t, "roi": roi, "mode": mode}
                self._video_update_keyframes_status()
                return
        self.video_roi_events.append({"t": t, "roi": roi, "mode": mode})
        self._video_update_keyframes_status()

    def _video_add_roi_point(self):
        """Bouton "➕ Point ici" (mode manuel UNIQUEMENT — désactivé/grisé
        en mode auto, voir _video_update_point_buttons_state) : EFFACE le
        rectangle actuellement affiché et exige un NOUVEAU dessin sur le
        sujet à suivre — demande explicite après clarification
        utilisateur ("Point ici efface et exige un nouveau dessin ...
        vous dessinez votre zone sur le sujet, elle se committe
        automatiquement au relâchement de la souris"). Remplace l'ancien
        comportement qui committait silencieusement le rectangle par
        défaut déjà affiché (jamais vraiment "dessiné" pour ce point), ce
        qui empêchait en pratique de définir une zone dédiée à chaque
        point. Le commit réel se fait dans _video_roi_end au relâchement
        du dessin qui suit (voir _video_awaiting_point_draw), toujours en
        mode "manual" : le système de points n'existe qu'en mode manuel."""
        if self.video_ref_frame is None:
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"),
                lang_manager.get("video_load_first_warning", "Chargez d'abord une vidéo"),
            )
            return
        self.video_roi = None
        self._video_awaiting_point_draw = True
        self._video_draw_roi_rect()
        self._video_update_crop_preview()

    def _video_add_zoom_point(self):
        """Bouton "🔍 Zoom ici" : crée/remplace un point de zoom à
        video_roi_edit_time avec la valeur courante du curseur "Zoom
        cadrage" — ET fige la position du cadre actuellement affiché à ce
        même instant dans video_roi_events (bug réel corrigé : la valeur de
        zoom était bien enregistrée mais pas la position du cadre au moment
        du clic — "les points zoom sont bien enregistrés avec leur valeur
        mais pas leur position" — les 2 pistes video_zoom_keyframes/
        video_roi_events restent structurellement INDÉPENDANTES [voir
        compute_crop_windows_from_events : le centre de la fenêtre de crop
        vient toujours de video_roi_events, jamais de video_zoom_keyframes],
        donc sans cette position associée, le rendu final utilisait la
        position du point de zone le plus proche existant — potentiellement
        très différente de celle réglée pour CE zoom — au lieu de celle
        voulue par l'utilisateur pour cet instant précis)."""
        t = self.video_roi_edit_time.get()
        zoom = self.video_crop_zoom.get()
        EPSILON = 0.05
        for i, (kt, _) in enumerate(self.video_zoom_keyframes):
            if abs(kt - t) < EPSILON:
                self.video_zoom_keyframes[i] = (t, zoom)
                break
        else:
            self.video_zoom_keyframes.append((t, zoom))
        if self.video_roi is not None:
            self._video_upsert_roi_event(t, self.video_roi, "manual")
        self._video_update_keyframes_status()
        self._video_redraw_roi_events()
        self._video_update_roi_history_text()
        self._video_commit_roi_history()

    def _video_delete_nearest_point(self):
        """Bouton "🗑️ Supprimer ce point" : retire le point (zone OU zoom,
        le plus proche en temps) le plus proche de video_roi_edit_time.
        "🗑️ Effacer points" reste disponible pour tout réinitialiser d'un
        coup."""
        t = self.video_roi_edit_time.get()
        idx_zone, nearest_zone = self._video_nearest_roi_event(t)
        nearest_zoom_idx = None
        if self.video_zoom_keyframes:
            nearest_zoom_idx = min(
                range(len(self.video_zoom_keyframes)),
                key=lambda i: abs(self.video_zoom_keyframes[i][0] - t),
            )
        dist_zone = abs(nearest_zone["t"] - t) if nearest_zone is not None else None
        dist_zoom = (
            abs(self.video_zoom_keyframes[nearest_zoom_idx][0] - t)
            if nearest_zoom_idx is not None
            else None
        )
        if dist_zone is None and dist_zoom is None:
            return
        if dist_zoom is None or (dist_zone is not None and dist_zone <= dist_zoom):
            del self.video_roi_events[idx_zone]
        else:
            del self.video_zoom_keyframes[nearest_zoom_idx]
        self._video_sync_roi_from_events()
        self._video_draw_roi_rect()
        self._video_update_crop_preview()
        self._video_update_keyframes_status()
        self._video_redraw_roi_events()
        self._video_update_roi_history_text()
        self._video_commit_roi_history()

    def _video_update_keyframes_status(self):
        """Résume le nombre de points de zone (auto/manuel) ET de points de
        zoom dans video_roi_keyframes_status_var (label sous les boutons)."""
        if not hasattr(self, "video_roi_keyframes_status_var"):
            return
        n = len(self.video_roi_events)
        nz = len(self.video_zoom_keyframes)
        if n == 0 and nz == 0:
            self.video_roi_keyframes_status_var.set("")
            return
        parts = []
        if n == 1:
            parts.append("1 zone (fixe)")
        elif n > 1:
            n_auto = sum(1 for e in self.video_roi_events if e["mode"] == "auto")
            n_manual = n - n_auto
            parts.append(f"{n} zones ({n_auto} auto, {n_manual} manuelle(s))")
        if nz == 1:
            parts.append("1 point de zoom")
        elif nz > 1:
            parts.append(f"{nz} points de zoom")
        self.video_roi_keyframes_status_var.set(" · ".join(parts))

    def _video_update_roi_history_text(self):
        """Rafraîchit le cadre "📜 Historique de cadrage" (liste
        chronologique en texte des points de zone ET de zoom) — demande
        explicite "un cadre avec l'historique en texte dans le cadre roi".
        Appelée aux mêmes moments que _video_redraw_roi_events (ajout/
        suppression/déplacement de point, undo/redo)."""
        if not hasattr(self, "video_roi_history_text"):
            return
        entries = []
        for ev in self.video_roi_events:
            label = "🎯 Début tracking" if ev["mode"] == "auto" else "✋ Zone manuelle"
            entries.append((ev["t"], label))
        for t, z in self.video_zoom_keyframes:
            entries.append((t, f"🔍 Zoom {z * 100:.0f}%"))
        entries.sort(key=lambda e: e[0])
        text = (
            "\n".join(f"{t:5.1f}s  {label}" for t, label in entries)
            if entries
            else "Aucun point posé."
        )
        self.video_roi_history_text.config(state="normal")
        self.video_roi_history_text.delete(1.0, tk.END)
        self.video_roi_history_text.insert(1.0, text)
        self.video_roi_history_text.config(state="disabled")

    def _video_default_roi_rect(self, frame_size):
        """Cadre 128:32 centré par défaut (taille dérivée du zoom effectif
        courant) — matérialisé automatiquement en mode manuel, sans besoin
        de dessin (demande explicite, uniquement quand le tracking est
        désactivé)."""
        fw, fh = frame_size
        return VideoEngine.roi_rect_for_zoom(
            frame_size, (fw / 2, fh / 2), self._video_effective_zoom()
        )

    def _video_effective_zoom(self):
        """Zoom cadrage/redimensionnement effectif : calculé automatiquement
        si "🪄 Resize auto" est coché (même heuristique que
        DMDEngine.adaptive_resize mode="auto" — fit si le ratio de la vidéo
        source est proche du ratio cible 128:32, sinon fill/crop serré),
        sinon la valeur manuelle du curseur "Zoom cadrage". Échelle -1..1
        (voir video_crop_zoom) : l'heuristique "resize auto" retourne
        désormais -1.0 (resize pur, remplace l'ancien 0.0) ou 0.0 (crop
        serré, remplace l'ancien 1.0)."""
        if self.video_resize_auto.get() and self.video_meta:
            w, h = self.video_meta.get("width", 0), self.video_meta.get("height", 0)
            if h > 0:
                ratio = w / h
                target_ratio = 128 / 32
                return -1.0 if abs(ratio - target_ratio) < 0.5 else 0.0
        try:
            return self.video_crop_zoom.get()
        except Exception:
            return 0.0

    # Distance (échelle -1..1) en dessous de laquelle un glissé du curseur
    # "Zoom cadrage" est happé exactement sur 0.0 (crop serré, le réglage
    # neutre) — demande explicite "rajoute la valeur de zoom du slide ou
    # fait un 'cran' qd on arrive à zéro" : sur les 200px du curseur, 0.03
    # correspond à ~3px, assez large pour "accrocher" au clic/glissé sans
    # empêcher de viser une valeur proche mais non nulle.
    VIDEO_ZOOM_SNAP_EPSILON = 0.03

    def _video_on_zoom_change(self, *_args):
        """Trace sur video_crop_zoom : happe la valeur sur 0.0 si le curseur
        est relâché tout près (voir VIDEO_ZOOM_SNAP_EPSILON), met à jour
        l'affichage numérique du pourcentage à côté du curseur, puis
        redimensionne le rectangle ROI affiché (taille seulement, centre
        conservé) pour refléter en direct le nouveau niveau de zoom, sans
        attendre "Générer Aperçu"."""
        z = self.video_crop_zoom.get()
        if abs(z) < self.VIDEO_ZOOM_SNAP_EPSILON and z != 0.0:
            self.video_crop_zoom.set(0.0)
            return  # le set() ci-dessus redéclenche cette même trace avec z=0.0
        pct = round(z * 100)
        self.video_crop_zoom_value_var.set("0%" if pct == 0 else f"{pct:+d}%")
        if self.video_ref_frame is not None and self.video_roi is not None:
            fw, fh = self.video_ref_frame.size
            x, y, w, h = self.video_roi
            cx, cy = x + w / 2, y + h / 2
            self.video_roi = VideoEngine.roi_rect_for_zoom(
                (fw, fh), (cx, cy), self._video_effective_zoom()
            )
            self._video_draw_roi_rect()
        self._video_update_crop_preview()
        self._video_update_gif_info()

    def _video_on_resize_auto_toggle(self):
        """Désactive le curseur "Zoom cadrage" manuel tant que
        `video_resize_auto` est vrai (la valeur n'est de toute façon plus
        utilisée dans ce cas, voir _video_effective_zoom) et applique
        immédiatement le nouveau zoom effectif au rectangle affiché.
        `video_resize_auto` est désormais un booléen DÉRIVÉ du sélecteur
        "Mode de cadrage" (voir _video_on_crop_mode_change), plus une case à
        cocher indépendante."""
        state = "disabled" if self.video_resize_auto.get() else "normal"
        self.video_crop_zoom_scale.configure(state=state)
        self._video_on_zoom_change()

    def _video_on_crop_mode_change(self, *_args):
        """Sélecteur "Mode de cadrage" (3 boutons radio mutuellement
        exclusifs) — remplace les 2 anciennes cases indépendantes "🎯 Suivi
        automatique"/"🪄 Resize auto" et leur logique de forçage/grisage
        croisé, jugée peu lisible par l'utilisateur ("le mode zoom auto et
        tracking auto s'excluent l'un l'autre... peut-être clarifier ce
        fonctionnement ?"). `video_roi_tracking_enabled`/`video_resize_auto`
        restent calculés ici comme des booléens DÉRIVÉS (voir __init__) :
        tout le reste du code (pipeline, _video_effective_zoom,
        _video_draw_roi_rect, _video_roi_start, etc.) continue de les lire
        sans changement — seul CE handler et _video_update_point_buttons_state/
        _video_roi_reset distinguent explicitement les 3 modes.

        - "tracking" : comportement ORIGINAL simple — un seul rectangle
          dessiné par l'utilisateur, suivi automatiquement par le tracker
          OpenCV sur TOUTE la vidéo. Pas de repositionnement manuel, pas de
          système de points. Taille de crop calculée automatiquement
          (resize auto forcé).
        - "auto_zoom" (nouveau) : l'utilisateur positionne un cadrage
          unique à la main (glisser le rectangle), mais sa TAILLE est
          calculée automatiquement (resize auto forcé, comme "tracking").
          Pas de tracker OpenCV, pas de système de points multiples.
        - "manual" : les 2 automatismes désactivés — système de points
          (zones multiples + zoom keyframé, "➕ Point ici" etc.) ET curseur
          "Zoom cadrage" pilotés entièrement à la main.

        Dans "tracking" et "auto_zoom", tout point/zoom keyframe existant
        est effacé au passage dans le mode, pour repartir d'un état propre
        plutôt que de laisser des points orphelins silencieusement ignorés
        par le pipeline (ambiguïté déjà signalée par le passé : "si je
        recoche tracking auto le mode zoom ne disparaît pas donc je ne
        peux pas délimiter ma zone d'intérêt")."""
        mode = self.video_crop_mode.get()
        # Toute bascule de mode annule un dessin en attente suite à "➕
        # Point ici" (n'a plus de sens si le mode change entre-temps).
        self._video_awaiting_point_draw = False
        self.video_roi_tracking_enabled.set(mode == "tracking")
        self.video_resize_auto.set(mode in ("tracking", "auto_zoom"))
        self._video_on_resize_auto_toggle()

        if mode == "tracking":
            self.video_roi_events = []
            self.video_zoom_keyframes = []
            self.video_roi = None
        else:
            if mode == "auto_zoom":
                self.video_roi_events = []
                self.video_zoom_keyframes = []
            # "auto_zoom" et "manual" partagent le même comportement de
            # matérialisation "staging" du rectangle unique quand rien
            # n'existe encore (uniquement dans self.video_roi, pas commité
            # dans video_roi_events — la création d'un point en "manual"
            # reste une action explicite via "➕ Point ici").
            if (
                not self.video_roi_events
                and self.video_roi is None
                and self.video_ref_frame is not None
            ):
                self.video_roi = self._video_default_roi_rect(self.video_ref_frame.size)

        self._video_draw_roi_rect()
        self._video_update_crop_preview()
        self._video_update_keyframes_status()
        self._video_redraw_roi_events()
        self._video_update_roi_history_text()
        self._video_commit_roi_history()
        self._video_update_point_buttons_state()
        self._video_update_gif_info()

    def _video_update_point_buttons_state(self):
        """Active/désactive les boutons de gestion des points de zone/zoom
        selon le mode courant — le système de points n'existe QUE dans le
        mode "✋ Manuel" du sélecteur "Mode de cadrage" (ni "🎯 Suivi
        automatique", ni "🪄 Cadrage auto (zoom)", qui n'utilisent jamais de
        points, voir _video_on_crop_mode_change). "🔄 Recentrer" n'est PAS
        concerné, il reste toujours actif (triple comportement selon le
        mode, voir _video_roi_reset)."""
        state = "normal" if self.video_crop_mode.get() == "manual" else "disabled"
        for btn in (
            self.roi_add_point_btn,
            self.roi_add_zoom_btn,
            self.roi_delete_point_btn,
            self.roi_clear_points_btn,
            self.roi_undo_btn,
            self.roi_redo_btn,
        ):
            btn.configure(state=state)

    def _video_clamp_roi_edit_time(self):
        """Contraint video_roi_edit_time à rester dans [trim_start, trim_end]
        (le marqueur de temps de cadrage doit toujours rester À L'INTÉRIEUR
        de la sélection trim, demande explicite) puis redessine les 3
        marqueurs — appelé au chargement d'une vidéo et à chaque changement
        de trim (poignées ou Spinbox "Durée")."""
        if not self.video_meta:
            return
        start = self.video_trim_start.get()
        end = self.video_trim_end.get()
        if end <= start:
            end = start + 0.01
        clamped = max(start, min(end, self.video_roi_edit_time.get()))
        if clamped != self.video_roi_edit_time.get():
            self.video_roi_edit_time.set(clamped)
        self._video_redraw_trim_handles()

    def generate_video_preview(self):
        """Bouton "🎬 Générer Aperçu" : lance le pipeline complet en thread
        séparé pour ne pas geler l'UI (pattern identique à process_images)."""
        if not self.video_path:
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"),
                lang_manager.get("video_load_first_warning", "Chargez d'abord une vidéo"),
            )
            return
        if self.video_processing:
            return
        self.video_processing = True
        self.video_animating = False
        threading.Thread(target=self._video_pipeline, daemon=True).start()

    def _video_pipeline(self):
        """Pipeline complet (thread) : trim → échantillonnage temporel →
        extraction (cv2) → tracking ROI + calcul de crop par frame (si ROI
        défini) → qualité auto (si cochée) → resize/pixel-perfect DMD →
        nettoyage. Toute mise à jour UI passe par root.after(0, ...) (pattern
        process_images)."""
        try:
            start = self.video_trim_start.get()
            end = self.video_trim_end.get()
            if end - start <= 0:
                raise RuntimeError("Plage de trim invalide (durée nulle)")
            fps = self.video_fps.get()

            self.root.after(0, lambda: self.update_progress(0, tr("t_extracting_frames", "Extraction des frames...")))
            timestamps = VideoEngine.sample_frame_timestamps(
                start, end, self.video_meta["fps"], fps
            )
            src_frames = VideoEngine.extract_frames_at(self.video_path, timestamps)

            zoom = self._video_effective_zoom()
            crop_windows = None
            # Timeline unifiée de points de zone (auto/manuel) — voir
            # VideoEngine.compute_crop_windows_from_events. Rétrocompatibilité
            # workflow simple : si aucun point n'a encore été explicitement
            # ajouté ("➕ Point ici"/"🔄 Recentrer") mais qu'un ROI est
            # dessiné, il est traité comme un point unique implicite au mode
            # de la case "🎯 Suivi automatique" — comportement identique à
            # avant l'introduction de la timeline multi-points.
            events = self.video_roi_events or (
                [{
                    "t": self.video_trim_start.get()
                    if self.video_roi_tracking_enabled.get()
                    else self.video_roi_edit_time.get(),
                    "roi": self.video_roi,
                    "mode": "auto" if self.video_roi_tracking_enabled.get() else "manual",
                }]
                if self.video_roi is not None
                else []
            )
            if events:
                self.root.after(
                    0, lambda: self.update_progress(30, tr("t_framing_roi", "Cadrage de la zone d'intérêt..."))
                )
                # Zoom keyframé dans le temps si ≥2 points de zoom existent
                # (interpolation linéaire sur tous les timestamps
                # échantillonnés), sinon le scalaire global unique comme
                # avant — voir VideoEngine.interpolate_zoom_keyframes.
                zoom_values = (
                    VideoEngine.interpolate_zoom_keyframes(timestamps, self.video_zoom_keyframes)
                    if len(self.video_zoom_keyframes) >= 2
                    else zoom
                )
                crop_windows = VideoEngine.compute_crop_windows_from_events(
                    src_frames, timestamps, events, zoom=zoom_values
                )
            # sinon : aucun point de zone -> pas de crop du tout
            # (comportement historique, crop_windows reste None).

            settings = None
            if self.video_quality_auto.get():
                sample_idxs = sorted(
                    {0, len(src_frames) // 2, len(src_frames) - 1}
                )
                settings = VideoEngine.auto_quality_settings(
                    [src_frames[i] for i in sample_idxs]
                )

            self.root.after(0, lambda: self.update_progress(60, tr("t_dmd_render", "Rendu DMD...")))
            pixel_perfect = self._get_force_pixel_perfect()
            out_frames = []
            for i, frame in enumerate(src_frames):
                if crop_windows is not None:
                    x0, y0, cw, ch = crop_windows[i]
                    if cw > 0 and ch > 0:
                        frame = frame.crop((x0, y0, x0 + cw, y0 + ch))
                if settings is not None:
                    frame = DMDEngine.optimize_for_dmd(frame, settings)
                resized, rw, rh = DMDEngine.adaptive_resize(
                    frame,
                    128,
                    32,
                    # "fit" (pas "fill") : voir _video_update_crop_preview
                    # pour la justification complète — nécessaire pour que
                    # zoom<1.0 affiche le crop entier en letterbox au lieu
                    # d'en recadrer l'excédent.
                    mode="fit" if crop_windows is not None else "auto",
                    pixel_perfect=pixel_perfect,
                )
                canvas_frame = Image.new("RGB", (128, 32), (0, 0, 0))
                canvas_frame.paste(resized, ((128 - rw) // 2, (32 - rh) // 2))
                canvas_frame = DMDEngine.cleanup_dmd_frame(canvas_frame, power=0.5)
                out_frames.append(canvas_frame)
                pct = 60 + int(30 * (i + 1) / len(src_frames))
                self.root.after(0, lambda p=pct: self.update_progress(p, tr("t_dmd_render", "Rendu DMD...")))

            self.video_frames = out_frames

            self.root.after(0, lambda: self.update_progress(95, tr("t_estimating_size", "Estimation du poids...")))
            try:
                size_bytes = estimate_gif_size(
                    out_frames,
                    fps=fps,
                    color_count=self.color_count_var.get(),
                    loop_mode=self.manual_loop_mode.get(),
                    loop_count=self.manual_loop_count.get(),
                    disposal=2,
                    optimize=False,
                )
                size_kb = size_bytes / 1024
                size_str = (
                    f"~{size_kb:.0f} Ko" if size_kb < 1024 else f"~{size_kb / 1024:.1f} Mo"
                )
            except Exception as size_err:
                logger.error(f"Erreur estimation poids GIF: {size_err}")
                size_str = "?"

            self.root.after(0, lambda s=size_str: self._video_pipeline_done(s))
        except Exception as e:
            # Capturer le message avant la lambda différée (voir même correctif
            # dans _video_load_thumbnails_and_ref) : "as e" ne survit pas à la
            # sortie du except, une lambda qui la référence lève NameError au
            # moment où root.after() l'exécute réellement.
            error_msg = str(e)
            logger.error(f"Erreur pipeline vidéo: {error_msg}")
            self.root.after(
                0,
                lambda msg=error_msg: messagebox.showerror(
                    lang_manager.get("error", "Erreur"),
                    f"{lang_manager.get('err_video_processing', 'Erreur traitement vidéo')}: {msg}",
                ),
            )
        finally:
            self.video_processing = False

    def _video_pipeline_done(self, size_str="—"):
        self.update_progress(100, tr("t_preview_ready", "Aperçu prêt"))
        self.video_status.set(tr("t_frames_generated", "{n} frames générées", n=len(self.video_frames)))
        self.video_gif_size_var.set(size_str)
        # self.video_frames n'est pas une tk.Variable (pas de trace possible)
        # : rafraîchi explicitement ici pour que "Frames"/"Poids estimé"
        # passent de l'estimation à la valeur RÉELLE de cette génération.
        self._video_update_gif_info()
        self.video_frame_idx = 0
        self.video_animating = True
        self.animate_video_preview()

    def animate_video_preview(self):
        """Animation de la preview vidéo — copie fidèle de
        animate_manual_preview (même mécanisme LED/classique selon "Mode DMD
        / Forcer pixel-perfect", voir cette méthode pour le détail)."""
        if not self.video_animating or not self.video_frames:
            return
        try:
            frame = self.video_frames[self.video_frame_idx]
            if self._get_force_pixel_perfect():
                display = DMDEngine.render_led_style(
                    frame,
                    scale=4,
                    led_ratio=0.525,
                    glow=True,
                    brightness=self.led_brightness_var.get(),
                )
            else:
                display = frame.resize((512, 128), Image.Resampling.NEAREST)
            self.video_preview_photo = ImageTk.PhotoImage(display)
            self.video_preview_canvas.delete("all")
            self.video_preview_canvas.create_image(
                256, 64, image=self.video_preview_photo
            )

            self.video_frame_idx = (self.video_frame_idx + 1) % len(self.video_frames)
            delay = int(1000 / self.video_fps.get())
            self._anim_schedule("video", delay, self.animate_video_preview)
        except Exception:
            self.video_animating = False

    def video_export(self):
        """Exporte le GIF vidéo (bouton "💾 Exporter GIF")."""
        if not self.video_frames:
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"),
                lang_manager.get("generate_preview_first_warning", "Générez d'abord un aperçu"),
            )
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".gif", filetypes=[("GIF", "*.gif")]
        )
        if not file_path:
            return

        try:
            export_frames_to_gif(
                self.video_frames,
                file_path,
                fps=self.video_fps.get(),
                color_count=self.color_count_var.get(),
                loop_mode=self.manual_loop_mode.get(),
                loop_count=self.manual_loop_count.get(),
                disposal=2,
                optimize=False,
            )
            file_size = Path(file_path).stat().st_size / 1024
            quality_line = self._export_quality_line(self.video_frames, self.video_fps.get(), file_path)
            messagebox.showinfo(
                lang_manager.get("success", "Succès"),
                f"{lang_manager.get('gif_exported', 'GIF exporté')}: {Path(file_path).name}\n{file_size:.1f} KB"
                + quality_line,
            )
            logger.info(f"Export vidéo: {Path(file_path).name}, {file_size:.1f} KB")
        except Exception as e:
            messagebox.showerror(
                lang_manager.get("error", "Erreur"), f"{lang_manager.get('err_export', 'Erreur export')}: {e}"
            )
            logger.error(f"Erreur export vidéo: {e}")

    def setup_textscroll_tab(self):
        """Configuration onglet TEXTSCROLL avec effets avancés"""
        main_frame = ttk.Frame(self.textscroll_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left: Params
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Text input
        text_frame = ttk.LabelFrame(left_panel, text="Texte", padding="5")
        text_frame.pack(fill=tk.X, pady=(0, 10))

        self.text_input = tk.Text(text_frame, height=4, width=50, wrap=tk.WORD)
        self.text_input.pack(fill=tk.X)
        self.text_input.insert(
            1.0, lang_manager.get("your_text_here", "Votre texte ici...")
        )
        self.text_input.bind("<FocusIn>", self.clear_text_placeholder)
        self.text_input.bind("<FocusOut>", self.restore_text_placeholder)

        # Font
        font_frame = ttk.LabelFrame(left_panel, text="Police", padding="5")
        font_frame.pack(fill=tk.X, pady=(0, 10))

        row1 = ttk.Frame(font_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text="Famille:").pack(side=tk.LEFT)
        self.text_font_family = tk.StringVar(value="Arial")

        # Récupérer vraies polices système
        # TOUTES les polices système (sans filtrage)
        available_fonts = self._get_usable_fonts()
        ttk.Combobox(
            row1,
            textvariable=self.text_font_family,
            values=available_fonts,
            state="readonly",
            width=20,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(row1, text="Taille:").pack(side=tk.LEFT, padx=(20, 5))
        self.text_font_size = tk.IntVar(value=config_manager.get("text_font_size", 20))
        self.text_font_size.trace_add(
            "write",
            lambda *args: _save_var("text_font_size", self.text_font_size),
        )
        ttk.Spinbox(
            row1, from_=8, to=48, textvariable=self.text_font_size, width=10
        ).pack(side=tk.LEFT)

        row2 = ttk.Frame(font_frame)
        row2.pack(fill=tk.X, pady=2)

        self.text_bold = tk.BooleanVar()
        ttk.Checkbutton(row2, text="Gras", variable=self.text_bold).pack(
            side=tk.LEFT, padx=5
        )

        self.text_italic = tk.BooleanVar()
        ttk.Checkbutton(row2, text="Italique", variable=self.text_italic).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(row2, text="Couleur texte", command=self.choose_text_color).pack(
            side=tk.LEFT, padx=20
        )
        self.text_color = (255, 255, 255)
        self.text_color_preview = Canvas(row2, width=30, height=20, bg="white")
        self.text_color_preview.pack(side=tk.LEFT, padx=5)

        # Effets texte
        effects_frame = ttk.LabelFrame(left_panel, text="Effets Texte", padding="5")
        effects_frame.pack(fill=tk.X, pady=(0, 10))

        row1 = ttk.Frame(effects_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text="Effet:").pack(side=tk.LEFT)
        self.text_effect = tk.StringVar(value="normal")
        text_effects = [
            "normal",
            "3d",
            "fire",
            "snow",
            "ice",
            "metal",
            "neon",
            "graffiti",
            "pixel_art",
            "outline",
            "shadow",
        ]
        ttk.Combobox(
            row1,
            textvariable=self.text_effect,
            values=text_effects,
            state="readonly",
            width=15,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(row1, text="Couleur fond", command=self.choose_text_bg).pack(
            side=tk.LEFT, padx=20
        )
        self.text_bg_color = (0, 0, 0)
        self.text_bg_preview = Canvas(row1, width=30, height=20, bg="black")
        self.text_bg_preview.pack(side=tk.LEFT, padx=5)

        # Effets couleur
        row2 = ttk.Frame(effects_frame)
        row2.pack(fill=tk.X, pady=2)

        color_effect_label = ttk.Label(row2, text="Effet couleur:")
        color_effect_label.pack(side=tk.LEFT)
        add_help_tooltip(color_effect_label, "tooltip_color_effect")
        self.text_color_effect = tk.StringVar(value="none")
        color_effects = ["none", "rainbow", "matrix", "fire", "gradient"]
        ttk.Combobox(
            row2,
            textvariable=self.text_color_effect,
            values=color_effects,
            state="readonly",
            width=15,
        ).pack(side=tk.LEFT, padx=5)

        # Animation
        anim_frame = ttk.LabelFrame(left_panel, text="Animation", padding="5")
        anim_frame.pack(fill=tk.X, pady=(0, 10))

        row1 = ttk.Frame(anim_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text="Type:").pack(side=tk.LEFT)
        self.text_anim_type = tk.StringVar(value="scroll_horizontal")
        text_anims = [
            "scroll_horizontal",
            "scroll_vertical",
            "scroll_wave",
            "starwars",
            "bounce_scroll",
            "typewriter",
            "explode",
            "matrix_rain",
            "spiral",
            "shake",
            "glitch",
            "fade_in",
            "static",
        ]
        ttk.Combobox(
            row1,
            textvariable=self.text_anim_type,
            values=text_anims,
            state="readonly",
            width=20,
        ).pack(side=tk.LEFT, padx=5)

        row2 = ttk.Frame(anim_frame)
        row2.pack(fill=tk.X, pady=2)

        ttk.Label(row2, text="FPS:").pack(side=tk.LEFT)
        self.text_fps = tk.IntVar(value=config_manager.get("text_fps", 10))
        self.text_fps.trace_add(
            "write", lambda *args: _save_var("text_fps", self.text_fps)
        )
        ttk.Spinbox(row2, from_=1, to=60, textvariable=self.text_fps, width=10).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Label(row2, text="Vitesse:").pack(side=tk.LEFT, padx=(20, 5))
        self.text_speed = tk.IntVar(value=config_manager.get("text_speed", 2))
        self.text_speed.trace_add(
            "write",
            lambda *args: _save_var("text_speed", self.text_speed),
        )
        ttk.Spinbox(row2, from_=1, to=10, textvariable=self.text_speed, width=10).pack(
            side=tk.LEFT
        )

        ttk.Label(row2, text="Durée (s):").pack(side=tk.LEFT, padx=(20, 5))
        self.text_duration = tk.DoubleVar(
            value=config_manager.get("text_duration", 3.0)
        )
        self.text_duration.trace_add(
            "write",
            lambda *args: _save_var("text_duration", self.text_duration),
        )
        ttk.Spinbox(
            row2,
            from_=1.0,
            to=30,
            increment=0.5,
            textvariable=self.text_duration,
            width=10,
        ).pack(side=tk.LEFT)

        ttk.Checkbutton(
            row2,
            text=lang_manager.get("auto_adjust", "Auto-ajuster"),
            variable=tk.BooleanVar(value=True),
        ).pack(side=tk.LEFT, padx=20)

        row3 = ttk.Frame(anim_frame)
        row3.pack(fill=tk.X, pady=2)

        # Case partagée avec les onglets AUTO et MANUEL (self.pixel_perfect_var,
        # créée dans setup_auto_tab) : pilote le rendu LED de animate_text_preview.
        text_pixel_perfect_check = ttk.Checkbutton(
            row3,
            text="Mode DMD / Forcer pixel-perfect",
            variable=self.pixel_perfect_var,
            command=self.on_global_param_change,
        )
        text_pixel_perfect_check.pack(side=tk.LEFT)
        add_help_tooltip(text_pixel_perfect_check, "tooltip_pixel_perfect")

        # Right: Preview
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH)

        preview_frame = ttk.LabelFrame(
            right_panel,
            text=lang_manager.get("preview_animation", "Aperçu Animation"),
            padding="5",
        )
        preview_frame.pack(fill=tk.BOTH, expand=False)

        text_preview_row = ttk.Frame(preview_frame)
        text_preview_row.pack(pady=10)

        self.text_preview_canvas = Canvas(
            text_preview_row, width=512, height=128, bg="black"
        )
        self.text_preview_canvas.pack(side=tk.LEFT)
        self._add_led_zoom_icon(
            self.text_preview_canvas,
            get_frames=lambda: self.text_frames,
            get_idx=lambda: self.text_frame_idx,
            get_fps=lambda: self.text_fps.get(),
            title="Aperçu Animation (Texte)",
        )
        self._add_led_brightness_slider(text_preview_row).pack(
            side=tk.LEFT, padx=(10, 0)
        )

        # Boutons juste sous la fenêtre de preview (déplacés depuis le panneau
        # gauche, demandé explicitement — plus cohérent avec MANUEL où
        # "Prévisualiser" est déjà sous son propre canvas de preview).
        btn_frame = ttk.Frame(preview_frame)
        btn_frame.pack(pady=5)

        ttk.Button(
            btn_frame, text="🎬 Générer Preview", command=self.generate_text_preview
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame, text="💾 Exporter GIF", command=self.export_text_gif
        ).pack(side=tk.LEFT, padx=5)

        self.text_preview_status = tk.StringVar(
            value=lang_manager.get("enter_text_generate", "Entrez du texte et générez")
        )
        ttk.Label(
            preview_frame,
            textvariable=self.text_preview_status,
            font=("Arial", 9, "italic"),
        ).pack(pady=5)

        # Infos GIF
        self.text_gif_info = tk.StringVar(value="")
        ttk.Label(
            preview_frame, textvariable=self.text_gif_info, font=("Arial", 8)
        ).pack(pady=5)

        # Appliquer police à la zone texte en temps réel
        self.text_font_family.trace_add(
            "write", lambda *args: self.apply_font_to_textbox()
        )
        self.text_font_size.trace_add(
            "write", lambda *args: self.apply_font_to_textbox()
        )
        self.text_bold.trace_add("write", lambda *args: self.apply_font_to_textbox())
        self.text_italic.trace_add("write", lambda *args: self.apply_font_to_textbox())

        # Appliquer police initiale
        self.apply_font_to_textbox()

    def setup_params_tab(self):
        """Configuration onglet PARAMETRES"""
        main_frame = ttk.Frame(self.params_frame, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # LANGUE
        lang_frame = ttk.LabelFrame(
            main_frame, text="🌍 Langue / Language / Idioma", padding="10"
        )
        lang_frame.pack(fill=tk.X, pady=(0, 20))

        self.lang_var = tk.StringVar(value=lang_manager.current_lang)

        ttk.Radiobutton(
            lang_frame,
            text="🇫🇷 Français",
            variable=self.lang_var,
            value="fr",
            command=self.change_language,
        ).pack(anchor=tk.W, pady=5)
        ttk.Radiobutton(
            lang_frame,
            text="🇬🇧 English",
            variable=self.lang_var,
            value="en",
            command=self.change_language,
        ).pack(anchor=tk.W, pady=5)
        ttk.Radiobutton(
            lang_frame,
            text="🇪🇸 Español",
            variable=self.lang_var,
            value="es",
            command=self.change_language,
        ).pack(anchor=tk.W, pady=5)

        # Thème
        theme_frame = ttk.LabelFrame(main_frame, text="Apparence", padding="10")
        theme_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(theme_frame, text="Thème:").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            theme_frame,
            text="🌙 Sombre",
            variable=self.theme,
            value="dark",
            command=self.apply_theme,
        ).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(
            theme_frame,
            text="☀️ Clair",
            variable=self.theme,
            value="light",
            command=self.apply_theme,
        ).pack(side=tk.LEFT, padx=10)

        # Comportement
        behavior_frame = ttk.LabelFrame(main_frame, text="Comportement", padding="10")
        behavior_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Checkbutton(
            behavior_frame,
            text="Ajouter type d'animation au nom de fichier",
            variable=self.add_anim_to_name,
        ).pack(anchor=tk.W, pady=5)

        # Export
        export_frame = ttk.LabelFrame(main_frame, text="Export", padding="10")
        export_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(export_frame, text="Qualité par défaut:").pack(anchor=tk.W, pady=5)

        quality_frame = ttk.Frame(export_frame)
        quality_frame.pack(fill=tk.X, pady=5)

        ttk.Label(quality_frame, text="Couleurs GIF:").pack(side=tk.LEFT)
        self.default_colors = tk.IntVar(value=config_manager.get("default_colors", 256))
        self.default_colors.trace_add(
            "write",
            lambda *args: _save_var("default_colors", self.default_colors),
        )
        ttk.Combobox(
            quality_frame,
            textvariable=self.default_colors,
            values=[str(v) for v in (8, 16, 32, 64, 128, 256)],
            state="readonly",
            width=10,
        ).pack(side=tk.LEFT, padx=5)

        # Cache
        cache_frame = ttk.LabelFrame(main_frame, text="Performance", padding="10")
        cache_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Checkbutton(
            cache_frame, text="Activer cache IA", variable=tk.BooleanVar(value=True)
        ).pack(anchor=tk.W, pady=5)

        ttk.Button(cache_frame, text="🗑️ Vider cache", command=self.clear_cache).pack(
            anchor=tk.W, pady=5
        )

        # Logs
        logs_frame = ttk.LabelFrame(main_frame, text="Logs", padding="10")
        logs_frame.pack(fill=tk.X)

        ttk.Checkbutton(
            logs_frame,
            text="Sauvegarder logs automatiquement",
            variable=tk.BooleanVar(value=False),
        ).pack(anchor=tk.W, pady=5)

        ttk.Button(logs_frame, text="📄 Exporter logs", command=self.export_logs).pack(
            anchor=tk.W, pady=5
        )

    def change_language(self):
        """Change la langue de l'interface"""
        new_lang = self.lang_var.get()
        lang_manager.set_language(new_lang)
        self.apply_translations()
        logger.info(f"Langue changée: {new_lang}")

        msg_restart = {
            "fr": "Veuillez redémarrer l'application pour appliquer la nouvelle langue.",
            "en": "Please restart the application to apply the new language.",
            "es": "Por favor reinicie la aplicación para aplicar el nuevo idioma.",
        }

    def setup_debug_tab(self):
        """Configuration onglet DEBUG"""
        main_frame = ttk.Frame(self.debug_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(toolbar, text="🗑️ Effacer logs", command=self.clear_logs).pack(
            side=tk.LEFT, padx=5
        )

        self.autoscroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Auto-scroll", variable=self.autoscroll_var).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Label(toolbar, text="Filtrer:").pack(side=tk.LEFT, padx=(20, 5))
        self.log_filter = tk.StringVar(value="ALL")
        log_filter_combo = ttk.Combobox(
            toolbar,
            textvariable=self.log_filter,
            values=["ALL", "INFO", "WARNING", "ERROR", "DEBUG"],
            state="readonly",
            width=10,
        )
        log_filter_combo.pack(side=tk.LEFT)
        # Bug corrige (signale par l'utilisateur) : changer le filtre ne
        # rafraichissait jamais l'affichage deja present, seules les NOUVELLES
        # lignes de log en tenaient compte (add_log_entry ne filtre qu'a
        # l'insertion). <<ComboboxSelected>> ne se declenche que sur un vrai
        # changement de valeur (pas a l'ouverture/fermeture de la liste).
        log_filter_combo.bind(
            "<<ComboboxSelected>>", lambda e: self._rebuild_log_display()
        )

        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_frame,
            wrap=tk.NONE,
            height=5,
            bg="#1a1a1a",
            fg="#00ff00",
            font=("Courier", 9),
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        log_scroll = ttk.Scrollbar(
            log_frame, orient=tk.VERTICAL, command=self.log_text.yview
        )
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)

        self.log_text.tag_config("INFO", foreground="#00ff00")
        self.log_text.tag_config("WARNING", foreground="#ffaa00")
        self.log_text.tag_config("ERROR", foreground="#ff0000")
        self.log_text.tag_config("DEBUG", foreground="#00aaff")

        logger.callbacks.append(self.add_log_entry)

    # ========================================================================
    # ONGLET AIDE
    # ========================================================================

    def setup_help_tab(self):
        """Configuration onglet AIDE — affiche lisezmoi*.md (rendu Markdown via
        RecalBoxDMD_md_renderer, réutilisé tel quel depuis le projet RecalBox_DMD)
        dans la langue actuellement sélectionnée (onglet PARAMÈTRES)."""
        main_frame = ttk.Frame(self.help_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        self.help_title_label = ttk.Label(
            toolbar, text="AIDE", font=("Arial", 12, "bold")
        )
        self.help_title_label.pack(side=tk.LEFT)

        ttk.Button(
            toolbar,
            text=lang_manager.get(
                "help_open_browser_btn", "🌐 Ouvrir dans le navigateur"
            ),
            command=self._open_help_in_browser,
        ).pack(side=tk.RIGHT)

        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        help_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        help_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.help_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            borderwidth=0,
            yscrollcommand=help_scroll.set,
        )
        self.help_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        help_scroll.config(command=self.help_text.yview)
        # Bloque la saisie clavier sans désactiver le widget (state="disabled"
        # empêcherait tag_bind sur les liens de continuer à réagir aux clics).
        self.help_text.bind("<Key>", lambda e: "break")

        self._refresh_help_tab_content()

    def _help_readme_path(self):
        """Chemin du fichier lisezmoi*.md correspondant à la langue actuelle
        (self.lang_var, onglet PARAMÈTRES) : fr → lisezmoi.md, en → lisezmoi_en.md,
        es → lisezmoi_es.md. Toujours à côté de ce script (pas de dossier fixe,
        compatible exécution depuis un dossier différent)."""
        lang = self.lang_var.get() if getattr(self, "lang_var", None) else "fr"
        names = {
            "en": "lisezmoi_en.md",
            "es": "lisezmoi_es.md",
        }
        readme_name = names.get(lang, "lisezmoi.md")
        base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
        return base_dir / readme_name

    def _refresh_help_tab_content(self):
        """(Re)charge et affiche le lisezmoi*.md correspondant à la langue
        actuelle. Appelé au premier affichage de l'onglet et à chaque
        changement de langue (voir apply_translations/change_language)."""
        if not getattr(self, "help_text", None):
            return

        readme_path = self._help_readme_path()
        try:
            readme_text = readme_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            readme_text = f"Impossible de lire {readme_path.name} : {e}"
            logger.error(f"Aide: {readme_text}")

        if getattr(self, "help_title_label", None):
            self.help_title_label.config(text=tr("t_help_title", "AIDE ({name})", name=readme_path.name))

        md_renderer.render_markdown_in_text(
            self.help_text,
            readme_text,
            on_external_link=lambda url: webbrowser.open_new_tab(url),
            on_anchor_link=self._help_scroll_to_anchor,
            base_dir=readme_path.parent,
        )

    def _help_scroll_to_anchor(self, anchor):
        """Fait défiler l'onglet AIDE jusqu'à l'ancre cliquée (lien interne du
        menu en tête de lisezmoi*.md). Cherche d'abord une mark exacte posée par
        le renderer sur chaque titre, puis une recherche texte en repli."""
        import unicodedata as _ud

        def _norm(s):
            n = _ud.normalize("NFKD", s.lower().replace("-", " ").replace("_", " "))
            n = "".join(c for c in n if not _ud.combining(c))
            n = "".join(c if c.isalnum() or c == " " else " " for c in n)
            return " ".join(n.split())

        try:
            tw = self.help_text
            anchor_norm = _norm(anchor)

            if ("anchor_" + anchor) in tw.mark_names():
                tw.see("anchor_" + anchor)
                return

            for mn in tw.mark_names():
                if mn.startswith("anchor_") and _norm(mn[7:]) == anchor_norm:
                    tw.see(mn)
                    return

            for q in (anchor, anchor.replace("-", " ").replace("_", " ")):
                pos = tw.search(q, "1.0", stopindex="end", nocase=True)
                if pos:
                    tw.see(pos)
                    return
        except Exception:
            pass

    def _open_help_in_browser(self):
        """Ouvre le lisezmoi*.md correspondant à la langue actuelle dans le
        navigateur par défaut (rendu Markdown natif du navigateur si association
        de fichier configurée, sinon affichage brut — comportement du système)."""
        readme_path = self._help_readme_path()
        try:
            webbrowser.open_new_tab(str(readme_path.resolve()))
        except Exception as e:
            open_err_label = lang_manager.get("err_open_file", "Impossible d'ouvrir")
            messagebox.showerror(
                lang_manager.get("error", "Erreur"),
                f"{open_err_label} {readme_path.name} : {e}",
            )
            logger.error(f"Aide: ouverture navigateur échouée: {e}")

    # ========================================================================
    # HELPERS UI
    # ========================================================================

    def create_quit_button(self, parent):
        quit_btn = ttk.Button(parent, text="Quitter", command=self.root.destroy)
        quit_btn.pack(side=tk.RIGHT, padx=10, pady=10)

    def create_slider(self, parent, label, from_, to, default, var_name):
        """Crée un slider avec label et valeur"""
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text=label, width=12).pack(side=tk.LEFT)
        var = tk.DoubleVar(value=default)
        setattr(self, var_name, var)
        ttk.Scale(
            row,
            from_=from_,
            to=to,
            variable=var,
            command=lambda v: self.apply_manual_effect(),
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        value_label = ttk.Label(row, text=f"{default:.2f}", width=5)
        value_label.pack(side=tk.LEFT)
        var.trace_add(
            "write", lambda *args: value_label.config(text=f"{var.get():.2f}")
        )

    def _insert_log_line(self, entry):
        """Insère une ligne de log déjà formatée, SANS filtrage — le filtrage est
        décidé par l'appelant (add_log_entry pour le flux temps réel,
        _rebuild_log_display pour une reconstruction complète)."""
        self.log_text.insert(tk.END, f"[{entry['time']}] ", "INFO")
        self.log_text.insert(tk.END, f"{entry['level']}: ", entry["level"])
        self.log_text.insert(tk.END, f"{entry['message']}\n")

    def add_log_entry(self, entry):
        """Ajoute une entrée de log dans l'interface (flux temps réel, une entrée
        à la fois — voir _rebuild_log_display pour un changement de filtre après
        coup, qui doit re-filtrer tout l'historique déjà affiché)."""
        filter_level = self.log_filter.get()
        if filter_level != "ALL" and entry["level"] != filter_level:
            return

        self._insert_log_line(entry)

        if self.autoscroll_var.get():
            self.log_text.see(tk.END)

    def _rebuild_log_display(self):
        """Reconstruit entièrement l'affichage des logs depuis logger.logs (tout
        l'historique, pas seulement ce qui a été inséré depuis l'ouverture de
        l'onglet) selon le niveau de filtre actuellement sélectionné. Bug corrigé
        (signalé par l'utilisateur) : changer le niveau dans le menu déroulant ne
        rafraîchissait jusqu'ici jamais l'affichage — seules les lignes arrivant
        APRÈS le changement en tenaient compte (add_log_entry ne filtre qu'à
        l'insertion), la page gardait donc le niveau précédent affiché."""
        self.log_text.delete(1.0, tk.END)
        filter_level = self.log_filter.get()
        for entry in logger.logs:
            if filter_level != "ALL" and entry["level"] != filter_level:
                continue
            self._insert_log_line(entry)
        if self.autoscroll_var.get():
            self.log_text.see(tk.END)

    def clear_logs(self):
        """Efface tous les logs"""
        self.log_text.delete(1.0, tk.END)
        logger.logs.clear()
        logger.info("Logs effacés")

    def apply_theme(self):
        """Applique le thème sélectionné"""
        theme = self.theme.get()
        config_manager.set("theme", theme)

        style = ttk.Style()

        # Onglets en colonne latérale gauche (v21) : libère la hauteur qu'occupait la
        # barre d'onglets horizontale (~30-40px, voir TAB_STRIP_GAIN dans setup_ui) au
        # profit du contenu, en échange d'une largeur supplémentaire à gauche pour la
        # colonne d'onglets. Appliqué aux 2 branches de thème ci-dessous.
        TAB_POSITION = "wn"

        if theme == "dark":
            style.theme_use("clam")
            style.configure(
                ".",
                background="#2b2b2b",
                foreground="white",
                fieldbackground="#404040",
                bordercolor="#404040",
                insertcolor="white",
            )
            style.configure("TLabel", background="#2b2b2b", foreground="white")
            style.configure("TFrame", background="#2b2b2b")
            style.configure("TLabelframe", background="#2b2b2b", foreground="white")
            style.configure(
                "TLabelframe.Label", background="#2b2b2b", foreground="white"
            )
            style.configure("TButton", background="#404040", foreground="white")
            style.map("TButton", background=[("active", "#505050")])
            style.configure(
                "TNotebook", background="#2b2b2b", tabposition=TAB_POSITION
            )
            style.configure("TNotebook.Tab", background="#404040", foreground="white")
            style.map("TNotebook.Tab", background=[("selected", "#505050")])

            # Treeview (liste d'images) — sans ce style, la liste reste au thème clair
            # par défaut (illisible sur fond sombre).
            style.configure(
                "Treeview",
                background="#404040",
                foreground="white",
                fieldbackground="#404040",
                borderwidth=0,
            )
            style.map(
                "Treeview",
                background=[("selected", "#0078d7")],
                foreground=[("selected", "white")],
            )

            # Champs de saisie
            style.configure(
                "TEntry",
                fieldbackground="#404040",
                foreground="white",
                insertcolor="white",
            )
            style.map(
                "TEntry",
                fieldbackground=[("readonly", "#404040"), ("disabled", "#404040")],
            )
            style.map(
                "TEntry", foreground=[("readonly", "white"), ("disabled", "#888888")]
            )

            style.configure(
                "TSpinbox",
                fieldbackground="#404040",
                foreground="white",
                insertcolor="white",
            )
            style.map(
                "TSpinbox",
                fieldbackground=[("readonly", "#404040"), ("disabled", "#404040")],
            )
            style.map(
                "TSpinbox", foreground=[("readonly", "white"), ("disabled", "#888888")]
            )

            style.configure(
                "TCombobox",
                fieldbackground="#404040",
                foreground="white",
                insertcolor="white",
            )
            style.map(
                "TCombobox",
                fieldbackground=[("readonly", "#404040"), ("disabled", "#404040")],
            )
            style.map(
                "TCombobox", foreground=[("readonly", "white"), ("disabled", "#888888")]
            )

            # Widgets Tkinter natifs
            self.root.option_add("*Entry*background", "#404040")
            self.root.option_add("*Entry*foreground", "white")
            self.root.option_add("*Entry*insertBackground", "white")
            self.root.option_add("*Entry*disabledBackground", "#404040")
            self.root.option_add("*Entry*disabledForeground", "#888888")
            self.root.option_add("*Text*background", "#404040")
            self.root.option_add("*Text*foreground", "white")
            self.root.option_add("*Text*insertBackground", "white")
            self.root.option_add("*Listbox*background", "#404040")
            self.root.option_add("*Listbox*foreground", "white")

            self.root.configure(bg="#2b2b2b")
        else:
            style.theme_use("default")
            style.configure("TNotebook", tabposition=TAB_POSITION)
            self.root.configure(bg="#f0f0f0")

        # Onglet AIDE (v32) : contrairement aux autres Text natifs de l'app
        # (colorés uniquement via option_add, donc jamais retouchés une fois
        # créés — limitation préexistante, voir changelog v31), help_text est
        # explicitement reconfiguré à CHAQUE appel de apply_theme (thème
        # initial et bascule manuelle dans PARAMÈTRES) puisqu'il doit rester
        # lisible dans les deux thèmes. Le rendu est ensuite refait (pas
        # seulement recoloré) : les couleurs d'accent du Markdown (liens,
        # citations, tableaux) sont calculées par le renderer À PARTIR de ces
        # bg/fg au moment du rendu, donc un simple .configure() sans nouveau
        # rendu laisserait les anciennes couleurs d'accent (thème précédent).
        if getattr(self, "help_text", None):
            if theme == "dark":
                help_bg, help_fg = "#404040", "white"
            else:
                help_bg, help_fg = "white", "black"
            self.help_text.configure(
                bg=help_bg, fg=help_fg, insertbackground=help_fg
            )
            self._refresh_help_tab_content()

        logger.info(f"Thème appliqué: {theme}")

    def on_tab_changed(self, event):
        """Callback changement d'onglet"""
        current_tab = self.notebook.index(self.notebook.select())

        # Si passage à MANUEL, charger image AUTO si sélectionnée
        if current_tab == 1 and self.current_image_idx is not None:
            self.load_from_auto()

    def select_folder(self):
        """Ajoute les images d'un dossier source (scan récursif, tous sous-dossiers)"""
        folder = filedialog.askdirectory()
        if folder:
            self.load_images_from_folder(folder)

    def select_images(self):
        """Ajoute des images individuelles à la liste existante"""
        files = filedialog.askopenfilenames(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.raw565")]
        )
        if files:
            added = self._add_image_paths(files)
            self.update_listbox()
            logger.info(f"{added} image(s) ajoutée(s) ({len(files)} sélectionnée(s))")

    def load_images_from_folder(self, folder):
        """Ajoute les images trouvées dans un dossier (scan récursif, tous
        sous-dossiers). Mémorise le dossier comme racine pour la reconstruction
        d'arborescence relative en sortie (voir process_images).
        v82 : scan en arrière-plan (voir _scan_folders_async)."""
        self.source_root_dir = folder
        self._scan_folders_async([folder])

    # v82 -- extensions reconnues au scan d'un dossier (une seule passe)
    _SCAN_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".raw565"}

    def _scan_folder_for_images(self, folder, counter=None, offset=0):
        """Recherche les fichiers image d'un dossier, TOUJOURS récursivement (tous
        sous-dossiers). Le chargement étant additif et chaque entrée supprimable
        individuellement de la liste (Suppr/menu contextuel), une case "Récursif"
        désélectionnable n'apportait plus rien et créait un piège silencieux :
        déposer/choisir un dossier ne contenant que des sous-dossiers renvoyait 0
        image trouvée en mode non récursif.
        v82 : UNE seule passe os.walk pour toutes les extensions (avant : 6
        glob("**/*.ext") successifs = 6 parcours complets de l'arborescence).
        Chemins normalisés (os.path.normpath) comme le faisait Path.glob, triés
        pour un ordre stable. counter : liste [n] mise à jour pendant le scan
        (lue par le thread Tk pour le compteur d'avancement). Aucun appel Tk ici :
        appelable depuis un thread."""
        found = []
        for dirpath, dirs, files in os.walk(folder):
            # v87 -- GIF mis de côté par "Revoir" : jamais rechargés
            dirs[:] = [d for d in dirs if d != dq.REVIEW_DIR]
            for fn in files:
                if os.path.splitext(fn)[1].lower() in self._SCAN_IMAGE_EXTS:
                    found.append(os.path.normpath(os.path.join(dirpath, fn)))
            if counter is not None:
                counter[0] = offset + len(found)
        found.sort()
        return found

    def _add_image_paths(self, paths):
        """Ajoute des chemins d'image à self.images en évitant les doublons.
        Retourne le nombre de nouvelles entrées effectivement ajoutées.
        v82 : doublons testés dans un set (avant : `p not in self.images` sur
        une liste = n²/2 comparaisons, ~1,5 milliard pour 54 777 images)."""
        existing = set(self.images)
        added = 0
        for p in paths:
            p = str(p)
            if p not in existing:
                existing.add(p)
                self.images.append(p)
                added += 1
        return added

    def _scan_folders_async(self, folders):
        """v82 -- scanne `folders` dans un thread et ajoute le résultat à la liste
        une fois fini, sans bloquer la fenêtre (retour utilisateur : dossier
        systems/ de 54 777 images -> fenêtre "Ne répond pas" pendant plusieurs
        minutes). Compteur d'avancement dans la barre de titre. Un seul scan à
        la fois (un nouveau dossier demandé pendant un scan est refusé et
        signalé dans le journal)."""
        if getattr(self, "_folder_scan_running", False):
            logger.warning("Scan de dossier déjà en cours -- attendez la fin avant d'en lancer un autre")
            return
        self._folder_scan_running = True
        counter = [0]
        result = {}
        base_title = self.root.title()
        try:
            self.root.config(cursor="watch")
        except tk.TclError:
            pass

        def work():
            found = []
            try:
                for folder in folders:
                    found.extend(
                        self._scan_folder_for_images(folder, counter=counter, offset=len(found))
                    )
            except Exception as e:  # remonté au thread Tk
                result["error"] = e
            result["found"] = found

        worker = threading.Thread(target=work, daemon=True)
        worker.start()

        def poll():
            if worker.is_alive():
                msg = lang_manager.get("scanning_images", "Recherche d'images… {n}")
                try:
                    self.root.title(f"{base_title} — {msg.replace('{n}', str(counter[0]))}")
                except tk.TclError:
                    return
                self.root.after(200, poll)
                return
            try:
                self.root.title(base_title)
                self.root.config(cursor="")
            except tk.TclError:
                pass
            self._folder_scan_running = False
            if "error" in result:
                logger.error(f"Scan de dossier interrompu : {result['error']}")
            found = result.get("found", [])
            added = self._add_image_paths(found)
            self.update_listbox()
            logger.info(
                f"{len(found)} image(s) trouvée(s) dans {', '.join(folders)} ({added} nouvelle(s))"
            )

        self.root.after(200, poll)

    def clear_image_list(self):
        """Vide la liste d'images chargées (ne touche pas aux fichiers sur disque)."""
        self.images = []
        self.source_root_dir = None
        self.update_listbox()
        logger.info("Liste d'images vidée")

    def _show_image_tree_menu(self, event):
        """Affiche le menu contextuel (clic droit) sur la liste d'images.
        Bug réel corrigé (audit i18n complet) : les entrées de tk.Menu ne
        sont PAS des widgets enfants au sens de winfo_children(), donc
        jamais atteintes par le parcours récursif de _update_widget_texts —
        seul un ré-étiquetage explicite ICI, juste avant l'affichage,
        permet de refléter la langue courante."""
        iid = self.image_tree.identify_row(event.y)
        if iid and iid not in self.image_tree.selection():
            self.image_tree.selection_set(iid)
        if self.image_tree.selection():
            self.image_tree_menu.entryconfig(
                0, label=lang_manager.get("remove_from_list_menu", "🗑 Retirer de la liste")
            )
            self.image_tree_menu.tk_popup(event.x_root, event.y_root)

    def remove_selected_images(self):
        """Retire de la liste les images actuellement sélectionnées (touche Suppr ou
        menu contextuel) — ne touche pas aux fichiers sur disque."""
        selected_indices = sorted(
            (int(iid) for iid in self.image_tree.selection()), reverse=True
        )
        if not selected_indices:
            return

        removed = 0
        for idx in selected_indices:
            if 0 <= idx < len(self.images):
                img_path = self.images.pop(idx)
                self.manual_exports.discard(img_path)
                self.image_settings.pop(img_path, None)
                removed += 1

        self.update_listbox()
        logger.info(f"{removed} image(s) retirée(s) de la liste")

    def on_files_dropped(self, event):
        """Glisser-déposer de fichiers/dossiers sur la zone Images (tkinterdnd2).
        Un dossier déposé est scanné comme self.select_folder (toujours récursif) ;
        un fichier image est ajouté directement. Ajout additif comme les boutons
        Dossier/Images. Un fichier vidéo (VIDEO_EXTS, v104) est routé vers
        l'onglet VIDEO (_video_load_from_path), quel que soit l'onglet actif au
        moment du dépôt — comportement déterministe basé sur l'extension plutôt
        que sur l'onglet visible."""
        image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".raw565"}
        video_exts = set(VIDEO_EXTS)
        paths = self.root.tk.splitlist(event.data)

        added_total = 0
        folders = []
        for p in paths:
            path_obj = Path(p)
            if path_obj.is_dir():
                self.source_root_dir = str(path_obj)
                folders.append(str(path_obj))
            elif path_obj.is_file() and path_obj.suffix.lower() in video_exts:
                self._video_load_from_path(str(path_obj))
            elif path_obj.is_file() and path_obj.suffix.lower() in image_exts:
                added_total += self._add_image_paths([str(path_obj)])

        self.update_listbox()
        logger.info(
            f"Glisser-déposer: {added_total} image(s) ajoutée(s) "
            f"({len(folders)} dossier(s) à scanner)"
        )
        # v82 -- dossiers déposés scannés en arrière-plan (voir _scan_folders_async)
        if folders:
            self._scan_folders_async(folders)

    def update_listbox(self):
        """Met à jour la liste d'images (Treeview). Affiche le chemin relatif au
        dossier racine chargé (self.source_root_dir) quand l'image se trouve dans un
        sous-dossier, pour distinguer les fichiers de même nom en mode récursif."""
        self.image_tree.delete(*self.image_tree.get_children())

        root = Path(self.source_root_dir) if self.source_root_dir else None

        for i, img in enumerate(self.images):
            img_path = Path(img)
            display_name = img_path.name
            if root:
                try:
                    rel = img_path.relative_to(root)
                    if rel.parent != Path("."):
                        display_name = str(rel)
                except ValueError:
                    pass

            prefix = ""
            tag = ""
            if img in self.manual_exports:
                prefix = "✓ "
                tag = "manual_export"
            elif img in self.image_settings:
                prefix = "⚙ "
                tag = "configured"

            self.image_tree.insert(
                "",
                tk.END,
                iid=str(i),
                text=prefix + display_name,
                tags=(tag,) if tag else (),
            )

        self.image_tree.tag_configure("manual_export", foreground="green")
        self.image_tree.tag_configure("configured", foreground="orange")

        if self.images:
            self.image_tree_hint.place_forget()
        else:
            self.image_tree_hint.place(relx=0.5, rely=0.5, anchor="center")

        self.progress_text_var.set(
            tr("t_status_counts", "{n} images | {m} manuelles", n=len(self.images), m=len(self.manual_exports))
        )

    def reauthorize_image(self):
        """Réautorise une image exclue (retirée des exports manuels)"""
        selection = self.image_tree.selection()
        if not selection:
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"),
                lang_manager.get("select_one_image_warning", "Sélectionnez une image"),
            )
            return

        img_path = self.images[int(selection[0])]
        if img_path in self.manual_exports:
            self.manual_exports.remove(img_path)
            self.update_listbox()
            reauthorized_suffix = lang_manager.get("reauthorized_suffix", "réautorisée pour traitement AUTO")
            messagebox.showinfo(
                lang_manager.get("success", "Succès"),
                f"{Path(img_path).name} {reauthorized_suffix}",
            )
            logger.info(f"Réautorisée: {Path(img_path).name}")
        else:
            not_excluded_msg = lang_manager.get("image_not_excluded", "Cette image n'est pas exclue")
            messagebox.showinfo(lang_manager.get("info", "Info"), not_excluded_msg)

    def on_image_select(self, event):
        """Callback sélection d'image dans la liste"""
        selection = self.image_tree.selection()
        if selection:
            idx = int(selection[0])
            self.current_image_idx = idx
            img_path = self.images[idx]

            self.animating = False
            threading.Thread(
                target=lambda: self.auto_analyze_and_preview(img_path), daemon=True
            ).start()

    def on_global_param_change(self):
        """Callback changement paramètres globaux - relance IA"""
        if self.current_image_idx is not None:
            img_path = self.images[self.current_image_idx]
            threading.Thread(
                target=lambda: self.auto_analyze_and_preview(img_path), daemon=True
            ).start()

    def show_original(self, image_path):
        """Affiche l'image originale"""
        img_orig = DMDEngine.load_image(image_path)

        # Préserver le fond noir pour les PNG avec transparence
        if (
            img_orig.mode in ("RGBA", "LA")
            or img_orig.info.get("transparency") is not None
        ):
            img_rgba = img_orig.convert("RGBA")
            background = Image.new("RGB", img_rgba.size, (0, 0, 0))
            background.paste(img_rgba, mask=img_rgba.split()[-1])
            img_orig = background
        else:
            img_orig = img_orig.convert("RGB")

        w, h = img_orig.size
        scale = min(640 / w, 130 / h)
        display_w, display_h = int(w * scale), int(h * scale)
        img_display = img_orig.resize((display_w, display_h), Image.Resampling.LANCZOS)

        self.preview_original = ImageTk.PhotoImage(img_display)
        self.canvas_original.delete("all")
        self.canvas_original.create_image(320, 65, image=self.preview_original)

    def update_image_info(self, image_path):
        """Met à jour les informations de l'image"""
        img = DMDEngine.load_image(image_path)
        file_size = Path(image_path).stat().st_size / 1024  # KB

        # Détecter palette
        palette = DMDEngine.detect_palette(img, max_colors=8)
        palette_str = ", ".join([f"RGB{c}" for c in palette[:3]]) + "..."

        info = tr(
            "t_image_info", K_DEFAULT_IMAGE_INFO,
            name=Path(image_path).name, fmt=img.format, w=img.size[0], h=img.size[1],
            mode=img.mode, size=file_size, palette=palette_str, ratio=img.size[0] / img.size[1],
        )

        self.info_text.config(state="normal")
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info)
        self.info_text.config(state="disabled")

    def auto_analyze_and_preview(self, image_path):
        """Analyse IA et génération des propositions : #1 meilleur resize (fit),
        #2 meilleur fill/scroll, #3 variante optimisée (nettoyage +/- fort,
        pixel-perfect si ça améliore le rendu) de la proposition retenue entre les
        deux premières, #4-6 artistiques (2 effets curatés selon les caractéristiques
        de l'image + 1 pioché au hasard dans le reste du pool pour l'exploration).
        Choix des 3 premières basé sur 2 critères : occupation de l'affichage et
        lisibilité (voir dmd_pipeline_quality.score_variant)."""
        try:
            self.ia_status_var.set(tr("t_analyzing", "🔍 Analyse en cours..."))
            self.root.update()

            # Afficher original et infos
            self.show_original(image_path)
            self.update_image_info(image_path)

            img = DMDEngine.crop_to_visible_content(DMDEngine.load_image(image_path))
            analysis = {"size": img.size}

            self.ia_status_var.set(tr("t_eval_resize_fill", "🤖 Évaluation resize vs fill..."))
            self.root.update()

            force_pixel_perfect = self._get_force_pixel_perfect()

            fit_variants = self.generate_settings_variants(analysis, "fit")
            fill_variants = self.generate_settings_variants(analysis, "fill")

            # Cache partagé (2026-08-06, Tier 0 plan perf batch) -- même
            # bénéfice ici que dans get_settings_for_image() : accélère aussi
            # l'aperçu interactif Auto/IA, scopé à cette seule image.
            variant_cache = {}

            fit_score, fit_settings, fit_canvas = self._best_variant(
                img, fit_variants, pixel_perfect=force_pixel_perfect, resize_cache=variant_cache
            )
            fit_settings = {**fit_settings, "name": tr("t_prop_resize", "Resize (adapté)")}
            fill_score, fill_settings, fill_canvas = self._best_variant(
                img, fill_variants, pixel_perfect=force_pixel_perfect, resize_cache=variant_cache
            )
            fill_settings = {**fill_settings, "name": tr("t_prop_fill", "Fill (scrolling)")}

            self.ia_status_var.set(tr("t_optimizing", "🧹 Optimisation nettoyage / pixel-perfect..."))
            self.root.update()

            # v86 : règle de forme, identique au lot (voir
            # dmd_pipeline_quality.shape_forces_fill) -- remplace le garde-fou
            # lettres (resize_will_shrink_text_too_much), qui forçait Fill sur
            # 75 % des logos presque carrés, souvent reconnaissables en Resize.
            min_ratio = self._get_fill_min_ratio()  # v91 : None = option du profil décochée
            shape_fill = bool(min_ratio) and _shape_forces_fill(img.size, min_ratio)
            if shape_fill:
                retained_settings = fill_settings
                logger.info("Logo large — Fill/scroll imposé par la forme")
            elif fit_score >= fill_score:
                retained_settings = fit_settings
            else:
                retained_settings = fill_settings

            opt_score, opt_settings, opt_canvas = (
                self._optimize_cleanup_and_pixel_perfect(
                    img,
                    retained_settings,
                    force_pixel_perfect=force_pixel_perfect,
                    resize_cache=variant_cache,
                )
            )
            # v85 : libellé traduit (dmd_pipeline_quality nomme la variante "Optimisé")
            opt_settings = {**opt_settings, "name": tr("t_prop_optimized", "Optimisé")}

            # v90 : logo sombre monochrome -> même décision que le lot
            # (dmd_pipeline_quality.maybe_invert_dark : inversé seulement si le
            # score qualité du rendu gagne au moins 3 points)
            bp = self.batch_params_snapshot()
            inverted = _maybe_invert_dark(
                image_path, img, opt_settings, lambda inv: _resolve_from_image(inv, bp)
            ) if bp["invert_dark"] else None
            dark_inverted = inverted is not None
            if dark_inverted:
                opt_settings = {**inverted, "name": tr("t_prop_optimized", "Optimisé")}
                opt_canvas, _ = _render_dmd_frame(
                    image_path, opt_settings, cleanup_power=opt_settings.get("cleanup_power", 1.0),
                    pixel_perfect=bool(opt_settings.get("_pixel_perfect", False)),
                )
                logger.info("Logo sombre — version inversée retenue (score qualité supérieur)")

            self.ia_status_var.set(tr("t_generating_artistic", "🎨 Génération propositions artistiques..."))
            self.root.update()

            # Les propositions artistiques partent de la proposition au score le plus
            # élevé (opt_settings, "Optimisé") pour garder son scrolling/pixel-perfect
            # — mémorisé pour permettre au bouton "New proposition" de relancer un
            # choix artistique sans refaire toute l'analyse.
            self._ai_base_settings = opt_settings
            self._ai_image_path = image_path

            safe_effect, dynamic_effect = self._choose_artistic_effects(opt_canvas)
            # 3e proposition artistique : pioche exploratoire dans le reste du pool
            # (exclut les 2 effets déjà curatés) pour offrir une option différente des
            # 2 choix "raisonnés" plutôt qu'une simple redite.
            explore_effect = self._pick_random_artistic_effect(
                exclude={safe_effect, dynamic_effect}
            )
            artistic1_settings, artistic1_canvas = self._generate_artistic_proposal(
                image_path, opt_settings, safe_effect
            )
            artistic2_settings, artistic2_canvas = self._generate_artistic_proposal(
                image_path, opt_settings, dynamic_effect
            )
            artistic3_settings, artistic3_canvas = self._generate_artistic_proposal(
                image_path, opt_settings, explore_effect
            )

            self.proposals = [
                (fit_score, fit_settings, fit_canvas),
                (fill_score, fill_settings, fill_canvas),
                (opt_score, opt_settings, opt_canvas),
                (None, artistic1_settings, artistic1_canvas),
                (None, artistic2_settings, artistic2_canvas),
                (None, artistic3_settings, artistic3_canvas),
            ]
            # v91 -- options de rendu du profil (plafond d'aller-retour) sur
            # toutes les propositions : l'aperçu animé et l'export les suivent
            self.proposals = [
                (s, _apply_render_profile(v, bp), c) for s, v, c in self.proposals
            ]

            # Réinitialiser tous les emplacements de proposition
            for j in range(len(self.proposal_canvases)):
                self.proposal_canvases[j].delete("all")
                self.proposal_labels[j].config(text=tr("t_proposal_n", "Proposition {n}", n=j + 1))
                self.proposal_info_labels[j].config(text="")

            for i, (score, variant, canvas) in enumerate(self.proposals):
                display = canvas.resize((384, 96), Image.Resampling.NEAREST)
                photo = ImageTk.PhotoImage(display)
                self.proposal_canvases[i].delete("all")
                self.proposal_canvases[i].create_image(192, 48, image=photo)
                self.proposal_canvases[i].image = photo

                score_text = f"{score:.2f}" if score is not None else "—"
                self.proposal_labels[i].config(
                    text=f"{i+1}. {variant['name']} (score: {score_text})"
                )

                # Afficher infos paramètres détaillées
                info_text = f"Score: {score_text}\n"
                if variant.get("_artistic_effect"):
                    info_text += tr(
                        "t_prop_info_artistic", "Effet : {effect} | Mode resize : {resize}\nFPS : {fps} | Durée : {dur}s",
                        effect=variant["_artistic_effect"], resize=variant["resize_mode"],
                        fps=variant["fps"], dur=variant.get("duration", 2.0),
                    )
                else:
                    info_text += tr(
                        "t_prop_info_tuning",
                        "Contraste : {c:.2f} | Saturation : {s:.2f}\nLuminosité : {b:.2f} | Seuil noir : {bt}\nNettoyage : {cl:.1f}",
                        c=variant["contrast"], s=variant["saturation"], b=variant.get("brightness", 1.0),
                        bt=variant["black_threshold"], cl=variant.get("cleanup_power", 1.0),
                    )
                    if variant.get("_pixel_perfect"):
                        info_text += tr("t_prop_info_pp", " | Pixel-perfect : activé")
                    info_text += "\n"
                    info_text += tr(
                        "t_prop_info_motion",
                        "FPS : {fps} | Vitesse : {speed}\nMode resize : {resize} | Direction : {dir}",
                        fps=variant["fps"], speed=variant["scroll_speed"],
                        resize=variant["resize_mode"], dir=variant["direction"],
                    )
                self.proposal_info_labels[i].config(text=info_text)

            # Sélectionner par défaut la proposition optimisée (la plus aboutie)
            self.selected_proposal = 2
            self.highlight_proposal(2)

            # Sauvegarder settings
            self.image_settings[image_path] = self.proposals[2][1].copy()

            best_settings = self.image_settings[image_path]

            base_note = (
                tr("t_shape_forces_fill", " (logo large → Fill imposé)")
                if shape_fill else ""
            )
            if dark_inverted:
                base_note += tr("t_dark_inverted", " (logo sombre → inversé)")
            self.ia_status_var.set(
                tr(
                    "t_retained", "✓ '{name}' retenu (score : {score}), base : {base}{note}",
                    name=opt_settings["name"], score=f"{opt_score:.2f}",
                    base=retained_settings["name"], note=base_note,
                )
            )

            # Lancer preview animé
            self.start_continuous_preview(image_path, best_settings)
            logger.info(f"Analyse terminée: {Path(image_path).name}")

        except Exception as e:
            self.ia_status_var.set(tr("t_error_msg", "❌ Erreur : {err}", err=e))
            logger.error(f"Erreur analyse: {e}")

    def generate_settings_variants(self, analysis, resize_mode):
        """Génère des variantes de paramètres pour UN mode de redimensionnement
        (fit ou fill), à évaluer indépendamment via score_variant. Générer les 2
        modes séparément (plutôt qu'un pool mélangé) évite qu'un mode ne domine
        structurellement le classement de l'autre.

        Wrapper fin (2026-08-06, Tier 2 plan perf batch) : lit les tk.Variable
        puis délègue à dmd_pipeline_quality.generate_settings_variants (version
        pure, réutilisable par un worker ProcessPoolExecutor qui ne peut pas
        lire self/Tk — voir process_one_image()). Comportement strictement
        inchangé, algorithme déplacé tel quel, pas dupliqué."""
        return _generate_settings_variants(
            analysis["size"],
            resize_mode,
            self.fps_var.get(),
            self.duration_var.get(),
            self.scroll_speed_var.get(),
            self.contrast_var.get(),
            self.saturation_var.get(),
        )

    def _get_force_pixel_perfect(self):
        """Lit la case globale "Force pixel-perfect". Lue UNE FOIS par analyse et
        propagée explicitement (clé "_pixel_perfect") à toutes les propositions, pour
        qu'une proposition déjà générée ne change jamais de comportement si la case
        est togglée ensuite sans relancer l'analyse (source unique de vérité, pas de
        double vérification au moment du rendu)."""
        try:
            return bool(self.pixel_perfect_var.get())
        except Exception:
            return False

    def _add_led_brightness_slider(self, parent):
        """Slider vertical "Luminosité LED" (0-100%, défaut 50%), partagé entre
        les 3 onglets de génération via self.led_brightness_var (propriété du
        panneau physique simulé, pas un réglage par onglet — même logique que
        pixel_perfect_var). Simule le réglage de luminosité d'un vrai panneau
        LED : voir DMDEngine.render_led_style, paramètre brightness."""
        frame = ttk.Frame(parent)

        ttk.Label(frame, text="💡", font=("Arial", 11)).pack(pady=(0, 2))
        # Texte initial calculé depuis la valeur RÉELLE de la variable (pas
        # "50%" en dur) : sinon, si led_brightness_var a été chargée depuis
        # config.json avec une valeur différente du défaut, le curseur
        # s'affiche à sa vraie position mais le texte reste bloqué sur "50%"
        # jusqu'au premier déplacement — décalage signalé par l'utilisateur.
        pct_label = ttk.Label(
            frame,
            text=f"{int(self.led_brightness_var.get() * 100)}%",
            font=("Arial", 8),
        )
        pct_label.pack(pady=(0, 2))
        scale = ttk.Scale(
            frame,
            from_=1.0,
            to=0.0,
            variable=self.led_brightness_var,
            orient=tk.VERTICAL,
            length=100,
        )
        scale.pack()
        self.led_brightness_var.trace_add(
            "write",
            lambda *a: pct_label.config(
                text=f"{int(self.led_brightness_var.get() * 100)}%"
            ),
        )
        # Sauvegarde uniquement au relâchement du curseur (pas à chaque
        # variation pendant le glissement, signalé comme trop fréquent) —
        # bindé sur cette instance du widget car le slider existe en 3
        # exemplaires (un par onglet) sur la même variable partagée.
        scale.bind(
            "<ButtonRelease-1>",
            lambda e: config_manager.set(
                "led_brightness", self.led_brightness_var.get()
            ),
        )
        add_help_tooltip(frame, "tooltip_led_brightness")
        return frame

    def _add_led_zoom_icon(self, canvas, get_frames, get_idx, get_fps, title):
        """Icône loupe apparaissant au survol du canvas de preview (uniquement
        si Mode DMD / pixel-perfect est coché — sinon pas de rendu LED à
        zoomer) : clic = ouvre un aperçu agrandi animé, voir
        _open_led_zoom_window. get_frames/get_idx/get_fps sont des callables
        (pas des valeurs figées à l'attachement) pour toujours lire l'état
        live de l'onglet appelant, y compris pendant l'animation en cours.
        Le hide est différé (after 150ms, annulé si la souris entre sur
        l'icône) car en Tkinter déplacer la souris du canvas vers un widget
        enfant placé dessus déclenche quand même <Leave> sur le canvas —
        sans ce délai, l'icône disparaîtrait juste avant qu'on puisse cliquer
        dessus."""
        icon = tk.Label(
            canvas,
            text="🔍",
            font=("Arial", 14),
            bg="#222222",
            fg="white",
            cursor="hand2",
            padx=4,
            pady=2,
        )
        hide_job = {"id": None}

        def cancel_hide():
            if hide_job["id"] is not None:
                canvas.after_cancel(hide_job["id"])
                hide_job["id"] = None

        def show_icon(event=None):
            if not self._get_force_pixel_perfect():
                return
            cancel_hide()
            icon.place(relx=1.0, rely=0.0, anchor="ne", x=-4, y=4)
            canvas.config(cursor="hand2")

        def schedule_hide(event=None):
            cancel_hide()
            hide_job["id"] = canvas.after(150, icon.place_forget)
            canvas.config(cursor="")

        def open_zoom(event=None):
            if not self._get_force_pixel_perfect():
                return
            self._open_led_zoom_window(get_frames, get_idx, get_fps, title)

        canvas.bind("<Enter>", show_icon, add="+")
        canvas.bind("<Leave>", schedule_hide, add="+")
        # Toute la zone de preview ouvre le zoom au clic, pas seulement
        # l'icône 🔍 (demande explicite de l'utilisateur) — même garde-fou
        # (Mode DMD coché) que l'icône.
        canvas.bind("<Button-1>", open_zoom, add="+")
        icon.bind("<Enter>", show_icon)
        icon.bind("<Leave>", schedule_hide)
        icon.bind("<Button-1>", open_zoom)
        add_help_tooltip(icon, "tooltip_led_zoom")

    def _open_led_zoom_window(self, get_frames, get_idx, get_fps, title):
        """Ouvre une fenêtre séparée montrant le rendu LED agrandi (scale=8)
        de l'aperçu en cours, avec sa propre boucle d'animation qui relit en
        direct la même liste de frames que l'aperçu normal — reste
        synchronisée automatiquement sans dupliquer la génération d'animation
        ni le rendu LED principal."""
        if not get_frames():
            messagebox.showinfo(
                lang_manager.get("info", "Info"),
                lang_manager.get("generate_preview_first_warning", "Générez d'abord un aperçu"),
            )
            return

        zoom_win = tk.Toplevel(self.root)
        zoom_win.title(f"🔍 {title}")
        zoom_win.resizable(False, False)
        ZOOM_SCALE = 8
        canvas_w, canvas_h = 128 * ZOOM_SCALE, 32 * ZOOM_SCALE
        zoom_canvas = Canvas(zoom_win, width=canvas_w, height=canvas_h, bg="black")
        zoom_canvas.pack(padx=10, pady=10)

        state = {"running": True, "photo": None}

        def refresh():
            if not state["running"]:
                return
            try:
                frames_now = get_frames()
                if frames_now:
                    idx = get_idx() % len(frames_now)
                    display = DMDEngine.render_led_style(
                        frames_now[idx],
                        scale=ZOOM_SCALE,
                        led_ratio=0.525,
                        brightness=self.led_brightness_var.get(),
                    )
                    state["photo"] = ImageTk.PhotoImage(display)
                    zoom_canvas.delete("all")
                    zoom_canvas.create_image(
                        canvas_w // 2, canvas_h // 2, image=state["photo"]
                    )
                fps = get_fps() or 10
                zoom_win.after(int(1000 / fps), refresh)
            except tk.TclError:
                state["running"] = False

        def on_close():
            state["running"] = False
            zoom_win.destroy()

        zoom_win.protocol("WM_DELETE_WINDOW", on_close)
        refresh()

    def _best_variant(self, img, variants, pixel_perfect=False, resize_cache=None):
        """Retourne (score, settings, canvas) de la meilleure variante (score le plus
        haut) parmi une liste, selon score_variant. Le choix pixel_perfect est
        explicitement gravé dans les settings retournés (clé "_pixel_perfect").
        `resize_cache` (optionnel) : propagé tel quel à score_variant().

        Wrapper fin (2026-08-06, Tier 2) : délègue à
        dmd_pipeline_quality.best_variant (version pure). self.score_variant
        (méthode) et le score_variant module-level utilisé par la version pure
        sont le MÊME calcul (voir _pipeline_score_variant) — aucune divergence
        possible entre le chemin UI et le chemin worker parallèle."""
        return _best_variant_pure(img, variants, pixel_perfect=pixel_perfect, resize_cache=resize_cache)

    # _TONAL_REFINEMENT_PARAMS : alias vers dmd_pipeline_quality.
    # TONAL_REFINEMENT_PARAMS, posé APRÈS la définition de la classe (voir
    # bloc de délégation en fin de fichier, "DMDConverter._TONAL_REFINEMENT_
    # PARAMS = ...") -- un import module-level utilisé ici directement dans
    # le corps de la classe s'exécuterait AVANT l'import en bas de fichier,
    # NameError. Même contrainte que le monkey-patch déjà en place pour
    # score_variant/render_dmd_frame.

    def _optimize_cleanup_and_pixel_perfect(
        self, img, base_settings, force_pixel_perfect=False, resize_cache=None
    ):
        """Affine une variante déjà retenue (proposition "Optimisé") en 2 étapes :
        balayage de puissance de nettoyage puis descente par coordonnées tonale
        (contraste/saturation/luminosité/seuil noir) pour rapprocher le rendu de
        la fidélité à l'original, sans jamais dégrader le score occupation+
        lisibilité affiché. Voir dmd_pipeline_quality.optimize_cleanup_and_pixel_perfect
        pour la docstring complète (raisonnement détaillé du garde-fou score/
        fidélité) et l'implémentation.

        Wrapper fin (2026-08-06, Tier 2 plan perf batch) : algorithme déplacé
        tel quel dans la version pure (réutilisable par process_one_image(),
        worker ProcessPoolExecutor), pas dupliqué."""
        return _optimize_cleanup_and_pixel_perfect_pure(
            img, base_settings, force_pixel_perfect=force_pixel_perfect, resize_cache=resize_cache
        )

    # Effets pris en charge par ManualEffects.apply_over_frames (superposables à une
    # animation de base déjà rendue - voir dmd_manual_effects.py)
    _ARTISTIC_EFFECT_POOL = (
        "color_shift_effect",
        "fade_effect",
        "wave_effect",
        "glitch_effect",
        "pulse_effect",
        "spiral_effect",
        "zoom_effect",
    )

    def _choose_artistic_effects(self, canvas):
        """Choisit 2 effets artistiques (mode manuel) adaptés au contenu de l'image :
        1 effet "sûr" qui préserve la forme (peu de risque pour la lisibilité) et 1
        effet "dynamique" plus marqué, sélectionnés selon la densité de contours
        (texte/logo net vs contenu plus organique) et la coloration de l'image."""
        chars = self.analyze_characteristics(canvas)
        crisp = chars["edge_density"] > 15.0
        colorful = chars["colorfulness"] > 0.35

        if crisp:
            safe = "color_shift_effect" if colorful else "fade_effect"
            dynamic = "wave_effect" if colorful else "glitch_effect"
        else:
            safe = "pulse_effect"
            dynamic = "spiral_effect" if chars["occupation"] > 0.15 else "zoom_effect"

        return safe, dynamic

    def _pick_random_artistic_effect(self, exclude=None):
        """Choisit un effet artistique au hasard dans le pool complet, en excluant si
        possible l'effet déjà affiché (utilisé par le bouton "New proposition")."""
        exclude = exclude or set()
        candidates = [e for e in self._ARTISTIC_EFFECT_POOL if e not in exclude]
        if not candidates:
            candidates = list(self._ARTISTIC_EFFECT_POOL)
        return random.choice(candidates)

    def _generate_artistic_proposal(self, image_path, base_settings, effect_name):
        """Génère une proposition artistique : superpose un effet du mode manuel à
        l'animation de la variante de base (resize_mode/direction/scroll/pixel-perfect
        conservés tels quels — voir ManualEffects.apply_over_frames). Retourne
        (settings, frame_aperçu)."""
        label = effect_name.replace("_effect", "").replace("_", " ").capitalize()
        settings = {
            **base_settings,
            "name": tr("t_prop_artistic", "Artistique : {label}", label=label),
            "_artistic_effect": effect_name,
        }
        frames, _fps = self.render_dmd_frame(
            image_path, settings, return_frames=True, cleanup_power=0.0
        )
        preview_frame = frames[len(frames) // 2].convert("RGB")
        return settings, preview_frame

    def regenerate_artistic_proposal(self, idx):
        """Relance un nouveau choix artistique pour la proposition idx (4, 5 ou 6),
        sans refaire toute l'analyse resize/fill/optimisation. Bouton "New
        proposition", remplace le verrouillage pour lot sur ces 3 propositions."""
        if not self._ai_base_settings or not self._ai_image_path:
            return
        if idx >= len(self.proposals):
            return

        current_effect = self.proposals[idx][1].get("_artistic_effect")
        new_effect = self._pick_random_artistic_effect(exclude={current_effect})

        self.ia_status_var.set(tr("t_new_artistic_running", "🎨 Nouvelle proposition artistique : {name}...", name=new_effect))
        self.root.update()

        settings, canvas = self._generate_artistic_proposal(
            self._ai_image_path, self._ai_base_settings, new_effect
        )
        self.proposals[idx] = (None, settings, canvas)

        display = canvas.resize((384, 96), Image.Resampling.NEAREST)
        photo = ImageTk.PhotoImage(display)
        self.proposal_canvases[idx].delete("all")
        self.proposal_canvases[idx].create_image(192, 48, image=photo)
        self.proposal_canvases[idx].image = photo
        self.proposal_labels[idx].config(text=f"{idx+1}. {settings['name']}")
        info_text = tr(
            "t_prop_info_new", "Score : —\nEffet : {effect} | Mode resize : {resize}\nFPS : {fps} | Durée : {dur}s",
            effect=settings["_artistic_effect"], resize=settings["resize_mode"],
            fps=settings["fps"], dur=settings.get("duration", 2.0),
        )
        self.proposal_info_labels[idx].config(text=info_text)

        if self.selected_proposal == idx and self.current_image_idx is not None:
            self.select_proposal(idx)

        self.ia_status_var.set(tr("t_new_artistic_done", "✓ Nouvelle proposition artistique : {name}", name=settings["name"]))

    def start_continuous_preview(self, image_path, settings):
        """Lance la preview animée continue"""
        self.animating = False
        time.sleep(0.1)

        try:
            cleanup_power = settings.get("cleanup_power", 1.0)
            frames, fps = self.render_dmd_frame(
                image_path, settings, return_frames=True, cleanup_power=cleanup_power
            )
            # Normalize frames to always be list[Image.Image]
            if isinstance(frames, Image.Image):
                normalized_frames: list[Image.Image] = [frames]
            elif isinstance(frames, list):
                normalized_frames = [f for f in frames if isinstance(f, Image.Image)]
            else:
                normalized_frames = []

            if not normalized_frames:
                normalized_frames = [Image.new("RGB", (128, 32), (0, 0, 0))]

            self.preview_frames = normalized_frames
            self.preview_index = 0
            self.animating = True
            self.current_fps = fps
            self._anim_schedule("auto", 0, self.animate_preview)
        except Exception as e:
            self.ia_status_var.set(tr("t_preview_error", "❌ Erreur aperçu : {err}", err=e))
            logger.error(f"Erreur preview: {e}")

    def animate_preview(self):
        """Animation de la preview principale. Si "Mode DMD / Forcer pixel-perfect"
        est coché, chaque frame est rendue en simulation LED (points ronds espacés
        par un bezel sombre, voir DMDEngine.render_led_style) au lieu du simple
        agrandissement carré NEAREST — mesuré à ~4-8ms/frame (scale=4), largement
        sous le budget d'une animation à 10fps (100ms/frame), donc pas de risque de
        ralentissement perceptible."""
        if not self.animating or not self.preview_frames:
            return

        try:
            frame = self.preview_frames[self.preview_index]
            if self._get_force_pixel_perfect():
                display = DMDEngine.render_led_style(
                    frame,
                    scale=4,
                    led_ratio=0.525,
                    glow=True,
                    brightness=self.led_brightness_var.get(),
                )
            else:
                display = frame.resize((512, 128), Image.Resampling.NEAREST)
            self.preview_dmd = ImageTk.PhotoImage(display)
            self.canvas_dmd_main.delete("all")
            self.canvas_dmd_main.create_image(256, 64, image=self.preview_dmd)

            self.preview_index = (self.preview_index + 1) % len(self.preview_frames)
            delay = int(1000 / self.current_fps) if self.current_fps > 0 else 100
            self._anim_schedule("auto", delay, self.animate_preview)
        except:
            self.animating = False

    def highlight_proposal(self, idx):
        """Met en surbrillance la proposition sélectionnée"""
        for i, canvas in enumerate(self.proposal_canvases):
            parent = canvas.master
            if i == idx:
                parent.config(relief=tk.SOLID, borderwidth=3)
                if self.theme.get() == "dark":
                    self.proposal_labels[i].config(
                        foreground="#00ff00", font=("Arial", 8, "bold")
                    )
                else:
                    self.proposal_labels[i].config(
                        foreground="green", font=("Arial", 8, "bold")
                    )
            else:
                parent.config(relief=tk.RAISED, borderwidth=2)
                if self.theme.get() == "dark":
                    self.proposal_labels[i].config(
                        foreground="#ffffff", font=("Arial", 8)
                    )
                else:
                    self.proposal_labels[i].config(
                        foreground="black", font=("Arial", 8)
                    )

    def select_proposal(self, idx):
        """Sélectionne une proposition IA"""
        if idx >= len(self.proposals):
            return

        self.selected_proposal = idx
        self.highlight_proposal(idx)

        if self.current_image_idx is not None:
            img_path = self.images[self.current_image_idx]
            score, settings, _ = self.proposals[idx]
            settings = settings.copy()
            self.image_settings[img_path] = settings

            score_text = f"{score:.2f}" if score is not None else "—"
            self.ia_status_var.set(
                tr("t_manual_pick", "👤 Sélection manuelle : '{name}' (score : {score})",
                   name=settings["name"], score=score_text)
            )
            self.start_continuous_preview(img_path, settings)
            logger.info(f"Proposition {idx+1} sélectionnée (score: {score_text})")

    def toggle_lock(self, idx, var):
        """Verrouille/déverrouille une proposition pour batch"""
        if var.get():
            # Déverrouiller les autres
            for i, lock in enumerate(self.proposal_locks):
                if i != idx:
                    lock.set(False)
            self.locked_proposal = idx
            self.ia_status_var.set(tr("t_proposal_locked", "🔒 Proposition {n} verrouillée pour le lot", n=idx + 1))
            logger.info(f"Proposition {idx+1} verrouillée")
        else:
            self.locked_proposal = None
            self.ia_status_var.set(tr("t_unlocked", "🔓 Déverrouillé"))
            logger.info("Déverrouillé")

    def batch_params_snapshot(self):
        """Snapshot figé des tk.Variable lues transitivement par la résolution de
        réglages (generate_settings_variants/_get_force_pixel_perfect) — 2026-08-06,
        Tier 2 plan perf batch. Créé UNE FOIS par lot (pas par image) avant de
        dispatcher aux workers ProcessPoolExecutor, qui ne peuvent pas lire
        self/Tk (tk.Variable non picklable à travers une frontière de
        process). Réutilisé aussi par get_settings_for_image() (chemin non
        parallèle : aperçu, ou fallback si le pool échoue), pour qu'il n'y ait
        qu'un seul endroit qui énumère ces variables."""
        return {
            "fps": self.fps_var.get(),
            "duration": self.duration_var.get(),
            "scroll_speed": self.scroll_speed_var.get(),
            "contrast": self.contrast_var.get(),
            "saturation": self.saturation_var.get(),
            "pixel_perfect": self._get_force_pixel_perfect(),
            "fill_min_ratio": self._get_fill_min_ratio(),
            "invert_dark": bool(self.invert_dark_var.get()),
            "max_scroll_cycle_s": self._get_scroll_cap(),
        }

    def _get_fill_min_ratio(self):
        """v86/v91 -- rapport L/H à partir duquel Fill est imposé, ou None si
        l'option est décochée (choix au score) ; borné, défaut si invalide."""
        if not self.fill_ratio_on_var.get():
            return None
        try:
            return max(1.0, min(8.0, float(self.fill_min_ratio_var.get())))
        except Exception:
            return _FILL_MIN_RATIO_DEFAULT

    def _get_scroll_cap(self):
        """v91 -- plafond d'aller-retour (s) du profil, ou None si décoché."""
        if not self.cap_on_var.get():
            return None
        try:
            return max(2.0, min(600.0, float(self.cap_s_var.get())))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # v91 -- Profils (dmd_profiles)
    # ------------------------------------------------------------------
    def _setup_profile_row(self, parent):
        """Ligne "Profil" + options du profil (onglet AUTO, paramètres
        globaux). Les options restent modifiables à la main après le choix
        d'un profil ; 💾 les enregistre dans profiles.json pour ce profil."""
        self.profiles = dmd_profiles.load_profiles(config_manager.user_dir)
        cur = self.profiles.get(config_manager.get("profile", "generic")) or self.profiles["generic"]

        row1 = ttk.Frame(parent)
        row1.pack(anchor=tk.W, pady=(2, 2), fill=tk.X)
        lbl = ttk.Label(row1, text="Profil :")
        lbl.pack(side=tk.LEFT, padx=(0, 5))
        add_help_tooltip(lbl, "tooltip_profile")
        self._profile_keys = list(self.profiles)  # ordre = valeurs de la liste (clé par position)
        self.profile_var = tk.StringVar(value=self._profile_label(config_manager.get("profile", "generic")))
        self.profile_combo = ttk.Combobox(row1, textvariable=self.profile_var, state="readonly", width=30,
                                          values=[self._profile_label(k) for k in self._profile_keys])
        self.profile_combo.pack(side=tk.LEFT)
        self.profile_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_profile_selected())
        new_btn = ttk.Button(row1, text="➕", width=3, command=self._new_profile)
        new_btn.pack(side=tk.LEFT, padx=(4, 0))
        add_help_tooltip(new_btn, "tooltip_profile_new")
        edit_btn = ttk.Button(row1, text="✏", width=3, command=self._edit_profile)
        edit_btn.pack(side=tk.LEFT, padx=(4, 0))
        add_help_tooltip(edit_btn, "tooltip_profile_edit")
        save_btn = ttk.Button(row1, text="💾", width=3, command=self._save_current_profile)
        save_btn.pack(side=tk.LEFT, padx=(4, 0))
        add_help_tooltip(save_btn, "tooltip_profile_save")
        del_btn = ttk.Button(row1, text="🗑", width=3, command=self._delete_profile)
        del_btn.pack(side=tk.LEFT, padx=(4, 0))
        add_help_tooltip(del_btn, "tooltip_profile_delete")

        # v95 -- options du profil sur la même ligne que la liste (hauteur de
        # l'onglet AUTO : voir v95 dans l'en-tête)
        row2 = row1
        ttk.Frame(row2, width=24).pack(side=tk.LEFT)
        cfg = config_manager.get
        self.fill_ratio_on_var = tk.BooleanVar(value=cfg("fill_ratio_on", cur["fill_min_ratio"] is not None))
        self.fill_min_ratio_var = tk.DoubleVar(value=cfg("fill_min_ratio", cur["fill_min_ratio"] or _FILL_MIN_RATIO_DEFAULT))
        self.invert_dark_var = tk.BooleanVar(value=cfg("invert_dark", cur["invert_dark"]))
        self.cap_on_var = tk.BooleanVar(value=cfg("cap_on", cur["max_scroll_cycle_s"] is not None))
        self.cap_s_var = tk.DoubleVar(value=cfg("max_scroll_cycle_s", cur["max_scroll_cycle_s"] or 30.0))

        chk = ttk.Checkbutton(row2, text="Défilement imposé dès (L/H):", variable=self.fill_ratio_on_var,
                              command=self._on_profile_option_change)
        chk.pack(side=tk.LEFT)
        add_help_tooltip(chk, "tooltip_fill_ratio")
        ttk.Spinbox(row2, from_=1.0, to=8.0, increment=0.5, format="%.1f", width=5,
                    textvariable=self.fill_min_ratio_var,
                    command=self._on_profile_option_change).pack(side=tk.LEFT, padx=(2, 16))
        chk = ttk.Checkbutton(row2, text="Inverser les logos sombres", variable=self.invert_dark_var,
                              command=self._on_profile_option_change)
        chk.pack(side=tk.LEFT, padx=(0, 16))
        add_help_tooltip(chk, "tooltip_invert_dark")
        chk = ttk.Checkbutton(row2, text="Plafond aller-retour (s):", variable=self.cap_on_var,
                              command=self._on_profile_option_change)
        chk.pack(side=tk.LEFT)
        add_help_tooltip(chk, "tooltip_scroll_cap")
        ttk.Spinbox(row2, from_=2, to=600, increment=5, format="%.0f", width=5,
                    textvariable=self.cap_s_var,
                    command=self._on_profile_option_change).pack(side=tk.LEFT, padx=(2, 0))

    def _profile_label(self, key):
        p = self.profiles.get(key) if hasattr(self, "profiles") else None
        if p is None:
            return key
        return tr(f"t_profile_{key}", p["label"])

    def _profile_key_from_label(self, label):
        """Clé du profil affiché : par position dans la liste (robuste à un
        changement de langue), repli sur le libellé puis sur "generic"."""
        idx = self.profile_combo.current() if hasattr(self, "profile_combo") else -1
        if 0 <= idx < len(self._profile_keys):
            return self._profile_keys[idx]
        return next((k for k in self._profile_keys if self._profile_label(k) == label), "generic")

    # v92 -- paramètres globaux portés par un profil : clé dmd_profiles -> variable Tk
    def _profile_param_vars(self):
        return {
            "fps": self.fps_var, "duration": self.duration_var,
            "scroll_speed": self.scroll_speed_var, "contrast": self.contrast_var,
            "saturation": self.saturation_var, "color_count": self.color_count_var,
            "pixel_perfect": self.pixel_perfect_var,
        }

    def _current_profile_values(self):
        values = {
            "fill_min_ratio": self._get_fill_min_ratio(),
            "invert_dark": bool(self.invert_dark_var.get()),
            "max_scroll_cycle_s": self._get_scroll_cap(),
        }
        for key, var in self._profile_param_vars().items():
            try:
                values[key] = var.get()
            except (tk.TclError, ValueError):
                values[key] = None  # saisie en cours invalide : non enregistrée
        return values

    def _refresh_profile_combo(self, select_key):
        self.profiles = dmd_profiles.load_profiles(config_manager.user_dir)
        self._profile_keys = list(self.profiles)
        self.profile_combo.configure(values=[self._profile_label(k) for k in self._profile_keys])
        key = select_key if select_key in self.profiles else "generic"
        self.profile_combo.current(self._profile_keys.index(key))
        config_manager.set("profile", key)
        return key

    def _new_profile(self):
        """v92 -- éditeur de profil, prérempli avec les réglages actuels."""
        ProfileEditor(self)

    def _edit_profile(self):
        """v92 -- éditeur sur le profil sélectionné."""
        ProfileEditor(self, self._profile_key_from_label(self.profile_var.get()))

    def _delete_profile(self):
        key = self._profile_key_from_label(self.profile_var.get())
        p = self.profiles[key]
        if p.get("builtin"):
            msg = tr("t_profile_reset_confirm",
                     "Remettre le profil « {name} » à ses valeurs d'origine ?", name=self._profile_label(key))
        else:
            msg = tr("t_profile_delete_confirm",
                     "Supprimer le profil « {name} » ?", name=self._profile_label(key))
        if not messagebox.askyesno(lang_manager.get("confirmation", "Confirmation"), msg):
            return
        dmd_profiles.delete_profile(config_manager.user_dir, key)
        key = self._refresh_profile_combo(key)
        self._on_profile_selected()
        logger.info(f"Profil {'réinitialisé' if p.get('builtin') else 'supprimé'} : {p['label']}")

    def _persist_profile_options(self):
        try:
            config_manager.set("fill_ratio_on", bool(self.fill_ratio_on_var.get()))
            config_manager.set("fill_min_ratio", float(self.fill_min_ratio_var.get()))
            config_manager.set("invert_dark", bool(self.invert_dark_var.get()))
            config_manager.set("cap_on", bool(self.cap_on_var.get()))
            config_manager.set("max_scroll_cycle_s", float(self.cap_s_var.get()))
        except (tk.TclError, ValueError):
            pass  # saisie en cours dans un Spinbox : pas d'écriture

    def _on_profile_option_change(self):
        self._persist_profile_options()
        self.on_global_param_change()

    def _on_profile_selected(self):
        key = self._profile_key_from_label(self.profile_var.get())
        p = self.profiles[key]
        config_manager.set("profile", key)
        self.fill_ratio_on_var.set(p["fill_min_ratio"] is not None)
        if p["fill_min_ratio"] is not None:
            self.fill_min_ratio_var.set(p["fill_min_ratio"])
        self.invert_dark_var.set(bool(p["invert_dark"]))
        self.cap_on_var.set(p["max_scroll_cycle_s"] is not None)
        if p["max_scroll_cycle_s"] is not None:
            self.cap_s_var.set(p["max_scroll_cycle_s"])
        for pkey, var in self._profile_param_vars().items():  # v92 : None = inchangé
            if p.get(pkey) is not None:
                var.set(p[pkey])
        logger.info(f"Profil appliqué : {p['label']} {self._current_profile_values()}")
        self._on_profile_option_change()

    def _save_current_profile(self):
        key = self._profile_key_from_label(self.profile_var.get())
        values = self._current_profile_values()
        try:
            path = dmd_profiles.save_profile(config_manager.user_dir, key, values)
        except OSError as e:
            messagebox.showerror(lang_manager.get("error", "Erreur"), str(e))
            return
        self._refresh_profile_combo(key)
        logger.info(f"Profil enregistré : {key} {values} -> {path}")
        messagebox.showinfo(
            lang_manager.get("success", "Succès"),
            tr("t_profile_saved", "Profil « {name} » enregistré.", name=self._profile_label(key)),
        )

    def get_settings_for_image(self, image_path, batch_params=None):
        """Récupère les settings optimaux pour une image (traitement par lot sans
        passer par l'aperçu interactif Auto/IA) : même logique resize-vs-fill puis
        optimisation nettoyage/pixel-perfect que auto_analyze_and_preview, sans les
        propositions artistiques (pas de sens en export automatique non supervisé).

        Wrapper fin (2026-08-06, Tier 2 plan perf batch) : délègue à
        dmd_pipeline_quality.resolve_image_settings (version pure, algorithme
        déplacé tel quel, réutilisée par process_one_image() côté worker
        parallèle). `batch_params` optionnel (sinon construit ici via
        batch_params_snapshot() — un seul appel, chemin non-batch comme
        l'aperçu Auto/IA)."""
        locked_settings = None
        if self.locked_proposal is not None and self.proposals:
            locked_settings = self.proposals[self.locked_proposal][1]

        cached_settings = self.image_settings.get(image_path)

        if batch_params is None:
            batch_params = self.batch_params_snapshot()

        return _resolve_image_settings(
            image_path,
            batch_params,
            locked_settings=locked_settings,
            cached_settings=cached_settings,
        )

    def process_images(self, image_list):
        """Traite un lot d'images"""
        logger.info("process_images démarré")
        output_dir = filedialog.askdirectory(title=tr("t_output_folder", "Dossier de sortie"))
        if not output_dir:
            return

        # Dossier racine pour la reconstruction de l'arborescence relative en sortie :
        # le dossier explicitement chargé (mode dossier/glisser-déposer), ou à défaut
        # le dossier du 1er fichier (fichiers individuels, pas d'arborescence à
        # reconstruire).
        if self.images:
            input_dir = (
                Path(self.source_root_dir)
                if self.source_root_dir
                else Path(self.images[0]).parent
            )
            if input_dir.resolve() == Path(output_dir).resolve():
                same_folders_msg = lang_manager.get(
                    "err_same_folders", "Les dossiers d'entrée et sortie doivent être différents"
                )
                messagebox.showerror(lang_manager.get("error", "Erreur"), same_folders_msg)
                logger.error("Dossiers identiques")
                return
        else:
            # Titre corrigé "Erreur"→"Attention" (bug d'incohérence pré-
            # existant : messagebox.showwarning affichait un titre "Erreur",
            # décalé par rapport à toutes les autres alertes non bloquantes
            # de l'app, qui utilisent systématiquement "Attention").
            no_source_msg = lang_manager.get(
                "no_images_for_source_folder", "Aucune image chargée pour définir le dossier source"
            )
            messagebox.showwarning(lang_manager.get("warning", "Attention"), no_source_msg)
            return

        # Vérifier dossier non vide
        if list(Path(output_dir).glob("*")):
            not_empty_msg = lang_manager.get(
                "output_folder_not_empty_confirm", "Le dossier de sortie n'est pas vide. Continuer ?"
            )
            if not messagebox.askyesno(lang_manager.get("confirmation", "Confirmation"), not_empty_msg):
                logger.warning("Batch annulé: dossier non vide")
                return

        # Filtrer exports manuels (ne pas écraser une image déjà exportée en MANUEL)
        to_process = [img for img in image_list if img not in self.manual_exports]

        if len(to_process) < len(image_list):
            skipped = len(image_list) - len(to_process)
            logger.warning(f"{skipped} images ignorées (exports manuels)")

        total = len(to_process)
        if total == 0:
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"),
                lang_manager.get("no_images_after_filter", "Aucune image à traiter après filtrage"),
            )
            return

        self.processing_canceled = False
        # Erreurs accumulees pour le resume de fin de lot (2026-08-05, demande
        # utilisateur : "supprimer les popups bloquantes lors du traitement par
        # lot, juste une mention dans le debug + resume en fin de process des
        # erreurs") -- une erreur sur UNE image n'affiche plus de popup, juste
        # une mention dans les logs (onglet DEBUG) + accumulation ici pour le
        # résumé affiché une seule fois en fin de lot (clear_progress_and_notify).
        errors = []
        success_count = 0

        # Figé AVANT dispatch (2026-08-06, Tier 2 plan perf batch : "multithread
        # ? ou autre solution ?") : les workers ProcessPoolExecutor tournent
        # dans des PROCESSUS séparés (pas des threads — le GIL limiterait trop
        # le gain sur ce pipeline, voir dmd_pipeline_quality.py v23/dmd_converter.py
        # v80 pour l'extraction en fonctions pures qui a rendu ceci possible) :
        # aucune tk.Variable/instance Tkinter n'est picklable à travers une
        # frontière de process, tout ce dont process_one_image() a besoin est
        # donc capturé ICI, une seule fois pour tout le lot — jamais relu depuis
        # un worker.
        batch_params = self.batch_params_snapshot()
        locked_settings = None
        if self.locked_proposal is not None and self.proposals:
            locked_settings = self.proposals[self.locked_proposal][1]
        image_settings_snapshot = dict(self.image_settings)
        add_anim_to_name = self.add_anim_to_name.get()
        color_count_fallback = self.color_count_var.get()
        loop_mode = self.manual_loop_mode.get()
        loop_count = self.manual_loop_count.get()
        input_dir_str = str(input_dir)
        output_dir_str = str(output_dir)

        # v84 -- nombre de workers mesuré (2026-09-24, 480 images mame/S, 20
        # cpu logiques) : ~85 Mo de RAM par worker ; débit 4 → 12 workers
        # ×1,9, 12 → 16 seulement +6 % (saturation). Règle : cpu logiques - 2
        # (garde de la marge pour l'interface et le système), plafonnée à 12,
        # jamais moins que l'ancien défaut min(4, cpu).
        cpu = os.cpu_count() or 1
        max_workers = max(min(4, cpu), min(12, cpu - 2), 1)

        # v96 -- réglages du lot dans dmd_batch.json (les corrections proposées
        # par Revoir refont le rendu avec les mêmes) ; jamais bloquant
        batch_no = None
        try:
            batch_no = dmd_autofix.add_batch(output_dir_str, {
                "date": datetime.datetime.now().isoformat(timespec="seconds"),
                "input_dir": input_dir_str,
                "profile": config_manager.get("profile", "generic"),
                "batch_params": batch_params,
                "locked": locked_settings is not None,
                "add_anim_to_name": add_anim_to_name,
                "color_count_fallback": color_count_fallback,
                "loop_mode": loop_mode,
                "loop_count": loop_count,
            })
        except Exception as e:
            logger.error(f"Réglages du lot non écrits ({dmd_autofix.BATCH_FILE}) : {e}")

        pool = ProcessPoolExecutor(max_workers=max_workers)
        futures = {
            pool.submit(
                process_one_image,
                img_path,
                batch_params,
                locked_settings,
                image_settings_snapshot.get(img_path),
                output_dir_str,
                input_dir_str,
                add_anim_to_name,
                color_count_fallback,
                loop_mode,
                loop_count,
            ): img_path
            for img_path in to_process
        }

        completed = 0
        canceled_mid_batch = False
        quality_rows = {}  # v87 -- collecté ici (thread consommateur), jamais par les workers
        for future in as_completed(futures):
            if self.processing_canceled:
                canceled_mid_batch = True
                break
            img_path, ok, err, output_name, nframes, color_count, quality = future.result()
            if quality is not None:
                if batch_no is not None:
                    quality[1]["b"] = batch_no
                quality_rows[quality[0]] = quality[1]
            completed += 1
            percent = int((completed / total) * 100)
            self.root.after(
                0, lambda p=percent, f=Path(img_path).name: self.update_progress(p, f)
            )
            if ok:
                logger.info(f"GIF créé: {output_name} ({nframes} frames, {color_count} couleurs)")
                success_count += 1
            else:
                errors.append(f"{Path(img_path).name}: {err}")
                logger.error(f"Erreur {Path(img_path).name}: {err}")

        if canceled_mid_batch:
            # Annule les futures pas encore démarrées ; celles déjà en cours
            # (jusqu'à max_workers) vont à leur terme -- changement de
            # comportement assumé vs l'ancien arrêt strict avant la prochaine
            # image (plan perf batch, Tier 2).
            pool.shutdown(wait=True, cancel_futures=True)
            self._save_quality_index(output_dir_str, quality_rows)
            self.root.after(0, lambda: self.progress_text_var.set(tr("t_interrupted", "Interrompu")))
            logger.info("Batch interrompu par l'utilisateur")
            return

        pool.shutdown(wait=True)
        quality_summary = self._save_quality_index(output_dir_str, quality_rows)

        self.root.after(
            0,
            lambda out=output_dir, s=success_count, errs=errors, qs=quality_summary: self.clear_progress_and_notify(
                s, total, out, errs, quality_summary=qs
            ),
        )

    def _save_quality_index(self, output_dir, rows):
        """v87 -- fusionne les scores du lot dans dmd_scores.json du dossier de
        sortie (un 2e lot dans le même dossier ne doit pas effacer le 1er) et
        renvoie le résumé du lot (dmd_quality.summarize), ou None."""
        if not rows:
            return None
        try:
            index = dq.load_index(output_dir)
            index.update(rows)
            dq.save_index(output_dir, index)
            summary = dq.summarize(rows)
            logger.info(
                f"Score qualité : {summary['count']} GIF, moyenne {summary['mean']}, "
                f"{summary['by_rating']} — index {dq.index_path(output_dir)}"
            )
            return summary
        except Exception as e:
            logger.error(f"Index qualité non écrit : {e}")
            return None

    def open_review_window(self, folder=None):
        """v88 -- ouvre la fenêtre "Revoir" (ReviewWindow) sur un dossier de
        sortie contenant dmd_scores.json. v94 : sans dossier fourni, ouvre
        directement le dossier du dernier lot (config last_review_folder) ;
        choix de dossier seulement s'il n'y en a pas encore ou s'il n'a plus
        d'index (le choix d'un autre dossier se fait dans la fenêtre)."""
        if folder is None:
            last = config_manager.get("last_review_folder", "")
            if last and os.path.isdir(last) and dq.load_index(last):
                folder = last
            else:
                opts = {"initialdir": last} if last and os.path.isdir(last) else {}
                folder = filedialog.askdirectory(
                    title=tr("t_review_pick_folder", "Dossier de GIF à revoir (contenant dmd_scores.json)"),
                    **opts,
                )
                if not folder:
                    return
        if not dq.load_index(folder):
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"),
                tr("t_review_no_index",
                   "Aucun score dans ce dossier ({name}).\n"
                   "Traitez d'abord des images par lot vers ce dossier.", name=dq.INDEX_NAME),
            )
            return
        config_manager.set("last_review_folder", str(folder))
        ReviewWindow(self, folder)

    def cancel_processing(self):
        """Interrompt le traitement en cours"""
        self.processing_canceled = True
        self.progress_text_var.set(tr("t_stop_requested", "Interruption demandée..."))
        logger.info("Interruption demandée")

    def process_all(self):
        """Traite toutes les images"""
        if not self.images:
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"),
                lang_manager.get("no_images_loaded", "Aucune image chargée"),
            )
            return
        threading.Thread(
            target=lambda: self.process_images(self.images), daemon=True
        ).start()

    def process_selected(self):
        """Traite les images sélectionnées"""
        selection = self.image_tree.selection()
        if not selection:
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"),
                lang_manager.get("select_images_warn", "Sélectionnez des images"),
            )
            return
        selected = [self.images[int(i)] for i in selection]
        threading.Thread(
            target=lambda: self.process_images(selected), daemon=True
        ).start()

    # ========================================================================
    # ONGLET MANUEL
    # ========================================================================

    def load_from_auto(self):
        """Charge l'image sélectionnée dans AUTO vers MANUEL"""
        if self.current_image_idx is None:
            return

        img_path = self.images[self.current_image_idx]
        self.manual_image = DMDEngine.ensure_rgb_on_black(DMDEngine.load_image(img_path))
        self.manual_original = self.manual_image.copy()
        self.manual_history = [self.manual_image.copy()]
        self.manual_history_index = 0

        # Reset sliders
        self.manual_brightness.set(1.0)
        self.manual_contrast.set(1.0)
        self.manual_saturation.set(1.0)
        self.manual_sharpness.set(1.0)

        self.display_manual_image()
        self.manual_status.set(tr("t_image_name", "Image : {name}", name=Path(img_path).name))
        logger.info(f"Image chargée en manuel: {Path(img_path).name}")

    def load_manual_image(self):
        """Charge une image manuellement"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.raw565")]
        )
        if file_path:
            self.review_target = None  # v97 : autre image, plus liée à Revoir
            self._load_manual_from_path(file_path)

    def _load_manual_from_path(self, file_path):
        """v97 -- corps de load_manual_image, réutilisé par l'édition depuis Revoir."""
        if file_path and getattr(self, "crop_mode", False):
            self._crop_stop(None)  # v98 : cadre propre à l'image précédente
        if file_path:  # v103 : zone propre à l'image précédente
            self._zone_mode_stop()
            self.manual_zone = None
        if file_path and hasattr(self, "manual_zoom_text"):
            self.manual_zoom = 1.0  # v99 : zoom propre à chaque image
            self.manual_zoom_step(0, regenerate=False)
        if file_path:
            self.manual_image = DMDEngine.ensure_rgb_on_black(DMDEngine.load_image(file_path))
            self.manual_original = self.manual_image.copy()
            self.manual_history = [self.manual_image.copy()]
            self.manual_history_index = 0

            self.manual_brightness.set(1.0)
            self.manual_contrast.set(1.0)
            self.manual_saturation.set(1.0)
            self.manual_sharpness.set(1.0)

            self.display_manual_image()
            self.manual_status.set(tr("t_image_name", "Image : {name}", name=Path(file_path).name))
            logger.info(f"Image chargée: {Path(file_path).name}")

    # --- v101 : boucles d'aperçu (une seule étape en attente par aperçu) ---------
    def _anim_cancel(self, name):
        job = self._anim_jobs.pop(name, None)
        if job is not None:
            try:
                self.root.after_cancel(job)
            except tk.TclError:
                pass

    def _anim_schedule(self, name, delay, fn):
        """Programme la prochaine image de l'aperçu `name` ("auto", "manual",
        "text", "video") en annulant celle déjà en attente : relancer un aperçu
        (régénération, autre image) ne crée plus une 2e boucle parallèle qui
        avançait les images en même temps (aperçu 2×, 3× trop rapide)."""
        self._anim_cancel(name)
        # cadence tenue sur l'horloge : le temps de dessin d'une image (rendu
        # LED ~15 ms) est déduit du délai, sinon 15 i/s s'affichaient à ~12 i/s
        now = time.perf_counter() * 1000.0
        due = self._anim_due.get(name) if delay > 0 else None
        due = now + delay if due is None or abs(due + delay - now) > 4 * delay + 250 else due + delay
        self._anim_due[name] = due
        self._anim_jobs[name] = self.root.after(max(1, int(round(due - now))), fn)

    def _manual_schedule_regen(self, *_args):
        """Champ FPS / durée / vitesse de MANUEL modifié : l'aperçu est refait
        600 ms après la dernière frappe (s'il y en avait un, et pas pour un
        morphing), pour que sa vitesse corresponde toujours aux réglages."""
        if self._manual_regen_job is not None:
            try:
                self.root.after_cancel(self._manual_regen_job)
            except tk.TclError:
                pass
        self._manual_regen_job = self.root.after(600, self._manual_regen_now)

    def _manual_regen_now(self):
        self._manual_regen_job = None
        if not (self.manual_image is not None and self.manual_frames
                and getattr(self, "_manual_frames_zoomable", False)):
            return
        try:  # saisie incomplète : on attend la suivante
            if self.manual_fps.get() < 1 or self.manual_duration.get() <= 0 or self.manual_scroll_speed.get() < 1:
                return
        except (tk.TclError, ValueError):
            return
        self.generate_manual_animation()

    _MANUAL_ZOOM_STEPS = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0)

    def manual_zoom_step(self, step, regenerate=True):
        """v99 -- zoom de l'animation MANUEL : palier suivant (+1), précédent
        (-1) ou retour à 100 % (0) ; l'aperçu est régénéré s'il existait."""
        steps = self._MANUAL_ZOOM_STEPS
        cur = min(range(len(steps)), key=lambda i: abs(steps[i] - self.manual_zoom))
        idx = steps.index(1.0) if step == 0 else max(0, min(len(steps) - 1, cur + step))
        self.manual_zoom = steps[idx]
        self.manual_zoom_text.set(tr("t_manual_zoom", "Zoom : {p} %", p=round(self.manual_zoom * 100)))
        logger.info(f"Zoom MANUEL : {round(self.manual_zoom * 100)} %")
        if (regenerate and self.manual_image is not None and self.manual_frames
                and getattr(self, "_manual_frames_zoomable", False)):
            self.generate_manual_animation()

    def edit_from_review(self, folder, rel, src, review=None, timing=None):
        """v97 -- "✎ Éditer dans MANUEL" (fenêtre Revoir) : charge la source du
        GIF dans l'onglet MANUEL, reprend le rythme du GIF (FPS, durée, boucle
        du lot : `timing`, choix utilisateur) ; l'export proposera de
        remplacer ce GIF."""
        self._load_manual_from_path(src)
        timing = timing or {}
        for key, var in (("fps", self.manual_fps), ("duration", self.manual_duration),
                         ("scroll_speed", self.manual_scroll_speed),
                         ("loop_mode", self.manual_loop_mode), ("loop_count", self.manual_loop_count)):
            if timing.get(key) is not None:
                var.set(timing[key])
        self.review_target = {"folder": str(folder), "rel": rel, "review": review}
        self.notebook.select(self.notebook.tabs()[1])
        self.manual_status.set(tr("t_review_edit_status", "Image : {name} — l'export remplacera {rel} (Revoir)",
                                  name=Path(src).name, rel=rel))
        self.root.lift()
        logger.info(f"Revoir : édition manuelle de {rel} (source {src})")

    def _export_to_review(self, fps):
        """v97 -- export MANUEL qui remplace le GIF du lot ouvert dans Revoir.
        Renvoie True si fait (ou refusé par erreur signalée), None si
        l'utilisateur préfère enregistrer ailleurs, False s'il annule."""
        t = self.review_target
        choice = messagebox.askyesnocancel(
            lang_manager.get("confirmation", "Confirmation"),
            tr("t_review_edit_replace",
               "Remplacer {rel} dans le dossier du lot ?\n\nOui : l'original est mis de côté dans {dir} "
               "(jamais supprimé).\nNon : enregistrer ailleurs.",
               rel=t["rel"], dir=os.path.join(dq.REVIEW_DIR, dmd_autofix.BEFORE_DIR)),
        )
        if choice is None:
            return False
        if not choice:
            return None
        target = os.path.join(t["folder"], *t["rel"].split("/"))
        tmp = target + ".manuel_tmp.gif"
        try:
            export_frames_to_gif(self.manual_frames, tmp, fps=fps, color_count=self.color_count_var.get(),
                                 loop_mode=self.manual_loop_mode.get(), loop_count=self.manual_loop_count.get(),
                                 disposal=2, optimize=False)
            q = dq.evaluate_frames(self.manual_frames, int(1000 / max(1, fps))).to_dict()
            before, bak = review_replace_gif(t["folder"], t["rel"], tmp, q, "manual")
        except Exception as e:
            if os.path.exists(tmp):
                os.remove(tmp)  # export temporaire non utilisé
            messagebox.showerror(lang_manager.get("error", "Erreur"), f"{lang_manager.get('err_export', 'Erreur export')}: {e}")
            logger.error(f"Revoir : remplacement manuel de {t['rel']} impossible : {e}")
            return True
        rw = t.get("review")
        if rw is not None:
            try:
                if rw.win.winfo_exists() and os.path.normcase(rw.folder) == os.path.normcase(t["folder"]):
                    rw.after_external_replace(t["rel"])
            except tk.TclError:
                pass
        messagebox.showinfo(lang_manager.get("success", "Succès"),
                            tr("t_review_edit_done", "{rel} remplacé : {before} → {score}.\nOriginal : {bak}",
                               rel=t["rel"], before=before, score=q["score"], bak=bak))
        logger.info(f"Revoir : {t['rel']} remplacé par l'export MANUEL, {before} → {q['score']}, original : {bak}")
        return True

    def display_manual_image(self):
        """Affiche l'image dans le canvas manuel"""
        if self.manual_image is None:
            return

        w, h = self.manual_image.size
        scale = min(640 / w, 320 / h)
        display_w, display_h = int(w * scale), int(h * scale)
        img_display = self.manual_image.resize(
            (display_w, display_h), Image.Resampling.LANCZOS
        )

        self.manual_preview = ImageTk.PhotoImage(img_display)
        self.manual_canvas.delete("all")
        self.manual_canvas.create_image(320, 160, image=self.manual_preview)
        if getattr(self, "crop_mode", False):  # v98 : cadre de recadrage redessiné
            self.crop_preview_rect = None
            self._crop_draw()
        self._zone_draw()  # v103 : zone d'effets toujours visible
        self.update_manual_info()

    def apply_manual_effect(self):
        """Applique les effets temps réel (sliders)"""
        if self.manual_image is None or not self.manual_history:
            return

        # v103 : partir de l'état courant de l'historique (partait de
        # manual_history[0], l'image chargée : toucher un curseur annulait
        # recadrage, filtres, remplissages…). Les réglages sont intégrés à la
        # prochaine action permanente (_manual_commit_history).
        committed = self.manual_history[self.manual_history_index]
        base_img = committed.copy()

        if self.manual_brightness.get() != 1.0:
            enhancer = ImageEnhance.Brightness(base_img)
            base_img = enhancer.enhance(self.manual_brightness.get())

        if self.manual_contrast.get() != 1.0:
            enhancer = ImageEnhance.Contrast(base_img)
            base_img = enhancer.enhance(self.manual_contrast.get())

        if self.manual_saturation.get() != 1.0:
            enhancer = ImageEnhance.Color(base_img)
            base_img = enhancer.enhance(self.manual_saturation.get())

        if self.manual_sharpness.get() != 1.0:
            enhancer = ImageEnhance.Sharpness(base_img)
            base_img = enhancer.enhance(self.manual_sharpness.get())

        self.manual_image = self._manual_zone_merge(committed, base_img)  # v103 : zone
        self.display_manual_image()

    def apply_filter(self, filter_name):
        """Applique un filtre"""
        if self.manual_image is None:
            return

        filters_map = {
            "flou": ImageFilter.BLUR,
            "flou_gaussien": lambda: ImageFilter.GaussianBlur(radius=2),
            "contours": ImageFilter.FIND_EDGES,
            "relief": ImageFilter.EMBOSS,
            "details+": ImageFilter.DETAIL,
        }

        point_ops = {
            "inverser": ImageOps.invert,
            "miroir_h": ImageOps.mirror,
            "miroir_v": ImageOps.flip,
            "n&b": lambda im: ImageOps.grayscale(im).convert("RGB"),
            "posteriser": lambda im: ImageOps.posterize(im, 4),
            "solariser": lambda im: ImageOps.solarize(im, threshold=128),
            "egaliser": ImageOps.equalize,
            "auto-contraste": ImageOps.autocontrast,
        }
        img = self.manual_image
        zone = self.manual_zone
        if filter_name in filters_map:
            f = filters_map[filter_name]
            # v103 : filtre de voisinage calculé sur toute l'image (pas d'effet de
            # bord au contour de la zone), seul l'intérieur de la zone est gardé
            self.manual_image = self._manual_zone_merge(img, img.filter(f() if callable(f) else f))
        elif filter_name in point_ops:
            if zone:  # v103 : appliqué au seul contenu de la zone (miroir, égaliser… de la zone)
                out = img.copy()
                out.paste(point_ops[filter_name](img.crop(tuple(zone))), (zone[0], zone[1]))
                self.manual_image = out
            else:
                self.manual_image = point_ops[filter_name](img)
        elif filter_name == "rotation_90":
            # toujours toute l'image (changerait les dimensions de la zone)
            self.manual_image = img.rotate(90, expand=True)
            self._manual_zone_clear(quiet=True)
        # v99 : resize_+ / resize_- retirés, remplacés par manual_zoom_step

        self._manual_commit_history()
        self.display_manual_image()
        logger.info(f"Filtre appliqué: {filter_name}")

    def _manual_commit_history(self):
        """Enregistre l'état courant de manual_image comme un nouveau point
        d'historique undo/redo. À appeler juste APRÈS toute action manuelle
        discrète qui modifie manual_image (filtre, remplissage, gomme,
        crop...) — PAS pour les sliders temps réel (apply_manual_effect), qui
        restent volontairement hors historique (glissement continu, pas une
        action unitaire à annuler d'un coup).
        Si l'utilisateur avait fait un ou plusieurs undo puis effectue une
        nouvelle action, la branche "redo" désormais obsolète est écrasée —
        comportement standard de tout éditeur avec undo/redo."""
        if self.manual_image is None:
            return
        self.manual_history = self.manual_history[: self.manual_history_index + 1]
        self.manual_history.append(self.manual_image.copy())
        self.manual_history_index = len(self.manual_history) - 1
        # v103 : l'action a été faite sur l'image affichée, curseurs compris :
        # leurs réglages sont désormais intégrés, ils reviennent à 1,00
        self._manual_reset_sliders()

    def _manual_reset_sliders(self):
        for name in ("manual_brightness", "manual_contrast", "manual_saturation", "manual_sharpness"):
            var = getattr(self, name, None)
            if var is not None:
                var.set(1.0)

    def manual_undo(self):
        """Annule la dernière action (incrémental, voir manual_redo)."""
        if self.manual_history_index > 0:
            self.manual_history_index -= 1
            self.manual_image = self.manual_history[self.manual_history_index].copy()
            self._manual_reset_sliders()  # v103 : réglages non intégrés abandonnés
            self.display_manual_image()
            self.manual_status.set(tr("t_undo_done", "Annulation effectuée"))
            logger.info("Annulation")
        else:
            messagebox.showinfo(
                lang_manager.get("info", "Info"), lang_manager.get("nothing_to_undo", "Rien à annuler")
            )

    def manual_redo(self):
        """Rétablit l'action précédemment annulée par manual_undo."""
        if self.manual_history_index < len(self.manual_history) - 1:
            self.manual_history_index += 1
            self.manual_image = self.manual_history[self.manual_history_index].copy()
            self._manual_reset_sliders()  # v103 : réglages non intégrés abandonnés
            self.display_manual_image()
            self.manual_status.set(tr("t_redo_done", "Rétablissement effectué"))
            logger.info("Rétablissement (redo)")
        else:
            messagebox.showinfo(
                lang_manager.get("info", "Info"), lang_manager.get("nothing_to_redo", "Rien à rétablir")
            )

    def toggle_fill_mode(self):
        """Active/désactive le mode remplissage"""
        self._zone_mode_stop()  # v103 : le clic sert au remplissage, plus à la zone
        self.fill_mode = not self.fill_mode
        self.eraser_mode = False

        if self.fill_mode:
            self.fill_btn.config(text=tr("fill_active", "🎨 Remplissage (ACTIF)"))
            self.eraser_btn.config(text=tr("eraser", "🧹 Gomme Magique"))
            self.manual_canvas.config(cursor="crosshair")
            self.manual_status.set(tr("t_fill_on", "Mode remplissage actif - Cliquez sur une zone"))
            logger.info("Remplissage ON")
        else:
            self.fill_btn.config(text=tr("fill", "🎨 Remplissage"))
            self.manual_canvas.config(cursor="arrow")
            self.manual_status.set(tr("t_fill_off", "Mode remplissage désactivé"))
            logger.info("Remplissage OFF")

    def toggle_eraser_mode(self):
        """Active/désactive la gomme magique"""
        self._zone_mode_stop()  # v103 : le clic sert à la gomme, plus à la zone
        self.eraser_mode = not self.eraser_mode
        self.fill_mode = False

        if self.eraser_mode:
            self.eraser_btn.config(text=tr("eraser_active", "🧹 Gomme Magique (ACTIF)"))
            self.fill_btn.config(text=tr("fill", "🎨 Remplissage"))
            self.manual_canvas.config(cursor="crosshair")
            self.manual_status.set(tr("t_eraser_on", "Gomme magique active - Cliquez pour effacer"))
            logger.info("Gomme magique ON")
        else:
            self.eraser_btn.config(text=tr("eraser", "🧹 Gomme Magique"))
            self.manual_canvas.config(cursor="arrow")
            self.manual_status.set(tr("t_eraser_off", "Gomme magique désactivée"))
            logger.info("Gomme magique OFF")

    def choose_fill_color(self):
        """Choisit la couleur de remplissage"""
        color = colorchooser.askcolor(
            title=tr("t_fill_color", "Couleur de remplissage"), initialcolor=self.fill_color
        )
        if color[0]:
            self.fill_color = tuple(int(c) for c in color[0])
            hex_color = "#%02x%02x%02x" % self.fill_color
            self.color_preview.config(bg=hex_color)
            logger.info(f"Couleur remplissage: {self.fill_color}")

    def on_manual_click(self, event):
        """Gère les clics sur le canvas manuel"""
        if self.manual_image is None:
            return

        # Convertir coordonnées canvas vers image
        w, h = self.manual_image.size
        scale = min(640 / w, 320 / h)
        display_w, display_h = int(w * scale), int(h * scale)

        offset_x = (640 - display_w) // 2
        offset_y = (320 - display_h) // 2

        click_x = event.x - offset_x
        click_y = event.y - offset_y

        if click_x < 0 or click_x >= display_w or click_y < 0 or click_y >= display_h:
            return

        # Coordonnées dans l'image originale
        img_x = int(click_x / scale)
        img_y = int(click_y / scale)

        if self.fill_mode:
            self.flood_fill(img_x, img_y)
        elif self.eraser_mode:
            self.magic_eraser(img_x, img_y)

    def flood_fill(self, x, y):
        """Remplissage par diffusion"""
        arr = np.array(self.manual_image)
        h, w = arr.shape[:2]

        if x < 0 or x >= w or y < 0 or y >= h:
            return

        target_color = tuple(arr[y, x])
        tolerance = self.fill_tolerance.get()

        # Masque global des pixels dans la tolérance de couleur (le diff ne dépend que
        # de target_color, pas du chemin parcouru, donc le résultat de la BFS classique
        # ne dépend que de ce masque et du seed -> flood fill vectorisable par dilatation)
        diff = np.abs(arr.astype(int) - np.array(target_color, dtype=int)).sum(axis=2)
        candidate_mask = diff <= tolerance

        visited = np.zeros((h, w), dtype=bool)
        frontier = np.zeros((h, w), dtype=bool)
        frontier[y, x] = True
        visited |= frontier

        while frontier.any():
            up = np.zeros((h, w), dtype=bool)
            up[:-1, :] = frontier[1:, :]
            down = np.zeros((h, w), dtype=bool)
            down[1:, :] = frontier[:-1, :]
            left = np.zeros((h, w), dtype=bool)
            left[:, :-1] = frontier[:, 1:]
            right = np.zeros((h, w), dtype=bool)
            right[:, 1:] = frontier[:, :-1]

            frontier = (up | down | left | right) & candidate_mask & ~visited
            visited |= frontier

        arr[visited] = self.fill_color

        self.manual_image = Image.fromarray(arr)
        self._manual_commit_history()
        self.display_manual_image()
        self.manual_status.set(tr("t_filled_px", "Remplissage : {n} pixels", n=int(visited.sum())))
        logger.info(f"Remplissage: {int(visited.sum())} pixels")

    def magic_eraser(self, x, y):
        """Gomme magique - efface couleur similaire"""
        arr = np.array(self.manual_image)
        h, w = arr.shape[:2]

        if x < 0 or x >= w or y < 0 or y >= h:
            return

        target_color = tuple(arr[y, x])
        tolerance = self.fill_tolerance.get()

        # Trouver tous les pixels similaires (diff couleur vectorisée numpy)
        diff = np.abs(arr.astype(int) - np.array(target_color, dtype=int)).sum(axis=2)
        mask = diff <= tolerance
        erased = int(mask.sum())
        arr[mask] = [0, 0, 0]  # Noir

        self.manual_image = Image.fromarray(arr)
        self._manual_commit_history()
        self.display_manual_image()
        self.manual_status.set(tr("t_erased_px", "Gomme : {n} pixels effacés", n=erased))
        logger.info(f"Gomme magique: {erased} pixels")

    @staticmethod
    def _bounce_out(t):
        """Easing "bounce" (formule bounceOut de Robert Penner) : t (0-1) → valeur
        avec effet de rebond amorti en fin de course, comme une balle qui rebondit
        avant de s'arrêter."""
        n1, d1 = 7.5625, 2.75
        if t < 1 / d1:
            return n1 * t * t
        elif t < 2 / d1:
            t -= 1.5 / d1
            return n1 * t * t + 0.75
        elif t < 2.5 / d1:
            t -= 2.25 / d1
            return n1 * t * t + 0.9375
        else:
            t -= 2.625 / d1
            return n1 * t * t + 0.984375

    def _apply_easing(self, frames, easing):
        """Re-échantillonne la liste de frames selon une courbe de easing
        (remappage du temps, pas du contenu) : le nombre de frames et la durée
        totale sont inchangés, seule la vitesse relative à chaque instant varie.
        Fonctionne pour n'importe quel type d'animation puisque ça n'agit que sur
        l'ordre de lecture des frames déjà générées."""
        n = len(frames)
        if easing == "linear" or n < 3:
            return frames

        if easing == "ease-in":
            ease_fn = lambda t: t * t
        elif easing == "ease-out":
            ease_fn = lambda t: 1 - (1 - t) ** 2
        elif easing == "ease-in-out":
            ease_fn = lambda t: 3 * t * t - 2 * t * t * t
        elif easing == "bounce":
            ease_fn = self._bounce_out
        else:
            return frames

        result = []
        for i in range(n):
            t = i / (n - 1)
            idx = min(n - 1, max(0, round(ease_fn(t) * (n - 1))))
            result.append(frames[idx])
        return result

    @staticmethod
    def _apply_bounce_edges(frames):
        """Replie la séquence en aller-retour (comme le mode boucle "ping-pong",
        mais à l'intérieur d'un seul passage plutôt qu'entre deux boucles) puis la
        ré-échantillonne pour tenir dans le même nombre de frames — la durée totale
        ne change pas, seul le mouvement va et vient au lieu de s'arrêter/boucler
        sec en bout de course."""
        n = len(frames)
        if n < 3:
            return frames
        cycle = frames + frames[-2:0:-1]
        m = len(cycle)
        return [cycle[round(i * (m - 1) / (n - 1))] for i in range(n)]

    @staticmethod
    def _apply_opacity(frames, opacity):
        """Fondu global de l'animation vers le noir (0.0 = invisible, 1.0 =
        intensité normale) — appliqué en dernier, après tout ajustement de
        mouvement/timing, pour ne pas interférer avec les autres effets."""
        if opacity >= 0.999:
            return frames
        opacity = max(0.0, opacity)
        black = Image.new("RGB", frames[0].size, (0, 0, 0))
        return [Image.blend(black, f.convert("RGB"), opacity) for f in frames]

    def generate_manual_animation(self):
        """Génère l'animation avec les paramètres manuels"""
        if self.manual_image is None:
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"),
                lang_manager.get("load_one_image_first_warning", "Chargez une image d'abord"),
            )
            return

        # v101 : l'étape d'animation en attente est annulée (_anim_schedule) ;
        # l'ancien time.sleep(0.1) ne l'empêchait pas de repartir en parallèle
        # de la nouvelle boucle (aperçu 2×, 3× trop rapide après chaque régénération)
        self._anim_cancel("manual")
        self.manual_animating = False

        try:
            anim_type = self.manual_anim_type.get()
            fps = self.manual_fps.get()
            duration = self.manual_duration.get()
            speed = self.manual_scroll_speed.get()
            direction = self.manual_direction.get()

            # Redimensionner pour DMD
            img_resized, new_w, new_h = DMDEngine.adaptive_resize(
                self.manual_image,
                128,
                32,
                "auto",
                pixel_perfect=self.pixel_perfect_var.get(),
            )
            # v99 -- zoom de l'animation, appliqué après le calcul 128×32
            zoom = getattr(self, "manual_zoom", 1.0)
            if abs(zoom - 1.0) > 1e-6:
                new_w, new_h = max(1, round(new_w * zoom)), max(1, round(new_h * zoom))
                resample = (Image.Resampling.NEAREST if self.pixel_perfect_var.get()
                            else Image.Resampling.LANCZOS)
                img_resized = img_resized.resize((new_w, new_h), resample)

            self._manual_frames_zoomable = True  # v99 : frames d'animation, le zoom peut les refaire
            # Générer frames selon type
            if anim_type == "scroll":
                self.manual_frames = ManualEffects.scroll_effect(
                    img_resized, direction, speed, duration, fps
                )
            elif anim_type == "fade_in":
                self.manual_frames = ManualEffects.fade_effect(
                    img_resized, duration, fps, fade_in=True
                )
            elif anim_type == "fade_out":
                self.manual_frames = ManualEffects.fade_effect(
                    img_resized, duration, fps, fade_in=False
                )
            elif anim_type == "zoom_in":
                self.manual_frames = ManualEffects.zoom_effect(
                    img_resized, duration, fps, zoom_in=True
                )
            elif anim_type == "zoom_out":
                self.manual_frames = ManualEffects.zoom_effect(
                    img_resized, duration, fps, zoom_in=False
                )
            elif anim_type == "rotate":
                self.manual_frames = ManualEffects.rotate_effect(
                    img_resized, duration, fps
                )
            elif anim_type == "wave":
                self.manual_frames = ManualEffects.wave_effect(
                    img_resized, duration, fps
                )
            elif anim_type == "bounce":
                self.manual_frames = ManualEffects.bounce_effect(
                    img_resized, duration, fps
                )
            elif anim_type == "flash":
                self.manual_frames = ManualEffects.flash_effect(
                    img_resized, duration, fps
                )
            elif anim_type == "slide_left":
                self.manual_frames = ManualEffects.slide_effect(
                    img_resized, "left", duration, fps
                )
            elif anim_type == "slide_right":
                self.manual_frames = ManualEffects.slide_effect(
                    img_resized, "right", duration, fps
                )
            elif anim_type == "spiral":
                self.manual_frames = ManualEffects.spiral_effect(
                    img_resized, duration, fps
                )
            elif anim_type == "shake":
                self.manual_frames = ManualEffects.shake_effect(
                    img_resized, duration, fps
                )
            elif anim_type == "pulse":
                self.manual_frames = ManualEffects.pulse_effect(
                    img_resized, duration, fps
                )
            elif anim_type == "glitch":
                self.manual_frames = ManualEffects.glitch_effect(
                    img_resized, duration, fps
                )
            elif anim_type == "pixelate":
                self.manual_frames = ManualEffects.pixelate_effect(
                    img_resized, duration, fps
                )
            elif anim_type == "blur_transition":
                self.manual_frames = ManualEffects.blur_transition_effect(
                    img_resized, duration, fps
                )
            elif anim_type == "color_shift":
                self.manual_frames = ManualEffects.color_shift_effect(
                    img_resized, duration, fps
                )
            else:
                self.manual_frames = [img_resized]

            # Contrôles avancés (Inverser direction / Rebond aux bords / Easing) :
            # agissent tous par ré-échantillonnage de la séquence déjà générée,
            # donc s'appliquent de la même façon quel que soit le type
            # d'animation choisi ci-dessus.
            if self.manual_reverse.get():
                self.manual_frames = self.manual_frames[::-1]

            if self.manual_bounce_edges.get():
                self.manual_frames = self._apply_bounce_edges(self.manual_frames)

            self.manual_frames = self._apply_easing(
                self.manual_frames, self.manual_easing.get()
            )

            # Appliquer mode boucle
            loop_mode = self.manual_loop_mode.get()
            loop_count = self.manual_loop_count.get()

            if loop_mode == "ping-pong":
                # Ajouter frames inversées (sans dupliquer première/dernière)
                reversed_frames = self.manual_frames[-2:0:-1]
                self.manual_frames = self.manual_frames + reversed_frames

            if loop_mode == "infini" or loop_count > 1:
                # Répéter frames
                original_frames = self.manual_frames.copy()
                for _ in range(loop_count - 1):
                    self.manual_frames.extend(original_frames)

            # Délai début : pause statique (1ère frame) au tout début de la
            # séquence complète, une seule fois (pas répétée à chaque boucle).
            delay_frames = round(self.manual_delay_start.get() * fps)
            if delay_frames > 0 and self.manual_frames:
                self.manual_frames = (
                    [self.manual_frames[0]] * delay_frames + self.manual_frames
                )

            # Opacité : fondu global, appliqué en tout dernier sur la séquence
            # finale (après boucle/délai) pour toucher chaque frame affichée.
            self.manual_frames = self._apply_opacity(
                self.manual_frames, self.manual_opacity.get()
            )

            self.manual_frame_idx = 0
            self.manual_animating = True
            self._manual_frames_fps = fps
            self.manual_preview_status.set(
                f"Animation: {len(self.manual_frames)} frames @ {fps} FPS"
            )
            self._anim_schedule("manual", 0, self.animate_manual_preview)

            logger.info(
                f"Animation générée: {anim_type}, {len(self.manual_frames)} frames"
            )

        except Exception as e:
            messagebox.showerror(
                lang_manager.get("error", "Erreur"), f"{lang_manager.get('err_generation', 'Erreur génération')}: {e}"
            )
            logger.error(f"Erreur animation manuelle: {e}")

    def animate_manual_preview(self):
        """Animation de la preview manuelle. Si "Mode DMD / Forcer pixel-perfect"
        est coché (variable partagée avec l'onglet AUTO), chaque frame est rendue
        en simulation LED comme dans Aperçu DMD Principal — voir animate_preview
        pour le détail (même mécanisme, porté ici pour cohérence entre les 2
        onglets)."""
        if not self.manual_animating or not self.manual_frames:
            return

        try:
            frame = self.manual_frames[self.manual_frame_idx]
            if self._get_force_pixel_perfect():
                display = DMDEngine.render_led_style(
                    frame,
                    scale=4,
                    led_ratio=0.525,
                    glow=True,
                    brightness=self.led_brightness_var.get(),
                )
            else:
                display = frame.resize((512, 128), Image.Resampling.NEAREST)
            self.manual_preview_photo = ImageTk.PhotoImage(display)
            self.manual_preview_canvas.delete("all")
            self.manual_preview_canvas.create_image(
                256, 64, image=self.manual_preview_photo
            )

            self.manual_frame_idx = (self.manual_frame_idx + 1) % len(
                self.manual_frames
            )
            # v101 : cadence des images générées (pas le champ FPS en cours de saisie)
            fps = self._manual_frames_fps or self.manual_fps.get()
            delay = int(1000 / max(1, fps))
            self._anim_schedule("manual", delay, self.animate_manual_preview)
        except:
            self.manual_animating = False

    def manual_export(self):
        """Exporte le GIF manuel"""
        if not self.manual_frames:
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"),
                lang_manager.get("generate_animation_first_warning", "Générez d'abord une animation"),
            )
            return

        # v101 : cadence avec laquelle les images ont été générées (le champ FPS
        # a pu changer depuis, ou être en cours de saisie)
        frames_fps = self._manual_frames_fps or self.manual_fps.get()

        if self.review_target is not None:  # v97 : édition lancée depuis Revoir
            done = self._export_to_review(frames_fps)
            if done is not None:
                return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".gif", filetypes=[("GIF", "*.gif")]
        )

        if not file_path:
            return

        try:
            fps = frames_fps
            color_count = self.color_count_var.get()

            export_frames_to_gif(
                self.manual_frames,
                file_path,
                fps=fps,
                color_count=color_count,
                loop_mode=self.manual_loop_mode.get(),
                loop_count=self.manual_loop_count.get(),
                disposal=2,
                optimize=False,
            )

            # Marquer comme export manuel
            if self.current_image_idx is not None:
                img_path = self.images[self.current_image_idx]
                self.manual_exports.add(img_path)
                self.update_listbox()

            file_size = Path(file_path).stat().st_size / 1024
            quality_line = self._export_quality_line(self.manual_frames, fps, file_path)
            messagebox.showinfo(
                lang_manager.get("success", "Succès"),
                f"{lang_manager.get('gif_exported', 'GIF exporté')}: {Path(file_path).name}\n{file_size:.1f} KB"
                + quality_line,
            )
            logger.info(f"Export manuel: {Path(file_path).name}, {file_size:.1f} KB")

        except Exception as e:
            messagebox.showerror(
                lang_manager.get("error", "Erreur"), f"{lang_manager.get('err_export', 'Erreur export')}: {e}"
            )
            logger.error(f"Erreur export manuel: {e}")

    # ========================================================================
    # ONGLET TEXTSCROLL
    # ========================================================================

    def clear_text_placeholder(self, event):
        """Efface le placeholder au focus"""
        if self.text_input.get(1.0, tk.END).strip() == "Votre texte ici...":
            self.text_input.delete(1.0, tk.END)

    def restore_text_placeholder(self, event):
        """Restaure le placeholder si vide"""
        if not self.text_input.get(1.0, tk.END).strip():
            self.text_input.insert(1.0, lang_manager.get("your_text_here", "Votre texte ici..."))

    def choose_text_color(self):
        """Choisit la couleur du texte"""
        color = colorchooser.askcolor(
            title=tr("t_text_color", "Couleur du texte"), initialcolor=self.text_color
        )
        if color[0]:
            self.text_color = tuple(int(c) for c in color[0])
            hex_color = "#%02x%02x%02x" % self.text_color
            self.text_color_preview.config(bg=hex_color)
            logger.info(f"Couleur texte: {self.text_color}")

    def choose_text_bg(self):
        """Choisit la couleur de fond"""
        color = colorchooser.askcolor(
            title=tr("t_bg_color", "Couleur du fond"), initialcolor=self.text_bg_color
        )
        if color[0]:
            self.text_bg_color = tuple(int(c) for c in color[0])
            hex_color = "#%02x%02x%02x" % self.text_bg_color
            self.text_bg_preview.config(bg=hex_color)
            logger.info(f"Couleur fond: {self.text_bg_color}")

    def generate_text_preview(self):
        """Génère la preview du texte animé"""
        self.text_animating = False
        time.sleep(0.1)

        try:
            text_img = self.render_text_image()
            if text_img is None:
                messagebox.showwarning(
                    lang_manager.get("warning", "Attention"),
                    lang_manager.get("enter_text_warning", "Entrez du texte"),
                )
                return

            anim_type = self.text_anim_type.get()
            fps = self.text_fps.get()
            speed = self.text_speed.get()
            duration = self.text_duration.get()

            # Auto-ajuster durée selon longueur texte
            text_length = len(self.text_input.get(1.0, tk.END).strip())
            if text_length > 50:
                duration = max(duration, text_length / 10)

            font = self.get_text_font()

            # Générer animation
            if anim_type == "scroll_horizontal":
                self.text_frames = ManualEffects.scroll_effect(
                    text_img, "horizontal", speed, duration, fps
                )
            elif anim_type == "scroll_vertical":
                self.text_frames = ManualEffects.scroll_effect(
                    text_img, "vertical", speed, duration, fps
                )
            elif anim_type == "scroll_wave":
                self.text_frames = TextAnimations.scroll_wave(text_img, duration, fps)
            elif anim_type == "starwars":
                self.text_frames = TextAnimations.starwars_scroll(
                    text_img, duration, fps
                )
            elif anim_type == "bounce_scroll":
                self.text_frames = TextAnimations.bounce_scroll(text_img, duration, fps)
            elif anim_type == "typewriter":
                text = self.text_input.get(1.0, tk.END).strip()
                self.text_frames = TextAnimations.typewriter(
                    text, font, self.text_color, self.text_bg_color, duration, fps
                )
            elif anim_type == "explode":
                self.text_frames = TextAnimations.explode(text_img, duration, fps)
            elif anim_type == "matrix_rain":
                text = self.text_input.get(1.0, tk.END).strip()
                self.text_frames = TextAnimations.matrix_rain(text, font, duration, fps)
            elif anim_type == "spiral":
                self.text_frames = TextAnimations.spiral_text(text_img, duration, fps)
            elif anim_type == "shake":
                self.text_frames = TextAnimations.shake_text(text_img, duration, fps)
            elif anim_type == "glitch":
                self.text_frames = TextAnimations.glitch_text(text_img, duration, fps)
            elif anim_type == "fade_in":
                self.text_frames = ManualEffects.fade_effect(
                    text_img, duration, fps, fade_in=True
                )
            elif anim_type == "static":
                canvas = Image.new("RGB", (128, 32), self.text_bg_color)
                w, h = text_img.size
                canvas.paste(text_img, ((128 - w) // 2, 0))
                self.text_frames = [canvas] * int(fps * duration)
            else:
                self.text_frames = [text_img]

            self.text_frame_idx = 0
            self.text_animating = True

            # Calculer infos GIF
            total_frames = len(self.text_frames)
            estimated_size = total_frames * 128 * 32 * 3 / 1024  # Estimation grossière

            self.text_preview_status.set(
                tr("t_text_anim_status", "Animation : {frames} frames @ {fps} FPS", frames=total_frames, fps=fps)
            )
            self.text_gif_info.set(
                tr("t_text_gif_info", "Durée : {dur:.1f}s | Taille estimée : {size:.1f} KB", dur=duration, size=estimated_size)
            )

            self._anim_schedule("text", 0, self.animate_text_preview)
            logger.info(f"Texte animé: {anim_type}, {total_frames} frames")

        except Exception as e:
            messagebox.showerror(
                lang_manager.get("error", "Erreur"),
                f"{lang_manager.get('err_text_generation', 'Erreur génération texte')}: {e}",
            )
            logger.error(f"Erreur texte: {e}")

    def animate_text_preview(self):
        """Animation de la preview texte. Si "Mode DMD / Forcer pixel-perfect"
        est coché (variable partagée avec AUTO/MANUEL), chaque frame est rendue
        en simulation LED comme dans les 2 autres onglets — voir animate_preview
        pour le détail (même mécanisme)."""
        if not self.text_animating or not self.text_frames:
            return

        try:
            frame = self.text_frames[self.text_frame_idx]
            if self._get_force_pixel_perfect():
                display = DMDEngine.render_led_style(
                    frame,
                    scale=4,
                    led_ratio=0.525,
                    glow=True,
                    brightness=self.led_brightness_var.get(),
                )
            else:
                display = frame.resize((512, 128), Image.Resampling.NEAREST)
            self.text_preview_photo = ImageTk.PhotoImage(display)
            self.text_preview_canvas.delete("all")
            self.text_preview_canvas.create_image(
                256, 64, image=self.text_preview_photo
            )

            self.text_frame_idx = (self.text_frame_idx + 1) % len(self.text_frames)
            delay = int(1000 / self.text_fps.get())
            self._anim_schedule("text", delay, self.animate_text_preview)
        except:
            self.text_animating = False

    def export_text_gif(self):
        """Exporte le GIF texte"""
        if not self.text_frames:
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"),
                lang_manager.get("generate_text_preview_first_warning", "Générez d'abord une preview"),
            )
            return

        # Nom par défaut: 40 premiers caractères du texte
        text = self.text_input.get(1.0, tk.END).strip()
        default_name = text[:40].replace(" ", "_").replace("\n", "_") + "_dmd.gif"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".gif",
            initialfile=default_name,
            filetypes=[("GIF", "*.gif")],
        )

        if not file_path:
            return

        try:
            fps = self.text_fps.get()
            color_count = self.color_count_var.get()

            export_frames_to_gif(
                self.text_frames,
                file_path,
                fps=fps,
                color_count=color_count,
                loop_mode=self.manual_loop_mode.get(),
                loop_count=self.manual_loop_count.get(),
                disposal=2,
                optimize=False,
            )

            file_size = Path(file_path).stat().st_size / 1024
            quality_line = self._export_quality_line(self.text_frames, fps, file_path)
            messagebox.showinfo(
                lang_manager.get("success", "Succès"),
                f"{lang_manager.get('gif_text_exported', 'GIF texte exporté')}: "
                f"{Path(file_path).name}\n{file_size:.1f} KB" + quality_line,
            )
            logger.info(f"Export texte: {Path(file_path).name}, {file_size:.1f} KB")

        except Exception as e:
            messagebox.showerror(
                lang_manager.get("error", "Erreur"), f"{lang_manager.get('err_export', 'Erreur export')}: {e}"
            )
            logger.error(f"Erreur export texte: {e}")

    # ========================================================================
    # PARAMETRES
    # ========================================================================

    def clear_cache(self):
        """Vide le cache"""
        self.image_settings.clear()
        self.proposals.clear()
        messagebox.showinfo(
            lang_manager.get("success", "Succès"), lang_manager.get("cache_cleared", "Cache vidé")
        )
        logger.info("Cache vidé")

    def export_logs(self):
        """Exporte les logs"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"dmd_logs_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            filetypes=[("Text", "*.txt")],
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for entry in logger.logs:
                    f.write(f"[{entry['time']}] {entry['level']}: {entry['message']}\n")

            logs_exported_label = lang_manager.get("logs_exported", "Logs exportés")
            messagebox.showinfo(
                lang_manager.get("success", "Succès"), f"{logs_exported_label}: {Path(file_path).name}"
            )
            logger.info(f"Logs exportés: {file_path}")
        except Exception as e:
            messagebox.showerror(
                lang_manager.get("error", "Erreur"),
                f"{lang_manager.get('err_export_logs', 'Erreur export logs')}: {e}",
            )

    def on_closing(self):
        """Gestion propre de la fermeture"""
        try:
            # Arrêter les animations en cours
            self.animating = False
            self.manual_animating = False
            self.text_animating = False
            self.video_animating = False
            # Libère le VideoCapture du lecteur intégré (onglet VIDEO) —
            # évite de fuir un descripteur de fichier ouvert.
            self._video_playback_stop_capture()

            # Sauvegarder config
            config_manager.save()

            logger.info("Application fermée proprement")
        except:
            pass
        finally:
            self.root.destroy()

    # ========================================================================
    # MAIN
    # ========================================================================

    def run(self):
        """Lance l'application"""
        self.root.mainloop()

    # ============================================================================
    # POINT D'ENTRÉE
    # ============================================================================

    def update_manual_info(self):
        """Met à jour les informations de l'image manuelle"""
        if not self.manual_image:
            self.manual_info_text.config(state="normal")
            self.manual_info_text.delete(1.0, tk.END)
            self.manual_info_text.insert(1.0, tr("t_no_image_loaded", "Aucune image chargée"))
            self.manual_info_text.config(state="disabled")
            return

        w, h = self.manual_image.size
        mode = self.manual_image.mode

        # Calculer taille mémoire approximative
        pixel_count = w * h
        if mode == "RGB":
            mem_size = pixel_count * 3
        elif mode == "RGBA":
            mem_size = pixel_count * 4
        else:
            mem_size = pixel_count

        mem_kb = mem_size / 1024

        # Palette dominante
        try:
            palette = DMDEngine.detect_palette(self.manual_image, max_colors=8)
            palette_str = "\n".join([f"  RGB{c}" for c in palette[:5]])
        except:
            palette_str = "  N/A"

        # Ratio vs DMD
        ratio = w / h if h > 0 else 0
        target_ratio = 128 / 32
        ratio_diff = abs(ratio - target_ratio)
        ratio_status = tr("t_ratio_ok", "✓ Optimal") if ratio_diff < 0.5 else tr("t_ratio_adjust", "⚠ Ajuster")

        info = tr(
            "t_manual_info", K_DEFAULT_MANUAL_INFO,
            w=w, h=h, mode=mode, mem=mem_kb, ratio=ratio, status=ratio_status, palette=palette_str,
            count=len(self.manual_history), pos=self.manual_history_index + 1,
        )

        self.manual_info_text.config(state="normal")
        self.manual_info_text.delete(1.0, tk.END)
        self.manual_info_text.insert(1.0, info)
        self.manual_info_text.config(state="disabled")

    def apply_font_to_textbox(self, event=None):
        """Applique la police sélectionnée à la zone de texte"""
        family = self.text_font_family.get()
        size = max(8, min(16, self.text_font_size.get() - 4))  # Adapter pour lisibilité

        weight = "bold" if self.text_bold.get() else "normal"
        slant = "italic" if self.text_italic.get() else "roman"

        try:
            import tkinter.font as tkfont

            font = tkfont.Font(family=family, size=size, weight=weight, slant=slant)
            self.text_input.config(font=font)
            logger.debug(f"Police appliquée à la zone texte: {family} {size}pt")
        except Exception as e:
            logger.warning(f"Impossible d'appliquer la police: {e}")

    # ========================================================================
    # NOUVELLES MÉTHODES - CROP MODE
    # ========================================================================

    def start_crop_mode(self):
        """Active le mode sélection de zone"""
        if self.manual_image is None:
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"),
                lang_manager.get("load_one_image_first_warning", "Chargez une image d'abord"),
            )
            return

        if self.crop_mode:  # 2e clic sur le bouton : annule
            self._crop_stop(tr("t_crop_off", "Recadrage désactivé"))
            return
        self._zone_mode_stop()  # v103 : un seul mode souris à la fois

        # v98 -- cadre 4:1 posé d'emblée, à DÉPLACER (demande utilisateur : le
        # tracer à la main n'était pas précis). Taille par défaut 128×32 px de
        # l'image = 1 pixel par LED ; molette = taille (ratio 4:1 gardé),
        # flèches = 1 px (Maj : 10 px), double-clic ou Entrée = appliquer,
        # Échap = annuler. Coordonnées tenues en pixels de l'image.
        self.crop_mode = True
        self.fill_mode = False
        self.eraser_mode = False
        self.fill_btn.config(text=tr("fill", "🎨 Remplissage"))
        self.eraser_btn.config(text=tr("eraser", "🧹 Gomme Magique"))
        w, h = self.manual_image.size
        cw = min(128, w, 4 * h)
        ch = max(1, cw // 4)
        cw = ch * 4
        self.crop_box = [(w - cw) // 2, (h - ch) // 2, cw, ch]
        self.crop_start = None
        c = self.manual_canvas
        c.config(cursor="fleur")
        c.unbind("<Button-1>")
        c.bind("<ButtonPress-1>", self.on_crop_start)
        c.bind("<B1-Motion>", self.on_crop_drag)
        c.bind("<ButtonRelease-1>", self.on_crop_end)
        c.bind("<Double-Button-1>", lambda e: self._crop_apply())
        c.bind("<MouseWheel>", self._crop_wheel)
        c.bind("<Return>", lambda e: self._crop_apply())
        c.bind("<Escape>", lambda e: self._crop_stop(tr("t_crop_off", "Recadrage désactivé")))
        for key, dx, dy in (("Left", -1, 0), ("Right", 1, 0), ("Up", 0, -1), ("Down", 0, 1)):
            c.bind(f"<{key}>", lambda e, dx=dx, dy=dy: self._crop_nudge(dx, dy, 1))
            c.bind(f"<Shift-{key}>", lambda e, dx=dx, dy=dy: self._crop_nudge(dx, dy, 10))
        c.focus_set()
        self._crop_draw()
        logger.info("Crop mode ON")

    # --- v103 : zone d'effets ----------------------------------------------------
    def _manual_zone_merge(self, base, effected):
        """Image `base` dont seule la zone reçoit le contenu de `effected`
        (même taille) ; sans zone, `effected` tel quel."""
        z = self.manual_zone
        if not z or base.size != effected.size:
            return effected
        out = base.copy()
        out.paste(effected.crop(tuple(z)), (z[0], z[1]))
        return out

    def toggle_zone_mode(self):
        if self.manual_image is None:
            messagebox.showwarning(lang_manager.get("warning", "Attention"),
                                   lang_manager.get("load_one_image_first_warning", "Chargez une image d'abord"))
            return
        if self.zone_mode:
            self._zone_mode_stop()
            return
        if self.crop_mode:
            self._crop_stop(None)
        if self.fill_mode or self.eraser_mode:
            self.fill_mode = self.eraser_mode = False
            self.fill_btn.config(text=tr("fill", "🎨 Remplissage"))
            self.eraser_btn.config(text=tr("eraser", "🧹 Gomme Magique"))
        self.zone_mode = True
        c = self.manual_canvas
        c.config(cursor="tcross")
        c.unbind("<Button-1>")
        c.bind("<ButtonPress-1>", self._zone_press)
        c.bind("<B1-Motion>", self._zone_motion)
        c.bind("<ButtonRelease-1>", self._zone_release)
        c.bind("<Escape>", lambda e: self._zone_mode_stop())
        c.focus_set()
        self.zone_btn.config(text=tr("t_zone_btn_active", "▭ Zone (ACTIF)"))
        self._zone_draw()

    def _zone_mode_stop(self):
        if not self.zone_mode:
            return
        self.zone_mode = False
        self._zone_drag = None
        c = self.manual_canvas
        for seq in ("<ButtonPress-1>", "<B1-Motion>", "<ButtonRelease-1>", "<Escape>"):
            c.unbind(seq)
        c.bind("<Button-1>", self.on_manual_click)
        c.config(cursor="arrow")
        self.zone_btn.config(text=tr("t_zone_btn", "▭ Zone"))
        self._zone_draw()

    def _manual_zone_clear(self, quiet=False):
        had = self.manual_zone is not None
        self.manual_zone = None
        if had and not quiet:
            self.apply_manual_effect()  # réglages en cours : de nouveau sur toute l'image
        self._zone_draw()
        if had:
            self.manual_status.set(tr("t_zone_cleared", "Zone effacée : effets sur toute l'image"))

    def _zone_img_xy(self, event):
        s, ox, oy = self._crop_geom()
        w, h = self.manual_image.size
        return (max(0, min(w, int(round((event.x - ox) / s)))),
                max(0, min(h, int(round((event.y - oy) / s)))))

    def _zone_press(self, event):
        x, y = self._zone_img_xy(event)
        z = self.manual_zone
        if z and z[0] <= x <= z[2] and z[1] <= y <= z[3]:
            self._zone_drag = ("move", x - z[0], y - z[1])  # clic dans la zone : on la déplace
        else:
            self._zone_drag = ("new", x, y)  # clic dehors : nouvelle zone tracée

    def _zone_motion(self, event):
        if not self._zone_drag:
            return
        x, y = self._zone_img_xy(event)
        w, h = self.manual_image.size
        kind, a, b = self._zone_drag
        if kind == "move":
            z = self.manual_zone
            zw, zh = z[2] - z[0], z[3] - z[1]
            nx, ny = max(0, min(w - zw, x - a)), max(0, min(h - zh, y - b))
            self.manual_zone = [nx, ny, nx + zw, ny + zh]
        else:
            self.manual_zone = [min(a, x), min(b, y), max(a, x), max(b, y)]
        self._zone_draw()

    def _zone_release(self, event):
        if not self._zone_drag:
            return
        self._zone_motion(event)
        self._zone_drag = None
        z = self.manual_zone
        if z and (z[2] - z[0] < 2 or z[3] - z[1] < 2):
            self.manual_zone = None  # simple clic hors zone : zone effacée
        self.apply_manual_effect()  # les réglages en cours suivent la zone
        self._zone_draw()

    def _zone_draw(self):
        c = self.manual_canvas
        c.delete("zone")
        z = self.manual_zone
        if self.manual_image is None:
            return
        if z and (z[2] > self.manual_image.size[0] or z[3] > self.manual_image.size[1]):
            self.manual_zone = z = None  # image changée (annuler, rotation…)
        if z:
            s, ox, oy = self._crop_geom()
            c.create_rectangle(ox + z[0] * s, oy + z[1] * s, ox + z[2] * s, oy + z[3] * s,
                               outline="#00e5ff", width=2, dash=(4, 3), tags="zone")
            t = c.create_text(ox + z[0] * s + 3, oy + z[1] * s + 2, anchor="nw", fill="#00e5ff",
                              font=("Segoe UI", 8), tags="zone",
                              text=tr("t_zone_label", "Zone {w}×{h}", w=z[2] - z[0], h=z[3] - z[1]))
            bx = c.bbox(t)
            c.tag_lower(c.create_rectangle(bx[0] - 2, bx[1] - 1, bx[2] + 2, bx[3] + 1, fill="#101010",
                                           outline="", tags="zone"), t)
        if self.zone_mode:
            text = tr("t_zone_hint", "Zone : tracez un rectangle (glisser), glissez dedans pour le déplacer ; "
                                     "curseurs et filtres ne touchent que la zone. Échap ou ▭ Zone = terminer")
            t = c.create_text(6, 4, text=text, anchor="nw", fill="white", width=628,
                              font=("Segoe UI", 9), tags="zone")
            bx = c.bbox(t)
            c.tag_lower(c.create_rectangle(bx[0] - 3, bx[1] - 2, bx[2] + 3, bx[3] + 2, fill="#202020",
                                           outline="#505050", tags="zone"), t)

    def _crop_geom(self):
        """(échelle, décalage x, décalage y) de l'image dans le canvas 640×320
        (même calcul que display_manual_image)."""
        w, h = self.manual_image.size
        s = min(640 / w, 320 / h)
        return s, (640 - int(w * s)) // 2, (320 - int(h * s)) // 2

    def _crop_clamp(self):
        w, h = self.manual_image.size
        b = self.crop_box
        if b[2] > w or b[3] > h:  # image changée (annuler/rétablir) : cadre réduit
            b[3] = max(1, min(h, w // 4))
            b[2] = b[3] * 4
        b[0] = max(0, min(b[0], w - b[2]))
        b[1] = max(0, min(b[1], h - b[3]))

    def _crop_draw(self):
        self._crop_clamp()
        s, ox, oy = self._crop_geom()
        x, y, cw, ch = self.crop_box
        c = self.manual_canvas
        if self.crop_preview_rect:
            c.delete(self.crop_preview_rect)
        c.delete("crop_hint")
        self.crop_preview_rect = c.create_rectangle(
            ox + x * s, oy + y * s, ox + (x + cw) * s, oy + (y + ch) * s, outline="red", width=2, dash=(5, 5)
        )
        per_led = cw / 128.0
        text = tr(
            "t_crop_status",
            "Cadre {w}×{h} px ({k} px par LED) en ({x}, {y}) — glisser pour déplacer, molette = taille, "
            "flèches = 1 px (Maj : 10), double-clic ou Entrée = appliquer, Échap = annuler",
            w=cw, h=ch, k=f"{per_led:.2f}".rstrip("0").rstrip("."), x=x, y=y)
        self.manual_status.set(text)
        # le libellé d'état est sous le canvas, hors de la fenêtre sur un écran
        # de 1080 px : l'aide du cadre est aussi écrite en haut du canvas
        t = c.create_text(6, 4, text=text, anchor="nw", fill="white", width=628,
                          font=("Segoe UI", 9), tags="crop_hint")
        bx = c.bbox(t)
        c.tag_lower(c.create_rectangle(bx[0] - 3, bx[1] - 2, bx[2] + 3, bx[3] + 2, fill="#202020",
                                       outline="#505050", tags="crop_hint"), t)
        c.tag_raise(self.crop_preview_rect)  # le cadre reste visible, même tout en haut

    def on_crop_start(self, event):
        """Prise du cadre : clic dedans = on le déplace ; clic dehors = il est
        centré sur le point cliqué."""
        s, ox, oy = self._crop_geom()
        ix, iy = (event.x - ox) / s, (event.y - oy) / s
        x, y, cw, ch = self.crop_box
        if not (x <= ix <= x + cw and y <= iy <= y + ch):
            self.crop_box[0], self.crop_box[1] = int(round(ix - cw / 2)), int(round(iy - ch / 2))
            self._crop_clamp()
        self.crop_start = (ix - self.crop_box[0], iy - self.crop_box[1])
        self.manual_canvas.focus_set()
        self._crop_draw()

    def on_crop_drag(self, event):
        if not self.crop_start:
            return
        s, ox, oy = self._crop_geom()
        ix, iy = (event.x - ox) / s, (event.y - oy) / s
        self.crop_box[0] = int(round(ix - self.crop_start[0]))
        self.crop_box[1] = int(round(iy - self.crop_start[1]))
        self._crop_clamp()
        self._crop_draw()

    def on_crop_end(self, event):
        self.crop_start = None  # le cadre reste en place ; appliquer = double-clic/Entrée

    def _crop_wheel(self, event):
        w, h = self.manual_image.size
        x, y, cw, ch = self.crop_box
        step = 1.1 if event.delta > 0 else 1 / 1.1
        new_ch = int(round(ch * step))
        if new_ch == ch:
            new_ch = ch + (1 if event.delta > 0 else -1)
        new_ch = max(2, min(new_ch, h, w // 4))
        new_cw = new_ch * 4
        cx, cy = x + cw / 2, y + ch / 2
        self.crop_box = [int(round(cx - new_cw / 2)), int(round(cy - new_ch / 2)), new_cw, new_ch]
        self._crop_clamp()
        self._crop_draw()

    def _crop_nudge(self, dx, dy, n):
        self.crop_box[0] += dx * n
        self.crop_box[1] += dy * n
        self._crop_clamp()
        self._crop_draw()
        return "break"

    def _crop_apply(self):
        if not self.crop_mode or self.manual_image is None:
            return
        x, y, cw, ch = self.crop_box
        self.manual_image = self.manual_image.crop((x, y, x + cw, y + ch))
        self.manual_zone = None  # v103 : coordonnées de la zone invalides après recadrage
        self._manual_commit_history()
        self._crop_stop(None)
        self.display_manual_image()
        self.manual_status.set(tr("t_crop_applied", "Recadrage appliqué : {w}×{h}px", w=cw, h=ch))
        logger.info(f"Crop: {cw}×{ch} en ({x}, {y})")

    def _crop_stop(self, message):
        c = self.manual_canvas
        for seq in ("<ButtonPress-1>", "<B1-Motion>", "<ButtonRelease-1>", "<Double-Button-1>", "<MouseWheel>",
                    "<Return>", "<Escape>", "<Left>", "<Right>", "<Up>", "<Down>",
                    "<Shift-Left>", "<Shift-Right>", "<Shift-Up>", "<Shift-Down>"):
            c.unbind(seq)
        c.bind("<Button-1>", self.on_manual_click)
        c.config(cursor="arrow")
        if self.crop_preview_rect:
            c.delete(self.crop_preview_rect)
            self.crop_preview_rect = None
        c.delete("crop_hint")
        self.crop_start = None
        self.crop_mode = False
        if message:
            self.manual_status.set(message)
            logger.info("Crop mode OFF")

    # ========================================================================
    # NOUVELLES MÉTHODES - SÉLECTION AUTO
    # ========================================================================

    def select_all_images(self):
        """Sélectionne toutes les images"""
        self.image_tree.selection_set(self.image_tree.get_children())
        logger.info("Toutes les images sélectionnées")

    def deselect_all_images(self):
        """Désélectionne toutes les images"""
        self.image_tree.selection_remove(self.image_tree.get_children())
        logger.info("Sélection effacée")

    def invert_selection(self):
        """Inverse la sélection"""
        current = set(int(i) for i in self.image_tree.selection())
        all_indices = set(range(len(self.images)))
        new_selection = all_indices - current

        self.image_tree.selection_set([str(idx) for idx in new_selection])

        logger.info(f"Sélection inversée: {len(new_selection)} images")

    # ========================================================================
    # MÉTHODES - MULTI-IMAGES ET MORPHING
    # ========================================================================

    def load_multiple_manual_images(self):
        """Charge plusieurs images pour morphing"""
        files = filedialog.askopenfilenames(
            title=tr("t_select_morph_images", "Sélectionner des images pour le morphing"),
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.raw565")],
        )

        if files:
            self.multi_images = []
            self.multi_images_listbox.delete(0, tk.END)

            for file in files:
                try:
                    img = DMDEngine.ensure_rgb_on_black(DMDEngine.load_image(file))
                    self.multi_images.append(img)
                    self.multi_images_listbox.insert(tk.END, Path(file).name)
                except Exception as e:
                    logger.error(f"Erreur chargement {file}: {e}")

            if self.multi_images:
                self.multi_images_frame.pack(fill=tk.X, pady=(0, 10))
                self.manual_status.set(
                    f"{len(self.multi_images)} images chargées pour morphing"
                )
                logger.info(f"{len(self.multi_images)} images chargées")

                # Charger première image
                self.manual_image = self.multi_images[0].copy()
                self.manual_original = self.manual_image.copy()
                self.display_manual_image()

    def on_multi_image_select(self, event):
        """Callback sélection image dans liste multi"""
        selection = self.multi_images_listbox.curselection()
        if selection and self.multi_images:
            idx = selection[0]
            self.manual_image = self.multi_images[idx].copy()
            self.manual_original = self.manual_image.copy()
            self.display_manual_image()
            self.manual_status.set(tr("t_image_n_of", "Image {n}/{total}", n=idx + 1, total=len(self.multi_images)))

    def clear_multi_images(self):
        """Efface la liste multi-images"""
        self.multi_images = []
        self.multi_images_listbox.delete(0, tk.END)
        self.multi_images_frame.pack_forget()
        self.manual_status.set(tr("t_multi_cleared", "Liste multi-images effacée"))
        logger.info("Multi-images effacées")

    def generate_morphing_animation(self):
        """Génère une animation de morphing entre les images"""
        if len(self.multi_images) < 2:
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"),
                lang_manager.get("morphing_needs_2_images", "Chargez au moins 2 images pour le morphing"),
            )
            return

        self.manual_status.set(tr("t_morph_running", "Génération du morphing..."))
        self.root.update()

        try:
            fps = self.manual_fps.get()
            transition_frames = int(fps * 1.0)  # 1 seconde par transition

            self.manual_frames = []
            self._manual_frames_zoomable = False  # v99 : morphing, le zoom ne le refait pas

            # Redimensionner toutes les images à la même taille
            target_size = self.multi_images[0].size
            resized_images = [
                img.resize(target_size, Image.Resampling.LANCZOS)
                for img in self.multi_images
            ]

            # Dimensions cible DMD constantes pour toute la fonction (target_size fixe)
            w, h = target_size
            scale = min(128 / w, 32 / h)
            new_w, new_h = int(w * scale), int(h * scale)
            x = (128 - new_w) // 2
            y = (32 - new_h) // 2

            # Générer transitions entre chaque paire
            for i in range(len(resized_images) - 1):
                img1 = np.array(resized_images[i])
                img2 = np.array(resized_images[i + 1])

                # Interpolation linéaire
                for frame_idx in range(transition_frames):
                    alpha = frame_idx / transition_frames
                    blended = (img1 * (1 - alpha) + img2 * alpha).astype(np.uint8)

                    # Centrer sur canvas DMD
                    canvas = Image.new("RGB", (128, 32), (0, 0, 0))
                    blended_img = Image.fromarray(blended).resize(
                        (new_w, new_h), Image.Resampling.LANCZOS
                    )
                    canvas.paste(blended_img, (x, y))

                    self.manual_frames.append(canvas)

                # Ajouter image finale (pause) : contenu identique à chaque frame de la
                # pause, on ne redimensionne/colle donc qu'une seule fois
                pause_canvas = Image.new("RGB", (128, 32), (0, 0, 0))
                img_final = resized_images[i + 1].resize(
                    (new_w, new_h), Image.Resampling.LANCZOS
                )
                pause_canvas.paste(img_final, (x, y))
                self.manual_frames.extend([pause_canvas] * int(fps * 0.5))

            # Lancer animation
            self.manual_frame_idx = 0
            self.manual_animating = True
            self._manual_frames_fps = fps  # v101 : cadence de ces images
            self._anim_schedule("manual", 0, self.animate_manual_preview)

            self.manual_preview_status.set(
                tr("t_morph_status", "Morphing : {frames} frames, {images} images",
                   frames=len(self.manual_frames), images=len(self.multi_images))
            )
            self.manual_status.set(tr("t_morph_done", "Morphing généré !"))
            logger.info(f"Morphing: {len(self.manual_frames)} frames")

        except Exception as e:
            messagebox.showerror(
                lang_manager.get("error", "Erreur"),
                f"{lang_manager.get('err_morphing_generation', 'Erreur génération morphing')}:\n{e}",
            )
            logger.error(f"Erreur morphing: {e}")
            self.manual_status.set(tr("t_morph_error", "Erreur morphing"))

    def _build_font_registry(self):
        """Cache famille→fichier via registre Windows"""
        if hasattr(self, "_font_registry_cache"):
            return self._font_registry_cache

        registry = {}
        fonts_dir = Path("C:/Windows/Fonts")

        try:
            import winreg

            key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"

            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    key = winreg.OpenKey(hive, key_path)
                except (FileNotFoundError, OSError):
                    continue

                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        i += 1
                    except OSError:
                        break

                    if (
                        not name
                        or "(TrueType)" not in name
                        and "(OpenType)" not in name
                    ):
                        continue

                    # "Arial Bold (TrueType)" → "Arial Bold"
                    full_name = re.sub(
                        r"\s*\((?:TrueType|OpenType)\)\s*$", "", name
                    ).strip()

                    # Résoudre chemin
                    if Path(value).is_absolute():
                        filepath = Path(value)
                    else:
                        filepath = fonts_dir / value

                    if not filepath.exists():
                        continue

                    # Détecter style
                    name_lower = full_name.lower()
                    is_bold = "bold" in name_lower or "gras" in name_lower
                    is_italic = (
                        "italic" in name_lower
                        or "oblique" in name_lower
                        or "italique" in name_lower
                    )

                    # Extraire famille (sans Bold/Italic)
                    family = full_name
                    for kw in [
                        "Bold Italic",
                        "Gras Italique",
                        "Bold Oblique",
                        "Bold",
                        "Gras",
                        "Italic",
                        "Italique",
                        "Oblique",
                        "Regular",
                    ]:
                        family = re.sub(
                            r"\s+" + re.escape(kw) + r"$",
                            "",
                            family,
                            flags=re.IGNORECASE,
                        )
                    family = family.strip()

                    fl = family.lower()
                    if fl not in registry:
                        registry[fl] = {}
                    registry[fl][(is_bold, is_italic)] = filepath

                try:
                    winreg.CloseKey(key)
                except:
                    pass

            logger.info(f"[FontRegistry] {len(registry)} familles indexées")
        except Exception as e:
            logger.error(f"[FontRegistry] Erreur: {e}")

        self._font_registry_cache = registry
        return registry

    def get_text_font(self):
        """Récupère police via registre"""
        family = self.text_font_family.get()
        size = self.text_font_size.get()
        is_bold = self.text_bold.get() if hasattr(self, "text_bold") else False
        is_italic = self.text_italic.get() if hasattr(self, "text_italic") else False

        logger.info(f"[get_text_font] {family} {size}pt B={is_bold} I={is_italic}")

        registry = self._build_font_registry()
        styles = registry.get(family.lower())

        if styles:
            wanted = (is_bold, is_italic)

            # 1. Style exact
            if wanted in styles:
                fp = styles[wanted]
                try:
                    font = ImageFont.truetype(str(fp), size)
                    logger.info(f"  ✓ {fp.name}")
                    return font
                except Exception as e:
                    logger.warning(f"  ⚠ {fp.name}: {e}")

            # 2. Fallback prioritaire
            for sk in [(is_bold, False), (False, is_italic), (False, False)]:
                if sk in styles:
                    fp = styles[sk]
                    try:
                        font = ImageFont.truetype(str(fp), size)
                        logger.info(f"  ✓ {fp.name} (fallback)")
                        return font
                    except:
                        continue

            # 3. Premier disponible
            for fp in styles.values():
                try:
                    font = ImageFont.truetype(str(fp), size)
                    logger.info(f"  ✓ {fp.name} (1er dispo)")
                    return font
                except:
                    continue

        # PIL direct
        try:
            font = ImageFont.truetype(family, size)
            logger.info(f"  ✓ {family} (PIL)")
            return font
        except:
            pass

        # Fallback Arial
        logger.warning(f"  ⚠ {family} introuvable, Arial défaut")
        try:
            return ImageFont.truetype("arial.ttf", size)
        except:
            return ImageFont.load_default()

    def _get_usable_fonts(self):
        """Liste des polices réellement utilisables (présentes dans le registre)

        Important: ne pas utiliser de cache pour que les polices ajoutées
        par l'utilisateur soient prises en compte à chaque lancement (et
        lors d'un refresh éventuel).
        """
        registry = self._build_font_registry()

        if registry:
            # Familles avec capitalisation propre depuis registre
            # On reconstruit les noms avec leur casse originale
            try:
                import winreg

                key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
                proper_names = {}  # {lower: ProperCase}

                for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                    try:
                        key = winreg.OpenKey(hive, key_path)
                    except (FileNotFoundError, OSError):
                        continue

                    i = 0
                    while True:
                        try:
                            name, _, _ = winreg.EnumValue(key, i)
                            i += 1
                        except OSError:
                            break

                        if not name:
                            continue
                        if "(TrueType)" not in name and "(OpenType)" not in name:
                            continue

                        full_name = re.sub(
                            r"\s*\((?:TrueType|OpenType)\)\s*$", "", name
                        ).strip()

                        # Extraire famille (sans Bold/Italic)
                        family = full_name
                        for kw in [
                            "Bold Italic",
                            "Gras Italique",
                            "Bold Oblique",
                            "Bold",
                            "Gras",
                            "Italic",
                            "Italique",
                            "Oblique",
                            "Regular",
                        ]:
                            family = re.sub(
                                r"\s+" + re.escape(kw) + r"$",
                                "",
                                family,
                                flags=re.IGNORECASE,
                            )
                        family = family.strip()

                        fl = family.lower()
                        if fl in registry and fl not in proper_names:
                            proper_names[fl] = family

                    try:
                        winreg.CloseKey(key)
                    except:
                        pass

                # Liste triée
                fonts = sorted(proper_names.values())
                logger.info(f"[FontList] {len(fonts)} polices utilisables")
                return fonts
            except Exception as e:
                logger.warning(f"[FontList] Erreur: {e}")

        # Fallback: utiliser tkfont
        try:
            from tkinter import font as tkfont

            fonts = sorted(
                [f for f in set(tkfont.families()) if f and not f.startswith("@")]
            )
            return fonts
        except Exception:
            return ["Arial", "Times New Roman", "Courier New"]

    def update_progress(self, percent, filename):
        self.progress_text_var.set(tr("t_batch_progress", "Traitement {pct}% : {name}", pct=percent, name=filename))
        self.progress_bar_var.set(percent)
        if hasattr(self, "progressbar"):
            self.progressbar.update_idletasks()

    # v87 -- notes de dmd_quality, du meilleur au pire : (code, libellé FR par
    # défaut, couleur de pastille). v88 : libellés traduits au lieu des emoji
    # (Tk/boîtes Windows les affichent en gris, indiscernables).
    _QUALITY_RATINGS = (("Excellent", "Excellent", "#f5c518"), ("Good", "Bon", "#3cb043"),
                        ("Acceptable", "Acceptable", "#e0d000"), ("Poor", "Faible", "#ff8c00"),
                        ("Bad", "Mauvais", "#e53935"))

    @staticmethod
    def _rating_label(code):
        default = next((fr for c, fr, _ in DMDConverter._QUALITY_RATINGS if c == code), code)
        return tr(f"t_rating_{code.lower()}", default)

    def _quality_distribution(self, counts):
        return " · ".join(f"{self._rating_label(c)} {counts.get(c, 0)}" for c, _, _ in self._QUALITY_RATINGS)

    def _export_quality_line(self, frames, fps, file_path):
        """v89 -- ligne de score pour le récapitulatif d'un export unique
        (MANUEL/VIDEO/TEXTSCROLL), GIF statique non pénalisé. "" en cas
        d'échec : le score n'est qu'une aide, jamais bloquant."""
        try:
            q = dq.evaluate_frames(frames, int(1000 / max(1, fps)), penalize_static=False)
        except Exception as e:
            logger.warning(f"Score qualité non calculé : {e}")
            return ""
        why = ", ".join(q.reasons_text(lang_manager.current_lang))
        logger.info(f"Score qualité {Path(file_path).name} : {q.score}/100 ({q.rating}) — {why}")
        return "\n" + tr("t_export_quality", "Score qualité : {score}/100 ({rating}) — {why}",
                         score=q.score, rating=self._rating_label(q.rating), why=why)

    def _quality_summary_text(self, summary):
        """Deux lignes pour la boîte de fin de lot : moyenne + répartition."""
        if not summary or not summary.get("count"):
            return ""
        return "\n\n" + tr(
            "t_quality_summary", "Score qualité : {count} GIF, moyenne {mean}/100",
            count=summary["count"], mean=summary["mean"],
        ) + "\n" + self._quality_distribution(summary.get("by_rating", {}))

    def clear_progress_and_notify(self, success_count, total, output_dir, errors=None,
                                  quality_summary=None):
        """success_count/total/errors (2026-08-05, demande utilisateur) : plus
        d'erreur affichée en popup PENDANT le lot (voir process_images) -- le
        résumé complet arrive ici, en une seule notification à la toute fin,
        au lieu de bloquer sur chaque image en échec.
        quality_summary (v87) : dmd_quality.summarize() du lot, ajouté au message."""
        errors = errors or []
        error_count = len(errors)
        quality_text = self._quality_summary_text(quality_summary)
        if quality_summary:
            # v94 -- dossier du dernier lot noté : le bouton 🔍 Revoir l'ouvre directement
            # (écrit ici, dans le fil Tk, jamais depuis le fil du lot)
            config_manager.set("last_review_folder", str(output_dir).strip())

        self.progress_text_var.set(tr("t_batch_done", "Terminé : {ok}/{total} GIF créés", ok=success_count, total=total))
        self.progress_bar_var.set(0)

        if error_count:
            # Détail complet dans les logs (onglet DEBUG), jamais en popup —
            # c'est justement ce que le popup bloquant faisait à tort avant.
            logger.warning(
                f"Batch : {error_count} erreur(s) sur {total} image(s) — "
                + "; ".join(errors)
            )

        # Proposer d'ouvrir le dossier de sortie -- seulement si au moins un
        # GIF a réellement été produit (sinon rien d'utile à y ouvrir).
        if success_count > 0:
            if error_count:
                batch_msg = lang_manager.get(
                    "batch_complete_open_folder_errors",
                    "{success}/{total} GIF créés dans:\n{output_dir}\n\n"
                    "⚠️ {errors} erreur(s) — voir l'onglet DEBUG pour le détail.\n\n"
                    "Voulez-vous ouvrir le dossier ?",
                ).format(
                    success=success_count,
                    total=total,
                    output_dir=output_dir,
                    errors=error_count,
                )
            else:
                batch_msg = lang_manager.get(
                    "batch_complete_open_folder",
                    "{total} GIF créés dans:\n{output_dir}\n\nVoulez-vous ouvrir le dossier ?",
                ).format(total=success_count, output_dir=output_dir)
            if quality_text:
                # résumé qualité juste avant la question finale (dernier paragraphe)
                head, sep, question = batch_msg.rpartition("\n\n")
                batch_msg = head + quality_text + sep + question if sep else batch_msg + quality_text
            response = messagebox.askyesno(lang_manager.get("complete", "Terminé"), batch_msg)
            if response:
                try:
                    output_dir = str(output_dir).strip()
                    if not Path(output_dir).exists():
                        raise FileNotFoundError(f"Dossier introuvable: {output_dir}")

                    import subprocess

                    # Meilleure compatibilité Windows (OneDrive, chemins spéciaux)
                    os.startfile(output_dir)  # type: ignore[attr-defined]
                    logger.info(f"Dossier ouvert: {output_dir}")
                except Exception as e:
                    logger.error(f"Impossible d'ouvrir le dossier via explorer: {e}")
            # v88 -- GIF faibles (Poor/Bad) : proposer la fenêtre "Revoir"
            if quality_summary:
                weak = sum(quality_summary.get("by_rating", {}).get(r, 0) for r in ("Poor", "Bad"))
                if weak and messagebox.askyesno(
                    lang_manager.get("confirmation", "Confirmation"),
                    tr("t_review_offer", "{n} GIF ont un score faible ou mauvais.\n"
                       "Ouvrir la fenêtre « Revoir » ?", n=weak),
                ):
                    self.open_review_window(str(output_dir).strip())
        elif error_count:
            # Aucune image réussie : un seul résumé, pas de proposition
            # d'ouvrir un dossier vide.
            fail_msg = lang_manager.get(
                "batch_all_failed",
                "Aucun GIF créé — {errors} erreur(s) sur {total} image(s). "
                "Voir l'onglet DEBUG pour le détail.",
            ).format(errors=error_count, total=total)
            messagebox.showerror(lang_manager.get("error", "Erreur"), fail_msg)

        logger.info(f"Batch terminé: {success_count}/{total} GIF ({error_count} erreur(s))")


# --- Pipeline delegation vers modules externes (qualité/rendu) ---
try:
    from .dmd_pipeline_quality import (
        hash_image as _hash_image,
        evaluate_quality as _evaluate_quality,
        score_variant as _score_variant,
        analyze_characteristics as _analyze_characteristics,
        render_dmd_frame as _render_dmd_frame,
        resize_will_shrink_text_too_much as _resize_will_shrink_text_too_much,
        generate_settings_variants as _generate_settings_variants,
        best_variant as _best_variant_pure,
        optimize_cleanup_and_pixel_perfect as _optimize_cleanup_and_pixel_perfect_pure,
        resolve_image_settings as _resolve_image_settings,
        shape_forces_fill as _shape_forces_fill,
        FILL_MIN_RATIO_DEFAULT as _FILL_MIN_RATIO_DEFAULT,
        maybe_invert_dark as _maybe_invert_dark,
        _resolve_from_image,
        apply_render_profile as _apply_render_profile,
        TONAL_REFINEMENT_PARAMS as _TONAL_REFINEMENT_PARAMS,
    )
except ImportError:
    from dmd_pipeline_quality import (
        hash_image as _hash_image,
        evaluate_quality as _evaluate_quality,
        score_variant as _score_variant,
        analyze_characteristics as _analyze_characteristics,
        render_dmd_frame as _render_dmd_frame,
        resize_will_shrink_text_too_much as _resize_will_shrink_text_too_much,
        generate_settings_variants as _generate_settings_variants,
        best_variant as _best_variant_pure,
        optimize_cleanup_and_pixel_perfect as _optimize_cleanup_and_pixel_perfect_pure,
        resolve_image_settings as _resolve_image_settings,
        shape_forces_fill as _shape_forces_fill,
        FILL_MIN_RATIO_DEFAULT as _FILL_MIN_RATIO_DEFAULT,
        maybe_invert_dark as _maybe_invert_dark,
        _resolve_from_image,
        apply_render_profile as _apply_render_profile,
        TONAL_REFINEMENT_PARAMS as _TONAL_REFINEMENT_PARAMS,
    )


def _pipeline_hash_image(self, img):
    return _hash_image(img)


def _pipeline_evaluate_quality(
    self, original_img, dmd_canvas, settings=None, pixel_perfect=False
):
    return _evaluate_quality(
        original_img,
        dmd_canvas,
        settings=settings,
        pixel_perfect=pixel_perfect,
    )


def _pipeline_score_variant(
    self, original_img, settings, pixel_perfect=False, cleanup_power=None,
    fidelity_weight=0.0, return_breakdown=False, resize_cache=None,
):
    """Score occupation+lisibilité (+fidélité tonale optionnelle, voir
    dmd_engine.py/dmd_converter.py v42). Voir dmd_pipeline_quality.score_variant.
    `resize_cache` : voir dmd_converter.py v78 / dmd_pipeline_quality.py v21
    (plan perf batch, Tier 0) — oublié ici lors du 1er passage (ce wrapper de
    délégation n'est pas nommé `score_variant` dans ce fichier, donc invisible
    à une recherche par nom exact ; l'appel réel `self.score_variant(...)`
    passe PAR ce wrapper), confirmé par une TypeError réelle en test bout-en-
    bout plutôt que par relecture seule."""
    return _score_variant(
        original_img,
        settings,
        pixel_perfect=pixel_perfect,
        cleanup_power=cleanup_power,
        fidelity_weight=fidelity_weight,
        return_breakdown=return_breakdown,
        resize_cache=resize_cache,
    )


def _pipeline_analyze_characteristics(self, canvas):
    """Caractéristiques d'un rendu DMD (occupation/contours/coloration), utilisées
    pour choisir des effets artistiques adaptés. Voir
    dmd_pipeline_quality.analyze_characteristics."""
    return _analyze_characteristics(canvas)


def _pipeline_resize_will_shrink_text_too_much(self, original_img, fit_scale):
    """Estime si le mode Resize/fit va réduire le texte source sous un seuil de
    lisibilité (hauteur de lettre projetée après resize), auquel cas Fill/scroll
    doit être préféré quel que soit le score brut. Plus appelée depuis v86
    (remplacée par la règle de forme, voir shape_forces_fill) ; conservée pour
    compatibilité, seuil fixe 8 px (le réglage "Seuil lettrage" a été retiré).
    Voir dmd_pipeline_quality.resize_will_shrink_text_too_much."""
    min_letter_px = 8.0
    return _resize_will_shrink_text_too_much(
        original_img, fit_scale, min_letter_px=min_letter_px
    )


def _pipeline_render_dmd_frame(
    self,
    image_path,
    settings,
    return_frames=False,
    cleanup=True,
    cleanup_power=1.0,
    return_direction=False,
    return_source=False,
):
    # Une variante (typiquement la proposition "Optimisé") peut forcer pixel_perfect
    # indépendamment de la case à cocher globale, via settings["_pixel_perfect"].
    if "_pixel_perfect" in settings:
        pixel_perfect = bool(settings["_pixel_perfect"])
    else:
        pixel_perfect = False
        try:
            pixel_perfect = bool(self.pixel_perfect_var.get())
        except Exception:
            pixel_perfect = False

    return _render_dmd_frame(
        image_path,
        settings,
        return_frames=return_frames,
        cleanup=cleanup,
        cleanup_power=cleanup_power,
        pixel_perfect=pixel_perfect,
        return_direction=return_direction,
        return_source=return_source,
    )


class ProfileEditor:
    """v92 -- fenêtre de création/modification d'un profil (dmd_profiles) :
    tous les paramètres éditables, chacun expliqué (infobulle au survol + bouton
    « ? » en popup), validation avant enregistrement. Remplace toute édition
    manuelle de profiles.json."""

    # (clé, type, libellé FR par défaut, bornes/choix, clé de l'explication)
    FIELDS = (
        ("fps", "int", "FPS (images/s)", (1, 60, 1), "tooltip_pe_fps"),
        ("duration", "float", "Durée minimale (s)", (0.5, 60, 0.5), "tooltip_pe_duration"),
        ("scroll_speed", "float", "Vitesse de défilement (px/image)", (0.1, 10, 0.1), "tooltip_scroll_speed"),
        ("contrast", "float", "Contraste", (0.5, 3.0, 0.05), "tooltip_pe_contrast"),
        ("saturation", "float", "Saturation", (0.0, 3.0, 0.05), "tooltip_pe_saturation"),
        ("color_count", "choice", "Couleurs GIF", (8, 16, 32, 64, 128, 256), "tooltip_pe_color_count"),
        ("pixel_perfect", "tristate", "Mode DMD / pixel-perfect", None, "tooltip_pixel_perfect"),
        ("fill_min_ratio", "opt_float", "Défilement imposé dès (L/H)", (1.0, 8.0, 0.5), "tooltip_fill_ratio"),
        ("invert_dark", "bool", "Inverser les logos sombres", None, "tooltip_invert_dark"),
        ("max_scroll_cycle_s", "opt_float", "Plafond aller-retour (s)", (2, 600, 5), "tooltip_scroll_cap"),
    )

    def __init__(self, app, key=None):
        """key=None : nouveau profil prérempli avec les réglages actuels ;
        sinon modification du profil `key`."""
        self.app, self.key = app, key
        profile = app.profiles.get(key) if key else None
        values = dict(profile) if profile else app._current_profile_values()
        self.builtin = bool(profile and profile.get("builtin"))

        win = self.win = tk.Toplevel(app.root)
        win.title(tr("t_pe_title_edit", "Modifier le profil") if key else tr("t_pe_title_new", "Nouveau profil"))
        win.transient(app.root)
        win.resizable(False, False)
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text=tr("t_pe_name", "Nom du profil :")).grid(row=0, column=0, sticky=tk.W, pady=4)
        self.name_var = tk.StringVar(value=app._profile_label(key) if key else "")
        name_entry = ttk.Entry(frm, textvariable=self.name_var, width=34)
        name_entry.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=4)
        if self.builtin:
            name_entry.state(["disabled"])  # profil fourni : nom fixe (traduit)

        self.vars = {}
        for i, (k, typ, label, spec, help_key) in enumerate(self.FIELDS, start=1):
            lbl = ttk.Label(frm, text=tr(f"t_pe_{k}", label))
            lbl.grid(row=i, column=0, sticky=tk.W, pady=3)
            add_help_tooltip(lbl, help_key)
            cell = ttk.Frame(frm)
            cell.grid(row=i, column=1, sticky=tk.W, pady=3)
            v = values.get(k)
            if typ in ("int", "float"):
                lo, hi, step = spec
                var = tk.StringVar(value="" if v is None else str(v))
                ttk.Spinbox(cell, from_=lo, to=hi, increment=step, textvariable=var, width=8).pack(side=tk.LEFT)
                self.vars[k] = var
            elif typ == "choice":
                var = tk.StringVar(value=str(v if v is not None else 256))
                ttk.Combobox(cell, textvariable=var, values=[str(c) for c in spec], width=6,
                             state="readonly").pack(side=tk.LEFT)
                self.vars[k] = var
            elif typ == "tristate":
                self._tri = [tr("t_pe_unchanged", "Inchangé"), tr("t_pe_yes", "Oui"), tr("t_pe_no", "Non")]
                var = tk.StringVar(value=self._tri[0] if v is None else (self._tri[1] if v else self._tri[2]))
                ttk.Combobox(cell, textvariable=var, values=self._tri, width=10,
                             state="readonly").pack(side=tk.LEFT)
                self.vars[k] = var
            elif typ == "bool":
                var = tk.BooleanVar(value=True if v is None else bool(v))
                ttk.Checkbutton(cell, variable=var, text=tr("t_pe_enabled", "Activé")).pack(side=tk.LEFT)
                self.vars[k] = var
            else:  # opt_float : case "activé" + valeur
                lo, hi, step = spec
                on = tk.BooleanVar(value=v is not None)
                var = tk.StringVar(value=str(v if v is not None else (2.0 if k == "fill_min_ratio" else 30)))
                ttk.Checkbutton(cell, variable=on, text=tr("t_pe_enabled", "Activé")).pack(side=tk.LEFT)
                ttk.Spinbox(cell, from_=lo, to=hi, increment=step, textvariable=var, width=8).pack(side=tk.LEFT, padx=(6, 0))
                self.vars[k] = (on, var)
            ttk.Button(frm, text="?", width=2,
                       command=lambda t=tr(f"t_pe_{k}", label), h=help_key:
                       messagebox.showinfo(t, lang_manager.get(h, h), parent=win)
                       ).grid(row=i, column=2, sticky=tk.W, padx=(8, 0))

        btns = ttk.Frame(frm)
        btns.grid(row=len(self.FIELDS) + 1, column=0, columnspan=3, sticky=tk.E, pady=(12, 0))
        ttk.Button(btns, text=tr("t_pe_cancel", "Annuler"), command=win.destroy).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(btns, text=tr("t_pe_save", "💾 Enregistrer"), command=self.save).pack(side=tk.RIGHT)
        win.grab_set()

    def _collect(self):
        """(valeurs, None) ou (None, message d'erreur)."""
        out = {}
        for k, typ, label, spec, _h in self.FIELDS:
            name = tr(f"t_pe_{k}", label)
            try:
                if typ in ("int", "float"):
                    raw = self.vars[k].get().strip().replace(",", ".")
                    val = int(float(raw)) if typ == "int" else float(raw)
                    lo, hi, _s = spec
                    if not lo <= val <= hi:
                        raise ValueError
                    out[k] = val
                elif typ == "choice":
                    out[k] = int(self.vars[k].get())
                elif typ == "tristate":
                    idx = self._tri.index(self.vars[k].get())
                    out[k] = None if idx == 0 else (idx == 1)
                elif typ == "bool":
                    out[k] = bool(self.vars[k].get())
                else:
                    on, var = self.vars[k]
                    if on.get():
                        val = float(var.get().strip().replace(",", "."))
                        lo, hi, _s = spec
                        if not lo <= val <= hi:
                            raise ValueError
                        out[k] = val
                    else:
                        out[k] = None
            except (ValueError, tk.TclError):
                lo_hi = f" ({spec[0]} – {spec[1]})" if isinstance(spec, tuple) and len(spec) == 3 else ""
                return None, tr("t_pe_invalid", "Valeur invalide : {name}{range}", name=name, range=lo_hi)
        return out, None

    def save(self):
        values, err = self._collect()
        if err:
            messagebox.showerror(lang_manager.get("error", "Erreur"), err, parent=self.win)
            return
        label = None if self.builtin else self.name_var.get().strip()
        if not self.builtin and not label:
            messagebox.showerror(lang_manager.get("error", "Erreur"),
                                 tr("t_pe_name_missing", "Donnez un nom au profil."), parent=self.win)
            return
        key = self.key or dmd_profiles.new_profile_key(label, self.app.profiles)
        dmd_profiles.save_profile(config_manager.user_dir, key, values, label=label)
        logger.info(f"Profil enregistré (éditeur) : {label or key} {values}")
        self.win.destroy()
        self.app._refresh_profile_combo(key)
        self.app._on_profile_selected()


def review_replace_gif(folder, rel, new_path, quality, code):
    """v97 -- remplace le GIF `rel` d'un dossier de lot par `new_path` :
    l'original part dans _a_revoir/_avant_correction/ (jamais supprimé,
    suffixe _2, _3… si une version y est déjà), l'index garde la nouvelle
    note, fixed=code et score_before (note d'origine, conservée d'une
    correction à l'autre). Renvoie (note d'origine, chemin de l'original).
    Commun aux corrections acceptées et à l'édition MANUEL depuis Revoir."""
    orig = os.path.join(folder, *rel.split("/"))
    bak = os.path.join(folder, dq.REVIEW_DIR, dmd_autofix.BEFORE_DIR, *rel.split("/"))
    if os.path.exists(bak):
        stem, ext = os.path.splitext(bak)
        n = 2
        while os.path.exists(f"{stem}_{n}{ext}"):
            n += 1
        bak = f"{stem}_{n}{ext}"
    os.makedirs(os.path.dirname(bak), exist_ok=True)
    shutil.move(orig, bak)
    try:
        shutil.move(new_path, orig)
    except Exception:
        shutil.move(bak, orig)  # remet l'original en place
        raise
    rows = dq.load_index(folder)
    row = rows.get(rel, {})
    before = row.get("score_before", row.get("score"))
    row.update(score=quality["score"], rating=quality["rating"], color=quality["color"],
               reasons=quality["reasons"], fixed=code, score_before=before)
    rows[rel] = row
    dq.save_index(folder, rows)
    return before, bak


class ReviewWindow:
    """v88 -- fenêtre "Revoir" : GIF d'un dossier de sortie triés du pire au
    meilleur selon dmd_scores.json (dmd_quality), aperçu LED animé au clic,
    déplacement (jamais suppression) des GIF <= seuil vers _a_revoir.
    Aide à la relecture uniquement : rien n'est déplacé sans confirmation."""

    CHUNK = 1000  # lignes insérées par tour de boucle Tk (fenêtre jamais figée)

    def __init__(self, app, folder):
        self.app, self.folder = app, str(folder)
        self.lang = lang_manager.current_lang
        self.items = []          # [(rel, info)]
        self.sort_key, self.sort_desc = "score", False
        self._fill_job = self._anim_job = None
        self._frames, self._delays, self._idx = [], [], 0
        self._photo = None
        # v96 -- corrections proposées : rel -> {"state", "props", "note"} ;
        # calcul en arrière-plan, fichiers proposés dans un dossier temporaire
        self.fixes = {}
        self._iid = {}
        self._players = []
        self._fix_thread = None
        self._fix_cancel = threading.Event()
        self._work_root = None
        self._job_seq = 0
        self._current_rel = None

        win = self.win = tk.Toplevel(app.root)
        win.title(tr("t_review_title", "Revoir les GIF — {folder}", folder=self.folder))
        win.geometry("1280x880")
        win.protocol("WM_DELETE_WINDOW", self.close)

        # Pastilles dessinées (les emoji couleur s'affichent en gris dans Tk sous Windows)
        self.dots = {}
        for code, _fr, color in DMDConverter._QUALITY_RATINGS:
            im = Image.new("RGBA", (56, 56), (0, 0, 0, 0))
            ImageDraw.Draw(im).ellipse((4, 4, 52, 52), fill=color)
            self.dots[code] = ImageTk.PhotoImage(im.resize((14, 14), Image.Resampling.LANCZOS))

        self.summary_var = tk.StringVar()
        ttk.Label(win, textvariable=self.summary_var, padding=(6, 6, 6, 0)).pack(fill=tk.X)
        top = ttk.Frame(win, padding=6)
        top.pack(fill=tk.X)
        ttk.Button(top, text=tr("t_review_open_folder", "📂 Ouvrir le dossier"),
                   command=self.open_folder).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text=tr("t_review_other_folder", "📂 Autre dossier…"),
                   command=self.change_folder).pack(side=tk.LEFT)
        self.fix_var = tk.StringVar()
        ttk.Label(top, textvariable=self.fix_var).pack(side=tk.LEFT, padx=12)
        self.fix_btn = ttk.Button(top, text=tr("t_fix_button", "🪄 Proposer des corrections ≤ seuil"),
                                  command=self.start_fixes)
        self.fix_btn.pack(side=tk.RIGHT, padx=4)
        add_help_tooltip(self.fix_btn, "tooltip_fix_button")
        self.move_btn = ttk.Button(top, text=tr("t_review_move", "Déplacer ≤ seuil vers {dest}", dest=dq.REVIEW_DIR),
                                   command=self.move_low)
        self.move_btn.pack(side=tk.RIGHT, padx=4)
        self.threshold_var = tk.IntVar(value=30)
        ttk.Spinbox(top, from_=0, to=100, textvariable=self.threshold_var, width=5).pack(side=tk.RIGHT)
        ttk.Label(top, text=tr("t_review_threshold", "Seuil :")).pack(side=tk.RIGHT, padx=(12, 4))

        body = ttk.PanedWindow(win, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        left = ttk.Frame(body)
        cols = ("score", "file", "reasons", "fix")
        self.tree = ttk.Treeview(left, columns=cols, show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="", command=lambda: self.sort_by("score"))
        self.tree.column("#0", width=30, minwidth=30, stretch=False, anchor=tk.CENTER)
        heads = {"score": tr("t_review_col_score", "Score"),
                 "file": tr("t_review_col_file", "Fichier"), "reasons": tr("t_review_col_reasons", "Raisons"),
                 "fix": tr("t_fix_col", "Correction")}
        widths = {"score": 60, "file": 330, "reasons": 230, "fix": 120}
        for c in cols:
            self.tree.heading(c, text=heads[c], command=lambda k=c: self.sort_by(k))
            self.tree.column(c, width=widths[c], stretch=c not in ("score", "fix"),
                             anchor=tk.CENTER if c in ("score", "fix") else tk.W)
        sb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        body.add(left, weight=3)

        right = ttk.Frame(body, padding=(8, 0))
        # v97 -- image source au-dessus du GIF produit
        self.src_var = tk.StringVar()
        ttk.Label(right, textvariable=self.src_var).pack(anchor=tk.W)
        self.src_canvas = tk.Canvas(right, width=512, height=96, bg="black", highlightthickness=0)
        self.src_canvas.pack(pady=(2, 8))
        self._src_photo = None
        self.canvas = tk.Canvas(right, width=512, height=128, bg="black", highlightthickness=0)
        self.canvas.pack(pady=(0, 8))
        self.detail_var = tk.StringVar()
        ttk.Label(right, textvariable=self.detail_var, wraplength=512, justify=tk.LEFT).pack(anchor=tk.W)
        self.edit_btn = ttk.Button(right, text=tr("t_review_edit", "✎ Éditer dans MANUEL"), command=self.edit_manual)
        self.edit_btn.pack(anchor=tk.W, pady=(6, 0))
        self.edit_btn.state(["disabled"])
        add_help_tooltip(self.edit_btn, "tooltip_review_edit")
        self.fix_frame = ttk.Frame(right)  # v96 -- propositions du GIF sélectionné
        self.fix_frame.pack(fill=tk.X, anchor=tk.W, pady=(10, 0))
        body.add(right, weight=2)

        self.reload()

    # --- données -----------------------------------------------------------
    def reload(self):
        rows = dq.load_index(self.folder)
        self.items = dq.sorted_rows(rows)  # sans les GIF déjà déplacés
        s = dq.summarize(rows)
        self.summary_var.set(tr("t_quality_summary", "Score qualité : {count} GIF, moyenne {mean}/100",
                                count=s["count"], mean=s["mean"])
                             + "   —   " + self.app._quality_distribution(s["by_rating"]))
        self.sort_by(self.sort_key, keep_order=True)

    def sort_by(self, key, keep_order=False):
        if not keep_order:
            # v96 : la colonne Correction trie d'abord les plus gros gains
            self.sort_desc = (not self.sort_desc) if key == self.sort_key else (key == "fix")
            self.sort_key = key
        getter = {
            "score": lambda kv: kv[1]["score"],
            "file": lambda kv: kv[0].lower(),
            "reasons": lambda kv: ", ".join(dq.reason_text(c, self.lang) for c in kv[1]["reasons"]),
            "fix": lambda kv: self._fix_gain(*kv),
        }[key]
        self.items.sort(key=getter, reverse=self.sort_desc)
        self._refill()

    def _refill(self):
        if self._fill_job:
            self.win.after_cancel(self._fill_job)
        self.tree.delete(*self.tree.get_children())
        self._fill_from(0)

    def _fill_from(self, start):
        if start == 0:
            self._iid = {}
        for i, (rel, info) in enumerate(self.items[start:start + self.CHUNK], start):
            why = ", ".join(dq.reason_text(c, self.lang) for c in info["reasons"])
            self.tree.insert("", tk.END, iid=str(i), image=self.dots.get(info["rating"], ""),
                             values=(info["score"], rel, why, self._fix_text(rel, info)))
            self._iid[rel] = str(i)
        nxt = start + self.CHUNK
        self._fill_job = self.win.after(1, self._fill_from, nxt) if nxt < len(self.items) else None

    # --- aperçu --------------------------------------------------------------
    def on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        rel, info = self.items[int(sel[0])]
        self._stop_anim()
        self._current_rel = rel
        self.edit_btn.state(["!disabled"])
        self._show_source(rel, info)
        self._show_fixes(rel, info)
        path = os.path.join(self.folder, *rel.split("/"))
        self._frames, self._delays = [], []
        try:
            with Image.open(path) as im:
                for i in range(getattr(im, "n_frames", 1)):
                    im.seek(i)
                    self._frames.append(im.convert("RGB"))
                    self._delays.append(int(im.info.get("duration", 100) or 100))
        except Exception as e:
            self.detail_var.set(f"{rel}\n{e}")
            return
        total_s = sum(self._delays) / 1000.0
        why = ", ".join(dq.reason_text(c, self.lang) for c in info["reasons"])
        self.detail_var.set(tr("t_review_detail", "{rating} {score}/100 — {rel}\n{n} images, {s} s\n{why}",
                               rating=DMDConverter._rating_label(info["rating"]), score=info["score"], rel=rel,
                               n=len(self._frames), s=f"{total_s:.1f}", why=why))
        self._idx = 0
        self._animate()

    def _animate(self):
        if not self._frames:
            return
        frame = self._frames[self._idx]
        display = DMDEngine.render_led_style(frame, scale=4, led_ratio=0.525, glow=True,
                                             brightness=self.app.led_brightness_var.get())
        self._photo = ImageTk.PhotoImage(display)
        self.canvas.delete("all")
        self.canvas.create_image(256, 64, image=self._photo)
        delay = self._delays[self._idx]
        self._idx = (self._idx + 1) % len(self._frames)
        if len(self._frames) > 1:
            self._anim_job = self.win.after(delay, self._animate)

    def _stop_anim(self):
        if self._anim_job:
            self.win.after_cancel(self._anim_job)
            self._anim_job = None

    # --- actions -------------------------------------------------------------
    def move_low(self):
        try:
            thr = int(self.threshold_var.get())
        except (tk.TclError, ValueError):
            return
        todo = dq.review_low(self.folder, thr, dry_run=True)
        if not todo:
            messagebox.showinfo(lang_manager.get("complete", "Terminé"),
                                tr("t_review_none", "Aucun GIF de score ≤ {thr}.", thr=thr), parent=self.win)
            return
        if not messagebox.askyesno(
            lang_manager.get("confirmation", "Confirmation"),
            tr("t_review_move_confirm",
               "Déplacer {n} GIF de score ≤ {thr} vers :\n{dest}\n\n"
               "Les fichiers sont déplacés (arborescence conservée), jamais supprimés.",
               n=len(todo), thr=thr, dest=os.path.join(self.folder, dq.REVIEW_DIR)),
            parent=self.win,
        ):
            return
        self._stop_anim()
        self._frames = []
        self.move_btn.state(["disabled"])

        def work():
            try:
                moved, err = dq.review_low(self.folder, thr), None
            except Exception as e:
                moved, err = [], e
            self.win.after(0, self._moved, moved, err)

        threading.Thread(target=work, daemon=True).start()

    def _moved(self, moved, err):
        self.move_btn.state(["!disabled"])
        if err is not None:
            logger.error(f"Revoir : déplacement interrompu : {err}")
            messagebox.showerror(lang_manager.get("error", "Erreur"), str(err), parent=self.win)
        else:
            logger.info(f"Revoir : {len(moved)} GIF déplacés vers {dq.REVIEW_DIR}")
            messagebox.showinfo(lang_manager.get("complete", "Terminé"),
                                tr("t_review_moved", "{n} GIF déplacés vers {dest}.", n=len(moved),
                                   dest=dq.REVIEW_DIR), parent=self.win)
        self.reload()

    # --- v96 : corrections proposées ------------------------------------------
    @staticmethod
    def _fix_label(code):
        names = {"trim": tr("t_fix_step_trim", "vide retiré"), "gamma": tr("t_fix_step_gamma", "gamma"),
                 "levels": tr("t_fix_step_levels", "niveaux"),
                 "dark_lift": tr("t_fix_step_dark_lift", "sombres éclaircis"),
                 "invert": tr("t_fix_step_invert", "inversion"),
                 "manual": tr("t_fix_step_manual", "édition manuelle")}
        return " + ".join(names.get(s, s) for s in code.split("+"))

    def _fix_gain(self, rel, info):
        f = self.fixes.get(rel)
        if f and f["state"] == "ready":
            return max(p["score"] for p in f["props"]) - info["score"]
        if info.get("fixed"):
            return -1
        return -2 if f else -3

    def _fix_text(self, rel, info):
        if info.get("fixed"):
            return tr("t_fix_state_done", "✓ {before} → {score}", before=info.get("score_before", "?"),
                      score=info["score"])
        f = self.fixes.get(rel)
        if not f:
            return ""
        if f["state"] == "pending":
            return tr("t_fix_state_pending", "calcul…")
        if f["state"] == "ready":
            return tr("t_fix_state_ready", "🪄 +{gain}", gain=self._fix_gain(rel, info))
        if f["state"] == "refused":
            return tr("t_fix_state_refused", "refusée")
        return "—"

    def _update_fix_cell(self, rel):
        iid = self._iid.get(rel)
        info = dict(self.items).get(rel) if iid is not None else None
        if iid is not None and info is not None and self.tree.exists(iid):
            self.tree.set(iid, "fix", self._fix_text(rel, info))

    def start_fixes(self):
        if self._fix_thread is not None and self._fix_thread.is_alive():
            return
        try:
            thr = int(self.threshold_var.get())
        except (tk.TclError, ValueError):
            return
        targets = [(rel, info) for rel, info in self.items
                   if info["score"] <= thr and not info.get("fixed") and rel not in self.fixes]
        if not targets:
            messagebox.showinfo(lang_manager.get("complete", "Terminé"),
                                tr("t_fix_none_todo", "Aucun GIF de score ≤ {thr} à corriger.", thr=thr),
                                parent=self.win)
            return
        data = dmd_autofix.load_batches(self.folder)
        batches = data.get("batches", [])

        def known(info):
            b = info.get("b")
            return bool(info.get("src")) and isinstance(b, int) and 0 <= b < len(batches)

        legacy_root = None
        if any(not known(info) for _rel, info in targets):
            # dossier produit avant la v96 : ni source ni réglages enregistrés
            messagebox.showinfo(
                lang_manager.get("warning", "Attention"),
                tr("t_fix_legacy",
                   "Ce dossier a été produit avant l'enregistrement des réglages du lot.\n"
                   "Choisissez le dossier des images SOURCE de ce lot : les corrections utiliseront "
                   "les réglages actuels de l'onglet AUTO (profil « {profile} »).",
                   profile=self.app.profile_var.get()),
                parent=self.win)
            legacy_root = self._pick_source_root()
            if not legacy_root:
                return
            cur = (self.app.batch_params_snapshot(), self.app.color_count_var.get(),
                   self.app.manual_loop_mode.get(), self.app.manual_loop_count.get())

        jobs, missing = [], 0
        for rel, info in targets:
            if known(info):
                rec = batches[info["b"]]
                src = info["src"]
                params = (rec["batch_params"], rec.get("color_count_fallback", 256),
                          rec.get("loop_mode", "infini"), rec.get("loop_count", 0))
            else:
                src = dmd_autofix.find_source(legacy_root, rel)
                params = cur
            if not src or not os.path.isfile(src):
                missing += 1
                continue
            jobs.append((rel, src, params, info["score"]))
        extra = tr("t_fix_missing", "\n{m} GIF sans image source retrouvée sont ignorés.", m=missing) if missing else ""
        if not jobs:
            messagebox.showwarning(lang_manager.get("warning", "Attention"),
                                   tr("t_fix_no_job", "Aucune image source retrouvée pour ces GIF."),
                                   parent=self.win)
            return
        if not messagebox.askyesno(
            lang_manager.get("confirmation", "Confirmation"),
            tr("t_fix_confirm",
               "Chercher des corrections pour {n} GIF de score ≤ {thr} ?\n\n"
               "Le calcul se fait en arrière-plan. Aucun GIF n'est modifié tant que vous "
               "n'acceptez pas une proposition.", n=len(jobs), thr=thr) + extra,
            parent=self.win,
        ):
            return
        if self._work_root is None:
            import tempfile
            self._work_root = tempfile.mkdtemp(prefix="dmd_autofix_")
        for rel, *_ in jobs:
            self.fixes[rel] = {"state": "pending", "props": [], "note": None}
            self._update_fix_cell(rel)
        self._fix_cancel.clear()
        self._fix_counts = [0, len(jobs), 0]  # traités, total, avec proposition
        self.fix_var.set(tr("t_fix_progress", "Corrections : {done}/{n} — {k} proposées", done=0, n=len(jobs), k=0))
        self.fix_btn.state(["disabled"])
        seq0 = self._job_seq
        self._job_seq += len(jobs)
        self._fix_thread = threading.Thread(target=self._run_fixes, args=(jobs, seq0), daemon=True)
        self._fix_thread.start()

    def _run_fixes(self, jobs, seq0):
        """Thread : calcule les propositions en parallèle (processus), résultat
        remis au fil Tk un GIF à la fois."""
        cpu = os.cpu_count() or 1
        pool = ProcessPoolExecutor(max_workers=max(1, min(12, cpu - 2, len(jobs))))
        futs = [pool.submit(autofix_one, rel, src, p[0], p[1], p[2], p[3], score,
                            os.path.join(self._work_root, f"{seq0 + i:05d}"))
                for i, (rel, src, p, score) in enumerate(jobs)]
        try:
            for fut in as_completed(futs):
                if self._fix_cancel.is_set():
                    break
                try:
                    rel, props, note = fut.result()
                except Exception as e:
                    logger.error(f"Revoir : correction impossible : {e}")
                    continue
                try:
                    self.win.after(0, self._fix_ready, rel, props, note)
                except (tk.TclError, RuntimeError):
                    break  # fenêtre fermée
        finally:
            pool.shutdown(wait=True, cancel_futures=True)
            if self._fix_cancel.is_set():
                self._cleanup_work()
            else:
                try:
                    self.win.after(0, self._fixes_finished)
                except (tk.TclError, RuntimeError):
                    pass

    def _fix_ready(self, rel, props, note):
        if self._fix_cancel.is_set():
            return  # dossier changé ou fenêtre fermée entre-temps
        if note not in (None, "nothing", "lit_background"):
            logger.error(f"Revoir : correction de {rel} : {note}")
        self.fixes[rel] = {"state": "ready" if props else "none", "props": props, "note": note}
        self._fix_counts[0] += 1
        self._fix_counts[2] += 1 if props else 0
        done, n, k = self._fix_counts
        self.fix_var.set(tr("t_fix_progress", "Corrections : {done}/{n} — {k} proposées", done=done, n=n, k=k))
        self._update_fix_cell(rel)
        if rel == self._current_rel:
            self._show_fixes(rel, dict(self.items).get(rel, {}))

    def _fixes_finished(self):
        self.fix_btn.state(["!disabled"])
        _done, n, k = self._fix_counts
        self.fix_var.set(tr("t_fix_finished", "Corrections : {k} GIF avec proposition sur {n}", k=k, n=n))
        logger.info(f"Revoir : corrections calculées, {k} GIF avec proposition sur {n}")

    def _stop_players(self):
        for p in self._players:
            p.stop()
        self._players = []

    def _show_fixes(self, rel, info):
        """Panneau sous l'aperçu : état ou propositions du GIF sélectionné."""
        self._stop_players()
        for w in self.fix_frame.winfo_children():
            w.destroy()
        if info.get("fixed"):
            ttk.Label(self.fix_frame, wraplength=512, justify=tk.LEFT, text=tr(
                "t_fix_done_detail", "Corrigé ({name}) : {before} → {score}.\nOriginal dans {dir}",
                name=self._fix_label(info["fixed"]), before=info.get("score_before", "?"), score=info["score"],
                dir=os.path.join(dq.REVIEW_DIR, dmd_autofix.BEFORE_DIR))).pack(anchor=tk.W)
            return
        f = self.fixes.get(rel)
        if not f:
            return
        if f["state"] != "ready":
            msg = {"pending": tr("t_fix_state_pending", "calcul…"),
                   "refused": tr("t_fix_refused_detail", "Propositions refusées."),
                   }.get(f["state"])
            if msg is None:
                msg = (tr("t_fix_lit_bg", "Fond plein : pas de correction automatique.")
                       if f.get("note") == "lit_background"
                       else tr("t_fix_none_found", "Aucune correction utile trouvée."))
            ttk.Label(self.fix_frame, text=msg).pack(anchor=tk.W)
            return
        for p in f["props"]:
            box = ttk.Frame(self.fix_frame)
            box.pack(fill=tk.X, anchor=tk.W, pady=(0, 8))
            ttk.Label(box, text=tr("t_fix_prop", "Proposition : {name} — {score}/100 (+{gain})",
                                   name=self._fix_label(p["code"]), score=p["score"],
                                   gain=p["score"] - info.get("score", 0))).pack(anchor=tk.W)
            cv = tk.Canvas(box, width=384, height=96, bg="black", highlightthickness=0)
            cv.pack(anchor=tk.W, pady=2)
            self._players.append(_GifPlayer(self.win, cv, p["path"], 3, self.app.led_brightness_var.get))
            ttk.Button(box, text=tr("t_fix_accept", "✓ Garder cette version"),
                       command=lambda pp=p: self.accept_fix(rel, pp)).pack(anchor=tk.W)
        ttk.Button(self.fix_frame, text=tr("t_fix_refuse", "✗ Refuser les propositions"),
                   command=lambda: self.refuse_fix(rel)).pack(anchor=tk.W)

    def _drop_props(self, rel, keep_path=None):
        for p in (self.fixes.get(rel) or {}).get("props", []):
            if p["path"] != keep_path:
                try:
                    os.remove(p["path"])  # proposition temporaire non retenue
                except OSError:
                    pass

    def accept_fix(self, rel, prop):
        """Remplace le GIF par la proposition ; l'original va dans
        _a_revoir/_avant_correction/ (jamais supprimé) ; l'index est mis à jour."""
        self._stop_players()
        self._stop_anim()
        self._frames = []
        # v98 : après validation, le GIF suivant de la liste est sélectionné
        order = [r for r, _ in self.items]
        pos = order.index(rel) if rel in order else -1
        next_rel = order[pos + 1] if 0 <= pos < len(order) - 1 else None
        try:
            before, bak = review_replace_gif(self.folder, rel, prop["path"], prop, prop["code"])
        except Exception as e:
            logger.error(f"Revoir : correction de {rel} non appliquée : {e}")
            messagebox.showerror(lang_manager.get("error", "Erreur"), str(e), parent=self.win)
            return
        self._drop_props(rel, keep_path=prop["path"])
        self.fixes[rel] = {"state": "accepted", "props": [], "note": None}
        logger.info(f"Revoir : {rel} corrigé ({prop['code']}) {before} → {prop['score']}, original : {bak}")
        self.reload()
        self._select_rel(next_rel or rel)

    def _select_rel(self, rel, tries=40):
        """Sélectionne la ligne de `rel` ; attend qu'elle soit insérée si la
        liste se remplit encore par paquets (grands dossiers)."""
        iid = self._iid.get(rel)
        if iid is not None and self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.see(iid)
        elif tries > 0 and self._fill_job:
            self.win.after(50, self._select_rel, rel, tries - 1)

    def refuse_fix(self, rel):
        self._stop_players()
        self._drop_props(rel)
        self.fixes[rel] = {"state": "refused", "props": [], "note": None}
        self._update_fix_cell(rel)
        self._show_fixes(rel, dict(self.items).get(rel, {}))

    def _cleanup_work(self):
        if self._work_root:
            shutil.rmtree(self._work_root, ignore_errors=True)  # propositions temporaires uniquement
            self._work_root = None

    # --- v97 : source affichée, édition dans MANUEL ------------------------------
    def _pick_source_root(self):
        """Demande le dossier des images source (dossier produit avant v96) et
        le mémorise dans dmd_batch.json ; None si annulé."""
        data = dmd_autofix.load_batches(self.folder)
        last = data.get("legacy_source_root", "")
        opts = {"initialdir": last} if last and os.path.isdir(last) else {}
        root_dir = filedialog.askdirectory(
            title=tr("t_fix_pick_source", "Dossier des images source de ce lot"), parent=self.win, **opts)
        if not root_dir:
            return None
        try:
            data["legacy_source_root"] = root_dir
            dmd_autofix.save_batches(self.folder, data)
        except Exception as e:
            logger.error(f"Revoir : {dmd_autofix.BATCH_FILE} non écrit : {e}")
        return root_dir

    def _source_of(self, rel, info):
        """Chemin de l'image source d'un GIF, ou None si inconnue."""
        src = info.get("src")
        if src and os.path.isfile(src):
            return src
        root_dir = dmd_autofix.load_batches(self.folder).get("legacy_source_root")
        if root_dir and os.path.isdir(root_dir):
            return dmd_autofix.find_source(root_dir, rel)
        return None

    def _show_source(self, rel, info):
        self.src_canvas.delete("all")
        self._src_photo = None
        src = self._source_of(rel, info)
        if not src:
            self.src_var.set(tr("t_review_src_unknown", "Source : inconnue"))
            return
        try:
            # sur damier gris, pas sur noir : les parties noires (invisibles
            # sur le DMD) doivent rester visibles, c'est tout l'intérêt
            img = DMDEngine.load_image(src).convert("RGBA")
            w, h = img.size
            img.thumbnail((512, 96), Image.Resampling.LANCZOS)
            board = Image.new("RGBA", img.size, (72, 72, 72, 255))
            dr = ImageDraw.Draw(board)
            for y in range(0, img.size[1], 8):
                for x in range((y // 8) % 2 * 8, img.size[0], 16):
                    dr.rectangle((x, y, x + 7, y + 7), fill=(104, 104, 104, 255))
            board.alpha_composite(img)
            img = board.convert("RGB")
            self._src_photo = ImageTk.PhotoImage(img)
            self.src_canvas.create_image(256, 48, image=self._src_photo)
            self.src_var.set(tr("t_review_src", "Source {w}×{h} — {name}", w=w, h=h, name=os.path.basename(src)))
        except Exception as e:
            self.src_var.set(tr("t_review_src_unknown", "Source : inconnue") + f" ({e})")

    def edit_manual(self):
        if self._current_rel is None:
            return
        rel = self._current_rel
        info = dict(self.items).get(rel, {})
        src = self._source_of(rel, info)
        if not src:
            if not self._pick_source_root():
                return
            src = self._source_of(rel, info)
            self._show_source(rel, info)
            if not src:
                messagebox.showwarning(lang_manager.get("warning", "Attention"),
                                       tr("t_fix_no_job", "Aucune image source retrouvée pour ces GIF."),
                                       parent=self.win)
                return
        self.app.edit_from_review(self.folder, rel, src, review=self, timing=self._timing_of(rel, info))

    def _timing_of(self, rel, info):
        """Rythme du GIF du lot (FPS d'après le délai médian, durée totale) et
        boucle du lot si enregistrée : repris par MANUEL pour que le GIF
        refait garde le même rythme que les autres (choix utilisateur v97)."""
        timing = {}
        b = info.get("b")
        batches = dmd_autofix.load_batches(self.folder).get("batches", [])
        rec = batches[b] if isinstance(b, int) and 0 <= b < len(batches) else None
        if rec is not None:
            timing["loop_mode"] = rec.get("loop_mode")
            timing["loop_count"] = rec.get("loop_count")
        try:
            with Image.open(os.path.join(self.folder, *rel.split("/"))) as im:
                delays = []
                for i in range(getattr(im, "n_frames", 1)):
                    im.seek(i)
                    delays.append(int(im.info.get("duration", 100) or 100))
            # FPS : ceux du lot (identiques pour toutes ses images) ; sinon
            # déduits du plus petit délai. Le GIF tronque les délais au 1/100 s
            # (15 i/s -> 60 ms) et fusionne les images identiques qui se
            # suivent (130, 190 ms…) : le délai seul ne suffit pas.
            if rec is not None and rec.get("batch_params", {}).get("fps"):
                fps = int(rec["batch_params"]["fps"])
            else:
                # v102 : un GIF fixe ou presque noir n'a souvent QU'UNE image
                # (images identiques fusionnées, ~2 s) : 1000/délai donnait
                # 1 i/s. Les FPS actuels d'AUTO sont retenus s'ils expliquent
                # tous les délais (multiples d'une image, à 15 ms près) ou si
                # le GIF n'a qu'une image ; sinon déduction par le plus petit
                # délai, et à défaut les FPS d'AUTO.
                try:
                    pref = int(self.app.fps_var.get())
                except (tk.TclError, ValueError):
                    pref = 10
                pref = max(1, min(60, pref))
                period = 1000.0 / pref
                fits = all(abs(x - max(1, round(x / period)) * period) <= 15 for x in delays)
                d = min(delays)
                cands = [f for f in range(1, 61) if int(1000 / f) // 10 * 10 == d]
                if len(delays) == 1 or fits or not cands:
                    fps = pref
                else:  # 60 ms = 15 ou 16 i/s, 50 ms = 17 à 20 : cadences usuelles d'abord
                    usual = [f for f in cands if f in (10, 12, 15, 20, 24, 25, 30)]
                    fps = (usual or cands)[0]
            fps = max(1, min(60, fps))
            timing["fps"] = fps
            if rec is not None and rec.get("batch_params", {}).get("duration"):
                # réglages exacts du lot : durée minimale et vitesse de défilement
                bp = rec["batch_params"]
                timing["duration"] = max(0.1, min(30.0, float(bp["duration"])))
                timing["scroll_speed"] = max(1, min(10, round(float(bp.get("scroll_speed", 1)))))
            else:
                frames = sum(max(1, round(x * fps / 1000.0)) for x in delays)
                timing["duration"] = max(0.1, min(30.0, round(frames / fps, 1)))
                timing["scroll_speed"] = max(1, min(10, round(float(self.app.scroll_speed_var.get()))))
        except Exception as e:
            logger.error(f"Revoir : rythme de {rel} illisible : {e}")
        return timing

    def after_external_replace(self, rel):
        """GIF remplacé depuis MANUEL : liste et aperçu rechargés."""
        self._drop_props(rel)
        self.fixes[rel] = {"state": "accepted", "props": [], "note": None}
        self.reload()
        iid = self._iid.get(rel)
        if iid is not None and self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.see(iid)

    def _cancel_fixes(self):
        """Arrête le calcul en cours et oublie les propositions (dossier ou
        fenêtre fermés) ; le nettoyage se fait à la fin du thread s'il tourne."""
        self._stop_players()
        self._fix_cancel.set()
        if self._fix_thread is None or not self._fix_thread.is_alive():
            self._cleanup_work()
        self.fixes = {}
        self.fix_var.set("")
        self.fix_btn.state(["!disabled"])

    def change_folder(self):
        """v94 -- revoir un autre dossier de sortie dans la même fenêtre."""
        new = filedialog.askdirectory(
            title=tr("t_review_pick_folder", "Dossier de GIF à revoir (contenant dmd_scores.json)"),
            initialdir=self.folder, parent=self.win,
        )
        if not new:
            return
        if not dq.load_index(new):
            messagebox.showwarning(
                lang_manager.get("warning", "Attention"),
                tr("t_review_no_index",
                   "Aucun score dans ce dossier ({name}).\n"
                   "Traitez d'abord des images par lot vers ce dossier.", name=dq.INDEX_NAME),
                parent=self.win,
            )
            return
        self._stop_anim()
        self._cancel_fixes()  # v96 : propositions propres à l'ancien dossier
        for w in self.fix_frame.winfo_children():
            w.destroy()
        self._current_rel = None
        self.edit_btn.state(["disabled"])
        self.src_canvas.delete("all")
        self.src_var.set("")
        self._frames = []
        self.canvas.delete("all")
        self.detail_var.set("")
        self.folder = str(new)
        config_manager.set("last_review_folder", self.folder)
        self.win.title(tr("t_review_title", "Revoir les GIF — {folder}", folder=self.folder))
        self.reload()

    def open_folder(self):
        try:
            os.startfile(self.folder)  # type: ignore[attr-defined]
        except Exception as e:
            logger.error(f"Impossible d'ouvrir le dossier : {e}")

    def close(self):
        self._stop_anim()
        self._cancel_fixes()  # v96 : propositions non acceptées = fichiers temporaires effacés
        if self._fill_job:
            self.win.after_cancel(self._fill_job)
        self.win.destroy()


class _GifPlayer:
    """v96 -- aperçu LED animé d'un GIF dans un canvas (propositions de
    correction de la fenêtre Revoir). Images chargées en mémoire : le
    fichier n'est pas verrouillé et peut être déplacé pendant la lecture."""

    def __init__(self, win, canvas, path, scale, brightness_fn):
        self.win, self.canvas, self.scale, self.brightness_fn = win, canvas, scale, brightness_fn
        self.frames, self.delays, self.idx, self.job, self.photo = [], [], 0, None, None
        try:
            with Image.open(path) as im:
                for i in range(getattr(im, "n_frames", 1)):
                    im.seek(i)
                    self.frames.append(im.convert("RGB"))
                    self.delays.append(int(im.info.get("duration", 100) or 100))
        except Exception as e:
            logger.error(f"Aperçu de proposition illisible ({path}) : {e}")
        self._tick()

    def _tick(self):
        if not self.frames:
            return
        img = DMDEngine.render_led_style(self.frames[self.idx], scale=self.scale, led_ratio=0.525, glow=True,
                                         brightness=self.brightness_fn())
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(64 * self.scale, 16 * self.scale, image=self.photo)
        delay = self.delays[self.idx]
        self.idx = (self.idx + 1) % len(self.frames)
        if len(self.frames) > 1:
            self.job = self.win.after(delay, self._tick)

    def stop(self):
        if self.job:
            try:
                self.win.after_cancel(self.job)
            except tk.TclError:
                pass
            self.job = None
        self.frames = []


def process_one_image(
    image_path,
    batch_params,
    locked_settings,
    cached_settings,
    output_dir_str,
    input_dir_str,
    add_anim_to_name,
    color_count_fallback,
    loop_mode,
    loop_count,
):
    """Traite UNE image (résolution réglages + rendu + export GIF) — fonction
    module-level PICKLABLE, aucune dépendance à self/Tk, unité de travail d'un
    worker ProcessPoolExecutor (2026-08-06, Tier 2 plan perf batch). Reproduit
    EXACTEMENT le corps de la boucle de process_images() (chemin séquentiel),
    en réutilisant les mêmes fonctions pures déjà extraites (Tier 2a) :
    resolve_image_settings/render_dmd_frame (dmd_pipeline_quality) +
    export_frames_to_gif (dmd_gif_exporter) — aucune logique dupliquée/
    réécrite, seulement les entrées explicites au lieu de self.*_var.get().

    Toutes les valeurs qui dépendraient normalement de self (tk.Variable,
    self.image_settings, self.locked_proposal/self.proposals) sont reçues
    déjà figées par l'appelant (process_images(), AVANT dispatch) — un worker
    ne peut de toute façon pas lire une instance Tkinter à travers une
    frontière de process (non picklable).

    Ne fait JAMAIS de popup/accès UI (impossible depuis un process enfant) :
    retourne (image_path, success, error_or_None, output_name_or_None,
    nb_frames, color_count, quality) — c'est PROCESS_IMAGES (thread
    consommateur) qui décide de la mise à jour de progression/du résumé final.
    quality (v87) : (chemin relatif posix du GIF, dmd_quality.to_dict()) ou None."""
    try:
        settings = _resolve_image_settings(
            image_path, batch_params, locked_settings=locked_settings, cached_settings=cached_settings
        )
        cleanup_power = settings.get("cleanup_power", 1.0)
        pixel_perfect = bool(settings.get("_pixel_perfect", False))

        frames, fps, actual_direction, img_source = _render_dmd_frame(
            image_path,
            settings,
            return_frames=True,
            cleanup_power=cleanup_power,
            pixel_perfect=pixel_perfect,
            return_direction=True,
            return_source=True,
        )

        if isinstance(frames, Image.Image):
            frames = [frames]
        elif not isinstance(frames, list):
            frames = [Image.new("RGB", (128, 32), (0, 0, 0))]

        stem = Path(image_path).stem
        output_name = f"{stem}_{actual_direction}.gif" if add_anim_to_name else f"{stem}.gif"
        img_path_obj = Path(image_path)
        input_dir = Path(input_dir_str)
        try:
            relative_path = img_path_obj.parent.relative_to(input_dir)
        except ValueError:
            relative_path = Path(".")
        output_subdir = Path(output_dir_str) / relative_path
        output_subdir.mkdir(parents=True, exist_ok=True)
        output_path = output_subdir / output_name

        source_palette = DMDEngine.detect_palette(img_source, max_colors=256)
        if len(source_palette) <= 8:
            color_count = 8
        elif len(source_palette) <= 16:
            color_count = 16
        else:
            color_count = color_count_fallback

        export_frames_to_gif(
            frames,
            output_path,
            fps=fps,
            color_count=color_count,
            loop_mode=loop_mode,
            loop_count=loop_count,
            disposal=2,
            optimize=False,
            # v84 -- une palette pour toute l'animation (frames issues de la
            # meme image source) : encodage ~x19 plus rapide, voir
            # dmd_gif_exporter.py v3
            shared_palette=True,
        )
        # v87 -- score qualité calculé ici (images déjà en mémoire, <= 10
        # échantillonnées) ; l'index est écrit par process_images, jamais ici
        quality = None
        try:
            q = dq.evaluate_frames(frames, int(1000 / fps))
            # v96 : source gardée dans l'index (corrections proposées par Revoir)
            quality = ((relative_path / output_name).as_posix(), dict(q.to_dict(), src=str(image_path)))
        except Exception:
            pass  # le score n'est qu'une aide : jamais bloquant pour l'export
        return (image_path, True, None, output_name, len(frames), color_count, quality)
    except Exception as e:
        return (image_path, False, str(e), None, 0, 0, None)


def autofix_one(rel, src, batch_params, color_count_fallback, loop_mode, loop_count, base_score, work_dir):
    """v96 -- propositions de correction pour UN GIF faible (fenêtre Revoir),
    PICKLABLE comme process_one_image (worker ProcessPoolExecutor). Chaque
    variante de la source (dmd_autofix.build_variants) est écrite dans
    `work_dir` puis passe par process_one_image avec les réglages du lot
    d'origine : même rendu, même export, même note que le lot. La source
    n'est jamais modifiée. Retourne (rel, propositions, note) ; une
    proposition = {"code", "path" (GIF dans work_dir), score, rating, color,
    reasons} ; note = None, "lit_background", "nothing" ou le message d'erreur."""
    try:
        img = DMDEngine.load_image(src)
        if dmd_autofix.has_lit_background(img):
            return rel, [], "lit_background"
        variants = dmd_autofix.build_variants(img)
        if not variants:
            return rel, [], "nothing"
        os.makedirs(work_dir, exist_ok=True)
        out_dir = os.path.join(work_dir, "gif")
        scored, made = {}, {}
        for code, v in variants.items():
            png = os.path.join(work_dir, code.replace("+", "__") + ".png")
            v.save(png)
            r = process_one_image(png, batch_params, None, None, out_dir, work_dir, False,
                                  color_count_fallback, loop_mode, loop_count)
            os.remove(png)
            if r[1] and r[6] is not None:
                q = {k: val for k, val in r[6][1].items() if k != "src"}
                scored[code] = q["score"]
                made[code] = (os.path.join(out_dir, r[3]), q)
        keep = dmd_autofix.choose(base_score, scored)
        props = []
        for code, (path, q) in made.items():
            if code in keep:
                props.append(dict(q, code=code, path=path))
            else:
                try:
                    os.remove(path)  # variante non retenue (fichier temporaire)
                except OSError:
                    pass
        props.sort(key=lambda p: keep.index(p["code"]))
        return rel, props, (None if props else "nothing")
    except Exception as e:
        return rel, [], str(e)


DMDConverter.hash_image = _pipeline_hash_image
DMDConverter.evaluate_quality = _pipeline_evaluate_quality
DMDConverter.score_variant = _pipeline_score_variant
DMDConverter.analyze_characteristics = _pipeline_analyze_characteristics
DMDConverter.resize_will_shrink_text_too_much = _pipeline_resize_will_shrink_text_too_much
DMDConverter.render_dmd_frame = _pipeline_render_dmd_frame
# Alias posé ici (2026-08-06, Tier 2 plan perf batch) : voir commentaire dans
# le corps de la classe, juste avant _optimize_cleanup_and_pixel_perfect.
DMDConverter._TONAL_REFINEMENT_PARAMS = _TONAL_REFINEMENT_PARAMS


# --- Pipeline délégation texte (PIL-only) ---
try:
    from .dmd_pipeline_text import render_text_image as _render_text_image
except ImportError:
    from dmd_pipeline_text import render_text_image as _render_text_image


def _pipeline_render_text_image(self):
    text = self.text_input.get(1.0, tk.END).strip()
    if not text or text == "Votre texte ici...":
        return None

    font = self.get_text_font()
    effect = self.text_effect.get()
    color_effect = self.text_color_effect.get()

    return _render_text_image(
        text=text,
        font=font,
        effect=effect,
        color_effect=color_effect,
        text_color=self.text_color,
        text_bg_color=self.text_bg_color,
    )


DMDConverter.render_text_image = _pipeline_render_text_image


if __name__ == "__main__":
    try:
        app = DMDConverter()
        app.run()
    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        print(f"ERREUR FATALE: {e}")
        traceback.print_exc()
        logger.error(f"ERREUR FATALE: {e}")
        try:
            config_manager.user_dir.mkdir(parents=True, exist_ok=True)
            crash_file = (
                config_manager.user_dir
                / f"crash_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )
            crash_file.write_text(error_details, encoding="utf-8")
            print(f"Log de crash enregistré: {crash_file}")
        except Exception:
            pass
