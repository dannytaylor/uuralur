
# ignore names under NEW
namefilter  = {
	'Mu Guardian',
	'Phantasm',
	'Decoy Phantasm',
	'Decoy',
	'Jack Frost',
	'Singularity',
	'Dimension Shift',
	'Coralax Blue Hybrid',
	'Dr',
	'Transference',
	'Poison Trap',
	'Animated Stone',
	'Victory Rush',
	'Bruiser',
	'Blind',
	'Galvanic Sentinel',
	'Voltaic Geyser',
	'Voltaic Sentinel',
	'Power Disruptor',
	'Protected Area',
	'Rain of Fire',
	'Water Spout',
	'Fortunata Mistress',
	'Superior Vigilant Assault',
	'Superior Scourging Blast',
	'Superior Defender\'s Bastion',
	'German Shepherd',
	'Ice Storm',
	'Energy Font',
	'Spectral Terror',
	'Coralax Red Hybrid',
	'Faraday Cage',
	'Architect Entertainment Instructor',
	'Architect Contact',
	'Spirit Panther',
	'Ticket Vendor',
	'Architect Entertainment Greeter',
	'Howler Wolf',
	'Alpha Howler Wolf',
	'Dire Wolf',
	'Lioness',
	'Burst of Speed',
	'Sleet',
	'Blizzard',
	'Siphon Power',
	'Imp',
	'Umbra Beast',
	'Shade',
	'Photon Seeker',
	'Grave Knight',
	'Spec Ops',
	'Force Field Generator',
}

# ignore NPCs with these costumes
ignorecostumes = { # npc costumes used by players throwing off player detection
	'FRK_45',
	'Kheldian_Peacebringer_Light_Form',
	'V_Coralax_Player_Boss',
}

# ignore reading lines from demos with these entities to cut down on lines length
ignore_line_ent = {
	'FXSCALE',
	'FXINT',
	'PARTSNAME',
	'COSTUME',
	'ORIGIN',
	'PYR',
	'SKY',
	'DEL',
	'floatdmg',
	'float',
	'Time',
	'Version',
	'EntRagdoll',
	'Player',
}


mapaliases = {
	'maps/Arena/Arena_Skyway_01/Arena_Skyway_01.txt':'Skyway',
	'maps/Arena/Arena_steel_01/Arena_steel_01.txt':'Steel',
	'maps/Arena/Arena_Outdoor_02/Arena_Outdoor_02.txt':'Luna Square',
	'maps/Arena/Arena_OutbreakRuin_01/Arena_OutbreakRuin_01.txt':'Outbreak',
	'maps/Arena/Arena_Praetoria_01/Arena_Praetoria_01.txt':'Last Bastion',
	'maps/Arena/Arena_Founders_01/Arena_Founders_01.txt':'Liberty Town',
	'maps/Arena/Arena_Atlas_01/Arena_Atlas_01.txt':'Atlas',
	'maps/Arena/Arena_Boomtown_01/Arena_Boomtown_01.txt':'Boomtown',
	'maps/Arena/Arena_Outdoor_01/Arena_Outdoor_01.txt':'Council Earth',
	'maps/Arena/Arena_Eden_01/Arena_Eden_01.txt':'Eden',
	'maps/Arena/Arena_Striga_01/Arena_Striga_01.txt':'Striga',
	'maps/Arena/Arena_Industrial_02/Arena_Industrial_02.txt':'New Industrial',
	'maps/Arena/Arena_Stadium_01/Arena_Stadium_01.txt':'Stadium',
	'maps/Arena/Arena_Industrial_02/Arena_Industrial_01.txt':'Seige',
}

movs = { # npc costumes used by players throwing off player detection
	'Death':"Death",
	'PLAYER_HITDEATH':"Death",
	'PLAYERKNOCKBACK':"Knockback (Hit)",
	'PLAYERKNOCKBACK_IMPACT':"Knockback (Land)",
}


at_fx = { # determine pset/AT for powers not picked up by actions
	# FX:[pset,possible_ats,reverse]
}

