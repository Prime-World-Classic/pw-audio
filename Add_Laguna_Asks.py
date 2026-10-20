# -*- coding: utf-8 -*-
"""Добавляет в FMOD-проект озвучку Laguna (asks) по образцу Artist S5:
  event group Heroes/Laguna/Asks/Human, события EVENTS (sounddef /Heroes5/Laguna/<Event>)
wav-файлы: Asks/russian/pwc/laguna/<Event>_N.wav, банк Asks05.
Патчит PrimeWorldtest.fdp (и PrimeWorld.fdp, если в нём есть образец) (резервная копия *.fdp.before_laguna_asks), повторный запуск ничего не меняет.
Затем: fmod_designercl -pc -L RU -S Asks05 PrimeWorldtest.fdp и скопировать PrimeWorld.fev + Asks05_RU.fsb в Data\\Audio.
"""
import os, re, shutil, uuid
import xml.dom.minidom

HERE = os.path.dirname(os.path.abspath(__file__))
WAV_DIR = "asks/russian/pwc/laguna"
# событие -> wav-файлы (случайный без повторов); имена событий как у остальных героев (Iddle — так в игре)
EVENTS = {
    "Move": ["Move_1.wav", "Move_2.wav"],
    "Ability1": ["Ability1_1.wav", "Ability1_2.wav", "Ability1_3.wav"],
    "Ability2": ["Ability2_1.wav", "Ability2_2.wav", "Ability2_3.wav"],
    "Ability3": ["Ability3_1.wav", "Ability3_2.wav", "Ability3_3.wav"],
    "UltimateAbility": ["UltimateAbility_1.wav", "UltimateAbility_2.wav"],  # кит (A4_1)
    "UltimateShark": ["UltimateShark_1.wav", "UltimateShark_2.wav", "UltimateShark_3.wav"],  # заглушка под будущий ульт с акулами
    "Attack": ["Attack_1.wav", "Attack_2.wav", "Attack_3.wav"],
    "Death": ["Death_1.wav", "Death_2.wav"],
    "Revive": ["Revive_1.wav", "Revive_2.wav"],
    "Deathenemyhero": ["Deathenemyhero_1.wav", "Deathenemyhero_2.wav", "Deathenemyhero_3.wav"],
    "Iddle": ["Iddle_1.wav", "Iddle_2.wav"],
}
SRC_SD = "/Heroes5/Artist_S5/Ability1"
SRC_WF = "asks/russian/pwc/artist_s5/Ability1_1.wav"

def new_guids(block):
    return re.sub(r"<guid>\{[0-9a-fA-F-]{36}\}</guid>", lambda m: "<guid>{%s}</guid>" % uuid.uuid4(), block)

def find(text, pattern, start=0):
    m = re.compile(pattern, re.S).search(text, start)
    if not m:
        raise SystemExit("block not found: " + pattern[:80])
    return m

def block_end(text, tag, start):
    """Конец элемента <tag>, открытого в позиции start (с учётом вложенности)."""
    depth = 0
    for m in re.compile(r"<(/?)%s>" % tag).finditer(text, start):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return m.end()
    raise SystemExit("unclosed " + tag)

def eventgroup_path(text, names):
    """Начало eventgroup по пути имён (Heroes/Artist/Asks/S5)."""
    pos, end = 0, len(text)
    for name in names:
        while True:
            m = find(text, r"<eventgroup>\s*<name>%s</name>" % re.escape(name), pos)
            if m.start() >= end:
                raise SystemExit("eventgroup not found: " + name)
            # берём только прямого потомка: между pos и m.start() все eventgroup закрыты
            opened = len(re.findall(r"<eventgroup>", text[pos:m.start()])) - len(re.findall(r"</eventgroup>", text[pos:m.start()]))
            if opened == 0:
                break
            pos = m.end()
        pos, end = m.end(), block_end(text, "eventgroup", m.start())
        start = m.start()
    return start, end

