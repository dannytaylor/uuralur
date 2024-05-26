import os,time, math, datetime, yaml, ast, statistics

import streamlit as st
ss = st.session_state # global shorthand for this file

import pandas as pd
import tools.util as util
import tools.render as render
from millify import millify

import plotly.graph_objects as go
import plotly.express as px

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode


config = yaml.safe_load(open('data/config.yaml'))

table_theme = config['table_theme']

def main(con):
	
	def get_hero_df():
		sqlq = util.str_sqlq('Heroes')
		hero_df = pd.read_sql_query(sqlq, con)
		hero_df = hero_df[~(hero_df['series_id'].str.contains('upload'))]
		hero_df['player']  = hero_df.apply(lambda x: x['hero'] if not x['player_name'] else x['player_name'], axis=1)
		hero_df['sid_mid'] = hero_df['series_id'] + "_" + hero_df['match_id'].astype(str)
		return hero_df

	hero_df = get_hero_df()

	table_height = 680 if not ss.mobile else 320

	
	st.caption('player summaries')
	
	# c2.markdown("""<p class="font20"" style="display:inline;color:#4d4d4d";>{}</p><p></p>""".format('overall stats'),True)
	c1,c2,c3,c4,c5 = st.columns([2,1,1,1,2])
	# c6 , 1 
	
	pname_empty = c1.empty()

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
	hero_gb.configure_default_column(width=32,cellStyle={'text-align': 'center'},suppressMovable=True)
	hero_gb.configure_columns('player',width=64,cellStyle={'text-align': 'left'})
	hero_gb.configure_columns(['win','loss','tie'],hide=True)
	hero_gb.configure_selection('single', pre_selected_rows=None)
	# hero_gb.configure_grid_options(headerHeight=10)

	# init layout for player_sel
	c11 = c2.empty()
	c12 = c3.empty()
	c13 = c4.empty()
	
	c21 = c2.empty()
	c22 = c3.empty()
	c23 = c4.empty()
	
	c31 = c2.empty()
	c32 = c3.empty()
	c33 = c4.empty()
	
	c41 = c2.empty()
	c42 = c3.empty()
	c43 = c4.empty()

	# at breakdown
	pset_fig_empty = c5.empty()
	path_options = ['archetype','set 1','set 2']

	# pset_path = c5.multiselect('sunburst chart order',path_options,default=path_options,help='defaults to AT>set1>set2 if none selected. "set 1" is the blast set for both corruptors and defenders')
	# if not pset_path:
	pset_path = path_options		

	# map pie
	# c6.write('')
	# map_fig_empty = c6.empty()
	

	c1.markdown("""<p><br></p>""",True) #pfp spacer
	pfp = c1.empty()
	match_linker = c5.empty() # c6.

	c1,c0,c2,c00,c3 = st.columns([2,0.1,3.5,0.1,2.3])

	player_sel = None
	hero_sel = None
	with c1:

		# st.markdown("""<p class="font20"" >{}</p>""".format('&nbsp players'),True)
		st.caption("@players")
			
		hero_ag = AgGrid(
			hero_write,
			allow_unsafe_jscode=True,
			custom_css=render.grid_css,
			gridOptions=hero_gb.build(),
			update_mode='SELECTION_CHANGED',
			fit_columns_on_grid_load= not ss.mobile,
			height = table_height,
			theme=table_theme,
			enable_enterprise_modules=False
		)

		row = hero_ag['selected_rows']
		if row:
			player_sel = row[0]['player']

	with c2:
		if player_sel:
			# st.markdown("""<p class="font20"" >{}</p>""".format('&nbsp heroes'),True)
			st.caption("heroes")
			ph_df = hero_df[hero_df['player']==player_sel].copy()

			# get latest at/set combo from dataframe
			p_heroes = ph_df.groupby('hero')[['archetype','set1','set2']].last()
			p_heroes = p_heroes.rename(columns={"match_id":'#'})
			p_heroes['#'] = ph_df.groupby('hero')[['match_id']].count()
			p_heroes['hero'] = p_heroes.index
			p_heroes = p_heroes[['hero','#','archetype','set1','set2']]
			p_heroes = p_heroes.sort_values(by='#',ascending=False)

			p_heroes['archetype'] = p_heroes['archetype'].map(lambda x: util.image_formatter("archetypes/"+x.replace('/','.')+'.png') if x else render.spacer_base64)
			# p_heroes['archetype'] = p_heroes['archetype'].apply(util.image_formatter)

			p_heroes_gb = GridOptionsBuilder.from_dataframe(p_heroes)
			p_heroes_gb.configure_selection('single', pre_selected_rows=None)
			p_heroes_gb.configure_default_column(filterable=False,width=64,suppressMovable=True)

			p_heroes_gb.configure_columns(['set1','set2'],width=44)
			p_heroes_gb.configure_columns('archetype',cellRenderer=render.icon,width=32)
			p_heroes_gb.configure_columns('#',width=32)

			# p_heroes_gb.configure_grid_options(headerHeight=0)

			p_hero_ag = AgGrid(
				p_heroes,
				allow_unsafe_jscode=True,
				custom_css=render.grid_css,
				gridOptions=p_heroes_gb.build(),
				fit_columns_on_grid_load= not ss.mobile,
				update_mode='SELECTION_CHANGED',
				height = table_height,
				theme=table_theme,
				enable_enterprise_modules=False
			)

			hrow = p_hero_ag['selected_rows']
			if hrow:
				hero_sel = hrow[0]['hero']

	if not player_sel:
		c2.markdown("""<div><br></div><div><br></div><div><br></div><div><br></div><div><br></div><div><br></div>""",True)
		c2.markdown("""<div style="margin:auto;width:50%;text-align:center;display:inline;color:#999";><p class="font20"" >{}</p></div>""".format('select a player to display <br>characters played.'),True)
		c3.markdown("""<div><br></div><div><br></div><div><br></div><div><br></div><div><br></div><div><br></div>""",True)
		c3.markdown("""<div style="margin:auto;width:50%;text-align:center;display:inline;color:#999";><p class="font20"" >{}</p></div>""".format('select a player to display filtered matches.'),True)

	with c3:
		matches = ss.matches.copy()
		if player_sel:
			# st.markdown("""<p class="font20"" >{}</p>""".format('&nbsp matches (YYMMDD)'),True)
			st.caption("matches (YYMMDD)")
			h_matches = hero_df[hero_df['player']==player_sel].copy()
			if hero_sel: h_matches = h_matches[h_matches['hero']==hero_sel]
			h_matches['sid_mid'] = h_matches['series_id'] + h_matches['match_id'].astype(str)
			matches['sid_mid'] = matches['series_id'] + matches['match_id'].astype(str)
			matches = matches[(matches['sid_mid'].isin(h_matches['sid_mid']))]
		matches = matches[['series_id','match_id','map']]
		matches = matches.sort_values(by='series_id',ascending=False)


		matches_gb = GridOptionsBuilder.from_dataframe(matches)
		matches_gb.configure_selection('single', pre_selected_rows=None)
		matches_gb.configure_default_column(width=12,suppressMovable=True)
		matches_gb.configure_columns(['map'],width=24)
		matches_gb.configure_columns(['series_id'],width=36)
		# matches_gb.configure_grid_options(headerHeight=0)
		if player_sel:
			matches_ag = AgGrid(
				matches,
				allow_unsafe_jscode=True,
				custom_css=render.grid_css,
				gridOptions=matches_gb.build(),
				update_mode='SELECTION_CHANGED',
				fit_columns_on_grid_load= not ss.mobile,
				height = table_height,
				theme=table_theme,
				enable_enterprise_modules=False
			)
			row = matches_ag['selected_rows']
		sid,mid = None,None
		if row:
			# spike ID == selected
			sid = row[0]['series_id']
			mid = row[0]['match_id']

		if player_sel:
			# with match_linker.form('match linker'):
			if sid and mid:
				def go_to_match():
					ss.view = {'match':'summary'}
					ss.sid = sid
					ss.mid = mid
					ss.new_mid = True

					ss['app_choice'] = 'players'

					params = {}
					params['s'] = sid
					params['m'] = mid
					st.query_params.from_dict(params)
				match_linker.button(label="go to match {} - {}".format(sid,mid), on_click=go_to_match,use_container_width=True)
			else:
				match_linker.button(label="select a match below",disabled=True,use_container_width=True)

	# player profile pic
	pfp_path = os.path.abspath('assets/players')
	if player_sel:
		pfp_files = [i for i in os.listdir(pfp_path)]
		pfp_players = [i.split('.')[0] for i in pfp_files]
		
		pname_empty.markdown("""<p class="font20""  style="display:inline;color:#4d4d4d";>{}</p>""".format(player_sel),True)
		if player_sel in pfp_players:
			image_path = pfp_path+'/'+[p for p in pfp_files if player_sel in p][0]
			# img = util.resize_image(pfp_path+'/'+image_path)
			pfp.image(util.resize_image(image_path,260)) 
		else:
			pfp.image(pfp_path + '/null.png') 
	else:
		pfp.image(pfp_path + '/null.png') 


	pset_hero_df = hero_df.copy()
	if player_sel:
		pset_hero_df = pset_hero_df[pset_hero_df['player'] == player_sel]
	map_fig = go.Figure()
	map_matches = ss.matches.copy()
	map_data = ss.matches.groupby('map')[['match_id']].count().copy()
	map_data = map_data.sort_values(by=['match_id'])
	cs_algae = ['rgb(214, 249, 235)','rgb(214, 249, 222)', 'rgb(214, 249, 207)', 'rgb(186, 228, 174)', 'rgb(156, 209, 143)', 'rgb(124, 191, 115)', 'rgb(85, 174, 91)', 'rgb(37, 157, 81)', 'rgb(7, 138, 78)', 'rgb(13, 117, 71)', 'rgb(23, 95, 61)', 'rgb(25, 75, 49)', 'rgb(23, 55, 35)', 'rgb(17, 36, 20)']
	map_fig.add_trace(go.Pie(
			labels=map_data.index,
			values=map_data['match_id'],
			hole=0.2,
			marker_colors = cs_algae,
		))
	map_fig.update_layout(
		showlegend=False,
		height=240,
		margin={'t': 0,'b':44,'l':0,'r':0},
	)


	@st.cache_resource(show_spinner=False,ttl=30)
	def get_player_data(player_sel):
		# sunburst data
		pset_hero_df['set 1'] = pset_hero_df['set1'].astype(str)
		pset_hero_df['set 2'] = pset_hero_df['set2'].astype(str)
		pset_hero_df['archetype'] = pset_hero_df['archetype'].astype(str)
		pset_hero_df['total'] = ''

		pset_fig = px.sunburst(
				pset_hero_df,
				path=pset_path,
			)
		pset_fig.update_layout(
			margin = dict(t=0, l=0, r=0, b=0),
			height=260)

		metrics = {}
		
		metrics[11] = len(pset_hero_df.groupby(['series_id']))
		if player_sel:
			metrics[12] = len(pset_hero_df)
			metrics[13] = 1
		else:
			metrics[12] = len(ss.matches)
			metrics[13] = len(hero_write)
		metrics[21] = len(pset_hero_df.groupby('hero')[['match_id']].count())
		metrics[22] = millify(pset_hero_df['deaths'].sum(),precision=1)
		metrics[23] = millify(pset_hero_df['targets'].sum(),precision=1)

		metrics[31] = millify(pset_hero_df['damage_taken'].sum(),precision=1)
		metrics[32] = millify(pset_hero_df['attacks'].sum(),precision=1)
		metrics[33] = millify(pset_hero_df['heals'].sum(),precision=1)
		
		metrics[41] = millify(pset_hero_df['greens'].sum(),precision=1)
		metrics[42] = millify(pset_hero_df['phases'].sum(),precision=1)
		metrics[43] = millify(pset_hero_df['jaunts'].sum(),precision=1)

		return metrics, pset_fig


	metrics,pset_fig = get_player_data(player_sel)

	c11.metric('# series',metrics[11])
	c12.metric('matches played',metrics[12])
	c13.metric('players recorded',metrics[13])
	
	c21.metric('unique heroes',metrics[21])
	c22.metric('tot deaths',metrics[22])
	c23.metric('tot spikes',metrics[23])
	
	c31.metric('tot damage',metrics[31])
	c32.metric('attacks thown',metrics[32])
	c33.metric('heals cast',metrics[33])
	
	c41.metric('greens popped',metrics[41])
	c42.metric('# phases',metrics[42])
	c43.metric('# jaunts',metrics[43])

	pset_fig_empty.plotly_chart(pset_fig,use_container_width=True,config={'displayModeBar': False})
	# if not ss.mobile:
	# 	map_fig_empty.plotly_chart(map_fig,use_container_width=True,config={'displayModeBar': False})