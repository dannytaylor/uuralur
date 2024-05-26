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


@st.cache_resource
def init_filter_lists(mh_df):
	at_list = mh_df['archetype'].unique().tolist()
	if None in at_list: at_list.remove(None)
	pset_list = pd.unique(mh_df[['set1', 'set2']].values.ravel('K')).tolist()
	hero_list = mh_df['hero'].unique().tolist()
	pset_list.remove(None)
	at_list.sort()
	pset_list.sort()
	hero_list.sort()	

	team_list = set(render.team_name_map.keys())
	team_list = list(team_list.difference(render.kb_tags))
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



	c1,c2 = st.empty(),st.empty() # clear graphs rendering when switching views

	# get hero data for all matches
	mh_df = hero_df.copy()

	# set ats and psets for filters
	at_list,pset_list,hero_list,team_list,dates,nspike_dict = init_filter_lists(mh_df)

	# data filters
	with st.sidebar.form('filters'):
		st.write('select data')
		with st.expander('data filters',expanded=False):
			data_aggr   = st.radio('show data by',['avg/match','overall',],help='applies applicable data',horizontal=True)
			data_filter = st.empty()

		with st.expander('match filters',expanded=False):
			match_type  = st.radio('match type',['all','scrim','pug'],help="any kickball/taco/community/pug series is a 'pug', any non-pug is a 'scrim'",horizontal=True)
			win_filter  = st.radio('win/loss',['all','win','loss'],help='losses includes ties',horizontal=True)
			def team_name_map(team):
				if team in render.team_name_map:
					return render.team_name_map[team]
				else:
					return team
			series_filters = {}
			# series_filters['date_first'] = st.date_input('start date filter',value=dates[0],min_value=dates[0],max_value=dates[-1])
			# series_filters['date_last']  = st.date_input('end date filter', value=dates[-1],min_value=series_filters['date_first'] ,max_value=dates[-1])
			series_filters['date_first'],series_filters['date_last'] = st.select_slider('date filters',options=dates,value=(dates[0],dates[-1]))
			# series_filters['date_last']  = st.select_slider('', options=dates,value=dates[-1])
			date_filtered = ss.series[(ss.series['date'] >= series_filters['date_first']) & (ss.series['date'] <= series_filters['date_last'])]['series_id'].tolist()
			team_filter   = st.multiselect('teams',team_list,format_func=team_name_map, default=None, help='all if none selected')
		
		with st.expander('hero filters',expanded=False):
			support_toggle = st.radio('role',['all','offence','support'],help='if set to all only calculates otp for offence matches and ohp for support matches',horizontal=True)
			at_filter   = st.multiselect('archetypes', at_list, default=None,help='all if none selected')
			pset_filter = st.multiselect('powersets',  pset_list, default=None, help='all if none selected')
			hero_filter = st.multiselect('hero name',  hero_list, default=None, help='all if none selected')

		init_filters = st.form_submit_button(label="apply filters", help=None, on_click=None, args=None, kwargs=None,use_container_width=True)


	available_data = ['deaths','targets','surv','damage_taken','attacks','heals']
	default_sel = ['deaths','targets','surv','otp','on heal%','damage_taken','attacks']
	target_data = ['otp','on heal%','on_target','on_heal']
	timing_data = ['attack mean','attack median','attack variance','heal mean','heal median','heal variance','phase mean','phase median','jaunt mean','jaunt median']
	count_data  = ['first_attacks','alpha_heals','phases','jaunts','greens']
	dmg_data    = ['dmg/spike (est)']
	record_data = ['win','loss','tie']
	available_data += target_data + timing_data + count_data + dmg_data + record_data

	# with st.form('data selection'):
	show_data = data_filter.multiselect('show columns (filters in sidebar)',available_data,default=default_sel)
		# init_data = st.form_submit_button('get data')

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
			# mh_df = mh_df[mh_df['series_id'].str.contains('_kb')|mh_df['series_id'].str.contains('_taco')]
			mh_df = mh_df[mh_df['series_id'].str.contains("|".join(render.kb_tags))==True]
		else:
			mh_df = mh_df[mh_df['series_id'].str.contains("|".join(render.kb_tags))==False]
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

	if init_filters:
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
					if data_aggr == 'avg/match':
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

					mh_gb.configure_grid_options(enableCellTextSelection=True,ensureDomOrder=True)
					mh_gb.configure_default_column(width=128,cellStyle={'text-align': 'center'})
					mh_gb.configure_columns('player',width=128,cellStyle={'text-align': 'left','font-weight':'bold'},pinned='left')
					mh_gb.configure_columns(['attacks','heals','on_target','on_heal'],type='customNumericFormat',precision=0)
					mh_gb.configure_columns(timing_data,type='customNumericFormat',precision=3)
					if data_aggr == 'avg/match':
						mh_gb.configure_columns(['deaths','targets']+count_data+dmg_data,type='customNumericFormat',precision=1)
						mh_gb.configure_columns(record_data,type='customNumericFormat',precision=3)
					else:
						mh_gb.configure_columns(['deaths','targets']+count_data+dmg_data+record_data,type='customNumericFormat',precision=0)

					mh_gb.configure_columns(hide_data,hide=True)
					# mh_gb.configure_selection('single', pre_selected_rows=None)

					# st.markdown("""<p class="font20"" style="display:inline;color:#4d4d4d";>{}</p><br>""".format(table_title),True)
					mh_ag = AgGrid(
						mh_write,
						allow_unsafe_jscode=True,
						custom_css=render.grid_css,
						gridOptions=mh_gb.build(),
						update_mode='NO_UPDATE',
						# fit_columns_on_grid_load= not ss.mobile,
						height = 920 if not ss.mobile else 400,
						theme=table_theme,
						enable_enterprise_modules=False
					)
		except:
			st.write('No data found for these filters')
	else:
		st.caption('')
		st.caption('Overall records by players. Select and apply filters in the sidebar to fetch data')







