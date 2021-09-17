# converting raw power json files to formats for demo parsing
import json, os

attack_fx  = {}
act_fx  = {} # activation, mostly toggles
hit_fx  = {}
cont_fx = {} # continuing effects only, usually toggles
cond_fx = {} # continuing effects only, usually toggles
no_fx = [] # list of power names without relevant effects

power_rename = json.loads(open('data/power_rename.json').read())
power_data = json.loads(open('data/power_data.json').read())

count_cfx = {'Hibernate'} # 'Thaw','Forge'
# all_ats = {"arachnos_soldier","arachnos_widow","blaster","brute","controller","corruptor","defender","dominator","mastermind","peacebringer","scrapper","sentinel","stalker","tanker","warshade"}
all_ats = {"arachnos_soldier","arachnos_widow","blaster","brute","controller","defender/corruptor","dominator","mastermind","peacebringer","scrapper","sentinel","stalker","tanker","warshade"}

fxfolder  = './data/fx/'
infolder  = './data/cod_json/powers/'
outfolder = '../data/'

def appendfx(name,fx,fxlist):
	if (fx 
		and fx not in power_rename['add_attack'] and fx not in power_rename['add_hit']
		and fx not in power_rename['ignore'] and fx not in power_rename['hold_fx']
		):
		if fx in  power_rename['fx']:
			name = power_rename['fx'][fx]
		if fx in fxlist:
			if name not in fxlist[fx]:
				fxlist[fx].append(name) 
		else:
			fxlist[fx] = [name]

	for psr in power_rename['powerset_rename']:
		# if a patch resulted in a powerset name change (e.g. earthcontrol to stonefx)
		if fx and psr in fx:
			appendfx(name,fx.replace(psr,power_rename['powerset_rename'][psr]),fxlist)

def removedoublesingles(fx,gx):
	singleatknames = {v[0] for k,v in fx.items() if len(v) == 1}
	singlehitnames = {v[0] for k,v in gx.items() if len(v) == 1}
	removehitnames = singlehitnames.intersection(singleatknames)
	removehitfx = [k for k,v in gx.items() if (len(v)==1 and v[0] in removehitnames)]
	for r in removehitfx:
		del gx[r]

def parsefx(name,fx):
	afx  = fx['attack_fx']
	rfx  = fx['hit_fx']
	actfx  = fx['activation_fx']
	cfx = None # continuing
	cdfx = None # conditional

	appendfx(name,afx,attack_fx)
	appendfx(name,rfx,hit_fx)

	# if fx['continuing_fx']:
	# 	appendfx(name,fx['continuing_fx'][0],cont_fx)
	# if fx['conditional_fx']:
	# 	appendfx(name,fx['conditional_fx'][0],cond_fx)

	if not afx and not rfx:
		appendfx(name,actfx,act_fx)

	attack_fx.update(act_fx)
	# hit_fx.update(cont_fx)

	# no_fx powers with no attack/hit/activate/continuing effects (mostly autos)
	# if not afx and not rfx and not cfx and not actfx:
	# 	if name not in no_fx:
	# 		no_fx.append(name)
	# return

def removemultkeys(fx,n): # remove PFXs with multiple (n) power names
	removekeys = {k for k in fx if len(fx[k])>n}
	for r in removekeys:
		del fx[r] 

# convert json files to simple fx:powername dict for lookups
def json2fx():
	jsonfiles = [f for f in os.listdir(infolder) if f.endswith(".json")]
	jsonfiles.sort()

	for p in jsonfiles:
		with open(infolder+p) as f:
			data = json.load(f)
			name = data['display_name']
			if name in power_rename['name']:
				name = power_rename['name'][name]
			fx   = data['fx']
			parsefx(name,fx)
			for customfx in data['custom_fx']:
				parsefx(name,customfx['fx'])

	# for viewing fx with multiple power names
	dupl = {}
	for k,v in attack_fx.items():
		if len(v)>1: dupl[k] = v
	for k,v in hit_fx.items():
		if len(v)>1: dupl[k] = v
	with open(fxfolder+'duplicate_fx.json','w') as f:
		json.dump(dupl,f,indent=4)


	removedoublesingles(attack_fx,hit_fx)

	with open(fxfolder+'attack_fx.json','w') as f:
		json.dump(attack_fx,f,indent=4)
	with open(fxfolder+'hit_fx.json','w') as f:
		json.dump(hit_fx,f,indent=4)

	removemultkeys(attack_fx,1)
	removemultkeys(hit_fx,1)

	# manual add powers by fx
	attack_fx.update(power_rename['add_attack'])
	hit_fx.update(power_rename['add_hit'])

	# merge atk/hit into single dict for parse script
	all_fx = {}
	all_fx['attack'] = attack_fx
	all_fx['hit'] = hit_fx
	all_fx['hold'] = power_rename['hold_fx']
	for k,v in all_fx.items(): # flatten strings out of lists
		for kk,vv in v.items():
			if len(vv) == 1:
				v[kk] = vv[0] 

	with open(outfolder+'fx.json','w') as f:
		json.dump(all_fx,f,indent=4)

	# with open(fxfolder+'act_fx.json','w') as f: json.dump(act_fx,f,indent=4)
	# with open(fxfolder+'cont_fx.json','w') as f: json.dump(cont_fx,f,indent=4)
	# with open(fxfolder+'cond_fx.json','w') as f: json.dump(cond_fx,f,indent=4)
	# with open(fxfolder+'no_fx.json','w') as f: json.dump(no_fx,f,indent=4)

	return


