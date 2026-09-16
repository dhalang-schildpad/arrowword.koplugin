# Prompt voor het schrijven van omschrijvingen (Gemini, Claude of een ander model)

Werkwijze per batch:

1. Kopieer de prompt hieronder (alles tussen de lijnen) in een nieuw gesprek.
2. Plak daaronder de inhoud van `batch-NNN-in.tsv`.
3. Sla het antwoord op als `generator/data/omschrijvingen/batch-NNN.tsv`
   (alleen de regels met woorden, zonder code-hekjes of uitleg).
4. Controleer: `python3 generator/omschrijvingen.py check generator/data/omschrijvingen/batch-NNN.tsv`
   Plak eventuele foutmeldingen terug in het gesprek en vraag om alleen die regels te herstellen.
5. Als alles OK is: `python3 generator/omschrijvingen.py merge`, daarna puzzels genereren.

---

Je schrijft omschrijvingen voor Nederlandse Zweedse puzzels, in de stijl van Denksport.

Hieronder staat een lijst met per regel: WOORD | huidige omschrijving. Het woord is het antwoord (hoofdletters, IJ telt als één letter). De huidige omschrijving is een automatisch ingekorte woordenboekdefinitie en is vaak slecht; gebruik hem alleen als hint voor de betekenis en negeer hem als hij onzin is.

Geef voor ELK woord, in dezelfde volgorde, precies één regel in dit formaat:

WOORD | omschrijving 1 | omschrijving 2 | omschrijving 3

Twee omschrijvingen is het minimum, drie is beter. Zet alle regels in één codeblok, zonder kopregel en zonder toelichting.

Regels:
- Kort: liefst één of twee woorden. Maximaal 18 tekens, en geen enkel woord langer dan 9 tekens (de omschrijving wordt in een cel afgebroken op 2 regels van 9 tekens).
- Bij voorkeur een synoniem; anders een korte definitie of categorie ("Boom", "Rivier in Italië", "Muzieknoot", "Griekse letter").
- Grammaticaal passend: meervoud bij meervoud, verleden tijd bij verleden tijd, infinitief bij infinitief, bijvoeglijk naamwoord bij bijvoeglijk naamwoord. Een verbogen vorm omschrijf je als die vorm: LIEP -> "Wandelde".
- Afkortingen: als het antwoord een afkorting is (ENZ, NL, EHBO), eindigt de omschrijving op "(afk.)" of is zelf een afkorting.
- Functiewoorden krijgen een grammaticale omschrijving: DE -> "Lidwoord", EN -> "Voegwoord", IK -> "Persoonlijk vnw.", TE -> "Voorzetsel".
- Verschillende betekenissen benutten: BANK -> "Zitmeubel" | "Geldinstelling".
- Nooit de stam van het antwoord in de omschrijving (niet "Lopen" bij LOOP). Geen lidwoord vooraan ("Lidwoord", niet "Een lidwoord"). Begin met een hoofdletter, geen punt aan het einde.
- Nederlands-Nederlands; geen uitsluitend Vlaamse betekenis als enige omschrijving.
- Hooguit 1 op de 20 woorden een woordspeling, dan met een "?" erachter.

De lijst:
