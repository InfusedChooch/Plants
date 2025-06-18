# Excel Link String Formula

```
=TEXTJOIN(
  ";", TRUE,

  IF(OR($E3="",$D3="",$C3=""), "",
     CONCAT("[",$E3,",",CHAR(34),$D3,CHAR(34),",",CHAR(34),$C3,CHAR(34),"]")),

  IF(OR($H3="",$G3="",$F3=""), "",
     CONCAT("[",$H3,",",CHAR(34),$G3,CHAR(34),",",CHAR(34),$F3,CHAR(34),"]")),

  IF(OR($K3="",$J3="",$I3=""), "",
     CONCAT("[",$K3,",",CHAR(34),$J3,CHAR(34),",",CHAR(34),$I3,CHAR(34),"]")),

  IF(OR($N3="",$M3="",$L3=""), "",
     CONCAT("[",$N3,",",CHAR(34),$M3,CHAR(34),",",CHAR(34),$L3,CHAR(34),"]"))
)
```
