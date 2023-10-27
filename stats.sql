SELECT * 
FROM
    ( SELECT count(*) as '#streams' FROM Stream ),
    ( SELECT count(*) as '#artists' FROM Artist ),
    ( SELECT count(*) as '#songs'   FROM Song ),
    ( SELECT 
        CAST (( SELECT count(*) FROM Album WHERE imgBigLocal IS NOT NULL ) * 1.0
        / count(*)
        * 100
        as INT)
        as '% Album img local'          
      FROM Album
     ),   
    ( SELECT 
        CAST (( SELECT count(*) FROM Artist WHERE imgBigLocal IS NOT NULL ) * 1.0
        / count(*)
        * 100
        as INT)
        as '% Artists img local'          
      FROM Artist
     )   






