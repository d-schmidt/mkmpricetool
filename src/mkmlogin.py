# coding=utf-8
import requests
from lxml.html import fromstring
import sys
import datetime
import time
from multiprocessing import Process, Queue, Lock
from multiprocessing.sharedctypes import Value
#from SearchProcess import processData
import os


loginData = {
    'username': '123123',
    'userPassword': '123123'
}

useMultiProccess = 1

wantedQuality = 'GD'

qualities = {
    'PO' : 1,
    'PL' : 2,
    'LP' : 3,
    'GD' : 4,
    'EX' : 5,
    'NM' : 6,
    'MT' : 7
}

acceptedCountries = set([
    #'Austria',
    #'Belgium',
    #'Bulgaria',
    #'Canada',         # not EU
    #'Cyprus',
    #'Czech Republic',
    #'Denmark',
    #'Estonia',
    #'Finland',
    #'France',
    'Germany',
    #'Great Britain',
    #'Greece',
    #'Hungary',
    #'Ireland',
    #'Italy',
    #'Latvia',
    #'Liechtenstein',
    #'Lithuania',
    #'Luxembourg',
    #'Malta',
    #'Netherlands',
    #'Norway',
    #'Poland',
    #'Portugal',
    #'Romania',
    #'Slovakia',
    #'Slovenia',
    #'Spain',
    #'Sweden',
    #'Switzerland'     # not EU
])

acceptedUserStatus = set([
    #'danger',   # bad user
    #'E-NULL',   # new user
    #'NYR',      # new user, not yet rated
    #'SS-5',     # thumb down
    'SS-4',     # average seller
    'SS-3',     # good seller
    'SS-2',     # very good seller
    'SS-1'      # outstanding seller
])

possibleUserStatus = set([
    'danger',   # bad user
    'E-NULL',   # new user
    'SS-5',     # thumb down
    'SS-4',     # average seller
    'SS-3',     # good seller
    'SS-2',     # very good seller
    'SS-1'      # outstanding seller
])

bannedEditions = set([
    u'WCD 1996: Bertrand Lestree',
    u'WCD 1996: Eric Tam',
    u'WCD 1996: George Baxter',
    u'WCD 1996: Leon Lindback',
    u'WCD 1996: Mark Justice',
    u'WCD 1996: Michael Locanto',
    u'WCD 1996: Preston Poulter',
    u'WCD 1996: Shawn Regnier',
    u'WCD 1997: Jakub Slemr',
    u'WCD 1997: Janosch Kuhn',
    u'WCD 1997: Paul McCabe',
    u'WCD 1997: Svend Geertsen',
    u'WCD 1998: Ben Rubin',
    u'WCD 1998: Brian Hacker',
    u'WCD 1998: Brian Selden',
    u'WCD 1998: Randy Buehler',
    u'WCD 1999: Jakub Šlemr',
    u'WCD 1999: Kai Budde',
    u'WCD 1999: Mark Le Pine',
    u'WCD 1999: Matt Linde',
    u'WCD 2000: Janosch Kühn',
    u'WCD 2000: Jon Finkel',
    u'WCD 2000: Nicolas Labarre',
    u'WCD 2000: Tom Van de Logt',
    u'WCD 2001: Alex Borteh',
    u'WCD 2001: Antoine Ruel',
    u'WCD 2001: Jan Tomcani',
    u'WCD 2001: Tom van de Logt',
    u'WCD 2002: Brian Kibler',
    u'WCD 2002: Carlos Romao',
    u'WCD 2002: Raphael Levy',
    u'WCD 2002: Sim Han How',
    u'WCD 2003: Daniel Zink',
    u'WCD 2003: Dave Humpherys',
    u'WCD 2003: Peer Kröger',
    u'WCD 2003: Wolfgang Eder',
    u'WCD 2004: Aeo Paquette',
    u'WCD 2004: Gabriel Nassif',
    u'WCD 2004: Julien Nuijten',
    u'WCD 2004: Manuel Bevand',
    u'World Championship Decks',
    u"Collectors' Edition",
    u'International Edition',
    u'Oversized 6x9 Promos'
])

singleBannedEditions = {
    # nobody wants oversized cards
    'Player Rewards Promos' : ['Comet Storm', 'Emrakul, the Aeons Torn',
                            'Feral Hydra', 'Glissa, the Traitor', 'Hero of Bladehold',
                            'Lightning Bolt', 'Rampaging Baloths', 'Spellbreaker Behemoth',
                            'Sun Titan', 'Wurmcoil Engine'],
    'Prerelease Promos' : ['Griselbrand', 'Bruna, Light of Alabaster', 'Gisela, Blade of Goldnight',
                            'Sigarda, Host of Herons', 'Avacyn, Angel of Hope']
}


def readWants(text):
    wantList = []

    html = fromstring(text)
    rows = html.xpath('//tr[@class][*[1][contains(@class, "centered")]]')

    for row in rows:
        name = row[2][0].text
        url = row[2][0].get('href')[1:]
        quali = row[5][1][0].get('alt')
        quali = qualities[quali]
        amount = int(row[10].text)

        if amount > 100:
            amount = amount - 100
            wantList.append(Card(name, url, quali, amount))

    return wantList


