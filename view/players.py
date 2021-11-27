import time, math, json, datetime, yaml, ast, statistics

import streamlit as st
ss = st.session_state # global shorthand for this file

import pandas as pd
import tools.util as util
import tools.render as render

import plotly.graph_objects as go

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
config = yaml.safe_load(open('data/config.yaml'))

table_theme = config['table_theme']



def main(con):
	sqlq = util.str_sqlq('Heroes')
	hero_df = pd.read_sql_query(sqlq, con)

	hero_df['player'] = hero_df.apply(lambda x: x['hero'] if not x['player_name'] else x['player_name'], axis=1)


	if ss.view['players'] == 'stats':
		with st.sidebar.expander('player filters',expanded = True):
			st.radio('role',['all','offence','support'],help='calculates otp and ohp values per role')
			st.radio('match type',['all','scim','kb'])
			st.radio('win/loss',['all','win','loss'],help='losses includes ties for filtering')
			st.multiselect('archetypes',['blaster','def'])
			st.multiselect('powersets',['etc','etc.'])
		c1,c2,c3,c4,c5,c6 = st.columns([1,1,1,1,2,2])

	elif ss.view['players'] == 'records':

		c1,c2,c3,c4,c5,c6 = st.columns([1,1,1,1,2,2])

		# st.write(hero_df)

		hero_write = hero_df.groupby('player')[['match_id']].count().copy()
		hero_write['player'] = hero_write.index
		hero_write['#matches'] = hero_write['match_id']
		hero_write['win']  = hero_df.groupby('player')[['win']].sum().copy()
		hero_write['loss'] = hero_df.groupby('player')[['loss']].sum().copy()
		hero_write['tie']  = hero_df.groupby('player')[['tie']].sum().copy()
		hero_write = hero_write.sort_values(by=['#matches'],ascending=False)

		hero_write = hero_write[['player','#matches','win','loss','tie']]

		hero_gb = GridOptionsBuilder.from_dataframe(hero_write)
		hero_gb.configure_default_column(width=32,cellStyle={'text-align': 'center'})
		hero_gb.configure_columns('player',width=64,cellStyle={'text-align': 'left'})
		hero_gb.configure_selection('single', pre_selected_rows=None)

		c1.metric('# series',len(ss.series))
		c2.metric('matches played',len(ss.matches))
		c3.metric('players recorded',len(hero_write))
		c4.metric('unique heroes',len(hero_df.groupby('hero')[['match_id']].count()))

		c1.metric('tot deaths (k)',round(hero_df['deaths'].sum()/1000,1))
		c2.metric('tot spikes (k)',round(hero_df['targets'].sum()/1000,1))
		c3.metric('tot damage (mil)',round(hero_df['damage_taken'].sum()/1000000,1))
		c4.metric('attacks thown (mil)',round(hero_df['attacks'].sum()/1000000,1))

		c1.metric('heals cast (k)',round(hero_df['heals'].sum()/1000,1))
		c2.metric('greens popped (k)',round(hero_df['greens'].sum()/1000,1))
		c3.metric('# phases (k)',round(hero_df['phases'].sum()/1000,1))
		c4.metric('# jaunts (k)',round(hero_df['jaunts'].sum()/1000,1))

		map_fig = go.Figure()
		map_data = ss.matches.groupby('map')[['match_id']].count().copy()
		map_data = map_data.sort_values(by=['match_id'])
		cs_algae = ['rgb(214, 249, 235)','rgb(214, 249, 222)', 'rgb(214, 249, 207)', 'rgb(186, 228, 174)', 'rgb(156, 209, 143)', 'rgb(124, 191, 115)', 'rgb(85, 174, 91)', 'rgb(37, 157, 81)', 'rgb(7, 138, 78)', 'rgb(13, 117, 71)', 'rgb(23, 95, 61)', 'rgb(25, 75, 49)', 'rgb(23, 55, 35)', 'rgb(17, 36, 20)']
		map_fig.add_trace(go.Pie(
				labels=map_data.index,
				values=map_data['match_id'],
				name='',
				hole=0.2,
				marker_colors = cs_algae,
			))
		map_fig.update_layout(
			showlegend=False,
			height=240,
			margin={'t': 16,'b':0,'l':0,'r':0},
		)
		c5.plotly_chart(map_fig,use_container_width=True,config={'displayModeBar': False})

		match_linker = c6.empty()

		c1,c2,c3 = st.columns([4,3,3])
		player_sel = None
		hero_sel = None
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
			if player_sel:
				p_heroes = hero_df[hero_df['player']==player_sel].copy()
				p_heroes = p_heroes.groupby('hero')[['match_id']].count()
				p_heroes['hero'] = p_heroes.index
				p_heroes = p_heroes.rename(columns={"match_id":'#'})

				p_heroes = p_heroes.sort_values(by='#',ascending=False)
				p_heroes_gb = GridOptionsBuilder.from_dataframe(p_heroes)
				p_heroes_gb.configure_selection('single', pre_selected_rows=None)
				p_heroes_gb.configure_default_column(filterable=False,width=64)
				p_heroes_gb.configure_columns('#',width=32)
				p_hero_ag = AgGrid(
					p_heroes,
					gridOptions=p_heroes_gb.build(),
					fit_columns_on_grid_load=True,
					update_mode='SELECTION_CHANGED',
					height = 800,
					theme=table_theme
				)

				hrow = p_hero_ag['selected_rows']
				if hrow:
					hero_sel = hrow[0]['hero']

			if not player_sel:
				st.write('')
				st.write('select player to list heroes played')

		with c3:
			matches = ss.matches.copy()
			if player_sel:
				h_matches = hero_df[hero_df['player']==player_sel].copy()
				if hero_sel: h_matches = h_matches[h_matches['hero']==hero_sel]
				h_matches['sid_mid'] = h_matches['series_id'] + h_matches['match_id'].astype(str)
				matches['sid_mid'] = matches['series_id'] + matches['match_id'].astype(str)
				matches = matches[(matches['sid_mid'].isin(h_matches['sid_mid']))]
			matches = matches[['series_id','match_id','map']]
			matches = matches.iloc[::-1]


			matches_gb = GridOptionsBuilder.from_dataframe(matches)
			matches_gb.configure_selection('single', pre_selected_rows=None)
			matches_gb.configure_default_column(width=12)
			matches_gb.configure_columns(['map'],width=24)
			matches_gb.configure_columns(['series_id'],width=36)
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

			with match_linker.form('match linker'):
				if sid and mid:
					st.write()
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

					st.form_submit_button(label="go to {} - {}".format(sid,mid), on_click=go_to_match)
				else:
					st.form_submit_button(label="select a player from the left to list played matches below")


