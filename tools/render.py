from st_aggrid import JsCode
import streamlit as st

# functions for rendering styles and formatting in AgGrid
# and color maps for graphs

# return base64 image html to be rendered
# original before aggrid change
icon1 = JsCode("""
function(params) {
	return params.value ? params.value : '';
}
""")
icon = JsCode("""
class UrlCellRenderer {
  init(params) {
    this.eGui = document.createElement('img');
    this.eGui.setAttribute('src', params.value);
  }
  getGui() {
    return this.eGui;
  }
}
""")

spacer_base64 = "<img src=\"data:image/jpeg;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAQAAADZc7J/AAAAH0lEQVR42mNkoBAwjhowasCoAaMGjBowasCoAcPNAACOMAAhOO/A7wAAAABJRU5ErkJggg==\">"

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
	if(params.data.team == "0") {return {"color":"#1946cf",};} 
	else return {"color":"#d60000",};
}
""")
team_color_bold = JsCode("""
function(params) {
	if(params.data.team == "0") {return {"color":"#1946cf","font-weight":"bold"};} 
	else return {"color":"#d60000","font-weight":"bold"};
}
""")

target_team_color = JsCode("""
function(params) {
	if(params.data.target_team == "0") {return {"color":"#1946cf",};} 
	else return {"color":"#d60000",};
}
""")

blu = JsCode("""
function(params) {
	return {"color":"#1946cf"};
}
""")

red = JsCode("""
function(params) {
	return {"color":"#d60000"};
}
""")


# render cell text color from support tag
support_color = JsCode("""
function(params) {
	if(params.data.support == "1") {return {"color":"seagreen",};} 
	else return {"color":"rgba(0,0,0,0.87)",};
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

grid_css = {
    "#gridToolBar": {"display": "none"}
    }

def set_width(width: str):
	if not st.session_state.mobile:
		pass
	st.markdown(
	
	f"""
	<style>
	.appview-container .main .block-container{{ max-width: {width}; }}

	""",
	    unsafe_allow_html=True,
	)


def css_rules():

	if st.session_state.mobile:
		maxwidth = "100%"
		minwidth = "100%"
	else:
		maxwidth = "1280px"
		minwidth = maxwidth

	css_str = f"""
		<style>
		@import url('https://fonts.googleapis.com/css2?family=Inter'); 

		html, body, [class*="css"] {{
		    font-family: 'Inter', sans-serif;
		}}

		.appview-container .main .block-container{{ 
			max-width: {maxwidth}; 
			min-width: {minwidth};
			min-height: {minwidth};
			padding: 2rem 1rem 1rem;
		}}

		ag-row-level-0 

		#gridToolBar {{
			display: none;
			max-height: 0px;
		}}

		.font40 {{
		    font-size:36px !important;
		    font-weight: bold;
		    font-family: 'Inter', sans-serif;
		    margin-top: 16px;
		    margin-bottom: 48px;
		}}

		.fontheader {{
		    font-size:28px !important;
		    font-weight: bold;
		    font-family: 'Inter', sans-serif;
		}}
		.font20 {{
		    font-size:20px !important;
		    font-weight: bold;
		    font-family: 'Inter', sans-serif;
		}}
		</style>
		"""

	st.markdown(css_str,unsafe_allow_html=True)

team_name_map = {
	"kb":"kickball",
	"taco":"taco",
	"pug":"pug",
	"ttd":"thursday throwdown",
	"event":"event",

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
	"tbbz":"blackout boys",
	"doom":"DOOM",
	"sos":"significant otters",
	"obs":"only bans",

	# "jh":"jh", # one match that has been renamed to correct
	"rare":"rare",
	"vori":"vori",
	"four":"four",
	"elk":"elk",
	"putos":"putos",

	"dl1":"(draft league)",
}

kb_tags = {"kb","pug","community","taco","ttd","event"}