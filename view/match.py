import os, sys, time, math, ujson, datetime, yaml, sqlite3, ast, statistics, random

import streamlit as st
ss = st.session_state # global shorthand for this file

import pandas as pd
import tools.util as util
import tools.render as render
import data.pset_icons as pset_icons
from tools.init_match import init_match
from millify import millify

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode
config = yaml.safe_load(open('data/config.yaml'))
powers = ujson.loads(open('data/powers.json').read())

# match wide vars
team_emoji_map = {0:'🔵',1:'🔴','':''}
kill_emoji_map = {None:'',1:'❌'}
team_colour_map = {0:'dodgerblue',1:'tomato'}
team_name_map = {0:'blu',1:'red'}
table_theme = config['table_theme']

def main(con):
	# match info, relevant to all views
	hero_df,actions_df,sdf,m_score,m_spikes,m_attacks,t_spikes,t_kills,t_dmg,ht_mean,ht_med = init_match(ss.sid,ss.mid)
	
	hero_df = hero_df.copy()
	actions_df = actions_df.copy()
	sdf = sdf.copy()

	hero_player_map = util.hero_player_dict(dict(zip(hero_df['hero'],hero_df['player_name'])))
	if ss['useplayernames']:
		hero_df['hero'] 	= hero_df['hero'].map(hero_player_map)
		hero_df['index'] = hero_df['hero']
		hero_df = hero_df.set_index('index') 

		actions_df['actor'] = actions_df['actor'].map(hero_player_map)
		actions_df['target']= actions_df['target'].map(hero_player_map)
		sdf['target'] 		= sdf['target'].map(hero_player_map)

	hero_list = hero_df['hero'].tolist()
	hero_team_map = {}
	for index, row in hero_df.iterrows():
		hname = row['hero']
		hero_team_map[hname] = row['team']
		pname = row['player_name']
		if pname == None:
			pname = hname
		hero_player_map[hname] = pname
	actions_df['team'] = actions_df['actor'].map(hero_team_map)

	# MATCH HEADSER
	c1,c2 = st.columns([8,2])

	sid_date = "20" + ss.sid[0:2] + "/" + ss.sid[2:4] + "/" + ss.sid[4:6]
	# header_str = sid_date +" > Match "+str(ss.mid) + " (" + ss.map +")"
	header_str = ""
	if not ss.mobile: header_str += sid_date
	if ss.view['match'] != 'series':
		header_str +=  " · match "
		header_str += str(ss.mid)
	header_str += " · "
	sid_str = ss.sid.split("_")[1:]
	sid_str = [render.team_name_map[s] if s in render.team_name_map else s for s in sid_str]
	header_str += " - ".join(sid_str)

	with c1:
		st.markdown("""<p class="fontheader"" style="display:inline; color:#4d4d4d";>{}</p>""".format(header_str),True)
		
		st.write('') #spacing hack
		st.write('')
	with c2:
		score_str = """<p style="text-align: left;">"""
		if not st.session_state.mobile: score_str += """<span class="fontheader" style="color:#4d4d4d";>{}</span>""".format('score: ')
		score_str += """<span class="fontheader" style="color:dodgerblue";>{}</span>""".format(str(m_score[0]))
		score_str += """<span class="fontheader" style="color:#4d4d4d";>{}</span>""".format(' - ')
		score_str += """<span class="fontheader" style="color:tomato";>{}</span>""".format(str(m_score[1]))
		score_str += """</p>"""
		st.markdown(score_str,True)


	opacities = ['deaths_opacity','targets_opacity','otp_opacity','ontgt_opacity','onheal_opacity','onhealn_opacity','surv_opacity']




	# START SUMMARY PAGE
	if ss.view['match'] == 'summary':

		hdf = hero_df.copy()

		c1,c2,c3,c4,c5,c7,c8 = st.columns([1,1,1,1,1,3,2])

		# summary header
		for t in [0,1]:
			t2 = abs(t-1)
			teamstring = """<p class="font40" style="color:{};">{}</p>""".format(team_colour_map[t],team_name_map[t],)
			c1.markdown(teamstring,True)
			c2.metric("Score"*t2,m_score[t],m_score[t]-m_score[t2])
			c3.metric("Spikes Called"*t2,m_spikes[t],m_spikes[t]-m_spikes[t2])
			c4.metric("Attacks Thrown"*t2,m_attacks[t],m_attacks[t]-m_attacks[t2])
			# c6.metric("Avg Timing"*t2,round(ht_mean[t],2),round(ht_mean[t]-ht_mean[t2],3),delta_color='inverse')
			c5.metric("Dmg Taken"*t2,millify(t_dmg[t],precision=1),millify((t_dmg[t]-t_dmg[t2]), precision=1),delta_color="inverse")


		score_fig = go.Figure()
		spike_fig = go.Figure()
		for t in [0,1]:
			t2 = abs(t-1)
			kill_time = [0] + actions_df[(actions_df['team'] == t2) & (actions_df['action'] == 'Death')]['time_m'].to_list()

			kill_count = [0]
			if kill_time != [0]:
			# append score 0 to start and max_score to end
				kill_count = [i for i in range(len(kill_time))]

			kill_time.append(10)
			kill_count.append(kill_count[-1])


			score_fig.add_trace(go.Scatter(
				x=kill_time,
				y=kill_count,
				name='',
				mode='lines',
				line=dict(color=team_colour_map[t], width=8),
			))

		spike_fig.add_trace(go.Bar(
			x=['blu','red'],
			y=[m_spikes[0],m_spikes[1]],
			name='spikes called',
			opacity=0.5,
			marker_color = [team_colour_map[0],team_colour_map[1]]
		))
		spike_fig.add_trace(go.Bar(
			x=['blu','red'],
			y=[m_score[0],m_score[1]],
			name='kills',
			marker_color = [team_colour_map[0],team_colour_map[1]]
		))

		score_fig.update_layout(
			showlegend=False,
			height=220,
			margin={'t': 0,'b':0,'l':0,'r':0},
			yaxis={'title':'score','fixedrange':True,'range':[0,1+max(m_score[0],m_score[1])]},
			xaxis={'visible':True,'fixedrange':True,'range':[0,10],'title':'match time (m)'},
		)
		spike_fig.update_layout(
			barmode="overlay",
			showlegend=False,
			height=220,
			margin={'t': 0,'b':42,'l':24,'r':0},
			yaxis={'fixedrange':True,'range':[0,max(m_spikes[0],m_spikes[1])+5]},
			xaxis={'visible':False,'fixedrange':True},
			hovermode="x unified",
			bargap=0.50,
		)
		c7.plotly_chart(score_fig,use_container_width=True,config={'displayModeBar': False})
		c8.plotly_chart(spike_fig,use_container_width=True,config={'displayModeBar': False})


		hdf['atk tm'] = hdf['avg atk'].map("{:0.2f}".format)
		hdf['atk tm'] = hdf['atk tm'].map(lambda x: '' if x == 'nan' else x)
		hdf['heal t'] = hdf['avg heal'].map("{:0.2f}".format)
		hdf['heal t'] = hdf['heal t'].map(lambda x: '' if x == 'nan' else x)
		hdf['atks'] = hdf['atks'].map(lambda x: '' if x == 0 else x)
		hdf['heals'] = hdf['heals'].map(lambda x: '' if x == 0 else x)
		hdf['dmg tk'] = hdf['damage_taken']/1000
		hdf['dmg tk'] = hdf['dmg tk'].map("{:0.1f}K".format)
		hdf = hdf[['team','hero','support','at','set1','set2','deaths','targets','surv','otp','on heal%','atks','heals']+opacities]
		hdf['support'] = hdf['support'].fillna(0)
		hdf = hdf.sort_values(['team','support'],ascending=[True,True])
		hdf = hdf.rename(columns={'on heal%':'onheal'})

		sum_gb = GridOptionsBuilder.from_dataframe(hdf)
		# sum_gb.configure_grid_options(enableCellTextSelection=True,ensureDomOrder=True)
		sum_gb.configure_grid_options(enableRangeSelection=True)
		sum_gb.configure_default_column(filterable=False,width=32,cellStyle={'text-align': 'center'},suppressMovable=True)
		sum_gb.configure_columns(['hero','set1','set2'],width=64)
		# sum_gb.configure_columns(['hero'],pinned='left',)
		# sum_gb.configure_columns(['surv'],cellStyle={'text-align': 'center'})
		sum_gb.configure_columns('hero',pinned='left',cellStyle=render.team_color)
		sum_gb.configure_columns(['deaths','targets','atks'],type='customNumericFormat',precision=0)
		# sum_gb.configure_columns(['set1','set2'],cellRenderer=render.icon,width=56,cellStyle={'text-align': 'left'})
		sum_gb.configure_columns(['set1','set2'],cellStyle=render.support_color,width=48)

		# opacities
		sum_gb.configure_columns(['deaths'],cellStyle=render.deaths_bg)
		sum_gb.configure_columns(['targets'],cellStyle=render.targets_bg)
		sum_gb.configure_columns(['surv'],cellStyle=render.surv_bg)
		sum_gb.configure_columns(['otp'],cellStyle=render.otp_bg)
		sum_gb.configure_columns(['onheal'],cellStyle=render.onheal_bg)

		sum_gb.configure_columns(['at'],width=28,cellRenderer=render.icon)
		sum_gb.configure_columns(['team','support']+opacities,hide=True)

		sum_ag = AgGrid(
			hdf,
			allow_unsafe_jscode=True,
			gridOptions=sum_gb.build(),
			fit_columns_on_grid_load= not ss.mobile,
			height = 16*48+64,
			theme = table_theme,
		)
	# END SUMMARY PAGE


	# START SUPPORT
	if ss.view['match'] == 'support':

		# support data setup
		sup_df = hero_df[hero_df['support']==1].copy()
		sup_heroes  = sup_df['hero'].tolist()
		sup_actions = actions_df[(actions_df['actor'].isin(sup_heroes))]
		sup_heals   = sup_actions[(sup_actions['actor'].isin(sup_heroes))&(sup_actions['action_tags'].str.contains('Heal'))&(sup_actions['action_target_type']=='Ally (Alive)')&(sup_actions['action']!='Spirit Ward')].copy()

		# filter out powers for displaying extras
		sup_extras  = sup_actions.loc[~sup_actions.index.isin(sup_heals.index)]
		sup_extras  = sup_extras[~((sup_extras['action_tags'].str.contains('MOV'))|(sup_extras['action_tags'].str.contains('Teleport'))|(sup_extras['action_tags'].str.contains('Phase')))]
		sup_extras  = sup_extras[~((sup_extras['action_type']=='Toggle')&(sup_extras['action_target_type']=='Self'))]
		sup_extras  = sup_extras[~(sup_extras['action_type']=='Inspiration')&~((sup_extras['action_type']=='Toggle')&(sup_extras['action_target_type']=='Self'))]
		sup_extras  = sup_extras[~(sup_extras['action_type']=='Inspiration')&~((sup_extras['action_type']=='Toggle')&(sup_extras['action_target_type']=='Self'))]
		sup_extras  = sup_extras[~((sup_extras['action']=='Healing Aura')|(sup_extras['action']=='Hasten')|(sup_extras['action']=='Nullify Pain'))]

		# counts for table
		n_heals,n_cms,n_phase,n_ff,n_late,n_topups = [],[],[],[],[],[]
		for h in sup_heroes:
			h_heals_df = sup_heals[sup_heals['actor'] == h]
			n_heals.append(len(h_heals_df.index))
			n_cms.append(len(sup_extras[(sup_extras['actor']==h)&(sup_extras['action_tags'].str.contains('CM'))].index)) 
			n_phase.append(len(h_heals_df[h_heals_df['action_tags'].str.contains('Phase Hit')].index))
			n_ff.append(len(h_heals_df[h_heals_df['action_tags'].str.contains('Fat Finger')].index)) 
			n_late.append(len(h_heals_df[h_heals_df['hit_hp'] == 0].index)) 
			n_topups.append(n_heals[-1] - len(h_heals_df[h_heals_df['spike_id'] > 0]))

		sup_df['heals']       = n_heals
		sup_df['phase hits']  = n_phase
		sup_df['fat fingers'] = n_ff
		sup_df['late'] 		  = n_late
		sup_df['cms'] 		  = n_cms
		sup_df['topups'] 	  = n_topups

		sup_timing_fig = go.Figure()

		h_heal_powers = {}
		h_extra_powers = {}
		min_timing = 10 # start high
		max_timing = 0 # start high
		for h, row in sup_df.iterrows():
			h_heal_powers[h] = {} # for action iterate later
			h_extra_powers[h] = {} # for action iterate later
			# for timing box plot
			timing = row['heal_timing']
			min_timing = min(min(timing),min_timing)
			max_timing = max(max(timing),max_timing)

			sup_timing_fig.add_trace(go.Box(
				y=timing,
				name=h,
				boxpoints='outliers',
				opacity=max(min(1,0.3+row['on heal float'])**2,0.4),
				line_width=4*row['on heal float'],
				boxmean=True,
				marker=dict(
					color=team_colour_map[row['team']],
					line_width=0,
					size = 4,
					)
			))

		for a, row in sup_heals.iterrows():
			hp = row['action'] # heal power
			h  = row['actor']
			if hp not in h_heal_powers[h]:
				h_heal_powers[h][hp] = 0
			if hp != 'Spirit Ward':
				h_heal_powers[h][hp] += 1


		for a, row in sup_extras.iterrows():
			hp = row['action'] # heal power
			h  = row['actor']
			if hp not in h_extra_powers[h]:
				h_extra_powers[h][hp] = 0
			h_extra_powers[h][hp] += 1


		sup_heal_fig = go.Figure()
		for h,hp in h_heal_powers.items():
			h_powers = list(hp.keys())
			h_powers.sort()
			for p in h_powers:
				colour = "grey"
				if p in render.heal_colours: colour = render.heal_colours[p]
				sup_heal_fig.add_trace(go.Bar(
					y=[hp[p]],
					x=[h],
					name=p,
					hovertemplate="<br>".join([p,str(hp[p])]),
					marker_color=colour,
					opacity=0.8,
				marker_line_width=2,
				marker_line_color='#222',
				))

		sup_extras_fig = go.Figure()
		for h,hp in h_extra_powers.items():
			hp = {k: v for k, v in sorted(hp.items(), key=lambda item: item[1],reverse=True)} # sort dict by value
			cs = 'teal'
			if hero_team_map[h] == 1: cs = 'burg' # colorscale
			sup_extras_fig.add_trace(go.Bar(
				y=list(hp.values()),
				x=[h]*len(hp),
				text=list(hp.keys()),
				# hovertemplate="<br>".join([h,str(hp[p])]),
				opacity=0.8,
				marker_line_width=2,
				marker_line_color='#222',
				marker={'color': list(hp.values())},
				marker_colorscale = cs,
			))

		sup_heals['hp_max']   = sup_heals['target'].map(lambda x: 0 if str(x)=='nan' or str(x)=='None' else hero_df.loc[x,'hp_max'])
		sup_heals['efficacy'] = sup_heals['hp_max'] - sup_heals['hit_hp']
		sup_heals['efficacy'] = sup_heals[(sup_heals['hp_max'] != 0)&(~sup_heals['action_tags'].str.contains('Absorb'))&(sup_heals['hit_hp'] != 0)]['efficacy']

		sup_eff_fig = go.Figure()
		
		hmax = 1
		if not sup_df.empty: 
			hmax = max(sup_df['heals'])

		for h in sup_heroes:
			hhero = sup_df.loc[h,'heals']
			sup_eff_fig.add_trace(go.Box(
				y=sup_heals[sup_heals['actor']==h]['efficacy'],
				name=h,
				boxpoints='outliers',
				opacity=0.8*hhero/hmax,
				line_width=3*hhero/hmax,
				boxmean=True,
				marker=dict(
					color=team_colour_map[hero_team_map[h]],
					line_width=0,
					size = 4,
					)
			))



		if sup_df.empty:
			st.write('no support heroes determined')
		else:
			c1,c2,c3,c4 = st.columns(4)
			row_height = 440
			if ss.mobile: 
				row_height = 240
			h_margins = dict(t=32, l=16, r=16, b=0)
			with c1:
				sup_timing_fig.update_layout(
					title_text='timing',
					height=row_height,
					margin = h_margins,
					showlegend=False,
					yaxis_title='first heal cast (s)',
					# yaxis={'range': [min_timing,min(6,max_timing)]},
					yaxis={'range': [0,min(6,max_timing)]},
					)
				st.plotly_chart(sup_timing_fig,use_container_width=True, config={'displayModeBar': False})

			with c2:
				sup_heal_fig.update_layout(
					title_text='heal powers',
					height=row_height,
					margin = h_margins,
					showlegend=False,
					barmode='stack',
					bargap=0.40,
					)
				st.plotly_chart(sup_heal_fig,use_container_width=True, config={'displayModeBar': False})


			with c3:
				sup_eff_fig.update_layout(
					title_text='hit efficacy (rough est.)',
					height=row_height,
					margin = h_margins,
					showlegend=False,
					yaxis_title='hp missing on hit',
					yaxis={'range': [1850,-5]},
					)
				st.plotly_chart(sup_eff_fig,use_container_width=True, config={'displayModeBar': False})
			
			with c4:
				sup_extras_fig.update_layout(
					title_text='extras',
					height=row_height,
					margin = h_margins,
					showlegend=False,
					barmode='stack',
					bargap=0.40,
					)
				st.plotly_chart(sup_extras_fig,use_container_width=True, config={'displayModeBar': False})


			sup_write = sup_df[['hero','at','set2','team','support','targets','on heal%','on heal','avg heal','med heal','var heal','alpha_heals',"phase hits","fat fingers","late","cms","heals","topups"]+opacities].copy()
			sup_write = sup_write.rename(columns={"targets":"tgtd","avg heal":"avg","med heal":"med","var heal":"variance","alpha_heals":"alpha","fat fingers":"ffs","topups":"top ups","on heal%":"on %"})
			# sup_write = sup_write.rename(columns={"targets":"tgtd","avg heal":"avg","med heal":"median","var heal":"variance","alpha_heals":"alpha","fat fingers":"ffs"})

			sup_gb = GridOptionsBuilder.from_dataframe(sup_write)
			sup_gb.configure_default_column(filterable=False,width=32,cellStyle={'text-align': 'center'},suppressMovable=True)
			# sup_gb.configure_columns('hero',width=96)
			sup_gb.configure_columns('hero',cellStyle=render.team_color,width=48,pinned='left')
			sup_gb.configure_columns('set2',cellStyle=render.support_color,width=44)
			sup_gb.configure_columns('at',cellRenderer=render.icon,width=32)
			sup_gb.configure_columns(['tgtd','on heal','alpha','phase hits','ffs','late',"cms","heals","top ups"],type='customNumericFormat',precision=0) # force render as string to remove hamburger menu
			sup_gb.configure_columns(['avg','med','variance'],type='customNumericFormat',precision=2)
			sup_gb.configure_columns(['team','support','variance','ffs']+opacities,hide=True)
			sup_gb.configure_columns(['on %'],cellStyle=render.onheal_bg)
			sup_gb.configure_columns(['on heal'],cellStyle=render.onhealn_bg)
			sup_gb.configure_columns(['tgtd'],cellStyle=render.targets_bg)
			sup_gb.configure_grid_options(headerHeight=64)
			
			sup_ag = AgGrid(
				sup_write,
				allow_unsafe_jscode=True,
				gridOptions=sup_gb.build(),
				fit_columns_on_grid_load= not ss.mobile,
				height = len(sup_df)*48+100,
				theme=table_theme
			)
	# END SUPPORT


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
		dmgpersurv,dmgperdeath = [],[]
		h_heals = []
		for h,row in hero_df.iterrows():
			dmg = sdf[sdf['target'] == h]['dmg'].sum()
			dmg_death = sdf[(sdf['target'] == h)&(sdf['kill'] == 1)]['dmg'].sum()
			dmg_surv = dmg - dmg_death
			h_dmg_spike.append(dmg)
			h_dmg_death.append(dmg_death)
			h_dmg_surv.append(dmg_surv)
			h_heals.append(actions_df[actions_df['target'] == h]['is_heal'].sum())

			d_surv = dmg_surv/(max(row['targets'] - row['deaths'],1))
			d_death = dmg_death/(max(row['deaths'],1))
			dmgpersurv.append(d_surv)
			dmgperdeath.append(d_death)

		hero_df['dmg_spike'] = h_dmg_spike
		hero_df['dmg_death'] = h_dmg_death
		hero_df['dmg_surv'] = h_dmg_surv
		hero_df['dmg/surv'] = dmgpersurv
		hero_df['dmg/death'] = dmgperdeath
		hero_df['dmg_surv'] = h_dmg_surv
		hero_df['nonspike_dmg'] = hero_df['damage_taken'] - hero_df['dmg_spike']
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
			t_dmg_death[t] /= max(c_deaths,1)


		for t in [0,1]:
			t2 = abs(t-1)

			c2.metric("dmg taken"*t2,millify(t_dmg[t],precision=1),millify((t_dmg[t]-t_dmg[t2])/1000,precision=1),delta_color="inverse")
			c3.metric("dmg/surv"*t2,millify(t_dmg_surv[t],precision=1),millify((t_dmg_surv[t]-t_dmg_surv[t2])/1000,precision=2),delta_color="inverse")
			c4.metric("dmg/death"*t2,  millify(t_dmg_death[t],precision=1),millify((t_dmg_death[t]-t_dmg_death[t2])/1000,precision=2),delta_color="inverse")


		# hp loss data
		@st.cache_data(show_spinner=False)
		def get_hp_data(sid,mid):
			with st.spinner("fetching HP data"):
				sqlq = util.str_sqlq('HP',ss.sid,ss.mid,['time_ms','hero','hp','hp_loss'])
				return pd.read_sql_query(sqlq, con)

		hp_df = get_hp_data(ss.sid,ss.mid).copy()
		if 'useplayernames' in ss and ss['useplayernames']:
			hp_df['hero'] = hp_df['hero'].map(hero_player_map)

		hero_df['dmg'] = hero_df['damage_taken']/1000
		hero_df['nonspike_dmg'] = hero_df['nonspike_dmg']/1000
		hero_df['dmg'] = hero_df['dmg'].map("{:0.1f}K".format)
		hero_df['nonspike_dmg'] = hero_df['nonspike_dmg'].map("{:0.1f}K".format)
		hero_df['dmg/surv'] = hero_df['dmg/surv'].map("{:0.0f}".format).map(lambda x: '' if x == '0' else x)
		hero_df['dmg/death'] = hero_df['dmg/death'].map("{:0.0f}".format).map(lambda x: '' if x == '0' else x)
		hero_write = hero_df[['team','hero','deaths','targets','surv','dmg','nonspike_dmg','dmg/surv','dmg/death','heals_taken','avg phase','avg jaunt']+opacities].copy()
		# hero_write = hero_write.fillna('')
		# hero_write['team'] = hero_write['team'].map(team_emoji_map)
		hero_write['avg jaunt'] = hero_write['avg jaunt'].fillna('')
		hero_write['avg phase'] = hero_write['avg phase'].fillna('')
		hero_write = hero_write.rename(columns={"nonspike_dmg":"nonspike dmg","dmg/surv":"dmg /surv","dmg/death":"dmg /death","heals_taken":"heals taken"})
		
		
		def_gb = GridOptionsBuilder.from_dataframe(hero_write)
		# type=["numericColumn","numberColumnFilter"], )
		def_gb.configure_default_column(filterable=False,width=64,cellStyle={'text-align': 'center'},suppressMovable=True)
		def_gb.configure_selection('multiple', pre_selected_rows=None)
		# def_gb.configure_columns(['avg phase','avg jaunt'],type='customNumericFormat',precision=2)
		def_gb.configure_columns(['dmg /surv','dmg /death','heals taken','deaths','targets'],type='customNumericFormat',precision=0)
		def_gb.configure_columns(['team']+opacities,hide=True)
		def_gb.configure_columns('hero',width=96,pinned='left')
		def_gb.configure_columns('hero',cellStyle=render.team_color)

		# opacities
		def_gb.configure_columns(['deaths'],cellStyle=render.deaths_bg)
		def_gb.configure_columns(['targets'],cellStyle=render.targets_bg)
		def_gb.configure_columns(['surv'],cellStyle=render.surv_bg)
		def_gb.configure_grid_options(headerHeight=64)


		def_ag = AgGrid(
			hero_write,
			allow_unsafe_jscode=True,
			gridOptions=def_gb.build(),
			fit_columns_on_grid_load= not ss.mobile,
			update_mode='SELECTION_CHANGED',
			height = 16*48+100,
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
					marker_symbol = 'x',
					marker_color='crimson',
					marker=dict(size=16,line=dict(width=0,color='crimson')),
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
					line=dict(color=team_colour_map[t], width=4),
				),row=1, col=1)
				hpl_fig.add_trace(go.Scatter(
					x=greens['time_m'],
					y=greens['greens'],
					name=team_name_map[t],
					mode='lines',
					line=dict(color=team_colour_map[t], width=4),
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
		c1,c2,c3,c4,c5,c6,c7 = st.columns([1,1,1,1,1,1,2])

		# split to only heroes with attack chains
		hdf = hero_df[(hero_df['attack_chains'] != "{}")].copy()

		ontgt = {}
		for i in [0,1]:
			ontgt[i] = hdf[hdf['team']==i]['on_target'].sum()/m_spikes[i]

		for t in [0,1]:
			t2 = abs(t-1)
			teamstring = """<p class="font40" style="color:{};">{}</p>""".format(team_colour_map[t],team_name_map[t],)
			c1.markdown(teamstring,True)
			c2.metric("Spikes Called"*t2,m_spikes[t],m_spikes[t]-m_spikes[t2])
			c3.metric("Attacks Thrown"*t2,m_attacks[t],m_attacks[t]-m_attacks[t2])
			c4.metric("Mean Timing"*t2,round(ht_mean[t],2),round(ht_mean[t]-ht_mean[t2],3),delta_color='inverse')
			c5.metric("Median Timing"*t2,round(ht_med[t],2),round(ht_med[t]-ht_med[t2],3),delta_color='inverse')
			c6.metric("Avg On Tgt"*t2,round(ontgt[t],1),round(ontgt[t]-ontgt[t2],2))


		with c7:
			hero_sel_st = st.sidebar.expander("⚔️ atk chain heroes",expanded=False)
			# st.markdown("""<p class="font20"" style="display:inline;color:#4d4d4d";>{}</p>""".format('attack chains'),True)

		c1,c2 = st.columns([2.5,1])
		with c1:
			# box plot for attack timing
			at_fig = make_subplots(rows=1,cols=2,column_widths=[0.7, 0.3],horizontal_spacing=0.05, shared_yaxes=True)
			total_timing = {0:[],1:[]}
			for h, row in hdf.iterrows():
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
				height=340 if not ss.mobile else 240,
				width=400,
				margin = dict(t=24, l=0, r=32, b=0),
				showlegend=False,
				yaxis_title='first atk timing (s)',
				xaxis={'fixedrange':True},
				yaxis={'range': [-2 ,5]},
				)
			st.plotly_chart(at_fig,use_container_width=True, config={'displayModeBar': False})

			
			# slice DF to new df for offence
			hero_write = hdf[['team','hero','targets','deaths','otp','on_target','avg atk','med atk','var atk','atks','offtgt','first_attacks']+opacities]
			hero_write = hero_write.rename(columns={"targets":'tgtd',"on_target": "on tgt","offtgt": "offtgt atk", "avg atk": "avg","med atk": "med","var atk": "var","first_attacks":'first'})
			hero_write = hero_write.sort_values(by='team')
			# hero_write['team'] = hero_write['team'].map(team_emoji_map)

			# aggrid options for offence table
			of_gb = GridOptionsBuilder.from_dataframe(hero_write)
			of_gb.configure_default_column(filterable=False,width=32,suppressMovable=True)
			of_gb.configure_grid_options(autoHeight=True)
			of_gb.configure_columns(['avg','med','var'],type='customNumericFormat',precision=2,width=36)
			of_gb.configure_columns(['on tgt','atks','offtgt atk','first','tgtd'],filterable=False,type='customNumericFormat',precision=0)
			of_gb.configure_columns('hero',width=60,pinned='left')
			of_gb.configure_columns('hero',cellStyle=render.team_color)
			of_gb.configure_columns(['deaths','team','var']+opacities,hide=True)

			of_gb.configure_columns(['tgtd'],cellStyle=render.targets_bg)
			of_gb.configure_columns(['otp'],cellStyle=render.otp_bg)
			of_gb.configure_columns(['ontgt'],cellStyle=render.ontgt_bg)

			of_gb.configure_selection('multiple', pre_selected_rows=None)

			of_ag = AgGrid(
				hero_write,
				allow_unsafe_jscode=True,
				gridOptions=of_gb.build(),
				fit_columns_on_grid_load= not ss.mobile,
				update_mode='SELECTION_CHANGED',
				height = len(hero_write)*48+64 if not ss.mobile else 320,
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
			ignore_missed = False
			if hero_sel == []:
				ignore_missed = True
				hero_sel = hero_df.index

			at_dicts = []
			max_length = 0
			for h in hero_sel:
				hteam  = hero_df.loc[h]['team']
				if ignore_missed:
					missed = 0 
				else:
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
			at_df['label'] = at_df['label'] + "<br>" + at_df['count'].astype(int).astype(str)
			# format center total to OTP or blank
			if len(hero_sel) == 1:
				hero = hero_sel[0]
				at_df.loc[at_df['id'] == 'Total', 'label'] = '<b>' + str(int(hero_df.loc[hero,'on_target'])) + ' (' + hero_df.loc[hero,'otp'] + ')</b>'
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
				height=300 if not ss.mobile else 240,
				)
			st.plotly_chart(ac_fig,use_container_width=True,config={'displayModeBar': False})
			st.caption('attack chains')

			## debugging table
			# at_df = at_df[['id','parent','count']]
			# st.table(at_df)

			# text chains for table display
			at_df['chain'] = at_df['id'].map(lambda x: x.replace("Total - ","").replace(" - "," → "))
			at_write = at_df[['chain','count']].sort_values(by='count',ascending=False)
			at_write = at_write[at_write['chain'] != 'Total']
			# chain to icons
			at_write['icons'] = at_write['chain'].map(lambda x: ' '.join([util.image_formatter('powers/' + powers[a]['icon']) for a in x.split(" → ")]))

			at_write = at_write.rename(columns={'count':'#'})
			at_write = at_write[['#','icons','chain']]

			at_gb = GridOptionsBuilder.from_dataframe(at_write)
			at_gb.configure_default_column(filterable=False,suppressMovable=True)
			at_gb.configure_columns('icons',cellRenderer=render.icon,width=40)
			at_gb.configure_columns('#',width=10,type='customNumericFormat',precision=0)
			at_gb.configure_columns('chain',width=40)
			# at_gb.configure_grid_options(headerHeight=0)


			sl_ag = AgGrid(
				at_write,
				allow_unsafe_jscode=True,
				gridOptions=at_gb.build(),
				# fit_columns_on_grid_load= not ss.mobile,
				fit_columns_on_grid_load= False,
				# height = 636 if not ss.mobile else 320,
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
			if not ss.mobile: st.plotly_chart(fig,use_container_width=True,config={'displayModeBar': False})


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
			filters = st.sidebar.expander('🔍 spike filters',expanded=False)
			spike_filters = {}
			with filters:
				spike_filters['players'] = st.multiselect('heroes',hero_list)
				spike_filters['team'] = st.radio('team',['all','blue','red'],horizontal=True)
				spike_filters['deaths'] = st.radio('deaths',['all','dead','alive'],horizontal=True)
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
			# sf['team'] = sf['team'].map(team_emoji_map)
			sf['kill'] = sf['kill'].map(kill_emoji_map)
			sf['dur'] = sf['dur'].map(lambda x: round(x/1000,1))


			sf_write = sf[['#','time','team','kill','target','dur','attacks','attackers','dmg']]
			sf_write = sf_write.rename(columns={'attacks':'atks','attackers':'atkr'})
			sf_gb = GridOptionsBuilder.from_dataframe(sf_write)
			sf_gb.configure_default_column(filterable=False,suppressMovable=True,width=54)
			sf_gb.configure_columns(['#','team','kill'],width=18)
			sf_gb.configure_columns(['atks','atkr','time'],width=64)
			sf_gb.configure_columns(['dur','dmg'],width=56)
			sf_gb.configure_columns(['target'],width=92,cellStyle=render.team_color)
			sf_gb.configure_columns('dur',type='customNumericFormat',precision=1)
			sf_gb.configure_columns(['dmg','atks','atkr'],type='customNumericFormat',precision=0,width=56)
			sf_gb.configure_columns('team',hide=True)
			sf_gb.configure_selection(selection_mode='single', pre_selected_rows=[0],suppressRowDeselection=True)

			# st.markdown("""<p class="font20"" style="display:inline;color:#4d4d4d";>{}</p>""".format('spike list'),True)
			st.caption("spike list")
			response = AgGrid(
				sf_write,
				allow_unsafe_jscode=True,
				gridOptions=sf_gb.build(),
				# data_return_mode="FILTERED_AND_SORTED",
				update_mode=GridUpdateMode.SELECTION_CHANGED,
				fit_columns_on_grid_load= not ss.mobile,
				height = 560 if not ss.mobile else 280,
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
			sl = actions_df[(actions_df['spike_id'] == spid)].copy()
			sl = sl.rename(columns={"time": "match_time", "spike_time": "cast", "spike_hit_time": "hit", "cast_dist": "dist"})

			# sl['actor_team'] = sl['actor'].map(hero_team_map)

			# times and target for spike hp log
			sp_target   = sdf.loc[spid-1,'target'] # spiketarget
			sp_delta   = sdf['start_delta'][spid-1]
			sp_start = sdf['time_ms'][spid-1]
			sp_end   = sdf['dur'][spid-1] + sp_start

			# columns for formatting spike log cells
			# actor/action color
			target_team = sdf[sdf['#']==spid]['team']
			target_team = target_team.iloc[0]
			sl['cell_color']  = sl['action_tags'].map(lambda x: 2 if 'Inspirations' in x else (3 if 'Teleport' in x else(4 if 'Phase\'' in x else (1 if 'Attack' in x else (0 if 'Heal' in x else 5)))))
			
			# hit time color
			sp_kill = sl[sl['action']=='Death']['hit_time']
			sp_kill_time = None
			if not sp_kill.empty:
				sp_kill_time = sp_kill.iloc[0]
			sl['hit_color'] = sl['hit_time'].map(lambda x: 1 if sp_kill_time and x>(sp_kill_time+120) else 0)
			
			act_min = min(sl['cast'].tolist())
			hit_max = max(sl['hit'].tolist())
			
			hp_start_time = min(sp_start - sp_delta,sp_start-act_min)
			hp_end_time   = max(sp_end+sp_delta+1000,sp_start+hit_max+sp_delta+1000)
			str_target = str(sp_target).replace('\'','\'\'')
			sqlq = util.str_sqlq('HP',ss.sid,ss.mid,["hero","time_ms","hp","hp_loss"],f"AND hero='{str_target}' AND time_ms>={hp_start_time} AND time_ms<={hp_end_time}")
			sp_hp_df = pd.read_sql_query(sqlq, con)
			if ss['useplayernames']:
				sp_hp_df['hero'] = sp_hp_df['hero'].map(hero_player_map)
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
			sl['hit_hp'] = sl['hit_hp'].fillna(-1).astype(int).astype(object).replace(-1,pd.NA)
			sl['dist'] = sl['dist'].fillna(-1).astype(int).astype(object).replace(-1,pd.NA)
			sl['icon_path'] = 'powers/'+sl['icon']
			sl['image'] = sl['icon_path'].apply(util.image_formatter)
			sl_write = sl[['cast','actor','image','action','hit','dist','cell_color','hit_color']]   
			sl_write = sl_write.fillna('')

			# color action markers by type
			acolours = []
			for t in sl['action_tags']:
				tags = ast.literal_eval(t)
				if 'Inspirations' in tags:
					acolours.append('GreenYellow')
				elif 'Attack' in tags:
					acolours.append('crimson')
				elif 'Phase' in tags:
					acolours.append('DeepSkyBlue')
				elif 'Heal' in tags:
					acolours.append('limegreen')
				elif 'Teleport' in tags:
					acolours.append('gold')
				else:
					acolours.append('Grey')

			# add action markers to HP graph
			# add white line as background color workaround

			hp_y_max = max(sp_hp_df['hp'].max(),sp_hp_df['hp_loss'].max(),2000)
			hp_range=[act_min,hit_max]

			y_cast,y_hit = 1.6,0.6
			sp_fig.add_trace(go.Scatter(x=[hp_range[0]-1,1+max(hp_range[1],max(sl['hit']))],y= [4,4],fill='tozeroy', mode='none',fillcolor='white',
				),row=2, col=1)

			## line between cast and hit but looks kinda ugly
			# i = 0
			# for a,row in sl.iterrows():
			# 	sp_fig.add_trace(go.Scatter(
			# 		x=[row['cast'],row['hit']],
			# 		y=[y_cast,y_hit],
			# 		name='',
			# 		mode='lines',
			# 		line=dict(color=acolours[i], width=2),
			# 		opacity=0.15,
			# 	),row=2, col=1)
			# 	i += 1

			sp_fig.add_trace(go.Scatter(
				x=sl['cast'],
				y=[y_cast]*len(sl['cast']),
				name='',
				text=sl['actor']+"<br>"+sl['action'],
				marker_color=acolours,
				marker=dict(size=12,line=dict(width=2,color='DarkSlateGrey')),
				mode='markers',
				hovertemplate = "<b>cast time</b> <br>%{text}"
			),row=2, col=1)
			sp_fig.add_trace(go.Scatter(
				x=sl['hit'],
				y=[y_hit]*len(sl['cast']),
				name='',
				text=sl['actor']+"<br>"+sl['action'],
				marker_color=acolours,
				marker=dict(size=12,line=dict(width=2,color='DarkSlateGrey')),
				# opacity=0.5,
				mode='markers',
				hovertemplate = "<b>hit time</b> <br>%{text}"
			),row=2, col=1)

			sp_fig.update_layout(
				height=250,
				showlegend=False,
				xaxis={'range':hp_range},
				margin={'t': 0,'b':40,'l':48,'r':0},
				# plot_bgcolor='rgba(0,0,0,0)',
			)
			sp_fig.update_xaxes(title_text="spike time (s)", row=2, col=1, showgrid=False)
			sp_fig.update_yaxes(visible=True, fixedrange=True, showgrid=True, title='hp',range=[0,hp_y_max],row=1, col=1)
			sp_fig.update_yaxes(visible=False, fixedrange=True, showgrid=False,range=[0,2],title='hit/cast',row=2, col=1)

			st.plotly_chart(sp_fig, use_container_width=True,config={'displayModeBar': False})

			sl_gb = GridOptionsBuilder.from_dataframe(sl_write)
			sl_gb.configure_default_column(filterable=False,suppressMovable=True,width=48)
			sl_gb.configure_columns('actor',width=80)
			sl_gb.configure_columns('action',width=64)
			# sl_gb.configure_columns(['cast'],width=48)
			sl_gb.configure_columns(['cast','hit'],type='customNumericFormat',precision=2)
			sl_gb.configure_columns('image',cellRenderer=render.icon,width=44)
			sl_gb.configure_columns(['actor','action'],cellStyle=render.spike_action_color)
			sl_gb.configure_columns(['hit'],cellStyle=render.spike_hit_color)
			sl_gb.configure_columns(['cell_color','hit_color'],hide=True)

			# st.markdown("""<p class="font20"" style="display:inline;color:#4d4d4d";>{}</p>""".format('spike log: #' + str(spid)),True)
			st.caption(f"spike log #{spid}")
			# st.caption(f"spike log: #{str(spid)}")
			sl_ag = AgGrid(
				sl_write,
				allow_unsafe_jscode=True,
				gridOptions=sl_gb.build(),
				fit_columns_on_grid_load= not ss.mobile,
				height = 560,
				theme=table_theme,
				enable_enterprise_modules=False
			)
	# END SPIKES


	# START LOGS
	elif ss.view['match'] == 'logs':
		
		c1,c3 = st.columns([4,6])
		a_df = actions_df.copy()
		a_df['hit'] = a_df['hit_time'] - a_df['time_ms']
		a_df['hit'] = a_df['hit']/1000

		with c1:
			# st.markdown("""<p class="font20"" style="color:#4d4d4d";>{}</p>""".format('filters'),True)
			with st.expander('🔍 filters',expanded=False):
				with st.form('log filters'):
					# list filters
					# time bounds
					t_start,t_end = st.slider('timing bounds (m)', min_value=0.0, max_value=10.0, value=(0.0,10.0), step=0.25, format=None)
					# t_end = st.slider('', min_value=0.0, max_value=10.0, value=10.0, step=0.25, format=None)
					t_start = min(t_start,t_end)*1000*60
					t_end = max(t_start,t_end)*1000*60

					# action toggles
					a_filtertoggle = st.checkbox('show self toggles',value=False)
					a_spikes = st.checkbox('show spike actions',value=True)
					a_nonspikes = st.checkbox('show non-spike actions',value=True)

					a_actor_team = st.radio('caster team',['all','blu','red'],horizontal=True)
					a_target_team = st.radio('target team',['all','blu','red'],horizontal=True)

					st.form_submit_button('apply filters')

			with st.expander('🧮 counts',expanded=True):
				counts_heroes = st.multiselect('heroes',hero_list)
				power_list = a_df['action'].unique().tolist()
				power_list.sort()
				counts_powers = st.multiselect('powers',power_list)

				col1,col2,col3,col4 = [],[],[],[] # hero icon power count
				for h in counts_heroes:
					for p in counts_powers:
						count = len(a_df[(a_df['actor']==h)&(a_df['action']==p)])
						if count>0:
							col1.append(h)
							image_path = 'powers/' + a_df.loc[a_df['action']==p,'icon'].iloc[0]
							image = util.image_formatter(image_path)
							col2.append(image)
							col3.append(p)
							col4.append(count)
				count_df = data = pd.DataFrame({'hero': col1, 'image': col2,'power':col3,'#':col4})
				if len(count_df)>0:
					count_gb = GridOptionsBuilder.from_dataframe(count_df)
					count_gb.configure_columns('image',cellRenderer=render.icon)
					count_ag = AgGrid(
						count_df,
						allow_unsafe_jscode=True,
						fit_columns_on_grid_load= not ss.mobile,
						gridOptions=count_gb.build(),
						theme=table_theme,
						height = len(count_df)*48+64,
						enable_enterprise_modules=False
					)

			# apply filters
			if not a_filtertoggle:
				a_df = a_df.loc[~((a_df['action_type'] == 'Toggle')&(a_df['action_target_type'] == 'Self'))]
			if not a_spikes:
				a_df = a_df.loc[(~a_df['spike_id'].notnull())]
			if not a_nonspikes:
				a_df = a_df.loc[(a_df['spike_id'] > 0)]

			if not a_nonspikes:
				a_df = a_df.loc[(a_df['spike_id'] > 0)]
			a_df = a_df.loc[(a_df['time_ms'] >= t_start) & (a_df['time_ms'] <= t_end)]

		with c3:

			# icons
			a_df['icon_path'] = 'powers/'+a_df['icon']
			a_df['image'] = a_df['icon_path'].apply(util.image_formatter)

			# team emojis
			a_df['team'] = a_df['actor'].map(hero_team_map)
			a_df['target_team'] = a_df['target'].map(hero_team_map)

			if a_actor_team == 'blu':
				a_df = a_df[a_df['team'] == 0]
			elif a_actor_team == 'red':
				a_df = a_df[a_df['team'] == 1]
			if a_target_team == 'blu':
				a_df = a_df[a_df['target_team'] == 0]
			elif a_actor_team == 'red':
				a_df = a_df[a_df['target_team'] == 1]

			actions_write = a_df[['time','team','actor','image','action','target_team','target']]
			actions_write = actions_write.rename(columns={"time":'cast'})
			actions_write['target'] = actions_write['target'].fillna('')

			al_gb = GridOptionsBuilder.from_dataframe(actions_write)
			al_gb.configure_default_column(width=84,suppressMovable=True)
			al_gb.configure_columns(['actor','target','action'],width=84)
			al_gb.configure_columns(['cast','image'],width=52)
			al_gb.configure_columns(['team','target_team'],hide=True)
			al_gb.configure_columns('image',cellRenderer=render.icon)
			al_gb.configure_columns('actor',cellStyle=render.team_color)
			al_gb.configure_columns('target',cellStyle=render.target_team_color)
			al_gb.configure_pagination(paginationAutoPageSize=False,paginationPageSize=100)

			al_ag = AgGrid(
				actions_write,
				allow_unsafe_jscode=True,
				gridOptions=al_gb.build(),
				fit_columns_on_grid_load= not ss.mobile,
				height = 1024,
				theme=table_theme,
				enable_enterprise_modules=False
			)
	# END LOGS


	# START SERIES
	elif ss.view['match'] == 'series':
		m_df = ss.matches[ss.matches['series_id']==ss.sid].copy()

		m_write = m_df[['match_id','map','score0','score1']]

		nspike_dict = {}
		nspike_dict[0] = dict(zip(m_df['match_id'],m_df['spikes0']))
		nspike_dict[1] = dict(zip(m_df['match_id'],m_df['spikes1']))

		m_gb = GridOptionsBuilder.from_dataframe(m_write)
		m_gb.configure_default_column(width=16)
		# m_gb.configure_grid_options(rowHeight=36)
		m_gb.configure_columns('map',width=42)
		m_gb.configure_columns('score0',cellStyle=render.blu)
		m_gb.configure_columns('score1',cellStyle=render.red)
		m_gb.configure_grid_options(headerHeight=0)

		# m_gb.configure_selection('single', pre_selected_rows=None)


		c1,c2 = st.columns([4,6])

		with st.sidebar.expander('🔧 data table settings',expanded=False):
			name_toggle    = st.radio('group by',['player name','hero name'],horizontal=True)
			data_aggr      = st.radio('show data by',['total for series','avg/match'],help='applies applicable data',horizontal=True)
			support_toggle = st.radio('role',['all','offence','support'],horizontal=True)

		with c1:

			st.markdown("""<p class="font20"" style="display:inline;color:#4d4d4d";>{}</p><br>""".format('matches'),True)
			m_write = m_write.sort_values(by='match_id')
			m_ag = AgGrid(
				m_write,
				allow_unsafe_jscode=True,
				gridOptions=m_gb.build(),
				# update_mode='SELECTION_CHANGED',
				fit_columns_on_grid_load= not ss.mobile,
				height = 240,
				theme=table_theme,
				enable_enterprise_modules=False
			)

		with c2:
			series_fig =   make_subplots(specs=[[{"secondary_y": True}]])
			m_write['x'] =   m_write['match_id'].astype(str) + " (" + m_write['map'] +  ")"
			series_fig.add_trace(
				go.Bar(x=m_write['x'], y=m_write['score0'], name="blu", marker_color='dodgerblue',
					), secondary_y=False
			)
			series_fig.add_trace(
					go.Bar(x=m_write['x'], y=m_write['score1'], name="red",marker_color='tomato',
					), secondary_y=False
			)

			series_fig.update_layout(
				showlegend=False,
				height=240 if not ss.mobile else 120,
				margin={'t': 0,'b':0,'l':64,'r':0},
				yaxis_title='score',
				bargap=0.50,
			)
			st.plotly_chart(series_fig,use_container_width=True,config={'displayModeBar': False})

		# st.write('data columns')
		available_data = ['deaths','targets','surv','damage_taken','attacks','heals']
		default_sel = ['deaths','targets','surv','otp','on heal%','damage_taken','attacks']
		target_data = ['otp','on heal%','on_target','on_heal']
		timing_data = ['attack mean','attack median','attack variance','heal mean','heal median','heal variance','phase mean','phase median','jaunt mean','jaunt median']
		count_data  = ['first_attacks','alpha_heals','phases','jaunts','greens']
		dmg_data    = ['dmg/spike (est)']
		record_data = ['win','loss','tie']
		available_data += target_data + timing_data + count_data + dmg_data + record_data
		show_data = st.multiselect('data columns (settings in sidebar)',available_data,default=default_sel)

		# get hero data for all matches
		sqlq = util.str_sqlq('Heroes',ss.sid)
		mh_df = pd.read_sql_query(sqlq, con)

		# toggles for viewing data by
		table_title = 'heroes'
		if name_toggle == 'player name':
			table_title = 'players'
			mh_df['player_name'] = mh_df.apply(lambda x: x['hero'] if not x['player_name'] else "@"+x['player_name'], axis=1)
			mh_df['hero'] = mh_df['player_name']
		table_title += " (" + data_aggr + ")"


		# initial toggle filters
		if support_toggle == 'support':
			mh_df = mh_df[mh_df['support']==1]
		elif support_toggle == 'offence':
			mh_df = mh_df[~(mh_df['support']==1)]

		# setup player table
		mh_write = mh_df.groupby('hero')[['match_id']].count().copy()
		mh_write['player'] = mh_write.index
		mh_write['#matches'] = mh_df.groupby('hero')[['match_id']].count()

		# str lists to lists
		mh_df['attack_timing']= mh_df['attack_timing'].map(lambda x: (ast.literal_eval(x)))
		mh_df['heal_timing']  = mh_df['heal_timing'].map(lambda x: (ast.literal_eval(x)))
		mh_df['phase_timing'] = mh_df['phase_timing'].map(lambda x: (ast.literal_eval(x)))
		mh_df['jaunt_timing'] = mh_df['jaunt_timing'].map(lambda x: (ast.literal_eval(x)))

		# on targets
		mh_df['on_target'] = mh_df['attack_timing'].map(lambda x: len(x) - sum(config['otp_penalty'] for t in x if t > config['otp_threshold']))
		mh_df['on_heal'] = mh_df['heal_timing'].map(lambda     x: len(x) - sum(config['ohp_penalty'] for t in x if t > config['ohp_threshold']))
		mh_df['on_target_possible'] = mh_df.apply(lambda x: nspike_dict[x['team']][x['match_id']] if (x['support'] != 1 or support_toggle != 'all') else 0, axis=1)
		mh_df['on_heal_possible'] = mh_df.apply(lambda x: nspike_dict[abs(1-x['team'])][x['match_id']]-x['targets'] if (x['support'] == 1 or support_toggle != 'all') else 0, axis=1)

		# group by player
		mh_write['attack_timing']= mh_df.groupby('hero').agg({'attack_timing': 'sum'})
		mh_write['heal_timing']  = mh_df.groupby('hero').agg({'heal_timing': 'sum'})
		mh_write['phase_timing'] = mh_df.groupby('hero').agg({'phase_timing': 'sum'})
		mh_write['jaunt_timing'] = mh_df.groupby('hero').agg({'jaunt_timing': 'sum'})

		# convert ms to s
		mh_write['attack_timing']= mh_write['attack_timing'].map(lambda x: [a/1000 for a in x])
		mh_write['phase_timing'] = mh_write['phase_timing'].map(lambda x: [a/1000 for a in x])
		mh_write['jaunt_timing'] = mh_write['jaunt_timing'].map(lambda x: [a/1000 for a in x])
		mh_write['heal_timing']   = mh_write['heal_timing'].map(lambda x: [a/1000 for a in x])

		# calc mean,median,vars
		mh_write['attack mean']     = mh_write['attack_timing'].map(lambda x: statistics.mean([abs(v) for v in x]) if len(x) > 0 else None)
		mh_write['attack median']   = mh_write['attack_timing'].map(lambda x: statistics.median(x) if len(x) > 0 else None)
		mh_write['attack variance'] = mh_write['attack_timing'].map(lambda x:  statistics.variance(x)  if len(x) > 1 else 0)

		mh_write['phase mean']   = mh_write['phase_timing'].map(lambda x: statistics.mean(x) if len(x) > 0 else None)
		mh_write['phase median'] = mh_write['phase_timing'].map(lambda x: statistics.median(x) if len(x) > 0 else None)
		mh_write['jaunt mean']   = mh_write['jaunt_timing'].map(lambda x: statistics.mean(x) if len(x) > 0 else None)
		mh_write['jaunt median'] = mh_write['jaunt_timing'].map(lambda x: statistics.median(x) if len(x) > 0 else None)

		mh_write['heal mean']     = mh_write['heal_timing'].map(lambda x: statistics.mean(x) if len(x) > 0 else None)
		mh_write['heal median']   = mh_write['heal_timing'].map(lambda x: statistics.median(x) if len(x) > 0 else None)
		mh_write['heal variance'] = mh_write['heal_timing'].map(lambda x: statistics.variance(x) if len(x) > 1 else None)

		# otps	
		otp_cols = ['on_target','on_heal','on_target_possible','on_heal_possible']
		mh_write[otp_cols] = mh_df.groupby('hero')[otp_cols].sum()
		mh_write['otp'] = mh_write['on_target']/mh_write['on_target_possible']
		mh_write['on heal%'] = mh_write['on_heal']/mh_write['on_heal_possible']

		mh_write['otp'] = mh_write['otp'].map("{:.0%}".format).map(lambda x: '' if (x == '0%' or x == 'nan%' or x == 'inf%') else x)
		mh_write['on heal%'] = mh_write['on heal%'].map("{:.0%}".format).map(lambda x: '' if (x == '0%' or x == 'nan%' or x == 'inf%') else x)



		# get data by mean or total
		sum_or_avg = ['deaths','targets','damage_taken','attacks','heals','on_target','on_heal']
		sum_or_avg += count_data + record_data
		if data_aggr == 'avg/match':
			mh_write[sum_or_avg] = mh_df.groupby('hero')[sum_or_avg].mean()
		else:
			mh_write[sum_or_avg] = mh_df.groupby('hero')[sum_or_avg].sum()

		mh_write['dmg/spike (est)'] = 0.8*mh_write['damage_taken']/mh_write['targets']
		mh_write['damage_taken'] = mh_write['damage_taken'].map(lambda x: x/1000).map("{:0.1f}K".format)
		
		# calc overall stats
		mh_write['surv'] = 1-mh_write['deaths']/mh_write['targets'] 
		mh_write['surv'] = mh_write['surv'].map("{:.0%}".format)
		mh_write['surv'] = mh_write['surv'].map(lambda x: '' if x == 'nan%' else x)

		mh_write = mh_write.fillna('')

		# if data_aggr == 'avg/match':
		# 	mh_write['deaths'] = mh_write['deaths'].map("{:0.1f}".format)
		# 	mh_write['targets'] = mh_write['targets'].map("{:0.1f}".format)

		mh_write = mh_write[['player','#matches']+available_data]
		hide_data = [d for d in available_data if d not in show_data]
		# mh_write = mh_df[['hero','#matches','deaths','targets','surv','dmg','otp','avg t']]
		mh_gb = GridOptionsBuilder.from_dataframe(mh_write)
		# mh_gb.configure_side_bar()
		mh_gb.configure_default_column(width=32,cellStyle={'text-align': 'center'},filterable=False,suppressMovable=True)
		mh_gb.configure_columns('player',width=64,cellStyle={'text-align': 'left','font-weight':'bold'},pinned='left')
		mh_gb.configure_columns(['attacks','heals','on_target','on_heal'],type='customNumericFormat',precision=0)
		mh_gb.configure_columns(timing_data,type='customNumericFormat',precision=2)
		mh_gb.configure_columns(count_data+dmg_data,type='customNumericFormat',precision=0)
		mh_gb.configure_columns(hide_data,hide=True)
		if data_aggr == 'avg/match':
			mh_gb.configure_columns(['deaths','targets']+count_data+dmg_data,type='customNumericFormat',precision=1)
			mh_gb.configure_columns(record_data,type='customNumericFormat',precision=2)

		st.markdown("""<p class="font20"" style="display:inline;color:#4d4d4d";>{}</p><br>""".format(table_title),True)
		mh_ag = AgGrid(
			mh_write,
			allow_unsafe_jscode=True,
			gridOptions=mh_gb.build(),
			# enable_enterprise_modules=True,
			# update_mode='SELECTION_CHANGED',
			# fit_columns_on_grid_load= not ss.mobile,
			height = 680 if not ss.mobile else 320,
			theme=table_theme,
			enable_enterprise_modules=False
		)
	# END SERIES
	
# end match viewer