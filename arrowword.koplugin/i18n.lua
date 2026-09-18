--[[--
Tiny translation helper for the plugin's own strings.

KOReader's gettext only knows KOReader's catalogue, so the plugin carries its
own table. Source strings are English; add a table per language below. The
language follows KOReader's UI language setting.
]]

local translations = {
    nl = {
        ["Arrowword puzzles"] = "Zweedse puzzels",
        ["Close"] = "Sluiten",
        ["Check"] = "Controleer",
        ["Hint"] = "Hint",
        ["DEL"] = "WIS",
        ["All correct!"] = "Alles goed!",
        ["No mistakes so far, %1 cells empty."] = "Nog geen fouten, %1 cellen leeg.",
        ["%1 wrong, %2 empty. Wrong letters are marked."] = "%1 fout, %2 leeg. Foute letters zijn gemarkeerd.",
        ["Solved! Congratulations."] = "Opgelost! Gefeliciteerd.",
        ["done"] = "klaar",
        ["in progress"] = "bezig",
        ["%1 of %2 done"] = "%1 van %2 klaar",
        ["Cannot read %1."] = "Kan %1 niet lezen.",
        ["%1 is not a valid puzzle."] = "%1 is geen geldige puzzel.",
        ["No puzzles found. Put .json files in %1."] = "Geen puzzels gevonden. Zet .json-bestanden in %1.",
    },
}

local lang
local function currentLanguage()
    if lang == nil then
        local setting = G_reader_settings and G_reader_settings:readSetting("language") or "en"
        lang = tostring(setting):match("^(%a%a)") or "en"
    end
    return lang
end

return function(text)
    local t = translations[currentLanguage()]
    return t and t[text] or text
end
