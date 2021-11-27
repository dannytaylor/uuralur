import os, sys, time, math, argparse, json, datetime, yaml, sqlite3, ast, statistics

import streamlit as st
ss = st.session_state # global shorthand for this file

import pandas as pd
import numpy as np
import tools.util as util
import tools.render as render

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
config = yaml.safe_load(open('data/config.yaml'))
powers = json.loads(open('data/powers.json').read())

table_theme = config['table_theme']



def main(con):
	sqlq = util.str_sqlq('Heroes')
	hero_df = pd.read_sql_query(sqlq, con)
	hero_df = hero_df.sort_values(by='team')


	if ss.view['players'] == 'matches':
		c1,c2 = st.columns(2)
		
		with st.sidebar.expander('player filters',expanded = True):
			st.write('hi')
		# st.write(hero_df)

		hero_write = hero_df.groupby('player_name')[['match_id']].count().copy()
		hero_write['player'] = hero_write.index
		hero_write['#matches'] = hero_write['match_id']
		hero_write = hero_write.sort_values(by=['#matches'],ascending=False)

		hero_write = hero_write[['player','#matches']]

		hero_gb = GridOptionsBuilder.from_dataframe(hero_write)
		hero_gb.configure_default_column(width=32,cellStyle={'text-align': 'center'},filterable=False)
		hero_gb.configure_columns('player',width=64,cellStyle={'text-align': 'left'})
		hero_gb.configure_selection('single', pre_selected_rows=None)

		player_sel = None
		with c1:
			hero_ag = AgGrid(
				hero_write,
				allow_unsafe_jscode=True,
				gridOptions=hero_gb.build(),
				update_mode='SELECTION_CHANGED',
				fit_columns_on_grid_load=True,
				height = 800,
				theme=table_theme
			)

			row = hero_ag['selected_rows']
			if row:
				player_sel = row[0]['player']

		with c2:
			matches = ss.matches.copy()
			if player_sel:
				h_matches = hero_df[hero_df['player_name']==player_sel]			
				matches = matches[(matches['series_id'].isin(h_matches['series_id']))&(matches['match_id'].isin(h_matches['match_id']))]
			matches = matches[['series_id','match_id','map']]

			match_linker = st.empty()

			matches_gb = GridOptionsBuilder.from_dataframe(matches)
			matches_gb.configure_selection('single', pre_selected_rows=None)
			matches_gb.configure_default_column(filterable=False)
			matches_ag = AgGrid(
				matches,
				allow_unsafe_jscode=True,
				gridOptions=matches_gb.build(),
				update_mode='SELECTION_CHANGED',
				fit_columns_on_grid_load=True,
				height = 800,
				theme=table_theme
			)
			row = matches_ag['selected_rows']
			sid,mid = None,None
			if row:
				# spike ID == selected
				sid = row[0]['series_id']
				mid = row[0]['match_id']

			if sid and mid:
				with match_linker.form('match linker'):
					st.write('selected: {} - #{}'.format(sid,mid))
					def go_to_match():
						ss.view = {'match':'summary'}
						ss.sid = sid
						ss.mid = mid
						ss.new_mid = True

						ss['app_choice'] = 'players'

						params = st.experimental_get_query_params()
						params['s'] = sid
						params['m'] = mid
						st.experimental_set_query_params(**params)

					st.form_submit_button(label="go to match", help='view match data', on_click=go_to_match)


