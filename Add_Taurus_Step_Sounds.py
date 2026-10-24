# -*- coding: utf-8 -*-
"""Добавляет в FMOD-проект событие шага Тауруса по образцу monster_step:
  SFX/Taurus_Step - тяжёлый глухой стальной шаг копыта, 4 варианта (случайно без повтора)
wav-файлы: SFXNew/taurus_step1..4.wav (банк SFX, sounddef /SFX3/Taurus_Step).
Свойства события и звука берутся у monster_step, размещение (группа SFX, папка /SFX3/) - как у событий Laguna.
Патчит PrimeWorldtest.fdp и PrimeWorld.fdp (резервная копия *.fdp.before_taurus_step), повторный запуск ничего не меняет.
Затем: fmod_designercl -pc -S SFX PrimeWorldtest.fdp и скопировать PrimeWorld.fev + SFX.fsb в Data\\Audio.
"""
import os, re, shutil
import xml.dom.minidom
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "Taurus_Step"
SRC_EVENT = "monster_step"
SRC_SD = "/Heroes3/Monster/Animation/monster_step"
ANCHOR = "Laguna_DolphinDive"           # new blocks go next to the Laguna ones (group SFX, folder /SFX3/)
WAVES = ["taurus_step%d" % i for i in range(1, 5)]


def new_guids(block):
    return re.sub(r"<guid>\{[0-9a-fA-F-]{36}\}</guid>", lambda m: "<guid>{%s}</guid>" % uuid.uuid4(), block)


def find(text, pattern):
    m = re.search(pattern, text, re.S)
    if not m:
        raise SystemExit("block not found: " + pattern[:80])
    return m


def patch(path):
    with open(path, "rb") as f:
        text = f.read().decode("utf-8")
    if "<name>%s</name>" % NAME in text:
        print("already patched:", os.path.basename(path)); return
    nl = "\r\n" if "\r\n" in text else "\n"
    src_sd = find(text, r"<sounddef>\s*<name>%s</name>.*?</sounddef>" % re.escape(SRC_SD)).group(0)
    src_ev = find(text, r"<event>\s*<name>%s</name>.*?</event>" % SRC_EVENT).group(0)
    src_wf = find(text, r"<waveform>\s*<filename>sfxnew/%s\.wav</filename>\s*<guid>.*?</waveform>" % ANCHOR).group(0)
    at_sd = find(text, r"<sounddef>\s*<name>/SFX3/%s</name>.*?</sounddef>" % ANCHOR)
    at_ev = find(text, r"<event>\s*<name>%s</name>.*?</event>" % ANCHOR)
    at_wf = find(text, r"<waveform>\s*<filename>sfxnew/%s\.wav</filename>\s*<guid>.*?</waveform>" % ANCHOR)

    # sound definition: monster_step's random list, entries replaced by our 4 files in bank SFX
    entries = re.findall(r"<waveform>\s*<filename>[^<]*</filename>\s*<soundbankname>.*?</waveform>", src_sd, re.S)
    assert len(entries) >= 1, "no waveform entries in %s" % SRC_SD
    ent = entries[0]
    new_entries = []
    for w in WAVES:
        e = re.sub(r"<filename>[^<]*</filename>", "<filename>sfxnew/%s.wav</filename>" % w, ent)
        e = re.sub(r"<soundbankname>[^<]*</soundbankname>", "<soundbankname>SFX</soundbankname>", e)
        new_entries.append(e)
    head = src_sd[:src_sd.index(entries[0])]
    tail = src_sd[src_sd.rindex(entries[-1]) + len(entries[-1]):]
    sd = new_guids(head.replace("<name>%s</name>" % SRC_SD, "<name>/SFX3/%s</name>" % NAME) + nl.join(new_entries) + tail)

    ev = new_guids(src_ev.replace("<name>%s</name>" % SRC_EVENT, "<name>%s</name>" % NAME, 1)
                   .replace("<name>%s</name>" % SRC_SD, "<name>/SFX3/%s</name>" % NAME))
    assert "<name>/SFX3/%s</name>" % NAME in ev

    wfs = [new_guids(src_wf.replace("sfxnew/%s.wav" % ANCHOR, "sfxnew/%s.wav" % w)) for w in WAVES]

    for m, blocks in sorted(((at_sd, [sd]), (at_ev, [ev]), (at_wf, wfs)), key=lambda x: -x[0].end()):
        text = text[:m.end()] + nl + nl.join(blocks) + text[m.end():]
    xml.dom.minidom.parseString(text.encode("utf-8"))  # проверка, что XML цел
    shutil.copyfile(path, path + ".before_taurus_step")
    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))
    print("patched:", os.path.basename(path), "| entries in source sounddef:", len(entries))


for w in WAVES:
    if not os.path.exists(os.path.join(HERE, "SFXNew", w + ".wav")):
        raise SystemExit("SFXNew\\%s.wav not found" % w)
for name in ("PrimeWorldtest.fdp", "PrimeWorld.fdp"):
    p = os.path.join(HERE, name)
    if os.path.exists(p):
        patch(p)
