import yaml
import demoparse_powers as p

powers = {}

# setup yaml and fx
for key, value in p.fx.items():
	if value not in powers:
		powers[value] = {}
		powers[value]['fx'] = [key]
		powers[value]['pset'] = None
		# powers[value]['type'] = None
		powers[value]['tags'] = []
	else:
		powers[value]['fx'].append(key)


for x in p.phases:
	powers[x]['tags'].append('phase')
for x in p.teleports:
	powers[x]['tags'].append('teleport')
for x in p.primaryattacks:
	powers[x]['tags'].append('primaryattack')
for key, value in p.weightedattacks.items():
	powers[key]['weight'] = key
for x in p.jauntoffoneattacks:
	powers[x]['tags'].append('jauntoffone')
for x in p.powerdelay:
	powers[x]['delay'] = x
for x in p.repeatpowers:
	powers[x]['tags'].append('repeat')
for key, value in p.hittiming.items():
	powers[key]['timing'] = value[0]
	powers[key]['projectile'] = value[1]
for x in p.preverse:
	for power in powers:
		if x in powers[power]['fx']:
			powers[power]['tags'].append('reverse')

for x in p.buffs:
	for power in powers:
		if x in powers[power]['fx']:
			powers[power]['type'] = 'buff'
for x in p.gatherbuffs:
	for power in powers:
		if x in powers[power]['fx']:
			powers[power]['tags'].append('gather')
for x in p.heals:
	powers[x]['type'] = 'heal'
for x in p.absorbs:
	powers[x]['tags'].append('absorb')
for x in p.cmpowers:
	powers[x]['tags'].append('cm')
for x in p.filterextras:
	powers[x]['tags'].append('filterextra')

for key, value in p.powersets.items():
	powers[key]['pset'] = value

with open('powers.yaml','w') as f:
	yaml.dump(powers,f)

