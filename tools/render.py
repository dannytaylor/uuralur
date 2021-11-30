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
	else return {"color":"rgba(0,0,0,0.87)",};
}
""")

# not used currently
spike_list = JsCode("""
function(params) {
	if(params.data.kill == "1") {
		return {"backgroundColor":"rgba(255, 127, 80, 0.1)", "color":text_color};
	}
}
""")

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
	st.markdown(f"""
	<style>
		.reportview-container .main .block-container{{
			min-width: """+str(width)+"""px;
			max-width: """+str(width)+"""px;
			padding: 3rem 1rem 1rem;
		}}
		# {{
		# }}
		.font40 {
		    font-size:40px !important;
		    font-weight: bold;
		    font-family: 'Roboto', sans-serif;
		    margin-top: 12px;
		    margin-bottom: 34px;
		}
		.font20 {
		    font-size:20px !important;
		    font-weight: bold;
		    font-family: 'Roboto', sans-serif;
		    margin-top: 6px;
		    margin-bottom: 6px;
		}
	</style>
	""", unsafe_allow_html=True,
)

team_name_map = {
	"kb":"kickball",
	"gb":"good boys",
	"rng":"renegades",
	"inc":"incursion",
	"jh":"rare",
	"brew":"brewery",
	"mft":"misfits",
	"lc":"laughing coffin",
	"ps":"pspsps",
	"wd":"watchdogs",
	"miswap":"misfits/wap",
}