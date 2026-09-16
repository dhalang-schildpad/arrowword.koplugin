--[[--
Zweedse puzzel plugin voor KOReader.

Toont een bibliotheek van puzzelbestanden (JSON, zie puzzles/FORMAT.md) en
opent een spelweergave om ze op te lossen. Voortgang wordt per puzzel bewaard.
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
local _ = require("gettext")
local T = require("ffi/util").template
local Screen = Device.screen

local Puzzle = require("puzzle")
local GameView = require("gameview")

local ZweedsePuzzel = WidgetContainer:extend{
    name = "zweedsepuzzel",
    is_doc_only = false,
}

function ZweedsePuzzel:init()
    logger.info("zweedsepuzzel: plugin geladen")
    self.settings = LuaSettings:open(DataStorage:getSettingsDir() .. "/zweedsepuzzel.lua")
    self.ui.menu:registerToMainMenu(self)

    -- ontwikkelhulp: open direct een puzzel (voor screenshots in de emulator)
    local auto = os.getenv("ZP_AUTOOPEN")
    if auto == "library" then
        UIManager:scheduleIn(1, function() self:showLibrary() end)
        if os.getenv("ZP_SCREENSHOT") then
            UIManager:scheduleIn(5, function() Screen:shot(os.getenv("ZP_SCREENSHOT")) end)
        end
    elseif auto then
        UIManager:scheduleIn(1, function() self:openPuzzle(auto) end)
    end
end

function ZweedsePuzzel:addToMainMenu(menu_items)
    menu_items.zweedsepuzzel = {
        text = _("Zweedse puzzel"),
        sorting_hint = "more_tools",
        callback = function() self:showLibrary() end,
    }
end

--- Mappen waarin puzzels gezocht worden.
function ZweedsePuzzel:puzzleDirs()
    return {
        DataStorage:getDataDir() .. "/zweedsepuzzels",
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

function ZweedsePuzzel:loadPuzzle(path)
    local s = readFile(path)
    if not s then return nil, T(_("Kan %1 niet lezen."), path) end
    local ok, data = pcall(require("json").decode, s)
    if not ok or type(data) ~= "table" or not data.cellen then
        return nil, T(_("%1 is geen geldige puzzel."), path)
    end
    local ok2, puzzle = pcall(Puzzle.new, data)
    if not ok2 then
        logger.warn("zweedsepuzzel: fout in puzzel", path, puzzle)
        return nil, T(_("%1 is geen geldige puzzel."), path)
    end
    return puzzle
end

function ZweedsePuzzel:progressKey(path)
    return path:match("([^/]+)%.json$") or path
end

function ZweedsePuzzel:listPuzzles()
    local items = {}
    local progress = self.settings:readSetting("voortgang") or {}
    for _, dir in ipairs(self:puzzleDirs()) do
        if lfs.attributes(dir, "mode") == "directory" then
            for entry in lfs.dir(dir) do
                if entry:match("%.json$") and not entry:match("^%._") then
                    local path = dir .. "/" .. entry
                    local puzzle = self:loadPuzzle(path)
                    if puzzle then
                        local pr = progress[self:progressKey(path)]
                        local status
                        if pr and pr.klaar then
                            status = _("klaar")
                        elseif pr and next(pr.letters or {}) then
                            status = _("bezig")
                        else
                            status = ""
                        end
                        local text = puzzle.titel
                        if puzzle.sterren then
                            text = text .. "  " .. string.rep("★", puzzle.sterren)
                        end
                        items[#items + 1] = {
                            text = text,
                            mandatory = status,
                            path = path,
                            callback = function() self:openPuzzle(path) end,
                        }
                    end
                end
            end
        end
    end
    table.sort(items, function(a, b) return a.text < b.text end)
    return items
end

function ZweedsePuzzel:showLibrary()
    local items = self:listPuzzles()
    if #items == 0 then
        UIManager:show(InfoMessage:new{
            text = T(_("Geen puzzels gevonden. Zet .json-bestanden in %1."), self:puzzleDirs()[1]),
        })
        return
    end
    self.library = Menu:new{
        title = _("Zweedse puzzels"),
        item_table = items,
        is_borderless = true,
        is_popout = false,
        is_enable_shortcut = false,
        width = Screen:getWidth(),
        height = Screen:getHeight(),
        -- geen close_callback: die zou de bibliotheek sluiten zodra een
        -- puzzel gekozen wordt (Menu:onMenuSelect). Sluiten via de X.
        onCloseAllMenus = function(menu)
            UIManager:close(menu)
            self.library = nil
            return true
        end,
    }
    UIManager:show(self.library)
end

function ZweedsePuzzel:saveProgress(path, puzzle)
    local progress = self.settings:readSetting("voortgang") or {}
    progress[self:progressKey(path)] = puzzle:getProgress()
    self.settings:saveSetting("voortgang", progress)
    self.settings:flush()
end

function ZweedsePuzzel:openPuzzle(path)
    local puzzle, err = self:loadPuzzle(path)
    if not puzzle then
        UIManager:show(InfoMessage:new{ text = err })
        return
    end
    local progress = self.settings:readSetting("voortgang") or {}
    puzzle:setProgress(progress[self:progressKey(path)])
    local view = GameView:new{
        puzzle = puzzle,
        on_progress = function(p) self:saveProgress(path, p) end,
        on_close = function()
            if self.library then
                self.library:switchItemTable(nil, self:listPuzzles())
            end
        end,
    }
    UIManager:show(view, "flashui")
end

return ZweedsePuzzel
