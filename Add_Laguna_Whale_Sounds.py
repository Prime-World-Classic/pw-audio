# -*- coding: utf-8 -*-
"""Добавляет в FMOD-проект 2 события кита Laguna (A4_1) по образцу событий дельфина:
  SFX/Laguna_WhaleSwim   - плавание, бесшовная петля (oneshot No, loopmode 0)
  SFX/Laguna_WhaleSplash - удар о воду при приземлении (one-shot)
wav-файлы: SFXNew/Laguna_Whale*.wav (банк SFX, sounddefs /SFX3/...).
Патчит PrimeWorldtest.fdp и PrimeWorld.fdp (резервная копия *.fdp.before_whale), повторный запуск ничего не меняет.
Затем: fmod_designercl -pc -S SFX PrimeWorldtest.fdp (из него собраны игровые банки) и скопировать PrimeWorld.fev + SFX.fsb в Data\\Audio.
"""
import os, re, shutil, sys, uuid
import xml.dom.minidom

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = "Laguna_DolphinDive"
NEW = [  # имя, параметры события
    ("Laguna_WhaleSwim", {"loop": True}),
    ("Laguna_WhaleSplash", {}),
]

def new_guids(block):
    return re.sub(r"<guid>\{[0-9a-fA-F-]{36}\}</guid>", lambda m: "<guid>{%s}</guid>" % uuid.uuid4(), block)

def find(text, pattern):
    m = re.search(pattern, text, re.S)
    if not m:
        raise SystemExit("block not found: " + pattern[:80])
    return m

def patch(path):
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8")
    if "Laguna_WhaleSwim" in text:
        print("already patched:", os.path.basename(path)); return
    sd = find(text, r"<sounddef>\s*<name>/SFX3/%s</name>.*?</sounddef>" % SRC)
    ev = find(text, r"<event>\s*<name>%s</name>.*?</event>" % SRC)
    wf = find(text, r"<waveform>\s*<filename>sfxnew/%s\.wav</filename>\s*<guid>.*?</waveform>" % SRC)
    add_sd, add_ev, add_wf = [], [], []
    for name, opt in NEW:
        b = new_guids(sd.group(0).replace(SRC, name)); add_sd.append(b)
        b = new_guids(wf.group(0).replace(SRC, name)); add_wf.append(b)
        e = new_guids(ev.group(0).replace(SRC, name))
        if opt.get("loop"):
            e = e.replace("<oneshot>Yes</oneshot>", "<oneshot>No</oneshot>")
            e = e.replace("<TEMPLATE_PROP_ONESHOT>1</TEMPLATE_PROP_ONESHOT>", "<TEMPLATE_PROP_ONESHOT>0</TEMPLATE_PROP_ONESHOT>")
            e = re.sub(r"<loopmode>1</loopmode>", "<loopmode>0</loopmode>", e)
            e = e.replace("<pitch_randomization>0.25</pitch_randomization>", "<pitch_randomization>0</pitch_randomization>")
            e = e.replace("<TEMPLATE_PROP_PITCH_RANDOMIZATION>1</TEMPLATE_PROP_PITCH_RANDOMIZATION>", "<TEMPLATE_PROP_PITCH_RANDOMIZATION>0</TEMPLATE_PROP_PITCH_RANDOMIZATION>")
            assert "<oneshot>No</oneshot>" in e and "<loopmode>0</loopmode>" in e
        add_ev.append(e)
    nl = "\r\n" if "\r\n" in text else "\n"
    # вставляем после исходных блоков, с конца файла к началу, чтобы не сбить позиции
    for m, blocks in sorted(((sd, add_sd), (ev, add_ev), (wf, add_wf)), key=lambda x: -x[0].end()):
        text = text[:m.end()] + nl + nl.join(blocks) + text[m.end():]
    xml.dom.minidom.parseString(text.encode("utf-8"))  # проверка, что XML цел
    shutil.copyfile(path, path + ".before_whale")
    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))
    print("patched:", os.path.basename(path))

for wav in ("Laguna_WhaleSwim.wav", "Laguna_WhaleSplash.wav"):
    if not os.path.exists(os.path.join(HERE, "SFXNew", wav)):
        print("WARNING: SFXNew\\%s not found" % wav)
for name in ("PrimeWorldtest.fdp", "PrimeWorld.fdp"):
    p = os.path.join(HERE, name)
    if os.path.exists(p):
        patch(p)
