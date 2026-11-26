V8.0.5 EXPERIMENTÁLNÍ – aktualizace nad V7.9 (obsahuje i základ V8.0).
Nahrajte Python soubory do kořene a workflow do .github/workflows.
Predikce jsou pouze v predictions.json, grafika ani e-mail se nemění.
Model: Elo, Poisson (remíza rozdělena napůl), logistická regrese, histogramový boosting, váhy podle validačního Brier skóre, logistická kalibrace a oddělený test.
Historie až 10 sezon, chronologické denní dávky UTC. Výchozí režim používá výsledky, góly, formu, odpočinek, domácí/venkovní formu a H2H.
Volitelná proměnná NHL_PREDICTION_DETAIL_GAMES (výchozí 0) povolí historické boxscore; může být velmi pomalá. Střely, brankářské a hráčské údaje jsou pouze historické týmové proxy, nikoli potvrzená sestava. PP/PK, vhazování a zranění nejsou zatím napojeny. Chybějící sloupce se vyřadí z tréninku.
Není implementována trvalá databáze, cache, optimalizace Elo parametrů, evidence živých predikcí ani grafická integrace. Živé API a celý workflow nebyly ověřeny.
