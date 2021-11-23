import os, sys, time, math, argparse, json, datetime, yaml, sqlite3, ast, statistics

import streamlit as st
ss = st.session_state # global shorthand for this file

import pandas as pd
import seaborn as sns
import tools.util as util

import plotly.express as px
import plotly.graph_objects as go

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
config = yaml.safe_load(open('data/config.yaml'))
powers = json.loads(open('data/powers.json').read())

def main(con):
	# match info, relevant to all views
	match_row = ss.matches[(ss.matches['match_id']==ss.mid)&(ss.matches['series_id']==ss.sid)]
	m_score  = [int(match_row.iloc[0]['score0']),int(match_row.iloc[0]['score1'])]
	m_spikes = [int(match_row.iloc[0]['spikes0']),int(match_row.iloc[0]['spikes1'])]

	# match wide dataframes
	sqlq = util.str_sqlq('Heroes',ss.sid,ss.mid)
	hero_df = pd.read_sql_query(sqlq, con)
	hero_list = hero_df['hero'].tolist()

	sqlq = util.str_sqlq('Actions',ss.sid,ss.mid)
	actions_df = pd.read_sql_query(sqlq, con)
	actions_df['time'] = pd.to_datetime(actions_df['time_ms'],unit='ms').dt.strftime('%M:%S.%f').str[:-4]

	# match wide vars
	icon_renderer = JsCode("""function(params) {
						return params.value ? params.value : '';
			}""")
	teammap = {0:'🔵',1:'🔴','':''}
	killmap = {None:'',1:'❌'}

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
		st.header('summary')

		c1,c2 = st.columns([1,2])
		hdf = hero_df[['hero','team','archetype','set1','set2','deaths','targets']].copy()

		with c2:
			hdf = hdf.sort_values(by='team')
			hdf['team'] = hdf['team'].map(teammap)
			hdf = hdf.set_index(['hero'])
			st.dataframe(hdf.style.format(na_rep='-'),height=520)
	# END SUMMARY PAGE


	# START OFFENCE
	if ss.view['match'] == 'offence':
		c1,c2 = st.columns([3,2])

		# split to only heroes with attack chains
		hero_df = hero_df[(hero_df['attack_chains'] != "{}")]
		hero_df['index'] = hero_df['hero']
		hero_df = hero_df.set_index('index')

		hero_df['on_target']  = hero_df['attack_chains'].map(lambda x: sum(ast.literal_eval(x).values()))
		hero_df['max_targets']= hero_df['team'].map(lambda x: m_spikes[x])
		hero_df['otp'] 		  = hero_df['on_target'] / hero_df['max_targets']
		hero_df['otp'] 		  = hero_df['otp'].map("{:.0%}".format)
		hero_df['timing'] = hero_df['attack_timing'].map(lambda x: (ast.literal_eval(x)))
		hero_df['avg timing'] = hero_df['timing'].map(lambda x: statistics.mean(x)/1000)
		hero_df['med timing'] = hero_df['timing'].map(lambda x: statistics.median(x)/1000)
		hero_df['var timing'] = hero_df['timing'].map(lambda x:  statistics.variance(x)/1000000  if len(x) > 1 else 0)
		
		# calc num attacks for table and headers
		hattacks = []
		hrogues  = []
		actions_df['is_atk'] = actions_df['action_tags'].map(lambda x: 1 if "Attack" in x else 0)
		actions_df['is_spike_atk'] = actions_df['spike_id'].map(lambda x: 1 if x else 0)
		actions_df['is_spike_atk'] = actions_df[['is_atk','is_spike_atk']].min(axis=1)
		for h in hero_df['hero']:
			atks = actions_df[actions_df['actor'] == h]['is_atk'].sum()
			spatks = actions_df[actions_df['actor'] == h]['is_spike_atk'].sum()
			offtgt = spatks
			hattacks.append(atks)
			hrogues.append(offtgt)
		hero_df['atks'] = hattacks
		hero_df['offtgt']  = hrogues

		m_attacks = {}
		m_attacks[0] = hero_df[hero_df['team'] == 0]['atks'].sum()
		m_attacks[1] = hero_df[hero_df['team'] == 1]['atks'].sum()


		with c1:
			spk_str = """<p style="">"""
			spk_str += """<span class="font20" style="color:#666";>{}</span>""".format('spikes called '+'&nbsp;'*7)
			spk_str += """<span class="font20" style="color:dodgerblue";>{}</span>""".format(str(m_spikes[0]))
			spk_str += """<span class="font20" style="color:#666";>{}</span>""".format(' - ')
			spk_str += """<span class="font20" style="color:tomato";>{}</span>""".format(str(m_spikes[1]))
			spk_str += """</p>"""
			st.markdown(spk_str,True)

			spk_str = """<p style="">"""
			spk_str += """<span class="font20" style="color:#666";>{}</span>""".format('attacks thrown '+'&nbsp;'*2)
			spk_str += """<span class="font20" style="color:dodgerblue";>{}</span>""".format(str(m_attacks[0]))
			spk_str += """<span class="font20" style="color:#666";>{}</span>""".format(' - ')
			spk_str += """<span class="font20" style="color:tomato";>{}</span>""".format(str(m_attacks[1]))
			spk_str += """</p>"""
			st.markdown(spk_str,True)

			## switched to aggrid format for now
			# def highlight_team(s):
			# 	 if s.team == 0:
			# 		 return ['background-color: rgba(30, 144, 255,0.2)'] * len(s)
			# 	 else:
			# 		 return ['background-color: rgba(255, 99, 71,0.2)'] * len(s)
			# cm = sns.light_palette("green", as_cmap=True)
			
			# slice DF to new df for offence
			hero_write = hero_df[['team','hero','targets','deaths','on_target','otp','avg timing','med timing','var timing','atks','offtgt']]
			hero_write = hero_write.rename(columns={"targets":'tgts',"on_target": "ontgt", "avg timing": "avg","med timing": "med","var timing": "var"})
			hero_write = hero_write.sort_values(by='team')
			hero_write['team'] = hero_write['team'].map(teammap)
			# hero_write = hero_write.style.apply(highlight_team, axis=1).format(precision=2)
			
			# st.dataframe(hero_write.style.format(precision=2).background_gradient(cmap=cm, subset=['avg timing','med timing']),height=640)
			# st.dataframe(hero_write,height=640)

			# aggrid options for offence table
			of_gb = GridOptionsBuilder.from_dataframe(hero_write)
			of_gb.configure_default_column(filterable=False)
			of_gb.configure_columns(['avg','med','var'],type='customNumericFormat',precision=2,width=32)
			of_gb.configure_columns('team',width=32,filterable=False)
			of_gb.configure_columns(['ontgt','otp','atks','offtgt'],width=36,filterable=False)
			of_gb.configure_columns('hero',width=64)
			of_gb.configure_columns(['tgts','deaths'],hide=True)

			of_gb.configure_selection('multiple', pre_selected_rows=None)

			of_ag = AgGrid(
				hero_write,
				# allow_unsafe_jscode=True,
				gridOptions=of_gb.build(),
				fit_columns_on_grid_load=True,
				update_mode='SELECTION_CHANGED',
				height = 720,
				theme = 'material',
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
			hero_sel = st.multiselect('heroes',hero_df.index,default=hero_sel)
			# default to all heroes if non selected
			if hero_sel == []:
				hero_sel = hero_df.index

			at_dicts = []
			max_length = 0
			for h in hero_sel:
				hteam  = hero_df.loc[h]['team']
				missed = m_spikes[hteam] - hero_df.loc[h]['on_target']
				at_dicts.append({'label':'Total','id':'Total','parent':'','name':'','count':missed,'length':0})
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
							add_dicts.append({'label':label,'id':parentid,'parent':newparent,'name':'','count':0,'length':i-1})
				at_dicts += add_dicts

			# if multiple heroes, merge same-IDs (must be unique)
			for i in range(len(at_dicts)):
				if at_dicts[i]['id'] != 'delete':
					for j in range(len(at_dicts)):
						if at_dicts[i]['id'] == at_dicts[j]['id'] and i != j:
							at_dicts[i]['count'] += at_dicts[j]['count']
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

			at_fig  = go.Figure(go.Sunburst(
				ids=at_df['id'],
				labels=at_df['label'],
				hoverinfo = "label",
				parents=at_df['parent'],
				values=at_df['count'],
			))

			at_fig.update_layout(margin = dict(t=0, l=0, r=0, b=0))
			st.plotly_chart(at_fig,use_container_width=True,config={'displayModeBar': False})

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
			at_gb.configure_columns('icons',cellRenderer=icon_renderer,width=36)
			at_gb.configure_columns('count',width=16)
			at_gb.configure_columns('chain',width=64)

			sl_ag = AgGrid(
				at_write,
				allow_unsafe_jscode=True,
				gridOptions=at_gb.build(),
				fit_columns_on_grid_load=True,
				height = 480,
				theme='material'
			)

	# END OFFENCE


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
			teamstring = """<p class="font40" style="color:{};">{}</p>""".format(teams_dict[t]['color'],teams_dict[t]['name'],)
			c1.markdown(teamstring,True)
	
		# calc hero timing
		ht = {0:[],1:[]}
		h0 = hero_df[(hero_df['team'] == 0)]
		h1 = hero_df[(hero_df['team'] == 1)]
		for t in h0['attack_timing']:
			ht[0] += ast.literal_eval(t)
		for t in h1['attack_timing']:
			ht[1] += ast.literal_eval(t)

		for t in [0,1]:
			t2 = abs(t-1)
			
			c2.metric("Spikes",m_spikes[t2],m_spikes[t2]-m_spikes[t])

			ht1 = statistics.mean(ht[t])/1000
			ht0 = statistics.mean(ht[t2])/1000
			c3.metric("Mean Timing",round(ht0,2),round(ht0-ht1,3),delta_color='inverse')
			ht1 = statistics.median(ht[t])/1000
			ht0 = statistics.median(ht[t2])/1000
			c4.metric("Median Timing",round(ht0,2),round(ht0-ht1,3),delta_color='inverse')

			a1 = round(tspikes[t]['attacks'].mean(),2)
			a0 = round(tspikes[t2]['attacks'].mean(),2)
			c5.metric("Avg Attacks",a0,round(a0-a1,2))
			a1 = round(tspikes[t]['attackers'].mean(),2)
			a0 = round(tspikes[t2]['attackers'].mean(),2)
			c6.metric("Avg Attackers",a0,round(a0-a1,2))

		# graph spikes and kills for summary
		with c7:
			fig = go.Figure()
			# spike traces
			lineoffset=50
			fig.add_trace(go.Scatter(
				x=tspikes[1]['time_m'],
				name='spikes',
				y=tspikes[1]['#']+lineoffset,
				text=tspikes[1]['target'],
				mode='lines',
				line=dict(color='DodgerBlue', width=6),
				hovertemplate = "%{x:.2f}<br><b>%{text}</b><br>",
			))
			fig.add_trace(go.Scatter(
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


		c1,c2 = st.columns([2,2])

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
			
			# format data for printing table
			sf['team'] = sf['team'].map(teammap)
			sf['kill'] = sf['kill'].map(killmap)
			sf['dur'] = sf['dur']/1000
			sf['dmg'] = sf['dmg']


			sf_write = sf[['#','time','team','kill','target','dur','attacks','attackers','greens','dmg']]
			gb = GridOptionsBuilder.from_dataframe(sf_write)
			gb.configure_columns(['#','team','kill'],width=20)
			gb.configure_columns(['attacks','attackers','greens'],width=48)
			gb.configure_columns(['time','dur','dmg'],width=64)
			gb.configure_columns(['target'],width=128)
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
			sl_gb.configure_columns(['actor','action'],width=84)
			sl_gb.configure_columns(['cast','hit','dist'],width=40)
			sl_gb.configure_columns(['cast','hit'],type='customNumericFormat',precision=2)
			sl_gb.configure_columns('image',cellRenderer=icon_renderer,width=40)

			sl_ag = AgGrid(
				sl_write,
				allow_unsafe_jscode=True,
				gridOptions=sl_gb.build(),
				fit_columns_on_grid_load=True,
				height = 720,
				theme='material'
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
				actions_df['t'] = actions_df['t'].map(teammap)
				# actions_df['tt'] = actions_df['target'].map(hero_team_map)
				# actions_df['tt'] = actions_df['tt'].map(teammap)
				# actions_df['tt'] = actions_df['tt'].fillna('')

				actions_write = actions_df[['time','t','actor','image','action','target']]
				actions_write = actions_write.rename(columns={"time":'cast'})
				actions_write['target'] = actions_write['target'].fillna('')

				al_gb = GridOptionsBuilder.from_dataframe(actions_write)
				al_gb.configure_columns(['actor','target','action'],width=84)
				al_gb.configure_columns(['cast','image'],width=48)
				al_gb.configure_columns(['t'],width=32)
				al_gb.configure_columns('image',cellRenderer=icon_renderer)
				al_gb.configure_pagination(paginationAutoPageSize=False,paginationPageSize=100)

				sl_ag = AgGrid(
					actions_write,
					allow_unsafe_jscode=True,
					gridOptions=al_gb.build(),
					fit_columns_on_grid_load=True,
					height = 1024,
					theme='material'
				)
	# END LOGS

