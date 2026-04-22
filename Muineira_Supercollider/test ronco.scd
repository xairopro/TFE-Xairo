(
// --- 1. OPCIÓN RELOXO (Tic mecánico e agudo, moi curto) ---
SynthDef(\tic_reloxo, { |out=0, amp=0.05, pan=0|
    // Unha envolvente ultra curta (5 milisegundos de caída)
    var env = EnvGen.ar(Env.perc(0.001, 0.05), doneAction: 2);
    // Unha onda sinusoidal que cae rapidamente de afinación (emula o "clic")
    var sig = SinOsc.ar(XLine.kr(2000, 1000, 0.05)) * env;
    Out.ar(out, Pan2.ar(sig, pan, amp));
}).add;

// --- 2. OPCIÓN FERREÑAS (Chasquido metálico suave, o que ti pedías) ---
SynthDef(\tic_ferrenas, { |out=0, amp=0.05, pan=0|
    // Envolvente un pouquiño máis longa para que soe á chapa vibrando
    var env = EnvGen.ar(Env.perc(0.005, 0.1), doneAction: 2);
    // Ruído branco pasado por un filtro paso banda moi agudo (8000 Hz)
    var sig = BPF.ar(WhiteNoise.ar, 8000, 0.5) * env;
    Out.ar(out, Pan2.ar(sig, pan, amp));
}).add;

// --- 3. OPCIÓN ESTALIDO (Pulso sordo de madeira/vinilo) ---
SynthDef(\tic_estalido, { |out=0, amp=0.05, pan=0|
    var env = EnvGen.ar(Env.perc(0.001, 0.03), doneAction: 2);
    // Ruído rosa filtrado para quitarlle o brillo e que sexa un "thump" grave
    var sig = PinkNoise.ar * env;
    sig = LPF.ar(sig, 1500);
    Out.ar(out, Pan2.ar(sig, pan, amp));
}).add;
)

// =====================================================================
// REPRODUTOR DO METRÓNOMO (1 pulso por segundo = 60 BPM)
// =====================================================================

// Selecciona a liña que queiras probar e execútaa (Cmd+Enter):

// Probar o Reloxo:
Pdef(\metronomo, Pbind(\instrument, \tic_reloxo, \dur, 1, \amp, 0.08)).play;

// Probar as Ferreñas (O meu favorito para o teu proxecto):
Pdef(\metronomo, Pbind(\instrument, \tic_ferrenas, \dur, 1, \amp, 0.05)).play;

// Probar o Estalido (Máis sordo):
Pdef(\metronomo, Pbind(\instrument, \tic_estalido, \dur, 1, \amp, 0.15)).play;

// --- PARA PARAR O METRÓNOMO ---
Pdef(\metronomo).stop;