-- Derived from KOReader's own .luacheckrc, so that `luacheck *.lua`
-- also works outside a KOReader checkout.
unused_args = false
std = "luajit"
self = false

globals = {
    "G_reader_settings",
    "G_defaults",
    "table.pack",
    "table.unpack",
}

read_globals = {
    "_ENV",
}

ignore = {
    "211/__*",
    "231/__",
    "631",
    "dummy",
}
