--[[--
Game view: paints the grid, the clue bar and the letter bar directly onto
the Blitbuffer and handles taps and swipes.
]]

local Blitbuffer = require("ffi/blitbuffer")
local Device = require("device")
local Font = require("ui/font")
local Geom = require("ui/geometry")
local GestureRange = require("ui/gesturerange")
local InfoMessage = require("ui/widget/infomessage")
local InputContainer = require("ui/widget/container/inputcontainer")
local RenderText = require("ui/rendertext")
local Size = require("ui/size")
local UIManager = require("ui/uimanager")
local logger = require("logger")
local _ = require("i18n")
local T = require("ffi/util").template
local Screen = Device.screen

local KEY_ROWS = {
    { "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P" },
    { "A", "S", "D", "F", "G", "H", "J", "K", "L" },
    { "Z", "X", "C", "V", "B", "N", "M", "DEL" },
}
-- language-specific extra keys, appended to the second row
local EXTRA_KEYS = { nl = { "IJ" } }

local GameView = InputContainer:extend{
    puzzle = nil,        -- Puzzle
    on_close = nil,      -- callback(puzzle)
    on_progress = nil,   -- callback(puzzle), after changes
}

-- Font:getFace scales by DPI; we work in pixels.
local function faceForPixels(px, bold)
    local scale = Screen:scaleBySize(1000) / 1000
    return Font:getFace(bold and "tfont" or "cfont", math.max(6, math.floor(px / scale)))
end

local function textWidth(face, text)
    return RenderText:sizeUtf8Text(0, math.huge, face, text, true, false).x
end

--- Text centred in a box.
local function drawCentered(bb, x, y, w, h, face, text, color, bold)
    local tw = textWidth(face, text)
    local fh, asc = face.ftsize:getHeightAndAscender()
    local tx = x + math.floor((w - tw) / 2)
    local ty = y + math.floor((h - fh) / 2 + asc)
    RenderText:renderUtf8Text(bb, tx, ty, face, text, true, bold or false, color or Blitbuffer.COLOR_BLACK, w)
end