def getSellerList(text, targetAmount, targetQuality, cardName):
    sellerList = []
    html = fromstring(text)
    rows = html.xpath('//tr[@class][*[1][contains(@class, "centered")]]')

    for row in rows:
        country = row[1][0][1][0].get('onmouseover').partition(': ')[2][:-2]

        if country in acceptedCountries:
            try:
                danger = row[1][0][2][0].get('alt')

                if danger not in possibleUserStatus:
                    danger = 'NYR'
            except IndexError:
                danger = 'NYR'

            if danger in acceptedUserStatus:
                name = row[1][0][0][0].text
                edition = row[2][0].get('onmouseover')[12:-2]
                quali = row[5][0][0].get('alt')
                quali = qualities[quali]
                amount = int(row[9].text)

                price = row[8].text
                price = price.partition(' ')[0]
                price =  int(price.replace(',','')) * 100
                playset = False

                for specialIcon in row[6]:
                    if specialIcon[0].tag == 'img' and specialIcon[0].get('alt') == 'playset':
                        playset = True
                        price = price // 4
                        amount = amount * 4
                        break

                if quali >= targetQuality and edition not in bannedEditions and not (edition in singleBannedEditions and cardName in singleBannedEditions[edition]):
                    overall = amount
                    justUpdate = False
                    updateOverAllList = []

                    for seller in sellerList:
                        if seller.name == name:
                            overall = seller.amount + overall
                            updateOverAllList.append(seller)

                            if seller.price == price and seller.playset == playset:
                                seller.amount = seller.amount + amount
                                justUpdate = True

                    for seller in updateOverAllList:
                        seller.overall = overall

                    if not justUpdate:
                        sellerList.append(Seller(name, playset, quali, amount, overall, price))

    # remove playsets and seller with too few cards
    needsCleaning = True

    while needsCleaning:
        removedSellers = []
        toRemoveSeller = []

        for seller in sellerList:
            if targetAmount > seller.overall or (targetAmount < 4 and seller.playset):
                sellerName = seller.name

                if seller.amount != seller.overall and not sellerName in removedSellers:
                    removedSellers.append(seller.name)

                toRemoveSeller.append(seller)

        for seller in toRemoveSeller:
            sellerList.remove(seller)

        if len(removedSellers) > 0:
            for removedSeller in removedSellers:
                overall = 0
                updateOverAllList = []

                for seller in sellerList:
                    if removedSeller == seller.name:
                        overall = overall + seller.amount
                        updateOverAllList.append(seller)

                for seller in updateOverAllList:
                    seller.overall = overall
        else:
            needsCleaning = False

    return sellerList


def sortAndCleanSellerList(sellerList, targetAmount):
    # packing same seller together
    toRemoveSeller = []

    sellerList.sort()

    for sellerId, seller in enumerate(sellerList):
        log = False
        #if seller.name == "H8Man": log = True
        #try: print sellerId, seller
        if log: print sellerId, seller.__str__().encode('ascii','replace')
        #except UnicodeEncodeError: pass
        if seller.amount != seller.overall:
            if log: print "a != o"
            if sellerId not in toRemoveSeller:
                if log: print "not in remove"
                if seller.amount >= targetAmount and (not seller.playset or (seller.playset and targetAmount % 4 == 0)):
                    if log: print "karten reichen"
                    seller.overall = seller.amount
                    if log: print "o = a", seller.amount
                    seller.price = seller.price * targetAmount
                    if log: print "p = p*t"

                    for innerId, innerSeller in enumerate(sellerList):
                        if innerId != sellerId and seller.name == innerSeller.name:
                            if innerId not in toRemoveSeller:
                                if log: print "append innerid", innerId, innerSeller.__str__().encode('ascii','replace')
                                toRemoveSeller.append(innerId)
                            else:
                                if log: print "innerid", innerId, "already in list"
                else:
                    if log: print "karten reichen noch nicht"
                    neededAmount = targetAmount - seller.amount
                    newPrice = seller.price * seller.amount
                    if log: print "new price", newPrice

                    for innerId, innerSeller in enumerate(sellerList):
                        if innerId != sellerId and seller.name == innerSeller.name:
                            if not seller.playset and not innerSeller.playset:
                                seller.amount = seller.amount + innerSeller.amount
                                toRemoveSeller.append(innerId)
                                if log: print "amount update, remove inner", innerId, innerSeller.__str__().encode('ascii','replace')

                                if seller.amount >= targetAmount:
                                    newPrice = newPrice + neededAmount * innerSeller.price
                                    if log: print "new price  seller hat genug", newPrice
                                    break
                                else:
                                    newPrice = newPrice + innerSeller.amount * innerSeller.price
                                    neededAmount -= innerSeller.amount
                                    if log: print "new price seller hat nich genug", newPrice

                    seller.price = newPrice
                    seller.overall = seller.amount
            else :
                if log: print "is already in removelist"
        else:
            if log: print "amount is already == overall amount"
            seller.price = seller.price * targetAmount

    toRemoveSeller.sort()

    #print toRemoveSeller
    #for seller in sellerList: print seller.__str__().encode('ascii','replace')
    #print len(sellerList)

    while toRemoveSeller:
        id = toRemoveSeller.pop()
        del sellerList[id]

    sellerList.sort()
    return sellerList


def getSellerPriceFromList(sellerName, sellerList):
    for seller in sellerList:
        if seller.name == sellerName:
            return seller.price


def getSellerIdFromList(sellerName, sellerList):
    for id, seller in enumerate(sellerList):
        if seller.name == sellerName:
            return id


def bubbleSortLists(cardList, cardSellerList):
    n = len(cardList)

    while n > 1:
        newN = 1

        for i in range(n-1):
            if len(cardSellerList[i]) < len(cardSellerList[i+1]):
                cardSellerList[i], cardSellerList[i+1] = cardSellerList[i+1], cardSellerList[i]
                cardList[i], cardList[i+1] = cardList[i+1], cardList[i]
                newN = i+1

        n = newN

