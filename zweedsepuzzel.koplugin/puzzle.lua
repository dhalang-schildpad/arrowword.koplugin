--[[--
Puzzelmodel: laadt een puzzel uit het JSON-formaat (zie puzzles/FORMAT.md) en
houdt de spelstatus bij (ingevulde letters, huidig woord, cursor).

Geen KOReader-afhankelijkheden, zodat dit los te testen is met luajit.
]]

local Puzzle = {}
Puzzle.__index = Puzzle

-- stap per pijlrichting: {dx, dy} van de letters
local DIR_STEP = { R = { 1, 0 }, D = { 0, 1 }, RD = { 0, 1 }, DR = { 1, 0 } }

--- Splits een antwoord in cellen; IJ is één cel.
function Puzzle.splitLetters(antwoord)
    local out, i = {}, 1
    while i <= #antwoord do
        if antwoord:sub(i, i + 1) == "IJ" then
            out[#out + 1] = "IJ"
            i = i + 2
        else
            out[#out + 1] = antwoord:sub(i, i)
            i = i + 1
        end
    end
    return out
end

local function key(x, y)
    return y * 1000 + x
end
Puzzle.key = key

--- Maakt een puzzel uit een gedecodeerde JSON-tabel.
function Puzzle.new(data)
    local self = setmetatable({}, Puzzle)
    self.data = data
    self.w, self.h = data.w, data.h
    self.titel = data.titel or "Zweedse puzzel"
    self.sterren = data.sterren
    self.cells = data.cellen
    self.words = {}
    self.cell_words = {}
    for _, wd in ipairs(data.woorden) do
        local step = DIR_STEP[wd.dir] or DIR_STEP.R
        local letters = Puzzle.splitLetters(wd.antwoord)
        local cells = {}
        local x, y = wd.start[1], wd.start[2]
        for i = 1, #letters do
            cells[i] = { x = x, y = y }
            x, y = x + step[1], y + step[2]
        end
        local word = {
            id = wd.id, oms = wd.oms, antwoord = wd.antwoord, letters = letters,
            dir = wd.dir, van = { x = wd.van[1], y = wd.van[2] }, cells = cells,
            horizontal = step[1] == 1,
        }
        self.words[#self.words + 1] = word
        for _, c in ipairs(cells) do
            local k = key(c.x, c.y)
            self.cell_words[k] = self.cell_words[k] or {}
            table.insert(self.cell_words[k], word)
        end
    end
    -- leesvolgorde: op omschrijvingscel, horizontaal eerst
    table.sort(self.words, function(a, b)
        if a.van.y ~= b.van.y then return a.van.y < b.van.y end
        if a.van.x ~= b.van.x then return a.van.x < b.van.x end
        return a.horizontal and not b.horizontal
    end)
    for i, w in ipairs(self.words) do
        w.index = i
    end
    self.entered = {}
    self.wrong = {}
    self.current = self.words[1]
    self.cursor = 1
    self.n_letter_cells = 0
    for y = 0, self.h - 1 do
        for x = 0, self.w - 1 do
            if self:isLetter(x, y) then
                self.n_letter_cells = self.n_letter_cells + 1
            end
        end
    end
    return self
end

function Puzzle:cellAt(x, y)
    local row = self.cells[y + 1]
    return row and row[x + 1] or nil
end

function Puzzle:isLetter(x, y)
    local c = self:cellAt(x, y)
    return c ~= nil and c.t == "L"
end

function Puzzle:getEntered(x, y)
    return self.entered[key(x, y)]
end

function Puzzle:isWrong(x, y)
    return self.wrong[key(x, y)] == true
end

function Puzzle:currentCell()
    return self.current.cells[self.cursor]
end

function Puzzle:wordsAt(x, y)
    return self.cell_words[key(x, y)] or {}
end

function Puzzle:wordContains(word, x, y)
    for i, c in ipairs(word.cells) do
        if c.x == x and c.y == y then return i end
    end
    return nil
end

--- Selecteert een lettercel. Een tweede tik op de cursorcel wisselt van woord.
-- @return true als de selectie veranderd is
function Puzzle:selectCell(x, y)
    if not self:isLetter(x, y) then return false end
    local words = self:wordsAt(x, y)
    if #words == 0 then return false end
    local cur = self:currentCell()
    local target
    if cur.x == x and cur.y == y and #words > 1 then
        -- wissel naar het andere woord door deze cel
        for i, w in ipairs(words) do
            if w == self.current then
                target = words[i % #words + 1]
                break
            end
        end
        target = target or words[1]
    elseif self:wordContains(self.current, x, y) then
        target = self.current
    else
        target = words[1]
        for _, w in ipairs(words) do
            if w.horizontal then target = w end
        end
    end
    self.current = target
    self.cursor = self:wordContains(target, x, y)
    return true
end

function Puzzle:selectWord(word, cursor)
    self.current = word
    self.cursor = cursor or 1
end

function Puzzle:nextWord(delta)
    local n = #self.words
    local i = (self.current.index - 1 + delta) % n + 1
    self:selectWord(self.words[i], 1)
end

--- Zet een letter in de cursorcel en schuift de cursor door.
-- @return lijst van gewijzigde cellen
function Puzzle:enterLetter(letter)
    local c = self:currentCell()
    local k = key(c.x, c.y)
    self.entered[k] = letter
    self.wrong[k] = nil
    local changed = { { x = c.x, y = c.y } }
    if self.cursor < #self.current.cells then
        self.cursor = self.cursor + 1
        local nc = self:currentCell()
        changed[#changed + 1] = { x = nc.x, y = nc.y }
    end
    return changed
end

--- Wist de cursorcel, of gaat een cel terug als die al leeg is.
function Puzzle:backspace()
    local c = self:currentCell()
    local k = key(c.x, c.y)
    local changed = { { x = c.x, y = c.y } }
    if self.entered[k] == nil and self.cursor > 1 then
        self.cursor = self.cursor - 1
        c = self:currentCell()
        k = key(c.x, c.y)
        changed[#changed + 1] = { x = c.x, y = c.y }
    end
    self.entered[k] = nil
    self.wrong[k] = nil
    return changed
end

--- Vult de cursorcel met de juiste letter.
function Puzzle:hint()
    return self:enterLetter(self.current.letters[self.cursor])
end

--- Markeert foute letters. @return aantal fout, aantal leeg
function Puzzle:check()
    local n_wrong, n_empty = 0, 0
    local gezien = {}
    self.wrong = {}
    for _, w in ipairs(self.words) do
        for i, c in ipairs(w.cells) do
            local k = key(c.x, c.y)
            if not gezien[k] then
                gezien[k] = true
                local e = self.entered[k]
                if e == nil then
                    n_empty = n_empty + 1
                elseif e ~= w.letters[i] then
                    self.wrong[k] = true
                    n_wrong = n_wrong + 1
                end
            end
        end
    end
    return n_wrong, n_empty
end

function Puzzle:isSolved()
    for _, w in ipairs(self.words) do
        for i, c in ipairs(w.cells) do
            if self.entered[key(c.x, c.y)] ~= w.letters[i] then
                return false
            end
        end
    end
    return true
end

function Puzzle:countFilled()
    local n = 0
    for _ in pairs(self.entered) do n = n + 1 end
    return n
end

--- Voortgang als serialiseerbare tabel.
function Puzzle:getProgress()
    local letters = {}
    for k, v in pairs(self.entered) do
        letters[tostring(k)] = v
    end
    return { letters = letters, klaar = self:isSolved(), woord = self.current.index, cursor = self.cursor }
end

function Puzzle:setProgress(p)
    if not p then return end
    self.entered = {}
    for k, v in pairs(p.letters or {}) do
        self.entered[tonumber(k)] = v
    end
    if p.woord and self.words[p.woord] then
        self.current = self.words[p.woord]
        self.cursor = math.min(p.cursor or 1, #self.current.cells)
    end
end

return Puzzle
