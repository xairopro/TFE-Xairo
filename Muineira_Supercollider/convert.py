import os
import librosa
import soundfile as sf

# O script buscará no cartafol onde estea gardado
directorio = "."
frecuencia_obxectivo = 48000

print(f"--- Iniciando unificación a {frecuencia_obxectivo}Hz ---")

for arquivo in os.listdir(directorio):
    if arquivo.endswith(".wav"):
        ruta_completa = os.path.join(directorio, arquivo)
        print(f"Procesando e sobreescribindo: {arquivo}")
        
        # Carga o audio. 'sr=frecuencia_obxectivo' forzará o resample se fai falla.
        # mono=False mantén o estéreo se o audio é estéreo.
        audio, sr = librosa.load(ruta_completa, sr=frecuencia_obxectivo, mono=False)
        
        # Soundfile necesita a matriz transposta se é estéreo
        if audio.ndim > 1:
            audio = audio.T
            
        # Sobreescribe o arquivo coa calidade correcta
        sf.write(ruta_completa, audio, frecuencia_obxectivo)

print("--- Feito! Todo o teu audio é agora 100% estándar e compatible. ---")