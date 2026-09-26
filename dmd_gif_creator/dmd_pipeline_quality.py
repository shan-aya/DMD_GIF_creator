# ============================================
# safe-modify — Historique des modifications
# ============================================
# Version actuelle : v27
#
# v27 — 2026-09-26 — safe-modify — Profils (décision utilisateur : moteur
#      générique sans limitation, profil « Logos Recalbox » pour les logos) :
#      options pilotées par batch_params, neutres par défaut —
#      fill_min_ratio (absent/None/0 = pas de règle de forme, choix au score),
#      invert_dark (True par défaut, décision utilisateur : actif aussi en
#      générique), max_scroll_cycle_s (plafond d'aller-retour, absent = aucun).
#      apply_render_profile() recopie le plafond dans les réglages retournés,
#      y compris ceux venus de l'aperçu (cache/verrou).
#
# v26 — 2026-09-25 — safe-modify — Logos sombres monochromes (demande
#      utilisateur après analyse du "gamma" de red77290) : les 315 GIF
#      entièrement noirs du pack F:\systems venaient TOUS de logos noirs sur
#      fond transparent (luminance visible médiane 0 : le gamma n'y peut rien).
#      is_dark_monochrome (luminance moyenne visible < 40, saturation < 60,
#      transparence requise) -> maybe_invert_dark : réglages résolus aussi sur
#      la source inversée (invert_visible), rendus complets comparés au score
#      dmd_quality, inversion retenue seulement si >= +3 points (les logos
#      sombres à contours/texte clairs restent intacts : leur score baisse une
#      fois inversés). Marqueur settings["invert_dark"] appliqué par
#      render_dmd_frame. resolve_image_settings : cœur extrait tel quel dans
#      _resolve_from_image. Le gamma de red77290 n'a rien apporté sur les
#      logos (32 logos sombres : 93,6 -> 93,9, 6 mieux / 6 moins bien).
#
# v25 — 2026-09-25 — safe-modify — Règle de forme (demande utilisateur : "je
#      préfère un logo détaillé qui scroll qu'un logo fixe non reconnaissable",
#      "je ne veux aucun rognage") : `shape_forces_fill` + constante
#      FILL_MIN_RATIO_DEFAULT (2.0). resolve_image_settings impose Fill si la
#      source recadrée est au moins 2 fois plus large que haute (réglable,
#      batch_params["fill_min_ratio"]) ; en dessous, choix au score inchangé.
#      Le lot n'avait jamais eu le garde-fou lettres de l'aperçu : les deux
#      suivent maintenant la même règle. resize_will_shrink_text_too_much est
#      conservée mais n'est plus appelée (voir docstring de shape_forces_fill).
#
# v24 — 2026-09-25 — safe-modify — resolve_image_settings (lot) : source
#      recadrée (crop_to_visible_content) AVANT de prendre sa taille, comme
#      l'aperçu. Bug présent depuis le 1er commit : le sens de défilement Fill
#      (horizontal si > 4:1) était calculé sur l'image NON recadrée alors que le
#      rendu, lui, recadre -- un logo à marges transparentes pouvait défiler
#      dans le mauvais sens en lot (3 006 sources sur 54 776 du pack F:\systems).
#
# v23 — 2026-08-06 — safe-modify — Plan perf batch (Tier 2a, préparation de la
#      parallélisation ACROSS images) : `generate_settings_variants`/
#      `best_variant`/`optimize_cleanup_and_pixel_perfect`/
#      `resolve_image_settings` — versions PURES (sans self/tk.Variable) des
#      méthodes DMDConverter homonymes (préfixées `_` côté classe),
#      déplacées ici pour être appelables depuis un worker
#      ProcessPoolExecutor (une instance Tkinter n'est pas picklable à
#      travers une frontière de process). Algorithme déplacé TEL QUEL, pas
#      réécrit — DMDConverter garde des méthodes du même nom qui ne font
#      plus que lire les tk.Variable puis déléguer ici, même pattern déjà en
#      place pour score_variant/render_dmd_frame. `TONAL_REFINEMENT_PARAMS`/
#      `CONTRAST_MULTS`/`BLACK_THRESHOLDS` (constantes) déplacées en
#      parallèle (étaient un attribut/valeurs codées en dur côté classe).
#      Vérifié réellement (pas supposé) : settings + hash SHA256 du GIF
#      exporté strictement identiques entre l'ancien code (commit ab29db0,
#      Tier 1) et ce refactor, sur 3 images synthétiques (comparaison A/B
#      directe des 2 versions du code, pas juste une relecture).
#
# v22 — 2026-08-06 — safe-modify — Plan perf batch (Tier 1, suite immédiate du
#      Tier 0 v21) : `render_dmd_frame()` gagne un paramètre optionnel
#      `return_source` (False par défaut = comportement inchangé) qui renvoie
#      AUSSI l'image source déjà chargée (`raw_source`, NON recadrée -- même
#      version que renvoyait l'ancien 3e chargement de process_images) en
#      dernière position du tuple. Évite un 3e `DMDEngine.load_image()`
#      redondant du même fichier par image traitée dans le batch (déjà
#      chargé 2 fois : get_settings_for_image + ce rendu). Renvoie
#      délibérément la version brute plutôt que `img_orig` (recadrée) pour
#      reproduire EXACTEMENT l'ancien comportement de `detect_palette`, pas
#      une version jugée équivalente.
#
# v21 — 2026-08-06 — safe-modify — Plan perf batch (Tier 0, "multithread ? ou
#      autre solution ?") : nouveau paramètre optionnel `resize_cache` (dict,
#      None par défaut = comportement inchangé) sur `score_variant()`. Constat :
#      get_settings_for_image() fait ~42 appels à score_variant pour UNE image
#      (grille fit/fill 3×4 + balayage cleanup + descente tonale), et chaque
#      appel refaisait `optimize_for_dmd` (chaîne PIL.ImageEnhance) +
#      `adaptive_resize` (LANCZOS) à pleine résolution même quand la
#      combinaison (brightness/contrast/saturation/black_threshold/
#      resize_mode/direction/pixel_perfect) était identique à un appel déjà
#      fait (fit et fill partagent la même grille tonale, le balayage cleanup
#      garde le même tonal, etc.) — ~42 passages pour ~21-25 combinaisons
#      réellement distinctes. Cache scopé à UNE SEULE image (créé/jeté par
#      l'appelant, jamais partagé entre images) : `tonal_key` pour le couple
#      (optimized, resized), `raw_key` séparé (arité différente, resize_mode/
#      direction/pixel_perfect seulement) pour `raw_resized` du chemin
#      fidélité tonale. Rétrocompatible : appel sans `resize_cache` = calcul
#      systématique comme avant, zéro changement de comportement.
#
# v20 — 2026-07-20 — safe-modify — Support du format d'entrée .raw565 (voir
#      dmd_engine.py v17 pour le détail complet du décodage) : `render_dmd_frame`
#      utilise désormais `DMDEngine.load_image(image_path)` au lieu de
#      `Image.open(image_path)` — sans ce changement, une image .raw565
#      ajoutée à la liste (chargement/aperçu/infos OK grâce à
#      dmd_converter.py v77) aurait planté avec `PIL.UnidentifiedImageError`
#      dès la génération réelle du rendu DMD (ce point d'entrée précis),
#      seul endroit de ce fichier qui ouvre une image depuis un chemin
#      utilisateur.
#
# v19 — 2026-07-18 — safe-modify — `score_variant` : nouveau paramètre optionnel
#      `fidelity_weight` (défaut 0.0, comportement inchangé pour tous les
#      appelants existants) + nouvelle fonction `_tonal_fidelity_score`. Suite à
#      un constat de l'utilisateur : après les fixes précédents (v13-v18), la
#      proposition 3 "Optimisé" du mode Auto/IA a `cleanup_power=0.0` le plus
#      souvent et hérite des MÊMES contraste/saturation/seuil noir que la
#      proposition 1 ou 2 retenue comme base — elle n'apporte plus grand-chose
#      de distinct. Analyse (voir plan de session) : `_optimize_cleanup_and_
#      pixel_perfect` (dmd_converter.py) ne balaie QUE cleanup_power/
#      pixel_perfect, jamais contraste/saturation/luminosité — mais surtout,
#      même en les balayant, le score ne l'aurait pas vu : vérifié empiriquement
#      que `legibility_score` reste EXACTEMENT 1.0 quel que soit le contraste/
#      saturation/luminosité/seuil noir testé (à cleanup_power=0), car depuis le
#      fix v16, candidat et référence de lisibilité sont tous deux dérivés de
#      `optimized` — littéralement la même image quand cleanup_power=0. Aucune
#      dimension du score ne mesurait la fidélité tonale à l'original. Ajout
#      d'une 3e dimension mesurable : `_tonal_fidelity_score` compare, sur le
#      masque de pixels actifs du candidat, la luminosité moyenne/le contraste
#      (std luma)/la saturation moyenne entre le rendu candidat et une NOUVELLE
#      référence "brute" (dérivée de `img`, AVANT `optimize_for_dmd` —
#      différente de `optimized`, utilisée pour la référence de lisibilité).
#      Activée uniquement quand `fidelity_weight>0` (poids nominal
#      `w_fidelity=1.5`, < `w_legibility=3.0` pour que la lisibilité reste
#      prioritaire en cas de conflit). Score final NORMALISÉ sur l'échelle
#      historique 0-4.0 (division par la somme des poids actifs × 4.0) même
#      quand la fidélité contribue — sinon un score "plus élevé" viendrait
#      juste d'une échelle plus large (0-5.5) et ne serait plus comparable au
#      score des propositions 1/2, qui restent en 0-4.0. Seul
#      `_optimize_cleanup_and_pixel_perfect` (dmd_converter.py v42) l'active,
#      décision explicite de
#      l'utilisateur pour que les propositions 1/2 restent des baselines
#      simples/prévisibles (voir mémoire, point 33/34).
#
# v18 — 2026-07-18 — safe-modify — `score_variant` et `render_dmd_frame` passent
#      désormais `direction=settings.get("direction")` à `DMDEngine.adaptive_resize`
#      — voir dmd_engine.py v15 pour le détail du bug corrigé (recadrage silencieux
#      du contenu sur les bords en mode "Mode DMD / Force pixel-perfect" + Fill,
#      signalé sur "1stDivisionManager(Europe).png"). Un seul paramètre ajouté par
#      appel, aucun autre changement — `adaptive_resize` gère la rétrocompatibilité
#      si `direction` est absent des settings.
#
# v17 — 2026-07-18 — safe-modify — `render_dmd_frame` et `score_variant`
#      appliquent désormais `DMDEngine.crop_to_visible_content` (dmd_engine.py
#      v14) à l'image source avant tout calcul d'échelle fit/fill. Suite à un
#      signalement utilisateur sur "4th&Inches(Europe).png" (marges transparentes
#      de 46px en haut/bas sur une image de 175px de haut, jamais recadrées) —
#      voir le changelog v14 de dmd_engine.py pour le détail du bug (Resize trop
#      petit ET Fill scrollant inutilement du vide). Un seul appel par fonction,
#      au point d'entrée (juste après `Image.open` dans `render_dmd_frame`, sur
#      `original_img` avant `ensure_rgb_on_black` dans `score_variant` — le crop a
#      besoin du canal alpha, donc DOIT précéder la conversion RGB qui le perd).
#      Couvre ainsi tout le flux Auto/IA (aperçu principal, export GIF simple et
#      par lot, vignettes de score, propositions artistiques — tous passent par
#      l'une de ces 2 fonctions) sans dupliquer la logique de crop à chaque appelant.
#
# v16 — 2026-07-18 — safe-modify — score_variant : la référence de lisibilité
#      (`ref_resized`) était construite depuis l'image BRUTE non rehaussée (`img`),
#      alors que le candidat passe par `optimize_for_dmd` (contraste ×1.5,
#      saturation ×1.3, sharpness ×1.2 par défaut) avant scoring. Le candidat avait
#      donc structurellement plus de contours que la référence même SANS aucun
#      cleanup_power, ce qui déclenchait une pénalité de lisibilité injustifiée
#      (`legibility_score = min(ratio, 1/ratio)` avec ratio > 1). Appliquer
#      cleanup_power (flou) réduisait ce contraste artificiel et faisait REMONTER
#      le score — le nettoyage était donc récompensé pour compenser un biais de
#      mesure, pas parce que l'image était réellement améliorée. Cause racine
#      identifiée suite à un signalement utilisateur : le nettoyage dégradait
#      visiblement les images tout en augmentant parfois leur score. Fix : la
#      référence réutilise maintenant `optimized` (déjà calculé pour le candidat)
#      au lieu de `img` — isole l'effet du cleanup_power post-resize spécifiquement,
#      sans mélanger l'effet du rehaussement de base. Voir aussi dmd_engine.py v13
#      (redesign de cleanup_dmd_frame, second volet du même correctif). La formule
#      symétrique min(ratio, 1/ratio) elle-même (fix v9/v10, motivé par le logo
#      "4th & Inches" trop texturé) N'EST PAS modifiée par ce correctif.
#
# v15 — 2026-07-18 — safe-modify — `render_dmd_frame` : bug réel signalé par
#      l'utilisateur — les vignettes des propositions 1/2 (Resize/Fill) avaient un
#      rendu "baveux"/avec artefacts (cleanup_power=0.6) alors que l'Aperçu DMD
#      Principal ET le GIF exporté, pour la MÊME proposition sélectionnée,
#      s'affichaient nets — incohérence entre la vignette et le rendu réel.
#      Root-causé : aux 2 appels internes à `DMDEngine.create_animation_frames`
#      (lignes ~733/747), le nettoyage était gardé par
#      `cleanup and settings.get("resize_mode") == "auto"` — condition TOUJOURS
#      FAUSSE pour tout settings produit par l'onglet Auto/IA
#      (`generate_settings_variants` ne met jamais `resize_mode` à `"auto"`, cette
#      valeur n'existe que côté `direction` pour le mode fit — confusion probable
#      entre les 2 champs à l'origine du bug). Résultat : `cleanup_dmd_frame`
#      n'était JAMAIS exécuté dans l'aperçu principal ni dans l'export GIF final,
#      quel que soit `cleanup_power`, alors que `score_variant` (qui rend les
#      vignettes) l'applique correctement sans cette garde
#      (`cleanup=(cleanup_power > 0)`, déjà correct). Fix : les 2 gardes remplacées
#      par `cleanup and cleanup_power > 0`, identique à `score_variant` — aperçu et
#      export appliquent désormais réellement le nettoyage demandé, cohérent avec
#      la vignette. Voir aussi dmd_converter.py (même session) :
#      `generate_settings_variants` ne fixait cleanup_power qu'à une valeur non
#      testée (0.6) pour les propositions 1/2 — remis à 0.0 en même temps, sans
#      quoi ce fix aurait rendu l'aperçu ET l'export "baveux" pour ces 2
#      propositions au lieu de corriger seulement l'incohérence.
# v14 — 2026-07-17 — safe-modify — Remplacement complet de detect_text_likelihood/
#      text_legibility_collapsed (composantes connexes sur seuil de luminance) par
#      resize_will_shrink_text_too_much (hauteur de lettre projetée après resize).
#      Après un long désaccord argumenté de l'utilisateur ("Resize lisible mais
#      forcé vers Fill" sur plusieurs vrais logos), 8 approches ont été testées sur
#      un corpus de 7 logos réels variés sans jamais généraliser correctement :
#      composantes connexes (luminance), + seuil min_components, OCR Tesseract
#      (installé pour l'occasion — échec total, même sur l'original en pleine
#      résolution), OCR sur rendu LED (pire), composantes connexes (couleur),
#      idem à échelle uniformisée, corrélation de forme original/candidat (6/7
#      mais rate le cas clé), corrélation + bruit chromatique interne (n'améliore
#      pas). L'utilisateur a proposé le bon angle : la variable physique qui
#      compte n'est pas "y a-t-il du texte reconnu" mais "combien de pixels
#      chaque lettre occupera-t-elle après réduction" — hauteur médiane des
#      lettres dans l'original (binarisation par distance de COULEUR, pas
#      luminance seule — voir _binarize_by_color_distance) × facteur d'échelle du
#      resize fit, comparé à un seuil de ~8px. Résultat : séparation PARFAITE sur
#      les 7 cas de test, y compris les 2 cas où toutes les tentatives
#      précédentes échouaient (logos où le texte fusionne déjà dans l'original —
#      hauteur médiane à 0, correctement classé "illisible").
# v13 — 2026-07-17 — safe-modify — `_binarize_for_components` avait le MÊME bug de
#      transparence corrigé en v11 dans `score_variant`/`evaluate_quality`
#      (`img.convert("RGB")` retire l'alpha SANS compositer sur fond noir), mais
#      celui-ci n'avait pas été traité — trouvé en recalibrant l'heuristique de
#      détection de texte sur un lot de logos réels (résultats incohérents d'un
#      script de test à l'autre selon qu'une conversion RGB était faite en amont ou
#      non). Toute l'analyse de composantes connexes sur des images RGBA
#      transparentes (la majorité des "clear logos") était donc faussée depuis le
#      début. Remplacé par `DMDEngine.ensure_rgb_on_black(img)`.
# v12 — 2026-07-17 — safe-modify — text_legibility_collapsed : faux positif signalé
#      par l'utilisateur sur le logo "A.G.E." (3 lettres A/G/E dans un triangle) — le
#      rendu Resize/fit y est parfaitement lisible d'après l'utilisateur, mais
#      l'override forçait quand même Fill. Cause : un logo compact à peu de
#      caractères, une fois binarisé, voit ses lettres fusionner avec le CONTOUR
#      englobant (le triangle) en une seule composante connexe dès le resize — signal
#      normal et attendu pour ce type de contenu, pas une preuve de perte de
#      lisibilité (contrairement à du texte libre sans cadre comme "4th & Inches",
#      où la fusion totale de 8 composantes en 1 reflète une vraie dégradation).
#      Nouveau paramètre min_orig_components (défaut 6) : l'override ne se déclenche
#      que si l'original contient au moins ce nombre de composantes "de taille
#      lettre" — sous ce seuil (logos courts/badges), le score classique (déjà
#      corrigé, v10) tranche normalement. A.G.E. (4 composantes) passe sous le
#      seuil, 4th&Inches (8) le dépasse toujours.
# v11 — 2026-07-17 — safe-modify — Bug réel signalé par l'utilisateur (logo "A.G.E."
#      doré, fond RGBA transparent) : les vignettes Propositions IA montraient un fond
#      BLANC/coloré diffus alors que l'aperçu principal (render_dmd_frame) et l'image
#      source affichaient un fond noir correct. Cause : `score_variant`/
#      `evaluate_quality` appelaient `original_img.convert("RGB")` AVANT
#      `optimize_for_dmd` — `.convert("RGB")` sur une image RGBA ne fait que retirer le
#      canal alpha SANS compositer sur un fond, gardant les pixels RVB bruts "sous" la
#      transparence (souvent blancs, pratique courante des éditeurs d'images) — cette
#      couleur fantôme se propage ensuite dans tout le pipeline (contraste/saturation/
#      resize), le seuil noir ne rattrapant que les pixels sombres, pas ces couleurs
#      claires révélées. `render_dmd_frame` (aperçu principal + export final) n'a pas ce
#      bug : il appelle `optimize_for_dmd` directement sur l'image RGBA d'origine, dont
#      l'appel interne à `ensure_rgb_on_black` compose correctement la transparence sur
#      noir. Remplacé `original_img.convert("RGB")` par
#      `DMDEngine.ensure_rgb_on_black(original_img)` aux 3 occurrences concernées
#      (`evaluate_quality` legacy ×2, `score_variant`) pour aligner le comportement sur
#      celui du pipeline de rendu final.
# v10 — 2026-07-17 — safe-modify — Suite à un désaccord argumenté de l'utilisateur sur
#      l'analyse précédente (logo "4th & Inches" toujours peu lisible même après le fix
#      v9) : 2 changements demandés explicitement.
#      1. legibility_score dans score_variant : la formule min(1.0, edge_cand/edge_ref)
#         plafonnait le ratio à 1.0 mais ne pénalisait jamais un candidat PLUS bruité
#         que la référence (edge_cand très supérieur à edge_ref = souvent du bruit de
#         quantification/contraste, pas du texte plus net). Remplacée par une formule
#         symétrique min(ratio, 1/ratio) qui pénalise l'écart dans les deux sens.
#      2. Nouvelle détection heuristique "présence de texte" SANS OCR (ni pytesseract
#         ni le binaire Tesseract ne sont installés dans cet environnement — ajouter
#         Tesseract aurait été une dépendance système plus lourde que ce que le projet
#         a accepté jusqu'ici) : compte les composantes connexes "de taille lettre" de
#         l'image source (detect_text_likelihood) vs du rendu Resize/fit
#         (text_legibility_collapsed) — si le nombre de lettres distinctes s'effondre
#         en Resize (fusion des traits), le mode Fill/scroll est mathématiquement
#         toujours au moins aussi lisible (facteur d'échelle fill >= facteur fit par
#         construction, voir adaptive_resize) et doit donc être préféré, quel que soit
#         le score brut. Si l'image source ne ressemble pas à du texte (peu ou pas de
#         composantes de taille lettre), le comportement reste basé sur le score
#         classique (avec le fix symétrique du point 1). Réutilise le principe de
#         diffusion vectorisée déjà présent dans flood_fill (dmd_converter.py) pour le
#         labelling de composantes connexes, sans dépendance à scipy.
# v9 — 2026-07-17 — safe-modify — score_variant : passe sample_mid_scroll=True aux 2
#      appels create_animation_frames (candidat + référence, voir dmd_engine.py v6).
#      Bug réel signalé par l'utilisateur sur une image logo large (mode fill/scroll) :
#      max_frames=1 renvoyait la frame à offset=0, qui pour un scroll ne montre que les
#      128 premiers pixels de gauche de l'image redimensionnée (souvent bien plus
#      large en fill) — le score de lisibilité et la miniature affichée ne portaient
#      donc que sur un fragment tronqué du logo, pas sur son ensemble, faussant la
#      comparaison face au mode "Resize" (non tronqué car il tient déjà dans 128px).
#      Avec le milieu du scroll échantillonné à la place, candidat ET référence sont
#      jugés sur une portion représentative comparable. Performance inchangée (toujours
#      O(1), voir dmd_engine.py v6).
# v8 — 2026-07-17 — safe-modify — render_dmd_frame : la branche _artistic_effect
#      rend maintenant l'animation de base normalement (create_animation_frames,
#      respecte resize_mode/direction/scroll/pixel-perfect de la proposition retenue)
#      PUIS superpose l'effet artistique via ManualEffects.apply_over_frames, au lieu
#      de forcer resize_mode="fit" et de remplacer entièrement l'animation par
#      l'effet seul sur une image statique (comportement v6, changé à la demande de
#      l'utilisateur : "ajouter leur effet à ceux existants (scrolling,
#      pixel-perfect...)"). L'effet peut avoir sa propre durée/fps
#      (settings["_artistic_duration"]/["_artistic_fps"], optionnels) indépendants
#      des paramètres globaux, pour permettre un cycle d'effet différent de celui du
#      scroll de base.
# v7 — 2026-07-17 — safe-modify — score_variant : passe max_frames=1 aux 2 appels
#      create_animation_frames (candidat + référence). Bug de performance majeur
#      découvert lors de l'analyse de lenteur du mode Auto/IA (7-15s par analyse,
#      jusqu'à ~300ms/variante en mode fill contre ~5ms en mode fit) : seul frames[0]
#      est utilisé, mais toute l'animation de scroll aller-retour (parfois 100+
#      frames) était générée à chaque appel. Score/canvas strictement inchangés
#      (frames[0] identique avec ou sans max_frames), juste beaucoup plus rapide.
# v6 — 2026-07-16 — safe-modify — Propositions artistiques (mode Auto/IA) : ajout de
#      analyze_characteristics (occupation/densité de contours/coloration, sert à
#      choisir des effets adaptés au contenu) et d'une branche dans render_dmd_frame
#      qui délègue à ManualEffects.<effet>(...) au lieu de
#      DMDEngine.create_animation_frames quand settings["_artistic_effect"] est
#      présent — point d'intégration unique, donc preview/export/batch en
#      bénéficient automatiquement sans dupliquer la logique de rendu.
# v5 — 2026-07-16 — safe-modify — Ajout de score_variant : nouveau scoring pour le
#      flux Auto/IA, à la demande de l'utilisateur suite à une refonte du mode Auto.
#      evaluate_quality combinait de nombreux termes (fidélité pixel, contraste local,
#      pénalité blancs...) qui faisaient dériver le score et biaisaient
#      systématiquement le classement en faveur du mode "resize"/fit. score_variant ne
#      retient QUE les 2 critères demandés par l'utilisateur : occupation de
#      l'affichage (part de pixels actifs, cible 10-30%) et lisibilité (contours actifs
#      conservés par rapport à une référence non "optimisée"). PLUS HAUT = MEILLEUR
#      (contrairement à evaluate_quality où plus bas = meilleur). evaluate_quality
#      reste inchangée (aucun appelant ne la retire pour l'instant).
# v4 — 2026-07-15 — safe-modify — evaluate_quality : suppression du code mort
#      `dmd_sample` — un échantillonnage de jusqu'à 4 frames était calculé
#      (idxs = [0, len//3, 2*len//3, len-1]) mais seul `dmd_sample[0]` était utilisé
#      ensuite, et `dmd_sample[0]` vaut toujours `dmd_frames[0]` (idxs[0] == 0 est
#      toujours retenu en premier). Remplacé par un accès direct à `dmd_frames[0]`.
#      Comportement/score strictement inchangé (le code mort ne changeait rien au
#      calcul), juste plus lisible. La régénération complète de `dmd_frames`/
#      `ref_frames` (candidat + référence) reste nécessaire pour comparer les deux
#      pipelines de rendu — non modifiée, voir TODO_optimisation.md pour le détail du
#      compromis risque/gain.
# v3 — 2026-07-15 — safe-modify — Factorisation du noyau de convolution Sobel, dupliqué
#      quasi à l'identique entre les fonctions imbriquées sobel_mag et
#      active_edge_strength (evaluate_quality), dans une fonction module-level
#      _sobel_magnitude réutilisée par les deux. Comportement numérique inchangé.
# v2 — 2026-07-15 — safe-modify — render_dmd_frame : ajout du paramètre optionnel
#      return_direction (défaut False, rétrocompatible) pour exposer la direction déjà
#      calculée en interne (auparavant jetée via _direction) et éviter que l'appelant
#      n'ait à la recalculer en rouvrant/re-traitant l'image (voir dmd_converter.py
#      process_images, qui recalculait la direction sur l'image BRUTE non redimensionnée,
#      ce qui pouvait donner une direction incorrecte en mode "auto").
# v1 — 2026-07-15 — safe-modify — Version de base (backup original conservé dans
#      _backups/dmd_pipeline_quality_2026-07-15_19-38-42.bak)
# ============================================

