--[[--
Arrowword plugin for KOReader.

Shows a library of puzzle files (JSON, see docs/PUZZLE_FORMAT.md) and opens a
game view to solve them. Folders are shown as packs. Progress is saved per
puzzle in settings/arrowword.lua.
]]

local DataStorage = require("datastorage")
local Device = require("device")
local InfoMessage = require("ui/widget/infomessage")
local LuaSettings = require("luasettings")
local Menu = require("ui/widget/menu")
local UIManager = require("ui/uimanager")
local WidgetContainer = require("ui/widget/container/widgetcontainer")
local lfs = require("libs/libkoreader-lfs")
local logger = require("logger")
local T = require("ffi/util").template
local Screen = Device.screen

local _ = require("i18n")
local Puzzle = require("puzzle")
local GameView = require("gameview")

local Arrowword = WidgetContainer:extend{
    name = "arrowword",
    is_doc_only = false,
}

function Arrowword:init()
    logger.info("arrowword: plugin loaded")
    self.settings = LuaSettings:open(DataStorage:getSettingsDir() .. "/arrowword.lua")
    self.ui.menu:registerToMainMenu(self)

    -- development aid: open a puzzle (or the library) right away, for
    -- screenshots in the emulator
    local auto = os.getenv("AW_AUTOOPEN")
    if auto == "library" then
        UIManager:scheduleIn(1, function() self:showLibrary() end)
        if os.getenv("AW_SCREENSHOT") then
            UIManager:scheduleIn(5, function() Screen:shot(os.getenv("AW_SCREENSHOT")) end)
        end
    elseif auto then
        UIManager:scheduleIn(1, function() self:openPuzzle(auto, auto) end)
    end
end

function Arrowword:addToMainMenu(menu_items)
    menu_items.arrowword = {
        text = _("Arrowword puzzles"),
        sorting_hint = "more_tools",
        callback = function() self:showLibrary() end,
    }
end

--- Directories that are searched for puzzles (recursively).
function Arrowword:puzzleDirs()
    return {
        DataStorage:getDataDir() .. "/arrowwords",
        self.path .. "/puzzles",
    }
end

local function readFile(path)
    local f = io.open(path, "r")
    if not f then return nil end
    local s = f:read("*a")
    f:close()
    return s
end

function Arrowword:loadPuzzle(path)
    local s = readFile(path)
    if not s then return nil, T(_("Cannot read %1."), path) end
    local ok, data = pcall(require("json").decode, s)
    if not ok or type(data) ~= "table" or not data.cells then
        return nil, T(_("%1 is not a valid puzzle."), path)
    end
    local ok2, puzzle = pcall(Puzzle.new, data)
    if not ok2 then
        logger.warn("arrowword: invalid puzzle", path, puzzle)
        return nil, T(_("%1 is not a valid puzzle."), path)
    end
    return puzzle
end

--- Builds menu items for one directory: sub-folders first (as packs), then puzzles.
-- `rel` is the path relative to the puzzle root and doubles as progress key prefix.
-- @return items, number of puzzles, number done
function Arrowword:listDir(dir, rel)
    local progress = self.settings:readSetting("progress") or {}
    local folders, files = {}, {}
    for entry in lfs.dir(dir) do
        if entry:sub(1, 1) ~= "." then
            local path = dir .. "/" .. entry
            local mode = lfs.attributes(path, "mode")
            if mode == "directory" then
                folders[#folders + 1] = entry
            elseif mode == "file" and entry:match("%.json$") then
                files[#files + 1] = entry
            end
        end
    end
    table.sort(folders)
    table.sort(files)

    local items, total, done = {}, 0, 0
    for __, entry in ipairs(folders) do
        local sub_items, sub_total, sub_done = self:listDir(dir .. "/" .. entry, rel .. entry .. "/")
        if sub_total > 0 then
            total, done = total + sub_total, done + sub_done
            items[#items + 1] = {
                text = entry,
                mandatory = T(_("%1 of %2 done"), sub_done, sub_total),
                sub_item_table = sub_items,
            }
        end
    end
    for __, entry in ipairs(files) do
        local path = dir .. "/" .. entry
        local puzzle = self:loadPuzzle(path)
        if puzzle then
            local key = rel .. entry
            local pr = progress[key]
            local status = ""
            if pr and pr.fingerprint == puzzle:fingerprint() then
                if pr.done then
                    status = _("done")
                    done = done + 1
                elseif next(pr.letters or {}) then
                    status = _("in progress")
                end
            end
            total = total + 1
            local text = puzzle.title
            if puzzle.stars then
                text = text .. "  " .. string.rep("★", puzzle.stars)
            end
            local item = { text = text, mandatory = status }
            item.callback = function() self:openPuzzle(path, key, item) end
            items[#items + 1] = item
        end
    end
    return items, total, done
end

function Arrowword:listPuzzles()
    local items = {}
    for __, dir in ipairs(self:puzzleDirs()) do
        if lfs.attributes(dir, "mode") == "directory" then
            for __i, item in ipairs((self:listDir(dir, ""))) do
                items[#items + 1] = item
            end
        end
    end
    return items
end

function Arrowword:showLibrary()
    local items = self:listPuzzles()
    if #items == 0 then
        UIManager:show(InfoMessage:new{
            text = T(_("No puzzles found. Put .json files in %1."), self:puzzleDirs()[1]),
        })
        return
    end
    self.library = Menu:new{
        title = _("Arrowword puzzles"),
        item_table = items,
        is_borderless = true,
        is_popout = false,
        is_enable_shortcut = false,
        width = Screen:getWidth(),
        height = Screen:getHeight(),
        -- no close_callback: it would close the library as soon as a puzzle is
        -- chosen (Menu:onMenuSelect). Close with the X.
        onCloseAllMenus = function(menu)
            UIManager:close(menu)
            self.library = nil
            return true
        end,
    }
    UIManager:show(self.library)
end

function Arrowword:saveProgress(key, puzzle)
    local progress = self.settings:readSetting("progress") or {}
    progress[key] = puzzle:getProgress()
    self.settings:saveSetting("progress", progress)
    self.settings:flush()
end

--- Opens a puzzle. `item` is the library entry, updated in place on close so
-- the library stays on the same page of the same pack.
function Arrowword:openPuzzle(path, key, item)
    local puzzle, err = self:loadPuzzle(path)
    if not puzzle then
        UIManager:show(InfoMessage:new{ text = err })
        return
    end
    local progress = self.settings:readSetting("progress") or {}
    puzzle:setProgress(progress[key])
    local view = GameView:new{
        puzzle = puzzle,
        on_progress = function(p) self:saveProgress(key, p) end,
        on_close = function(p)
            if self.library and type(item) == "table" then
                if p:isSolved() then
                    item.mandatory = _("done")
                elseif p:countFilled() > 0 then
                    item.mandatory = _("in progress")
                end
                self.library:updateItems()
            end
        end,
    }
    UIManager:show(view, "flashui")
end

return Arrowword
