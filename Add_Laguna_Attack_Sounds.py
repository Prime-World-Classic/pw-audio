# -*- coding: utf-8 -*-
"""Добавляет в FMOD-проект события автоатаки Laguna (рыбки) по образцу событий дельфина:
  SFX/Laguna_AttackCast - вылет, one-shot, случайный выбор (randomnorepeat) из 4 вариантов
  SFX/Laguna_AttackHit  - попадание, так же из 4 вариантов
wav-файлы: SFXNew/<имя>_1..4.wav (банк SFX, sounddef /SFX3/<имя>).
Звуки - присланный пользователем референс (Шедеврум, 4c99bdb8f535c24.mp3): _1 как есть, _2.._4 сдвинуты на +1/-1/+2 полутона
(pedalboard PitchShift), у всех лёгкий Reverb(room 0.35, wet 0.18), громкость ~ -17.5 LUFS (медиана атак героев -18.6).
Попадание - мягкое «тело» того же звука без яркого начала, темнее и короче, те же сдвиги тона, ~ -23.5 LUFS.
Патчит PrimeWorldtest.fdp и PrimeWorld.fdp (резервная копия *.fdp.before_<имя>), уже добавленные события пропускает.
Затем: fmod_designercl -pc -S SFX PrimeWorldtest.fdp и скопировать PrimeWorld.fev + SFX.fsb в Data\\Audio.
"""
import os, re, shutil, uuid
import xml.dom.minidom

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = "Laguna_DolphinDive"
NAMES = ["Laguna_AttackCast", "Laguna_AttackHit"]

def new_guids(block):
    return re.sub(r"<guid>\{[0-9a-fA-F-]{36}\}</guid>", lambda m: "<guid>{%s}</guid>" % uuid.uuid4(), block)

def find(text, pattern):
    m = re.search(pattern, text, re.S)
    if not m:
        raise SystemExit("block not found: " + pattern[:80])
    return m

def patch(path, NAME):
    WAVS = ["%s_%d" % (NAME, i) for i in range(1, 5)]
    with open(path, "rb") as f:
        text = f.read().decode("utf-8")
    if "<name>%s</name>" % NAME in text:
        print("already patched:", os.path.basename(path), NAME); return
    sd = find(text, r"<sounddef>\s*<name>/SFX3/%s</name>.*?</sounddef>" % SRC)
    ev = find(text, r"<event>\s*<name>%s</name>.*?</event>" % SRC)
    wf = find(text, r"<waveform>\s*<filename>sfxnew/%s\.wav</filename>\s*<guid>.*?</waveform>" % SRC)
    nl = "\r\n" if "\r\n" in text else "\n"
    # sounddef: один sounddef, 4 waveform-записи, случайный выбор без повтора
    s = new_guids(sd.group(0).replace("/SFX3/" + SRC, "/SFX3/" + NAME))
    entry = find(s, r"<waveform>\s*<filename>sfxnew/%s\.wav</filename>.*?</waveform>" % SRC).group(0)
    entries = nl.join(entry.replace(SRC, w) for w in WAVS)
    s = s.replace(entry, entries)
    assert "<type>randomnorepeat</type>" in s and s.count("<waveform>") == 4
    # событие: тот же 3D one-shot, но разброс высоты мягче
    e = new_guids(ev.group(0).replace(SRC, NAME))
    e = e.replace("<pitch_randomization>0.25</pitch_randomization>", "<pitch_randomization>0.05</pitch_randomization>")
    assert "<name>/SFX3/%s</name>" % NAME in e
    # waveform-описания файлов (по одному на wav)
    w = [new_guids(wf.group(0).replace(SRC, x)) for x in WAVS]
    for m, block in sorted(((sd, s), (ev, e), (wf, nl.join(w))), key=lambda x: -x[0].end()):
        text = text[:m.end()] + nl + block + text[m.end():]
    xml.dom.minidom.parseString(text.encode("utf-8"))  # XML цел
    shutil.copyfile(path, path + ".before_" + NAME)
    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))
    print("patched:", os.path.basename(path), NAME)

for NAME in NAMES:
    for i in range(1, 5):
        if not os.path.exists(os.path.join(HERE, "SFXNew", "%s_%d.wav" % (NAME, i))):
            raise SystemExit("SFXNew: %s_%d.wav not found" % (NAME, i))
for name in ("PrimeWorldtest.fdp", "PrimeWorld.fdp"):
    p = os.path.join(HERE, name)
    if os.path.exists(p):
        for NAME in NAMES:
            patch(p, NAME)