import hashlib
import statistics
from typing import List, Tuple

import numpy as np
from PIL import Image

try:
    from .dmd_engine import DMDEngine
except ImportError:
    from dmd_engine import DMDEngine

try:
    from .dmd_manual_effects import ManualEffects
except ImportError:
    from dmd_manual_effects import ManualEffects

try:
    from . import dmd_quality as dq
except ImportError:
    import dmd_quality as dq


def hash_image(img: Image.Image) -> str:
    """Retourne un hash stable pour une image RGB."""
    data = img.convert("RGB").tobytes()
    return hashlib.md5(data).hexdigest()


def _sobel_magnitude(luma: np.ndarray) -> np.ndarray:
    """Magnitude du gradient de Sobel (approximé) sur une image de luminance 2D."""
    kx = np.array([[1, 0, -1], [2, 0, -2], [1, 0, -1]], dtype=np.float32)
    ky = np.array([[1, 2, 1], [0, 0, 0], [-1, -2, -1]], dtype=np.float32)
    pad = 1
    L = np.pad(luma, ((pad, pad), (pad, pad)), mode="edge")

    gx = (
        kx[0, 0] * L[:-2, :-2]
        + kx[0, 1] * L[:-2, 1:-1]
        + kx[0, 2] * L[:-2, 2:]
        + kx[1, 0] * L[1:-1, :-2]
        + kx[1, 1] * L[1:-1, 1:-1]
        + kx[1, 2] * L[1:-1, 2:]
        + kx[2, 0] * L[2:, :-2]
        + kx[2, 1] * L[2:, 1:-1]
        + kx[2, 2] * L[2:, 2:]
    )
    gy = (
        ky[0, 0] * L[:-2, :-2]
        + ky[0, 1] * L[:-2, 1:-1]
        + ky[0, 2] * L[:-2, 2:]
        + ky[1, 0] * L[1:-1, :-2]
        + ky[1, 1] * L[1:-1, 1:-1]
        + ky[1, 2] * L[1:-1, 2:]
        + ky[2, 0] * L[2:, :-2]
        + ky[2, 1] * L[2:, 1:-1]
        + ky[2, 2] * L[2:, 2:]
    )
    return np.sqrt(gx * gx + gy * gy)


