uniform float center_x_percent<
    string label = "Center x percent";
    string widget_type = "slider";
    float minimum = 0.0;
    float maximum = 100.0;
    float step = 0.01;
> = 50.0;
uniform float center_y_percent<
    string label = "Center x percent";
    string widget_type = "slider";
    float minimum = 0.0;
    float maximum = 100.0;
    float step = 0.01;
> = 50.0;


float4 mainImage(VertData v_in) : TARGET
{
    float2 center_pos = float2(center_x_percent * .01, center_y_percent * .01);
    float2 uv = v_in.uv;
    float power = float(sin(elapsed_time*0.5)*0.6 + sin(elapsed_time*0.021+2.0)*0.3);
    if (power > 0.0){
        float b = 0.4;// sqrt(dot(center_pos, center_pos));
        uv = center_pos  + normalize(v_in.uv - center_pos) * tan(distance(center_pos, v_in.uv) * (0.3+power*2.5)) * b / tan( b * (0.3+power*3.0));
    } else if(power < 0){
        float b;
        if (uv_pixel_interval.x < uv_pixel_interval.y){
            b = center_pos.x;
        } else {
            b = center_pos.y;
        }
        uv = center_pos  + normalize(v_in.uv - center_pos) * atan(distance(center_pos, v_in.uv) * -power * 10.0) * b / atan(-power * b * 10.0);
    }
    return image.Sample(textureSampler, uv);
}
