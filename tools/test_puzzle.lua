-- Tests for puzzle.lua without the KOReader UI.
-- Run with tools/test.sh (uses luajit and json.lua from the emulator build).
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
    if cond then n_ok = n_ok + 1 else n_fail = n_fail + 1; print("FAIL: " .. msg) end
end

local path = arg[1] or "tools/fixtures/test-small.json"
local p = Puzzle.new(json.decode(readFile(path)))

check(#p.words == 5, "5 words")
check(p.words[1].answer == "RAAM", "first word in reading order is RAAM (clue cell (1,0)), got " .. p.words[1].answer)
check(p.n_letter_cells == 13, "13 letter cells")
check(#Puzzle.splitLetters("IJS", "nl") == 2 and Puzzle.splitLetters("IJS", "nl")[1] == "IJ", "Dutch IJ is one cell")
check(#Puzzle.splitLetters("IJS", "en") == 3, "no digraphs in English")

-- selection: horizontal first, a second tap switches
check(p:selectCell(1, 1), "select a letter cell")
check(p.current.answer == "REEDS" and p.cursor == 1, "horizontal first")
p:selectCell(1, 1)
check(p.current.answer == "RAAM", "second tap switches to vertical")
p:selectCell(1, 1)
check(p.current.answer == "REEDS", "third tap switches back")
check(not p:selectCell(0, 0), "empty cell is not selectable")
check(p:selectCell(3, 0) and p.current.answer == "ELS" and p.cursor == 1, "tapping a clue cell selects its word")

-- input
p:selectCell(1, 1)
if p.current.answer ~= "REEDS" then p:selectCell(1, 1) end
p:enterLetter("R"); p:enterLetter("E")
check(p:getEntered(1, 1) == "R" and p:getEntered(2, 1) == "E", "letters entered")
check(p.cursor == 3, "cursor advances")
p:backspace()
check(p:getEntered(2, 1) == nil and p.cursor == 2, "backspace on an empty cell steps back and clears")
p:backspace()
check(p:getEntered(1, 1) == nil and p.cursor == 1, "backspace steps back again")
p:enterLetter("R")

-- checking
p:selectCell(2, 1); p:enterLetter("X")
local n_wrong, n_empty = p:check()
check(n_wrong == 1 and n_empty == 11, "1 wrong, 11 empty; got " .. n_wrong .. "/" .. n_empty)
check(p:isWrong(2, 1), "wrong cell marked")
p:selectCell(2, 1); p:enterLetter("E")
check(not p:isWrong(2, 1), "mark cleared after correction")

-- hints and solving
for _, w in ipairs(p.words) do
    p:selectWord(w, 1)
    for _ = 1, #w.cells do p:hint() end
end
check(p:isSolved(), "everything filled by hints is solved")

-- saving and restoring progress
local prog = p:getProgress()
local q = Puzzle.new(json.decode(readFile(path)))
q:setProgress(prog)
check(q:isSolved() and q.current.index == p.current.index, "progress restored")
prog.fingerprint = prog.fingerprint + 1
local r = Puzzle.new(json.decode(readFile(path)))
r:setProgress(prog)
check(r:countFilled() == 0, "progress of a different puzzle is ignored")

-- word navigation wraps around
q:selectWord(q.words[#q.words], 1); q:nextWord(1)
check(q.current.index == 1, "nextWord wraps around")

print(string.format("%d ok, %d failed", n_ok, n_fail))
os.exit(n_fail == 0 and 0 or 1)
