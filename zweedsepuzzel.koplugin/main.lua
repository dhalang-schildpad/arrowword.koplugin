--[[--
Zweedse puzzel plugin voor KOReader.

Fase 0: alleen een menu-item dat een bericht toont, om te controleren dat de
plugin geladen wordt in de emulator en op de Kobo Forma.
]]

local InfoMessage = require("ui/widget/infomessage")
local UIManager = require("ui/uimanager")
local WidgetContainer = require("ui/widget/container/widgetcontainer")
local logger = require("logger")
local _ = require("gettext")

local ZweedsePuzzel = WidgetContainer:extend{
    name = "zweedsepuzzel",
    is_doc_only = false,
}

function ZweedsePuzzel:init()
    logger.info("zweedsepuzzel: plugin geladen")
    self.ui.menu:registerToMainMenu(self)
end

function ZweedsePuzzel:addToMainMenu(menu_items)
    menu_items.zweedsepuzzel = {
        text = _("Zweedse puzzel"),
        sorting_hint = "more_tools",
        callback = function()
            UIManager:show(InfoMessage:new{
                text = _("Zweedse puzzel: plugin werkt. Puzzels volgen in fase 2."),
            })
        end,
    }
end

return ZweedsePuzzel
