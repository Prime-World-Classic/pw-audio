# -*- coding: utf-8 -*-
"""Добавляет в FMOD-проект события прыжка Тауруса (способность A4_2 «Мощный прыжок»), по образцу monster_ground_explosion:
  SFX/Taurus_JumpCharge - подготовка (A4_2_PrepareTime 1.5 с): тяжёлый нарастающий энергетический заряд (рецепт «Э1»
                          заряда A1, растянутый на 1.5 с); звучит на эффекте подготовки, гаснет за 150 мс (oneshot No)
  SFX/Taurus_JumpLaunch - толчок: копыто, низкий удар, всплеск подземного гула, свист вверх
  SFX/Taurus_JumpAir    - полёт: ветер; останавливается входом в узел jumpLand (fadeout 200 мс, oneshot No)
  SFX/Taurus_JumpLand   - приземление: взрыв земли Химеры, щит, суббас, падающие камни
wav: SFXNew/taurus_jump_charge.wav, taurus_jump_launch.wav, taurus_jump_air.wav, taurus_jump_land.wav (банк SFX),
генератор - .claude/pw-tools/audio/make_taurus_sfx.py.
Свойства события и звука берутся у monster_ground_explosion, размещение (группа SFX, папка /SFX3/) - как у событий Laguna.
Патчит PrimeWorldtest.fdp и PrimeWorld.fdp (резервная копия *.fdp.before_taurus_jump), повторный запуск ничего не меняет.
Затем: fmod_designercl -pc -S SFX PrimeWorldtest.fdp и скопировать PrimeWorld.fev + SFX.fsb в Data\\Audio.
"""
import os, re, shutil
import xml.dom.minidom
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_EVENT = "monster_ground_explosion"
SRC_SD = "/Heroes3/Monster/Animation/monster_ground_explosion"
ANCHOR = "Laguna_DolphinDive"           # new blocks go next to the Laguna ones (group SFX, folder /SFX3/)
#          event              waves                                  fadeout ms  oneshot
EVENTS = [("Taurus_JumpCharge", ["taurus_jump_charge"], 150, "No"),
          ("Taurus_JumpLaunch", ["taurus_jump_launch"], None, None),
          ("Taurus_JumpAir", ["taurus_jump_air"], 200, "No"),
          ("Taurus_JumpLand", ["taurus_jump_land"], None, None)]


def new_guids(block):
    return re.sub(r"<guid>\{[0-9a-fA-F-]{36}\}</guid>", lambda m: "<guid>{%s}</guid>" % uuid.uuid4(), block)


def find(text, pattern):
    m = re.search(pattern, text, re.S)
    if not m:
        raise SystemExit("block not found: " + pattern[:80])
    return m


def add_event(text, name, waves, fadeout, oneshot, nl):
    src_sd = find(text, r"<sounddef>\s*<name>%s</name>.*?</sounddef>" % re.escape(SRC_SD)).group(0)
    src_ev = find(text, r"<event>\s*<name>%s</name>.*?</event>" % SRC_EVENT).group(0)
    src_wf = find(text, r"<waveform>\s*<filename>sfxnew/%s\.wav</filename>\s*<guid>.*?</waveform>" % ANCHOR).group(0)
    at_sd = find(text, r"<sounddef>\s*<name>/SFX3/%s</name>.*?</sounddef>" % ANCHOR)
    at_ev = find(text, r"<event>\s*<name>%s</name>.*?</event>" % ANCHOR)
    at_wf = find(text, r"<waveform>\s*<filename>sfxnew/%s\.wav</filename>\s*<guid>.*?</waveform>" % ANCHOR)

    entries = re.findall(r"<waveform>\s*<filename>[^<]*</filename>\s*<soundbankname>.*?</waveform>", src_sd, re.S)
    assert len(entries) >= 1, "no waveform entries in %s" % SRC_SD
    new_entries = []
    for w in waves:
        e = re.sub(r"<filename>[^<]*</filename>", "<filename>sfxnew/%s.wav</filename>" % w, entries[0])
        e = re.sub(r"<soundbankname>[^<]*</soundbankname>", "<soundbankname>SFX</soundbankname>", e)
        new_entries.append(e)
    head = src_sd[:src_sd.index(entries[0])]
    tail = src_sd[src_sd.rindex(entries[-1]) + len(entries[-1]):]
    sd = new_guids(head.replace("<name>%s</name>" % SRC_SD, "<name>/SFX3/%s</name>" % name) + nl.join(new_entries) + tail)

    ev = new_guids(src_ev.replace("<name>%s</name>" % SRC_EVENT, "<name>%s</name>" % name, 1)
                   .replace("<name>%s</name>" % SRC_SD, "<name>/SFX3/%s</name>" % name))
    assert "<name>/SFX3/%s</name>" % name in ev
    # a sound stopped from the game (released key, end of the run): fade out instead of a cut, not a one-shot event
    for tag, val in (("fadeout_time", fadeout), ("oneshot", oneshot)):
        if val is not None:
            ev, k = re.subn(r"<%s>[^<]*</%s>" % (tag, tag), "<%s>%s</%s>" % (tag, val, tag), ev, count=1)
            assert k == 1, tag

    wfs = [new_guids(src_wf.replace("sfxnew/%s.wav" % ANCHOR, "sfxnew/%s.wav" % w)) for w in waves]
    for m, blocks in sorted(((at_sd, [sd]), (at_ev, [ev]), (at_wf, wfs)), key=lambda x: -x[0].end()):
        text = text[:m.end()] + nl + nl.join(blocks) + text[m.end():]
    return text


def patch(path):
    with open(path, "rb") as f:
        text = f.read().decode("utf-8")
    nl = "\r\n" if "\r\n" in text else "\n"
    added = []
    for name, waves, fadeout, oneshot in EVENTS:
        if "<name>%s</name>" % name in text:
            continue
        text = add_event(text, name, waves, fadeout, oneshot, nl)
        added.append(name)
    if not added:
        print("already patched:", os.path.basename(path)); return
    xml.dom.minidom.parseString(text.encode("utf-8"))  # проверка, что XML цел
    shutil.copyfile(path, path + ".before_taurus_jump")
    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))
    print("patched:", os.path.basename(path), added)


for name, waves, fadeout, oneshot in EVENTS:
    for w in waves:
        if not os.path.exists(os.path.join(HERE, "SFXNew", w + ".wav")):
            raise SystemExit("SFXNew\\%s.wav not found" % w)
for name in ("PrimeWorldtest.fdp", "PrimeWorld.fdp"):
    p = os.path.join(HERE, name)
    if os.path.exists(p):
        patch(p)
