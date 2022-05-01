import os, sys, time, math, argparse, json, yaml, sqlite3, duckdb

import streamlit as st
ss = st.session_state # global shorthand for this file

import pandas as pd
import tools.util as util
import tools.render as render
import datetime

import view.match as match
import view.players as players
import view.upload as upload
import view.info

import parse

import plotly.express as px
import plotly.graph_objects as go

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

st.set_page_config(
	page_title='coh demos',
	page_icon='🤖',
	initial_sidebar_state="expanded",
)

# sqlite connections
con = duckdb.connect('demos.duck.db')
# cur = con.cursor()

# global vars/config
config = yaml.safe_load(open('data/config.yaml'))
# h2p    = json.loads(open('data/hero2player.json').read())

# setup series/match multiselect dataframes
def init_series():
	ss.series 		= pd.read_sql_query("SELECT * FROM Series", con)
	ss.series['date'] = pd.to_datetime(ss.series['series_date'])
	ss.series['date'] = ss.series['date'].dt.date
def init_matches():
	ss.matches = pd.read_sql_query("SELECT * FROM Matches", con)
	ss.matches['sid_mid'] = ss.matches['series_id'] + "_" + ss.matches['match_id'].astype(str)
if 'series' not in ss:	
	init_series()
if 'match' not in ss:
	init_matches()
if 'new_mid' not in ss: ss.new_mid = False
if 'mobile'  not in ss: 
	ss['mobile']  = False

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
		# st.sidebar.image('assets/sidebar_header.png')
		st.sidebar.markdown("""
			<a href='/'>
			<img src='https://raw.githubusercontent.com/dannytaylor/uuralur/bad1599d072cc570ff167e27afb23d960a7fda3f/assets/sidebar_header.png'>
			</a><p/>
			""",True)
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

		def set_query():
			params = st.experimental_get_query_params()
			if 'sid_key' in ss:
				params['s'] = ss['sid_key']
				params['m'] = ss['mid_key']
				st.experimental_set_query_params(**params)
		def clear_query():
			st.experimental_set_query_params()

		# sidebar layout setup
		app_exp = st.sidebar.empty()
		sid_empty = st.sidebar.empty()
		mid_empty = st.sidebar.empty()
		nav_empty = st.sidebar.empty()
		# app_exp = st.sidebar.expander('page', expanded=False)
		filter_exp = st.sidebar.empty()

		# page selecter
		if ss.new_mid:
			ss['app_choice'] = 'match'
			app_choice = app_exp.radio("page", self.app_names,on_change=clear_query,key='app_choice')
			ss.new_mid = False
		else: # for empty nav_lists
			app_choice = app_exp.radio("page", self.app_names,on_change=clear_query,key='app_choice')
		nav_names = self.app_view[app_choice]
		# st_sidebar_title.title(app_choice)


		series_ids = ss.series[~(ss.series['series_id'].str.contains('upload'))]['series_id'].to_list()
		if query_sid_choice and 'upload' in query_sid_choice:
			init_series()
			init_matches()
			if len(ss.series[ss.series['series_id'] == query_sid_choice]) > 0:
				series_ids.append(query_sid_choice)
		series_ids.sort()
		series_ids.reverse()


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
					params = {'s':[query_sid_choice]}
					st.experimental_set_query_params(**params)
					ss[mid_key] = sid_mids[0]
			else:
				clear_query()
				ss[sid_key] = series_ids[0]

			def format_sid_str(sid):
				# sid_date = "20" + sid[0:2] + "/" + sid[2:4] + "/" + sid[4:6] + " "
				sid_date = sid.split("_")[0] + " · "
				sid_str = sid.split("_")[1:]
				sid_str = [render.team_name_map[s] if s in render.team_name_map else s for s in sid_str]
				return sid_date + " - ".join(sid_str)


			ss.sid = sid_empty.selectbox("series",series_ids,on_change=set_query,format_func=format_sid_str,help='series dates in YYMMDD format',key=sid_key)


			# match picker
			sid_matches = ss.matches[ss.matches['series_id'] == ss.sid] # update match list for SID only
			ss.sid_mids = sid_matches['match_id'].tolist()
			ss.sid_mids.sort()
			def format_mid_str(mid):
				row = sid_matches[sid_matches['match_id']==mid]
				mid_map = row.iloc[0]['map']
				return str(mid) + " (" + mid_map + ")"
			ss.mid = mid_empty.selectbox("matches",ss.sid_mids,format_func=format_mid_str,on_change=set_query,help='Match number from series in order played',key=mid_key) 

		if nav_names:
			page_view  = nav_empty.radio("navigation", nav_names ,on_change=set_query)
		else: 
			page_view = None

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

		with st.sidebar.expander('settings',expanded=False):
			def toggle_mobile():
				ss.mobile = not ss.mobile
			# st.checkbox('mobile view',key='mobile',help='this site is not designed with mobile in mind, but this toggle will make it viewable at least')

def view_match(title, info=None):
	match.main(con)

def view_records(title, info=None):
	players.main(con)

def view_upload(title, info=None):
	upload.main()

def view_info(title, info=None):
	view.info.main()

def main():
	mp = MultiPage()
	mp.add_app('match', ['summary','spikes','offence','defence','support','logs','series'] , view_match, info='')
	mp.add_app('records',['summary','stats'], view_records, info='')
	mp.add_app('upload',[], view_upload, info='')
	mp.add_app('info',[], view_info, info='')
	mp.run()

if __name__ == '__main__':
	render.init_css(1440)
	main()