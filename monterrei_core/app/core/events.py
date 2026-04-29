"""Constantes de eventos WebSocket. Centralizadas para evitar typos."""

# Server -> Client
EVT_STATE_RESTORE = "state:restore"
EVT_STATE_SNAPSHOT = "state:snapshot"
EVT_MIDI_BPM = "midi:bpm"
EVT_MIDI_BAR = "midi:bar"
EVT_MIDI_STATUS = "midi:status"
EVT_HARDWARE_STATUS = "hw:status"

# Movement events
EVT_M1_SLIDESHOW = "m1:slideshow"
EVT_M1_VIDEO = "m1:video"
EVT_M2_LORENZ_TICK = "m2:tick"
EVT_M2_GROUP_STARTED = "m2:group_started"
EVT_M2_INSTRUMENT_ACTIVATED = "m2:activated"
EVT_M2_BLACKOUT = "m2:blackout"
EVT_M3_TRIGGER = "m3:trigger"
EVT_M4_VOTING_OPEN = "m4:voting_open"
EVT_M4_VOTING_CLOSE = "m4:voting_close"
EVT_M4_LOOP_ASSIGNED = "m4:loop_assigned"
EVT_M4_SHUTDOWN_MODE = "m4:shutdown_mode"
EVT_M4_MUSICIAN_OFF = "m4:musician_off"

# Musician/director surface
EVT_PLAY_STATE = "musician:play"        # {playing: bool, instrument, color, flash}
EVT_DIRECTOR_UPDATE = "director:update"
EVT_PUBLIC_UPDATE = "public:update"
EVT_ADMIN_UPDATE = "admin:update"
EVT_PROJECTION_UPDATE = "projection:update"

# Color override
EVT_COLOR_OVERRIDE = "color:override"

# Client -> Server
CMD_REGISTER = "register"
CMD_VOTE = "vote"
CMD_SHUTDOWN_CLICK = "shutdown_click"
CMD_ADMIN = "admin:cmd"   # multiplexador por subtipo
