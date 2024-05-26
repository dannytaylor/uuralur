# download power json files from City of Data

import json,requests,os

ats = ['blaster','controller','defender','scrapper','tanker','brute','corruptor','dominator','mastermind','stalker','peacebringer','warshade','sentinel','arachnos_soldier','arachnos_widow']
ignore_powers = ['gadgetry','utility_belt','wind_control','inspirations.holiday','inspirations.large','inspirations.medium','inspirations.small_dual','inspirations.special','inspirations.super']
manualurls = ['temporary_powers.temporary_powers.raptor_pack',
				'temporary_powers.accolades.eye_of_the_magus','temporary_powers.accolades.vanguard_medal','temporary_powers.accolades.geas_of_the_kind_ones',
				'temporary_powers.accolades.megalomaniac','temporary_powers.accolades.demonic_aura','temporary_powers.accolades.vanguard_medal',
				'temporary_powers.accolades.crey_cbx-9_pistol','temporary_powers.accolades.stolen_immobilizer_ray'
				]

powercats = ['pool','epic','inspirations'] # non-AT specific power categories
powersets = []
# powers pre-seeded with arena temps
powers = ['temporary_powers.temporary_powers.raptor_pack','temporary_powers.temporary_powers.web_grenade','temporary_powers.temporary_powers.jaunt_initializer']

jsonfolder = 'data/cod_json'

def fetchjson(url):
	print(url)
	response = requests.get(url)
	data = response.text
	jsondata = json.loads(data)
	return jsondata

def fetchicons(powerpath):
	url = 'https://cod.uberguy.net/homecoming/icons/'
	iconpath = './data/cod_json/icons/'
	jsonfiles = [f for f in os.listdir(powerpath) if f.endswith(".json")]
	for p in jsonfiles:
		with open(powerpath+p) as f:
			data = json.load(f)
			iconname = data['icon']
			if iconname:
				r = requests.get(url+iconname)
				if r.status_code == 200: # if retrieved
					print(iconname)
					iconfile = open(iconpath+iconname, "wb")
					iconfile.write(r.content)
					iconfile.close()

def writejson(jsondata,filename,folder='.'):
	with open(jsonfolder+'/'+folder+'/'+filename+'.json', 'w') as outfile:
		json.dump(jsondata, outfile,indent=4)

def ignore_power(power):
	for ip in ignore_powers:
		if ip not in power:
			return True
	return False

def main():
	global powers
	for at in ats:
		url = 'https://cod.uberguy.net/homecoming/archetypes/'+at+'.json'
		jsondata = fetchjson(url)

		powercats.append(jsondata['primary_category'].lower())
		powercats.append(jsondata['secondary_category'].lower())

		writejson(jsondata,at,'archetypes')

	for pc in powercats:
		url = 'https://cod.uberguy.net/homecoming/powers/'+pc+'/index.json'
		jsondata = fetchjson(url)
		writejson(jsondata,pc,'powercategories')
		for pcn in jsondata['powerset_names']:# powerset_display_names
			powersets.append(pcn.replace('.','/').lower())
	for ps in powersets:
		url = 'https://cod.uberguy.net/homecoming/powers/'+ps+'/index.json'
		jsondata = fetchjson(url)
		writejson(jsondata,ps.replace('/','.'),'powersets')
		for pn in jsondata['power_names']: # power_display_names
			powers.append(pn.replace('.','/').lower())
	powers = [p for p in powers if ignore_power(p.replace('/','.'))]
	for p in powers:
		url = 'https://cod.uberguy.net/homecoming/powers/'+p+'.json'
		jsondata = fetchjson(url)
		writejson(jsondata,p.replace('/','.'),'powers')

if __name__ == "__main__":
	# main()
	fetchicons('./data/cod_json/powers/')