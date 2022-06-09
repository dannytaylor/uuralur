import sys,sqlite3,os,ast,yaml,statistics,inspect,json

# to allow running outside of streamlit
# run from project root
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 

import pandas as pd
import numpy as np
import tools.util as util
import tools.render as render


db_file = "demos.db"
config = yaml.safe_load(open('data/config.yaml'))
cache_folder = '.cache'


import streamlit as st

# @st.cache(show_spinner=False)
def init_match(sid,mid,upload=False,batch=False,force=False):

	con = sqlite3.connect(db_file)
	
	cache_file = "/".join([cache_folder,str(sid),str(mid)+".db"])

	# if cache already exists
	if batch and "upload" in sid:
		return
	if os.path.isfile(cache_file) and not force:
		if batch: 
			print(f'already exists {sid} {mid}')
			return
		# if it does, just grab the init data from the pickle
		# need to be careful preserving order if changes made

		cache_con 	= sqlite3.connect(cache_file)
		sqlq 	= util.str_sqlq('hero_df',sid,mid)
		hero_df = pd.read_sql_query(sqlq, cache_con)

		# check if cache current via player list
		sqlq = util.str_sqlq('Heroes',sid,mid)
		hero_df_check = pd.read_sql_query(sqlq, con)['player_name']
		# if current pickle from old version of player_names.json assume needs rerunning, otherwise OK
		if set(hero_df['player_name'])!= set(hero_df_check):
			print(f"regenerating cache {sid} {mid}")
			init_match(sid,mid,force=True)

		sqlq 		= util.str_sqlq('actions_df')
		actions_df 	= pd.read_sql_query(sqlq, cache_con)

		sqlq 		= util.str_sqlq('sdf')
		sdf 		= pd.read_sql_query(sqlq, cache_con)

		sqlq 		= util.str_sqlq('match_data')
		match_data	= pd.read_sql_query(sqlq, cache_con)
		m_score 	= match_data.loc[0, :].values.tolist()
		m_spikes 	= match_data.loc[1, :].values.tolist()
		m_attacks 	= match_data.loc[2, :].values.tolist()

		sqlq 		= util.str_sqlq('t_spikes0')
		t_spikes0 	= pd.read_sql_query(sqlq, cache_con)
		sqlq 		= util.str_sqlq('t_spikes1')
		t_spikes1 	= pd.read_sql_query(sqlq, cache_con)
		t_spikes 	= {0:t_spikes0,1:t_spikes1}

		sqlq 		= util.str_sqlq('t_kills0')
		t_kills0 	= pd.read_sql_query(sqlq, cache_con)
		sqlq 		= util.str_sqlq('t_kills1')
		t_kills1 	= pd.read_sql_query(sqlq, cache_con)
		t_kills 	= {0:t_kills0,1:t_kills1}

		t_dmg 		= match_data.loc[3, :].values.tolist()
		ht_mean 	= match_data.loc[4, :].values.tolist()
		ht_med 		= match_data.loc[5, :].values.tolist()

	# otherwise if no cache file already, create one for first run
	else:
		with st.spinner("running first time match setup..."):
			print(f'generating cache {sid} {mid}')

			os.makedirs(os.path.dirname(cache_file), exist_ok=True)
			cache_con 	= sqlite3.connect(cache_file)

			matches = pd.read_sql_query("SELECT * FROM Matches", con)
			match_row = matches[(matches['match_id']==mid)&(matches['series_id']==sid)]
			m_score  = [int(match_row.iloc[0]['score0']),int(match_row.iloc[0]['score1'])]
			m_spikes = [int(match_row.iloc[0]['spikes0']),int(match_row.iloc[0]['spikes1'])]

			sqlq = util.str_sqlq('Heroes',sid,mid)
			hero_df = pd.read_sql_query(sqlq, con)
			hero_df = hero_df.sort_values(by='team')

			sqlq = util.str_sqlq('Actions',sid,mid)
			actions_df = pd.read_sql_query(sqlq, con)
			actions_df['time'] = pd.to_datetime(actions_df['time_ms'],unit='ms').dt.strftime('%M:%S.%f').str[:-4]
			actions_df['time_m'] = actions_df['time_ms']/60000

			# hero stats on target and timing
			# offense
			hero_df['timing']  = hero_df['attack_timing'].map(lambda x: (ast.literal_eval(x)))
			hero_df['on_target']  = hero_df['timing'].map(lambda x: len(x) - sum(config['otp_penalty'] for t in x if t > config['otp_threshold'])) 
			hero_df['timing']  = hero_df['timing'].map(lambda x: [a/1000 for a in x])
			hero_df['avg atk'] = hero_df['timing'].map(lambda x: statistics.mean([abs(v) for v in x]) if len(x) > 0 else None)
			hero_df['med atk'] = hero_df['timing'].map(lambda x: statistics.median(x) if len(x) > 0 else None)
			hero_df['var atk'] = hero_df['timing'].map(lambda x:  statistics.variance(x)  if len(x) > 1 else 0)
			hero_df['max_targets'] = hero_df['team'].map(lambda x: m_spikes[x])

			# defense
			hero_df['phase_timing'] = hero_df['phase_timing'].map(lambda x: (ast.literal_eval(x)))
			hero_df['n_phases']     = hero_df['phase_timing'].map(lambda x: len(x))
			hero_df['phase_timing'] = hero_df['phase_timing'].map(lambda x: [a/1000 for a in x]) 
			hero_df['avg phase']    = hero_df['phase_timing'].map(lambda x: statistics.mean(x) if len(x) > 0 else None)
			hero_df['avg phase']    = hero_df['avg phase'].map("{:0.2f}".format).astype(str) + " (" + hero_df['n_phases'].astype(str) + ")"
			hero_df['avg phase']    = hero_df['avg phase'].map(lambda x: '' if 'nan' in x else x)
			hero_df['jaunt_timing'] = hero_df['jaunt_timing'].map(lambda x: (ast.literal_eval(x)))
			hero_df['n_jaunts']     = hero_df['jaunt_timing'].map(lambda x: len(x))
			hero_df['jaunt_timing'] = hero_df['jaunt_timing'].map(lambda x: [a/1000 for a in x])
			hero_df['avg jaunt']    = hero_df['jaunt_timing'].map(lambda x: statistics.mean(x) if len(x) > 0 else None)
			hero_df['avg jaunt']    = hero_df['avg jaunt'].map("{:0.2f}".format).astype(str) + " (" + hero_df['n_jaunts'].astype(str) + ")"
			hero_df['avg jaunt']    = hero_df['avg jaunt'].map(lambda x: '' if 'nan' in x else x)

			# support
			hero_df['heal_timing'] = hero_df['heal_timing'].map(lambda x: ast.literal_eval(x))
			hero_df['on heal']     = hero_df['heal_timing'].map(lambda x: len(x)  - sum(config['ohp_penalty'] for t in x if t > config['ohp_threshold']))
			hero_df['heal_timing'] = hero_df['heal_timing'].map(lambda x: [a/1000 for a in x])
			hero_df['avg heal']    = hero_df['heal_timing'].map(lambda x: statistics.mean(x) if len(x) > 0 else None)
			hero_df['med heal']    = hero_df['heal_timing'].map(lambda x: statistics.median(x) if len(x) > 0 else None)
			hero_df['var heal']    = hero_df['heal_timing'].map(lambda x: statistics.variance(x) if len(x) > 1 else None)
			hero_df['on heal divisor'] = hero_df['team'].map(lambda x: m_spikes[abs(x-1)]) - hero_df['targets']
			hero_df['on heal float']   = hero_df['on heal']/hero_df['on heal divisor']
			

			# summary
			hero_df['otp_float']  	= hero_df['on_target'] / hero_df['max_targets']
			hero_df['otp']        	= hero_df['otp_float'].map("{:.0%}".format)
			hero_df['otp']        	= hero_df['otp'].map(lambda x: '' if x == '0%' else x) 
			hero_df['on heal%']    	= hero_df['on heal float'].map("{:.0%}".format)
			hero_df['on heal%']	   	= hero_df['on heal%'].map(lambda x: '' if x == '0%' else x)
			hero_df['surv_float'] 	= 1-hero_df['deaths']/hero_df['targets']
			hero_df['surv'] 		= hero_df['surv_float'].map("{:.0%}".format)
			hero_df['surv'] 		= hero_df['surv'].map(lambda x: '' if x == 'nan%' else x)

			hero_df['set1'] 		= hero_df['set1'].map(lambda x: '-' if x == None else x)
			hero_df['set2'] 		= hero_df['set2'].map(lambda x: '-' if x == None else x)
			hero_df['icon_at'] 		= hero_df['archetype'].map(lambda x: render.spacer_base64 if x == None else util.image_formatter("archetypes/"+x.replace('/','.')+'.png')) # placeholder if none
			# hero_df['icon_set1'] = hero_df['set1'].map(lambda x: util.image_formatter("powers/"+pset_icons.icon_map[x]) if x in pset_icons.icon_map else render.spacer_base64) # placeholder if none
			# hero_df['icon_set2'] = hero_df['set2'].map(lambda x: util.image_formatter("powers/"+pset_icons.icon_map[x]) if x in pset_icons.icon_map else render.spacer_base64) # placeholder if none
			# hero_df['set1'] = hero_df['icon_set1'] + "  " + hero_df['set1']
			# hero_df['set2'] = hero_df['icon_set2'] + "  " + hero_df['set2']

			hero_df['at'] = hero_df['icon_at']
			# hero_df['at'] = hero_df['icon_at'] + " " + hero_df['icon_set1']  + " " + hero_df['icon_set2']

			# computed opacities for styling
			hero_df['deaths_opacity'] = 0.2*(hero_df['deaths']/max(hero_df['deaths']))**1.5
			hero_df['targets_opacity'] = 0.2*(hero_df['targets']/max(hero_df['targets']))**1.5
			hero_df['otp_opacity'] = 0.2*hero_df['otp_float']**3
			hero_df['ontgt_opacity'] = 0.15*(hero_df['on_target']/max(hero_df['on_target']))**2
			hero_df['onheal_opacity'] = 0.5*hero_df['on heal float']**2.5
			hero_df['onhealn_opacity'] = 0.15*(hero_df['on heal']/max(hero_df['on heal']))**3
			hero_df['surv_opacity'] = 0.1*hero_df['surv_float']**1.5

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

			hero_df['index'] = hero_df['hero']
			hero_df = hero_df.set_index('index') 
			
			# get spike data for match
			sqlq = util.str_sqlq('Spikes',sid,mid)
			sdf = pd.read_sql_query(sqlq, con)
			sdf = sdf.rename(columns={"spike_duration": "dur", "spike_id": "#","spike_hp_loss": "dmg","target_team": "team"})
			sdf['time'] = pd.to_datetime(sdf['time_ms'],unit='ms').dt.strftime('%M:%S')
			sdf['time_m'] = sdf['time_ms']/60000

			m_attacks = {}
			m_attacks[0] = int(hero_df[hero_df['team'] == 0]['atks'].sum())
			m_attacks[1] = int(hero_df[hero_df['team'] == 1]['atks'].sum())

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
		
			# convert to str
			stringify = ['attack_chains','attack_timing','phase_timing','heal_timing','jaunt_timing','timing']
			for i in stringify:
				hero_df[i] = hero_df[i].map(lambda x: str(x))

			hero_df.to_sql("hero_df",cache_con,if_exists='replace')
			actions_df.to_sql("actions_df",cache_con,if_exists='replace')
			sdf.to_sql("sdf",cache_con,if_exists='replace')

			t_spikes[0].to_sql("t_spikes0",cache_con,if_exists='replace')
			t_spikes[1].to_sql("t_spikes1",cache_con,if_exists='replace')
			t_kills[0].to_sql("t_kills0",cache_con,if_exists='replace')
			t_kills[1].to_sql("t_kills1",cache_con,if_exists='replace')

			match_data = {}
			for i in [0,1]:
				match_data[i] = [m_score[i],m_spikes[i],m_attacks[i],t_dmg[i],ht_mean[i],ht_med[i]]
			match_data = pd.DataFrame.from_dict(match_data)
			match_data.to_sql("match_data",cache_con,if_exists='replace')

	# unconvert from str
	stringify = ['attack_timing','phase_timing','heal_timing','jaunt_timing','timing']
	for i in stringify:
		hero_df[i] = hero_df[i].map(lambda x: ast.literal_eval(x))

	return hero_df,actions_df,sdf,m_score,m_spikes,m_attacks,t_spikes,t_kills,t_dmg,ht_mean,ht_med


def main():
	con = sqlite3.connect(db_file)
	matches = pd.read_sql_query("SELECT * FROM Matches", con)
	series = pd.read_sql_query("SELECT * FROM Series", con)
	for sid in series['series_id']:
		mids = pd.read_sql_query("SELECT * FROM Matches WHERE series_id = \""+sid+"\"", con)
		for mid in mids['match_id']:
			init_match(sid,int(mid),batch=True)


if __name__ == '__main__':
	main()