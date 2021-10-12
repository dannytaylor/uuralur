import os, sys, time, math, argparse, json, datetime, yaml, sqlite3

import streamlit as st
import pandas as pd
import numpy as np
import tools.util as util

from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder
import plotly.express as px
import plotly.graph_objects as go


# sqlite connections
con = sqlite3.connect('demos.db')
cur = con.cursor()

# global vars/config
config = yaml.safe_load(open('data/config.yaml'))
h2p    = json.loads(open('data/hero2player.json').read())
sid,mid = None, None

# st state state vars
if 'series' not in st.session_state:	
	st.session_state.series 		= pd.read_sql_query("SELECT * FROM Series", con)
	st.session_state.series['date'] = pd.to_datetime(st.session_state.series['series_date'])
	st.session_state.series['date'] = st.session_state.series['date'].dt.date
if 'matches' not in st.session_state:
	st.session_state.matches 			= pd.read_sql_query("SELECT * FROM Matches", con)
	st.session_state.matches['match_id'] = st.session_state.matches['match_id'].astype(str) # easier to work with strings for other sections
	st.session_state.matches['mid_map'] = st.session_state.matches['match_id'] + ' (' + st.session_state.matches['map'] + ')'


matches = st.session_state.matches
series = st.session_state.series

def match_series_picker(picker,filters=None):
	global sid
	global mid

	series_ids = series[(series['date'] >= filters['date_first']) & (series['date'] <= filters['date_last'])]


	# apply filters to series id lister
	if filters['match_type'] == 'scrims':
		series_ids = series_ids[series_ids['kb'] == 0]
	elif filters['match_type'] == 'kickball':
		series_ids = series_ids[series_ids['kb'] == 1]
	series_ids = series_ids['series_id'].tolist()
	series_ids.reverse()

	# get queries
	queries = st.experimental_get_query_params()
	queries = {k: v[0] if isinstance(v, list) else v for k, v in queries.items()}  # fetch the first item in each query string as we don't have multiple values for each query string key for this
	default_sid = queries["s"] if "s" in queries and queries["s"] in series_ids else None
	default_mid = queries["m"] if "m" in queries and default_sid else None
	if 'sid_picker' not in st.session_state: st.session_state.sid_picker = default_sid
	if 'mid_picker' not in st.session_state: st.session_state.mid_picker = default_mid

	series_select = picker.multiselect('series', series_ids,default=sid,key='sid_picker')

	if len(series_select) == 1:
		sid = series_select[0]
		match_ids  	  = matches[matches['series_id'] == sid]
		match_display = match_ids['mid_map']
		match_default = None
		if mid:
			i = match_ids.loc[match_ids['match_id'] == mid].index[0]
			match_default = match_ids.loc[i,'mid_map']
		if mid not in match_ids['match_id'].values:
			mid = None
			
		match_select = picker.multiselect('match', match_display ,default=match_default)
		if len(match_select) == 1:
			mid = match_select[0].split(' ')[0]
		else:
			mid = None
	else:
		sid,mid = None, None

	
# sidebar content organization
def sidebar():
	st.sidebar.header('uuralur')

	picker = st.sidebar.container()
	series_filters = st.sidebar.expander('series filters')

	filters = {}
	with series_filters:
		dates = series['date'].tolist()
		filters['date_first'] = st.date_input('first date',value=dates[0],min_value=dates[0],max_value=dates[-1])
		filters['date_last']  = st.date_input('last date',value=dates[-1],min_value=dates[0],max_value=dates[-1])
		filters['match_type']   = st.radio('match types',['all','scrims','kickball'])

	match_series_picker(picker,filters)

# main content window
def viewer():
	return

# set the URL query based on sid and mid
def set_query():
	if sid:
		if mid:
			st.experimental_set_query_params(s=sid,m=mid)
		else:
			st.experimental_set_query_params(s=sid)
	else:
		st.experimental_set_query_params()
	return

def main():
	st.set_page_config(
		page_title='uuralur',
		page_icon='🤖',
		layout="wide",
		initial_sidebar_state="expanded",
	)

	sidebar()
	viewer()
	set_query()


if __name__ == '__main__':
	main()