def patch(path):
    with open(path, "rb") as f:
        text = f.read().decode("utf-8")
    if "/Heroes5/Laguna/" in text:
        print("already patched:", os.path.basename(path)); return
    if SRC_SD not in text:  # в PrimeWorld.fdp нет asks Artist S5 (игровые банки собираются из PrimeWorldtest.fdp)
        print("skipped (no %s):" % SRC_SD, os.path.basename(path)); return
    nl = "\r\n" if "\r\n" in text else "\n"

    # sounddef: копия Artist_S5/Ability1 с нашими wav, в новую папку Laguna после папки Artist_S5
    sd = find(text, r"<sounddef>\s*<name>%s</name>.*?</sounddef>" % re.escape(SRC_SD)).group(0)
    wf_items = re.findall(r"<waveform>.*?</waveform>", sd, re.S)
    sds = []
    for ev, wavs in EVENTS.items():
        b = sd.replace(SRC_SD, "/Heroes5/Laguna/" + ev)
        body = nl.join(re.sub(r"<filename>[^<]*</filename>", "<filename>%s/%s</filename>" % (WAV_DIR, w), wf_items[0]) for w in wavs)
        b = b.replace(sd[sd.find(wf_items[0]):sd.rfind(wf_items[-1]) + len(wf_items[-1])], body)
        sds.append(new_guids(b))
    folder = nl.join(["<sounddeffolder>", "<name>Laguna</name>", "<guid>{%s}</guid>" % uuid.uuid4(), "<open>0</open>"] + sds + ["</sounddeffolder>"])
    af = find(text, r"<sounddeffolder>\s*<name>Artist_S5</name>")
    sd_pos = block_end(text, "sounddeffolder", af.start())

    # waveform в банке Asks05
    wf = find(text, r"<waveform>\s*<filename>%s</filename>\s*<guid>.*?</waveform>" % re.escape(SRC_WF))
    wfs = nl.join(new_guids(wf.group(0).replace(SRC_WF, "%s/%s" % (WAV_DIR, w))) for wavs in EVENTS.values() for w in wavs)

    # event group Heroes/Laguna/Asks/Human рядом с Heroes/Artist
    s5_start, s5_end = eventgroup_path(text, ["Heroes", "Artist", "Asks", "S5"])
    s5 = text[s5_start:s5_end]
    src_ev = find(s5, r"<event>\s*<name>Ability1</name>.*?</event>").group(0)
    evs = [new_guids(src_ev.replace("<name>Ability1</name>", "<name>%s</name>" % ev, 1).replace(SRC_SD, "/Heroes5/Laguna/" + ev)) for ev in EVENTS]
    head = s5[:s5.find("<event>")]
    def group(name, inner):
        h = re.sub(r"<name>S5</name>", "<name>%s</name>" % name, head, count=1)
        return new_guids(h + inner + nl + "</eventgroup>")
    human = group("Human", nl.join(evs))
    asks = group("Asks", human)
    laguna = group("Laguna", asks)
    art_start, art_end = eventgroup_path(text, ["Heroes", "Artist"])

    for pos, blk in sorted(((sd_pos, folder), (wf.end(), wfs), (art_end, laguna)), key=lambda x: -x[0]):
        text = text[:pos] + nl + blk + text[pos:]
    xml.dom.minidom.parseString(text.encode("utf-8"))  # проверка, что XML цел
    shutil.copyfile(path, path + ".before_laguna_asks")
    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))
    print("patched:", os.path.basename(path))

for wavs in EVENTS.values():
    for w in wavs:
        if not os.path.exists(os.path.join(HERE, WAV_DIR, w)):
            print("WARNING: %s/%s not found" % (WAV_DIR, w))
for name in ("PrimeWorldtest.fdp", "PrimeWorld.fdp"):
    p = os.path.join(HERE, name)
    if os.path.exists(p):
        patch(p)
