from st_aggrid import JsCode
import streamlit as st

# functions for rendering styles and formatting in AgGrid
# and color maps for graphs

# return base64 image html to be rendered
icon = JsCode("""
function(params) {
	return params.value ? params.value : '';
}
""")

# helper function for reading aggrid param data
console = JsCode("""
function(params) {
	console.log({
	"params": params, // object from cell
	"data": params.data, // dict of row
	"value": params.value, // value of cell
})}
""")

# render cell text color from team
team_color = JsCode("""
function(params) {
	if(params.data.team == "0") {return {"color":"dodgerblue",};} 
	else return {"color":"tomato",};
}
""")

target_team_color = JsCode("""
function(params) {
	if(params.data.target_team == "0") {return {"color":"dodgerblue",};} 
	else return {"color":"tomato",};
}
""")

blu = JsCode("""
function(params) {
	return {"color":"dodgerblue"};
}
""")

red = JsCode("""
function(params) {
	return {"color":"tomato"};
}
""")


# render cell text color from support tag
support_color = JsCode("""
function(params) {
	if(params.data.support == "1") {return {"color":"seagreen",};} 
	else return {"color":"rgba(250,250,250,250.87)",};
}
""")

# bg opacities from param
deaths_bg = JsCode("""
function(params) {
	var c = "rgba(229, 57, 53,"+params.data.deaths_opacity+")";
	return {"background-color":c,"text-align": "center"};
}
""")
targets_bg = JsCode("""
function(params) {
	var c = "rgba(251, 192, 45,"+params.data.targets_opacity+")";
	return {"background-color":c,'text-align': 'center'};
}
""")
surv_bg = JsCode("""
function(params) {
	var c = "rgba(0, 137, 123,"+params.data.surv_opacity+")";
	return {"background-color":c,'text-align': 'center'};
}
""")
otp_bg = JsCode("""
function(params) {
	var c = "rgba(67, 160, 71,"+params.data.otp_opacity+")";
	return {"background-color":c,'text-align': 'center'};
}
""")
ontgt_bg = JsCode("""
function(params) {
	var c = "rgba(124, 179, 66,"+params.data.ontgt_opacity+")";
	return {"background-color":c,'text-align': 'center'};
}
""")
onheal_bg = JsCode("""
function(params) {
	var c = "rgba(67, 160, 71,"+params.data.onheal_opacity+")";
	return {"background-color":c,'text-align': 'center'};
}
""") # percent on heal
onhealn_bg = JsCode("""
function(params) {
	var c = "rgba(124, 179, 66,"+params.data.onhealn_opacity+")";
	return {"background-color":c,'text-align': 'center'};
}
""") # count on heal



# heal, atk, green, jaunt, phase, other/death
spike_action_color = JsCode("""
function(params) {
	if(params.data.cell_color == "0") {return {"color":"#328464"};}
	else if(params.data.cell_color == "1") {return {"color":"#b4202a"};}
	else if(params.data.cell_color == "2") {return {"color":"#14a02e"};}
	else if(params.data.cell_color == "3") {return {"color":"#588dbe"};}
	else if(params.data.cell_color == "4") {return {"color":"#285cc4"};}
	else {return {"color":"#333941"};}
}
""")

spike_hit_color = JsCode("""
function(params) {
	if(params.data.hit_color == "1") {return {"color":"crimson"};}
	else if(params.data.hit_color == "2") {return {"color":"darkblue"};}
}
""")

heal_colours = {
	"Heal Other":"#5ac54f",
	"Absorb Pain":"#33984b",
	"Soothe":"#ea323c",
	"Share Pain":"#891e2b",
	"Rejuvenating Circuit":"#00cdf9",
	"Insulating Circuit":"#0069aa",
	"Cauterize":"#ffa214",
	"O2 Boost":"#657392",
	"Glowing Touch":"#fdd2ed",
	"Aid Other":"#134c4c",
	"Spirit Ward":"#622461",
	"Alkaloid":"#99e65f",
}

def init_css(width):
	css_str = f"""
		<style>
			.reportview-container .main .block-container{{
				padding: 1rem 1rem 1rem;
		"""
	if not st.session_state.mobile:
		css_str += f"""
				min-width: """+str(width-200)+"""px;
				max-width: """+str(width)+"""px;
			"""
	css_str += """}}{{}}
		.font40 {
		    font-size:32px !important;
		    font-weight: bold;
		    font-family: 'Helvetica Neue', sans-serif;
		    margin-top: 12px;
		    margin-bottom: 48px;
		}

		.fontheader {
		    font-size:24px !important;
		    
		    font-family: 'Helvetica Neue', sans-serif;
		}
		.font20 {
		    font-size:20px !important;
		    font-weight: bold;
		    font-family: 'Helvetica Neue', sans-serif;
		    margin: 0.5rem;
		}
		</style>
		"""
	st.markdown(css_str,unsafe_allow_html=True)

team_name_map = {
	"kb":"kickball",
	"gb":"good boys",
	"rng":"renegades",
	"inc":"incursion",
	"brew":"brewery",
	"mft":"misfits",
	"lc":"laughing coffin",
	"ps":"pspsps",
	"wd":"watchdogs",
	"miswap":"misfits/wap",
	"ggz":"gossipy guyz",
	"cum":"constantly under managed",
	"wap":"war against peace",

	# "jh":"jh", # one match that has been renamed to correct
	"rare":"rare",
	"vori":"vori",
	"four":"four",
	"elk":"elk",
	"pug":"pug",
	"putos":"putos",
	"taco":"taco",
}

powerset_icon_map = {
	"Fire Blast":"fireblast_blaze.png",
	"Ice Blast":"iceblast_bitterfrostblast.png",
	"Empathy":"empathy_healother.png",
	"Electrical Affinity":"shocktherapy_insulatingcircuit.png",
	"Nature Affinity":"natureaffinity_wildbastion.png",
	"Radiation Emission":"radiationpoisoning_enervatingfield.png",
	"Poison":"poison_envenomaoe.png"
}