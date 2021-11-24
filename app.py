import os, sys, time, math, argparse, json, datetime, yaml, sqlite3

import streamlit as st
ss = st.session_state # global shorthand for this file

import pandas as pd
import tools.util as util
import match

import plotly.express as px
import plotly.graph_objects as go

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# sqlite connections
con = sqlite3.connect('demos.db')
cur = con.cursor()

# global vars/config
config = yaml.safe_load(open('data/config.yaml'))
h2p    = json.loads(open('data/hero2player.json').read())

# setup global vars for st
if "sid" not in ss: ss.sid = []
if "mid" not in ss: ss.mid = []
if "view" not in ss: ss.view = None

# setup series/match multiselect dataframes
if 'series' not in ss:	
	ss.series 		= pd.read_sql_query("SELECT * FROM Series", con)
	ss.series['date'] = pd.to_datetime(ss.series['series_date'])
	ss.series['date'] = ss.series['date'].dt.date
if 'matches' not in ss:
	ss.matches 			= pd.read_sql_query("SELECT * FROM Matches", con)



# filter series by settings
def series_filters():
	dates_expander = st.sidebar.expander('filters',expanded=False)
	series_filters = {}
	with dates_expander:
		dates = ss.series['date'].tolist()
		series_filters['date_first'] = st.date_input('start date filter',value=dates[0],min_value=dates[0],max_value=dates[-1])
		series_filters['date_last']  = st.date_input('end date filter', value=dates[-1],min_value=series_filters['date_first'] ,max_value=dates[-1])
		series_filters['kickball']   = st.checkbox('kickball',	  value=True,help="Any kickball/community series")
		series_filters['scrims']     = st.checkbox('scrims', value=True,help="Any non-KB, typically set team versus team")
	series_filtered = ss.series[(ss.series['date'] >= series_filters['date_first']) & (ss.series['date'] <= series_filters['date_last'])]

	# filter series by series type
	if not series_filters['kickball'] and series_filters['scrims']:
		series_filtered = series_filtered[series_filtered['kb'] == 0]
	if series_filters['kickball'] and not series_filters['scrims']:
		series_filtered = series_filtered[series_filtered['kb'] == 1]

	return series_filtered


def update_query():
	if 'match' in ss.view:
		st.experimental_set_query_params(s=ss.sid,m=ss.mid)
	elif 'series' in ss.view:
		st.experimental_set_query_params(s=ss.sid)
	else:
		st.experimental_set_query_params()


def sidebar():
	st.sidebar.title('uuralur')

	with st.sidebar.container():
		ss.view = {st.radio('view mode',['match','series','players'],help='View demo data by single Match, Series (i.e. a night of matches), or by Players (with series filtering)'):None}
	
	pickers = st.sidebar.container()

	navigator = st.sidebar.container()

	sid_filtered = series_filters() # filter series for selecting by options
	sid_filtered = sid_filtered['series_id'].to_list()
	sid_filtered.reverse()
	

	# only show MID picker if single SID selected
	if 'match' in ss.view or 'series' in ss.view:
		ss.sid = pickers.selectbox("series",sid_filtered,on_change=update_query,help='In YYMMDD format with tags for either teams playing or KB')

		if 'match' in ss.view:
			sid_matches = ss.matches[ss.matches['series_id'] == ss.sid] # update match list for SID only

			# format text to display map name in multiselect
			sid_mids = sid_matches['match_id']
			
			sid_matches = sid_matches.set_index('match_id') # update match list for SID only
			def format_mid_str(mid):
				return str(mid) + " (" + sid_matches.loc[mid,'map'] + ")"
			
			ss.mid = pickers.selectbox("match",sid_mids,format_func=format_mid_str,on_change=update_query,help='Match number from series in order played') 
			ss.map = sid_matches.loc[ss.mid,'map']
	update_query()
	with navigator:
		if 'match' in ss.view:
			ss.view['match'] = st.radio('navigation',['summary','spikes','offence','defence','support','logs'])
		if 'series' in ss.view:
			ss.view['series'] = st.radio('navigation',['summary','offence','defence','support'])

# load URL queries only on initial load
def load_queries():
	querys = st.experimental_get_query_params()
	ss.view = {'match':'summary'}
	if 'init_queries' not in ss:
		ss.init_queries = st.experimental_get_query_params()
		if 's' in ss.init_queries:
			sid_check = ss.init_queries['s'][0]
			if sid_check in ss.series['series_id']:
				ss.sid = sid_check
				if 'm' in ss.init_queries:
					ss.view = {'match':'summary'}
				else:
					ss.view = {'series':'summary'}

def init_css(width):
	st.markdown(
			f"""
	<style>
		.reportview-container .main .block-container{{
			# min-width: """+str(width/2)+"""px;
			max-width: """+str(width)+"""px;
		}}
		# {{
		# }}
		.font40 {
		    font-size:40px !important;
		    font-weight: bold;
		    font-family: 'Roboto', sans-serif;
		    margin-top: 12px;
		    margin-bottom: 28px;
		}
		.font20 {
		    font-size:20px !important;
		    font-weight: bold;
		    font-family: 'Roboto', sans-serif;
		    margin-top: 6px;
		    margin-bottom: 6px;
		}
	</style>
	""",
			unsafe_allow_html=True,
)
def body():

	init_css(1440)

	if 'match' in ss.view:
		match.main(con)

def main():
	st.set_page_config(
		page_title='uuralur',
		page_icon='🤖',
		# layout="wide", # manual widths via body_width hack
		initial_sidebar_state="expanded",
	)
	# load_queries() # not working yet
	sidebar()
	body()



if __name__ == '__main__':
	main()