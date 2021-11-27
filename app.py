import os, sys, time, math, argparse, json, datetime, yaml, sqlite3

import streamlit as st
ss = st.session_state # global shorthand for this file

import pandas as pd
import tools.util as util
import tools.render as render
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
if 'match' not in ss:
	ss.matches = pd.read_sql_query("SELECT * FROM Matches", con)
if 'new_mid' not in ss: ss.new_mid = False

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

		st_sidebar_title = st.sidebar.empty()
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

		def set_query():
			params = st.experimental_get_query_params()
			if 'sid_key' in ss:
				params['s'] = ss['sid_key']
				params['m'] = ss['mid_key']
				st.experimental_set_query_params(**params)
		def clear_query():
			st.experimental_set_query_params()

		# sidebar layout setup
		sid_empty = st.sidebar.empty()
		mid_empty = st.sidebar.empty()
		nav_empty = st.sidebar.empty()
		app_exp = st.sidebar.expander('viewer', expanded=True)
		filter_exp = st.sidebar.empty()

		# page selecter
		if ss.new_mid:
			ss['app_choice'] = 'match'
			app_choice = app_exp.radio("viewer", self.app_names,on_change=clear_query,key='app_choice')
			ss.new_mid = False
		else:
			app_choice = app_exp.radio("viewer", self.app_names,on_change=clear_query,key='app_choice')
		nav_names = self.app_view[app_choice]
		st_sidebar_title.title(app_choice)

		# series list getter and filterer
		def series_filters():
			exp = filter_exp.expander('series filters', expanded=False)
			series_filters = {}
			dates = ss.series['date'].tolist()
			series_filters['date_first'] = exp.date_input('start date filter',value=dates[0],min_value=dates[0],max_value=dates[-1],on_change=clear_query)
			series_filters['date_last']  = exp.date_input('end date filter', value=dates[-1],min_value=series_filters['date_first'] ,max_value=dates[-1],on_change=clear_query)
			series_filters['kickball']   = exp.checkbox('kickball',	  value=True,help="Any kickball/community series",on_change=clear_query)
			series_filters['scrims']     = exp.checkbox('scrims', value=True,help="Any non-KB, typically set team versus team",on_change=clear_query)
			
			# apply filters and list sids
			series_filtered = ss.series[(ss.series['date'] >= series_filters['date_first']) & (ss.series['date'] <= series_filters['date_last'])]
			# filter series by series type
			if not series_filters['kickball'] and series_filters['scrims']:
				series_filtered = series_filtered[series_filtered['kb'] == 0]
			if series_filters['kickball'] and not series_filters['scrims']:
				series_filtered = series_filtered[series_filtered['kb'] == 1]
			series_ids = series_filtered['series_id'].to_list()
			series_ids.reverse()
			return series_ids
		if app_choice == 'match':
			series_ids = series_filters()


		def match_select():
			# get query and set if allowable
			if query_sid_choice in series_ids:
				ss[sid_key] = query_sid_choice
				sid_mids = ss.matches[ss.matches['series_id'] == query_sid_choice]['match_id'].tolist()
				if ss.new_mid:
					ss[mid_key] = ss.mid
					ss.new_mid = False
				elif query_mid_choice in sid_mids:
					ss[mid_key] = query_mid_choice 
				else: 
					ss[mid_key] = sid_mids[0]
			else:
				ss[sid_key] = series_ids[0]

			ss.sid = sid_empty.selectbox("series",series_ids,on_change=set_query,help='In YYMMDD format with tags for either teams playing or KB',key=sid_key)


			# match picker
			sid_matches = ss.matches[ss.matches['series_id'] == ss.sid] # update match list for SID only
			ss.sid_mids = sid_matches['match_id'].tolist()
			ss.sid_mids.sort()
			def format_mid_str(mid):
				row = sid_matches[sid_matches['match_id']==mid]
				mid_map = row.iloc[0]['map']
				return str(mid) + " (" + mid_map + ")"
			ss.mid = mid_empty.selectbox("matches",ss.sid_mids,format_func=format_mid_str,on_change=set_query,help='Match number from series in order played',key=mid_key) 

		page_view  = nav_empty.radio("navigation", nav_names ,on_change=set_query)

		# if in match view mode
		if app_choice == 'match':
			match_select()
		ss.view = {app_choice:page_view}
		
		return app_choice

	def run(self):
		# callback to update query param from app choice
		viewer = self.sidebar()

		# run the selected app
		app = self.apps[self.app_names.index(viewer)]
		app['function'](app['title'], *app['args'], **app['kwargs'])

def view_match(title, info=None):
	match.main(con)

def view_players(title, info=None):
	players.main(con)


def main():
	mp = MultiPage()
	mp.add_app('match', ['summary','spikes','offence','defence','support','logs','series'] , view_match, info='')
	mp.add_app('records',['summary','player stats'], view_players, info='')
	mp.run()


if __name__ == '__main__':
	st.set_page_config(
		page_title='uuralur',
		page_icon='🤖',
		# layout="wide", # manual widths via body_width hack
		initial_sidebar_state="expanded",
	)
	render.init_css(1440)
	main()