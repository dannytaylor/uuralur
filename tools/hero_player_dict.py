import json

# from the playername:[heroes] dict, add the playername to the hero data dict

p_data = json.loads(open('../data/player_names.json').read())
h_p = {}

for p,heroes in p_data.items():
	for h in heroes:
		h_p[h] = p

with open('../data/hero_players.json','w') as f: 
	json.dump(h_p,f,indent=1,sort_keys=True)