def initpower(name,powers,data):
	p = powers[name]
	p['tags'] = set()
	p['powersets'] = set()
	p['archetypes'] = set()
	p['targets_affected'] = set() # "foe/ally/self (alive/dead)

	# attribs determined by first instance found
	p['type'] = data['type']
	p['recharge_time'] = data['recharge_time']
	p['effect_area'] = data['effect_area'] # singletaget (includes self), aoe (target and pb), self, location, cone
	p['target_type'] = data['target_type']
	p['frames_attack'] = data['fx']['frames_attack']/30 # how long in animation
	p['frames_before_hit'] = data['fx']['frames_before_hit']/30 # frames from cast to projectile launch
	p['projectile_speed'] = data['fx']['projectile_speed']

	# fx (non-custom)
	p['attack_fx'] = set()
	p['hit_fx'] = set()
	p['activation_fx'] = set()

	updatepower(name,powers,data)

def addpooltags(name,powers,data):
	p = powers[name]
	pools = {'Pool','Epic','Temporary_Powers','Inspirations'}
	for pool in pools:
		if data['powerset'].startswith(pool):
			p['tags'].add(pool)
			p['archetypes'] = p['archetypes'].union(all_ats)
			break

def updatepowerfx(name,powers,data):
	p = powers[name]
	if data['fx']['attack_fx']: 		p['attack_fx'].add(data['fx']['attack_fx'])
	if data['fx']['hit_fx']: 			p['hit_fx'].add(data['fx']['hit_fx'])
	if data['fx']['activation_fx']:		p['activation_fx'].add(data['fx']['activation_fx'])
	# if a patch resulted in a powerset name change (e.g. earthcontrol to stonefx)
	for psr in power_rename['powerset_rename']:
		if data['fx']['attack_fx'] and psr in data['fx']['attack_fx']: 			p['attack_fx'].add(data['fx']['attack_fx'].replace(psr,power_rename['powerset_rename'][psr]))
		if data['fx']['hit_fx'] and psr in data['fx']['hit_fx']: 				p['hit_fx'].add(data['fx']['hit_fx'].replace(psr,power_rename['powerset_rename'][psr]))
		if data['fx']['activation_fx'] and psr in data['fx']['activation_fx']:	p['activation_fx'].add(data['fx']['activation_fx'].replace(psr,power_rename['powerset_rename'][psr]))


def updatepower(name,powers,data):
	p = powers[name]
	powerset = data['display_fullname'].split('.')[1]

	p['powersets'].add(powerset)
	p['archetypes'] = p['archetypes'].union(set(data['archetypes']))
	if 'defender' in p['archetypes'] or 'corruptor' in p['archetypes']:
		p['archetypes'].discard('defender')
		p['archetypes'].discard('corruptor')
		p['archetypes'].add('defender/corruptor')
	p['archetypes'].discard('boss_monster')
	p['targets_affected'] = p['targets_affected'].union(set(data['targets_affected']))
	updatepowerfx(name,powers,data)
	# tags
	if 'Enhance Heal' in data['boosts_allowed'] or name == "Respite" and data['target_type'] != 'Location':
		p['tags'].add("Heal")
	elif 'Universal Damage Sets' in data['allowed_boostset_cats'] and 'Foe (Alive)' in p['targets_affected']:
		p['tags'].add("Attack")
	elif '-RES' in data['display_short_help'].upper() and 'Foe (Alive)' in p['targets_affected']:
		p['tags'].add("Debuff")
		p['tags'].add("Attack")
	for tag, power in power_data['tags'].items():
		if name in power: p['tags'].add(tag)
	addpooltags(name,powers,data)

	# for dict of Powerset Name:Allowable ATs
	if powerset not in powers['powersets']: powers['powersets'][powerset] = set()
	atadd = set(data['archetypes'])
	if 'defender' in p['archetypes'] or 'corruptor' in atadd:
		atadd.discard('defender')
		atadd.discard('corruptor')
		atadd.add('defender/corruptor')
	powers['powersets'][powerset] = powers['powersets'][powerset].union(atadd)


# use lists initially for union and add functions, convert back to lists to write to JSON
def sets2lists(powers):
	for k,v in powers.items():
		if isinstance(v,set):
			powers[k] = list(v)
		elif isinstance(v,dict):
			powers[k] = sets2lists(v)
			
	return powers

# convert json files to pase power dictionary structure with relevant information
def json2powers():
	powers = {}
	powers['powersets'] = {}
	unid   = []

	jsonfiles = [f for f in os.listdir(infolder) if f.endswith(".json")]
	jsonfiles.sort()

	for jf in jsonfiles:
		with open(infolder+jf) as f:
			data = json.load(f)

			name = data['display_name']
			if name in power_rename['name']:
				name = power_rename['name'][name]

			if name not in powers: # first find of power name
				powers[name] = {}
				initpower(name,powers,data)
			else: updatepower(name,powers,data)
			if "boss_monster" in powers[name]['archetypes']:powers[name]['archetypes'].remove("boss_monster")


	sets2lists(powers)

	with open(outfolder+'powers.json','w') as f:
		json.dump(powers,f,indent=4)
	
if __name__ == '__main__':
	json2fx()
	json2powers()