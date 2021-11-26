import os, sys, time, math, argparse, json, datetime, yaml, sqlite3

import streamlit as st
ss = st.session_state # global shorthand for this file

import pandas as pd
import tools.util as util
import view.match as match
import view.players as players

import plotly.express as px
import plotly.graph_objects as go

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# sqlite connections
con = sqlite3.connect('demos.db')
cur = con.cursor()

# global vars/config
config = yaml.safe_load(open('data/config.yaml'))
h2p    = json.loads(open('data/hero2player.json').read())

# setup series/match multiselect dataframes
if 'series' not in ss:	
	ss.series 		= pd.read_sql_query("SELECT * FROM Series", con)
	ss.series['date'] = pd.to_datetime(ss.series['series_date'])
	ss.series['date'] = ss.series['date'].dt.date
if 'matches' not in ss:
	ss.matches = pd.read_sql_query("SELECT * FROM Matches", con)

def init_css(width):
	st.markdown(f"""
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
	""", unsafe_allow_html=True,
)

class MultiPage:
	def __init__(self):
		self.apps = []
		self.app_names = []
		self.app_view = {}

	def add_app(self, title, views, func, *args, **kwargs):
		self.app_names.append(title)
		self.app_view[title] = views
		self.apps.append({
			"title": title,
			"views": views,
			"function": func,
			"args":args,
			"kwargs": kwargs
		})

	def sidebar(self):

		st.sidebar.title('uuralur')
		# st keys
		sid_key='sid_key'
		mid_key='mid_key'

		# get app choice from query_params
		query_params = st.experimental_get_query_params()
		query_sid_choice = query_params['s'][0] if 's' in query_params else None
		if 'm' in query_params and query_params['m'][0].isnumeric():
			query_mid_choice = int(query_params['m'][0])  
		else:
		 	query_mid_choice = None

		# update session state (this also sets the default radio button selection as it shares the key!)
		# ss[key] = query_app_choice if query_app_choice in self.app_names else self.app_names[0]
		# if 'match' in ss.view:
		# 	if 'sid_key' in ss and 'mid_key' in ss:
		# 		ss[sid_key] = query_sid_choice if query_sid_choice in self.app_names else self.app_names[0]

		def on_change():
			params = st.experimental_get_query_params()
			params['s'] = ss['sid_key']
			params['m'] = ss['mid_key']
			st.experimental_set_query_params(**params)

		# sidebar layout setup
		sid_empty = st.sidebar.empty()
		mid_empty = st.sidebar.empty()
		nav_empty = st.sidebar.empty()
		app_exp = st.sidebar.expander('viewer', expanded=False)

		# page selecter
		app_choice = app_exp.radio("viewer", self.app_names)
		nav_names = self.app_view[app_choice]

		if app_choice == 'match':
			# series picker
			series_ids = ss.series['series_id'].to_list()
			series_ids.reverse()

			# get query and set if allowable
			if query_sid_choice in series_ids:
				ss[sid_key] = query_sid_choice
				sid_mids = ss.matches[ss.matches['series_id'] == query_sid_choice]['match_id'].tolist()
				ss[mid_key] = query_mid_choice if query_mid_choice in sid_mids else sid_mids[0]
			else:
				ss[sid_key] = series_ids[0]

			ss.sid = sid_empty.selectbox("series",series_ids,on_change=on_change,help='In YYMMDD format with tags for either teams playing or KB',key=sid_key)


			# match picker
			sid_matches = ss.matches[ss.matches['series_id'] == ss.sid] # update match list for SID only
			sid_mids = sid_matches['match_id'].tolist()
			sid_mids.sort()
			def format_mid_str(mid):
				row = sid_matches[sid_matches['match_id']==mid]
				mid_map = row.iloc[0]['map']
				return str(mid) + " (" + mid_map + ")"
			ss.mid = mid_empty.selectbox("match",sid_mids,format_func=format_mid_str,on_change=on_change,help='Match number from series in order played',key=mid_key) 

		page_view  = nav_empty.radio("navigation", nav_names ,on_change=on_change)
		ss.view = {app_choice:page_view}

		return app_choice

	def run(self):
		# callback to update query param from app choice
		viewer = self.sidebar()

		# run the selected app
		app = self.apps[self.app_names.index(viewer)]
		app['function'](app['title'], *app['args'], **app['kwargs'])

def app1(title, info=None):
	match.main(con)

def app2(title, info=None):
	st.title(title)
	st.write(info)

	# player.main(con)


def main():
	mp = MultiPage()
	mp.add_app('match', ['summary','spikes','offence','defence','support','logs','series'] , app1, info='Hello from App 1')
	mp.add_app('player',['summary'], app2, info='Hello from App 2')
	mp.run()




if __name__ == '__main__':
	st.set_page_config(
		page_title='uuralur',
		page_icon='🤖',
		# layout="wide", # manual widths via body_width hack
		initial_sidebar_state="expanded",
	)
	init_css(1440)
	main()