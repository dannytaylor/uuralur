import json, os


power_data = json.loads(open('../data/powers.json').read())

pset_icons = {}

powerset_folder = "data/cod_json/powersets/"
jsonfiles = [f for f in os.listdir(powerset_folder) if f.endswith(".json")]
for j in jsonfiles:
	with open(powerset_folder+j) as f:
		pset = json.load(f)

		if 'power_display_names' in pset and  pset['display_name'] not in pset_icons: # if powerset doesn't have an icon yet
			for p in pset['power_display_names']: # for each power in the power set
				if p in power_data:
					if len(power_data[p]['powersets']) == 1: # if the power is unique to the set
						pset_icons[pset['display_name']] = power_data[p]['icon'] # then we can use the power icon for the set
						
						break

# for p in power_data:
# 	print(p)
# 	if 'powersets' in power_data[p]:
# 		for s in power_data[p]['powersets']:
# 			if s not in pset_icons:
# 				pset_icons[s] = power_data[p]['icon']


icon_dict = "../data/pset_icons.py"
with open(icon_dict, "w") as myfile:
	myfile.write('icon_map = ' + str(pset_icons))