def bubbleSortListsAsc(cardList, cardSellerList):
    n = len(cardList)

    while n > 1:
        newN = 1

        for i in range(n-1):
            if len(cardSellerList[i]) > len(cardSellerList[i+1]):
                cardSellerList[i], cardSellerList[i+1] = cardSellerList[i+1], cardSellerList[i]
                cardList[i], cardList[i+1] = cardList[i+1], cardList[i]
                newN = i+1

        n = newN

roundR = 0
def getCheapestPrice(cardList, cardSellerList):
    buyMap = {}

    if len(cardList) > 0 and len(cardSellerList) > 0:
        # remove irrelevant seller
        print '\nstarting to find the best price'
        print 'step 1: cleanup'

        needsCleaning = True

        while needsCleaning:
            multiSeller = set()
            needsCleaning = False
            #print '      new round'

            for shopCard, sellerList in enumerate(cardSellerList):
                lowestPrice = sellerList[0].price
                cheapestSeller = sellerList[0].name

                toRemoveSeller = []

                for seller in sellerList:
                    keepMe = False

                    if seller.name == cheapestSeller:
                        keepMe = True
                    elif seller.price < lowestPrice + 8500:  #auf 70 cent gesetzt
                        if seller.name not in multiSeller:
                            for innerShopCard, innerSellerList in enumerate(cardSellerList):
                                if innerShopCard != shopCard:
                                    for innerSeller in innerSellerList:
                                        if seller.name == innerSeller.name:
                                            #print seller.name, innerSeller.name, 'found in', shopCard, innerShopCard
                                            keepMe = True
                                            multiSeller.add(seller.name)
                                            break
                                if keepMe:
                                    break
                        else:
                            keepMe = True

                    if not keepMe:
                        #print 'remove seller', seller.name, 'from list', shopCard
                        toRemoveSeller.append(seller)

                #print cardSellerList
                #print 'delete seller count', len(toRemoveSeller)

                for seller in toRemoveSeller:
                    #print seller
                    needsCleaning = True
                    sellerList.remove(seller)

        j = 0
        for i, card in enumerate(cardList):
            j = j + len(cardSellerList[i])
            print 'remaining seller for card', i, card.name, len(cardSellerList[i])
        print 'total seller', j

        cleaningMap = {}

        for shopCard, sellerList in enumerate(cardSellerList):
            for seller in sellerList:
                if seller.name not in cleaningMap:
                    #print 'add seller to map', seller.name
                    cleaningMap[seller.name] = set()

                cleaningMap[seller.name].add(shopCard)

        """
        print len(cleaningMap)

        for seller, cleanCardList in cleaningMap.iteritems():
            print seller, cleanCardList
        #"""

        removeSellerFromCardMap = {}

        for sellerName, cleanCardList in cleaningMap.iteritems():
            cleanCardSum = 0
            cheapestSum = 0
            for cardIndex in cleanCardList:
                cleanCardSum = cleanCardSum + getSellerPriceFromList(sellerName, cardSellerList[cardIndex])
                cheapestSum = cheapestSum + cardSellerList[cardIndex][0].price + 8500

            if len(cleanCardList) > 17:
                cleanCardSum = cleanCardSum + 18500
            elif len(cleanCardList) > 4:
                cleanCardSum = cleanCardSum + 12000
            else:
                cleanCardSum = cleanCardSum + 8500

            if cleanCardSum > cheapestSum:
                for cardId in cleanCardList:
                    if cardId not in removeSellerFromCardMap:
                        removeSellerFromCardMap[cardId] = set()

                    removeSellerFromCardMap[cardId].add(getSellerIdFromList(sellerName, cardSellerList[cardId]))

            for innerSellerName, innerCardList in cleaningMap.iteritems():
                if sellerName != innerSellerName:
                    if innerCardList <= cleanCardList:
                        sumSeller = 0
                        sumInnerSeller = 0

                        for cardId in innerCardList:
                            #print sellerName, cardId, cleanCardList, len(cardSellerList[cardId]), cardSellerList[cardId]
                            sumSeller = sumSeller + getSellerPriceFromList(sellerName, cardSellerList[cardId])
                            sumInnerSeller = sumInnerSeller + getSellerPriceFromList(innerSellerName, cardSellerList[cardId])

                        #print 'innerSeller', innerSellerName, sumInnerSeller, ' <= ', sellerName, sumSeller, 'selling cards', innerCardList, cleanCardList

                        if sumInnerSeller >= sumSeller:
                            for cardId in innerCardList:
                                if cardId not in removeSellerFromCardMap:
                                    removeSellerFromCardMap[cardId] = set()
                                #print 'innerSeller', innerSellerName, 'removed from card', cardId, cardList[cardId]
                                removeSellerFromCardMap[cardId].add(getSellerIdFromList(innerSellerName, cardSellerList[cardId]))
                    elif cleanCardList < innerCardList:
                        sumSeller = 0
                        sumInnerSeller = 0

                        for cardId in cleanCardList:
                            sumSeller = sumSeller + getSellerPriceFromList(sellerName, cardSellerList[cardId])
                            sumInnerSeller = sumInnerSeller + getSellerPriceFromList(innerSellerName, cardSellerList[cardId])

                        #print 'outerSeller', sellerName, sumSeller, ' < ', innerSellerName, sumInnerSeller, 'selling cards', cleanCardList, innerCardList

                        if sumSeller >= sumInnerSeller:
                            for cardId in cleanCardList:
                                if cardId not in removeSellerFromCardMap:
                                    removeSellerFromCardMap[cardId] = set()
                                #print 'outerSeller', sellerName, 'removed from card', cardId, cardList[cardId]
                                removeSellerFromCardMap[cardId].add(getSellerIdFromList(sellerName, cardSellerList[cardId]))

        for cardId, toRemoveSellerList in removeSellerFromCardMap.iteritems():
            toRemoveSellerList = list(toRemoveSellerList)
            toRemoveSellerList.sort()

            #print toRemoveSellerList
            #print cardList[cardId]
            #try: print cardSellerList[cardId]
            #except UnicodeEncodeError: pass

            while toRemoveSellerList:
                del cardSellerList[cardId][toRemoveSellerList.pop()]

        j = 0

        for i, card in enumerate(cardList):
            j = j + len(cardSellerList[i])
            print 'remaining seller for card', i, card.name, len(cardSellerList[i])
            #for seller in cardSellerList[i]: print seller

        print 'total seller', j
        #usedCards = set()
        # step 2 find cheapest
        print '\nstep 2: trying to find the best price'
        priceMissingCards = []
        priceMissingCards.append(0)
        sumMissingCards = 0
        bubbleSortLists(cardList, cardSellerList)
        tempSellerSet = set()
        firstCardSellers = set()
        firstCardSellersAmountDict = {}

        for shopCard, sellerList in enumerate(cardSellerList):
            sumMissingCards += sellerList[0].price
            priceMissingCards.append(sumMissingCards)
            if sellerList[0].name not in firstCardSellers:
                firstCardSellers.add(sellerList[0].name)
                firstCardSellersAmountDict[sellerList[0].name] = cardList[shopCard].amount
            else:
                firstCardSellersAmountDict[sellerList[0].name] += cardList[shopCard].amount

            for seller in sellerList:
                tempSellerSet.add(seller.name)

        comparePrice = 999999999

        sellerNameList = list(tempSellerSet)
        numberOfPosibilities = 1
        for shopCard, sellerList in enumerate(cardSellerList):
            numberOfPosibilities = numberOfPosibilities * len(sellerList)
            for seller in sellerList:
                seller.id = sellerNameList.index(seller.name)

        usedSellerCardCount = [0]*len(sellerNameList)
        print "possible combinations", numberOfPosibilities
        
        comparePrice = sumMissingCards
        for sellerName in firstCardSellers:
            amount = firstCardSellersAmountDict[sellerName]
            if amount > 17:
                comparePrice += 18500
            elif amount > 4:
                comparePrice += 12000
            else:
                comparePrice += 8500
        print "price buying simply the cheapest: ", (comparePrice/10000.0)

        """
        bubbleSortListsAsc(cardList, cardSellerList)
        sumP = 0
        for i in range(1,len(cardSellerList)):
            sumP += cardSellerList[i][0].price
        priceMissingCards = [sumP]
        for i in range(1,len(cardSellerList)):
            priceMissingCards.append(priceMissingCards[i-1]-cardSellerList[i][0].price)
        cardAmountList = []
        for c in cardList:
            cardAmountList.append(c.amount)
        start = datetime.datetime.now()
        print start
        import cProfile
        cProfile.runctx('searchLoop(ax, bx, cx, dx, ex)', globals(),
                            {'ax': cardSellerList,
                            'bx' : comparePrice,
                            'cx' : cardAmountList,
                            'dx' : priceMissingCards,
                            'ex' : usedSellerCardCount}, 'profile.tmp')

        """

        if len(cardList) > 10 and useMultiProccess > 1:
            useMultipleProcesses(comparePrice, cardSellerList, cardList, priceMissingCards, usedSellerCardCount, sellerNameList)
        else:
            a = 0
            loop = True
            if loop:
                cardList.reverse()
                cardSellerList.reverse()
                sumP = 0
                for i in range(1,len(cardSellerList)):
                    sumP += cardSellerList[i][0].price
                priceMissingCards = [sumP]
                for i in range(1,len(cardSellerList)):
                    priceMissingCards.append(priceMissingCards[i-1]-cardSellerList[i][0].price)
                cardAmountList = []
                for c in cardList:
                    cardAmountList.append(c.amount)
                import mkm_recursive
                #sys.setcheckinterval(100000)
                start = datetime.datetime.now()
                print start
                sellerIds = mkm_recursive.searchLoop(cardSellerList, # list[ list[ seller( int id, int price ), ... ], ... ]
                            comparePrice, # int
                            cardAmountList, # list[ int, ... ]
                            priceMissingCards, # list[ int, ... ]
                            usedSellerCardCount,
                            cardList)
                end = datetime.datetime.now()
                sellerIds = sellerIds[:len(cardList)]
                print end, 'start was', start, 'dur', end-start, "\n"
                sellerDict = {}
                for cardId in range(len(sellerIds)):
                    if sellerIds[cardId] in sellerDict:
                        sellerDict[sellerIds[cardId]].append(cardId)
                    else:
                        sellerDict[sellerIds[cardId]] = [cardId]

                allSum = 0
                for sellerId, cardIds in sellerDict.iteritems():
                    cardCount = 0
                    for cardId in cardIds:
                        cardCount += cardList[cardId].amount
                    print 'buy from', sellerNameList[sellerId], cardCount, 'cards', cardIds
                    sumPrice = 0
                    for cardId in cardIds:
                        for seller in cardSellerList[cardId]:
                            if seller.name == sellerNameList[sellerId]:
                                sumPrice += seller.price
                                print "    card(s):", cardList[cardId].amount, cardList[cardId].name, "- price:", (seller.price/10000.0)
                                break
                    shipping = 0
                    if cardCount > 17:
                        shipping = 1.85
                    elif cardCount > 4:
                        shipping = 1.20
                    else:
                        shipping = 0.85
                    allSum += (sumPrice/10000.0)+shipping
                    print "    sum cards:", (sumPrice/10000.0), "shipping:", shipping, "sum:", (sumPrice/10000.0)+shipping
                print '\nfinal best price: ', allSum, "you saved ", (comparePrice/10000.0) - allSum
            else:
                for card in cardList:
                    print card
                start = datetime.datetime.now()
                print start
                result, price = searchRecursive(0, comparePrice, cardSellerList, cardList, priceMissingCards,
                                                len(cardList), usedSellerCardCount)
                print roundR
                end = datetime.datetime.now()
                print end, 'start was', start, 'dur', end-start
                print '\nfinal best price: ', (price/10000.0)

                if result is not None:
                    for name, data in result.iteritems():
                        print 'buy from', sellerNameList[name], data[0], 'cards', data[1]
                        sumPrice = 0
                        for cardName in data[1]:
                            for i in range(len(cardList)):
                                if cardList[i].name == cardName:
                                    for seller in cardSellerList[i]:
                                        if seller.name == sellerNameList[name]:
                                            sumPrice += seller.price
                                            print "    card(s):", cardList[i].amount, cardName, "- price:", (seller.price/10000.0)
                                            break
                                    break
                        shipping = 0
                        if data[0] > 17:
                            shipping = 1.85
                        elif data[0] > 4:
                            shipping = 1.20
                        else:
                            shipping = 0.85
                        print "    sum cards:", (sumPrice/10000.0), "shipping:", shipping, "sum:", (sumPrice/10000.0)+shipping
        """
        import pstats

        stat = pstats.Stats('profile.tmp')
        stat.sort_stats('cumulative')
        stat.print_stats()
        #"""
        print "price buying simply the cheapest: ", (comparePrice/10000.0)
    return buyMap


