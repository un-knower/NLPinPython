import numpy as np
import json
import time


def loadData(filename):
    dataArr = []
    fr = open(filename)
    for line in fr.readlines():
        lineArr = line.strip().split('\t')
        row = map(float, lineArr)
        dataArr.append(row)
    return np.mat(dataArr)


def binSplit(dataMat, featureId, value):
    idx0 = np.nonzero(dataMat[:, featureId] > value)[0]
    idx1 = np.nonzero(dataMat[:, featureId] <= value)[0]
    return dataMat[idx0], dataMat[idx1]


def regLeaf(dataMat):
    # caluate the mean value for each leaf
    return np.mean(dataMat[:, -1])


def regError(dataMat):
    # calculate the variance
    return np.var(dataMat[:, -1]) * np.shape(dataMat)[0]


def chooseBestFeature(dataMat, leafType=regLeaf, errType=regError, ops=(1, 4)):
    """
    Parameters
    ------------
    dataMat : numpy.matrix
    leafType : regLeaf(dataMat), optional
    errType : regError(dataMat), optional
    ops: (tolS, tolN), optional
        for prepruning trees
        tolS is a tolerance on the error reduction
        tolN is the minimum data instances to include in a split
    """
    tolS = ops[0]
    tolN = ops[1]
    # if all values are the same, quit and return the values
    if len(set(dataMat[:, -1].T.tolist()[0])) == 1:
        return None, leafType(dataMat)
    m, n = np.shape(dataMat)
    S = errType(dataMat)  # sum of dataMat error
    bestS = np.inf
    bestIndex = 0
    bestValue = 0
    for featIndex in range(n - 1):
        for featValue in set(dataMat[:, featIndex].T.tolist()[0]):
            mat0, mat1 = binSplit(dataMat, featIndex, featValue)
            if np.shape(mat0)[0] < tolN or np.shape(mat1)[0] < tolN:
                continue
            newS = errType(mat0) + errType(mat1)
            if newS < bestS:
                bestS = newS
                bestIndex = featIndex
                bestValue = featValue

    # if the decrease (S - newS) is less than threshold tolS,
    # then stop spliting
    if (S - bestS) < tolS:
        return None, leafType(dataMat)

    mat0, mat1 = binSplit(dataMat, bestIndex, bestValue)
    if np.shape(mat0)[0] < tolN or np.shape(mat1)[0] < tolN:
        return None, leafType(dataMat)
    return bestIndex, bestValue


def createTree(dataMat, leafType=regLeaf, errType=regError, ops=(1, 4)):
    featIndex, featValue = chooseBestFeature(dataMat, leafType, errType, ops)
    if featIndex is None:
        return featValue

    retTree = {}
    retTree['featIndex'] = featIndex
    retTree['featValue'] = featValue

    nodeStack = []
    nodeStack.append(retTree)
    dataStack = []
    dataStack.append(dataMat)
    while len(nodeStack) != 0:
        curNode = nodeStack.pop()
        if curNode['featIndex'] is None:
            continue
        #  cannot always binSplit dataMat, need a stack
        curMat = dataStack.pop()
        leftMat, rightMat = binSplit(curMat, curNode['featIndex'], curNode['featValue'])
        leftIndex, leftValue = chooseBestFeature(leftMat, leafType, errType, ops)
        rightIndex, rightValue = chooseBestFeature(rightMat, leafType, errType, ops)
        # need to judge whethe leftIndex is None
        if rightIndex is None:
            curNode['right'] = rightValue
        else:
            rightTree = {}
            rightTree['featIndex'] = rightIndex
            rightTree['featValue'] = rightValue
            curNode['right'] = rightTree
            dataStack.append(rightMat)
            nodeStack.append(rightTree)

        if leftIndex is None:
            curNode['left'] = leftValue
        else:
            leftTree = {}
            leftTree['featIndex'] = leftIndex
            leftTree['featValue'] = leftValue
            curNode['left'] = leftTree
            dataStack.append(leftMat)
            nodeStack.append(leftTree)

    return retTree


def isTree(obj):
    return type(obj).__name__ == 'dict'


def getMean2(tree):
    """
    @deprecated
    non-recurrent algorithm, but cost more time on small data set
    """
    nodeStack = []
    nodeStack.append(tree)
    stateStack = []
    stateStack.append(None)
    curNode = tree
    while len(nodeStack) != 0:
        if isTree(curNode['left']):
            curNode = curNode['left']
            nodeStack.append(curNode)
            stateStack.append('left')
        if isTree(curNode['right']):
            curNode = curNode['right']
            nodeStack.append(curNode)
            stateStack.append('right')
        if not isTree(curNode['left']) and not isTree(curNode['right']):
            curNode = nodeStack.pop()
            tmp = stateStack.pop()
            parent = nodeStack[-1] if len(nodeStack) != 0 else None
            if tmp is not None:
                parent[tmp] = (curNode['left'] + curNode['right']) / 2.0
                curNode = parent
            else:
                tree = (curNode['left'] + curNode['right']) / 2.0
    return tree


def getMean(tree):
    if isTree(tree['right']):
        tree['right'] = getMean(tree['right'])
    if isTree(tree['left']):
        tree['left'] = getMean(tree['left'])
    return (tree['left'] + tree['right']) / 2.0


def prune(tree, dataMat):
    # no data to split
    if np.shape(dataMat)[0] == 0:
        return getMean(tree)
    if isTree(tree['left']) or isTree(tree['right']):
        lMat, rMat = binSplit(dataMat, tree['featIndex'], tree['featValue'])
    if isTree(tree['left']):
        tree['left'] = prune(tree['left'], lMat)
    if isTree(tree['right']):
        tree['right'] = prune(tree['right'], rMat)

    if not isTree(tree['left']) and not isTree(tree['right']):
        lMat, rMat = binSplit(dataMat, tree['featIndex'], tree['featValue'])
        errNoMerge = np.sum(np.power(lMat[:, -1] - tree['left'], 2))
        errNoMerge = np.sum(np.power(rMat[:, -1] - tree['right'], 2)) + errNoMerge
        treeMean = (tree['left'] + tree['right']) / 2.0
        errMerge = np.sum(np.power(dataMat[:, -1] - treeMean, 2))
        if errMerge < errNoMerge:
            print 'merging'
            return treeMean
        else:
            return tree
    else:
        return tree


if __name__ == '__main__':
    print 'start'
    dataMat = loadData('ex2test.txt')
    # subMat1, subMat2 = binSplit(dataMat, 2, 2.4)
    retTree = createTree(dataMat, ops=(0, 1))
    retTree = prune(retTree, dataMat)
    print json.dumps(retTree, indent=4)
    # start = time.clock()
    # print getMean2(retTree)
    # print 'time:', time.clock() - start
    # start = time.clock()
    # print getMean(retTree)
    # print 'time:', time.clock() - start
