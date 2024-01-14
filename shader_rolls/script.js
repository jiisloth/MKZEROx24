function titleCase(str) {
    str = str.split('_');
    for (var i = 0; i < str.length; i++) {
        str[i] = str[i].charAt(0).toUpperCase() + str[i].slice(1);
    }
    return str.join(' ');
}

function shuffleArray(array) {
    for (var i = array.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var temp = array[i];
        array[i] = array[j];
        array[j] = temp;
    }
}


let attr = decodeURI(window.location.search.substring(1)).split("&");
const ih = 164

let params = {
    "delay": 0,
    "rolls": []
}

console.log(attr)
for (let i = 0; i < attr.length; i++) {
    let param = attr[i].split("=")
    if (param.length === 2){
        params[param[0]] = param[1]
    } else {
        params["rolls"].push(parseInt(param[0]))
    }
}
console.log(params["rolls"])
let rolls = ""
for (let i = 0; i < params["rolls"].length; i++) {
    if (params["rolls"][i] < 0){
        continue
    }
    let shader = shaders[params["rolls"][i]]
    let roll = '<div class="rollholder rollh' +i + '"><div class="rolline"></div><div class="rollfade roll' + i + '"><div id="roll_' + i + '" class="roll">'

    for (let r = 0; r < 100; r++) {
        let rshader = shaders[Math.floor(Math.random()*shaders.length)]
        let rshader2 = shaders[Math.floor(Math.random()*shaders.length)]
        if (Math.abs(rshader2["intensity"] - shader["intensity"]) < Math.abs(rshader["intensity"] - shader["intensity"])){
            rshader = rshader2
        }
        if (r === 10){
            rshader = shader
        }
        let sn = rshader["name"]
        let si = rshader["intensity"]
        let red = Math.min(255, (si * 2) * 255)
        let green = Math.min(255, ((1 - si) * 2) * 255)
        let style = "color: rgb(" + red + "," + green + ",0); background-image: url('shader_thumb/" + sn + ".png')"
        if (r === 10){
            roll += '<div class="chosen" style="' + style + '">' + titleCase(sn) + '</div>'
        } else {
            roll += '<div style="' + style + '">' + titleCase(sn) + '</div>'
        }
    }
    roll += '</div></div></div>'
    rolls += roll

}
document.getElementById("screen").innerHTML = rolls

for (let i = 0; i < params["rolls"].length; i++) {
    if (params["rolls"][i] < 0) {
        continue
    }
    document.getElementById("roll_"+ i).style.transition = "all "+ (2+Math.random()*2 + i) +"s cubic-bezier(0.18, 0.64, " + (0.4 +Math.random()*0.2) +", " + (0.97 + Math.random()*0.1) +") 0s"
    setTimeout(function () {
        document.getElementById("roll_"+ i).style.marginTop = -ih*10 -30 - (ih-30)* Math.random() + "px";
        }, 1)
}
setTimeout(function () {
    document.getElementById("screen").style.display = "none"
}, 11000)