# old recursive solution
def searchRecursive(currentPrice, comparePrice, cardSellerList, cardList, priceMissingCards, index, usedSellerCardCount):
    global roundR

    resultList = None
    #print (' '*(6-index)), 'cup', currentPrice, 'cop', comparePrice, 'now', cardList[index-1].name

    index=index - 1
    currentCard = cardList[index]
    foundSomething = False

    for seller in cardSellerList[index]:
        roundR += 1
        #print " " * (6 - index), currentCard.name, seller.name
        testPrice = currentPrice + seller.price

        if testPrice + priceMissingCards[index] > comparePrice:
            break

        shippingCost = 0
        cardsOfThisSeller = currentCard.amount

        if usedSellerCardCount[seller.id] > 0:
            oldCount = usedSellerCardCount[seller.id]
            cardsOfThisSeller += oldCount

            if cardsOfThisSeller >= 18 and oldCount < 18:
                shippingCost = 6500
            elif cardsOfThisSeller >= 5 and oldCount < 5:
                shippingCost = 3500
        else:
            shippingCost = 8500

        newPrice = testPrice + shippingCost
        lowestPossibleEndPrice = newPrice + priceMissingCards[index]

        if lowestPossibleEndPrice < comparePrice:
            foundSomething = True

            usedSellerCardCount[seller.id] = cardsOfThisSeller
            currentCard.seller = seller.id

            if index > 0:
                result, comparePrice = searchRecursive(newPrice, comparePrice,
                                                        cardSellerList, cardList, priceMissingCards, index,
                                                        usedSellerCardCount)
                if result is not None:
                    resultList = result
            else:
                comparePrice = newPrice
                resultList = {}

                for card in cardList:
                    if card.seller in resultList:
                        cardAmount = resultList[card.seller][0] + card.amount
                        cardsFromThisSeller = resultList[card.seller][1]
                        cardsFromThisSeller.add(card.name)
                        resultList[card.seller] = (cardAmount, cardsFromThisSeller)
                    else:
                        resultList[card.seller] = (card.amount, set([card.name]))

            usedSellerCardCount[seller.id] = cardsOfThisSeller - currentCard.amount
            currentCard.seller = None

    if not foundSomething:
        return None, comparePrice

    return resultList, comparePrice


