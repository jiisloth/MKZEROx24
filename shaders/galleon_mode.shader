// Gamma Correction shader by Charles Fettinger for obs-shaderfilter plugin 4/2019
//https://github.com/Oncorporation/obs-shaderfilter

uniform float Red<
    string label = "Red";
    string widget_type = "slider";
    float minimum = 0.0;
    float maximum = 10.0;
    float step = 0.01;
> = 0;
uniform float Green<
    string label = "Green";
    string widget_type = "slider";
    float minimum = 0.1;
    float maximum = 10.0;
    float step = 0.01;
> = 1.2;
uniform float Blue<
    string label = "Blue";
    string widget_type = "slider";
    float minimum = 0.1;
    float maximum = 10.0;
    float step = 0.01;
> = 0.45;
uniform string notes<
    string widget_type = "info";
> = "Modify Colors to correct for gamma, use equal values for general correction."

float4 mainImage(VertData v_in) : TARGET
{  
	float3 gammaRGB = float3(1.0,clamp(Green,0.1,10.0),clamp(Blue,0.1,10.0));
	float4 c = image.Sample(textureSampler, v_in.uv);
	c.rgb = float3(0, c.g*0.9+c.r*0.1, c.r*0.1+c.b*0.9);
	c.rgb = pow(c.rgb, 1.0 / gammaRGB);	
	c.r = c.r*0.2;
	return c;
}
