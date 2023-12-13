import os
import time

from PIL import ImageGrab
import obsws_python as obs
import random

pos = [1920, 122]
size = [640, 480]


config = {}

shaders = []


def main():
    global states
    global vidset
    read_conf()
    random.seed(int(config["SEED"]))
    read_shaders(config["SHADER_CSV_FILE"])
    cl = obs.ReqClient(host=config["OBS_WS_URL"], port=int(config["OBS_WS_PORT"]), password=config["OBS_WS_PASS"], timeout=3)

    random.shuffle(shaders)
    i = 1
    cl.set_current_program_scene("kuva")
    cl.start_record()

    for source in ["PlayerScreen1", "PlayerScreen2", "PlayerScreen3", "PlayerScreen4"]:
        shader_list = cl.get_source_filter_list(source)
        for shader in shader_list.filters:
            cl.remove_source_filter(source, shader["filterName"])
    time.sleep(0.5)
    for shader in shaders:
        cl.set_input_settings("Number", {"text": str(i)}, True)
        shadersettings = {'from_file': True,
                          'override_entire_effect': shader["is_effect"],
                          'use_shader_elapsed_time': False,
                          'shader_file_name': config["PROJECT_DIR_PATH"] + "shaders/" + shader["filename"]
                          }
        for source in ["PlayerScreen1","PlayerScreen2","PlayerScreen3","PlayerScreen4"]:
            cl.create_source_filter(source, shader["filename"], "shader_filter", shadersettings)
        print(f'{i} {shader["filename"]}')
        cl.set_current_program_scene("Peli")
        time.sleep(15)
        cl.set_current_program_scene("kuva")
        time.sleep(0.5)
        for source in ["PlayerScreen1","PlayerScreen2","PlayerScreen3","PlayerScreen4"]:
            cl.remove_source_filter(source, shader["filename"])
        i += 1
    cl.stop_record()



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
    return
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