# new search loop solution
def searchLoop(whoSellsThisCardList, # list[ list[ seller( int id, int price ), ... ], ... ]
                comparePrice, # int
                cardAmountList, # list[ int, ... ]
                priceMissingCards, # list[ int, ... ]
                usedSellerCardCount,
                cardList): # list[ int, ... ]
    index = 0
    lastIndex = len(whoSellsThisCardList)-1
    sellerCountPerCard = []
    for sellers in whoSellsThisCardList:
        sellerCountPerCard.append(len(sellers))
    zeroIndexListLength = sellerCountPerCard[0]
    sellerIdPerCard = [0 for i in range(len(whoSellsThisCardList))]
    costAddedPerCard = [0 for i in range(len(whoSellsThisCardList))]
    resultBuyCardFromSellerId = []
    workingBuyCardFromSellerId = [0 for i in range(len(whoSellsThisCardList))]
    currentPrice = 0
    rounds = 0
    sellers = whoSellsThisCardList[index]
    #import array
    #cardAmountList = array.array('i', cardAmountList)
    #sellerIdPerCard = array.array('i', sellerIdPerCard)
    #costAddedPerCard = array.array('l', costAddedPerCard)
    #usedSellerCardCount = array.array('i', usedSellerCardCount)

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
                    resultBuyCardFromSellerId = list(workingBuyCardFromSellerId)
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
    return resultBuyCardFromSellerId, comparePrice


