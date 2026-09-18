--[[--
Puzzle model: loads a puzzle from the JSON format (see docs/PUZZLE_FORMAT.md)
and tracks the game state (entered letters, current word, cursor).

No KOReader dependencies, so it can be tested with plain luajit.
]]

local Puzzle = {}
Puzzle.__index = Puzzle

-- step per arrow direction: {dx, dy} of the letters
local DIR_STEP = { R = { 1, 0 }, D = { 0, 1 }, RD = { 0, 1 }, DR = { 1, 0 } }

-- letters that occupy a single cell although they are written with two characters
local DIGRAPHS = { nl = { "IJ" } }

--- Splits an answer into cells; language digraphs (Dutch IJ) take one cell.
function Puzzle.splitLetters(answer, lang)
    local digraphs = DIGRAPHS[lang or "nl"] or {}
    local out, i = {}, 1
    while i <= #answer do
        local taken = false
        for __, d in ipairs(digraphs) do
            if answer:sub(i, i + #d - 1) == d then
                out[#out + 1] = d
                i = i + #d
                taken = true
                break
            end
        end
        if not taken then
            out[#out + 1] = answer:sub(i, i)
            i = i + 1
        end
    end
    return out
end

local function key(x, y)
    return y * 1000 + x
end
Puzzle.key = key

--- Builds a puzzle from a decoded JSON table (format version 2).
function Puzzle.new(data)
    assert(data.version == 2, "unsupported puzzle format version")
    local self = setmetatable({}, Puzzle)
    self.data = data
    self.w, self.h = data.w, data.h
    self.lang = data.lang or "nl"
    self.title = data.title or "Arrowword"
    self.stars = data.stars
    self.cells = data.cells
    self.words = {}
    self.cell_words = {}
    for __, wd in ipairs(data.words) do
        local step = DIR_STEP[wd.dir] or DIR_STEP.R
        local letters = Puzzle.splitLetters(wd.answer, self.lang)
        local cells = {}
        local x, y = wd.start[1], wd.start[2]
        for i = 1, #letters do
            cells[i] = { x = x, y = y }
            x, y = x + step[1], y + step[2]
        end
        local word = {
            id = wd.id, clue = wd.clue, answer = wd.answer, letters = letters,
            dir = wd.dir, from = { x = wd.from[1], y = wd.from[2] }, cells = cells,
            horizontal = step[1] == 1,
        }
        self.words[#self.words + 1] = word
        for __c, c in ipairs(cells) do
            local k = key(c.x, c.y)
            self.cell_words[k] = self.cell_words[k] or {}
            table.insert(self.cell_words[k], word)
        end
    end
    -- reading order: by clue cell, horizontal first
    table.sort(self.words, function(a, b)
        if a.from.y ~= b.from.y then return a.from.y < b.from.y end
        if a.from.x ~= b.from.x then return a.from.x < b.from.x end
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

--- A cheap checksum of the puzzle content, stored with the progress so that
-- progress is ignored when a file is replaced by a different puzzle.
function Puzzle:fingerprint()
    local sum = self.w * 31 + self.h
    for __, w in ipairs(self.words) do
        for i = 1, #w.answer do
            sum = (sum * 33 + w.answer:byte(i)) % 1000000007
        end
    end
    return sum
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

--- Word whose clue sits in clue cell (x, y); a second tap on a split cell
-- switches to its other clue.
function Puzzle:wordFromClueCell(x, y)
    local found = {}
    for __, w in ipairs(self.words) do
        if w.from.x == x and w.from.y == y then
            found[#found + 1] = w
        end
    end
    if #found == 0 then return nil end
    for i, w in ipairs(found) do
        if w == self.current then
            return found[i % #found + 1]
        end
    end
    return found[1]
end

--- Selects a cell. A letter cell selects a word through it (a second tap on
-- the cursor cell switches word); a clue cell selects the word it describes.
-- @return true if the selection changed
function Puzzle:selectCell(x, y)
    local cell = self:cellAt(x, y)
    if cell and cell.t == "C" then
        local w = self:wordFromClueCell(x, y)
        if not w then return false end
        self.current, self.cursor = w, 1
        return true
    end
    if not self:isLetter(x, y) then return false end
    local words = self:wordsAt(x, y)
    if #words == 0 then return false end
    local cur = self:currentCell()
    local target
    if cur.x == x and cur.y == y and #words > 1 then
        -- switch to the other word through this cell
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
        for __, w in ipairs(words) do
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

--- Puts a letter in the cursor cell and advances the cursor.
-- @return list of changed cells
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

--- Clears the cursor cell, or steps back first when it is already empty.
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

--- Fills the cursor cell with the correct letter.
function Puzzle:hint()
    return self:enterLetter(self.current.letters[self.cursor])
end

--- Marks wrong letters. @return number wrong, number empty
function Puzzle:check()
    local n_wrong, n_empty = 0, 0
    local seen = {}
    self.wrong = {}
    for __, w in ipairs(self.words) do
        for i, c in ipairs(w.cells) do
            local k = key(c.x, c.y)
            if not seen[k] then
                seen[k] = true
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
    for __, w in ipairs(self.words) do
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
    for __ in pairs(self.entered) do n = n + 1 end
    return n
end

--- Progress as a serialisable table.
function Puzzle:getProgress()
    local letters = {}
    for k, v in pairs(self.entered) do
        letters[tostring(k)] = v
    end
    return {
        letters = letters, done = self:isSolved(), word = self.current.index,
        cursor = self.cursor, fingerprint = self:fingerprint(),
    }
end

--- Restores progress; ignored when it belongs to a different puzzle.
function Puzzle:setProgress(p)
    if not p or p.fingerprint ~= self:fingerprint() then return end
    self.entered = {}
    for k, v in pairs(p.letters or {}) do
        self.entered[tonumber(k)] = v
    end
    if p.word and self.words[p.word] then
        self.current = self.words[p.word]
        self.cursor = math.min(p.cursor or 1, #self.current.cells)
    end
end

return Puzzle
