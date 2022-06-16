# for updating playernames in DB for already parsed matches
import sys,sqlite3,os,json,time
import pandas as pd

pnames = json.loads(open('data/player_names.json').read())

def main():
	if sys.argv[1] and sys.argv[1].endswith(".db"):
		db_file = os.path.abspath(sys.argv[1])
		con = sqlite3.connect(db_file)
		cur = con.cursor()

		for p,h in pnames.items():
			p_str = f"\'{p}\'"
			h_str = [hero.replace('\'','\'\'') for hero in h]
			h_str = '(\'' + '\',\''.join(h_str) + '\')'
			h_str = h_str.upper() # case insensitive check
			sql = f"UPDATE Heroes SET player_name={p_str} WHERE player_name IS NULL AND UPPER(hero) IN {h_str};"
			cur.execute(sql)

		con.commit()

	else: # doesn't actually check validity :)
		print("not a valid db file") 
	
if __name__ == '__main__':
	main()