def useMultipleProcesses(comparePrice, cardSellerList, cardList, priceMissingCards, usedSellerCardCount, sellerNameList):
    threadList = []

    for i in range(useMultiProccess):
        threadList.append("Thread-" + str(i+1))

    threadLock = Lock()
    workQueue = Queue()
    threads = []
    threadID = 1
    index = len(cardList) - 1
    currentCard = cardList[index]
    sharePrice = Value('i', comparePrice)
    resultQueue = Queue()

    for seller in cardSellerList[index]:
        usedSellerCardCount = [0]*len(usedSellerCardCount)
        usedSellerCardCount[seller.id] = currentCard.amount
        workQueue.put((list(usedSellerCardCount), seller.price+8500, seller.id))

    startTime = datetime.datetime.now()
    # Create new threads
    #for tName in threadList:
    #    thread = Process(target=processData, args=(tName, workQueue, sharePrice, resultQueue, threadLock, cardSellerList, cardList, priceMissingCards, index, sellerNameList))
    #    thread.start()
    #    threads.append(thread)
    #    threadID += 1

    # Wait for queue to empty
    while not workQueue.empty():
        time.sleep(0.01)
        pass

    # Wait for all threads to complete
    for t in threads:
        t.join()

    print datetime.datetime.now() - startTime
    print "Exiting Main Thread, end price:", sharePrice.value/10000.0
    while not resultQueue.empty():
        r = resultQueue.get(False)
    for resultName, resultUsedSeller in r.iteritems():
        print 'buy from', sellerNameList[resultName], ' ', resultUsedSeller[0],'cards', resultUsedSeller[1]



class Seller:
    def __init__(self, name, playset, quality, amount, overall, price):
        self.name = name
        self.playset = playset
        self.quality = quality
        self.amount = amount
        self.overall = overall
        self.price = price
        self.id = -1
    def __str__(self):
        return 'Seller(%s, %s, %s, %s, %s, %s, %s)' %(self.id, self.name, self.playset, self.quality, self.amount, self.overall, self.price)
    def __repr__(self):
        return self.__str__()
    def __eq__(self, other):
        return (self.name == other.name
                and self.overall == other.overall
                and self.price == other.price
                and self.amount == other.amount
                and self.quality == other.quality
                and self.playset == other.playset)
    def __cmp__(self, other):
        if self.price == other.price:
            if self.quality == other.quality:
                return cmp(other.amount, self.amount)
            return cmp(other.quality, self.quality)
        return cmp(self.price, other.price)


class Card:
    def __init__(self, name, url, quality, amount):
        self.name = name
        self.url = url
        self.quality = quality
        self.amount = amount
        self.seller = None
    def __str__(self):
        return 'Card(%s, %s, %s, %s, %s)' %(self.name, self.url[-6:], self.quality, self.amount, self.seller)
    def __repr__(self):
        return self.__str__()


def readWantList(file):
    wantMap = {}

    with open(file) as f:
        for line in f.readlines():
            # allow to comment out lines int the file
            if len(line) > 1 and line[0] != '#':
                amount, space, name = line.partition(' ')
                name = name.strip()
                if len(name) > 0:
                    if name in wantMap:
                        print "old amount", wantMap[name], amount
                        wantMap[name] = wantMap[name] + int(amount)
                    else:
                        print name, "add", amount
                        wantMap[name] = int(amount)

    return wantMap