def evaluate_quality(
    original_img: Image.Image,
    dmd_canvas: Image.Image,
    settings=None,
    pixel_perfect: bool = False,
) -> float:
    """Évalue la qualité d'une conversion (score bas = meilleur).

    Dépendance au contexte: le score privilégie la lisibilité DMD
    (contraste/contours/occupation) et non la simple similarité pixel-wise.
    """
    if settings is None:
        # Mode legacy: comparaison pixel-wise simple
        resample = (
            Image.Resampling.NEAREST if pixel_perfect else Image.Resampling.LANCZOS
        )
        reference = DMDEngine.ensure_rgb_on_black(original_img).resize((128, 32), resample)
        arr_orig = np.array(reference).astype(float)
        arr_dmd = np.array(dmd_canvas.convert("RGB")).astype(float)
        diff = np.mean(np.abs(arr_orig - arr_dmd))
        white_orig = np.sum(np.all(arr_orig > 240, axis=2))
        white_dmd = np.sum(np.all(arr_dmd > 240, axis=2))
        white_penalty = max(0, white_dmd - white_orig) * 5
        return diff + white_penalty

    img = DMDEngine.ensure_rgb_on_black(original_img)
    resample = Image.Resampling.NEAREST if pixel_perfect else Image.Resampling.LANCZOS

    optimized = DMDEngine.optimize_for_dmd(img, settings)
    resized, new_w, new_h = DMDEngine.adaptive_resize(
        optimized,
        128,
        32,
        settings["resize_mode"],
        pixel_perfect=pixel_perfect,
    )

    # On évalue sur plusieurs frames pour que le mode scrolling puisse être valorisé
    dmd_frames, _ = DMDEngine.create_animation_frames(
        resized,
        settings,
        (0, 0, 0),
        cleanup=False,
        cleanup_power=settings.get("cleanup_power", 1.0),
    )

    # Frame de référence pour la comparaison (modèle)
    dmd_frame0 = dmd_frames[0].convert("RGB")

    ref_resized = img.resize((new_w, new_h), resample)
    ref_frames, _ = DMDEngine.create_animation_frames(
        ref_resized,
        settings,
        (0, 0, 0),
        cleanup=False,
        cleanup_power=0.0,
    )
    ref_frame0 = ref_frames[0].convert("RGB")

    def rgb_to_luma(arr_rgb: np.ndarray) -> np.ndarray:
        r = arr_rgb[:, :, 0]
        g = arr_rgb[:, :, 1]
        b = arr_rgb[:, :, 2]
        return 0.299 * r + 0.587 * g + 0.114 * b

    l_ref = rgb_to_luma(np.array(ref_frame0).astype(np.float32))
    l_cand = rgb_to_luma(np.array(dmd_frame0).astype(np.float32))

    def estimate_bg_luma(luma: np.ndarray) -> float:
        h, w = luma.shape
        cs = min(6, max(1, min(h, w) // 8))
        corners = np.concatenate(
            [
                luma[:cs, :cs].reshape(-1),
                luma[:cs, -cs:].reshape(-1),
                luma[-cs:, :cs].reshape(-1),
                luma[-cs:, -cs:].reshape(-1),
            ]
        )
        return float(np.median(corners))

    bg_ref = estimate_bg_luma(l_ref)
    bg_cand = estimate_bg_luma(l_cand)

    thr_ref = bg_ref + 18.0
    thr_cand = bg_cand + 18.0

    active_ref = float(np.mean(l_ref > thr_ref))
    active_cand = float(np.mean(l_cand > thr_cand))

    # Occupation: pénaliser images trop petites/peu actives
    target_low, target_high = 0.08, 0.25
    occ_pen = 0.0
    if active_cand < target_low:
        occ_pen = (target_low - active_cand) * 25.0
    elif active_cand > target_high:
        occ_pen = (active_cand - target_high) * 8.0

    # Contraste local sur les pixels actifs
    def local_contrast(luma: np.ndarray, thr: float) -> float:
        mask = luma > thr
        if int(mask.sum()) < 8:
            return 0.0
        vals = luma[mask]
        return float(np.std(vals))

    cont_ref = local_contrast(l_ref, thr_ref)
    cont_cand = local_contrast(l_cand, thr_cand)
    cont_pen = abs(cont_ref - cont_cand) / 50.0

    # Contours: gradient magnitude (Sobel approximé)
    g_ref = _sobel_magnitude(l_ref)
    g_cand = _sobel_magnitude(l_cand)

    mask_edges = (g_ref > 20) | (g_cand > 20)
    if int(mask_edges.sum()) < 16:
        edge_diff = float(np.mean(np.abs(g_ref - g_cand)))
    else:
        edge_diff = float(np.mean(np.abs(g_ref[mask_edges] - g_cand[mask_edges])))

    # Fidélité (composante faible, pour ne pas trop “détruire” la ressemblance)
    luma_diff = float(np.mean(np.abs(l_ref - l_cand)))

    white_orig = float(np.sum(l_ref > 240.0))
    white_cand = float(np.sum(l_cand > 240.0))
    white_penalty = max(0.0, white_cand - white_orig) / (128 * 32)

    # Bonus explicite anti-“trop petit”
    small_pen = 0.0
    if active_ref > target_low and active_cand < 0.03:
        small_pen = (0.03 - active_cand) * 80.0

    # =============================
    # LISIBILITÉ TEXTE / LOGO
    # =============================
    def active_edge_strength(luma: np.ndarray, thr: float) -> float:
        mask = luma > thr
        if int(mask.sum()) < 8:
            return 0.0

        gmag = _sobel_magnitude(luma)
        vals = gmag[mask]
        return float(np.mean(vals)) if vals.size else 0.0

    edge_strength_ref = active_edge_strength(l_ref, thr_ref)
    edge_strength_cand = active_edge_strength(l_cand, thr_cand)

    lis_pen = 0.0
    if edge_strength_ref > 0:
        if edge_strength_cand < edge_strength_ref:
            lis_pen = (
                (edge_strength_ref - edge_strength_cand)
                / max(1.0, edge_strength_ref)
                * 1.8
            )
        else:
            lis_pen = (
                (edge_strength_cand - edge_strength_ref)
                / max(1.0, edge_strength_ref)
                * 0.2
            )

    # =============================
    # POIDS - priorité lisibilité
    # =============================
    w_fid = 0.25
    w_edge = 0.95
    w_cont = 0.75
    w_occ = 1.25
    w_white = 0.55
    w_lis = 3.00

    score = (
        w_fid * luma_diff
        + w_edge * (edge_diff / 30.0)
        + w_cont * cont_pen
        + w_occ * occ_pen
        + w_white * white_penalty
        + w_lis * lis_pen
        + small_pen
    )

    return float(score)


def _rgb_to_luma(arr_rgb: np.ndarray) -> np.ndarray:
    r = arr_rgb[:, :, 0]
    g = arr_rgb[:, :, 1]
    b = arr_rgb[:, :, 2]
    return 0.299 * r + 0.587 * g + 0.114 * b


def _estimate_bg_luma(luma: np.ndarray) -> float:
    h, w = luma.shape
    cs = min(6, max(1, min(h, w) // 8))
    corners = np.concatenate(
        [
            luma[:cs, :cs].reshape(-1),
            luma[:cs, -cs:].reshape(-1),
            luma[-cs:, :cs].reshape(-1),
            luma[-cs:, -cs:].reshape(-1),
        ]
    )
    return float(np.median(corners))


def _active_edge_strength(luma: np.ndarray, thr: float) -> float:
    """Force moyenne des contours (Sobel) sur les pixels actifs (au-dessus du seuil)."""
    mask = luma > thr
    if int(mask.sum()) < 8:
        return 0.0
    gmag = _sobel_magnitude(luma)
    vals = gmag[mask]
    return float(np.mean(vals)) if vals.size else 0.0


def _tonal_fidelity_score(
    dmd_canvas: Image.Image,
    raw_canvas: Image.Image,
    active_mask: np.ndarray,
) -> float:
    """Compare, sur les pixels actifs du candidat, la luminosité moyenne, le
    contraste (écart-type de luminosité) et la saturation moyenne entre le rendu
    final (`dmd_canvas`) et une référence "brute" NON rehaussée par
    optimize_for_dmd (`raw_canvas`) — mesure à quel point le rendu s'est éloigné
    du profil tonal de l'image source. Voir changelog v19."""
    if int(active_mask.sum()) < 8:
        return 1.0

    l_cand = _rgb_to_luma(np.array(dmd_canvas).astype(np.float32))
    l_raw = _rgb_to_luma(np.array(raw_canvas).astype(np.float32))

    mean_cand, std_cand = float(l_cand[active_mask].mean()), float(l_cand[active_mask].std())
    mean_raw, std_raw = float(l_raw[active_mask].mean()), float(l_raw[active_mask].std())

    hsv_cand = np.array(dmd_canvas.convert("HSV")).astype(np.float32)
    hsv_raw = np.array(raw_canvas.convert("HSV")).astype(np.float32)
    sat_cand = float(hsv_cand[:, :, 1][active_mask].mean()) / 255.0
    sat_raw = float(hsv_raw[:, :, 1][active_mask].mean()) / 255.0

    luminosity_fid = max(0.0, 1.0 - abs(mean_cand - mean_raw) / 255.0)
    contrast_fid = max(0.0, 1.0 - abs(std_cand - std_raw) / 128.0)
    saturation_fid = max(0.0, 1.0 - abs(sat_cand - sat_raw))

    return (luminosity_fid + contrast_fid + saturation_fid) / 3.0


def score_variant(
    original_img: Image.Image,
    settings: dict,
    pixel_perfect: bool = False,
    cleanup_power: float = None,
    fidelity_weight: float = 0.0,
    return_breakdown: bool = False,
    resize_cache: dict = None,
):
    """Rend et score une variante de réglages selon 2 critères demandés par
    l'utilisateur pour le mode Auto/IA :

    - occupation de l'affichage : part de pixels actifs (au-dessus du fond) sur le
      panneau DMD, cible 10%-30% (ni trop vide ni surchargé).
    - lisibilité : force des contours actifs conservée par rapport à une référence
      redimensionnée de la même façon et AVEC le même optimize_for_dmd (contraste/
      saturation/seuil noir) que le candidat, mais SANS cleanup_power — isole ainsi
      spécifiquement l'effet du nettoyage post-resize, pour juger si celui-ci
      dégrade le texte/logo (voir changelog v16).

    `fidelity_weight` (0.0 par défaut, comportement inchangé) : active une 3e
    dimension optionnelle, la fidélité tonale à l'original (luminosité/contraste/
    saturation), voir `_tonal_fidelity_score` et changelog v19. N'affecte QUE les
    appelants qui la passent explicitement (`_optimize_cleanup_and_pixel_perfect`).

    PLUS HAUT = MEILLEUR (contrairement à evaluate_quality où plus bas = meilleur).
    Retourne (score, canvas_rendu) — le canvas est renvoyé pour éviter à l'appelant
    de refaire un rendu séparé juste pour l'aperçu.

    `resize_cache` (optionnel, None par défaut = comportement inchangé) : dict
    fourni par l'appelant, réutilisé/rempli ici pour éviter de refaire 2 calculs
    coûteux à pleine résolution quand plusieurs appels partagent les mêmes
    entrées :
    - `optimize_for_dmd` (chaîne PIL.ImageEnhance Contrast/Color/Sharpness +
      MedianFilter, LE poste le plus coûteux) ne dépend QUE des 4 réglages
      tonaux (brightness/contrast/saturation/black_threshold) — PAS de
      resize_mode/direction/pixel_perfect. Fit et fill utilisent la MÊME
      grille tonale (voir generate_settings_variants) : cache clé sur le tonal
      SEUL, pour que les 12 variantes fit et les 12 variantes fill partagent
      les mêmes 12 calculs au lieu d'en refaire 24.
    - `adaptive_resize` (LANCZOS, plus rapide mais pas gratuit) dépend EN PLUS
      de resize_mode/direction/pixel_perfect — clé séparée, sur-ensemble de la
      précédente. Utile pour le balayage cleanup_power et la descente tonale
      (`_optimize_cleanup_and_pixel_perfect`), qui répètent souvent exactement
      la même combinaison tonal+resize.
    Le cache est scopé à UNE image (créé et jeté par l'appelant), jamais
    partagé entre images — voir get_settings_for_image()/
    auto_analyze_and_preview().
    """
    if cleanup_power is None:
        cleanup_power = settings.get("cleanup_power", 1.0)

    original_img = DMDEngine.crop_to_visible_content(original_img)
    img = DMDEngine.ensure_rgb_on_black(original_img)
    resample = Image.Resampling.NEAREST if pixel_perfect else Image.Resampling.LANCZOS

    tonal_key = (
        "opt",
        round(float(settings.get("brightness", 1.0)), 6),
        round(float(settings.get("contrast", 1.5)), 6),
        round(float(settings.get("saturation", 1.3)), 6),
        int(settings.get("black_threshold", 30)),
    )
    optimized = resize_cache.get(tonal_key) if resize_cache is not None else None
    if optimized is None:
        optimized = DMDEngine.optimize_for_dmd(img, settings)
        if resize_cache is not None:
            resize_cache[tonal_key] = optimized

    resize_key = tonal_key + ("resized", settings.get("resize_mode"), settings.get("direction"), pixel_perfect)
    cached_resize = resize_cache.get(resize_key) if resize_cache is not None else None
    if cached_resize is not None:
        resized, new_w, new_h = cached_resize
    else:
        resized, new_w, new_h = DMDEngine.adaptive_resize(
            optimized,
            128,
            32,
            settings["resize_mode"],
            pixel_perfect=pixel_perfect,
            direction=settings.get("direction"),
        )
        if resize_cache is not None:
            resize_cache[resize_key] = (resized, new_w, new_h)
    cand_frames, _ = DMDEngine.create_animation_frames(
        resized,
        settings,
        (0, 0, 0),
        cleanup=(cleanup_power > 0),
        cleanup_power=cleanup_power,
        max_frames=1,
        sample_mid_scroll=True,
    )
    dmd_canvas = cand_frames[0].convert("RGB")

    ref_resized = optimized.resize((new_w, new_h), resample)
    ref_frames, _ = DMDEngine.create_animation_frames(
        ref_resized,
        settings,
        (0, 0, 0),
        cleanup=False,
        cleanup_power=0.0,
        max_frames=1,
        sample_mid_scroll=True,
    )
    ref_canvas = ref_frames[0].convert("RGB")

    l_cand = _rgb_to_luma(np.array(dmd_canvas).astype(np.float32))
    l_ref = _rgb_to_luma(np.array(ref_canvas).astype(np.float32))

    bg_cand = _estimate_bg_luma(l_cand)
    bg_ref = _estimate_bg_luma(l_ref)
    thr_cand = bg_cand + 18.0
    thr_ref = bg_ref + 18.0

    active_mask_cand = l_cand > thr_cand
    active_cand = float(np.mean(active_mask_cand))

    # --- Occupation : cible 10%-30% de pixels actifs ---
    target_low, target_high = 0.10, 0.30
    if active_cand < target_low:
        occ_score = active_cand / target_low if target_low > 0 else 0.0
    elif active_cand > target_high:
        occ_score = max(0.0, 1.0 - (active_cand - target_high) / (1.0 - target_high))
    else:
        occ_score = 1.0

    # --- Lisibilité : contours actifs conservés vs référence ---
    # Formule SYMÉTRIQUE (v10) : un candidat avec BEAUCOUP plus de contours que la
    # référence n'est pas forcément "plus net" — c'est souvent du bruit de
    # quantification/contraste (speckle) qui gonfle artificiellement la magnitude de
    # Sobel sans que le texte soit réellement plus lisible pour un humain. L'ancienne
    # formule min(1.0, ratio) plafonnait sans jamais pénaliser ce cas ; min(ratio,
    # 1/ratio) pénalise l'écart dans les deux sens et pique à 1.0 quand candidat et
    # référence ont une force de contour comparable.
    edge_ref = _active_edge_strength(l_ref, thr_ref)
    edge_cand = _active_edge_strength(l_cand, thr_cand)
    if edge_ref <= 0:
        legibility_score = 1.0
    else:
        ratio = edge_cand / edge_ref
        legibility_score = min(ratio, 1.0 / ratio) if ratio > 0 else 0.0

    # --- Fidélité tonale à l'original (optionnelle, voir changelog v19) ---
    fidelity_score = 1.0
    if fidelity_weight > 0:
        # raw_resized ne dépend PAS du tonal (contraste/saturation/etc.),
        # seulement de resize_mode/direction/pixel_perfect — préfixe "raw"
        # dédié, jamais de collision avec tonal_key/resize_key ("opt"/"opt"+
        # "resized", arités différentes de toute façon).
        raw_key = ("raw", settings.get("resize_mode"), settings.get("direction"), pixel_perfect)
        raw_resized = resize_cache.get(raw_key) if resize_cache is not None else None
        if raw_resized is None:
            raw_resized, _, _ = DMDEngine.adaptive_resize(
                img,
                128,
                32,
                settings["resize_mode"],
                pixel_perfect=pixel_perfect,
                direction=settings.get("direction"),
            )
            if resize_cache is not None:
                resize_cache[raw_key] = raw_resized
        raw_frames, _ = DMDEngine.create_animation_frames(
            raw_resized,
            settings,
            (0, 0, 0),
            cleanup=False,
            cleanup_power=0.0,
            max_frames=1,
            sample_mid_scroll=True,
        )
        raw_canvas = raw_frames[0].convert("RGB")
        fidelity_score = _tonal_fidelity_score(dmd_canvas, raw_canvas, active_mask_cand)

    w_legibility = 3.0
    w_occupation = 1.0
    w_fidelity = 1.5
    max_score = w_legibility + w_occupation  # échelle historique (0-4.0)

    weights_sum = w_legibility + w_occupation
    raw = w_legibility * legibility_score + w_occupation * occ_score
    if fidelity_weight > 0:
        weights_sum += w_fidelity
        raw += fidelity_weight * w_fidelity * fidelity_score

    # Normalisé sur l'échelle historique (0-4.0) pour rester comparable au score
    # des propositions 1/2 (fidelity_weight=0) même quand la dimension fidélité
    # est active — sinon un score "plus haut" ne signifierait rien de comparable
    # (échelle 0-5.5 au lieu de 0-4.0), voir changelog v19.
    score = raw / weights_sum * max_score

    if return_breakdown:
        # plain_score : occupation+lisibilité SEULES (identique à ce que
        # renverrait score_variant avec fidelity_weight=0) — sert de
        # garde-fou à l'appelant pour ne jamais accepter un changement qui
        # dégraderait ce score historique au nom de la fidélité (voir
        # _optimize_cleanup_and_pixel_perfect, dmd_converter.py v42).
        plain_score = w_legibility * legibility_score + w_occupation * occ_score
        breakdown = {
            "occ_score": occ_score,
            "legibility_score": legibility_score,
            "fidelity_score": fidelity_score,
            "plain_score": plain_score,
        }
        return float(score), dmd_canvas, breakdown

    return float(score), dmd_canvas


def _flood_fill_component(mask: np.ndarray, y0: int, x0: int) -> np.ndarray:
    """Diffusion vectorisée (dilatation booléenne répétée) depuis une graine —
    retourne le masque de LA composante connexe (4-connexité) contenant (y0, x0).
    Même principe que flood_fill (dmd_converter.py), sans dépendance à scipy."""
    h, w = mask.shape
    frontier = np.zeros((h, w), dtype=bool)
    frontier[y0, x0] = True
    comp = frontier.copy()

    while frontier.any():
        up = np.zeros((h, w), dtype=bool)
        up[:-1, :] = frontier[1:, :]
        down = np.zeros((h, w), dtype=bool)
        down[1:, :] = frontier[:-1, :]
        left = np.zeros((h, w), dtype=bool)
        left[:, :-1] = frontier[:, 1:]
        right = np.zeros((h, w), dtype=bool)
        right[:, 1:] = frontier[:, :-1]
        frontier = (up | down | left | right) & mask & ~comp
        comp |= frontier

    return comp


def _label_connected_components_bbox(mask: np.ndarray) -> List[Tuple[int, int, int]]:
    """Étiquette les composantes connexes (4-connexité) d'un masque booléen et
    retourne, pour chacune, (aire_en_pixels, hauteur_bbox, largeur_bbox) — la
    hauteur de bounding box sert à estimer la taille physique des lettres (voir
    resize_will_shrink_text_too_much)."""
    h, w = mask.shape
    visited = np.zeros((h, w), dtype=bool)
    boxes: List[Tuple[int, int, int]] = []

    remaining_ys, remaining_xs = np.where(mask & ~visited)
    while remaining_ys.size:
        y0, x0 = int(remaining_ys[0]), int(remaining_xs[0])
        comp = _flood_fill_component(mask, y0, x0)
        visited |= comp
        ys, xs = np.where(comp)
        boxes.append((
            int(comp.sum()),
            int(ys.max() - ys.min() + 1),
            int(xs.max() - xs.min() + 1),
        ))
        remaining_ys, remaining_xs = np.where(mask & ~visited)

    return boxes


def _estimate_bg_color(arr_rgb: np.ndarray) -> np.ndarray:
    """Comme _estimate_bg_luma mais retourne la couleur RVB médiane des coins (pas
    seulement la luminance) — nécessaire pour un seuillage par distance de couleur
    qui capture aussi le contraste de teinte/saturation, pas que de luminosité
    (ex. texte rouge sur fond vert de luminance proche : indiscernable pour un
    seuillage luminance seule, évident pour un humain)."""
    h, w, _ = arr_rgb.shape
    cs = min(6, max(1, min(h, w) // 8))
    corners = np.concatenate(
        [
            arr_rgb[:cs, :cs].reshape(-1, 3),
            arr_rgb[:cs, -cs:].reshape(-1, 3),
            arr_rgb[-cs:, :cs].reshape(-1, 3),
            arr_rgb[-cs:, -cs:].reshape(-1, 3),
        ]
    )
    return np.median(corners, axis=0)


def _binarize_by_color_distance(img: Image.Image, color_thr: float = 40.0) -> np.ndarray:
    """Masque binaire (pixel actif vs fond) par distance de COULEUR (RVB) au fond
    estimé, à la résolution NATIVE de l'image (pas de réduction préalable — la
    hauteur de bounding box mesurée doit rester en pixels réels de l'image
    source, voir resize_will_shrink_text_too_much)."""
    arr = np.array(DMDEngine.ensure_rgb_on_black(img)).astype(np.float32)
    bg = _estimate_bg_color(arr)
    dist = np.linalg.norm(arr - bg, axis=2)
    return dist > color_thr


def _median_letter_height(
    mask: np.ndarray, min_area: int = 15, max_area_ratio: float = 0.35
) -> float:
    """Hauteur médiane (en pixels, dans le repère du masque) des composantes
    connexes "de taille lettre" — exclut le bruit ponctuel (min_area) et les
    grandes formes pleines (max_area_ratio de la surface totale). Retourne 0.0 si
    aucune composante ne passe le filtre (texte déjà totalement fusionné dans le
    masque analysé, ex. contour épais reliant toutes les lettres)."""
    max_area = mask.size * max_area_ratio
    boxes = _label_connected_components_bbox(mask)
    heights = [bh for area, bh, bw in boxes if min_area <= area <= max_area]
    if not heights:
        return 0.0
    return statistics.median(heights)


def resize_will_shrink_text_too_much(
    original_img: Image.Image,
    fit_scale: float,
    min_letter_px: float = 8.0,
) -> bool:
    """Estime si le mode Resize/fit va rendre le texte source illisible, à partir
    d'un principe physique simple plutôt que d'une reconnaissance de "présence de
    texte" : une lettre a besoin d'un minimum de pixels de hauteur pour rester
    visuellement distincte une fois réduite. Mesure la hauteur MÉDIANE des
    composantes "de taille lettre" dans l'image source (binarisation par distance
    de COULEUR — capture aussi les logos où la lisibilité vient d'un contraste de
    teinte, pas seulement de luminosité), la multiplie par le facteur d'échelle du
    resize fit (fit_scale = min(128/w, 32/h)), et compare au seuil min_letter_px.

    Si aucune composante "de taille lettre" n'est détectée dans l'original (texte
    déjà fusionné avec son contour dans le design source), retourne True — un
    texte déjà fusionné à pleine résolution ne peut que rester illisible une fois
    réduit.

    Approche validée empiriquement sur 7 logos réels variés (types de rendu très
    différents : contours nets, dégradés chromés, texture rayures/étoiles) :
    sépare parfaitement les cas lisibles/illisibles observés, y compris 2 cas où
    toutes les heuristiques précédentes (composantes connexes sur seuil de
    luminance, OCR Tesseract sur rendu carré et LED, corrélation de forme
    original/candidat) échouaient. Remplace detect_text_likelihood/
    text_legibility_collapsed (composantes connexes sur seuil de luminance,
    abandonné — voir mémoire projet pour l'historique des tentatives)."""
    mask = _binarize_by_color_distance(original_img)
    med_h = _median_letter_height(mask)
    if med_h <= 0:
        return True
    return (med_h * fit_scale) < min_letter_px


# ============================================================================
# Résolution des réglages (Tier 2, plan perf batch, 2026-08-06) — versions
# PURES (sans self/tk.Variable) de DMDConverter.generate_settings_variants/
# _best_variant/_optimize_cleanup_and_pixel_perfect/get_settings_for_image,
# déplacées ici pour être appelables depuis un worker ProcessPoolExecutor
# (non picklable si liées à une instance Tkinter). DMDConverter garde des
# méthodes du même nom qui ne font plus que lire les tk.Variable puis
# déléguer ici — même pattern déjà en place pour score_variant/
# render_dmd_frame (_pipeline_score_variant/_pipeline_render_dmd_frame dans
# dmd_converter.py). Voir process_one_image() (dmd_converter.py) pour
# l'utilisation côté worker.
# ============================================================================

# Grille fixe (ex-mode "précis") : le fix de performance max_frames a rendu
# l'analyse sub-seconde dans tous les cas, l'option "Mode IA" rapide/précis
# n'avait plus d'intérêt réel et a été supprimée.
CONTRAST_MULTS = [0.9, 1.0, 1.15]
BLACK_THRESHOLDS = [25, 30, 35, 40]

# Paramètres tonaux ré-explorés à l'étape 2 de optimize_cleanup_and_pixel_perfect
# (nom, deltas, additif?) — deltas multiplicatifs pour contraste/saturation/
# luminosité (±15% autour de la valeur courante), additif clampé pour le seuil
# noir (±10, borné [10,60]).
TONAL_REFINEMENT_PARAMS = (
    ("contrast", (0.85, 1.0, 1.15), False),
    ("saturation", (0.85, 1.0, 1.15), False),
    ("brightness", (0.85, 1.0, 1.15), False),
    ("black_threshold", (-10, 0, 10), True),
)


# v25 -- règle de forme : à partir de ce rapport largeur/hauteur (source
# recadrée), Fill/défilement est imposé au lieu de Resize. Réglable dans l'UI
# ("Défilement dès"), transmis au lot via batch_params["fill_min_ratio"].
FILL_MIN_RATIO_DEFAULT = 2.0


def shape_forces_fill(size, min_ratio=FILL_MIN_RATIO_DEFAULT):
    """True si la forme de la source (recadrée) impose Fill/défilement.
    Aucun rognage : Fill agrandit selon max(128/w, 32/h) et le sens de
    défilement (generate_settings_variants) suit le même rapport, donc tout le
    logo passe à l'écran au cours de l'animation. Remplace, dans l'aperçu comme
    dans le lot, le garde-fou resize_will_shrink_text_too_much : mesuré sur
    54 776 logos réels, la détection de lettres forçait Fill sur 75 % des
    logos presque carrés, dont une majorité parfaitement reconnaissables en
    Resize (gros plans défilants méconnaissables à la place)."""
    w, h = size
    return h > 0 and (w / h) >= float(min_ratio)


def generate_settings_variants(
    size, resize_mode, base_fps, base_duration, base_scroll, base_contrast, base_saturation
):
    """Génère des variantes de paramètres pour UN mode de redimensionnement
    (fit ou fill), à évaluer indépendamment via score_variant. Générer les 2
    modes séparément (plutôt qu'un pool mélangé) évite qu'un mode ne domine
    structurellement le classement de l'autre. Version pure de
    DMDConverter.generate_settings_variants (voir ce wrapper pour la lecture
    des tk.Variable base_*)."""
    w, h = size
    ratio = w / h
    target_ratio = 128 / 32

    direction = (
        "auto"
        if resize_mode == "fit"
        else ("horizontal" if ratio > target_ratio else "vertical")
    )
    label = "Resize" if resize_mode == "fit" else "Fill"

    variants = []
    for cm in CONTRAST_MULTS:
        for bt in BLACK_THRESHOLDS:
            variants.append(
                {
                    "name": label,
                    "resize_mode": resize_mode,
                    "contrast": base_contrast * cm,
                    "saturation": base_saturation,
                    "brightness": 1.0,
                    "black_threshold": bt,
                    "fps": base_fps,
                    "scroll_speed": base_scroll,
                    "duration": base_duration,
                    "direction": direction,
                    # Resize/Fill affichent le rendu "brut" (aucun nettoyage) —
                    # c'est Optimisé (#3) qui teste réellement cleanup_power
                    # (0.0 à 1.0, via optimize_cleanup_and_pixel_perfect) et le
                    # retient seulement s'il améliore le score.
                    "cleanup_power": 0.0,
                }
            )
    return variants


def best_variant(img, variants, pixel_perfect=False, resize_cache=None):
    """Retourne (score, settings, canvas) de la meilleure variante (score le plus
    haut) parmi une liste, selon score_variant. Le choix pixel_perfect est
    explicitement gravé dans les settings retournés (clé "_pixel_perfect").
    Version pure de DMDConverter._best_variant."""
    best = None
    for v in variants:
        score, canvas = score_variant(
            img, v, pixel_perfect=pixel_perfect, resize_cache=resize_cache
        )
        if best is None or score > best[0]:
            best = (score, {**v, "_pixel_perfect": pixel_perfect}, canvas)
    return best


def optimize_cleanup_and_pixel_perfect(
    img, base_settings, force_pixel_perfect=False, resize_cache=None
):
    """Affine une variante déjà retenue (proposition "Optimisé") en 2 étapes —
    voir DMDConverter._optimize_cleanup_and_pixel_perfect (version méthode,
    docstring complète conservée là) pour le détail du raisonnement. Version
    pure, comportement strictement identique, réglages en paramètres
    explicites plutôt que lus depuis self."""
    pixel_perfect_options = (force_pixel_perfect,)
    SCORE_EPSILON = 0.001  # tolérance flottante, pas une concession de qualité

    best = None
    for cleanup_power in (0.0, 0.3, 0.6, 0.9, 1.0):
        for pixel_perfect in pixel_perfect_options:
            score, canvas = score_variant(
                img,
                base_settings,
                pixel_perfect=pixel_perfect,
                cleanup_power=cleanup_power,
                resize_cache=resize_cache,
            )
            if best is None or score > best[0]:
                best = (score, cleanup_power, pixel_perfect, canvas)

    best_score, opt_cleanup, opt_pixel_perfect, best_canvas = best
    current = dict(base_settings)

    _, _, guard_breakdown = score_variant(
        img,
        current,
        pixel_perfect=opt_pixel_perfect,
        cleanup_power=opt_cleanup,
        fidelity_weight=1.0,
        return_breakdown=True,
        resize_cache=resize_cache,
    )
    best_fidelity = guard_breakdown["fidelity_score"]

    for param, deltas, additive in TONAL_REFINEMENT_PARAMS:
        param_best = None
        for delta in deltas:
            candidate = dict(current)
            if additive:
                candidate[param] = max(10, min(60, current[param] + delta))
            else:
                candidate[param] = current[param] * delta
            _, canvas, breakdown = score_variant(
                img,
                candidate,
                pixel_perfect=opt_pixel_perfect,
                cleanup_power=opt_cleanup,
                fidelity_weight=1.0,
                return_breakdown=True,
                resize_cache=resize_cache,
            )
            accepted = (
                breakdown["plain_score"] >= best_score - SCORE_EPSILON
                and breakdown["fidelity_score"] > best_fidelity
            )
            if accepted and (param_best is None or breakdown["fidelity_score"] > param_best[2]):
                param_best = (candidate[param], canvas, breakdown["fidelity_score"], breakdown["plain_score"])
        if param_best is not None:
            current[param] = param_best[0]
            best_canvas = param_best[1]
            best_fidelity = param_best[2]
            best_score = max(best_score, param_best[3])

    opt_settings = {
        **current,
        "name": "Optimisé",
        "cleanup_power": opt_cleanup,
        "_pixel_perfect": opt_pixel_perfect,
    }
    return best_score, opt_settings, best_canvas


# v26 -- logos sombres monochromes (ex. texte noir sur fond transparent, prévu
# pour un fond clair) : invisibles sur un DMD noir. Mesures sur les PIXELS
# VISIBLES uniquement (sinon tout logo sur fond noir paraîtrait "sombre").
DARK_LUM_MAX = 40.0     # luminance moyenne visible sous laquelle le logo est "sombre"
DARK_SAT_MAX = 60.0     # saturation moyenne visible sous laquelle il est monochrome
DARK_INVERT_MARGIN = 3  # points de score qualité que l'inversion doit gagner


def is_dark_monochrome(img):
    """True si l'image a de la transparence et que ses pixels visibles sont
    sombres et peu saturés. Sans transparence, jamais : inverser une image
    opaque inverserait aussi son fond."""
    if img.mode not in ("RGBA", "LA", "P") and img.info.get("transparency") is None:
        return False
    a = np.asarray(img.convert("RGBA")).astype(np.float32)
    alpha = a[..., 3]
    vis = alpha > 16
    if not vis.any() or vis.all():
        return False
    rgb = a[..., :3][vis]
    lum = float((0.299 * rgb[:, 0] + 0.587 * rgb[:, 1] + 0.114 * rgb[:, 2]).mean())
    mx, mn = rgb.max(axis=1), rgb.min(axis=1)
    sat = float((np.where(mx > 0, (mx - mn) / np.maximum(mx, 1.0), 0.0) * 255.0).mean())
    return lum < DARK_LUM_MAX and sat < DARK_SAT_MAX


def invert_visible(img):
    """Inverse les couleurs, transparence conservée (le fond transparent reste
    noir une fois posé sur le DMD) : un logo noir devient blanc."""
    rgba = np.asarray(img.convert("RGBA")).copy()
    rgba[..., :3] = 255 - rgba[..., :3]
    return Image.fromarray(rgba, "RGBA")


def _rendered_quality(image_path, settings):
    """Score dmd_quality (0-100) du rendu complet que produirait l'export."""
    frames, fps = render_dmd_frame(
        image_path, settings, return_frames=True,
        cleanup_power=settings.get("cleanup_power", 1.0),
        pixel_perfect=bool(settings.get("_pixel_perfect", False)),
    )
    frames = frames if isinstance(frames, list) else [frames]
    return dq.evaluate_frames(frames, int(1000 / max(1, fps))).score


def maybe_invert_dark(image_path, img, base_settings, resolve_fn):
    """Si `img` (source recadrée) est un logo sombre monochrome, résout aussi
    ses réglages sur la version inversée (`resolve_fn(image_inversée)`) et
    renvoie ces réglages (marqués invert_dark) seulement si leur rendu gagne
    au moins DARK_INVERT_MARGIN points de score qualité ; sinon None.
    Mesuré sur 54 776 logos réels : ~1 % concernés, les 315 GIF entièrement
    noirs du pack récupérés en quasi-totalité, et les logos sombres à parties
    claires (contours, texte coloré) conservés car leur score baisse une fois
    inversés."""
    if not is_dark_monochrome(img):
        return None
    try:
        inv_settings = dict(resolve_fn(invert_visible(img)), invert_dark=True)
        if _rendered_quality(image_path, inv_settings) >= _rendered_quality(image_path, base_settings) + DARK_INVERT_MARGIN:
            return inv_settings
    except Exception:
        pass  # jamais bloquant : on garde le rendu normal
    return None


def resolve_image_settings(image_path, batch_params, locked_settings=None, cached_settings=None):
    """Résout les réglages optimaux pour UNE image (même logique resize-vs-fill
    puis optimisation nettoyage/pixel-perfect que l'aperçu interactif Auto/IA,
    sans les propositions artistiques — pas de sens en export automatique non
    supervisé). Version pure de DMDConverter.get_settings_for_image.

    `batch_params` : dict {fps, duration, scroll_speed, contrast, saturation,
    pixel_perfect} — snapshot figé des tk.Variable AVANT dispatch (voir
    process_images()/process_one_image(), jamais lu depuis un worker).
    `locked_settings`/`cached_settings` : équivalents figés de
    self.proposals[self.locked_proposal]/self.image_settings[image_path],
    résolus par l'appelant AVANT dispatch (un worker ne peut pas lire self).
    """
    if locked_settings is not None:
        return apply_render_profile(locked_settings, batch_params)
    if cached_settings is not None:
        return apply_render_profile(cached_settings, batch_params)

    # v24 : recadrée comme dans l'aperçu (auto_analyze_and_preview) -- la taille
    # sert au sens de défilement Fill (generate_settings_variants), le rendu
    # recadrant de son côté (score_variant/render_dmd_frame)
    img = DMDEngine.crop_to_visible_content(DMDEngine.load_image(image_path))
    settings = _resolve_from_image(img, batch_params)
    # v26 : logo sombre monochrome -> version inversée si nettement meilleure
    # (v27 : désactivable par profil, batch_params["invert_dark"], actif par défaut)
    if batch_params.get("invert_dark", True):
        inverted = maybe_invert_dark(image_path, img, settings,
                                     lambda inv: _resolve_from_image(inv, batch_params))
        if inverted is not None:
            settings = inverted
    return apply_render_profile(settings, batch_params)


def apply_render_profile(settings, batch_params):
    """v27 -- copie des réglages avec les options de RENDU du profil actif
    (aujourd'hui : plafond d'aller-retour max_scroll_cycle_s, lu par
    DMDEngine.create_animation_frames). Appliqué aussi aux réglages venus de
    l'aperçu (cache/verrou) : changer de profil après un aperçu s'applique
    au lot. Sans plafond dans le profil, la clé est retirée (aucune limite)."""
    out = dict(settings)
    cap = batch_params.get("max_scroll_cycle_s")
    if cap:
        out["max_scroll_cycle_s"] = float(cap)
    else:
        out.pop("max_scroll_cycle_s", None)
    return out


def _resolve_from_image(img, batch_params):
    """Cœur de resolve_image_settings (v26 : extrait tel quel pour pouvoir être
    rejoué sur la version inversée d'un logo sombre)."""
    size = img.size
    force_pixel_perfect = batch_params["pixel_perfect"]

    fit_variants = generate_settings_variants(
        size, "fit", batch_params["fps"], batch_params["duration"],
        batch_params["scroll_speed"], batch_params["contrast"], batch_params["saturation"],
    )
    fill_variants = generate_settings_variants(
        size, "fill", batch_params["fps"], batch_params["duration"],
        batch_params["scroll_speed"], batch_params["contrast"], batch_params["saturation"],
    )

    # Cache partagé (Tier 0) sur les ~42 appels à score_variant nécessaires
    # pour UNE image — scopé à cette image uniquement.
    variant_cache = {}

    fit_score, fit_settings, _ = best_variant(
        img, fit_variants, pixel_perfect=force_pixel_perfect, resize_cache=variant_cache
    )
    fill_score, fill_settings, _ = best_variant(
        img, fill_variants, pixel_perfect=force_pixel_perfect, resize_cache=variant_cache
    )

    # v25 : même règle que l'aperçu (auto_analyze_and_preview) ; v27 : seulement
    # si le profil la demande (fill_min_ratio absent/None/0 = choix au score)
    min_ratio = batch_params.get("fill_min_ratio")
    if min_ratio and shape_forces_fill(size, min_ratio):
        retained_settings = fill_settings
    else:
        retained_settings = fit_settings if fit_score >= fill_score else fill_settings

    _, opt_settings, _ = optimize_cleanup_and_pixel_perfect(
        img, retained_settings, force_pixel_perfect=force_pixel_perfect, resize_cache=variant_cache,
    )
    return opt_settings.copy()


def analyze_characteristics(canvas: Image.Image) -> dict:
    """Caractéristiques simples d'un rendu DMD, utilisées pour choisir des effets
    artistiques adaptés au contenu (mode Auto/IA, propositions artistiques) :

    - occupation : part de pixels actifs (au-dessus du fond)
    - edge_density : force moyenne des contours actifs (texte/logo net = élevé,
      contenu plus organique/photo = plus faible)
    - colorfulness : saturation moyenne des pixels actifs (0-1)
    """
    rgb = canvas.convert("RGB")
    arr = np.array(rgb).astype(np.float32)
    luma = _rgb_to_luma(arr)
    bg = _estimate_bg_luma(luma)
    thr = bg + 18.0
    mask = luma > thr

    occupation = float(np.mean(mask))
    edge_density = _active_edge_strength(luma, thr)

    if int(mask.sum()) >= 8:
        hsv = np.array(rgb.convert("HSV")).astype(np.float32)
        colorfulness = float(np.mean(hsv[:, :, 1][mask])) / 255.0
    else:
        colorfulness = 0.0

    return {
        "occupation": occupation,
        "edge_density": edge_density,
        "colorfulness": colorfulness,
    }


def render_dmd_frame(
    image_path: str,
    settings: dict,
    return_frames: bool = False,
    cleanup: bool = True,
    cleanup_power: float = 1.0,
    pixel_perfect: bool = False,
    return_direction: bool = False,
    return_source: bool = False,
):
    """Rend une image en DMD avec les paramètres donnés.

    `return_source` (2026-08-06, Tier 1 plan perf batch, défaut False =
    comportement inchangé) : si True, renvoie AUSSI l'image source déjà
    chargée ici en dernière position du tuple — évite à l'appelant
    (process_images) de rouvrir/redécoder le même fichier une 3e fois juste
    pour `detect_palette`. Renvoie délibérément la version NON recadrée
    (`raw_source`, avant `crop_to_visible_content`) : c'est ce que
    process_images passait jusqu'ici à `detect_palette` (simple
    `DMDEngine.load_image`, sans crop) — vérifié que `crop_to_visible_content`
    ne change PAS la détection de palette dans le cas courant, mais renvoyer
    la version brute reproduit le comportement exact plutôt que de le
    supposer équivalent. Même précédent que `return_direction`."""
    raw_source = DMDEngine.load_image(image_path)
    img_orig = DMDEngine.crop_to_visible_content(raw_source)
    if settings.get("invert_dark"):  # v26 : logo sombre retenu inversé
        img_orig = invert_visible(img_orig)

    # Détecter fond
    bg_color, _is_dark = DMDEngine.detect_background_color(img_orig)

    # Forcer fond noir en mode AUTO pour conserver le rendu DMD attendu
    if settings.get("resize_mode") == "auto":
        bg_color = (0, 0, 0)

    # Optimiser pour DMD
    img = DMDEngine.optimize_for_dmd(img_orig, settings)

    # Redimensionner adaptatif
    img, new_w, new_h = DMDEngine.adaptive_resize(
        img,
        128,
        32,
        settings["resize_mode"],
        pixel_perfect=pixel_perfect,
        direction=settings.get("direction"),
    )

    artistic_effect = settings.get("_artistic_effect")
    if artistic_effect:
        # Proposition artistique (mode Auto/IA) : rend d'abord l'animation de base
        # normalement (respecte resize_mode/direction/scroll/pixel-perfect de la
        # proposition retenue), puis superpose l'effet par-dessus chaque frame — le
        # scrolling/pixel-perfect reste visible, l'effet s'y ajoute au lieu de le
        # remplacer. Point d'intégration unique — preview, export simple et export
        # par lot en bénéficient tous sans logique dupliquée.
        base_frames, base_direction = DMDEngine.create_animation_frames(
            img,
            settings,
            bg_color,
            cleanup=(cleanup and cleanup_power > 0),
            cleanup_power=cleanup_power,
        )
        effect_duration = float(settings.get("_artistic_duration", 2.0))
        effect_fps = int(settings.get("_artistic_fps", settings.get("fps", 10)))
        frames = ManualEffects.apply_over_frames(
            artistic_effect, base_frames, duration=effect_duration, fps=effect_fps
        )
        direction = f"{artistic_effect}_{base_direction}"
    else:
        frames, direction = DMDEngine.create_animation_frames(
            img,
            settings,
            bg_color,
            cleanup=(cleanup and cleanup_power > 0),
            cleanup_power=cleanup_power,
            max_frames=(1 if not return_frames else None),
        )

    if not return_frames:
        result = (frames[0], settings["fps"])
        if return_direction:
            result = (*result, direction)
        if return_source:
            result = (*result, raw_source)
        return result

    result = (frames, settings["fps"])
    if return_direction:
        result = (*result, direction)
    if return_source:
        result = (*result, raw_source)
    return result
