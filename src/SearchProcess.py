

def processData(tName, queue, sharePrice, resultQueue, threadLock, cardSellerList, cardList, priceMissingCards, index, sellerNameList):
    while not queue.empty():
        usedSellerCardCount, currentPrice, sellerId = queue.get(False)
        cardList[index].seller = sellerId

        comparePrice = sharePrice.value

        #print "%s processing" % (tName)
        returnList, returnPrice = searchRecursive(currentPrice, comparePrice, cardSellerList, cardList, priceMissingCards,
                                            index, usedSellerCardCount, sellerNameList)

        if returnList is not None:
            threadLock.acquire()
            if returnPrice <= sharePrice.value:
                #print "add new price", returnPrice
                sharePrice.value = returnPrice
                resultQueue.put(returnList)

            threadLock.release()


def searchRecursive(currentPrice, comparePrice, cardSellerList, cardList, priceMissingCards, index, usedSellerCardCount, sellerNameList):
    currentCard = None
    resultList = None
    currentCardSellers = None
    #print (' '*(6-index)), 'cup', currentPrice, 'cop', comparePrice, 'now', cardList[index-1].name

    index=index - 1
    currentCard = cardList[index]
    currentCardSellers = cardSellerList[index]
    foundSomething = False

    for seller in currentCardSellers:
        shippingCost = 0
        usedSeller = None
        cardsOfThisSeller = currentCard.amount

        if usedSellerCardCount[seller.id] > 0:
            oldCount = usedSellerCardCount[seller.id]
            cardsOfThisSeller += oldCount

            if cardsOfThisSeller >= 18 and oldCount < 18:
                shippingCost = 6500
            elif cardsOfThisSeller >= 5 and oldCount < 5:
                shippingCost = 4000
        else:
            shippingCost = 8500

        newPrice = currentPrice + shippingCost + seller.price
        lowestPossibleEndPrice = newPrice + priceMissingCards[index]

        #print (' '*(6-index)), currentCard.name, seller.name, 'isUsed', isUsedSeller, 'np', newPrice, 'cop', comparePrice, 'pmc', priceMissingCards[index], 'lpep', lowestPossibleEndPrice

        if lowestPossibleEndPrice < comparePrice and newPrice < comparePrice:
            foundSomething = True

            usedSellerCardCount[seller.id] = cardsOfThisSeller
            currentCard.seller = seller.id

            if index > 0:
                result, comparePrice = searchRecursive(newPrice, comparePrice,
                                                        cardSellerList, cardList, priceMissingCards, index,
                                                        usedSellerCardCount, sellerNameList)
                #if index == 14: print comparePrice, result
                if result is not None:
                    resultList = result
            else:
            #if returnPrice < comparePrice:
                #comparePrice = returnPrice
                comparePrice = newPrice
                resultList = {}

                #print '\n', (' '*(6-index)), 'a new price: ', (comparePrice/1000.0), '-', datetime.datetime.now()

                for card in cardList:
                    if card.seller in resultList:
                        cardAmount = resultList[card.seller][0] + card.amount
                        cardsFromThisSeller = resultList[card.seller][1]
                        cardsFromThisSeller.add(card.name)
                        resultList[card.seller] = (cardAmount, cardsFromThisSeller)
                    else:
                        resultList[card.seller] = (card.amount, set([card.name]))

                #print "\n"
                #for resultName, resultUsedSeller in resultList.iteritems():
                    #print (' '*(6-index)), 'buy from', sellerNameList[resultName], ' ', resultUsedSeller[0],'cards', resultUsedSeller[1]

            usedSellerCardCount[seller.id] = cardsOfThisSeller - currentCard.amount
            currentCard.seller = None

    if not foundSomething:
        #print (' '*(6-index)), currentCard.name, 'nothing found'
        return None, comparePrice

    #print (' '*(6-index)), currentCard.name, 'done'
    return resultList, comparePrice