#
# lets save money
#
def main(args = sys.argv[1:]):
    import pickle
    wantMap = None
    wantList, cardSellerList, completePrice = None, None, None

    if not os.path.exists("wantList.dump"):
        if len(args) > 0:
            if not os.path.exists(args[0]):
                print("to want file missing")
                exit()

            wantMap = readWantList(args[0])

        with requests.session() as c:
            r = c.post('https://www.magickartenmarkt.de/?action=processPost&post=login', data=loginData)

            if r.status_code == 200:
                print 'login success, lets start'
            else:
                print 'login failed'
                exit()

            wantList = []

            if wantMap is not None:
                print "adding wanted", len(wantMap), "cards from", args[0], "to wantList in mkm"
                with open("result_" + args[0], 'w') as f:
                    import random
                    import urllib
                    for cardName, amount in wantMap.iteritems():
                        sCardName = urllib.quote_plus(cardName)
                        print "search card: " + cardName
                        r = c.get("https://www.magickartenmarkt.de/ajax_metacardnames.php?searchString=" + sCardName + "&idLanguage=1")
                        if len(r.text) == 0:
                            print("warn response 0")
                            time.sleep(1)
                            r = c.get("https://www.magickartenmarkt.de/ajax_metacardnames.php?searchString=" + sCardName + "&idLanguage=1")
                        if len(r.text) == 0:
                            print("warn response 0")
                            time.sleep(1)
                            r = c.get("https://www.magickartenmarkt.de/ajax_metacardnames.php?searchString=" + sCardName + "&idLanguage=1")
                        if len(r.text) == 0:
                            print("warn response 0")
                            time.sleep(1)
                            r = c.get("https://www.magickartenmarkt.de/ajax_metacardnames.php?searchString=" + sCardName + "&idLanguage=1")
                        foundCards=r.text.split('$$**%%')
                        if len(foundCards) == 1:
                            foundCards.append('')
                        for s in foundCards[:-1]:
                            card = s.split('**')
                            f.write(str(amount) + ' ' + cardName + "\n")
                            #if card[1] == cardName:
                            if bytearray([ord(i) for i in card[1]]).decode('utf-8') == cardName.decode('utf-8'):
                                print "adding", amount, "of", cardName
                                """
                                payload = {
                                    "suggestedname":"",
                                    "cardAmount":str(amount+100),
                                    "idMetacard":card[0],
                                    "qf_IdLanguage":"1",
                                    "suggestions":card[0],
                                    "idProduct":"0",
                                    "formIdentificationNumber":str(random.randint(10000, 99999)),
                                    "condition":"GD",
                                    "idLanguage":"",
                                    "queryFilter[isFoil]":"",
                                    "queryFilter[isSigned]":"",
                                    "cardPrice":""
                                }
                                r = c.post("https://www.magickartenmarkt.de/index.php?action=processPost&post=addWant", data=payload)
                                print r.status_code
                                time.sleep(1)
                                """
                                wantList.append(Card(cardName, "/?mainPage=showMetacard&idMetacard=" + card[0], qualities[wantedQuality], int(amount)))
                                break
                            else:
                                print "name not equal", repr(cardName.decode('utf-8')), repr(bytearray([ord(i) for i in card[1]]).decode('utf-8')), repr(card[1])

            else:
                print "reading wantlist online"
                foundSomething = True
                page = 0

                while foundSomething:
                    r = c.get('https://www.magickartenmarkt.de/?mainPage=showWants&resultsPage=' + str(page))
                    page = page + 1

                    if r.status_code != 200:
                        sys.exit('wtf reponse error', r.status_code, r.reason, r)

                    tempWantList = readWants(r.text)

                    if len(tempWantList) > 0:
                        print "found number of cards on page ", page, ": ", len(tempWantList)
                        wantList.extend(tempWantList)

                        if len(tempWantList) < 50:
                            foundSomething = False
                    else:
                        foundSomething = False


            print "cards found: ", len(wantList)
            completePrice = 0
            cardSellerList = []
            sellerSet = set()

            for card in wantList:
                foundSomething = True
                sellerList = []
                page = 0
                print "get seller of card: ", card.name
                retry_counter = 0

                while foundSomething:
                    url = 'https://www.magickartenmarkt.de' + card.url + '&resultsPage=' + str(page) + '&dispLanguage=1' # English
                    page = page + 1
                    #print url
                    r = c.get(url)
                    retry_counter = retry_counter + 1
                    #print r.status_code, r.reason, url
                    error = len(r.text) == 0
                    
                    if not error:
                        try:
                            tempSellerList = getSellerList(r.text, card.amount, card.quality, card.name)
        
                            if len(tempSellerList) > 0:
                                print "found number of seller on page ", page, ": ", len(tempSellerList)
                                sellerList.extend(tempSellerList)
                            else:
                                foundSomething = False
                        except Exception as e:
                            print "Exception while parsing: " + e 
                            error = True
                        
                    if error and retry_counter < 6:
                        print 'error while reading page, retry', retry_counter, '/5'
                        time.sleep(5)
                        page = page - 1
                        foundSomething = True
                    
                if len(sellerList) != 0:
                    sellerList = sortAndCleanSellerList(sellerList, card.amount)
                    completePrice = completePrice + sellerList[0].price + 8500
                    print "number of sellers found: ", len(sellerList), 'cheapest seller', sellerList[0].name, ' ', sellerList[0].price

                    cardSellerList.append(sellerList)

                    for seller in sellerList:
                        sellerSet.add(seller.name)
                else:
                    print 'error no seller found for this card found'

            print '\nestimated price just buying all cards: ', ((completePrice - len(wantList) * 8500) / 10000.0), '+shipping', (len(wantList) * 8500 / 10000.0), '(', (completePrice/10000.0), ')', len(sellerSet)
            with open("wantList.dump", 'wb') as f:
                pickle.dump((wantList, cardSellerList, completePrice), f)
    else:
        print "unpickle"
        with open("wantList.dump", 'rb') as f:
            wantList, cardSellerList, completePrice = pickle.load(f)
        print '\nestimated price just buying all cards: ', ((completePrice - len(wantList) * 8500) / 10000.0), '+shipping', (len(wantList) * 8500 / 10000.0), '(', (completePrice/10000.0), ')'


    #and now get me the best price
    #wantList = wantList[:25]
    #cardSellerList = cardSellerList[:25]
    getCheapestPrice(wantList, cardSellerList)
    print '\nprice just buying all cards: ', ((completePrice - len(wantList) * 8500) / 10000.0), '+shipping', (len(wantList) * 8500 / 10000.0), '(', (completePrice/10000.0), ')'


