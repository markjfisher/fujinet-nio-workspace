10 OPEN #1,8,0,"N1:fixture://resident-write"
20 PRINT #1;"BCD"
30 CLOSE #1
40 OPEN #1,8,0,"N1:fixture://resident-write"
50 FOR I=1 TO 127:PRINT #1;"A";:NEXT I
60 PRINT #1
70 CLOSE #1
80 POKE 1763,1:POKE 1764,173
