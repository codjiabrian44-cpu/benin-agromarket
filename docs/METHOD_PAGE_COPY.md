# Method and limits page: French copy (placeholders in {curly braces})
Rules for the agent: every {placeholder} is computed from the export (web/src/data/generated/method-tables.json, forecasts.json) or from a generated table in docs/tables/. If a field is missing, add it in the export script and run validate_export. Never type a number by hand. Translate to English with the same structure and the same placeholders. Terms in [brackets] get a glossary tooltip.

## 1. Ce que ce site fait, et ce qu'il ne fait pas
Ce site montre l'évolution mensuelle des prix de détail du maïs blanc, de la tomate et de l'igname blanche sur les marchés béninois bien suivis, et propose des prévisions pour les 1 à 3 prochains mois, avec leur marge d'incertitude. Les prix sont nominaux, en francs CFA par kilo (XOF/kg). Ce sont des prévisions statistiques : elles peuvent se tromper, et elles ne constituent pas un conseil d'achat ou de vente.

## 2. D'où viennent les données
Les prix viennent de la base de prix alimentaires du Programme alimentaire mondial (PAM), publiée sur la plateforme HDX sous licence CC BY-IGO 3.0. Elle rassemble des relevés de sources nationales (ONASA, CT-SAGSA, INStaD, FAO). Elle contient {n_observations} relevés de prix entre {first_date} et {last_date}, sur {n_active_markets} marchés répartis dans {n_departments} départements. Tous les prix sont des prix réellement relevés, jamais estimés.

## 3. Les données utilisées pour prévoir
Avant 2019, le suivi est clairsemé, et en 2017 et 2018 le relevé national a été interrompu. Ces périodes sont montrées pour information, mais jamais comblées ni utilisées pour entraîner ou tester les prévisions. Les prévisions reposent sur la période {model_window_start} à {model_window_end} ({n_model_months} mois). Un marché est dit [bien suivi] s'il compte au moins {tier1_min_months} mois de relevés sur {n_model_months}. Cela donne {n_markets_maize} marchés pour le maïs blanc, {n_markets_tomato} pour la tomate et {n_markets_yam} pour l'igname blanche. Les mois sans relevé ne sont jamais remplis : les courbes s'interrompent.
L'igname existe sous deux variétés dont les prix diffèrent nettement (écart moyen de {yam_variety_gap} XOF/kg). Le site ne prévoit que l'igname blanche (kokoro).

## 4. Comment les prévisions sont faites
Pour chaque produit et chaque horizon (1, 2 et 3 mois), on compare des méthodes simples (reprendre le dernier prix connu, ou appliquer le rythme saisonnier habituel) à des modèles plus élaborés ({models_list_plain}). Le choix se fait sur une période de validation ({validation_start} à {validation_end}). Un test final ({test_start} à {test_end}) n'est regardé qu'une seule fois, après avoir figé le choix. Si un modèle élaboré ne fait pas mieux qu'une méthode simple, c'est la méthode simple qui est conservée. Les [fourchettes à 80 % et 90 %] se déduisent des erreurs passées.

## 5. Ce que montre le test final
{results_table}
(One row per product and horizon: method in plain words, average error in %, gain over the best simple method, share of observed prices inside the 80 % range, reliability label.)
{sentence_gain_summary}
(Computed: for which products and horizons a model beats the simple method, and by how much.)
Dans {n_cases_other_better} cas sur {n_cases_total}, un autre modèle aurait fait mieux que celui retenu sur le test final : choisir sur la validation comporte une part de hasard.
Ajouter la pluie et la température (NASA POWER) n'a pas amélioré les prévisions (variation de l'erreur : {weather_effect_range}). Ces données ne sont donc pas utilisées.

## 6. Ce que ces prévisions ne savent pas faire
- Elles ne prévoient pas les chocs soudains (sécheresse, coupure de route, hausse du carburant, fermeture de frontière).
- Elles ne vont pas au-delà de 3 mois.
- Elles ne concernent que les marchés bien suivis et les prix de détail.
- Les prix sont nominaux : l'inflation n'est pas retirée.
- Elles sont moins fiables pour la tomate, dont les prix changent brutalement d'un mois à l'autre.
{known_limits}
(Computed: every product and horizon whose reliability label is not "calibrated", in plain words, with the figures.)

## 7. Transparence
Le code, les tableaux et le protocole sont publics : {github_url}. Tous les chiffres de ce site sont produits par des scripts, jamais saisis à la main. Chaque phase du projet a été relue de façon indépendante par un second agent, qui a recalculé les résultats.
[OPTIONAL, the author decides] Ce projet personnel de Brian Codjia, étudiant en informatique à l'IFRI (Abomey-Calavi, Bénin), a été réalisé avec des agents d'intelligence artificielle sous sa supervision.

## 8. Sources et attribution
{attribution_text}
(Exact text from docs/DECISIONS.md, Decision 5.)
NASA POWER (domaine public) et FAOSTAT (CC BY 4.0) sont cités comme sources de contexte. Ce site est un projet indépendant : il n'est affilié ni au PAM, ni à l'ONASA, ni à l'INStaD.

## 9. Mises à jour
Les données sont arrêtées au {as_of_date}. Les prévisions couvrent {first_forecast_month} à {last_forecast_month}. Cette date est rappelée sur chaque page de prévisions.
