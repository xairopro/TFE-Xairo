// 1. Configuración de Memoria e Inicio Blindado a 48kHz
s.options.sampleRate = 48000;
s.options.memSize = 65536;

s.options.device = "Scarlett 18i20 USB"; // Nome exacto da túa interface
s.options.numOutputBusChannels = 20;    // Abrimos as 20 canles de saída

s.boot;

// 2. Bloque principal
s.waitForBoot({
	var pathDir, bufGaita, bufLume, bufPandeireta, bufPandeireta2, bufGaita2, bufPechado, bufFrullato, bufRonco, bufParcial;
	var bufCampaBat, bufCampaRes;
	var win, synths, stateArray, rule30, caTask;

	"Cargando audios a 48kHz. Lorenz extremo 0-100% (Frullato illado do GLBZ CAOS)...".postln;
	pathDir = thisProcess.nowExecutingPath.dirname;

	bufGaita = Buffer.read(s, pathDir +/+ "gaita.wav");
	bufLume = Buffer.read(s, pathDir +/+ "lume.wav");
	bufPandeireta = Buffer.read(s, pathDir +/+ "pandeireta.wav");
	bufPandeireta2 = Buffer.read(s, pathDir +/+ "pandeireta2.wav");
	bufGaita2 = Buffer.read(s, pathDir +/+ "gaita2.wav");
	bufPechado = Buffer.read(s, pathDir +/+ "pechado.wav");
	bufFrullato = Buffer.read(s, pathDir +/+ "frullato.wav");
	bufRonco = Buffer.read(s, pathDir +/+ "ronco.wav");
	bufParcial = Buffer.read(s, pathDir +/+ "parcial.wav");

	bufCampaBat = Buffer.read(s, pathDir +/+ "campa_do_fa.wav");
	bufCampaRes = Buffer.read(s, pathDir +/+ "campa_do_fa_1.wav");

	~masterBus = Bus.control(s, 1); ~masterBus.set(1.0);
	~caVolBus = Bus.control(s, 1); ~caVolBus.set(0.5);
	~xyMaxAmp = 0.8;
	~shepRateBus = Bus.control(s, 1); ~shepRateBus.set(1.0);

	s.sync;

	// --- 3. SINTETIZADORES CO MOTOR LORENZ DINÁMICO 0-100% ---

	// --- SINTETIZADOR DO METRÓNOMO INDEPENDENTE ---
	SynthDef(\tic_ferrenas, { |out=0, amp=0.05, pan=0|
		var env = EnvGen.ar(Env.perc(0.005, 0.1), doneAction: 2);
		var sig = BPF.ar(WhiteNoise.ar, 8000, 0.5) * env;
		Out.ar(out, Pan2.ar(sig, pan, amp));
	}).add;

	SynthDef(\abismo, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \verbMix.kr(0.5).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(15.1)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(15.2)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85;
		var eLz = lz2.linlin(0, 1, 0.1, 1.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var sig = Warp1.ar(1, bufGaita, LFTri.kr(1/120).range(0.05, 0.95), 0.25, 0.4, -1, 16, 0.2, 4);
		SendReply.kr(Impulse.kr(15), '/ui_abismo', [fAmp, fExt]);
		Out.ar(0, Pan2.ar(FreeVerb.ar(sig, fExt, 0.9, 0.8) * fAmp * 1.2 * master, 0));
	}).add;

	SynthDef(\lume_petrushka, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \resDecay.kr(3.0).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(15.3)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(15.4)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 0.1, 8.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var sig = PlayBuf.ar(1, bufLume, BufRateScale.kr(bufLume), loop: 1);
		var res = [36, 40, 43, 42, 46, 49].midicps.collect { |f| Ringz.ar(sig, f, fExt) };
		SendReply.kr(Impulse.kr(15), '/ui_lume_petr', [fAmp, fExt]);
		Out.ar(0, Limiter.ar(Splay.ar(Mix(res) * 0.035), 0.9) * fAmp * master);
	}).add;

	SynthDef(\lume_re9, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \resDecay.kr(3.0).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(15.5)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(15.6)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 0.1, 8.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var sig = PlayBuf.ar(1, bufLume, BufRateScale.kr(bufLume), loop: 1);
		var res = [73.42, 110.0, 164.81, 261.63].collect { |f| Ringz.ar(sig, f, fExt) };
		SendReply.kr(Impulse.kr(15), '/ui_lume_re9', [fAmp, fExt]);
		Out.ar(0, Limiter.ar(Splay.ar(Mix(res) * 0.04), 0.9) * fAmp * master);
	}).add;

	SynthDef(\estalidos_lume, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \brillo.kr(4434.92).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(15.7)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(15.8)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 2000, 8000);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var sig = HPF.ar(PlayBuf.ar(1, bufLume, BufRateScale.kr(bufLume), loop: 1), 2000);
		var res = [1.0, 1.41421356, 1.5, 1.40625].collect { |ratio| Ringz.ar(sig, fExt * ratio, decaytime: 0.08) };
		SendReply.kr(Impulse.kr(15), '/ui_estalidos', [fAmp, fExt]);
		Out.ar(0, Limiter.ar(Splay.ar(Mix(res) * 0.15), 0.9) * fAmp * master);
	}).add;

	SynthDef(\enxame_harmonico, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \detune.kr(0.01).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(16.1)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(16.2)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 0.001, 0.05);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var sig = PlayBuf.ar(1, bufRonco, BufRateScale.kr(bufRonco), loop: 1);
		var voces = 5.collect { |i| Pan2.ar(PitchShift.ar(sig, 0.1, 1.0 + (fExt * Rand(-1.0, 1.0)), 0.01, 0.01), Rand(-0.8, 0.8)) };
		SendReply.kr(Impulse.kr(15), '/ui_ronco_enxame', [fAmp, fExt]);
		Out.ar(0, Mix(voces) * fAmp * 1.0 * master);
	}).add;

	SynthDef(\crossover_pas, {
		var freqCorte = \corte.kr(200).lag(0.1);
		var mestura = In.ar(0, 2);
		var gravesMono = LPF.ar(mestura[0] + mestura[1], freqCorte) * 0.5;
		var restoPAs = HPF.ar(mestura, freqCorte);
		ReplaceOut.ar(0, restoPAs);
		Out.ar(2, gravesMono);
	}).add;

	// --- M. SÍSMICO ACTUALIZADO A SÍNTESE SENOIDAL ---
	SynthDef(\motor_sismico, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \desfase.kr(0.0).lag(0.2);
		var lz1 = A2K.kr(LorenzL.ar(16.3)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(16.4)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linlin(0, 1, 0.0, 3.0).round(1); // Redondeo por seguridade para lorenz
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);

		var freqBase = 50.0;
		// A segunda senoidal suma o fExt redondeado a enteiros (0, 1, 2, ou 3)
		var sigFinal = (SinOsc.ar(freqBase) + SinOsc.ar(freqBase + fExt.round(1))) * 0.5 * fAmp * master;

		SendReply.kr(Impulse.kr(15), '/ui_sismico', [fAmp, fExt]);
		Out.ar(0, Pan2.ar(sigFinal * 1.2, 0));
	}).add;

	SynthDef(\bombo_tectonico, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \resDecay.kr(4.0).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(16.5)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(16.6)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 1.0, 10.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var sig = PlayBuf.ar(1, bufPandeireta, BufRateScale.kr(bufPandeireta) * 0.2, loop: 1);
		var res = Ringz.ar(sig, [16.35, 32.70, 49.00], fExt);
		res = Compander.ar(LPF.ar(Mix(res), 300), LPF.ar(Mix(res), 300), 0.1, 1, 0.1, 0.01, 0.1) * 0.6;
		SendReply.kr(Impulse.kr(15), '/ui_tectonico', [fAmp, fExt]);
		Out.ar(0, Pan2.ar(res * fAmp * master, 0));
	}).add;

	SynthDef(\magma_granular, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \density.kr(20).lag(0.2);
		var lz1 = A2K.kr(LorenzL.ar(16.7)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(16.8)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 2.0, 60.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var trig = Dust.kr(fExt);
		var sig = TGrains.ar(2, trig, bufRonco, 0.5, TRand.kr(0.0, BufDur.kr(bufRonco), trig), (1.0/fExt)*1.40625, TRand.kr(-0.5, 0.5, trig), 0.5);
		SendReply.kr(Impulse.kr(15), '/ui_magma', [fAmp, fExt]);
		Out.ar(0, LPF.ar(sig, SinOsc.kr(0.1).range(150, 600)) * fAmp * 3.5 * master);
	}).add;

	SynthDef(\asubiador, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \rate.kr(8.0).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(16.9)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(17.0)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 1.0, 20.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var sig = PlayBuf.ar(1, bufParcial, BufRateScale.kr(bufParcial), loop: 1);
		var gate = LFPulse.kr(fExt, 0, 0.3) * LFPulse.kr(fExt * 1.41421356, 0, 0.3);
		SendReply.kr(Impulse.kr(15), '/ui_asubiador', [fAmp, fExt]);
		Out.ar(0, Pan2.ar(sig * gate * fAmp * 1.0 * master, 0));
	}).add;

	SynthDef(\choiva_cristal, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \gotaRate.kr(10).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(17.1)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(17.2)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 2.0, 40.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var trig = Dust.kr(fExt);
		var sig = TGrains.ar(2, trig, bufParcial, TRand.kr(0.5, 2.5, trig), TRand.kr(0.0, BufDur.kr(bufParcial), trig), TRand.kr(0.05, 0.2, trig), TRand.kr(-1.0, 1.0, trig), 0.5);
		SendReply.kr(Impulse.kr(15), '/ui_choiva', [fAmp, fExt]);
		Out.ar(0, Limiter.ar(Ringz.ar(sig, TRand.kr(3000, 8000, trig), 0.1) * fAmp * 0.6 * master, 0.9));
	}).add;

	SynthDef(\halo_xelado, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \shimmer.kr(0.8).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(17.3)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(17.4)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linlin(0, 1, 0.1, 1.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var sig = PlayBuf.ar(1, bufParcial, BufRateScale.kr(bufParcial), loop: 1);
		var verb = FreeVerb.ar(PitchShift.ar(sig, 0.2, 2.0, 0.01, 0.01), fExt, 0.99, 0.1);
		SendReply.kr(Impulse.kr(15), '/ui_halo', [fAmp, fExt]);
		Out.ar(0, Pan2.ar(verb * fAmp * 1.0 * master, 0));
	}).add;

	SynthDef(\soplete_plasma, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \drive.kr(3.0).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(17.5)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(17.6)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 1.0, 15.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var sig = PlayBuf.ar(1, bufParcial, BufRateScale.kr(bufParcial), loop: 1);
		var mix = Mix([sig, PitchShift.ar(sig, 0.1, 0.711111, 0.001, 0.001), PitchShift.ar(sig, 0.1, 1.40625, 0.001, 0.001)]);
		SendReply.kr(Impulse.kr(15), '/ui_soplete', [fAmp, fExt]);
		Out.ar(0, Pan2.ar(LPF.ar((mix * fExt).fold2(1.0) / fExt, 5000) * fAmp * 0.7 * master, 0));
	}).add;

	SynthDef(\pandeireta_glitch, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \density.kr(15).lag(0.2);
		var lz1 = A2K.kr(LorenzL.ar(17.7)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(17.8)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 1.0, 50.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var trig = Dust.kr(fExt);
		SendReply.kr(Impulse.kr(15), '/ui_pand_gran', [fAmp, fExt]);
		Out.ar(0, TGrains.ar(2, trig, bufPandeireta, 1.0, TRand.kr(0.0, BufDur.kr(bufPandeireta)-0.1, trig), 0.1, TRand.kr(-0.8, 0.8, trig), 0.8) * fAmp * 1.2 * master);
	}).add;

	SynthDef(\pandeireta_normal, {
		var fAmp = \amp.kr(0).lag(0.1); var cutoffInput = \cutoff.kr(2093); var bypass = \bypass.kr(1).lag(0.8);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var sig = PlayBuf.ar(1, bufPandeireta2, BufRateScale.kr(bufPandeireta2), loop: 1);
		var filteredSig = Limiter.ar(RLPF.ar(sig, Latch.kr(cutoffInput, Impulse.kr(1.0)), 0.05) * 1.5, 0.9);
		SendReply.kr(Impulse.kr(15), '/ui_pand_norm', [fAmp, cutoffInput]);
		Out.ar(0, Pan2.ar(SelectX.ar(bypass, [filteredSig, sig]) * fAmp * 1.2 * master, 0));
	}).add;

	SynthDef(\espectro_conxelado, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \freezeRate.kr(0.2).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(18.1)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(18.2)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 0.05, 2.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var sig = PlayBuf.ar(1, bufGaita, BufRateScale.kr(bufGaita) * 0.25, loop: 1);
		SendReply.kr(Impulse.kr(15), '/ui_espectro', [fAmp, fExt]);
		Out.ar(0, Pan2.ar(FreeVerb.ar(IFFT(PV_MagFreeze(FFT(LocalBuf(2048), sig), LFNoise0.kr(fExt) > 0)), 0.8, 0.9, 0.2) * fAmp * 1.0 * master, 0));
	}).add;

	SynthDef(\pantasmas, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \feedback.kr(0.5).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(18.3)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(18.4)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linlin(0, 1, 0.1, 0.95);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var sig = PlayBuf.ar(1, bufGaita, BufRateScale.kr(bufGaita) * 0.5, loop: 1);
		SendReply.kr(Impulse.kr(15), '/ui_pantasmas', [fAmp, fExt]);
		Out.ar(0, LPF.ar(Splay.ar([sig, CombN.ar(sig, 2.0, 0.75, fExt * 10), CombN.ar(sig, 2.0, 1.06066, fExt * 12)]), 2000) * fAmp * 0.8 * master);
	}).add;

	SynthDef(\sub_lume, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(18.5)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85;
		var oA = \overAmp.kr(0); var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		SendReply.kr(Impulse.kr(15), '/ui_sub', [fAmp, 0]);
		Out.ar(0, Pan2.ar(LPF.ar(PlayBuf.ar(1, bufLume, BufRateScale.kr(bufLume)*0.15, loop: 1), 150) * fAmp * 4.0 * master, 0));
	}).add;

	SynthDef(\slicer, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \sliceRate.kr(1.61803).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(18.7)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(18.8)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 0.5, 10.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		SendReply.kr(Impulse.kr(15), '/ui_slicer', [fAmp, fExt]);
		Out.ar(0, Pan2.ar(PlayBuf.ar(1, bufGaita2, BufRateScale.kr(bufGaita2), loop: 1) * LFPulse.kr(fExt, 0, 0.5).lag(0.01) * fAmp * 1.0 * master, 0));
	}).add;

	SynthDef(\reloxo_pechado, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \hitRate.kr(4.0).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(18.9)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(19.0)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 1.0, 15.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var trig = Impulse.kr(fExt);
		SendReply.kr(Impulse.kr(15), '/ui_reloxo', [fAmp, fExt]);
		Out.ar(0, Pan2.ar(PlayBuf.ar(1, bufPechado, BufRateScale.kr(bufPechado) * TRand.kr(0.85, 1.15, trig), trig) * fAmp * 1.2 * master, TRand.kr(-0.4, 0.4, trig)));
	}).add;

	SynthDef(\enxame_frullato, {
		var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \swarmPitch.kr(0.5).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(19.1)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(19.2)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 0.1, 2.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);
		SendReply.kr(Impulse.kr(15), '/ui_enxame', [fAmp, fExt]);
		Out.ar(0, Pan2.ar(Warp1.ar(1, bufFrullato, LFSaw.kr(0.5).range(0, 1), fExt, 0.1, -1, 8, 0.1, 4) * fAmp * 1.5 * master, 0));
	}).add;

	SynthDef(\campa_batimentos, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \freqBat.kr(1.5).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(19.3)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(19.4)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linlin(0, 1, 0.1, 10.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);

		var snd = Warp1.ar(1, bufCampaBat, LFSaw.kr(0.01).range(0.618, 0.718), 1, 0.2, -1, 8, 0.1);
		var sndEsq = BPF.ar(PitchShift.ar(snd, 0.1, 1.0, pitchDispersion: fExt/100), 277, 0.5) * 3;
		var sndDer = BPF.ar(PitchShift.ar(snd, 0.1, 1.0, pitchDispersion: (fExt*1.1)/100), 277, 0.5) * 3;
		SendReply.kr(Impulse.kr(15), '/ui_campa_bat', [fAmp, fExt]);
		Out.ar(0, [sndEsq, sndDer] * fAmp * 1.2 * master);
	}).add;

	SynthDef(\campa_resplandor, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \cola.kr(15).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(19.5)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(19.6)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 1.0, 30.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);

		var snd = Warp1.ar(1, bufCampaRes, LFNoise1.kr(0.05).range(0.1, 0.9), 1, 0.4, -1, 12, 0.1);
		snd = Mix([snd * SinOsc.kr(LFNoise2.kr(0.1).range(0.1, 0.3)).range(0.8, 1.0), PitchShift.ar(snd, 0.2, 2.0, 0.01, 0.01) * 1.5]);
		SendReply.kr(Impulse.kr(15), '/ui_campa_resp', [fAmp, fExt]);
		Out.ar(0, GVerb.ar(LPF.ar(snd, 6000), 100, fExt, 0.5, drylevel: 0.2, earlyreflevel: 0.5, taillevel: 0.8) * fAmp * 0.6 * master);
	}).add;

	SynthDef(\campa_granular, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \densidade.kr(40).lag(0.2);
		var lz1 = A2K.kr(LorenzL.ar(19.7)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(19.8)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 2.0, 400.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);

		var snd = Ringz.ar(Dust2.ar(fExt), 1200 * [1, 2.04, 2.58, 4.0, 5.16], [0.1, 0.2, 0.4, 0.1, 0.3]).sum * SinOsc.kr(0.2).range(0.4, 1.0);
		SendReply.kr(Impulse.kr(15), '/ui_campa_gran', [fAmp, fExt]);
		Out.ar(0, Pan2.ar(FreeVerb.ar(snd, 0.8, 0.95, 0.1) * fAmp * 0.7 * master, 0));
	}).add;

	SynthDef(\harm_fa_estatico, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \pan.kr(0).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(19.9)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(20.0)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linlin(0, 1, -1.0, 1.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);

		var snd = FreeVerb.ar(Warp1.ar(1, bufParcial, LFTri.kr(1/BufDur.kr(bufParcial)).range(0.1, 0.9), 1, 0.2, -1, 8, 0.1), 0.4, 0.8, 0.2);
		SendReply.kr(Impulse.kr(15), '/ui_harm_est', [fAmp, fExt]);
		Out.ar(0, Pan2.ar(snd * fAmp * 1.2 * master, fExt));
	}).add;

	SynthDef(\harm_fa_octa, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \notaRate.kr(3).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(20.1)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(20.2)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 0.5, 10.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(useLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(useLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1);

		var trig = Impulse.kr(fExt);
		var seq = Demand.kr(trig, 0, Dseq([-6, -5, -3, -2, 0, 1, 3, 4].midiratio, inf));
		var snd = PlayBuf.ar(1, bufParcial, BufRateScale.kr(bufParcial) * seq, trigger: trig, startPos: 0, loop: 1);
		SendReply.kr(Impulse.kr(15), '/ui_harm_oct', [fAmp, fExt]);
		Out.ar(0, Pan2.ar(FreeVerb.ar(snd * EnvGen.kr(Env.perc(0.01, 0.8), trig), 0.6, 0.9, 0.1) * fAmp * 1.0 * master, TRand.kr(-0.5, 0.5, trig)));
	}).add;

	// --- G7: RECONSTRUCIÓN ESPECTRAL (sen Lorenz; revela parciais aleatorios progresivamente) ---
	SynthDef(\reconstrucion, { |out=0, t_trig=0, amp=0, time=10|
		var ampL, timeL, master, phase, wipe, src, chain, sig;
		ampL = amp.lag(0.1);
		timeL = time.max(0.001);
		master = In.kr(~masterBus, 1).lag(0.1);
		// Sweep arranca en 0 ao recibir trigger e sobe a 1 en 'time' segundos.
		// Antes do primeiro trigger Sweep == 0  =>  wipe = 1 - 0 = 1 (todos os bins eliminados, silencio).
		// Despois do trigger, Sweep ramp 0->1 en 'time' segs => wipe 1->0 (vai destapando bins ata o son completo).
		phase = Sweep.kr(t_trig, 1.0 / timeL).clip(0, 1);
		wipe = 1.0 - phase;
		src = PlayBuf.ar(1, bufRonco, BufRateScale.kr(bufRonco), loop: 1);
		chain = FFT(LocalBuf(2048), src);
		// PV_RandComb elimina aleatoriamente bins (wipe=1 todos eliminados, wipe=0 ningún)
		// Re-aleatoriza con Impulse: novos parciais aparecen progresivamente segundo baixa wipe.
		chain = PV_RandComb(chain, wipe, Impulse.kr(8));
		sig = IFFT(chain);
		SendReply.kr(Impulse.kr(15), '/ui_reconstr', [ampL, phase]);
		Out.ar(out, Pan2.ar(sig * ampL * 1.2 * master, 0));
	}).add;

	SynthDef(\shep_risset, {
		var gLz = \globalLorenz.kr(0).lag(0.5);
		var aMan = \amp.kr(0).lag(0.1); var eMan = \speed.kr(-0.618).lag(0.1);
		var lz1 = A2K.kr(LorenzL.ar(20.3)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var lz2 = A2K.kr(LorenzL.ar(20.4)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1);
		var aLz = lz1 * 0.85; var eLz = lz2.linexp(0, 1, 0.1, 3.0);
		var oA = \overAmp.kr(0); var oE = \overExt.kr(0);
		var fAmp = SelectX.kr(oA, [SelectX.kr(gLz, [aMan, aLz]), aMan]); var fExt = SelectX.kr(oE, [SelectX.kr(gLz, [eMan, eLz]), eMan]);
		var master = In.kr(~masterBus, 1).lag(0.1); var baseRate = In.kr(~shepRateBus, 1).lag(0.1);

		var phase = Phasor.ar(0, fExt / (100 * SampleRate.ir), 0, 1);
		var sig = 10.collect({ |i|
			var voicePhase = (phase + (i / 10)).wrap(0, 1);
			Pan2.ar(PlayBuf.ar(1, bufRonco, BufRateScale.kr(bufRonco) * (baseRate * (2 ** ((voicePhase * 5) - 2.5))), loop: 1), SinOsc.ar(0.03 + (i * 0.005)) * 0.4 * ((i % 2 * 2) - 1)) * (sin(voicePhase * pi) ** 2);
		});
		sig = Mix(sig) / 3.5;
		SendReply.kr(Impulse.kr(15), '/ui_shep_solo', [fAmp, fExt], \replyID.kr(0));
		Out.ar(0, (sig + (FreeVerb2.ar(sig[0], sig[1], 0.1, 0.8, 0.8) * 0.15)) * fAmp * master);
	}).add;

	// Secundarios
	SynthDef(\explorador_xy, {
		var gLz = \globalLorenz.kr(0).lag(0.5); var locLz = \lorenz.kr(0).lag(0.1); var useLz = Clip.kr(gLz + locLz, 0, 1);
		var ampManual = \amp.kr(0.0).lag(0.1); var posXManual = \posX.kr(0.5).lag(0.1); var posYManual = \posY.kr(0.5).lag(0.1);
		var master = In.kr(~masterBus, 1).lag(0.1);
		var posX = SelectX.kr(useLz, [posXManual, A2K.kr(LorenzL.ar(20.5)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1)]);
		var posY = SelectX.kr(useLz, [posYManual, A2K.kr(LorenzL.ar(20.6)).lag(0.2).linlin(-9, 9, 0, 1).fold(0, 1)]);
		var trig = Dust.ar(LinExp.kr(posY, 0.0, 1.0, 5, 200));
		Out.ar(0, TGrains.ar(2, trig, bufGaita, LinExp.kr(posY, 0.0, 1.0, 0.5, 1.5), posX * BufDur.kr(bufGaita), 0.15, TRand.kr(-0.8, 0.8, trig), 0.8) * ampManual * master);
	}).add;

	SynthDef(\ca_player, {
		var out = 0, buf = bufPandeireta, rateManual = \rate.kr(1.0);
		var gLz = \globalLorenz.kr(0).lag(0.5);
		var caAmp = In.kr(~caVolBus, 1).lag(0.1); var master = In.kr(~masterBus, 1).lag(0.1);
		var rate = SelectX.kr(gLz, [rateManual, rateManual * A2K.kr(LorenzL.ar(20.7)).lag(0.2).linlin(-9, 9, 0.5, 3.0).fold(0.5, 3.0)]);
		var amp = caAmp * SelectX.kr(gLz, [1.0, A2K.kr(LorenzL.ar(20.8)).lag(0.2).linlin(-9, 9, 0.2, 1.5).fold(0.2, 1.5)]);
		Out.ar(out, Pan2.ar(PlayBuf.ar(1, buf, BufRateScale.kr(buf) * rate, startPos: IRand(0, BufFrames.ir(buf) * 0.8)) * EnvGen.ar(Env.perc(0.001, 0.1), doneAction: 2) * amp * master, Rand(-0.5, 0.5)));
	}).add;

	s.sync;

	~xySynth = Synth(\explorador_xy, [\amp, 0.0]);
	~shepEnxameGrp = Group.new;
	fork { 6.do { |i| Synth(\shep_risset, [\amp, 0.0, \speed, -0.618], target: ~shepEnxameGrp); 0.1.wait; }; };

	~saidaScarlett = Synth(\crossover_pas, [\corte, 200], target: s, addAction: \addToTail);

	stateArray = Array.fill(16, { [0, 1].choose });
	rule30 = { |state| var nextState = Array.newClear(state.size); state.size.do { |i| nextState[i] = (30 >> ((state.wrapAt(i - 1) << 2) | (state[i] << 1) | state.wrapAt(i + 1))) & 1; }; nextState; };
	caTask = Task({ var index = 0; loop { if(stateArray[index] == 1) { Synth(\ca_player, [\rate, 0.8 + (stateArray.sum * 0.05), \globalLorenz, ~glbzState]); }; index = index + 1; if(index >= stateArray.size) { index = 0; stateArray = rule30.value(stateArray); }; 0.0625.wait; } });

	~mostrarAxuda = { |titulo, descricion| var infoWin = Window(titulo, Rect(Window.screenBounds.width/2 - 150, Window.screenBounds.height/2 - 75, 300, 150), border: true); StaticText(infoWin, Rect(15, 15, 270, 120)).string_(descricion).font_(Font("Helvetica", 13)).align_(\topLeft); infoWin.front; };

	// --- 6. INTERFACE GRÁFICA ---
	defer {
		var cGr1 = Color.red(0.6), cGr2 = Color.blue(0.6), cGr3 = Color.new255(200, 100, 0), cGr4 = Color.magenta(0.6), cGr5 = Color.green(0.6), cGr6 = Color.cyan(0.7), cGr7 = Color.new255(180, 140, 0);
		var topRow, bottomRow, makeSep, g1Layout, g2Layout, g3Layout, g4Layout, g5Layout, g6Layout, g7Layout, masterLayout;
		var colCaVol2d, caTitleLayout, caVolLabel, caVolSlider, caBtn, xyVolTitleLayout, xyVolLabel, xyVolSlider, xyBtn, xyPadCol, xyPad, xyLzBtn;
		var mTitleLayout, mTitle, mInfoBtn, mVolLabel, mVolSlider, lzGlobalBtn, muteBtn, colShepRate, srTitle, srLbl, srSl;
		var metronomoBtn;
		var g7AmpLabel, g7AmpSlider, g7TimeSpec, g7TimeLabel, g7TimeSlider, g7StartBtn, g7Col;
		~glbzState = 0;
		~metronomoPlayer = nil;
		~volSliders = (); // Dicionario de sliders de volume por synthKey (para captura Lorenz)

		// --- COMUNICACIÓN BIDIRECCIONAL CON OPEN STAGE CONTROL (porto 8000) ---
		~oscOut = NetAddr("127.0.0.1", 8000);
		// Bandeira para evitar loops infinitos: cando o cambio veu da tablet, non reenviar
		~fromOSC = false;
		~sendOSC = { |path, val| if(~fromOSC.not) { ~oscOut.sendMsg(path, val) } };

		synths = (
			abismo: Synth(\abismo), lume_petr: Synth(\lume_petrushka), lume_re9: Synth(\lume_re9), estalidos: Synth(\estalidos_lume), ronco_enxame: Synth(\enxame_harmonico),
			sismico: Synth(\motor_sismico), tectonico: Synth(\bombo_tectonico), magma: Synth(\magma_granular), asubiador: Synth(\asubiador), halo: Synth(\halo_xelado),
			choiva: Synth(\choiva_cristal), soplete: Synth(\soplete_plasma), pand_gran: Synth(\pandeireta_glitch), pand_norm: Synth(\pandeireta_normal),
			espectro: Synth(\espectro_conxelado), pantasmas: Synth(\pantasmas), slicer: Synth(\slicer), reloxo: Synth(\reloxo_pechado), enxame: Synth(\enxame_frullato), sub: Synth(\sub_lume),
			campa_bat: Synth(\campa_batimentos), campa_resp: Synth(\campa_resplandor), campa_gran: Synth(\campa_granular), harm_est: Synth(\harm_fa_estatico), harm_oct: Synth(\harm_fa_octa),
			shep_solo: Synth(\shep_risset, [\amp, 0.0, \speed, -0.618, \replyID, 1]), shep_enxame: ~shepEnxameGrp,
			reconstrucion: Synth(\reconstrucion, [\amp, 0, \time, 10])
		);

		CmdPeriod.doOnce { Window.closeAll };
		win = Window("Mesa Electroacústica", Rect(10, 10, 1350, 850));
		win.onClose = { synths.do(_.free); ~xySynth.free; ~saidaScarlett.free; caTask.stop; if(~metronomoPlayer.notNil) { ~metronomoPlayer.stop }; OSCdef.all.copy.do(_.free); };
		win.layout = VLayout().spacing_(15);
		topRow = HLayout().spacing_(8); bottomRow = HLayout().spacing_(8);
		makeSep = { StaticText().string_("||").font_(Font("Helvetica", 16)).align_(\center).fixedWidth_(5) };

		~makeCol = { |nome, synthKey, extraParam, extraSpec, tenLorenz=true, descricion="", corTitulo, oscPath, replyID= -1|
			var col = VLayout().spacing_(2);
			var titleLayout = HLayout().spacing_(1);
			var title = StaticText().string_(nome).align_(\center).font_(Font("Helvetica", 10, true)).stringColor_(corTitulo ? Color.black);
			var infoBtn = Button().states_([["?", Color.white, Color.grey(0.4)]]).maxWidth_(14).maxHeight_(14).action_({ ~mostrarAxuda.value(nome, descricion) });

			var volLabel = StaticText().string_("Vol: 0.0").align_(\center).font_(Font("Helvetica", 9));
			var volSlider = Slider().orientation_(\vertical).value_(0);
			var extraLabel = StaticText().string_(extraSpec.units ++ ":" ++ extraSpec.default.round(0.01)).align_(\center).font_(Font("Helvetica", 9));
			var extraSlider = Slider().orientation_(\vertical).value_(extraSpec.unmap(extraSpec.default));
			var mdAmp = false, mdExt = false;
			var lzBtn = nil, bypassBtn = nil;
			var oscBase = "/osc/" ++ synthKey.asString;

			// Gardar referencia para captura ao desactivar Lorenz (despois de todos os var)
			~volSliders[synthKey] = volSlider;

			// --- Acción do fader de volume: cambia o synth, etiqueta e reenvía á tablet (se non vén dela) ---
			volSlider.action_({ |sl|
				synths[synthKey].set(\amp, sl.value);
				volLabel.string_("Vol: " ++ sl.value.round(0.01));
				~sendOSC.value(oscBase ++ "/amp", sl.value.asFloat);
			});
			extraSlider.action_({ |sl|
				var rVal = extraSpec.map(sl.value);
				synths[synthKey].set(extraParam, rVal);
				extraLabel.string_(extraSpec.units ++ ":" ++ rVal.round(0.01));
				if(synthKey == \reloxo) { synths[\slicer].set(\sliceRate, rVal * 1.41421356); };
				~sendOSC.value(oscBase ++ "/" ++ extraParam.asString, sl.value.asFloat);
			});

			volSlider.mouseDownAction_({ mdAmp = true; synths[synthKey].set(\overAmp, 1); });
			volSlider.mouseUpAction_({ mdAmp = false; synths[synthKey].set(\overAmp, 0); });
			extraSlider.mouseDownAction_({ mdExt = true; synths[synthKey].set(\overExt, 1); });
			extraSlider.mouseUpAction_({ mdExt = false; synths[synthKey].set(\overExt, 0); });

			// --- SendReply do motor Lorenz: actualiza UI local + reenvía á tablet en valor normalizado ---
			if(oscPath.notNil) {
				OSCdef(synthKey, { |msg|
					if(replyID == -1 or: { msg[2] == replyID }) {
						var ampVal = msg[3];
						var extVal = msg[4];
						defer {
							if(mdAmp.not) {
								~fromOSC = true;
								volSlider.value_(ampVal);
								~fromOSC = false;
								volLabel.string_("Vol: " ++ ampVal.round(0.01));
								~oscOut.sendMsg(oscBase ++ "/amp", ampVal.asFloat);
							};
							if(extVal.notNil and: { mdExt.not }) {
								var u = extraSpec.unmap(extVal);
								~fromOSC = true;
								extraSlider.value_(u);
								~fromOSC = false;
								extraLabel.string_(extraSpec.units ++ ":" ++ extVal.round(0.01));
								~oscOut.sendMsg(oscBase ++ "/" ++ extraParam.asString, u.asFloat);
							};
						};
					}
				}, oscPath);
			};

			titleLayout.add(nil); titleLayout.add(title); titleLayout.add(infoBtn);
			col.add(titleLayout); col.add(volLabel); col.add(volSlider);

			if(synthKey == \pand_norm) {
				bypassBtn = Button().states_([["Mel", Color.white, Color.blue(0.6)], ["Lmp", Color.black, Color.gray(0.8)]]).value_(1).action_({ |b|
					synths[synthKey].set(\bypass, b.value);
					~sendOSC.value(oscBase ++ "/bypass", b.value);
				});
				col.add(bypassBtn);
			} {
				if(tenLorenz) {
					lzBtn = Button().states_([["LZ OFF", Color.black, Color.gray(0.8)], ["LZ ON", Color.white, Color.red(0.6)]]).value_(0).action_({ |b|
						if(b.value == 0) {
							// Captura o nivel actual de Lorenz e mantén o son exactamente igual
							synths[synthKey].set(\amp, volSlider.value, \lorenz, 0);
						} {
							synths[synthKey].set(\lorenz, 1);
						};
						~sendOSC.value(oscBase ++ "/lz", b.value);
					});
					col.add(lzBtn);
				} {
					col.add(StaticText().string_("").minHeight_(20));
				};
			};

			if(synthKey == \sub) { extraSlider.visible_(false); extraLabel.visible_(false); };
			col.add(extraLabel); col.add(extraSlider);

			// --- OSC IN: faders dende a tablet (con bandeira fromOSC para evitar loop) ---
			OSCdef((oscBase ++ "/amp").asSymbol, { |m|
				var v = m[1].asFloat.clip(0, 1);
				defer {
					~fromOSC = true;
					volSlider.valueAction_(v);
					~fromOSC = false;
				};
			}, oscBase ++ "/amp");

			if(synthKey != \sub) {
				OSCdef((oscBase ++ "/" ++ extraParam.asString).asSymbol, { |m|
					var v = m[1].asFloat.clip(0, 1);
					defer {
						~fromOSC = true;
						extraSlider.valueAction_(v);
						~fromOSC = false;
					};
				}, oscBase ++ "/" ++ extraParam.asString);
			};

			// --- OSC IN: TOGGLE Lorenz dende a tablet ---
			// Lectura limpa de 0/1, aplicación directa ao Synth E actualización visual da UI dentro de defer
			if(lzBtn.notNil) {
				OSCdef((oscBase ++ "/lz").asSymbol, { |m|
					var v = (m[1].asFloat > 0).asInteger;
					// 1) Aplicar directamente ao Synth (garante que apaga e acende)
					if(v == 0) {
						synths[synthKey].set(\amp, volSlider.value, \lorenz, 0);
					} {
						synths[synthKey].set(\lorenz, 1);
					};
					// 2) Refrescar o botón da UI local sen disparar a acción (evita reenvío)
					defer {
						~fromOSC = true;
						lzBtn.value_(v);
						~fromOSC = false;
					};
				}, oscBase ++ "/lz");
			};

			// --- OSC IN: TOGGLE Bypass (pand_norm) dende a tablet ---
			if(bypassBtn.notNil) {
				OSCdef((oscBase ++ "/bypass").asSymbol, { |m|
					var v = (m[1].asFloat > 0).asInteger;
					synths[synthKey].set(\bypass, v);
					defer {
						~fromOSC = true;
						bypassBtn.value_(v);
						~fromOSC = false;
					};
				}, oscBase ++ "/bypass");
			};

			col;
		};

		g1Layout = VLayout(StaticText().string_("G1: GRAVES / LUME").align_(\center).font_(Font("Helvetica", 11, true)).stringColor_(cGr1).background_(Color.white(0.9)),
			HLayout(
				~makeCol.value("Ronco Enx", \ronco_enxame, \detune, ControlSpec(0.001, 0.05, 'exp', 0, 0.01, "Det"), true, "", cGr1, '/ui_ronco_enxame'),
				~makeCol.value("Lu(Petr)", \lume_petr, \resDecay, ControlSpec(0.1, 8.0, 'exp', 0, 3.0, "Dec"), true, "", cGr1, '/ui_lume_petr'),
				~makeCol.value("Lu(Re9)", \lume_re9, \resDecay, ControlSpec(0.1, 8.0, 'exp', 0, 3.0, "Dec"), true, "", cGr1, '/ui_lume_re9'),
				~makeCol.value("Sub", \sub, \amp, ControlSpec(0, 1, 'lin', 0, 0, ""), true, "", cGr1, '/ui_sub'),

				// --- CONTROLADOR DA UI MODIFICADO PARA O NOVO MOTOR SÍSMICO (paso de '1' forzando saltos enteiros de 0 a 3Hz) ---
				~makeCol.value("M. Sísm", \sismico, \desfase, ControlSpec(0, 3, 'lin', 1, 0, "Hz"), true, "", cGr1, '/ui_sismico'),

				~makeCol.value("B. Tect", \tectonico, \resDecay, ControlSpec(1.0, 10.0, 'exp', 0, 4.0, "Dec"), true, "", cGr1, '/ui_tectonico'),
				~makeCol.value("Magma", \magma, \density, ControlSpec(2, 60, 'exp', 0, 20, "Fric."), true, "", cGr1, '/ui_magma')
			)
		);

		g2Layout = VLayout(StaticText().string_("G2: ATMOSFERAS / CAMPÁS").align_(\center).font_(Font("Helvetica", 11, true)).stringColor_(cGr2).background_(Color.white(0.9)),
			HLayout(
				~makeCol.value("Dr. Gaita", \abismo, \verbMix, ControlSpec(0.1, 1.0, 'lin', 0, 0.5, "Rev"), true, "", cGr2, '/ui_abismo'),
				~makeCol.value("Pantas.", \pantasmas, \feedback, ControlSpec(0.1, 0.95, 'lin', 0, 0.5, "Eco"), true, "", cGr2, '/ui_pantasmas'),
				~makeCol.value("Frullato", \enxame, \swarmPitch, ControlSpec(0.1, 2.0, 'exp', 0, 0.5, "Ptch"), true, "", cGr2, '/ui_enxame'),
				~makeCol.value("C. Batim", \campa_bat, \freqBat, ControlSpec(0.1, 10.0, 'lin', 0, 1.5, "Vib"), true, "", cGr2, '/ui_campa_bat'),
				~makeCol.value("C. Respl", \campa_resp, \cola, ControlSpec(1, 30, 'lin', 0, 15, "Rev"), true, "", cGr2, '/ui_campa_resp')
			)
		);

		g3Layout = VLayout(StaticText().string_("G3: RITMO").align_(\center).font_(Font("Helvetica", 11, true)).stringColor_(cGr3).background_(Color.white(0.9)),
			HLayout(
				~makeCol.value("Slicer", \slicer, \sliceRate, ControlSpec(0.5, 10.0, 'exp', 0, 1.618, "Hz"), true, "", cGr3, '/ui_slicer'),
				~makeCol.value("Reloxo", \reloxo, \hitRate, ControlSpec(1.0, 15.0, 'exp', 0, 4.0, "Hz"), true, "", cGr3, '/ui_reloxo')
			)
		);

		topRow.add(g1Layout); topRow.add(makeSep.value); topRow.add(g2Layout); topRow.add(makeSep.value); topRow.add(g3Layout); topRow.add(nil);

		g4Layout = VLayout(StaticText().string_("G4: XEO / VENTO (FA#)").align_(\center).font_(Font("Helvetica", 11, true)).stringColor_(cGr4).background_(Color.white(0.9)),
			HLayout(
				~makeCol.value("Halo Xel.", \halo, \shimmer, ControlSpec(0.1, 1.0, 'lin', 0, 0.8, "Mix"), true, "", cGr4, '/ui_halo'),
				~makeCol.value("Soplete", \soplete, \drive, ControlSpec(1.0, 15.0, 'exp', 0, 3.0, "Dist"), true, "", cGr4, '/ui_soplete'),
				~makeCol.value("Fa# Vento", \harm_est, \pan, ControlSpec(-1.0, 1.0, 'lin', 0, 0.0, "Pan"), true, "", cGr4, '/ui_harm_est'),
				~makeCol.value("Fa# Octa", \harm_oct, \notaRate, ControlSpec(0.5, 10.0, 'exp', 0, 3.0, "Vel"), true, "", cGr4, '/ui_harm_oct')
			)
		);

		colCaVol2d = VLayout().spacing_(2);
		caTitleLayout = HLayout().spacing_(2); caTitleLayout.add(nil); caTitleLayout.add(StaticText().string_("Autómata").align_(\center).font_(Font("Helvetica", 10, true)).stringColor_(cGr5)); colCaVol2d.add(caTitleLayout);
		caVolLabel = StaticText().string_("Vol: 0.50").align_(\center).font_(Font("Helvetica", 9));
		caVolSlider = Slider().orientation_(\vertical).maxHeight_(120).value_(0.5).action_({ |sl|
			~caVolBus.set(sl.value);
			caVolLabel.string_("Vol: " ++ sl.value.round(0.01));
			~sendOSC.value("/osc/ca/amp", sl.value.asFloat);
		});
		caBtn = Button().states_([["CA OFF", Color.black, Color.gray(0.8)], ["CA ON", Color.white, Color.red(0.6)]]).action_({ |b|
			if(b.value == 1) { caTask.play; } { caTask.stop; };
			~sendOSC.value("/osc/ca/on", b.value);
		});
		colCaVol2d.add(caVolLabel); colCaVol2d.add(caVolSlider); colCaVol2d.add(caBtn); colCaVol2d.add(StaticText().string_("---").align_(\center).font_(Font("Helvetica", 8)).stringColor_(Color.gray));

		xyVolTitleLayout = HLayout().spacing_(2); xyVolTitleLayout.add(nil); xyVolTitleLayout.add(StaticText().string_("Vol 2D").align_(\center).font_(Font("Helvetica", 10, true)).stringColor_(cGr5)); colCaVol2d.add(xyVolTitleLayout);
		xyVolLabel = StaticText().string_("Vol: 0.80").align_(\center).font_(Font("Helvetica", 9));
		xyVolSlider = Slider().orientation_(\vertical).maxHeight_(120).value_(0.8);
		xyBtn = Button().states_([["2D OFF", Color.black, Color.gray(0.8)], ["2D ON", Color.white, cGr5]]).value_(0);
		xyVolSlider.action_({ |sl|
			~xyMaxAmp = sl.value;
			xyVolLabel.string_("Vol: " ++ sl.value.round(0.01));
			if(xyBtn.value == 1) { ~xySynth.set(\amp, ~xyMaxAmp); };
			~sendOSC.value("/osc/xy/amp", sl.value.asFloat);
		});
		xyBtn.action_({ |b|
			if(b.value == 1) { ~xySynth.set(\amp, ~xyMaxAmp); } { ~xySynth.set(\amp, 0.0); };
			~sendOSC.value("/osc/xy/on", b.value);
		});
		colCaVol2d.add(xyVolLabel); colCaVol2d.add(xyVolSlider); colCaVol2d.add(xyBtn); colCaVol2d.add(nil);

		xyPadCol = VLayout(); xyPadCol.add(StaticText().string_("Navegación 2D").align_(\center).font_(Font("Helvetica", 10, true)).stringColor_(cGr5));
		xyPad = Slider2D().fixedWidth_(140).fixedHeight_(140).background_(Color.black).knobColor_(Color.cyan);
		xyPad.action_({ |sl|
			~xySynth.set(\posX, sl.x, \posY, sl.y);
			if(~fromOSC.not) { ~oscOut.sendMsg("/osc/xy/pad", sl.x.asFloat, sl.y.asFloat); };
		});
		xyLzBtn = Button().states_([["LZ 2D OFF", Color.black, Color.gray(0.8)], ["LZ 2D ON", Color.white, Color.red(0.6)]]).action_({ |b| ~xySynth.set(\lorenz, b.value); });
		xyPadCol.add(xyPad); xyPadCol.add(xyLzBtn); xyPadCol.add(nil);

		g5Layout = VLayout(StaticText().string_("G5: PERCUSIÓN / I.A.").align_(\center).font_(Font("Helvetica", 11, true)).stringColor_(cGr5).background_(Color.white(0.9)),
			HLayout(
				~makeCol.value("Pandeir.", \pand_norm, \cutoff, ControlSpec(200, 4000, 'exp', 0, 2093, "Hz"), false, "", cGr5, '/ui_pand_norm'),
				~makeCol.value("P. Gran", \pand_gran, \density, ControlSpec(1, 50, 'exp', 0, 15, "Gr/s"), true, "", cGr5, '/ui_pand_gran'),
				~makeCol.value("Estalidos", \estalidos, \brillo, ControlSpec(2000, 8000, 'exp', 0, 4434.92, "Hz"), true, "", cGr5, '/ui_estalidos'),
				~makeCol.value("Asubiad.", \asubiador, \rate, ControlSpec(1.0, 20.0, 'exp', 0, 8.0, "Hz"), true, "", cGr5, '/ui_asubiador'),
				~makeCol.value("C. Gran", \campa_gran, \densidade, ControlSpec(2, 400, 'exp', 0, 40, "Gr/s"), true, "", cGr5, '/ui_campa_gran'),
				colCaVol2d, xyPadCol
			)
		);

		colShepRate = VLayout().spacing_(2); srTitle = HLayout().spacing_(1); srTitle.add(nil); srTitle.add(StaticText().string_("Ton Base").align_(\center).font_(Font("Helvetica", 10, true)).stringColor_(cGr6)); colShepRate.add(srTitle);
		srLbl = StaticText().string_("x1.00").align_(\center).font_(Font("Helvetica", 9));
		srSl = Slider().orientation_(\vertical).value_(ControlSpec(0.25, 4.0, 'exp').unmap(1.0)).action_({ |sl|
			var val = ControlSpec(0.25, 4.0, 'exp').map(sl.value);
			~shepRateBus.set(val);
			srLbl.string_("x" ++ val.round(0.01));
			~sendOSC.value("/osc/shep/baserate", sl.value.asFloat);
		});
		colShepRate.add(srLbl); colShepRate.add(srSl); colShepRate.add(StaticText().string_("").minHeight_(50));

		g6Layout = VLayout(StaticText().string_("G6: ILUSIÓN SHEPARD").align_(\center).font_(Font("Helvetica", 11, true)).stringColor_(cGr6).background_(Color.white(0.9)),
			HLayout(
				~makeCol.value("Shp. Solo", \shep_solo, \speed, ControlSpec(-3.0, 3.0, 'lin', 0, -0.618, "Vel."), false, "", cGr6, '/ui_shep_solo', 1),
				~makeCol.value("Shp. Enx", \shep_enxame, \speed, ControlSpec(-3.0, 3.0, 'lin', 0, -0.618, "Vel."), false, "", cGr6, nil),
				colShepRate
			)
		);

		masterLayout = VLayout(StaticText().string_("SAÍDA").align_(\center).font_(Font("Helvetica", 11, true)).stringColor_(Color.red(0.8)).background_(Color.white(0.9)),
			VLayout(
				HLayout(nil, StaticText().string_("MASTER").align_(\center).font_(Font("Helvetica", 10, true)).stringColor_(Color.red(0.6))),
				mVolLabel = StaticText().string_("Vol: 1.00").align_(\center).font_(Font("Helvetica", 9)),
				mVolSlider = Slider().orientation_(\vertical).value_(1.0).action_({ |sl|
					mVolLabel.string_("Vol: " ++ sl.value.round(0.01));
					if(muteBtn.value == 0) { ~masterBus.set(sl.value); };
					~sendOSC.value("/osc/master/amp", sl.value.asFloat);
				}),

				metronomoBtn = Button().states_([["Metrónomo OFF", Color.black, Color.gray(0.8)], ["Metrónomo ON", Color.white, Color.magenta(0.6)]]).value_(0).action_({ |b|
					if(b.value == 1) {
						~metronomoPlayer = Pbind(\instrument, \tic_ferrenas, \dur, 1, \amp, 0.05).play;
					} {
						if(~metronomoPlayer.notNil) { ~metronomoPlayer.stop };
					};
					~sendOSC.value("/osc/master/metro", b.value);
				}),

				lzGlobalBtn = Button().states_([["GLBZ CAOS OFF", Color.black, Color.gray(0.8)], ["GLBZ CAOS ON", Color.white, Color.blue(0.8)]]).value_(0).action_({ |b|
					~glbzState = b.value;
					if(b.value == 0) {
						// Captura o nivel actual de cada sintetizador antes de desactivar GlobalLorenz
						synths.keysValuesDo { |k, synth|
							if(k != \pand_norm and: { k != \enxame and: { k != \reconstrucion } }) {
								if(~volSliders[k].notNil) {
									synth.set(\amp, ~volSliders[k].value, \globalLorenz, 0);
								} {
									synth.set(\globalLorenz, 0);
								};
							};
						};
					} {
						synths.keysValuesDo { |k, synth|
							if(k != \pand_norm and: { k != \enxame and: { k != \reconstrucion } }) {
								synth.set(\globalLorenz, 1);
							};
						};
					};
					~xySynth.set(\globalLorenz, b.value);
					~sendOSC.value("/osc/master/glbz", b.value);
				}),
				muteBtn = Button().states_([["Son ON", Color.black, Color.green(0.7)], ["MUTE", Color.white, Color.red(0.7)]]).value_(0).action_({ |b|
					if(b.value == 1) { ~masterBus.set(0.0); } { ~masterBus.set(mVolSlider.value); };
					~sendOSC.value("/osc/master/mute", b.value);
				})
			)
		);

		// --- G7: RECONSTRUCIÓN ESPECTRAL (sen Lorenz) ---
		g7TimeSpec = ControlSpec(1.0, 30.0, 'lin', 0, 10.0, "s");
		g7AmpLabel = StaticText().string_("Vol: 0.0").align_(\center).font_(Font("Helvetica", 9));
		g7AmpSlider = Slider().orientation_(\vertical).value_(0).action_({ |sl|
			synths[\reconstrucion].set(\amp, sl.value); g7AmpLabel.string_("Vol: " ++ sl.value.round(0.01));
			~sendOSC.value("/osc/g7/amp", sl.value.asFloat);
		});
		~volSliders[\reconstrucion] = g7AmpSlider;
		g7TimeLabel = StaticText().string_("Tempo: 10.0 s").align_(\center).font_(Font("Helvetica", 9));
		g7TimeSlider = Slider().orientation_(\vertical).value_(g7TimeSpec.unmap(g7TimeSpec.default)).action_({ |sl|
			var v = g7TimeSpec.map(sl.value);
			synths[\reconstrucion].set(\time, v); g7TimeLabel.string_("Tempo: " ++ v.round(0.1) ++ " s");
			~sendOSC.value("/osc/g7/time", sl.value.asFloat);
		});
		g7StartBtn = Button().states_([["START", Color.white, cGr7]]).action_({
			synths[\reconstrucion].set(\t_trig, 1);
			if(~fromOSC.not) { ~oscOut.sendMsg("/osc/g7/start", 1) };
		});
		g7Col = VLayout(
			HLayout(nil, StaticText().string_("Reconstrución").align_(\center).font_(Font("Helvetica", 10, true)).stringColor_(cGr7), nil),
			g7AmpLabel, g7AmpSlider,
			g7TimeLabel, g7TimeSlider,
			g7StartBtn
		);
		g7Layout = VLayout(
			StaticText().string_("G7: RECONSTRUCIÓN").align_(\center).font_(Font("Helvetica", 11, true)).stringColor_(cGr7).background_(Color.white(0.9)),
			HLayout(g7Col)
		);

		// G7 colócase XUSTO Á ESQUERDA do masterLayout
		bottomRow.add(g4Layout); bottomRow.add(makeSep.value); bottomRow.add(g5Layout); bottomRow.add(makeSep.value); bottomRow.add(g6Layout); bottomRow.add(makeSep.value); bottomRow.add(g7Layout); bottomRow.add(makeSep.value); bottomRow.add(masterLayout); bottomRow.add(nil);

		// --- OSC IN: G7 ---
		OSCdef(\g7_amp_in, { |m|
			var v = m[1].asFloat.clip(0, 1);
			defer { ~fromOSC = true; g7AmpSlider.valueAction_(v); ~fromOSC = false; };
		}, "/osc/g7/amp");
		OSCdef(\g7_time_in, { |m|
			// Acepta valor normalizado 0..1 (envío directo do fader de O.S.C.)
			var v = m[1].asFloat.clip(0, 1);
			defer { ~fromOSC = true; g7TimeSlider.valueAction_(v); ~fromOSC = false; };
		}, "/osc/g7/time");
		OSCdef(\g7_start_in, { |m|
			// Trigger ao recibir calquera valor > 0 (compatible con botón momentáneo)
			if(m[1].asFloat > 0) {
				synths[\reconstrucion].set(\t_trig, 1);
			};
		}, "/osc/g7/start");

		// --- OSC IN: MASTER / GLOBAIS ---
		OSCdef(\master_amp_in, { |m|
			var v = m[1].asFloat.clip(0, 1);
			defer { ~fromOSC = true; mVolSlider.valueAction_(v); ~fromOSC = false; };
		}, "/osc/master/amp");
		OSCdef(\master_mute_in, { |m|
			var v = (m[1].asFloat > 0).asInteger;
			// Aplicar directamente E refrescar a UI dentro de defer
			if(v == 1) { ~masterBus.set(0.0) } { ~masterBus.set(mVolSlider.value) };
			defer { ~fromOSC = true; muteBtn.value_(v); ~fromOSC = false; };
		}, "/osc/master/mute");
		OSCdef(\master_glbz_in, { |m|
			var v = (m[1].asFloat > 0).asInteger;
			defer { ~fromOSC = true; lzGlobalBtn.valueAction_(v); ~fromOSC = false; };
		}, "/osc/master/glbz");
		OSCdef(\master_metro_in, { |m|
			var v = (m[1].asFloat > 0).asInteger;
			defer { ~fromOSC = true; metronomoBtn.valueAction_(v); ~fromOSC = false; };
		}, "/osc/master/metro");

		// --- OSC IN: AUTÓMATA ---
		OSCdef(\ca_amp_in, { |m|
			var v = m[1].asFloat.clip(0, 1);
			defer { ~fromOSC = true; caVolSlider.valueAction_(v); ~fromOSC = false; };
		}, "/osc/ca/amp");
		OSCdef(\ca_on_in, { |m|
			var v = (m[1].asFloat > 0).asInteger;
			defer { ~fromOSC = true; caBtn.valueAction_(v); ~fromOSC = false; };
		}, "/osc/ca/on");

		// --- OSC IN: NAVEGACIÓN 2D / XY ---
		OSCdef(\xy_amp_in, { |m|
			var v = m[1].asFloat.clip(0, 1);
			defer { ~fromOSC = true; xyVolSlider.valueAction_(v); ~fromOSC = false; };
		}, "/osc/xy/amp");
		OSCdef(\xy_on_in, { |m|
			var v = (m[1].asFloat > 0).asInteger;
			defer { ~fromOSC = true; xyBtn.valueAction_(v); ~fromOSC = false; };
		}, "/osc/xy/on");
		OSCdef(\xy_pad_in, { |m|
			var x = m[1].asFloat.clip(0, 1);
			var y = m[2].asFloat.clip(0, 1);
			~xySynth.set(\posX, x, \posY, y);
			defer { ~fromOSC = true; xyPad.setXY(x, y); ~fromOSC = false; };
		}, "/osc/xy/pad");

		// --- OSC IN: SHEPARD BASE RATE ---
		OSCdef(\shep_baserate_in, { |m|
			var v = m[1].asFloat.clip(0, 1);
			defer { ~fromOSC = true; srSl.valueAction_(v); ~fromOSC = false; };
		}, "/osc/shep/baserate");

		win.layout.add(topRow); win.layout.add(StaticText().string_("==========================================================================================================").align_(\center).font_(Font("Helvetica", 12)).stringColor_(Color.gray(0.7))); win.layout.add(bottomRow); win.layout.add(nil);
		win.front;
		("Open Stage Control: enviar OSC ao porto sclang " ++ NetAddr.langPort.asString ++ " (127.0.0.1). Saída cara á tablet en 127.0.0.1:8000.").postln;
	};
});