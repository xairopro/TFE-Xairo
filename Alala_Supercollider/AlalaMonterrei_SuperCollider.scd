// 1. Configuración de Memoria e Inicio
s.options.sampleRate = 48000;
s.options.memSize = 65536;
s.boot;

// 2. Bloque principal
s.waitForBoot({
	var pathDir, b_chop, b_puente, b_arcoMute, b_harm, b_cordal, b_est1, b_choiva;
	var win, synths;

	"Cargando audios (Forzados a mono para evitar problemas granulares)...".postln;
	pathDir = thisProcess.nowExecutingPath.dirname;

	b_chop = Buffer.readChannel(s, pathDir +/+ "chop.wav", channels: [0]);
	b_puente = Buffer.readChannel(s, pathDir +/+ "sobre_puente.wav", channels: [0]);
	b_arcoMute = Buffer.readChannel(s, pathDir +/+ "arco_mute.wav", channels: [0]);
	b_harm = Buffer.readChannel(s, pathDir +/+ "harmonico.wav", channels: [0]);
	b_cordal = Buffer.readChannel(s, pathDir +/+ "arco_cordal.wav", channels: [0]);
	b_est1 = Buffer.readChannel(s, pathDir +/+ "estalidos.wav", channels: [0]);
	b_choiva = Buffer.readChannel(s, pathDir +/+ "choiva.wav", channels: [0]);

	~masterBus = Bus.control(s, 1); ~masterBus.set(1.0);

	s.sync;

	// --- 3. SINTETIZADORES TEXTURAIS ---

	SynthDef(\chop_granular, { |amp=0, density=15, pan=0|
		var master = In.kr(~masterBus, 1).lag(0.1);
		var trig = Dust.kr(density.lag(0.1));
		var sig = TGrains.ar(2, trig, b_chop, 1.0, TRand.kr(0.0, BufDur.kr(b_chop), trig), 0.1, TRand.kr(-0.8, 0.8, trig), 0.5);
		Out.ar(0, sig * amp.lag(0.1) * 2.0 * master);
	}).add;

	SynthDef(\puente_vento, { |amp=0, cutoff=1500, pan=0|
		var master = In.kr(~masterBus, 1).lag(0.1);
		var pointer = LFTri.kr(1/(BufDur.kr(b_puente)*2)).range(0.1, 0.9);
		var sig = Warp1.ar(1, b_puente, pointer, 1.0, 0.2, -1, 8, 0.1);
		sig = BPF.ar(sig, cutoff.lag(0.1), 0.15) * 5.0;
		Out.ar(0, Pan2.ar(sig * amp.lag(0.1) * master, pan));
	}).add;

	SynthDef(\arco_mute_tubo, { |amp=0, freq=100, pan=0|
		var master = In.kr(~masterBus, 1).lag(0.1);
		var pointer = LFTri.kr(1/(BufDur.kr(b_arcoMute)*2)).range(0.1, 0.9);
		var sig = Warp1.ar(1, b_arcoMute, pointer, 1.0, 0.2, -1, 8, 0.1);
		var res = CombN.ar(sig, 0.1, freq.reciprocal.lag(0.1), 2.0);
		Out.ar(0, Pan2.ar(res * amp.lag(0.1) * 0.8 * master, pan));
	}).add;

	SynthDef(\harmonico_pad, { |amp=0, pitch=1.0, pan=0|
		var master = In.kr(~masterBus, 1).lag(0.1);
		var pointer = LFTri.kr(0.1).range(0.1, 0.9);
		var sig = Warp1.ar(1, b_harm, pointer, pitch.lag(0.1), 0.4, -1, 12, 0.1);
		sig = FreeVerb.ar(sig, 0.8, 0.95, 0.1);
		Out.ar(0, Pan2.ar(sig * amp.lag(0.1) * 1.5 * master, pan));
	}).add;

	SynthDef(\cordal_radio, { |amp=0, crush=4000, pan=0|
		var master = In.kr(~masterBus, 1).lag(0.1);
		var pointer = LFTri.kr(1/(BufDur.kr(b_cordal)*2)).range(0.1, 0.9);
		var sig = Warp1.ar(1, b_cordal, pointer, 1.0, 0.2, -1, 8, 0.1);
		sig = Latch.ar(sig, Impulse.ar(crush.lag(0.1)));
		sig = LPF.ar(sig, crush.lag(0.1));
		Out.ar(0, Pan2.ar(sig * amp.lag(0.1) * 1.5 * master, pan));
	}).add;

	SynthDef(\estalidos_lume, { |amp=0, grainSize=0.2, pan=0|
		var master = In.kr(~masterBus, 1).lag(0.1);
		var trig = Dust.kr(20);
		var sig = TGrains.ar(2, trig, b_est1, 1.0, TRand.kr(0.0, BufDur.kr(b_est1), trig), grainSize.lag(0.1), TRand.kr(-0.8, 0.8, trig), 0.5);
		Out.ar(0, sig * amp.lag(0.1) * 1.5 * master);
	}).add;

	SynthDef(\choiva_shimmer, { |amp=0, dispers=0.5, pan=0|
		var master = In.kr(~masterBus, 1).lag(0.1);
		var pointer = LFTri.kr(1/(BufDur.kr(b_choiva)*1.5)).range(0.1, 0.9);
		var sig = Warp1.ar(1, b_choiva, pointer, 1.0, 0.2, -1, 8, 0.1);
		sig = PitchShift.ar(sig, 0.1, 1.0, pitchDispersion: dispers.lag(0.1), timeDispersion: 0.05);
		sig = FreeVerb.ar(sig, 0.7, 0.9, 0.2);
		Out.ar(0, Pan2.ar(sig * amp.lag(0.1) * 1.5 * master, pan));
	}).add;

	s.sync;

	synths = (
		chop: Synth(\chop_granular),
		puente: Synth(\puente_vento),
		arcomute: Synth(\arco_mute_tubo),
		harm: Synth(\harmonico_pad),
		cordal: Synth(\cordal_radio),
		est1: Synth(\estalidos_lume),
		choiva: Synth(\choiva_shimmer)
	);

	// Función para ventás de axuda
	~mostrarAxuda = { |titulo, descricion|
		var infoWin = Window(titulo, Rect(Window.screenBounds.width/2 - 150, Window.screenBounds.height/2 - 75, 300, 150), border: true);
		StaticText(infoWin, Rect(15, 15, 270, 120)).string_(descricion).font_(Font("Helvetica", 13)).align_(\topLeft);
		infoWin.front;
	};

// --- 4. INTERFACE GRÁFICA (DASHBOARD COMPACTO) ---
	defer {
		var masterLayout, masterTitleLayout, centerFader;
		var mVolLabel, mVolSlider, muteBtn;

		CmdPeriod.doOnce { Window.closeAll };
		// 1. Reducido o ancho de 950 a 650
		win = Window("Dashboard - Cuarteto de Corda", Rect(100, 100, 650, 400));
		win.onClose = { synths.do(_.free); };

		// 2. Reducido o espazado entre columnas
		win.layout = HLayout().spacing_(10).margins_(15);

		centerFader = { |slider| var hl = HLayout(); hl.add(nil); hl.add(slider); hl.add(nil); hl };

		~makeCol = { |nome, synthKey, extraParam, extraSpec, descricion|
			var col = VLayout().spacing_(5);
			var titleLayout = HLayout().spacing_(2);
			var title = StaticText().string_(nome).align_(\center).font_(Font("Helvetica", 11, true)).stringColor_(Color.black);
			var infoBtn = Button().states_([["?", Color.white, Color.grey(0.4)]]).maxWidth_(16).maxHeight_(16).action_({
				~mostrarAxuda.value(nome, descricion);
			});
			var volLabel = StaticText().string_("Vol: 0.0").align_(\center).font_(Font("Helvetica", 10));
			var volSlider = Slider().orientation_(\vertical).value_(0).background_(Color.black).knobColor_(Color.white).fixedWidth_(35);
			var extraLabel = StaticText().string_(extraSpec.units ++ ":" ++ extraSpec.default.round(0.01)).align_(\center).font_(Font("Helvetica", 10));
			var extraSlider = Slider().orientation_(\vertical).value_(extraSpec.unmap(extraSpec.default)).background_(Color.black).knobColor_(Color.white).fixedWidth_(35);

			titleLayout.add(nil); titleLayout.add(title); titleLayout.add(infoBtn); titleLayout.add(nil);

			volSlider.action_({ |sl|
				synths[synthKey].set(\amp, sl.value);
				volLabel.string_("Vol: " ++ sl.value.round(0.01));
			});

			extraSlider.action_({ |sl|
				var rVal = extraSpec.map(sl.value);
				synths[synthKey].set(extraParam, rVal);
				extraLabel.string_(extraSpec.units ++ ":" ++ rVal.round(0.01));
			});

			col.add(titleLayout); col.add(volLabel); col.add(centerFader.value(volSlider)); col.add(extraLabel); col.add(centerFader.value(extraSlider));
			col;
		};

		win.layout.add(~makeCol.value("Chop", \chop, \density, ControlSpec(2, 50, 'exp', 0, 15, "Dens."), "Sonido percusivo de chop.\n\nFader inferior: Controla a densidade da nube granular."));
		win.layout.add(~makeCol.value("Ponte", \puente, \cutoff, ControlSpec(200, 4000, 'exp', 0, 1500, "Hz"), "Ruído frotando sobre a ponte.\n\nFader inferior: Modifica a frecuencia do filtro."));
		win.layout.add(~makeCol.value("A.Mute", \arcomute, \freq, ControlSpec(50, 800, 'exp', 0, 100, "Hz"), "Frotar o arco coas cordas mutadas.\n\nFader inferior: Cambia a afinación da resonancia."));
		win.layout.add(~makeCol.value("Harm.", \harm, \pitch, ControlSpec(0.5, 2.0, 'lin', 0, 1.0, "Pitch"), "Glissando harmónico alongado.\n\nFader inferior: Cambia o ton (pitch) sen afectar á velocidade."));
		win.layout.add(~makeCol.value("Cordal", \cordal, \crush, ControlSpec(500, 10000, 'exp', 0, 4000, "Crsh"), "Son de frotar o cordal do instrumento.\n\nFader inferior: Destrúe o audio por redución de bits."));
		win.layout.add(~makeCol.value("Est.1", \est1, \grainSize, ControlSpec(0.05, 0.5, 'exp', 0, 0.2, "Tam."), "Estalidos do arco solto.\n\nFader inferior: Controla o tamaño do gran."));
		win.layout.add(~makeCol.value("Choiva", \choiva, \dispers, ControlSpec(0.0, 2.0, 'lin', 0, 0.5, "Disp."), "Son de pingas de choiva.\n\nFader inferior: Controla a dispersión espectral."));

		// 3. Eliminados os "||" e posta unha liña vertical limpa de 1 pixel
		win.layout.add(StaticText().background_(Color.gray(0.8)).fixedWidth_(1));

		masterTitleLayout = HLayout(
			nil,
			StaticText().string_("MASTER").align_(\center).font_(Font("Helvetica", 11, true)).stringColor_(Color.black),
			Button().states_([["?", Color.white, Color.grey(0.4)]]).maxWidth_(16).maxHeight_(16).action_({
				~mostrarAxuda.value("Control Master", "Control xeral da saída de audio.\n\nSobe ou baixa o nivel de todas as texturas simultaneamente.");
			}),
			nil
		);

		masterLayout = VLayout(
			masterTitleLayout,
			mVolLabel = StaticText().string_("Vol: 1.00").align_(\center).font_(Font("Helvetica", 10)),
			centerFader.value(mVolSlider = Slider().orientation_(\vertical).value_(1.0).background_(Color.black).knobColor_(Color.white).fixedWidth_(35).action_({ |sl|
				mVolLabel.string_("Vol: " ++ sl.value.round(0.01));
				if(muteBtn.value == 0) { ~masterBus.set(sl.value); };
			})),
			muteBtn = Button().states_([["Son ON", Color.white, Color.black], ["MUTE", Color.white, Color.red(0.7)]]).value_(0).action_({ |b|
				if(b.value == 1) { ~masterBus.set(0.0); } { ~masterBus.set(mVolSlider.value); };
			})
		);
		win.layout.add(masterLayout);

		win.front;
	};
});