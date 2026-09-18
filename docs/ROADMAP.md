# Roadmap

The project's priority is puzzle quality. Items are roughly in order within each section.

## Puzzles and generator

- **Fewer empty cells, more crossings.** Today about 65% of cells are letters, 10 to 15% are empty, and half of the letters are crossed only once. Printed arrowwords have almost no empty cells. Ideas: a larger filler list, penalties for empty cells, fewer three-letter words.
- **Separate grid size from difficulty**, so small screens can have hard puzzles: device classes ("large" 13 x 14, "compact" 10 x 11) next to the star levels.
- **Review pass over the clues.** The hand-written clues were checked mechanically and sampled by hand; obscure short words from the tail of the frequency list need a human eye or removal.
- **Clue difficulty levels**, so easy puzzles get literal synonyms and hard ones get indirect clues.
- **Bent arrows** (`RD`, `DR`) and picture-free variants common in printed puzzles.
- **Unique pack names and releases.** Packs as GitHub Releases, named by language, level and number.

## Languages

- **English** word list, fillers, clues and prompt. See CONTRIBUTING.md, "Adding a language".
- German is an obvious third: arrowwords ("Schwedenrätsel") are very popular there.

## Plugin

- Solution-word bar under the grid that fills in as numbered cells are solved, and a finished screen.
- Confirmation before a hint.
- Use the page-turn buttons for previous and next word.
- Optional: reveal a whole word, clear the puzzle, show elapsed time.

## Project

- Device reports beyond the Kobo Forma (see DEVICES.md).
- A small command-line or web front end for generating packs.
- Make the repository public once the above has settled.

The original Dutch planning notes, with the research behind the early decisions, are kept in `docs/history/`.
