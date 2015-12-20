this doesn't work anymore
============
The page is different now and has its own estimation price finder.

Tries to find the best price based on the cards you want to buy on magickartenmarkt.de

usage:  
mkmlogin.py [optional cardlistfile]

if you don't supply a file with english names  
1 cardname    
4 cardname    

it will try to login and read your default wantlist and select all cards with amount >100 and subtract 100


up to 25 cards does work, after that O(n²) kills it
