##### uuralur the mirror presides over the garden of pvp memories

s/o charlie for the deep lore name

record demos in game, arena maps only, with slash command  
`/demorecord DEMONAME`  
`/demostop` or stops on map exit  
demos saved to the `COH DIRECTORY\demos` location

requirements.txt should be update to date

parse by main demo folder (all demos), by series, or a single match  
``` python parse.py -a PARENTFOLDERPATH | -s SERIESFOLDERPATH | -m MATCHDEMOPATH [-d DBFILE]```  
writes to an sqlite3 demos.db by default

folder structure 
```
|- demos
    |- series 1
    |- series 2
        |- 1.cohdemo
        |- 2.cohdemo
        |- ...
    |- ...
```

folder name structure yymmdd_SERIES where series is usually team1_team2 or pug or kb

run web app with existing sqlite db  
``` streamlit run app.py```  

precache calculated match data in json  
``` python tools/init_match.py ```  
runs on all matches in db file without existing caches. delete cache file to force rerun on a match