if __name__ == "__main__":
    #import cProfile
    #cProfile.run('main()', 'profile.tmp')
    if sys.platform == "win32":
        import codecs
        from ctypes import WINFUNCTYPE, windll, POINTER, byref, c_int
        from ctypes.wintypes import BOOL, HANDLE, DWORD, LPWSTR, LPCWSTR, LPVOID

        original_stderr = sys.stderr

        # If any exception occurs in this code, we'll probably try to print it on stderr,
        # which makes for frustrating debugging if stderr is directed to our wrapper.
        # So be paranoid about catching errors and reporting them to original_stderr,
        # so that we can at least see them.
        def _complain(message):
            print >>original_stderr, isinstance(message, str) and message or repr(message)

        # Work around <http://bugs.python.org/issue6058>.
        codecs.register(lambda name: name == 'cp650001' and codecs.lookup('utf-8') or None)
        codecs.register(lambda name: name == 'cp650000' and codecs.lookup('utf-8') or None)

        # Make Unicode console output work independently of the current code page.
        # This also fixes <http://bugs.python.org/issue1602>.
        # Credit to Michael Kaplan <http://blogs.msdn.com/b/michkap/archive/2010/04/07/9989346.aspx>
        # and TZOmegaTZIOY
        # <http://stackoverflow.com/questions/878972/windows-cmd-encoding-change-causes-python-crash/1432462#1432462>.
        try:
            # <http://msdn.microsoft.com/en-us/library/ms683231(VS.85).aspx>
            # HANDLE WINAPI GetStdHandle(DWORD nStdHandle);
            # returns INVALID_HANDLE_VALUE, NULL, or a valid handle
            #
            # <http://msdn.microsoft.com/en-us/library/aa364960(VS.85).aspx>
            # DWORD WINAPI GetFileType(DWORD hFile);
            #
            # <http://msdn.microsoft.com/en-us/library/ms683167(VS.85).aspx>
            # BOOL WINAPI GetConsoleMode(HANDLE hConsole, LPDWORD lpMode);

            GetStdHandle = WINFUNCTYPE(HANDLE, DWORD)(("GetStdHandle", windll.kernel32))
            STD_OUTPUT_HANDLE = DWORD(-11)
            STD_ERROR_HANDLE  = DWORD(-12)
            GetFileType = WINFUNCTYPE(DWORD, DWORD)(("GetFileType", windll.kernel32))
            FILE_TYPE_CHAR   = 0x0002
            FILE_TYPE_REMOTE = 0x85000
            GetConsoleMode = WINFUNCTYPE(BOOL, HANDLE, POINTER(DWORD)) \
                                 (("GetConsoleMode", windll.kernel32))
            INVALID_HANDLE_VALUE = DWORD(-1).value

            def not_a_console(handle):
                if handle == INVALID_HANDLE_VALUE or handle is None:
                    return True
                return ((GetFileType(handle) & ~FILE_TYPE_REMOTE) != FILE_TYPE_CHAR
                        or GetConsoleMode(handle, byref(DWORD())) == 0)

            old_stdout_fileno = None
            old_stderr_fileno = None
            if hasattr(sys.stdout, 'fileno'):
                old_stdout_fileno = sys.stdout.fileno()
            if hasattr(sys.stderr, 'fileno'):
                old_stderr_fileno = sys.stderr.fileno()

            STDOUT_FILENO = 1
            STDERR_FILENO = 2
            real_stdout = (old_stdout_fileno == STDOUT_FILENO)
            real_stderr = (old_stderr_fileno == STDERR_FILENO)

            if real_stdout:
                hStdout = GetStdHandle(STD_OUTPUT_HANDLE)
                if not_a_console(hStdout):
                    real_stdout = False

            if real_stderr:
                hStderr = GetStdHandle(STD_ERROR_HANDLE)
                if not_a_console(hStderr):
                    real_stderr = False

            if real_stdout or real_stderr:
                # BOOL WINAPI WriteConsoleW(HANDLE hOutput, LPWSTR lpBuffer, DWORD nChars,
                #                           LPDWORD lpCharsWritten, LPVOID lpReserved);

                WriteConsoleW = WINFUNCTYPE(BOOL, HANDLE, LPWSTR, DWORD, POINTER(DWORD), \
                                            LPVOID)(("WriteConsoleW", windll.kernel32))

                class UnicodeOutput:
                    def __init__(self, hConsole, stream, fileno, name):
                        self._hConsole = hConsole
                        self._stream = stream
                        self._fileno = fileno
                        self.closed = False
                        self.softspace = False
                        self.mode = 'w'
                        self.encoding = 'utf-8'
                        self.name = name
                        self.flush()

                    def isatty(self):
                        return False
                    def close(self):
                        # don't really close the handle, that would only cause problems
                        self.closed = True
                    def fileno(self):
                        return self._fileno
                    def flush(self):
                        if self._hConsole is None:
                            try:
                                self._stream.flush()
                            except Exception, e:
                                _complain("%s.flush: %r from %r"
                                          % (self.name, e, self._stream))
                                raise

                    def write(self, text):
                        try:
                            if self._hConsole is None:
                                if isinstance(text, unicode):
                                    text = text.encode('utf-8')
                                self._stream.write(text)
                            else:
                                if not isinstance(text, unicode):
                                    text = str(text).decode('utf-8')
                                remaining = len(text)
                                while remaining > 0:
                                    n = DWORD(0)
                                    # There is a shorter-than-documented limitation on the
                                    # length of the string passed to WriteConsoleW (see
                                    # <http://tahoe-lafs.org/trac/tahoe-lafs/ticket/1232>.
                                    retval = WriteConsoleW(self._hConsole, text,
                                                           min(remaining, 10000),
                                                           byref(n), None)
                                    if retval == 0 or n.value == 0:
                                        raise IOError("WriteConsoleW returned %r, n.value = %r"
                                                      % (retval, n.value))
                                    remaining -= n.value
                                    if remaining == 0: break
                                    text = text[n.value:]
                        except Exception, e:
                            _complain("%s.write: %r" % (self.name, e))
                            raise

                    def writelines(self, lines):
                        try:
                            for line in lines:
                                self.write(line)
                        except Exception, e:
                            _complain("%s.writelines: %r" % (self.name, e))
                            raise

                if real_stdout:
                    sys.stdout = UnicodeOutput(hStdout, None, STDOUT_FILENO,
                                               '<Unicode console stdout>')
                else:
                    sys.stdout = UnicodeOutput(None, sys.stdout, old_stdout_fileno,
                                               '<Unicode redirected stdout>')

                if real_stderr:
                    sys.stderr = UnicodeOutput(hStderr, None, STDERR_FILENO,
                                               '<Unicode console stderr>')
                else:
                    sys.stderr = UnicodeOutput(None, sys.stderr, old_stderr_fileno,
                                               '<Unicode redirected stderr>')
        except Exception, e:
            _complain("exception %r while fixing up sys.stdout and sys.stderr" % (e,))


    main()