--- Breaks text into lines that fit `width`. A "\n" in the text forces a
-- line break; otherwise lines break on spaces.
-- @return lines, or nil if it does not fit in max_lines
local function wrap(face, text, width, max_lines, allow_hyphen)
    local lines = {}
    for alinea in (text .. "\n"):gmatch("(.-)\n") do
        local line
        for word in alinea:gmatch("%S+") do
            local proef = line and (line .. " " .. word) or word
            if textWidth(face, proef) <= width then
                line = proef
            else
                if line then lines[#lines + 1] = line end
                -- word too long: hyphenate (only when allowed)
                if not allow_hyphen and textWidth(face, word) > width then return nil end
                while textWidth(face, word) > width do
                    local n = #word - 1
                    while n > 1 and textWidth(face, word:sub(1, n) .. "-") > width do
                        n = n - 1
                    end
                    if n < 2 then return nil end
                    lines[#lines + 1] = word:sub(1, n) .. "-"
                    word = word:sub(n + 1)
                end
                line = word
            end
        end
        if line then lines[#lines + 1] = line end
    end
    if #lines > max_lines then return nil end
    return lines
end

--- Arrow with its tip at (tx, ty), direction "R" or "D"; `size` is the length of the head.
local function drawArrow(bb, tx, ty, dir, size, color)
    local half = math.max(2, math.floor(size / 2))
    local thick = math.max(2, math.floor(size / 4))
    if dir == "R" then
        bb:paintRect(tx - size * 2, ty - math.floor(thick / 2), size * 2 - half, thick, color)
        for i = 0, half do
            bb:paintRect(tx - half + i, ty - (half - i), 1, 2 * (half - i) + 1, color)
        end
    else
        bb:paintRect(tx - math.floor(thick / 2), ty - size * 2, thick, size * 2 - half, color)
        for i = 0, half do
            bb:paintRect(tx - (half - i), ty - half + i, 2 * (half - i) + 1, 1, color)
        end
    end
end

function GameView:init()
    local W, H = Screen:getWidth(), Screen:getHeight()
    -- key rows for this puzzle's language
    self.key_rows = {}
    for i, row in ipairs(KEY_ROWS) do
        self.key_rows[i] = { unpack(row) }
    end
    for __, k in ipairs(EXTRA_KEYS[self.puzzle.lang or ""] or {}) do
        table.insert(self.key_rows[2], k)
    end
    self.dimen = Geom:new{ x = 0, y = 0, w = W, h = H }
    self.covers_fullscreen = true

    local m = Size.margin.default
    self.margin = m
    self.title_h = Screen:scaleBySize(44)
    self.clue_h = Screen:scaleBySize(54)
    self.key_h = Screen:scaleBySize(40)
    self.keys_h = self.key_h * #self.key_rows + m

    local p = self.puzzle
    local grid_avail_h = H - self.title_h - self.clue_h - self.keys_h - 3 * m
    self.cell = math.floor(math.min((W - 2 * m) / p.w, grid_avail_h / p.h))
    self.grid_x = math.floor((W - self.cell * p.w) / 2)
    self.grid_y = self.title_h + m
    self.grid_w = self.cell * p.w
    self.grid_h = self.cell * p.h
    self.clue_y = self.grid_y + self.grid_h + m
    self.keys_y = H - self.keys_h
    self.key_w = math.floor((W - 2 * m) / #self.key_rows[1])
    self.row_x = {}
    for i, row in ipairs(self.key_rows) do
        self.row_x[i] = math.floor((W - self.key_w * #row) / 2)
    end
    -- previous/next word buttons in the clue bar
    local aw = Screen:scaleBySize(44)
    self.prev_rect = Geom:new{ x = m, y = self.clue_y + Screen:scaleBySize(4), w = aw, h = self.clue_h - Screen:scaleBySize(8) }
    self.next_rect = Geom:new{ x = W - m - aw, y = self.clue_y + Screen:scaleBySize(4), w = aw, h = self.clue_h - Screen:scaleBySize(8) }

    self.letter_face = faceForPixels(self.cell * 0.62, true)
    self.small_face = faceForPixels(self.cell * 0.22)
    -- clues: descending series of font sizes, from ~0.27 of a cell down to very small
    self.clue_faces = {}
    local scale = Screen:scaleBySize(1000) / 1000
    local groot = math.max(6, math.floor(self.cell * 0.27 / scale))
    for n = groot, 4, -1 do
        self.clue_faces[#self.clue_faces + 1] = Font:getFace("cfont", n)
    end
    self.ui_face = Font:getFace("cfont", 20)
    self.title_face = Font:getFace("tfont", 22)
    self.key_face = Font:getFace("tfont", 24)
    self.key_small_face = Font:getFace("cfont", 15)

    -- buttons in the title bar (right to left)
    self.buttons = {}
    local bx = W - m
    for __, b in ipairs({ { id = "close", text = _("Close") }, { id = "check", text = _("Check") }, { id = "hint", text = _("Hint") } }) do
        local bw = textWidth(self.ui_face, b.text) + Screen:scaleBySize(24)
        bx = bx - bw
        b.rect = Geom:new{ x = bx, y = Screen:scaleBySize(4), w = bw, h = self.title_h - Screen:scaleBySize(8) }
        self.buttons[#self.buttons + 1] = b
        bx = bx - Screen:scaleBySize(6)
    end
    self.title_max_w = bx - m

    self.ges_events = {
        Tap = { GestureRange:new{ ges = "tap", range = self.dimen } },
        Swipe = { GestureRange:new{ ges = "swipe", range = self.dimen } },
    }
    self.unsaved = 0

    logger.info("arrowword: screen", W, H, "cell", self.cell)
    if os.getenv("AW_SCRIPT") then
        self:runDevScript(os.getenv("AW_SCRIPT"))
    end
end

--- Development aid: runs a list of actions separated by ";".
-- Actions: cell:x,y  key:A  swipe:west  button:check  shot:/path.png  wait:2
function GameView:runDevScript(script)
    local t = 4 -- wait for the first paint
    for action in script:gmatch("[^;]+") do
        local name, arg = action:match("^%s*(%w+):?(.-)%s*$")
        if name == "wait" then
            t = t + (tonumber(arg) or 1)
        else
            t = t + 0.4
            UIManager:scheduleIn(t, function()
                logger.info("arrowword: script", name, arg)
                if name == "cell" then
                    local x, y = arg:match("(%d+),(%d+)")
                    local r = self:cellRect(tonumber(x), tonumber(y))
                    self:onTap(nil, { pos = { x = r.x + r.w / 2, y = r.y + r.h / 2 } })
                elseif name == "key" then
                    self:onKey(arg)
                elseif name == "swipe" then
                    self:onSwipe(nil, { direction = arg })
                elseif name == "button" then
                    self:onButton(arg)
                elseif name == "shot" then
                    logger.info("arrowword: screenshot", Screen:shot(arg))
                end
            end)
        end
    end
end

-- geometry ------------------------------------------------------------------

function GameView:cellRect(x, y)
    return Geom:new{ x = self.grid_x + x * self.cell, y = self.grid_y + y * self.cell, w = self.cell, h = self.cell }
end

function GameView:cellAtPos(px, py)
    if px < self.grid_x or py < self.grid_y or px >= self.grid_x + self.grid_w or py >= self.grid_y + self.grid_h then
        return nil
    end
    return math.floor((px - self.grid_x) / self.cell), math.floor((py - self.grid_y) / self.cell)
end

function GameView:keyAtPos(px, py)
    if py < self.keys_y then return nil end
    local row = math.floor((py - self.keys_y) / self.key_h) + 1
    if not self.key_rows[row] then return nil end
    local col = math.floor((px - self.row_x[row]) / self.key_w) + 1
    return self.key_rows[row][col]
end

function GameView:wordRect(word)
    local first, last = word.cells[1], word.cells[#word.cells]
    local r = self:cellRect(first.x, first.y)
    local r2 = self:cellRect(last.x, last.y)
    return Geom:new{ x = r.x, y = r.y, w = r2.x + r2.w - r.x, h = r2.y + r2.h - r.y }
end

function GameView:clueRect()
    return Geom:new{ x = 0, y = self.clue_y, w = self.dimen.w, h = self.clue_h }
end

-- painting ------------------------------------------------------------------

function GameView:paintTo(bb, x, y)
    local W, H = self.dimen.w, self.dimen.h
    bb:paintRect(0, 0, W, H, Blitbuffer.COLOR_WHITE)
    self:paintTitle(bb)
    self:paintGrid(bb)
    self:paintClue(bb)
    self:paintKeys(bb)
end

function GameView:paintTitle(bb)
    local p = self.puzzle
    local title_text = p.title
    if p.stars then
        title_text = title_text .. "  " .. string.rep("★", p.stars)
    end
    local fh, asc = self.title_face.ftsize:getHeightAndAscender()
    local ty = math.floor((self.title_h - fh) / 2 + asc)
    RenderText:renderUtf8Text(bb, self.margin, ty, self.title_face, title_text, true, false, Blitbuffer.COLOR_BLACK, self.title_max_w)
    for __, b in ipairs(self.buttons) do
        bb:paintBorder(b.rect.x, b.rect.y, b.rect.w, b.rect.h, Size.border.button, Blitbuffer.COLOR_BLACK, Size.radius.button)
        drawCentered(bb, b.rect.x, b.rect.y, b.rect.w, b.rect.h, self.ui_face, b.text)
    end
    bb:paintRect(0, self.title_h - Size.line.medium, self.dimen.w, Size.line.medium, Blitbuffer.COLOR_BLACK)
end

function GameView:paintGrid(bb)
    local p = self.puzzle
    for y = 0, p.h - 1 do
        for x = 0, p.w - 1 do
            self:paintCell(bb, x, y)
        end
    end
    bb:paintBorder(self.grid_x - 1, self.grid_y - 1, self.grid_w + 2, self.grid_h + 2, Size.border.thick, Blitbuffer.COLOR_BLACK)
end

function GameView:paintCell(bb, x, y)
    local p = self.puzzle
    local c = p:cellAt(x, y)
    local r = self:cellRect(x, y)
    local cur = p:currentCell()
    local fill = Blitbuffer.COLOR_WHITE
    if c.t == "X" then
        fill = Blitbuffer.COLOR_GRAY_B
    elseif c.t == "L" then
        if p:wordContains(p.current, x, y) then
            fill = Blitbuffer.COLOR_GRAY_E
        end
    end
    bb:paintRect(r.x, r.y, r.w, r.h, fill)
    bb:paintBorder(r.x, r.y, r.w, r.h, Size.border.default, Blitbuffer.COLOR_BLACK)
    if c.t == "L" and cur.x == x and cur.y == y then
        -- cursor cell: thick inner border, clearly visible on e-ink
        bb:paintInnerBorder(r.x, r.y, r.w, r.h, math.max(3, math.floor(self.cell / 16)), Blitbuffer.COLOR_BLACK)
    end

    if c.t == "L" then
        local letter = p:getEntered(x, y)
        if letter then
            drawCentered(bb, r.x, r.y, r.w, r.h, self.letter_face, letter, Blitbuffer.COLOR_BLACK, true)
        end
        if c.n then
            local fh, asc = self.small_face.ftsize:getHeightAndAscender()
            RenderText:renderUtf8Text(bb, r.x + 3, r.y + 2 + asc - math.floor(fh * 0.15), self.small_face, tostring(c.n), true, false, Blitbuffer.COLOR_BLACK)
        end
        if p:isWrong(x, y) then
            local s = math.max(4, math.floor(self.cell / 7))
            bb:paintRect(r.x + r.w - s - 3, r.y + 3, s, s, Blitbuffer.COLOR_BLACK)
        end
    elseif c.t == "C" then
        self:paintClueCell(bb, r, c)
    end
end

function GameView:paintClueCell(bb, r, c)
    local n = #c.clues
    local pad = math.max(2, math.floor(self.cell * 0.04))
    local arrow = math.max(4, math.floor(self.cell * 0.10))
    local has_down = false
    for __, o in ipairs(c.clues) do
        if o.dir ~= "R" then has_down = true end
    end
    for i, o in ipairs(c.clues) do
        local hh = (n == 1) and r.h or math.floor(r.h / n)
        local hy = r.y + (i - 1) * hh
        if i == 2 then
            bb:paintRect(r.x, hy, r.w, Size.line.thin, Blitbuffer.COLOR_BLACK)
        end
        local avail_w = r.w - 2 * pad - (o.dir == "R" and math.floor(arrow * 1.5) or 0)
        -- the down arrow always sits against the bottom edge of the cell
        local is_last = (i == n)
        local avail_h = hh - 2 * pad - ((is_last and has_down) and arrow or 0)
        local max_lines = (n == 1) and 4 or 2
        -- first without hyphenation (a smaller font is preferred over a hyphen),
        -- then with hyphenation
        local lines, face, line_h
        for __, hyphen in ipairs({ false, true }) do
            for __f, f in ipairs(self.clue_faces) do
                local fh = f.ftsize:getHeightAndAscender()
                local lh = math.ceil(fh * 0.88)
                local fit_lines = math.min(max_lines, math.floor(avail_h / lh))
                if fit_lines >= 1 then
                    lines = wrap(f, o.text, avail_w, fit_lines, hyphen)
                    if lines then face, line_h = f, lh break end
                end
            end
            if lines then break end
        end
        if not lines then
            face = self.clue_faces[#self.clue_faces]
            line_h = math.ceil(face.ftsize:getHeightAndAscender() * 0.88)
            lines = { o.text }
            if os.getenv("AW_DEBUGLOG") then
                local f = io.open(os.getenv("AW_DEBUGLOG"), "a")
                f:write(string.format("does not fit: %q dir=%s n=%d avail_w=%d avail_h=%d line_h=%d max_lines=%d\n",
                    o.text, o.dir, n, avail_w, avail_h, line_h, max_lines))
                f:close()
            end
        end
        local _, asc = face.ftsize:getHeightAndAscender()
        local total = line_h * #lines
        local ty = hy + pad + math.floor((avail_h - total) / 2)
        for __, line in ipairs(lines) do
            local tw = textWidth(face, line)
            RenderText:renderUtf8Text(bb, r.x + pad + math.floor((avail_w - tw) / 2), ty + math.floor(asc * 0.88), face, line, true, false, Blitbuffer.COLOR_BLACK, avail_w)
            ty = ty + line_h
        end
        if o.dir == "R" then
            drawArrow(bb, r.x + r.w - 2, hy + math.floor(hh / 2), "R", arrow, Blitbuffer.COLOR_BLACK)
        else
            local ax = (n == 2 and i == 1) and (r.x + math.floor(r.w / 4)) or (r.x + math.floor(r.w / 2))
            drawArrow(bb, ax, r.y + r.h - 2, "D", arrow, Blitbuffer.COLOR_BLACK)
        end
    end
end

function GameView:paintClue(bb)
    local p = self.puzzle
    local r = self:clueRect()
    bb:paintRect(r.x, r.y, r.w, r.h, Blitbuffer.COLOR_WHITE)
    local w = p.current
    local arrow_char = w.horizontal and "→" or "↓"
    -- undo cell hyphenation (hyphen + line break) for the clue bar
    local clue_text = w.clue:gsub("%-\n", ""):gsub("\n", " ")
    local text = T("%1 %2  (%3)", arrow_char, clue_text, #w.letters)
    for __, br in ipairs({ { self.prev_rect, "<" }, { self.next_rect, ">" } }) do
        bb:paintBorder(br[1].x, br[1].y, br[1].w, br[1].h, Size.border.button, Blitbuffer.COLOR_BLACK, Size.radius.button)
        drawCentered(bb, br[1].x, br[1].y, br[1].w, br[1].h, self.key_face, br[2])
    end
    local tx = self.prev_rect.x + self.prev_rect.w + self.margin * 2
    local fh, asc = self.ui_face.ftsize:getHeightAndAscender()
    RenderText:renderUtf8Text(bb, tx, r.y + math.floor((r.h - fh) / 2 + asc), self.ui_face, text, true, false, Blitbuffer.COLOR_BLACK, self.next_rect.x - self.margin * 2 - tx)
end

function GameView:paintKeys(bb)
    for ri, row in ipairs(self.key_rows) do
        for ci, k in ipairs(row) do
            local kx = self.row_x[ri] + (ci - 1) * self.key_w
            local ky = self.keys_y + (ri - 1) * self.key_h
            local g = Size.margin.small
            bb:paintBorder(kx + g, ky + g, self.key_w - 2 * g, self.key_h - 2 * g, Size.border.default, Blitbuffer.COLOR_BLACK, Size.radius.default)
            local label = k == "DEL" and _("DEL") or k
            drawCentered(bb, kx, ky, self.key_w, self.key_h, #label > 2 and self.key_small_face or self.key_face, label)
        end
    end
end

-- refreshing ----------------------------------------------------------------

function GameView:refreshRect(rect)
    UIManager:setDirty(self, function() return "ui", rect end)
end

function GameView:refreshCells(cells)
    local r
    for __, c in ipairs(cells) do
        local cr = self:cellRect(c.x, c.y)
        if r then
            local x1, y1 = math.min(r.x, cr.x), math.min(r.y, cr.y)
            local x2, y2 = math.max(r.x + r.w, cr.x + cr.w), math.max(r.y + r.h, cr.y + cr.h)
            r = Geom:new{ x = x1, y = y1, w = x2 - x1, h = y2 - y1 }
        else
            r = cr
        end
    end
    if r then self:refreshRect(r) end
end

function GameView:refreshWordChange(old_word)
    self:refreshRect(self:wordRect(old_word))
    self:refreshRect(self:wordRect(self.puzzle.current))
    self:refreshRect(self:clueRect())
end

function GameView:refreshGrid()
    self:refreshRect(Geom:new{ x = self.grid_x - 2, y = self.grid_y - 2, w = self.grid_w + 4, h = self.grid_h + 4 })
end

-- input ---------------------------------------------------------------------

function GameView:onTap(_, ges)
    local px, py = ges.pos.x, ges.pos.y
    for __, b in ipairs(self.buttons) do
        if b.rect:contains(Geom:new{ x = px, y = py, w = 1, h = 1 }) then
            self:onButton(b.id)
            return true
        end
    end
    local point = Geom:new{ x = px, y = py, w = 1, h = 1 }
    if self.prev_rect:contains(point) then
        self:onKey("<")
        return true
    elseif self.next_rect:contains(point) then
        self:onKey(">")
        return true
    end
    local cx, cy = self:cellAtPos(px, py)
    if cx then
        local old = self.puzzle.current
        if self.puzzle:selectCell(cx, cy) then
            self:refreshWordChange(old)
        end
        return true
    end
    local k = self:keyAtPos(px, py)
    if k then
        self:onKey(k)
        return true
    end
    return true
end

function GameView:onSwipe(_, ges)
    local old = self.puzzle.current
    if ges.direction == "west" then
        self.puzzle:nextWord(1)
    elseif ges.direction == "east" then
        self.puzzle:nextWord(-1)
    else
        return true
    end
    self:refreshWordChange(old)
    return true
end

function GameView:onKey(k)
    local p = self.puzzle
    local old = p.current
    if k == "DEL" then
        self:refreshCells(p:backspace())
        self:markChanged()
    elseif k == "<" then
        p:nextWord(-1)
        self:refreshWordChange(old)
    elseif k == ">" then
        p:nextWord(1)
        self:refreshWordChange(old)
    else
        self:refreshCells(p:enterLetter(k))
        self:markChanged()
        if p:isSolved() then
            self:onSolved()
        end
    end
end

function GameView:onButton(id)
    local p = self.puzzle
    if id == "close" then
        self:close()
    elseif id == "check" then
        local n_wrong, n_empty = p:check()
        self:refreshGrid()
        self:markChanged(true)
        local text
        if n_wrong == 0 and n_empty == 0 then
            text = _("All correct!")
        elseif n_wrong == 0 then
            text = T(_("No mistakes so far, %1 cells empty."), n_empty)
        else
            text = T(_("%1 wrong, %2 empty. Wrong letters are marked."), n_wrong, n_empty)
        end
        UIManager:show(InfoMessage:new{ text = text, timeout = 3 })
    elseif id == "hint" then
        self:refreshCells(p:hint())
        self:markChanged(true)
        if p:isSolved() then
            self:onSolved()
        end
    end
end

function GameView:onSolved()
    self:markChanged(true)
    UIManager:show(InfoMessage:new{ text = _("Solved! Congratulations."), timeout = 4 })
end

function GameView:markChanged(force)
    self.unsaved = self.unsaved + 1
    if force or self.unsaved >= 5 then
        self.unsaved = 0
        if self.on_progress then self.on_progress(self.puzzle) end
    end
end

function GameView:close()
    if self.on_progress then self.on_progress(self.puzzle) end
    UIManager:close(self)
    if self.on_close then self.on_close(self.puzzle) end
end

function GameView:onClose()
    self:close()
    return true
end

function GameView:onCloseWidget()
    UIManager:setDirty(nil, "flashui")
end

return GameView
