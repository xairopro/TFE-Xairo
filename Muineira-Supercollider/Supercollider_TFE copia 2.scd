(
s.waitForBoot({
    // 1. Definimos o SynthDef (o xerador de son)
    SynthDef(\ondas_saida3, { |freq1 = 50, freq2 = 51, amp1 = 0.1, amp2 = 0.1|
        var osc1 = SinOsc.ar(freq1) * amp1;
        var osc2 = SinOsc.ar(freq2) * amp2;
        var mestura = osc1 + osc2; // Sumamos as dúas ondas

        // A saída física 3 correspóndese co bus número 2
        Out.ar(2, mestura);
    }).add;

    // Agardamos a que o servidor cargue o SynthDef correctamente
    s.sync;

    // 2. Instanciamos o Synth
    ~synth = Synth(\ondas_saida3);

    // 3. Deseñamos a Interface Gráfica (GUI)
    Window.closeAll; // Pechamos fiestras previas para evitar que se acumulen
    ~fiestra = Window("Control de Ondas (Só Saída 3)", Rect(200, 200, 420, 250)).front;

    // Cando se peche a fiestra da interface, o son apágase automaticamente
    ~fiestra.onClose = { ~synth.free; "Son detido e synth liberado.".postln; };
    ~fiestra.view.decorator = FlowLayout(~fiestra.view.bounds, 15@15, 10@10);

    // --- Control da Onda 1 ---
    EZSlider(~fiestra, 380@40, "Frec 1 (Hz)", ControlSpec(20, 500, 'exp', 0.1, 50), { |ez|
        ~synth.set(\freq1, ez.value);
    }, 50);

    EZSlider(~fiestra, 380@40, "Amp 1", \amp, { |ez|
        ~synth.set(\amp1, ez.value);
    }, 0.1);

    // --- Control da Onda 2 ---
    EZSlider(~fiestra, 380@40, "Frec 2 (Hz)", ControlSpec(20, 500, 'exp', 0.1, 51), { |ez|
        ~synth.set(\freq2, ez.value);
    }, 51);

    EZSlider(~fiestra, 380@40, "Amp 2", \amp, { |ez|
        ~synth.set(\amp2, ez.value);
    }, 0.1);

    "Interface cargada. Emitindo sinais pola saída física 3.".postln;
});
)