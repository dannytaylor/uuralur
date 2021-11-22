import os, sys, time, math, argparse, json, datetime, yaml, sqlite3, ast, statistics

import streamlit as st
ss = st.session_state # global shorthand for this file

import pandas as pd
import tools.util as util

import plotly.express as px
import plotly.graph_objects as go

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
config = yaml.safe_load(open('data/config.yaml'))

def main(con):
	# high level score,map,etc. to go hero
	# match header
	mh = st.container()
	sid_date = "20" + ss.sid[0:2] + "/" + ss.sid[2:4] + "/" + ss.sid[4:6]
	mh.header(sid_date +" > Match "+str(ss.mid) + " (" + ss.map +")")

	
	sqlq = util.str_sqlq('Heroes',ss.sid,ss.mid)
	hero_df = pd.read_sql_query(sqlq, con)
	hero_list = hero_df['hero'].tolist()

	sqlq = util.str_sqlq('Actions',ss.sid,ss.mid)
	actions_df = pd.read_sql_query(sqlq, con)
	actions_df['time'] = pd.to_datetime(actions_df['time_ms'],unit='ms').dt.strftime('%M:%S.%f').str[:-4]


	# START SUMMARY PAGE
	if ss.view['match'] == 'summary':
		st.header('summary')

		c1,c2 = st.columns([1,2])
		hdf = hero_df[['hero','team','archetype','set1','set2','deaths','targets']].copy()

		with c2:
			teammap = {0:'🔵',1:'🔴'}
			hdf = hdf.sort_values(by='team')
			hdf['team'] = hdf['team'].map(teammap)
			hdf = hdf.set_index(['hero'])
			st.dataframe(hdf.style.format(na_rep='-'),height=520)
	# END SUMMARY PAGE


	# START SPIKES
	elif ss.view['match'] == 'spikes':
		# get spike data for match
		sqlq = util.str_sqlq('Spikes',ss.sid,ss.mid)
		sdf = pd.read_sql_query(sqlq, con)
		sdf = sdf.rename(columns={"spike_duration": "dur", "spike_id": "#","spike_hp_loss": "dmg","target_team": "team"})
		sdf['time'] = pd.to_datetime(sdf['time_ms'],unit='ms').dt.strftime('%M:%S')
		
		c1,c2,c3,c4,c5,c6,c7 = st.columns([1,1,1,1,1,1,4])
		teams_dict = {0:{'name':'blu','color':'DodgerBlue'},
			 1:{'name':'red','color':'Tomato'}}

		# sort spikes by teams
		sdf['time_m'] = sdf['time_ms']/60000
		tspikes = {}
		tkills = {}
		for t in [0,1]:
			tspikes[t] = sdf[sdf['team'] == t]
			tkills[t] = sdf[(sdf['team'] == t) & (sdf['kill'] == 1)]
			teamstring = """<h2 style="color:{};">{}</h1>""".format(teams_dict[t]['color'],teams_dict[t]['name'],)
			c1.markdown(teamstring,True)
	
		# calc hero timing
		ht = {0:[],1:[]}
		h0 = hero_df[(hero_df['team'] == 0)]
		h1 = hero_df[(hero_df['team'] == 1)]
		for t in h0['timing']:
			ht[0] += ast.literal_eval(t)
		for t in h1['timing']:
			ht[1] += ast.literal_eval(t)

		for t in [0,1]:
			t2 = abs(t-1)
			c2.metric("Spikes",len(tspikes[t2].index),len(tspikes[t2].index)-len(tspikes[t].index))

			ht0 = statistics.mean(ht[t])/1000
			ht1 = statistics.mean(ht[t2])/1000
			c3.metric("Mean Timing",round(ht0,2),round(ht0-ht1,3),delta_color='inverse')
			ht0 = statistics.median(ht[t])/1000
			ht1 = statistics.median(ht[t2])/1000
			c4.metric("Median Timing",round(ht0,2),round(ht0-ht1,3),delta_color='inverse')

			a0 = round(tspikes[t]['attacks'].mean(),2)
			a1 = round(tspikes[t2]['attacks'].mean(),2)
			c5.metric("Avg Attacks",a0,round(a0-a1,2))
			a0 = round(tspikes[t]['attackers'].mean(),2)
			a1 = round(tspikes[t2]['attackers'].mean(),2)
			c6.metric("Avg Attackers",a0,round(a0-a1,2))

		# graph spikes and kills for summary
		with c7:
			fig = go.Figure()
			# spike traces
			lineoffset=50
			fig.add_trace(go.Line(
				x=tspikes[1]['time_m'],
				name='spikes',
				y=tspikes[1]['#']+lineoffset,
				text=tspikes[1]['target'],
				mode='lines',
				line=dict(color='DodgerBlue', width=6),
				hovertemplate = "%{x:.2f}<br><b>%{text}</b><br>",
			))
			fig.add_trace(go.Line(
				x=tspikes[0]['time_m'],
				y=tspikes[0]['#'],
				text=tspikes[0]['target'],
				name='spikes',
				mode='lines',
				line=dict(color='tomato', width=6),
				hovertemplate = "%{x:.2f}<br><b>%{text}</b><br>",
			))

			# kill traces
			fig.add_trace(go.Scatter(
				x=tkills[0]['time_m'],
				y=tkills[0]['#'],
				text=tspikes[0]['target'],
				name='kills',
				mode='markers',
				marker_color='white',
				marker=dict(size=12,line=dict(width=4,color='tomato')),
				hovertemplate = "%{x:.2f}<br><b>%{text}</b><br>kill",
			))
			fig.add_trace(go.Scatter(
				x=tkills[1]['time_m'],
				y=tkills[1]['#']+lineoffset,
				text=tspikes[1]['target'],
				name='kills',
				mode='markers',
				marker_color='white',
				marker=dict(size=12,line=dict(width=4,color='DodgerBlue')),
				hovertemplate = "%{x:.2f}<br><b>%{text}</b><br>kill",
			))
			
			fig.update_layout(
				showlegend=False,
				height=240,
				xaxis_title="match time (m)",
				xaxis={'range':[0,10]},
				yaxis={'showticklabels':False,'title':'# spikes'},
				margin={'t': 0,'b':0,'l':52,'r':0},
				plot_bgcolor='rgba(0,0,0,0)',
			)
			st.plotly_chart(fig,use_container_width=True,config={'displayModeBar': False})


		c1,c2 = st.columns([3,2])

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
				height=320,
				margin={'t': 20,'b':0,'l':0,'r':0},
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

			# format selection text for spikes
			# select spike for rightside viewing
			def format_spike_str(spid):
				text = '[' + sf.loc[spid-1,'time'] + '] ' + sf.loc[spid-1,'target']
				if sf.loc[spid-1,'kill'] == 1:
					text += " 💀"
				return text		
			
			# format data for printing table
			killmap = {None:'',1:'💀'}
			teammap = {0:'🔵',1:'🔴'}
			sf['team'] = sf['team'].map(teammap)
			sf['kill'] = sf['kill'].map(killmap)
			sf['dur'] = sf['dur']/1000
			sf['dmg'] = sf['dmg']


			sf_write = sf[['#','time','team','kill','target','dur','attacks','attackers','greens','dmg']]
			gb = GridOptionsBuilder.from_dataframe(sf_write)
			gb.configure_columns(['#','team','kill'],width=22)
			gb.configure_columns(['attacks','attackers','greens'],width=48)
			gb.configure_columns(['time','dur','dmg'],width=64)
			gb.configure_selection('single', pre_selected_rows=[0])
			gb.configure_columns('dur',type='customNumericFormat',precision=1)
			gb.configure_columns('dmg',type='customNumericFormat',precision=0)
			# gb.configure_columns('team',hide=True)

			response = AgGrid(
				sf_write,
				# allow_unsafe_jscode=True,
				gridOptions=gb.build(),
				# data_return_mode="filtered_and_sorted",
				update_mode='SELECTION_CHANGED',
				fit_columns_on_grid_load=True,
				height = 640,
				theme='material'
			)

			# selected row on grid click
			row = response['selected_rows']
			if row:
				# spike ID == selected
				spid = row[0]['#']
			else:
				spid = 1

			# times and target for spike hp log
			sp_target   = sdf.loc[spid-1,'target'] # spiketarget
			sp_start = sdf['time_ms'][spid-1]
			sp_end   = sdf['dur'][spid-1]+sp_start

		# right side
		# spike log
		with c2:
			# st.subheader('spike log')
			
			# spike hp log
			conditions = " AND hero=\'"+ sp_target.replace('\'','\'\'') + "\'"
			conditions += " AND time_ms>= " + str(sp_start - config['spike_display_extend'])
			conditions += " AND time_ms<= " + str(sp_end + config['spike_display_extend'] + 1000)
			sqlq = util.str_sqlq('HP',ss.sid,ss.mid,['time_ms','hp','hp_loss'],conditions)
			hp_df = pd.read_sql_query(sqlq, con)

			# hp graph data
			hp_df['spike_time'] = (hp_df['time_ms']-sp_start)/1000 # convert to relative time
			hp_df.at[0,'hp_loss'] = 0 # start at 0 HP loss
			hp_df['hp_loss'] = hp_df['hp_loss'].cumsum() # convert hp loss @ time to cumulative
			if sdf.at[spid-1,'kill'] == 1: # if spike death truncate graph at death
				deathatrow = len(hp_df)
				for i in range(len(hp_df['hp'])):
					if hp_df['hp'][i] == 0:
						deathatrow = i+1
						break 
				hp_df = hp_df[0:deathatrow]
			
			hp_fig = go.Figure()

			# hp at time
			hp_fig.add_trace(go.Scatter(
				x=hp_df['spike_time'],
				y=hp_df['hp'],
				name='hp',
				mode='lines',
				line=dict(color='coral', width=6),
			))
			# cumu hp loss at time
			hp_fig.add_trace(go.Scatter(
				x=hp_df['spike_time'],
				y=hp_df['hp_loss'],
				name='hp loss',
				mode='lines',
				line=dict(color='SlateBlue', width=6,dash='dash'),
			))
			hp_time = hp_df['spike_time'].tolist()

			# grab actions with spike id
			sl = actions_df[(actions_df['spike_id'] == spid)] 
			# format spike dataframe
			sl = sl.rename(columns={"time": "match_time", "spike_time": "cast", "spike_hit_time": "hit", "cast_dist": "dist"})
			sl['cast'] = sl['cast']/1000
			sl['hit'] = sl['hit']/1000
			sl['hit_hp'] = sl['hit_hp'].fillna(-1).astype(int).replace(-1,pd.NA)
			sl['dist'] = sl['dist'].fillna(-1).astype(int).replace(-1,pd.NA)
			# sl['image'] = '<image src=\'http:/localhost:8000/assets/icons/powers/' + sl['icon'] + '\'>'
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


			hp_range=[min(0,hp_time[0]),max(2,hp_time[-1])]
			# hp graph, data above
			hp_fig.update_layout(
				height=270,
				showlegend=False,
				xaxis_title="spike time (s)",
				yaxis={'visible': True, 'title':'hp','fixedrange':True,'range':[0,max(2000,max(hp_df['hp_loss']))]},
				xaxis={'visible':False,'fixedrange':True,'range':hp_range},
				margin={'t': 20,'b':0,'l':0,'r':0},
				hovermode="x unified"
			)
			st.plotly_chart(hp_fig, use_container_width=True,config={'displayModeBar': False})

			# add action markers to HP graph
			act_fig = go.Figure()
			act_fig.add_trace(go.Scatter(
				x=sl['cast'],
				y=[1.6]*len(sl['cast']),
				name='',
				text=sl['actor']+"<br>"+sl['action'],
				marker_color=acolours,
				marker=dict(size=12,line=dict(width=2,color='DarkSlateGrey')),
				mode='markers',
				hovertemplate = "<b>cast time</b> <br>%{text}"
			))
			act_fig.add_trace(go.Scatter(
				x=sl['hit'],
				y=[0.6]*len(sl['cast']),
				name='',
				text=sl['actor']+"<br>"+sl['action'],
				marker_color=acolours,
				marker=dict(size=12,line=dict(width=2,color='DarkSlateGrey')),
				# opacity=0.5,
				mode='markers',
				hovertemplate = "<b>hit time</b> <br>%{text}"
			))
			act_fig.update_layout(
				height=91,
				showlegend=False,
				xaxis_title="spike time (s)",
				yaxis={'visible': True,'title':'hit/cast','showticklabels':False,'fixedrange':True,'range':[0,2]},
				xaxis={'visible':True,'fixedrange':True,'range':hp_range},
				margin={'t': 0,'b':40,'l':48,'r':0},
				plot_bgcolor='rgba(0,0,0,0)',
			)
			st.plotly_chart(act_fig, use_container_width=True,config={'displayModeBar': False})


			# render html text as html
			icon_renderer = JsCode("""function(params) {
						return params.value ? params.value : '';
			}""")

			sl_gb = GridOptionsBuilder.from_dataframe(sl_write)
			sl_gb.configure_columns(['actor','action'],width=86)
			sl_gb.configure_columns(['cast','hit','dist'],width=44)
			sl_gb.configure_columns(['cast','hit'],type='customNumericFormat',precision=2)
			sl_gb.configure_columns('image',cellRenderer=icon_renderer,width=32)

			sl_ag = AgGrid(
				sl_write,
				allow_unsafe_jscode=True,
				gridOptions=sl_gb.build(),
				fit_columns_on_grid_load=True,
				height = 720,
				theme='material'
			)

	# END SPIKES
