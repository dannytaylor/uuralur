import os,time, math, json, datetime, yaml, ast, statistics

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


@st.cache
def init_filter_lists(mh_df):
	at_list = mh_df['archetype'].unique().tolist()
	pset_list = pd.unique(mh_df[['set1', 'set2']].values.ravel('K')).tolist()
	hero_list = mh_df['hero'].unique().tolist()
	pset_list.remove(None)
	at_list.sort()
	pset_list.sort()
	hero_list.sort()

	team_list = list(render.team_name_map.keys())
	team_list.remove('kb')
	team_list.sort()

	dates = ss.series[~(ss.series['series_id'].str.contains('upload'))]['date'].tolist()

	nspike_dict = {}
	nspike_dict[0] = dict(zip(ss.matches['sid_mid'],ss.matches['spikes0']))
	nspike_dict[1] = dict(zip(ss.matches['sid_mid'],ss.matches['spikes1']))


	return at_list,pset_list,hero_list,team_list,dates,nspike_dict

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

	if ss.view['records'] == 'stats':

		c1,c2 = st.empty(),st.empty() # clear graphs rendering when switching views

		# get hero data for all matches
		mh_df = hero_df.copy()

		# set ats and psets for filters
		at_list,pset_list,hero_list,team_list,dates,nspike_dict = init_filter_lists(mh_df)

		# data filters
		with st.sidebar.form('filters'):
			st.write('data filters')
			data_aggr   = st.radio('show data by',['overall','average per match'],help='applies applicable data')
			with st.expander('hero filters',expanded=False):
				support_toggle = st.radio('role',['all','offence','support'],help='if set to all only calculates otp for offence matches and ohp for support matches')
				at_filter   = st.multiselect('archetypes', at_list, default=None,help='all if none selected')
				pset_filter = st.multiselect('powersets',  pset_list, default=None, help='all if none selected')
				hero_filter = st.multiselect('hero name',  hero_list, default=None, help='all if none selected')
			with st.expander('match filters',expanded=False):
				match_type  = st.radio('match type',['all','scrim','kb'],help="any kickball/community series is kb, any non-kb is a 'scrim'")
				win_filter  = st.radio('win/loss',['all','win','loss'],help='losses includes ties for this filter')
				def team_name_map(team):
					if team in render.team_name_map:
						return render.team_name_map[team]
					else:
						return team
				team_filter   = st.multiselect('team name',team_list,format_func=team_name_map, default=None, help='all if none selected')
				series_filters = {}
				# series_filters['date_first'] = st.date_input('start date filter',value=dates[0],min_value=dates[0],max_value=dates[-1])
				# series_filters['date_last']  = st.date_input('end date filter', value=dates[-1],min_value=series_filters['date_first'] ,max_value=dates[-1])
				series_filters['date_first'] = st.select_slider('date filters',options=dates,value=dates[0])
				series_filters['date_last']  = st.select_slider('', options=dates,value=dates[-1])
				date_filtered = ss.series[(ss.series['date'] >= series_filters['date_first']) & (ss.series['date'] <= series_filters['date_last'])]['series_id'].tolist()
			

			st.form_submit_button(label="apply filters", help=None, on_click=None, args=None, kwargs=None)


		available_data = ['deaths','targets','surv','damage_taken','attacks','heals']
		default_sel = ['deaths','targets','surv','otp','on heal%','damage_taken','attacks']
		target_data = ['otp','on heal%','on_target','on_heal']
		timing_data = ['attack mean','attack median','attack variance','heal mean','heal median','heal variance','phase mean','phase median','jaunt mean','jaunt median']
		count_data  = ['first_attacks','alpha_heals','phases','jaunts','greens']
		dmg_data    = ['dmg/spike (est)']
		record_data = ['win','loss','tie']
		available_data += target_data + timing_data + count_data + dmg_data + record_data

		with st.form('data selection'):
			show_data = st.multiselect('show columns (filters in sidebar)',available_data,default=default_sel)
			st.form_submit_button('get data')

		# toggles for viewing data by
		table_title = 'players'
		mh_df['player'] = mh_df['player_name']

		# initial toggle filters
		if support_toggle == 'support':
			mh_df = mh_df[mh_df['support']==1]
		elif support_toggle == 'offence':
			mh_df = mh_df[~(mh_df['support']==1)]

		# match type filters 
		if match_type != 'all':
			if match_type == 'kb':
				mh_df = mh_df[mh_df['series_id'].str.contains('_kb')|mh_df['series_id'].str.contains('_taco')]
			else:
				mh_df = mh_df[~(mh_df['series_id'].str.contains('_kb')|mh_df['series_id'].str.contains('_taco'))]
		if win_filter != 'all':
			if win_filter == 'win':
				mh_df = mh_df[mh_df['win'] == 1]
			else:
				mh_df = mh_df[mh_df['loss'] == 1]

		# date filters
		mh_df = mh_df[mh_df['series_id'].isin(date_filtered)]

		# hero filters
		if at_filter:
			mh_df = mh_df[mh_df['archetype'].isin(at_filter)]
		if pset_filter:
			mh_df = mh_df[(mh_df['set1'].isin(pset_filter))|(mh_df['set2'].isin(pset_filter))]
		if hero_filter:
			mh_df = mh_df[mh_df['hero'].isin(hero_filter)]
		if team_filter:
			base = r'^{}'
			expr = '(?=.*{})'
			mh_df = mh_df[mh_df['series_id'].str.contains(''.join(expr.format(t) for t in team_filter))]


		try:
			with st.spinner('calculating data...'):
				# setup player table
				mh_write = mh_df.groupby('player')[['match_id']].count().copy()
				mh_write['player'] = mh_write.index
				mh_write['#matches'] = mh_df.groupby('player')[['match_id']].count()
				if len(mh_write) == 0:
					st.write('no data for these filters')
					pass
				else:
					# str lists to lists
					mh_df['attack_timing']= mh_df.apply(lambda x: (ast.literal_eval(x['attack_timing']) if (x['support'] != 1 or support_toggle != 'all') else []), axis=1)
					mh_df['heal_timing']  = mh_df.apply(lambda x: (ast.literal_eval(x['heal_timing'])   if (x['support'] == 1 or support_toggle != 'all') else []), axis=1)
					mh_df['phase_timing'] = mh_df['phase_timing'].map(lambda x: (ast.literal_eval(x)))
					mh_df['jaunt_timing'] = mh_df['jaunt_timing'].map(lambda x: (ast.literal_eval(x)))

					# on targets
					mh_df['on_target'] = mh_df['attack_timing'].map(lambda x: len(x) - sum(config['otp_penalty'] for t in x if t > config['otp_threshold']))
					mh_df['on_heal'] = mh_df['heal_timing'].map(lambda     x: len(x) - sum(config['ohp_penalty'] for t in x if t > config['ohp_threshold'])) 
					mh_df['on_target_possible'] = mh_df.apply(lambda x: nspike_dict[x['team']][x['sid_mid']] if (x['support'] != 1 or support_toggle != 'all') else 0, axis=1)
					mh_df['on_heal_possible']   = mh_df.apply(lambda x: nspike_dict[abs(1-x['team'])][x['sid_mid']]-x['targets'] if (x['support'] == 1 or support_toggle != 'all') else 0, axis=1)

					# group by player
					mh_write['attack_timing']= mh_df.groupby('player').agg({'attack_timing': 'sum'})
					mh_write['heal_timing']  = mh_df.groupby('player').agg({'heal_timing': 'sum'})
					mh_write['phase_timing'] = mh_df.groupby('player').agg({'phase_timing': 'sum'})
					mh_write['jaunt_timing'] = mh_df.groupby('player').agg({'jaunt_timing': 'sum'})

					# convert ms to s
					mh_write['attack_timing']= mh_write['attack_timing'].map(lambda x: [a/1000 for a in x])
					mh_write['phase_timing'] = mh_write['phase_timing'].map(lambda x: [a/1000 for a in x])
					mh_write['jaunt_timing'] = mh_write['jaunt_timing'].map(lambda x: [a/1000 for a in x])
					mh_write['heal_timing']   = mh_write['heal_timing'].map(lambda x: [a/1000 for a in x])

					# calc mean,median,vars
					# mh_write['attack mean']     = mh_write['attack_timing'].map(lambda x: statistics.mean([abs(v) for v in x]) if len(x) > 0 else None)
					mh_write['attack mean']     = mh_write['attack_timing'].map(lambda x: statistics.mean(x) if len(x) > 0 else None)
					mh_write['attack median']   = mh_write['attack_timing'].map(lambda x: statistics.median(x) if len(x) > 0 else None)
					mh_write['attack variance'] = mh_write['attack_timing'].map(lambda x:  statistics.variance(x)  if len(x) > 1 else None)

					mh_write['phase mean']   = mh_write['phase_timing'].map(lambda x: statistics.mean(x) if len(x) > 0 else None)
					mh_write['phase median'] = mh_write['phase_timing'].map(lambda x: statistics.median(x) if len(x) > 0 else None)
					mh_write['jaunt mean']   = mh_write['jaunt_timing'].map(lambda x: statistics.mean(x) if len(x) > 0 else None)
					mh_write['jaunt median'] = mh_write['jaunt_timing'].map(lambda x: statistics.median(x) if len(x) > 0 else None)

					mh_write['heal mean']     = mh_write['heal_timing'].map(lambda x: statistics.mean(x) if len(x) > 0 else None)
					mh_write['heal median']   = mh_write['heal_timing'].map(lambda x: statistics.median(x) if len(x) > 0 else None)
					mh_write['heal variance'] = mh_write['heal_timing'].map(lambda x: statistics.variance(x) if len(x) > 1 else None)

					# otps	
					otp_cols = ['on_target','on_heal','on_target_possible','on_heal_possible']
					mh_write[otp_cols] = mh_df.groupby('player')[otp_cols].sum()
					mh_write['otp'] = mh_write['on_target']/mh_write['on_target_possible']
					mh_write['on heal%'] = mh_write['on_heal']/mh_write['on_heal_possible']

					mh_write['otp']      = mh_write['otp'].map("{:.1%}".format).map(lambda x: '' if (x == '0%' or x == 'nan%' or x == 'inf%') else x)
					mh_write['otp']      = mh_write['otp'].map(lambda x: " "+x if len(x) == 4 else x)
					mh_write['on heal%'] = mh_write['on heal%'].map("{:.1%}".format).map(lambda x: '' if (x == '0%' or x == 'nan%' or x == 'inf%') else x)
					mh_write['on heal%'] = mh_write['on heal%'].map(lambda x: " "+x if len(x) == 4 else x)


					# get data by mean or total
					sum_or_avg = ['deaths','targets','damage_taken','attacks','heals','on_target','on_heal']
					sum_or_avg += count_data + record_data
					if data_aggr == 'average per match':
						mh_write[sum_or_avg] = mh_df.groupby('player')[sum_or_avg].mean()
					else:
						mh_write[sum_or_avg] = mh_df.groupby('player')[sum_or_avg].sum()

					mh_write['dmg/spike (est)'] = 0.8*mh_write['damage_taken']/mh_write['targets']
					mh_write['damage_taken'] = mh_write['damage_taken'].map(lambda x: millify(x,precision=1))
					
					# calc overall stats
					mh_write['surv'] = 1-mh_write['deaths']/mh_write['targets'] 
					mh_write['surv'] = mh_write['surv'].map("{:.0%}".format)
					mh_write['surv'] = mh_write['surv'].map(lambda x: '' if x == 'nan%' else x)

					mh_write = mh_write.fillna('')

					mh_write = mh_write[['player','#matches']+available_data].sort_values(by='#matches',ascending=False)
					hide_data = [d for d in available_data if d not in show_data]
					# mh_write = mh_df[['player','#matches','deaths','targets','surv','dmg','otp','avg t']]
				
					mh_gb = GridOptionsBuilder.from_dataframe(mh_write)
					mh_gb.configure_default_column(width=32,cellStyle={'text-align': 'center'},suppressMovable=True)
					mh_gb.configure_columns('player',width=64,cellStyle={'text-align': 'left'},pinned='left')
					mh_gb.configure_columns(['attacks','heals','on_target','on_heal'],type='customNumericFormat',precision=0)
					mh_gb.configure_columns(timing_data,type='customNumericFormat',precision=3)
					if data_aggr == 'average per match':
						mh_gb.configure_columns(['deaths','targets']+count_data+dmg_data,type='customNumericFormat',precision=1)
						mh_gb.configure_columns(record_data,type='customNumericFormat',precision=3)
					else:
						mh_gb.configure_columns(['deaths','targets']+count_data+dmg_data+record_data,type='customNumericFormat',precision=0)

					mh_gb.configure_columns(hide_data,hide=True)
					mh_gb.configure_selection('single', pre_selected_rows=None)

					# st.markdown("""<p class="font20"" style="display:inline;color:#4d4d4d";>{}</p><br>""".format(table_title),True)
					mh_ag = AgGrid(
						mh_write,
						allow_unsafe_jscode=True,
						gridOptions=mh_gb.build(),
						# update_mode='SELECTION_CHANGED',
						# fit_columns_on_grid_load= not ss.mobile,
						height = 800 if not ss.mobile else 320,
						theme=table_theme
					)
		except:
			st.write('no data for these filters')

	elif ss.view['records'] == 'summary':
		c1,c2 = st.columns([2,8])
		pname_empty = c1.empty()
		c2.markdown("""<p class="font20"" style="display:inline;color:{}";>{}</p><p></p>""".format(config['header_color'],'overall stats'),True)
		c1,c2,c3,c4,c5,c6 = st.columns([2,1,1,1,3,2])


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
		pset_path = c5.multiselect('sunburst chart order',path_options,default=path_options,help='defaults to AT>set1>set2 if none selected. "set 1" is the blast set for both corruptors and defenders')
		if not pset_path:
			pset_path = path_options		

		# map pie
		c6.write('')
		map_fig_empty = c6.empty()
		

		c1.markdown("""<p><br></p>""",True) #pfp spacer
		pfp = c1.empty()
		match_linker = c6.empty()
	
		c1,c0,c2,c00,c3 = st.columns([2,0.25,5,0.25,2.5])

		player_sel = None
		hero_sel = None
		with c1:

			st.markdown("""<p class="font20"" >{}</p>""".format('&nbsp players'),True)
				
			hero_ag = AgGrid(
				hero_write,
				allow_unsafe_jscode=True,
				gridOptions=hero_gb.build(),
				update_mode='SELECTION_CHANGED',
				fit_columns_on_grid_load= not ss.mobile,
				height = table_height,
				theme=table_theme
			)

			row = hero_ag['selected_rows']
			if row:
				player_sel = row[0]['player']

		with c2:
			if player_sel:
				st.markdown("""<p class="font20"" >{}</p>""".format('&nbsp heroes'),True)
				ph_df = hero_df[hero_df['player']==player_sel].copy()

				# get latest at/set combo from dataframe
				p_heroes = ph_df.groupby('hero')[['archetype','set1','set2']].last()
				p_heroes = p_heroes.rename(columns={"match_id":'#'})
				p_heroes['#'] = ph_df.groupby('hero')[['match_id']].count()
				p_heroes['hero'] = p_heroes.index
				p_heroes = p_heroes[['hero','#','archetype','set1','set2']]
				p_heroes = p_heroes.sort_values(by='#',ascending=False)

				p_heroes['archetype'] = p_heroes['archetype'].map(lambda x: "archetypes/"+x.replace('/','.')+'.png')
				p_heroes['archetype'] = p_heroes['archetype'].apply(util.image_formatter)

				p_heroes_gb = GridOptionsBuilder.from_dataframe(p_heroes)
				p_heroes_gb.configure_selection('single', pre_selected_rows=None)
				p_heroes_gb.configure_default_column(filterable=False,width=64,suppressMovable=True)

				p_heroes_gb.configure_columns('archetype',cellRenderer=render.icon,width=32)
				p_heroes_gb.configure_columns('#',width=32)

				# p_heroes_gb.configure_grid_options(headerHeight=0)

				p_hero_ag = AgGrid(
					p_heroes,
					allow_unsafe_jscode=True,
					gridOptions=p_heroes_gb.build(),
					fit_columns_on_grid_load= not ss.mobile,
					update_mode='SELECTION_CHANGED',
					height = table_height,
					theme=table_theme
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
				st.markdown("""<p class="font20"" >{}</p>""".format('&nbsp matches'),True)
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
					gridOptions=matches_gb.build(),
					update_mode='SELECTION_CHANGED',
					fit_columns_on_grid_load= not ss.mobile,
					height = table_height,
					theme=table_theme
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

						params = st.experimental_get_query_params()
						params['s'] = sid
						params['m'] = mid
						st.experimental_set_query_params(**params)
					match_linker.button(label="go to match {} - {}".format(sid,mid), on_click=go_to_match)
				else:
					match_linker.button(label="select a match below")

		# player profile pic
		pfp_path = os.path.abspath('assets/players')
		if player_sel:
			pfp_files = [i for i in os.listdir(pfp_path)]
			pfp_players = [i.split('.')[0] for i in pfp_files]
			
			pname_empty.markdown("""<p class="font20""  style="display:inline;color:#4d4d4d";>{}</p>""".format(player_sel),True)
			if player_sel in pfp_players:
				image_path = pfp_path+'/'+[p for p in pfp_files if player_sel in p][0]
				# img = util.resize_image(pfp_path+'/'+image_path)
				pfp.image(util.resize_image(image_path,200)) 
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


		@st.cache(show_spinner=False,ttl=30)
		def get_player_data(player_sel):
			# sunburst data
			pset_hero_df['set 1'] = pset_hero_df['set1'].astype(str)
			pset_hero_df['set 2'] = pset_hero_df['set2'].astype(str)
			pset_hero_df['total'] = ''

			pset_fig = px.sunburst(
					pset_hero_df,
					path=pset_path,
				)
			pset_fig.update_layout(
				margin = dict(t=0, l=0, r=0, b=0),
				height=220)

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
		if not ss.mobile:
			map_fig_empty.plotly_chart(map_fig,use_container_width=True,config={'displayModeBar': False})






