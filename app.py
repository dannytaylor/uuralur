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
	ss.matches 			= pd.read_sql_query("SELECT * FROM Matches", con)

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

	def add_app(self, title, func, *args, **kwargs):
		self.app_names.append(title)
		self.apps.append({
			"title": title,
			"function": func,
			"args":args,
			"kwargs": kwargs
		})

	def sidebar(self):
		# common key
		key='viewer'

		# get app choice from query_params
		query_params = st.experimental_get_query_params()
		query_app_choice = query_params['app'][0] if 'app' in query_params else None

		# update session state (this also sets the default radio button selection as it shares the key!)
		ss[key] = query_app_choice if query_app_choice in self.app_names else self.app_names[0]

		def on_change():
			params = st.experimental_get_query_params()
			params['app'] = ss[key]
			st.experimental_set_query_params(**params)

		app_choice = st.sidebar.radio("viewer", self.app_names, on_change=on_change, key=key)
		return app_choice

	def run(self):
		# callback to update query param from app choice
		viewer = self.sidebar()

		# run the selected app
		app = self.apps[self.app_names.index(viewer)]
		app['function'](app['title'], *app['args'], **app['kwargs'])

def app1(title, info=None):
	ss.mid = 1
	ss.sid = '211109_kb'
	ss.view = {'match':'summary'}

	match.main(con)

def app2(title, info=None):
	st.title(title)
	st.write(info)

	# player.main(con)


def main():
	mp = MultiPage()
	mp.add_app('Application 1', app1, info='Hello from App 1')
	mp.add_app('Application 2', app2, info='Hello from App 2')
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