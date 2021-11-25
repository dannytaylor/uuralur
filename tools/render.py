from st_aggrid import JsCode

# functions for rendering styles and formatting in AgGrid

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
	if(params.data.team == "🔵") {return {"color":"dodgerblue",};} 
	else return {"color":"tomato",};
}
""")

# render cell text color from support tag
support_color = JsCode("""
function(params) {
	if(params.data.support == "1") {return {"color":"seagreen",};} 
	else return {"color":"black",};
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

