uniform float speed<
    string label = "Speed";
    string widget_type = "slider";
    float minimum = 0.0;
    float maximum = 100.0;
    float step = 0.01;
> = 2.0;

float4 mainImage(VertData v_in) : TARGET
{
	float4 color = image.Sample(textureSampler, v_in.uv);
	float t = elapsed_time * speed;

	float blink = clamp((1.0 + sin(t)) / 2.0 + (1.0 + sin(2.1*t)*1.3) / 2.0,0.0,1.0);
	return float4(color.r, color.g, color.b, color.a * blink);
}
