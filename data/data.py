
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
	'Arena_OutbreakRuin_01.txt':'outbreak',
	'Arena_Founders_01.txt':'liberty town',
	'Arena_Praetoria_01.txt':'last bastion', # aka ruined eden
	'Arena_Industrial_01.txt':'factory',
	'Arena_Industrial_02.txt':'industrial (new)',
	'Arena_Outdoor_01.txt':'council earth',
	'Arena_Outdoor_02.txt':'luna square',
}

primaryattacks = { # npc costumes used by players throwing off player detection
	'Blaze',
}

movs = { # npc costumes used by players throwing off player detection
	'Death':"Death",
	'PLAYER_HITDEATH':"Death",
	'PLAYERKNOCKBACK':"Knockback (Hit)",
	'PLAYERKNOCKBACK_IMPACT':"Knockback (Land)",
}


at_fx = { # determine pset/AT for powers not picked up by actions
	# FX:[pset,possible_ats,reverse]
	"WEAPONS/BOW/TRICKARROW/NETARROWHITENERGY.FX": ["Trick Arrow",{"controller","defender/corruptor","mastermind"},True]
}

