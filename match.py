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

table_theme = 'material'

def main(con):
	# match info, relevant to all views
	match_row = ss.matches[(ss.matches['match_id']==ss.mid)&(ss.matches['series_id']==ss.sid)]
	m_score  = [int(match_row.iloc[0]['score0']),int(match_row.iloc[0]['score1'])]
	m_spikes = [int(match_row.iloc[0]['spikes0']),int(match_row.iloc[0]['spikes1'])]

	# match wide dataframes
	sqlq = util.str_sqlq('Heroes',ss.sid,ss.mid)
	hero_df = pd.read_sql_query(sqlq, con)
	hero_df = hero_df.sort_values(by='team')
	hero_list = hero_df['hero'].tolist()

	sqlq = util.str_sqlq('Actions',ss.sid,ss.mid)
	actions_df = pd.read_sql_query(sqlq, con)
	actions_df['time'] = pd.to_datetime(actions_df['time_ms'],unit='ms').dt.strftime('%M:%S.%f').str[:-4]
	actions_df['time_m'] = actions_df['time_ms']/60000

	# match wide vars
	team_emoji_map = {0:'🔵',1:'🔴','':''}
	kill_emoji_map = {None:'',1:'❌'}
	team_colour_map = {0:'dodgerblue',1:'tomato'}
	team_name_map = {0:'blu',1:'red'}

	# hero info, setup heroname:player/team info for views
	hero_team_map = {}
	hero_player_map = {}
	for index, row in hero_df.iterrows():
		hname = row['hero']
		hero_team_map[hname] = row['team']
		pname = row['player_name']
		if pname == None:
			pname = hname
		hero_player_map[hname] = pname
	actions_df['team'] = actions_df['actor'].map(hero_team_map)

	# hero stats on target and timing
	hero_df['on_target']  = hero_df['attack_chains'].map(lambda x: sum(ast.literal_eval(x).values()))
	hero_df['max_targets']= hero_df['team'].map(lambda x: m_spikes[x])
	hero_df['otp_float']  = hero_df['on_target'] / hero_df['max_targets']
	hero_df['otp']        = hero_df['otp_float'].map("{:.0%}".format)
	hero_df['otp'] = hero_df['otp'].map(lambda x: '' if x == '0%' else x)
	hero_df['timing'] = hero_df['attack_timing'].map(lambda x: (ast.literal_eval(x)))
	hero_df['timing'] = hero_df['timing'].map(lambda x: [a/1000 for a in x])
	hero_df['avg atk'] = hero_df['timing'].map(lambda x: statistics.mean([abs(v) for v in x]) if len(x) > 0 else None)
	hero_df['med atk'] = hero_df['timing'].map(lambda x: statistics.median(x) if len(x) > 0 else None)
	hero_df['var atk'] = hero_df['timing'].map(lambda x:  statistics.variance(x)  if len(x) > 1 else 0)

	hero_df['phase_timing'] = hero_df['phase_timing'].map(lambda x: (ast.literal_eval(x)))
	hero_df['phase_timing'] = hero_df['phase_timing'].map(lambda x: [a/1000 for a in x])
	hero_df['avg phase']    = hero_df['phase_timing'].map(lambda x: statistics.mean(x) if len(x) > 0 else None)
	hero_df['jaunt_timing'] = hero_df['jaunt_timing'].map(lambda x: (ast.literal_eval(x)))
	hero_df['jaunt_timing'] = hero_df['jaunt_timing'].map(lambda x: [a/1000 for a in x])
	hero_df['avg jaunt']    = hero_df['jaunt_timing'].map(lambda x: statistics.mean(x) if len(x) > 0 else None)

	hero_df['heal_timing'] = hero_df['heal_timing'].map(lambda x: ast.literal_eval(x))
	hero_df['heal_timing'] = hero_df['heal_timing'].map(lambda x: [a/1000 for a in x])
	hero_df['avg heal']    = hero_df['heal_timing'].map(lambda x: statistics.mean(x) if len(x) > 0 else None)
	hero_df['med heal']    = hero_df['heal_timing'].map(lambda x: statistics.median(x) if len(x) > 0 else None)
	hero_df['var heal']    = hero_df['heal_timing'].map(lambda x: statistics.variance(x) if len(x) > 0 else None)
	hero_df['on heal']     = hero_df['heal_timing'].map(lambda x: len(x))
	hero_df['on heal divisor'] = hero_df['team'].map(lambda x: m_spikes[abs(x-1)]) - hero_df['targets']
	hero_df['on heal float']   = hero_df['on heal']/hero_df['on heal divisor']
	hero_df['on heal%']    = hero_df['on heal float'].map("{:.0%}".format)
	hero_df['on heal%']	   = hero_df['on heal%'].map(lambda x: '' if x == '0%' else x)


	hero_df['surv_float'] = 1-hero_df['deaths']/hero_df['targets']
	hero_df['surv'] = hero_df['surv_float'].map("{:.0%}".format)
	hero_df['surv'] = hero_df['surv'].map(lambda x: '' if x == 'nan%' else x)

	hero_df['set1'] = hero_df['set1'].map(lambda x: '-' if x == None else x)

	# calc num attacks for tables and headers
	hattacks = []
	hrogues  = []
	actions_df['is_atk'] = actions_df['action_tags'].map(lambda x: 1 if "Attack" in x else 0)
	a_notspike = actions_df[ actions_df["spike_id"].isnull() ]
	for h in hero_df['hero']:
		atks = actions_df[actions_df['actor'] == h]['is_atk'].sum()
		offtgt = a_notspike[a_notspike['actor'] == h]['is_atk'].sum()
		spatks = atks-offtgt
		hattacks.append(atks)
		hrogues.append(offtgt)
	hero_df['atks'] = hattacks
	hero_df['offtgt']  = hrogues

	m_attacks = {}
	m_attacks[0] = int(hero_df[hero_df['team'] == 0]['atks'].sum())
	m_attacks[1] = int(hero_df[hero_df['team'] == 1]['atks'].sum())


	hero_df['index'] = hero_df['hero']
	hero_df = hero_df.set_index('index') 
	
	# get spike data for match
	sqlq = util.str_sqlq('Spikes',ss.sid,ss.mid)
	sdf = pd.read_sql_query(sqlq, con)
	sdf = sdf.rename(columns={"spike_duration": "dur", "spike_id": "#","spike_hp_loss": "dmg","target_team": "team"})
	sdf['time'] = pd.to_datetime(sdf['time_ms'],unit='ms').dt.strftime('%M:%S')
	sdf['time_m'] = sdf['time_ms']/60000
	# sort spikes by teams
	t_spikes = {}
	t_kills = {}
	for t in [0,1]:
		t_spikes[t] = sdf[sdf['team'] == t]
		t_kills[t] = sdf[(sdf['team'] == t) & (sdf['kill'] == 1)]

	# calc damage for summary/defence
	t_dmg = {}
	for t in [0,1]:
		t_dmg[t] = hero_df[(hero_df['team'] == t)]['damage_taken'].sum()
	# calc hero timing by team for headers
	ht,ht_mean,ht_med,ht_var = {},{},{},{}
	for t in [0,1]:
		ht[t] = []
		for tl in hero_df[(hero_df['team'] == t)]['timing']:
			ht[t] += tl
	for t in [0,1]:
		ht_mean[t] = statistics.mean([abs(x) for x in ht[t]])
		ht_med[t] = statistics.median(ht[t])


	# get hp data for later views
	sqlq = util.str_sqlq('HP',ss.sid,ss.mid)
	hp_df = pd.read_sql_query(sqlq, con)



	# MATCH HEADSER
	c1,c2 = st.columns(2)
	sid_date = "20" + ss.sid[0:2] + "/" + ss.sid[2:4] + "/" + ss.sid[4:6]
	header_str = sid_date +" > Match "+str(ss.mid) + " (" + ss.map +")"
	with c1:
		st.markdown("""<p class="font40"" style="display:inline; color:#4d4d4d";>{}</p>""".format(header_str),True)
	with c2:
		score_str = """<p style="text-align: right;">"""
		score_str += """<span class="font40" style="color:#666";>{}</span>""".format('score: ')
		score_str += """<span class="font40" style="color:dodgerblue";>{}</span>""".format(str(m_score[0]))
		score_str += """<span class="font40" style="color:#666";>{}</span>""".format(' - ')
		score_str += """<span class="font40" style="color:tomato";>{}</span>""".format(str(m_score[1]))
		score_str += """</p>"""
		st.markdown(score_str,True)



	# START SUMMARY PAGE
	if ss.view['match'] == 'summary':

		hdf = hero_df.copy()

		hdf['icon_path'] = hdf['archetype'].map(lambda x: "archetypes/"+x.replace('/','.')+'.png')
		hdf['at'] = hdf['icon_path'].apply(util.image_formatter)

		c1,c2,c3,c4,c5,c6,c7 = st.columns([1,1,1,1,1,1,4])
		# summary header
		for t in [0,1]:
			t2 = abs(t-1)
			teamstring = """<p class="font40" style="color:{};">{}</p>""".format(team_colour_map[t],team_name_map[t],)
			c1.markdown(teamstring,True)
			c2.metric("Score"*t2,m_score[t],m_score[t]-m_score[t2])
			c3.metric("Spikes Called"*t2,m_spikes[t],m_spikes[t]-m_spikes[t2])
			c4.metric("Attacks Thrown"*t2,m_attacks[t],m_attacks[t]-m_attacks[t2])
			c5.metric("Avg Timing"*t2,round(ht_mean[t],2),round(ht_mean[t]-ht_mean[t2],3),delta_color='inverse')
			c6.metric("Dmg Taken (k)"*t2,round(t_dmg[t]/1000,1),round((t_dmg[t]-t_dmg[t2])/1000,1),delta_color="inverse")


		score_fig = go.Figure()
		for t in [0,1]:
			t2 = abs(t-1)
			kill_info = actions_df[(actions_df['team'] == t2) & (actions_df['action'] == 'Death')].copy().reset_index()

			# append score 0 to start and max_score to end
			kill_info['count'] = kill_info.index + 1
			kill_info.loc[-1] = kill_info.loc[0]
			kill_info.index = kill_info.index + 1
			kill_info.loc[0,'time_m'] = 0
			kill_info.loc[0,'count'] = 0
			kill_info = kill_info.sort_index()

			kill_info = kill_info.append(kill_info.iloc[-1]).reset_index()
			kill_info.loc[kill_info.index[-1], 'time_m'] = 10

			score_fig.add_trace(go.Scatter(
				x=kill_info['time_m'],
				y=kill_info['count'],
				name='',
				mode='lines',
				line=dict(color=team_colour_map[t], width=8),
			))
		score_fig.update_layout(
			barmode="overlay",
			showlegend=False,
			height=220,
			margin={'t': 0,'b':0,'l':0,'r':0},
			yaxis={'showticklabels':False, 'fixedrange':True,'range':[0,max(m_score[0],m_score[1])]},
			xaxis={'visible':True,'fixedrange':True,'range':[0,10],'title':'match time (m)'},
		)
		c7.plotly_chart(score_fig,use_container_width=True,config={'displayModeBar': False})

		hdf['team'] = hdf['team'].map(team_emoji_map)

		# hdf = hdf.set_index(['hero'])
		# st.dataframe(hdf.style.format(na_rep='-'),height=520)

		hdf['atk tm'] = hdf['avg atk'].map("{:0.2f}".format)
		hdf['atk tm'] = hdf['atk tm'].map(lambda x: '' if x == 'nan' else x)
		hdf['heal t'] = hdf['avg heal'].map("{:0.2f}".format)
		hdf['heal t'] = hdf['heal t'].map(lambda x: '' if x == 'nan' else x)
		hdf['dmg tk'] = hdf['damage_taken']/1000
		hdf['dmg tk'] = hdf['dmg tk'].map("{:0.1f}K".format)
		hdf = hdf[['team','hero','support','at','set1','set2','deaths','targets','surv','dmg tk','otp','atks','atk tm','on heal%']]

		# hdf = hdf.rename(columns={})
		sum_gb = GridOptionsBuilder.from_dataframe(hdf)
		sum_gb.configure_default_column(filterable=False,width=32,cellStyle={'text-align': 'center'})
		# sum_gb.configure_columns(['avg','med','var'],type='customNumericFormat',precision=2,width=36)
		sum_gb.configure_columns(['hero','set1','set2'],width=56)
		# sum_gb.configure_columns(['targets','deaths','atks'],width=24)
		# sum_gb.configure_columns(['dmg tk','otp','surv'],width=32)
		# sum_gb.configure_columns(['otp','surv','atk t','heal t'],width=32)


		# sum_gb.configure_columns(['surv'],cellStyle={'text-align': 'center'})
		sum_gb.configure_columns('hero',cellStyle=render.team_color)
		sum_gb.configure_columns(['set1','set2'],cellStyle=render.support_color)
		sum_gb.configure_columns('at',cellRenderer=render.icon)
		sum_gb.configure_columns(['team','support'],hide=True)

		sum_ag = AgGrid(
			hdf,
			allow_unsafe_jscode=True,
			gridOptions=sum_gb.build(),
			fit_columns_on_grid_load=True,
			height = 828,
			theme = table_theme,
		)

	# END SUMMARY PAGE

	# START DEFENCE
	if ss.view['match'] == 'defence':
		c1,c2,c3,c4,c5 = st.columns([1,1,1,1,6])

		hp_loss_st = c5.empty()


		def flag_heals(df):
			if ('Heal' in  df['action_tags']) and ('Ally' in  df['action_target_type']):
				return 1
			else:
				return 0
		actions_df['is_heal'] = actions_df.apply(flag_heals,axis=1)

		h_dmg_spike,h_dmg_surv,h_dmg_death = [],[],[]
		h_heals = []
		for h,row in hero_df.iterrows():
			dmg = sdf[sdf['target'] == h]['dmg'].sum()
			dmg_death = sdf[(sdf['target'] == h)&(sdf['kill'] == 1)]['dmg'].sum()
			dmg_surv = dmg - dmg_death
			h_dmg_spike.append(dmg)
			h_dmg_death.append(dmg_death)
			h_dmg_surv.append(dmg_surv)
			h_heals.append(actions_df[actions_df['target'] == h]['is_heal'].sum())

		hero_df['dmg_spike'] = h_dmg_spike
		hero_df['dmg_death'] = h_dmg_death
		hero_df['dmg_surv'] = h_dmg_surv
		hero_df['dmg_nonspike'] = hero_df['damage_taken'] - hero_df['dmg_spike']
		hero_df['heals_taken'] = h_heals


		# defence header
		t_dmg_surv = {}
		t_dmg_death = {}
		for t in [0,1]:
			t2 = abs(t-1)
			teamstring = """<p class="font40" style="color:{};">{}</p>""".format(team_colour_map[t],team_name_map[t],)
			c1.markdown(teamstring,True)

			c_deaths = sdf[(sdf['team'] == t)&(sdf['kill']==1)]['kill'].sum()
			t_dmg_surv[t] = hero_df[(hero_df['team'] == t)]['dmg_surv'].sum()
			t_dmg_surv[t] /= (m_spikes[t2] - c_deaths)
			t_dmg_death[t] = hero_df[(hero_df['team'] == t)]['dmg_death'].sum()
			t_dmg_death[t] /= c_deaths


		for t in [0,1]:
			t2 = abs(t-1)

			c2.metric("dmg taken (k)"*t2,round(t_dmg[t]/1000,1),round((t_dmg[t]-t_dmg[t2])/1000,1),delta_color="inverse")
			c3.metric("dmg/surv"*t2,round(t_dmg_surv[t]/1000,2),round((t_dmg_surv[t]-t_dmg_surv[t2])/1000,2),delta_color="inverse")
			c4.metric("dmg/death"*t2,  round(t_dmg_death[t]/1000,2),round((t_dmg_death[t]-t_dmg_death[t2])/1000,2),delta_color="inverse")


		# hp loss data
		sqlq = util.str_sqlq('HP',ss.sid,ss.mid,['time_ms','hero','hp','hp_loss'])
		hp_df = pd.read_sql_query(sqlq, con)

		hero_df['dmg'] = hero_df['damage_taken']/1000
		hero_df['dmg_nonspike'] = hero_df['dmg_nonspike']/1000
		hero_df['dmg'] = hero_df['dmg'].map("{:0.1f}K".format)
		hero_df['dmg_nonspike'] = hero_df['dmg_nonspike'].map("{:0.1f}K".format)
		hero_write = hero_df[['team','hero','deaths','targets','surv','dmg','dmg_nonspike','heals_taken','avg phase','avg jaunt']].copy()
		# hero_write = hero_write.fillna('')
		hero_write['team'] = hero_write['team'].map(team_emoji_map)
		hero_write['avg jaunt'] = hero_write['avg jaunt'].fillna('')
		hero_write['avg phase'] = hero_write['avg phase'].fillna('')
		
		def_gb = GridOptionsBuilder.from_dataframe(hero_write)
		# type=["numericColumn","numberColumnFilter"], )
		def_gb.configure_default_column(filterable=False,width=64,cellStyle={'text-align': 'center'})
		def_gb.configure_selection('multiple', pre_selected_rows=None)
		def_gb.configure_columns(['avg phase','avg jaunt'],type='customNumericFormat',precision=2)
		def_gb.configure_columns('team',hide=True)
		def_gb.configure_columns('hero',width=96)
		def_gb.configure_columns('hero',cellStyle=render.team_color)


		def_ag = AgGrid(
			hero_write,
			allow_unsafe_jscode=True,
			gridOptions=def_gb.build(),
			fit_columns_on_grid_load=True,
			update_mode='SELECTION_CHANGED',
			height = 840,
			theme=table_theme
		)

		hero_sel = []
		rows = def_ag['selected_rows']
		if rows:
			hero_sel = [r['hero'] for r in rows]


		# hp loss/greens graphs
		hp_df['team'] = hp_df['hero'].map(hero_team_map)
		hp_df['time_m'] = hp_df['time_ms']/60000
		hp_df = hp_df.sort_values(by='time_m')
		actions_df['is_green'] = actions_df['action'].map(lambda x: 1 if x == 'Respite' else 0)



		hpl_fig = make_subplots(rows=1,cols=2,horizontal_spacing=0.15,shared_xaxes=True,)

		if hero_sel:
			for h in hero_sel:
				hero_hp_df = hp_df[hp_df['hero']==h].copy()
				hero_hp_df['cumsum'] = hero_hp_df['hp_loss'].cumsum()

				greens = actions_df[(actions_df['actor']==h)&(actions_df['is_green']==1)].copy()
				greens['greens'] = greens['is_green'].cumsum()


				# dmg taken
				hpl_fig.add_trace(go.Scatter(
					y=hero_hp_df['cumsum'],
					x=hero_hp_df['time_m'],
					name=h,
					mode='lines',
					line=dict(color='coral', width=4,dash='dot'),
				),row=1, col=1)

				# spike markers
				h_spikes = sdf[sdf['target']==h]
				for sp,row in h_spikes.iterrows():
					sp_hp_df = hero_hp_df[(hero_hp_df['time_ms'] > row['time_ms'] - 2000)&(hero_hp_df['time_ms'] < row['time_ms'] + row['dur'] + 2000)]
					hpl_fig.add_trace(go.Scatter(
						y=sp_hp_df['cumsum'],
						x=sp_hp_df['time_m'],
						text='spike #'+str(row['#']),
						name=h,
						mode='lines',
						line=dict(color='SlateBlue', width=4),
					),row=1, col=1)

				# kill markers
				hpl_fig.add_trace(go.Scatter(
					y=hero_hp_df[hero_hp_df['hp'] == 0]['cumsum'],
					x=hero_hp_df[hero_hp_df['hp'] == 0]['time_m'],
					name=h,
					text='death',
					mode='markers',
					marker_color='white',
					marker=dict(size=8,line=dict(width=4,color='SlateBlue')),
				),row=1, col=1)

				# greens by player
				hpl_fig.add_trace(go.Scatter(
					x=greens['time_m'],
					y=greens['greens'],
					name=h,
					mode='lines',
					line=dict(color='seagreen', width=4),
				),row=1, col=2)
		else:
			for t in [0,1]:
				hero_hp_df = hp_df[hp_df['team']==t].copy()
				hero_hp_df['cumsum'] = hero_hp_df['hp_loss'].cumsum()

				greens = actions_df[actions_df['team']==t].copy()
				greens['greens'] = greens['is_green'].cumsum()

				hpl_fig.add_trace(go.Scatter(
					y=hero_hp_df[hero_hp_df['team'] == t]['cumsum'],
					x=hero_hp_df['time_m'],
					name=team_name_map[t],
					mode='lines',
					line=dict(color=team_colour_map[t], width=3),
				),row=1, col=1)
				hpl_fig.add_trace(go.Scatter(
					x=greens['time_m'],
					y=greens['greens'],
					name=team_name_map[t],
					mode='lines',
					line=dict(color=team_colour_map[t], width=3),
				),row=1, col=2)

		hpl_fig.update_layout(
				height=220,
				showlegend=False,
				margin={'t': 0,'b':0,'l':0,'r':20},
				xaxis={'title':'time (m)','range':[0,10]},
				yaxis={'title':'dmg taken'},
				# plot_bgcolor='rgba(0,0,0,0)',
			)

		green_range = [0,20*8]
		if hero_sel:
			green_range = [0,20]
		hpl_fig.update_xaxes(title_text="time (m)", row=1, col=2)
		hpl_fig.update_yaxes(visible=True, fixedrange=True,range=green_range, showgrid=True, title='greens used',row=1, col=2)
		hp_loss_st.plotly_chart(hpl_fig, use_container_width=True,config={'displayModeBar': False})

	# END DEFENCE 



	# START OFFENCE
	if ss.view['match'] == 'offence':
		c1,c2,c3,c4,c5,c6,c7 = st.columns([1,1,1,1,1,1,3])

		for t in [0,1]:
			t2 = abs(t-1)
			teamstring = """<p class="font40" style="color:{};">{}</p>""".format(team_colour_map[t],team_name_map[t],)
			c1.markdown(teamstring,True)
			c2.metric("Spikes Called"*t2,m_spikes[t],m_spikes[t]-m_spikes[t2])
			c3.metric("Attacks Thrown"*t2,m_attacks[t],m_attacks[t]-m_attacks[t2])
			c4.metric("Mean Timing"*t2,round(ht_mean[t],2),round(ht_mean[t]-ht_mean[t2],3),delta_color='inverse')
			c5.metric("Median Timing"*t2,round(ht_med[t],2),round(ht_med[t]-ht_med[t2],3),delta_color='inverse')

		# split to only heroes with attack chains
		hero_df = hero_df[(hero_df['attack_chains'] != "{}")]

		with c7:
			hero_sel_st = st.empty()
			st.markdown("""<p class="font20"" style="display:inline;color:#4d4d4d";>{}</p>""".format('attack chains'),True)

		c1,c2 = st.columns([2,1])
		with c1:
			# box plot for attack timing
			at_fig = make_subplots(rows=1,cols=2,column_widths=[0.7, 0.3],horizontal_spacing=0.05, shared_yaxes=True)
			total_timing = {0:[],1:[]}
			for h, row in hero_df.iterrows():
				total_timing[row['team']] += row['timing']
				at_fig.add_trace(go.Box(
					y=row['timing'],
					name=h,
					boxpoints='outliers',
					opacity=max(row['otp_float'],0.3),
					line_width=4*row['otp_float'],
					boxmean=True,
					marker=dict(
						color=team_colour_map[row['team']],
						line_width=0,
						size = 4,
						)
					),row=1, col=1
				)
			for i in [0,1]:
				at_fig.add_trace(go.Box(
					y=total_timing[i],
					name=team_name_map[i],
					boxpoints='outliers',
					boxmean=True,
					line_width=3,
					marker=dict(
						color=team_colour_map[i],
						line_width=0,
						size = 4,
						)
					),row=1, col=2
				)

			at_fig.update_layout(
				height=360,
				width=400,
				margin = dict(t=24, l=0, r=32, b=0),
				showlegend=False,
				yaxis_title='first atk timing (s)',
				yaxis={'range': [-2 ,5]},
				)
			st.plotly_chart(at_fig,use_container_width=True, config={'displayModeBar': False})

			
			# slice DF to new df for offence
			hero_write = hero_df[['team','hero','targets','deaths','on_target','otp','avg atk','med atk','var atk','atks','offtgt','first_attacks']]
			hero_write = hero_write.rename(columns={"targets":'tgts',"on_target": "ontgt", "avg atk": "avg","med atk": "med","var atk": "var","first_attacks":'first'})
			hero_write = hero_write.sort_values(by='team')
			hero_write['team'] = hero_write['team'].map(team_emoji_map)

			# aggrid options for offence table
			of_gb = GridOptionsBuilder.from_dataframe(hero_write)
			of_gb.configure_default_column(filterable=False)
			of_gb.configure_columns(['avg','med','var'],type='customNumericFormat',precision=2,width=36)
			of_gb.configure_columns(['ontgt','otp','atks','offtgt','first'],width=32,filterable=False,type='customNumericFormat',precision=0)
			of_gb.configure_columns('hero',width=60)
			of_gb.configure_columns('hero',cellStyle=render.team_color)
			of_gb.configure_columns(['tgts','deaths','team'],hide=True)

			of_gb.configure_selection('multiple', pre_selected_rows=None)

			of_ag = AgGrid(
				hero_write,
				allow_unsafe_jscode=True,
				gridOptions=of_gb.build(),
				fit_columns_on_grid_load=True,
				update_mode='SELECTION_CHANGED',
				height = 860,
				theme = table_theme,
			)

			# get hero selection from aggrid clicks
			rows = of_ag['selected_rows']
			if rows:
				hero_sel = [r['hero'] for r in rows]
			else:
				hero_sel = []
			# hero_sel = hero_df.index

		with c2:

			# ATTACK CHAINS
			hero_sel = hero_sel_st.multiselect('heroes',hero_df.index,default=hero_sel,help='You can also click/ctrl-click from the table on the right to select heroes.')
			# default to all heroes if non selected
			if hero_sel == []:
				hero_sel = hero_df.index

			at_dicts = []
			max_length = 0
			for h in hero_sel:
				hteam  = hero_df.loc[h]['team']
				missed = m_spikes[hteam] - hero_df.loc[h]['on_target']
				at_dicts.append({'label':'Total','id':'Total','parent':'','text':'','count':missed,'length':0})
				hat = ast.literal_eval(hero_df.loc[h]['attack_chains']) # hero attack chains dict (list:count)
				for at,n in hat.items():
					at_dict = {'label':None,'id':None,'parent':None,'name':'','count':0,'length':0}
					at_list = ast.literal_eval(at)
					at_dict['label'] = at_list[-1]
					at_dict['length'] = len(at_list)
					max_length = max(len(at_list),max_length)
					if len(at_list) == 1:
						at_dict['parent'] = 'Total'
						at_dict['id'] = 'Total - ' + at_list[-1]
					else:
						at_dict['parent'] = 'Total - '+' - '.join(at_list[0:len(at_list)-1])
						at_dict['id'] = at_dict['parent'] + ' - ' + at_list[-1]
					at_dict['count'] = n
					at_dict['text'] =  "<b>" + str(n) + "</b><br>" + at_dict['id'].replace('Total - ','').replace('Total','')
					at_dicts.append(at_dict)


			# create empty dict if parent leaf doesn't exist
			# traverse from longest lengths first
			for i in range(max_length,0,-1):
				add_dicts = []
				for a in at_dicts:
					if a['length'] == i:
						parentid = a['parent']
						# for each parentid, find all dicts with that ID
						parentdicts = [b for b in at_dicts if b['id'] == parentid and b['id'] != a['id']]
						# if none found, add it with count=0
						if parentdicts == []:
							label = parentid.split(' - ')[-1]
							newparent  = parentid.split(' - ')
							newparent  = ' - '.join(newparent[0:len(newparent)-1])
							text =  "<b>" + str(0) + "</b><br>" + parentid.replace('Total - ','').replace('Total','')
							add_dicts.append({'label':label,'id':parentid,'parent':newparent,'text':text,'count':0,'length':i-1})
				at_dicts += add_dicts

			# if multiple heroes, merge same-IDs (must be unique)
			for i in range(len(at_dicts)):
				if at_dicts[i]['id'] != 'delete':
					for j in range(len(at_dicts)):
						if at_dicts[i]['id'] == at_dicts[j]['id'] and i != j:
							at_dicts[i]['count'] += at_dicts[j]['count']
							at_dicts[i]['text'] =  "<b>" + str(at_dicts[i]['count']) + "</b><br>" + at_dicts[i]['id'].replace('Total - ','').replace('Total','')
							at_dicts[j]['id'] = 'delete' # flag ID for deletion
							break
			at_dicts = [atd for atd in at_dicts if atd['id'] != 'delete']

			at_df = pd.DataFrame.from_records(at_dicts)

			

			# format labels with counts
			at_df['label'] = at_df['label'] + "<br>" + at_df['count'].astype(str)
			# format center total to OTP or blank
			if len(hero_sel) == 1:
				hero = hero_sel[0]
				at_df.loc[at_df['id'] == 'Total', 'label'] = '<b>' + str(hero_df.loc[hero,'on_target']) + ' (' + hero_df.loc[hero,'otp'] + ')</b>'
			else:
				at_df.loc[at_df['id'] == 'Total', 'label'] = ''

			ac_fig  = go.Figure(go.Sunburst(
				ids=at_df['id'],
				labels=at_df['label'],
				hovertext = at_df['text'],
				hoverinfo = "text",
				parents=at_df['parent'],
				values=at_df['count'],
				rotation=45,
			))

			ac_fig.update_layout(
				margin = dict(t=0, l=0, r=0, b=0),
				height=360)
			st.plotly_chart(ac_fig,use_container_width=True,config={'displayModeBar': False})

			## debugging table
			# at_df = at_df[['id','parent','count']]
			# st.table(at_df)

			# text chains for table display
			at_df['chain'] = at_df['id'].map(lambda x: x.replace("Total - ","").replace(" - "," → "))
			at_write = at_df[['chain','count']].sort_values(by='count',ascending=False)
			at_write = at_write[at_write['chain'] != 'Total']
			# chain to icons
			at_write['icons'] = at_write['chain'].map(lambda x: ' '.join([util.image_formatter('powers/' + powers[a]['icon']) for a in x.split(" → ")]))
			at_write = at_write[['icons','chain','count']]

			at_gb = GridOptionsBuilder.from_dataframe(at_write)
			at_gb.configure_columns('icons',cellRenderer=render.icon,width=36)
			at_gb.configure_columns('count',width=16)
			at_gb.configure_columns('chain',width=56)

			sl_ag = AgGrid(
				at_write,
				allow_unsafe_jscode=True,
				gridOptions=at_gb.build(),
				fit_columns_on_grid_load=True,
				height = 720,
				theme=table_theme
			)


	# END OFFENCE


	# START SPIKES
	elif ss.view['match'] == 'spikes':
		
		c1,c2,c3,c4,c5,c6,c7 = st.columns([1,1,1,1,1,1,4])

		for t in [0,1]:
			teamstring = """<p class="font40" style="color:{};">{}</p>""".format(team_colour_map[t],team_name_map[t],)
			c1.markdown(teamstring,True)
	

		for t in [0,1]:
			t2 = abs(t-1)

			c2.metric("Spikes"*t2,m_spikes[t],m_spikes[t]-m_spikes[t2])
			c3.metric("Mean Timing"*t2,round(ht_mean[t],2),round(ht_mean[t]-ht_mean[t2],3),delta_color='inverse')
			c4.metric("Median Timing"*t2,round(ht_med[t],2),round(ht_med[t]-ht_med[t2],3),delta_color='inverse')

			a1 = round(t_spikes[t]['attacks'].mean(),2)
			a0 = round(t_spikes[t2]['attacks'].mean(),2)
			c5.metric("Avg Attacks"*t2,a0,round(a0-a1,2))
			a1 = round(t_spikes[t]['attackers'].mean(),2)
			a0 = round(t_spikes[t2]['attackers'].mean(),2)
			c6.metric("Avg Attackers"*t2,a0,round(a0-a1,2))

		# graph spikes and kills for summary
		with c7:
			fig = go.Figure()
			# spike traces
			lineoffset=50
			fig.add_trace(go.Scatter(
				x=t_spikes[1]['time_m'],
				name='spikes',
				y=t_spikes[1]['#']+lineoffset,
				text=t_spikes[1]['target'],
				mode='lines',
				line=dict(color='DodgerBlue', width=6),
				hovertemplate = "%{x:.2f}<br><b>%{text}</b><br>",
			))
			fig.add_trace(go.Scatter(
				x=t_spikes[0]['time_m'],
				y=t_spikes[0]['#'],
				text=t_spikes[0]['target'],
				name='spikes',
				mode='lines',
				line=dict(color='tomato', width=6),
				hovertemplate = "%{x:.2f}<br><b>%{text}</b><br>",
			))

			# kill traces
			fig.add_trace(go.Scatter(
				x=t_kills[0]['time_m'],
				y=t_kills[0]['#'],
				text=t_spikes[0]['target'],
				name='kills',
				mode='markers',
				marker_color='white',
				marker=dict(size=12,line=dict(width=4,color='tomato')),
				hovertemplate = "%{x:.2f}<br><b>%{text}</b><br>kill",
			))
			fig.add_trace(go.Scatter(
				x=t_kills[1]['time_m'],
				y=t_kills[1]['#']+lineoffset,
				text=t_spikes[1]['target'],
				name='kills',
				mode='markers',
				marker_color='white',
				marker=dict(size=12,line=dict(width=4,color='DodgerBlue')),
				hovertemplate = "%{x:.2f}<br><b>%{text}</b><br>kill",
			))

			fig.update_layout(
				showlegend=False,
				height=220,
				xaxis_title="match time (m)",
				xaxis={'range':[0,10]},
				yaxis={'showticklabels':False,'title':'# spikes'},
				margin={'t': 0,'b':0,'l':52,'r':0},
				plot_bgcolor='rgba(0,0,0,0)',
			)
			st.plotly_chart(fig,use_container_width=True,config={'displayModeBar': False})


		c1,c2 = st.columns(2)

		# left side
		with c1:
			# st.subheader('spike list')
			colourmap = {0:'DodgerBlue',1:'Tomato'}

			# spikes counts by players
			pc0 = sdf[(sdf['team'] == 0)]
			pc1 = sdf[(sdf['team'] == 1)]
			pc0 = pc0.groupby('target').count().sort_values('#',ascending=False)
			pc1 = pc1.groupby('target').count().sort_values('#',ascending=False)
			pc0['colour'] = 'DodgerBlue'
			pc1['colour'] = 'Tomato'
			pc = pd.concat([pc0,pc1])
			pc = pc.sort_values('#',ascending=False)
			

			fig = go.Figure()
			fig.add_trace(go.Bar(
				x=pc.index,
				y=pc['#'],
				name='targets',
				marker_color=pc['colour'],
				opacity=0.5
			))
			fig.add_trace(go.Bar(
				x=pc.index,
				y=pc['kill'],
				name='deaths',
				marker_color=pc['colour'],
			))
			fig.update_layout(
				barmode="overlay",
				showlegend=False,
				height=250,
				margin={'t': 8,'b':0,'l':0,'r':0},
				yaxis={'visible': True, 'fixedrange':True},
				xaxis={'visible':True,'fixedrange':True},
				hovermode="x unified"
			)
			st.plotly_chart(fig,use_container_width=True,config={'displayModeBar': False})

			# select individual spikes
			st_spikes = st.empty()

			# spike filters
			filters = st.expander('spike filters',expanded=False)
			spike_filters = {}
			with filters:
				spike_filters['players'] = st.multiselect('heroes',hero_list)
				spike_filters['team'] = st.radio('team',['all','blue','red'])
				spike_filters['deaths'] = st.radio('deaths',['all','dead','alive'])
			sf = sdf.copy() # spikes filtered dataframe copy
			if spike_filters['players']: # if 1+ players are selected
				sf = sf[sf['target'].isin(spike_filters['players'])]
			if spike_filters['team'] == 'blue':
				sf = sf[(sf['team'] == 0)]
			elif spike_filters['team'] == 'red':
				sf = sf[(sf['team'] == 1)]
			if spike_filters['deaths'] == 'dead':
				sf = sf[(sf['kill'] == 1)]
			elif spike_filters['deaths'] == 'alive':
				sf = sf[(sf['kill'] != 1)]
			
			# format data for printing table
			sf['team'] = sf['team'].map(team_emoji_map)
			sf['kill'] = sf['kill'].map(kill_emoji_map)
			sf['dur'] = sf['dur'].map(lambda x: round(x/1000,1))


			sf_write = sf[['#','time','team','kill','target','dur','attacks','attackers','dmg']]
			sf_write = sf_write.rename(columns={'attacks':'atks','attackers':'atkr'})
			sf_gb = GridOptionsBuilder.from_dataframe(sf_write)
			sf_gb.configure_default_column(filterable=False)
			sf_gb.configure_columns(['#','team','kill'],width=18)
			sf_gb.configure_columns(['atks','atkr'],width=60)
			sf_gb.configure_columns(['time','dur','dmg'],width=54)
			sf_gb.configure_columns(['target'],width=100,cellStyle=render.team_color)
			sf_gb.configure_selection('single', pre_selected_rows=[0])
			sf_gb.configure_columns('dur',filterable=True)
			sf_gb.configure_columns('dmg',type='customNumericFormat',precision=0)
			sf_gb.configure_columns('team',hide=True)

			response = AgGrid(
				sf_write,
				allow_unsafe_jscode=True,
				gridOptions=sf_gb.build(),
				# data_return_mode="filtered_and_sorted",
				update_mode='SELECTION_CHANGED',
				fit_columns_on_grid_load=True,
				height = 640,
				theme=table_theme
			)

			# selected row on grid click
			row = response['selected_rows']
			if row:
				# spike ID == selected
				spid = row[0]['#']
			else:
				spid = 1

		# right side
		# spike log
		with c2:
			# st.subheader('spike log')

			# grab actions with spike id
			sl = actions_df[(actions_df['spike_id'] == spid)] 
			sl = sl.rename(columns={"time": "match_time", "spike_time": "cast", "spike_hit_time": "hit", "cast_dist": "dist"})
 
			# times and target for spike hp log
			sp_target   = sdf.loc[spid-1,'target'] # spiketarget
			sp_delta   = sdf['start_delta'][spid-1]
			sp_start = sdf['time_ms'][spid-1]
			sp_end   = sdf['dur'][spid-1] + sp_start

			act_min = min(sl['cast'].tolist())
			hit_max = max(sl['hit'].tolist())
			
			# spike hp log
			hp_start_time = min(sp_start - sp_delta,sp_start-act_min)
			hp_end_time   = max(sp_end+sp_delta+1000,sp_start+hit_max+sp_delta+1000)
			sp_hp_df = hp_df[(hp_df['hero'] == sp_target)&(hp_df['time_ms'] >= hp_start_time)&(hp_df['time_ms'] <= hp_end_time)].copy()
			sp_hp_df = sp_hp_df.reset_index()


			act_min /= 1000
			hit_max /= 1000

			# hp graph data
			sp_hp_df['spike_time'] = sp_hp_df['time_ms'] - sp_start  - sp_delta # convert to relative time
			sp_hp_df['spike_time'] = sp_hp_df['spike_time'] - sp_delta # convert to relative time
			sp_hp_df['spike_time'] = sp_hp_df['spike_time']/1000 # convert to relative time
			sp_hp_df.at[0,'hp_loss'] = 0 # start at 0 HP loss
			sp_hp_df['hp_loss'] = sp_hp_df['hp_loss'].cumsum() # convert hp loss @ time to cumulative
			if sdf.at[spid-1,'kill'] == 1: # if spike death truncate graph at death
				deathatrow = len(sp_hp_df)
				for i in range(len(sp_hp_df['hp'])):
					if sp_hp_df['hp'][i] == 0:
						deathatrow = i+1
						break 
				sp_hp_df = sp_hp_df[0:deathatrow]
			
			sp_fig = make_subplots(rows=2,cols=1,row_heights=[0.80, 0.20],vertical_spacing=0.1, shared_xaxes=True)

			# hp at time
			sp_fig.add_trace(go.Scatter(
				x=sp_hp_df['spike_time'],
				y=sp_hp_df['hp'],
				name='hp',
				mode='lines',
				line=dict(color='coral', width=6),
			),row=1, col=1)
			# cumu hp loss at time
			sp_fig.add_trace(go.Scatter(
				x=sp_hp_df['spike_time'],
				y=sp_hp_df['hp_loss'],
				name='hp loss',
				mode='lines',
				line=dict(color='SlateBlue', width=6,dash='dash'),
			),row=1, col=1)
			hp_time = sp_hp_df['spike_time'].tolist()

			# format spike dataframe
			sl['cast'] = sl['cast']/1000
			sl['hit'] = sl['hit']/1000
			sl['hit_hp'] = sl['hit_hp'].fillna(-1).astype(int).replace(-1,pd.NA)
			sl['dist'] = sl['dist'].fillna(-1).astype(int).replace(-1,pd.NA)
			sl['icon_path'] = 'powers/'+sl['icon']
			sl['image'] = sl['icon_path'].apply(util.image_formatter)
			sl_write = sl[['cast','actor','image','action','hit','dist']]   
			sl_write = sl_write.fillna('')

			# color action markers by type
			acolours = []
			for t in sl['action_tags']:
				tags = ast.literal_eval(t)
				if 'Inspirations' in tags:
					acolours.append('GreenYellow')
				elif 'Attack' in tags:
					acolours.append('crimson')
				elif 'Heal' in tags:
					acolours.append('limegreen')
				elif 'Teleport' in tags:
					acolours.append('gold')
				elif 'Phase' in tags:
					acolours.append('DeepSkyBlue')
				else:
					acolours.append('Grey')

			# add action markers to HP graph
			# add white line as background color workaround
			sp_fig.add_trace(go.Scatter(x=[-2,60],y= [4,4],fill='tozeroy', mode='none',fillcolor='white',
				),row=2, col=1)
			sp_fig.add_trace(go.Scatter(
				x=sl['cast'],
				y=[1.6]*len(sl['cast']),
				name='',
				text=sl['actor']+"<br>"+sl['action'],
				marker_color=acolours,
				marker=dict(size=12,line=dict(width=2,color='DarkSlateGrey')),
				mode='markers',
				hovertemplate = "<b>cast time</b> <br>%{text}"
			),row=2, col=1)
			sp_fig.add_trace(go.Scatter(
				x=sl['hit'],
				y=[0.6]*len(sl['cast']),
				name='',
				text=sl['actor']+"<br>"+sl['action'],
				marker_color=acolours,
				marker=dict(size=12,line=dict(width=2,color='DarkSlateGrey')),
				# opacity=0.5,
				mode='markers',
				hovertemplate = "<b>hit time</b> <br>%{text}"
			),row=2, col=1)

			hp_y_max = max(sp_hp_df['hp'].max(),sp_hp_df['hp_loss'].max(),2000)
			hp_range=[act_min,hit_max-sp_delta/1000]

			sp_fig.update_layout(
				height=314,
				showlegend=False,
				xaxis={'fixedrange':True,'range':hp_range},
				margin={'t': 0,'b':40,'l':48,'r':0},
				# plot_bgcolor='rgba(0,0,0,0)',
			)
			sp_fig.update_xaxes(title_text="spike time (s)", row=2, col=1, showgrid=False)
			sp_fig.update_yaxes(visible=True, fixedrange=True, showgrid=True, title='hp',row=1, col=1)
			sp_fig.update_yaxes(visible=False, fixedrange=True, showgrid=False,range=[0,2],title='hit/cast',row=2, col=1)

			sp_fig.update_yaxes(range=[0,hp_y_max], row=1, col=1)

			st.plotly_chart(sp_fig, use_container_width=True,config={'displayModeBar': False})


			sl_gb = GridOptionsBuilder.from_dataframe(sl_write)
			sl_gb.configure_default_column(filterable=False)
			sl_gb.configure_columns(['actor','action'],width=84)
			sl_gb.configure_columns(['cast','hit','dist'],width=40)
			sl_gb.configure_columns(['cast','hit'],type='customNumericFormat',precision=2)
			sl_gb.configure_columns('image',cellRenderer=render.icon,width=40)

			sl_ag = AgGrid(
				sl_write,
				allow_unsafe_jscode=True,
				gridOptions=sl_gb.build(),
				fit_columns_on_grid_load=True,
				height = 720,
				theme=table_theme
			)

	# END SPIKES



	# START LOGs
	elif ss.view['match'] == 'logs':

			c1,c2,c3 = st.columns([2,1,7])
			actions_df['hit'] = actions_df['hit_time'] - actions_df['time_ms']
			actions_df['hit'] = actions_df['hit']/1000

			with c1:
				st.markdown("""<p class="font20"" style="color:#4d4d4d";>{}</p>""".format('filters'),True)
				# list filters
				# time bounds
				t_start = st.slider('timing bounds (m)', min_value=0.0, max_value=10.0, value=0.0, step=0.25, format=None)
				t_end = st.slider('', min_value=0.0, max_value=10.0, value=10.0, step=0.25, format=None)
				t_start = min(t_start,t_end)*1000*60

				# action toggles
				a_filtertoggle = st.checkbox('show self toggles',value=False)
				a_spikes = st.checkbox('show spike actions',value=True)
				a_nonspikes = st.checkbox('show non-spike actions',value=True)
				t_end = max(t_start,t_end)*1000*60


				# apply filters
				if not a_filtertoggle:
					actions_df = actions_df.loc[(actions_df['action_type'] != 'Toggle')&(actions_df['action_target_type'] != 'Self')]
				if not a_spikes:
					actions_df = actions_df.loc[(~actions_df['spike_id'].notnull())]
				if not a_nonspikes:
					actions_df = actions_df.loc[(actions_df['spike_id'] > 0)]

				actions_df = actions_df.loc[(actions_df['time_ms'] >= t_start) & (actions_df['time_ms'] <= t_end)]
			with c3:

				# icons
				actions_df['icon_path'] = 'powers/'+actions_df['icon']
				actions_df['image'] = actions_df['icon_path'].apply(util.image_formatter)

				# team emojis
				actions_df['t'] = actions_df['actor'].map(hero_team_map)
				actions_df['t'] = actions_df['t'].map(team_emoji_map)
				# actions_df['tt'] = actions_df['target'].map(hero_team_map)
				# actions_df['tt'] = actions_df['tt'].map(team_emoji_map)
				# actions_df['tt'] = actions_df['tt'].fillna('')

				actions_write = actions_df[['time','t','actor','image','action','target']]
				actions_write = actions_write.rename(columns={"time":'cast'})
				actions_write['target'] = actions_write['target'].fillna('')

				al_gb = GridOptionsBuilder.from_dataframe(actions_write)
				al_gb.configure_columns(['actor','target','action'],width=84)
				al_gb.configure_columns(['cast','image'],width=48)
				al_gb.configure_columns(['t'],width=32)
				al_gb.configure_columns('image',cellRenderer=render.icon)
				al_gb.configure_pagination(paginationAutoPageSize=False,paginationPageSize=100)

				sl_ag = AgGrid(
					actions_write,
					allow_unsafe_jscode=True,
					gridOptions=al_gb.build(),
					fit_columns_on_grid_load=True,
					height = 1024,
					theme=table_theme
				)
	# END LOGS

