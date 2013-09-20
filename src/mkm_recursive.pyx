# cython: boundscheck=False
# cython: wraparound=False
def searchLoop(whoSellsThisCardList, # list[ list[ seller( int id, int price ), ... ], ... ]
                int comparePrice, # int
                cardAmountListPy, # list[ int, ... ]
                priceMissingCardsPy, # list[ int, ... ]
                usedSellerCardCountA,
                cardList): # list[ int, ... ]
    resultBuyCardFromSellerId = [0]*100
    cdef int index = 0
    cdef int lastIndex = len(whoSellsThisCardList)-1
    cdef int i = 0
    cdef int sellerCountPerCard[100]
    for sellers in whoSellsThisCardList:
        sellerCountPerCard[i] = len(sellers)
        i = i+1
    cdef int cardAmountList[100]
    for i in range(len(cardAmountListPy)): 
        cardAmountList[i] = cardAmountListPy[i]
        i = i + 1 
    cdef int priceMissingCards[100]
    for i in range(len(priceMissingCardsPy)): 
        priceMissingCards[i] = priceMissingCardsPy[i]
        i = i + 1 
    cdef int zeroIndexListLength = sellerCountPerCard[0]
    cdef int sellerIdPerCard[100]
    cdef int costAddedPerCard[100]
    cdef int workingBuyCardFromSellerId[100]
    for i in range(100):
        sellerIdPerCard[i] = 0
        costAddedPerCard[i] = 0
        workingBuyCardFromSellerId[i] = 0
    
    cdef int usedSellerCardCount[1000]
    for i in range(1000):
        usedSellerCardCount[i] = 0
    i = 0
    cdef int currentPrice = 0
    cdef int rounds = 0
    sellers = whoSellsThisCardList[index]
    cdef int currentCardPrice = 0
    cdef int currentCardSellerId = 0
    cdef int newPrice = 0
    while not (index == 0 and sellerIdPerCard[0] == zeroIndexListLength):
        rounds += 1
        currentCardSeller = sellers[sellerIdPerCard[index]]
        currentCardPrice = currentCardSeller.price
        #print " " * (index), cardList[index].name, currentCardSeller.name
        if currentPrice + priceMissingCards[index] + currentCardPrice < comparePrice:
            cardsOfThisSeller = cardAmountList[index]
            currentCardSellerId = currentCardSeller.id
    
            if usedSellerCardCount[currentCardSellerId] > 0:
                oldCount = usedSellerCardCount[currentCardSellerId]
                cardsOfThisSeller += oldCount #
    
                if cardsOfThisSeller >= 18 and oldCount < 18:
                    currentCardPrice += 6500
                elif cardsOfThisSeller >= 5 and oldCount < 5:
                    currentCardPrice += 3500
            else:
                currentCardPrice += 8500
    
            newPrice = currentCardPrice + currentPrice

            if newPrice + priceMissingCards[index] < comparePrice:
                workingBuyCardFromSellerId[index] = currentCardSellerId
                if index == lastIndex:
                    comparePrice = newPrice
                    for i in range(lastIndex+1): 
                        resultBuyCardFromSellerId[i] = workingBuyCardFromSellerId[i]
                else:
                    usedSellerCardCount[currentCardSellerId] = cardsOfThisSeller
                    costAddedPerCard[index] = currentCardPrice
                    currentPrice = newPrice
                    index += 1
                    sellers = whoSellsThisCardList[index]
                    continue
        else:
            sellerIdPerCard[index] = 0
            index -= 1
            usedSellerCardCount[workingBuyCardFromSellerId[index]] -= cardAmountList[index]
            currentPrice -= costAddedPerCard[index]
            sellers = whoSellsThisCardList[index]
                
        sellerIdPerCard[index] += 1
        if sellerIdPerCard[index] == sellerCountPerCard[index]:
            while sellerIdPerCard[index] == sellerCountPerCard[index] and index > 0:
                sellerIdPerCard[index] = 0
                index -= 1
                sellerIdPerCard[index] += 1
                usedSellerCardCount[workingBuyCardFromSellerId[index]] -= cardAmountList[index]
                currentPrice -= costAddedPerCard[index]
            sellers = whoSellsThisCardList[index]

    print rounds
    return resultBuyCardFromSellerId