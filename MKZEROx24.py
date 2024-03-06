import math
import os
import sys
import time
import argparse
import obsws_python as obspy
import json
from PIL import Image
from threading import Thread
import random
from websockets.sync.client import connect


parser = argparse.ArgumentParser(description='MKZEROx24 game operator.', formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('--config', type=str,
                    help='Config file for websocket configuration.\nDefault: config.cfg', default="config.cfg")
parser.add_argument('--shaders', type=str,
                    help='Shader list file to use.\nDefault: shaders.json', default="shaders.json")
parser.add_argument('-v', '--verbosity', type=int,
                    help='Verbosity of the script.\n'
                         '0: Silent.\n'
                         '1: Basic info.\n'
                         '2: Websocket traffic types.\n'
                         '3: Main state info.'
                         '4: Everything.'
                         'Default: 1: Basic info.', default=1)
parser.add_argument('-c', '--code', type=str,
                    help='Gamecode for connecting to scoreboard.\nDefault: Ask for input.')
parser.add_argument('-s', '--seed', type=int,
                    help='Seed for randomization.\nDefault: Random seed.')
parser.add_argument('-n', '--norolling',
                    help='Skips shader rolling display and delay.', action="store_true")
parser.add_argument('-i', '--init',
                    help='inits OBS sources without starting game.', action="store_true")
parser.add_argument('--reset',
                    help='hardresets everything in obs.', action="store_true")
parser.add_argument('-r', '--reconnect',
                    help='Reconnects without recalculating current shaders.', action="store_true")

subparsers = parser.add_subparsers(dest="preview", help='Preview')
prewparse = subparsers.add_parser('preview')
prewparse.add_argument('-d', '--duration', type=int, default=15,
                       help='duration for each shader in preview')
prewparse.add_argument('-r', '--record', action="store_true",
                       help='Record shaders')
prewparse.add_argument('-e', '--evaluate', type=int, default=1,
                       help='Ask for N scores to be given for each shader and store values.')
prewparse.add_argument('-s', '--sort', choices='NSFR', default="F",
                       help='Sort shaders by Name, current Score, order in File, Random')
prewparse.add_argument('--number', choices='OTBN', default="N",
                       help='Show shader number in OBS, Terminal, Both or None.')
prewparse.add_argument('--name', choices='OTBN', default="N",
                       help='Show shader name in OBS, Terminal, Both or None.')

obs_sources = {
    "end": "_MKZx24",
    "main": "Game_MKZx24",
    "roller": "Roller#_MKZx24",
    "game_screen": "GameScreen#_MKZx24",
    "overlay_scene": "OverlayScene_MKZx24",
    "penalty_item": "PENALTYITEM_#_MKZx24",
    "game_source": "Source_MKZx24",
    "preview_source": "Source_MKZx24",
    "crop_filter": "set_screen_MKZx24",
}

players = []
states = []
weapon_uses = []

settings = {
    "seed": 0,
    "gamecode": "",
    "video": {"x": 1920, "y": 1080},
    "verbosity": 1,
    "rounds": 24,
    "controllers": 4,
    "reconnect": False,
    "norolling": False,
    "hardreset": False,
    "shader-random": 0.0,
    "shader-max-range": 0.0,
    "penalty_img": [],
    "runnin_id": 0,
    "shader-cut-off": 0.8
}
thread_id = 0

obs: obspy.ReqClient
scoreboard: connect

shaders = []
fireshaders = []

penalty_img_size = 250

screens = [
    [
        {"size_x": 1, "size_y": 1, "pos_x": 0, "pos_y": 0,
         "crop": {"left": 0, "top": 0, "right": 0, "bottom": 0}},
    ],
    [
        {"size_x": 1, "size_y": 0.5, "pos_x": 0, "pos_y": 0,
         "crop": {"left": 0, "top": 0, "right": 0, "bottom": 0.5}},
        {"size_x": 1, "size_y": 0.5, "pos_x": 0, "pos_y": 0.5,
         "crop": {"left": 0, "top": 0.5, "right": 0, "bottom": 0}}
    ],
    [
        {"size_x": 0.5, "size_y": 0.5, "pos_x": 0, "pos_y": 0,
         "crop": {"left": 0, "top": 0, "right": 0.5, "bottom": 0.5}},
        {"size_x": 0.5, "size_y": 0.5, "pos_x": 0.5, "pos_y": 0,
         "crop": {"left": 0.5, "top": 0, "right": 0, "bottom": 0.5}},
        {"size_x": 0.5, "size_y": 0.5, "pos_x": 0, "pos_y": 0.5,
         "crop": {"left": 0, "top": 0.5, "right": 0.5, "bottom": 0}},
    ],
    [
        {"size_x": 0.5, "size_y": 0.5, "pos_x": 0, "pos_y": 0,
         "crop": {"left": 0, "top": 0, "right": 0.5, "bottom": 0.5}},
        {"size_x": 0.5, "size_y": 0.5, "pos_x": 0.5, "pos_y": 0,
         "crop": {"left": 0.5, "top": 0, "right": 0, "bottom": 0.5}},
        {"size_x": 0.5, "size_y": 0.5, "pos_x": 0, "pos_y": 0.5,
         "crop": {"left": 0, "top": 0.5, "right": 0.5, "bottom": 0}},
        {"size_x": 0.5, "size_y": 0.5, "pos_x": 0.5, "pos_y": 0.5,
         "crop": {"left": 0.5, "top": 0.5, "right": 0, "bottom": 0}},
    ]
]

def main():
    global states
    global weapon_uses
    while True:
        message = json.loads(scoreboard.recv())
        if message["type"] == "error":
            v_print(-1, f"Error from scoreboard: {message}")
            break
        if message["type"] == "all_states":
            v_print(2, f'Got scoreboard states')
            old_states = states[:]
            states = message["state"]
            v_print(4, states)
            if settings["reconnect"]:
                settings["reconnect"] = False
                continue
            reset = True
            if len(old_states) == len(states):
                reset = False
                for s in range(len(old_states)):
                    if old_states[s] != states[s]:
                        reset = True
                        break

            reset_states()
            if reset:
                update_shaders()

            scoreboard.send(json.dumps({'type': 'get_weapon_usage'}))
        if message["type"] == "reset_state":
            v_print(2, f'Host reconnected.')
            scoreboard.send(json.dumps({'type': 'get_all_states'}))
        if message["type"] == "state":
            v_print(2, f'Got another scoreboard state.')
            v_print(4, f'{message["state"]}')
            states.append(message["state"])
            if len(states) > 1:
                ret = check_states(states[-1], states[-2])
                if ret == -2:
                    scoreboard.send(json.dumps({'type': 'get_all_states'}))
                elif ret >= 0:
                    update_shaders()
        if message["type"] == "weapon_use":
            v_print(2, f'Got another weapon use.')
            v_print(4, f'{message["weapon_use"]}')
            use_weapon(message["weapon_use"],states[-1])
            weapon_uses.append(message["weapon_use"])
        if message["type"] == "weapon_usage":
            v_print(2, f'Got all weapon use.')
            v_print(4, f'{message["weapon_usage"]}')
            weapon_uses = message["weapon_usage"]

    v_print(-1, "Websocket closed.")


def init_conf():
    global obs
    ws_config = {}
    args = parser.parse_args()
    with open(args.config) as f:
        conf = f.read().splitlines()
        for i, line in enumerate(conf):
            cfg = line.split("=")
            if len(cfg) == 2:
                ws_config[cfg[0]] = cfg[1]
            elif line:
                v_print(-1, f'Error reading config on line {i + 1}, {line}')

    if args.preview:
        print("LUL")

    obs = obspy.ReqClient(host=ws_config["OBS_WS_URL"], port=int(ws_config["OBS_WS_PORT"]),
                          password=ws_config["OBS_WS_PASS"], timeout=3)
    if not obs:
        v_print(-1, f'Could not connect to OBS')
        return False
    v_print(1, f'Connected to OBS websocket.')

    vs = obs.get_video_settings()
    v_print(4, f'{vs}')
    settings["video"] = dict(x=vs.base_width, y=vs.base_height)
    settings["hardreset"] = args.reset
    settings["verbosity"] = args.verbosity

    if not args.init:
        sb_settings = connect_to_scoreboard(args.code, ws_config)
        if not sb_settings:
            return False
        v_print(4, f'{sb_settings}')
        set_players(sb_settings["players"])
        settings["controllers"] = int(sb_settings["controllers"])
        settings["rounds"] = int(sb_settings["rounds"])
        settings["penalty_img"] = get_penalty_items()
        if args.seed:
            settings["seed"] = args.seed
            v_print(1, f'Using random seed: {settings["seed"]}')
        else:
            settings["seed"] = random.randint(0, 9999999)
            v_print(1, f'Using random seed: {settings["seed"]}')
        random.seed(int(settings["seed"]))
        settings["reconnect"] = args.reconnect
        settings["norolling"] = args.norolling

        read_shaders(args.shaders)
        create_shader_js()
    return True


def create_shader_js():
    js = "const shaders = [\n"
    for shader in shaders:
        js += f'  {{"name": "{shader["name"]}", "intensity": {(shader["intensity_min"]+shader["intensity_max"])/2}}},\n'
    js += "];"
    with open("shader_rolls/shaders.js", "w") as f:
        f.write(js)

def get_penalty_items():
    items = []
    penalty_dir = os.path.dirname(__file__) + "/penalty_img"
    files = os.listdir(penalty_dir)
    for f in files:
        if os.path.isfile(penalty_dir + "/" + f):
            image = Image.open(penalty_dir + "/" + f)
            w, h = image.size
            scale = penalty_img_size / max(w, h)
            items.append({"file": f, "scale": scale})
    return items


def connect_to_scoreboard(gamecode, ws_config):
    global scoreboard
    scoreboard = connect("wss://" + ws_config["SCOREBOARD_WS_URL"] + ":" + ws_config["SCOREBOARD_WS_PORT"])
    if not scoreboard:
        v_print(-1, f'Could not connect to Scoreboard')
        return {}
    v_print(1, f'Connected to scoreboard server.')
    lastcode = ""
    if os.path.isfile(os.path.dirname(__file__) + "/gamecode.txt"):
        with open("gamecode.txt", "r") as f:
            lastcode = f.read()
    while True:
        if not gamecode:

            if lastcode != "":
                gamecode = input(f'Insert scoreboard gamecode ({lastcode}): ')
                if gamecode == "":
                    gamecode = lastcode
            else:
                gamecode = input("Insert scoreboard gamecode: ")
                if gamecode == "":
                    v_print(-1, f'Aborted scoreboard connection.')
                    return {}

        scoreboard.send(json.dumps({'type': 'join', 'secret': gamecode}))
        message = json.loads(scoreboard.recv())
        if message["type"] == "error":
            v_print(-1, f'Connecting with gamecode: {gamecode} failed')
            lastcode = ""
            gamecode = None
        if message["type"] == "joined":
            settings["gamecode"] = gamecode
            with open("gamecode.txt", "w") as f:
                f.write(gamecode)
            v_print(2, f'Joined scoreboard successfully.')
            scoreboard.send(json.dumps({'type': 'get_settings'}))
        if message["type"] == "settings":
            v_print(2, f'Got scoreboard settings.')
            scoreboard.send(json.dumps({'type': 'get_all_states'}))
            return message["settings"]


def create_or_reset_scene(scenes, scene):
    to_del = []
    if settings["hardreset"] and scene in scenes:
        if scene + "_old" in scenes:
            obs.remove_scene(scene + "_old")
            to_del = [scene + "_old"]
            time.sleep(0.5)
        obs.set_scene_name(scene, scene + "_old")
        v_print(1, f'Deleting old {scene} scene from OBS.')
        time.sleep(0.5)
    if scene not in scenes or settings["hardreset"]:
        obs.create_scene(scene)
        v_print(1, f'Creating new {scene} scene in OBS.')
    return to_del


def add_source_to_scene(scene, source):
    for item in obs.get_scene_item_list(scene).scene_items:
        if item["sourceName"] == source:
            return item["sceneItemId"]
    sourceid = obs.create_scene_item(scene, source).scene_item_id
    return sourceid


def init_scenes():
    to_del = []
    scenes = []
    items = []
    for scene in obs.get_scene_list().scenes:
        scenes.append(scene["sceneName"])
    to_del += create_or_reset_scene(scenes, obs_sources["main"])

    for item in obs.get_input_list().inputs:
        items.append(item["inputName"])

    if not obs_sources["game_source"] in items:
        v_print(1, "Game source is needed. If you haven't yet added a game source, create it now in obs.")
        while True:
            gs = input("Give game source name: ")
            if gs == "":
                return False
            items = []
            for item in obs.get_input_list().inputs:
                items.append(item["inputName"])
            if not gs in items:
                v_print(1, "No such source!")
            else:
                if gs != obs_sources["game_source"]:
                    if input(f'Allow renaming {gs} to {obs_sources["game_source"]}? Y/n').lower() != "n":
                        obs.set_input_name(gs, obs_sources["game_source"])
                    else:
                        obs_sources["game_source"] = gs
                break
    main_sid = add_source_to_scene(obs_sources["main"], obs_sources["game_source"])
    obs.set_scene_item_enabled(obs_sources["main"], main_sid, False)

    crop_settings = {
                      "expand_bottom": -settings["video"]["y"] / 2,
                      "expand_right": -settings["video"]["x"] / 2}
    screen_settings = screens[settings["controllers"]-1]

    for i in range(settings["controllers"]):
        game_screen = obs_sources["game_screen"].replace("#", str(i + 1))
        to_del += create_or_reset_scene(scenes, game_screen)
        source_id = add_source_to_scene(game_screen, obs_sources["game_source"])
        screen_id = add_source_to_scene(obs_sources["main"], game_screen)
        for f in obs.get_source_filter_list(game_screen).filters:
            obs.remove_source_filter(game_screen, f["filterName"])
        crop_settings = {
            "left": screen_settings[i]["crop"]["left"] * settings["video"]["x"],
            "top": screen_settings[i]["crop"]["top"] * settings["video"]["y"],
            "right": screen_settings[i]["crop"]["right"] * settings["video"]["x"],
            "bottom": screen_settings[i]["crop"]["bottom"] * settings["video"]["y"],
        }

        obs.create_source_filter(game_screen, obs_sources["crop_filter"], "crop_filter", crop_settings)
        obs.set_scene_item_transform(obs_sources["main"], screen_id, {
            'positionX': screen_settings[i]["pos_x"] * settings["video"]["x"],
            'positionY': screen_settings[i]["pos_y"] * settings["video"]["y"],
        })

        obs.set_scene_item_index(obs_sources["main"], screen_id, 0)

    to_del += create_or_reset_scene(scenes, obs_sources["overlay_scene"])
    for i in obs.get_scene_item_list(obs_sources["overlay_scene"]).scene_items:
        obs.remove_scene_item(obs_sources["overlay_scene"], i["sceneItemId"])
    add_source_to_scene(obs_sources["main"], obs_sources["overlay_scene"])

    for s in to_del:
        obs.remove_scene(s)


def set_players(player_settings):
    for p in player_settings:
        players.append({
            "name": p[0],
            "icon": p[1],
            "score": 0,
            "shaders": []
        })


def reset_states():
    global states
    for p in players:
        p["shaders"] = []
    random.seed(int(settings["seed"]))
    last_state = states[0]
    for state in states:
        ret = check_states(state, last_state)
        if ret == -2:
            v_print(-1, "Problems checking the states, Please fix / Restart")
        last_state = state


def check_states(state, last_state):
    winner = -1
    jonne_ready = True
    zero_wins = 0
    jonne = 0
    if state["wins"] != last_state["wins"]:
        for p in range(len(players)):
            if state["wins"][p] - 1 == last_state["wins"][p]:
                winner = p
            if state["wins"][p] < last_state["wins"][p]:
                v_print(2, "Went backwards, reseting states.")
                # Went backwards
                return -2
            if state["wins"][p] == 0:
                zero_wins += 1
                if zero_wins > 1:
                    jonne_ready = False
            if state["playsline"][p] > state["playsline"][jonne]:
                jonne = p

        if winner >= 0:
            players[winner]["score"] += 1 / 3 + state["fire"][winner] / 5
            if jonne_ready and jonne >= 0:
                players[jonne]["score"] -= 1
                if players[jonne]["score"] < 0:
                    players[jonne]["score"] = 0
    return winner


def update_shaders(dont_hide=False):
    global thread_id
    thread_id += 1
    if not settings["norolling"] or dont_hide:
        obs.set_scene_item_enabled(obs_sources["main"],
                                   obs.get_scene_item_id(obs_sources["main"], obs_sources["game_source"]).scene_item_id,
                                   True)
        time.sleep(0.5)

    state = states[-1]

    reset_penalty_box()
    for c in range(settings["controllers"]):
        game_screen = obs_sources["game_screen"].replace("#", str(c + 1))
        shader_list = obs.get_source_filter_list(game_screen)
        for shader in shader_list.filters:
            if shader["filterName"] != obs_sources["crop_filter"]:
                obs.remove_source_filter(game_screen, shader["filterName"])
    game_sources = {}
    wins = state["wins"][:]
    wins.sort()
    windif = wins[-1] - wins[-2]

    for p in range(len(players)):
        if state["line"][p] < settings["controllers"]:
            game_screen = obs_sources["game_screen"].replace("#", str(state["line"][p] + 1))
            game_sources[game_screen] = {"wins": None, "score": None, "lead": None, "crap": None, "fire": None, "penalties": []}
            players[p]["shaders"] = []
            pscore = players[p]["score"]
            add_crap = False
            penalties = state["spes"][p].count("-")
            for wu in weapon_uses:
                if wu["target"] == p:
                    if wu["weapon"] == 0:
                        penalties += 1
                    if wu["weapon"] == 1 and round(time.time() * 1000) < wu["end_time"]:
                        if add_crap:
                            pscore += 2
                        add_crap = True

            if state["wins"][p] > 0:
                shader = get_shader(p, state["wins"][p], settings["shader-random"], settings["shader-max-range"])
                players[p]["shaders"].append(shader["group"])
                game_sources[game_screen]["wins"] = shader

            if pscore >= 1:
                shader = get_shader(p, pscore, settings["shader-random"] * 2,
                                    settings["shader-max-range"] * 2)
                players[p]["shaders"].append(shader["group"])
                game_sources[game_screen]["score"] = shader

            if state["wins"][p] == wins[-1] and windif > 0:
                shader = get_shader(p, min(5 + windif * 5, settings["rounds"]), 0, settings["rounds"] / 3)
                players[p]["shaders"].append(shader["group"])
                game_sources[game_screen]["lead"] = shader
            if add_crap:
                shader = get_shader(p, settings["rounds"], 0, settings["rounds"] / 7)
                players[p]["shaders"].append(shader["group"])
                game_sources[game_screen]["crap"] = shader


            fire = min(state["fire"][p], len(fireshaders))
            if fire > 0:
                game_sources[game_screen]["fire"] = fireshaders[fire]
            for s in range(penalties):
                count = math.ceil(pow(random.random(), 5) * 6 + 0.001)
                for pp in range(count):
                    penalty_source = settings["penalty_img"][random.randint(0, len(settings["penalty_img"]) - 1)]
                    game_sources[game_screen]["penalties"].append(
                        {"source": penalty_source, "seat": state["line"][p], "intensity": s, "multiplier": count})
    if settings["norolling"]:
        set_shaders(game_sources, thread_id, dont_hide)
    else:
        set_rollers(game_sources)
        Thread(target=set_shaders, args=[game_sources, thread_id, dont_hide], daemon=True).start()


def set_rollers(game_sources):
    screensettings = screens[settings["controllers"]-1]
    for c in range(settings["controllers"]):
        source = obs_sources["game_screen"].replace("#", str(c + 1))
        atributes = ""
        for k in ["wins", "score", "lead", "crap"]:
            if game_sources[source][k]:
                atributes += str(shaders.index(game_sources[source][k]))
            else:
                atributes += "-1"
            if k != "crap":
                atributes += "&"
        browser_settings = {
            'url': "file://" + os.path.dirname(__file__) + "/shader_rolls/index.html?"+atributes,
            'width': settings["video"]["x"] * screensettings[c]["size_x"],
            'height': settings["video"]["y"]*2 * screensettings[c]["size_y"]
        }
        siid = obs.create_input(obs_sources["overlay_scene"], obs_sources["roller"].replace("#", str(c + 1)), "browser_source", browser_settings, True)
        browser_transform = {
            'positionX': settings["video"]["x"] * screensettings[c]["pos_x"],
            'positionY': settings["video"]["y"] * (screensettings[c]["pos_y"]-0.5),
        }
        obs.set_scene_item_transform(obs_sources["overlay_scene"], siid.scene_item_id, browser_transform)


def set_shaders(game_sources, t_id, dont_hide):
    if not settings["norolling"]:
        time.sleep(7.5)
        if t_id != thread_id:
            v_print(2, "Thread grew too old. (Newer state available) Terminating.")
            return

    v_print(2, "Setting following effects for players:")
    to_print = {}
    splits = obs_sources["game_screen"].split("#")
    for source in game_sources.keys():
        source_i = int(source.split(splits[0])[1].split(splits[1])[0])
        to_print[source_i] = ""
        for k in game_sources[source].keys():
            if game_sources[source][k]:
                if k != "penalties":
                    create_shader(source, game_sources[source][k])
                    to_print[source_i] += f' {k.ljust(10)}: {game_sources[source][k]["name"].ljust(25)}'
                else:
                    to_print[source_i] += f' {k.ljust(10)}: '
                    for p in game_sources[source][k]:
                        to_print[source_i] += f' {p["source"]["file"].ljust(30)}'
                        add_penalty_dvd(p)
    for i in range(len(game_sources.keys())):
        if to_print[i + 1] != "":
            v_print(2, str(i + 1) + ": " + to_print[i + 1])
    if not settings["norolling"]:
        obs.set_scene_item_enabled(obs_sources["main"],
                                   obs.get_scene_item_id(obs_sources["main"], obs_sources["game_source"]).scene_item_id,
                                   False)
    return


def create_shader(source, shader):
    shadersettings = {'from_file': True,
                      'override_entire_effect': shader["is_effect"],
                      'use_shader_elapsed_time': False,
                      'shader_file_name': shader["file_path"]
                      }
    obs.create_source_filter(source, shader["name"], "shader_filter", shadersettings)


def get_shader(player, score, fir, mid):
    global players
    midf = mid / settings["rounds"]
    firf = fir / settings["rounds"]
    intensity = score / settings["rounds"]
    intensity += firf * random.random() - firf / 2
    intensity = max(min(intensity, 1), 0)
    choises = []
    for shader in shaders:
        if shader["group"] in players[player]["shaders"]:
            continue
        if intensity + midf / 2 >= shader["intensity_min"] and intensity - midf / 2 <= shader["intensity_max"]:
            intensity_multiplier = 1
            if abs(intensity - (shader["intensity_min"] + shader["intensity_max"]) / 2) > 0:
                intensity_multiplier = max(0.01, 1.0 - abs(
                    intensity - (shader["intensity_min"] + shader["intensity_max"]) / 2))
            for i in range(1 + round(intensity_multiplier * 100 * shader["weight"])):
                choises.append(shader)
    if len(choises) == 0:
        return get_shader(player, score, 0, mid + 2)
    return choises[random.randint(0, len(choises) - 1)]


def read_shaders(shaderjson):
    shader_multiplier = 1/settings["shader-cut-off"]
    with open(shaderjson) as f:
        json_shaders = json.loads(f.read())
        for shader in json_shaders:
            path = os.path.dirname(__file__) + "/shaders/" + shader["filename"]
            if os.path.isfile(path):
                shader["name"] = shader["filename"].split(".")[0]
                shader["display_name"] = " ".join(shader["filename"].split(".")[0].split("_")).title()
                shader["file_path"] = path
                shader["intensity_max"] *= shader_multiplier
                shader["intensity_min"] *= shader_multiplier
                if shader["filename"].split(".")[1] == "effect":
                    shader["is_effect"] = True
                else:
                    shader["is_effect"] = False
                shaders.append(shader)
            else:
                v_print(-1, f'Shader {shader["filename"]}, not found. no such file: {path}')

    for i in range(5):
        fire_path = os.path.dirname(__file__) + "/shaders/on_fire_" + str(i + 1) + ".effect"
        if os.path.isfile(fire_path):
            fireshaders.append({
                "name": "on_fire_" + str(i + 1),
                "display_name": "On Fire " + str(i + 1),
                "file_path": fire_path,
                "intensity": i + 1,
                "is_effect": True,
                "group": "on_fire"
            })
        else:
            v_print(-1, f'Fire shader not found! No such file: {fire_path}')


def read_csv_shaders(shadercsv):
    shaders = json.loads()
    with open(shadercsv) as f:
        shaderlines = f.read().splitlines()
        for line in shaderlines[1:]:
            shader = line.split(",")
            if len(shader) >= 3:
                path = os.path.dirname(__file__) + "/shaders/" + shader[0]
                if os.path.isfile(path):
                    shader_conf = {"name": shader[0].split(".")[0],
                                   "display_name": " ".join(shader[0].split(".")[0].split("_")).title(),
                                   "file_path": path,
                                   "intensity_min": float(shader[1]),
                                   "intensity_max": float(shader[2]),
                                   "is_effect": False,
                                   "group": shader[3],
                                   "weight": float(shader[4]) / float(max(1, int(shader[2]) - int(shader[1])) * 0.3)
                                   }
                    if shader[3] == "":
                        shader_conf["group"] = shader_conf["name"].split("_")[0]
                    if shader[0].split(".")[1] == "effect":
                        shader_conf["is_effect"] = True
                    shaders.append(shader_conf)
                else:
                    v_print(-1, f'Shader {shader[0]}, not found. no such file: {path}')
        v_print(1, f'Added {len(shaders)} shaders!')
    for i in range(5):
        fire_path = os.path.dirname(__file__) + "/shaders/on_fire_" + str(i + 1) + ".effect"
        if os.path.isfile(fire_path):
            fireshaders.append({
                "name": "on_fire_" + str(i),
                "display_name": "On Fire " + str(i),
                "file_path": fire_path,
                "intensity": str(i),
                "is_effect": True,
                "group": "on_fire"
            })
        else:
            v_print(-1, f'Fire shader not found! No such file: {fire_path}')


def reset_penalty_box():
    for item in obs.get_scene_item_list(obs_sources["overlay_scene"]).scene_items:
        obs.remove_scene_item(obs_sources["overlay_scene"], item["sceneItemId"])
        # obs.remove_input(item["sourceName"])


def add_penalty_dvd(penalty):
    penaltyname = obs_sources["penalty_item"].replace("#", str(settings["runnin_id"]))
    settings["runnin_id"] += 1
    hue_shift = False
    if random.random() > 0.8:
        hue_shift = True
    crop_x = penalty_img_size + random.randint(0, 80) - 50
    crop_y = penalty_img_size + random.randint(0, 80) - 50
    vidset = settings["video"]
    penalty_settings = {'color_shift': hue_shift,
                        'hue_shift': 0,
                        'linear_alpha': True,
                        'logo_scale': (penalty["source"]["scale"] * (0.9 + random.random() * 0.2) * (
                                    1 + (penalty["intensity"] * random.random() * 0.2))) / (
                                                  penalty["multiplier"] * 0.5 + 0.5),
                        'source_cx': vidset["x"] / 2 + crop_x * 2,
                        'source_cy': vidset["y"] / 2 + crop_y * 2,
                        'file': os.path.dirname(__file__) + "/penalty_img/" + penalty["source"]["file"],
                        'source_id': 'image_source',
                        'speed': max(20, 100 + random.random() * 200 - penalty["intensity"] * 20) * (penalty[
                            "multiplier"]*0.6 + 0.4)}
    siid = obs.create_input(obs_sources["overlay_scene"], penaltyname, "dvds3_source", penalty_settings,
                            True).scene_item_id
    pos = [[0, 0], [vidset["x"] / 2, 0], [0, vidset["y"] / 2], [vidset["x"] / 2, vidset["y"] / 2]]
    transform = {
        'cropBottom': crop_y,
        'cropLeft': crop_x,
        'cropRight': crop_x,
        'cropTop': crop_y,
        'positionX': pos[penalty["seat"]][0],
        'positionY': pos[penalty["seat"]][1],
        'rotation': 0.0,
        'scaleX': 1.0,
        'scaleY': 1.0,
        'sourceWidth': vidset["x"] / 2 + crop_x * 2,
        'sourceHeight': vidset["y"] / 2 + crop_y * 2,
        'width': vidset["x"] / 2 + crop_x * 2,
        'height': vidset["y"] / 2 + crop_y * 2
    }
    obs.set_scene_item_transform(obs_sources["overlay_scene"], siid, transform)


def v_print(v, pstr):
    if v <= settings["verbosity"]:
        if v < 0:
            print(pstr, file=sys.stderr)
        else:
            print(pstr)

def use_weapon(use, state):
    global players
    global weapon_uses
    if use["weapon"] == 0:  # SEND FRIENDS
        if state["line"][use["target"]] < settings["controllers"]:
            penalties = state["spes"][use["target"]].count("-")
            for wu in weapon_uses:
                if wu["weapon"] == 0 and wu["target"] == use["target"]:
                    penalties += 1
            count = math.ceil(pow(random.random(), 5) * 6 + 0.001)
            penalty_source = settings["penalty_img"][random.randint(0, len(settings["penalty_img"]) - 1)]
            add_penalty_dvd({"source": penalty_source, "seat": state["line"][use["target"]], "intensity": penalties, "multiplier": count})
    if use["weapon"] == 1:  # SEND SHIT
        if state["line"][use["target"]] < settings["controllers"]:
            shader = get_shader(use["target"], settings["rounds"], 1, settings["rounds"] / 7)
            game_screen = obs_sources["game_screen"].replace("#", str(state["line"][use["target"]] + 1))
            create_shader(game_screen, shader)
    if use["weapon"] == 2:  # BAN PLAYER
        pass
    if use["weapon"] == 3:  # REROLL
        update_shaders(True)


if __name__ == "__main__":
    if not init_conf():
        quit()
    if not settings["reconnect"]:
        init_scenes()
    if not settings["gamecode"]:
        quit()
    main()

