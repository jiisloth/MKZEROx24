import os
import time

from PIL import ImageGrab
import obsws_python as obs
import random

pos = [1920, 122]
size = [640, 480]
source = "template.png"
redoall = False

config = {}

shaders = []


def main():
    global states
    global vidset
    read_conf()
    random.seed(int(config["SEED"]))
    read_shaders(config["SHADER_CSV_FILE"])
    cl = obs.ReqClient(host=config["OBS_WS_URL"], port=int(config["OBS_WS_PORT"]), password=config["OBS_WS_PASS"], timeout=3)
    cl.open_source_projector(source, -1, "AdnQywADAAAAAAAAAAAAZAAAAn8AAAJDAAAAAAAAAHoAAAJ/AAACWQAAAAAAAAAAAAAAAAAAAAAAegAAAn8AAAJZ")
    i = 0
    for shader in shaders:
        if os.path.isfile(config["PROJECT_DIR_PATH"] + "shader_thumb/" + shader["filename"].split(".")[0] + ".png") and not redoall:
            continue
        shadersettings = {'from_file': True,
                          'override_entire_effect': shader["is_effect"],
                          'use_shader_elapsed_time': False,
                          'shader_file_name': config["PROJECT_DIR_PATH"] + "shaders/" + shader["filename"]
                          }
        cl.create_source_filter(source, shader["filename"], "shader_filter", shadersettings)
        time.sleep(0.2)
        screenshot = ImageGrab.grab(bbox=(pos[0], pos[1], pos[0]+size[0], pos[1]+size[1]))
        screenshot.save(config["PROJECT_DIR_PATH"] + "shader_thumb/" + shader["filename"].split(".")[0] + ".png", 'PNG')
        time.sleep(0.2)
        cl.remove_source_filter(source, shader["filename"])
        i += 1
        print(f'Tumbnail done for {shader["filename"].split(".")[0].ljust(50)} {str(i).rjust(3)}/{len(shaders)} - {i/len(shaders)*100 :.1f}%')



def read_conf():
    global config
    with open("config.cfg") as f:
        conf = f.read().splitlines()
        for line in conf:
            cfg = line.split("=")
            if len(cfg) == 2:
                config[cfg[0]] = cfg[1]


def read_shaders(shadercsv):
    with open(shadercsv) as f:
        shaderlines = f.read().splitlines()
        for line in shaderlines[1:]:
            shader = line.split(",")
            if len(shader) >= 3:
                path = config["PROJECT_DIR_PATH"] + "shaders/"+ shader[0]
                if os.path.isfile(path):
                    shader_conf = {
                        "filename": shader[0],
                        "is_effect": False,
                        }
                    if shader[3] == "":
                        shader_conf["group"] = shader_conf["name"].split("_")[0]
                    if shader[0].split(".")[1] == "effect":
                        shader_conf["is_effect"] = True
                    shaders.append(shader_conf)
                else:
                    print(f'Shader {shader[0]}, not found. no such file: {path}')
        print(f'Added {len(shaders)} shaders!')
    for i in range(5):
        fire_path = config["PROJECT_DIR_PATH"] + "shaders/on_fire_" + str(i) + ".effect"
        if os.path.isfile(fire_path):
            shaders.append({
                "filename": "on_fire_" + str(i)+".effect",
                "is_effect": True,
                })
        else:
            print(f'Fire shader not found! No such file: {fire_path}')



if __name__ == "__main__":
    main()