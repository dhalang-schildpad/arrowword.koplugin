-- Test van zweedsepuzzel.koplugin/puzzle.lua zonder KOReader-UI.
-- Draaien: tools/test.sh (gebruikt de luajit en json.lua uit de emulatorbuild).
local json = require("json")
local Puzzle = require("puzzle")

local function readFile(path)
    local f = assert(io.open(path, "r"))
    local s = f:read("*a")
    f:close()
    return s
end

local n_ok, n_fail = 0, 0
local function check(cond, msg)
    if cond then n_ok = n_ok + 1 else n_fail = n_fail + 1; print("FOUT: " .. msg) end
end

local p = Puzzle.new(json.decode(readFile(arg[1] or "puzzles/test-klein.json")))

check(#p.words == 5, "5 woorden")
check(p.words[1].antwoord == "RAAM", "eerste woord in leesvolgorde is RAAM (omschrijvingscel (1,0)), kreeg " .. p.words[1].antwoord)
check(p.n_letter_cells == 13, "13 lettercellen")
check(#Puzzle.splitLetters("IJS") == 2 and Puzzle.splitLetters("IJS")[1] == "IJ", "IJ is één cel")

-- selectie: horizontaal heeft voorrang, tweede tik wisselt
check(p:selectCell(1, 1), "lettercel selecteren")
check(p.current.antwoord == "REEDS" and p.cursor == 1, "horizontaal eerst")
p:selectCell(1, 1)
check(p.current.antwoord == "RAAM", "tweede tik wisselt naar verticaal")
p:selectCell(1, 1)
check(p.current.antwoord == "REEDS", "derde tik wisselt terug")
check(not p:selectCell(0, 0), "omschrijvingscel niet selecteerbaar")

-- invoer
p:enterLetter("R"); p:enterLetter("E")
check(p:getEntered(1, 1) == "R" and p:getEntered(2, 1) == "E", "letters ingevuld")
check(p.cursor == 3, "cursor schuift door")
p:backspace()
check(p:getEntered(2, 1) == nil and p.cursor == 2, "wis op lege cel gaat terug en wist de vorige")
p:backspace()
check(p:getEntered(1, 1) == nil and p.cursor == 1, "wis op lege cel gaat weer terug")
p:enterLetter("R")

-- controleren
p:selectCell(2, 1); p:enterLetter("X")
local n_wrong, n_empty = p:check()
check(n_wrong == 1 and n_empty == 11, "1 fout, 11 leeg; kreeg " .. n_wrong .. "/" .. n_empty)
check(p:isWrong(2, 1), "foute cel gemarkeerd")
p:selectCell(2, 1); p:enterLetter("E")
check(not p:isWrong(2, 1), "markering weg na correctie")

-- hint en oplossen
for _, w in ipairs(p.words) do
    p:selectWord(w, 1)
    for _ = 1, #w.cells do p:hint() end
end
check(p:isSolved(), "alles via hints ingevuld is opgelost")

-- voortgang bewaren en herstellen
local prog = p:getProgress()
local q = Puzzle.new(json.decode(readFile(arg[1] or "puzzles/test-klein.json")))
q:setProgress(prog)
check(q:isSolved() and q.current.index == p.current.index, "voortgang hersteld")

-- woordnavigatie loopt rond
q:selectWord(q.words[#q.words], 1); q:nextWord(1)
check(q.current.index == 1, "nextWord loopt rond")

print(string.format("%d ok, %d fout", n_ok, n_fail))
os.exit(n_fail == 0 and 0 or 1)
