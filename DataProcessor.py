
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use("agg")
from SetDataContainer import SetDataContainer as sdc
from MapInfo import MapInfo as mi
from MapInfo import MapInfos
from ResetTracker import ResetTracker
import os


class DataProcessor:
    '''Converts the pandas dataframe containing set data into matplotlib images
       and saves the to the appropriate folder'''

    def __init__(self, baseDirectory=None, posMap=None):
        self.sdc = sdc()
        self.rotation = ""
        if baseDirectory is not None:
            self.baseDirectory = baseDirectory
            self.locMapDirectory = baseDirectory + "/LocationMaps/"
            self.callMapDirectory = baseDirectory + "/SetCallMaps/"
            self.ptaMapDirectory = baseDirectory + "/PTAMaps/"
            self.IMPMAPDirectory = baseDirectory + "/ImportantTimesMaps/"
            self.posResetDirectory = baseDirectory + "/PositiveResetMaps/"
            self.negResetDirectory = baseDirectory + "/NegativeResetMaps/"
            self.runBreakDirectory = baseDirectory + "/RunBreakMaps/"
            self.createDirectory(self.locMapDirectory)
            self.createDirectory(self.callMapDirectory)
            self.createDirectory(self.ptaMapDirectory)
            self.createDirectory(self.IMPMAPDirectory)
            self.createDirectory(self.posResetDirectory)
            self.createDirectory(self.negResetDirectory)
            self.createDirectory(self.runBreakDirectory)
        self.sets = [["Black", "Middle", "Red"], ["N/A", "Pipe", "C-Ball"]]
        self.hasPTA = False
        self.hasReset = False
        self.hasIMP = False
        self.hasPosReset = False
        self.hasNegReset = False
        self.hasRun = False
        self.lastChoice = ""
        self.locFileInfos = MapInfos()
        self.callFileInfos = MapInfos()
        self.ptaFileInfos = MapInfos()
        self.impFileInfos = MapInfos()
        self.posResetInfos = MapInfos()
        self.negResetInfos = MapInfos()
        self.runBreakInfos = MapInfos()
        self.PTAMaking = False
        self.posInferenceMap = posMap

    def createDirectory(self, path):
        '''Creates a directory for a given map type if it does not already exist'''

        try:
            os.mkdir(path)
        except FileExistsError:
            pass

    def parsedata(self, data, rotation=None, passedPTAMap=None):
        '''iterates over the data one row at a time and parses it into the data container'''

        # used to track if a reset has occurred
        rt = ResetTracker()
        if rotation is not None:
            self.rotation = rotation
        else:
            self.rotation = data.iloc[0]["rotation"]

        for index, row in data.iterrows():

            # extract all the information I need
            lockey = row["location"]
            choicekey, middleCall = self.stripDelims(row["choice"])
            result = row["result"]
            hitResult = result[len(result)-1]
            chosenPlayer = result[:-1]
            rt.currentHitter = chosenPlayer
            passer = row["passer"]
            home, away = row["score"].split("-")
            isRun = row["run"]
            set = row["set"]
            rt.currentHitSet = set

            self.sdc.addToLocMap(lockey, choicekey, hitResult)
            self.sdc.addToSetCallMap(middleCall, choicekey, hitResult)
            if int(passer) == int(chosenPlayer):
                self.hasPTA = True
                self.sdc.addToPTAMap(choicekey, hitResult)
            else:
                self.sdc.addPass(str(passer))
            if self.isImportantTime((int(home), int(away)), int(set)):
                self.hasIMP = True
                self.sdc.addToIMPMAP(choicekey, hitResult)
            if rt.isPosReset():
                self.hasPosReset = True
                self.sdc.addToPosResetMap(choicekey, hitResult)
            if rt.isNegReset():
                self.hasNegReset = True
                self.sdc.addToNegResetMap(choicekey, hitResult)
            if isRun == "end":
                self.hasRun = True
                self.sdc.addToRunBreakMap(choicekey, hitResult)

            rt.updateOld(hitResult)
        self.sdc.addPasses(self.posInferenceMap)
        if passedPTAMap is not None:
            self.sdc.ptaMap = passedPTAMap

    def createPlots(self):

        title = "On passes to location {} in rotation {}"
        filename = "Location | {} | {}.png"
        for items in self.sdc.getLocMapItems():
            self.createType2Map(title, self.locMapDirectory, filename, self.locFileInfos, items)

        title = "When the middle is running {} in rotation {}"
        filename = "Setter Call | {} | {}.png"
        for items in self.sdc.getSetCallMapItems():
            self.createType2Map(title, self.callMapDirectory, filename, self.callFileInfos, items)

        if self.hasPTA:
            self.PTAMaking = True
            title = "On pass to attack in rotation {}"
            filename = "PTA | {}.png"
            self.createType1Map(self.sdc.ptaMap, title, self.ptaMapDirectory, filename, self.ptaFileInfos)
            self.PTAMaking = False

        if self.hasIMP:
            title = "Important time in rotation {}"
            filename = "IMP | {}.png"
            self.createType1Map(self.sdc.IMPMAP, title, self.IMPMAPDirectory, filename, self.impFileInfos)

        if self.hasPosReset:
            title = "Positive reset in rotation {}"
            filename = "PR | {}.png"
            self.createType1Map(self.sdc.posResetMap, title, self.posResetDirectory, filename, self.posResetInfos)

        if self.hasNegReset:
            title = "Negative reset in rotation {}"
            filename = "NR | {}.png"
            self.createType1Map(self.sdc.negResetMap, title, self.negResetDirectory, filename, self.negResetInfos)

        if self.hasRun:
            title = "Run breaking decision in rotation {}"
            filename = "RB | {}.png"
            self.createType1Map(self.sdc.runBreakMap, title, self.runBreakDirectory, filename, self.runBreakInfos)


    def createType1Map(self, m, title, directory, filenamePart, infos):
        fig, ax, im, captionString = self.createFigure(m)
        # if fig is None tham no data for this existed
        if fig is None:
            return
        ax.set_title(title.format(self.rotation))
        fig.colorbar(im)
        filename = directory + filenamePart.format(self.rotation)
        infos.add(mi(filename, captionString, self.rotation))
        fig.savefig(filename)
        plt.close(fig)

    def createType2Map(self, title, directory, filenamePart, infos, items):
        identifier = items[0]
        fig, ax, im, captionString = self.createFigure(items[1])
        if fig is None:
            return
        ax.set_title(title.format(identifier, self.rotation))
        fig.colorbar(im)
        filename = directory + filenamePart.format(self.rotation, identifier)
        infos.add(mi(filename, captionString, self.rotation))
        fig.savefig(filename)
        plt.close(fig)

    def createFigure(self, items):
        p, kp, eff, n, captionString = self.createChoiceArray(items)
        if p.shape == (0,):
            return None, None, None, None

        fig, ax = plt.subplots()
        im = ax.imshow(p, cmap="Greens", vmax=1.0, vmin=0.0)

        ax.set_xticklabels([])
        ax.set_yticklabels([])

        for i in range(2):
            for j in range(3):
                percent = "{:.2f}%".format(round(p[i][j] * 100, 2))
                kPercent = "{:.2f}%".format(round(kp[i][j] * 100, 2))
                efficiency = "{:.2f}%".format(round(eff[i][j] * 100, 2))
                if self.PTAMaking:
                    passSetPercent = n[i][j][2] / float(n[i][j][3]) * 100 if n[i][j][3] != 0 else 0.0
                    text = "{}\n{:.2f}% of passes\n{} Kill%\n{} Eff\n{} total sets\n{} total passes".format(self.sets[i][j], passSetPercent,
                                                                                           kPercent, efficiency,
                                                                                           n[i][j][2], n[i][j][3])
                else:
                    text = "{}\n{} of sets\n{} Kill%\n{} Eff\n{} total sets".format(self.sets[i][j], percent,
                                                                                       kPercent, efficiency, n[i][j][2])
                ax.text(j, i, text, ha="center", va="center", color="black")
        return fig, ax, im, captionString

    def createChoiceArray(self, m):
        middleStuff = []
        # combine middle sets into one
        for i in range(4):
            middleStuff.append(m["31"][i] + m["51"][i] + m["61"][i] + m["FS"][i])

        # create list which stats for each position in order
        numbers = [[m["BK"], middleStuff, m["Red"]],
                   [self.sdc.initSetInformation(), m["p"], m["C"]]]
        total = sum([k[2] for k in numbers[0]])
        total += sum([k[2] for k in numbers[1]])
        total = float(total)

        # create stats list for middle sets individually
        allMids = [m["31"], m["51"], m["61"], m["FS"]]
        stats = []
        for mid in allMids:
            if mid[2] != 0:
                kill = round(mid[0] / mid[2], 2) * 100
                killEff = round((mid[0] - mid[1]) / mid[2], 2) * 100
            else:
                kill = 0.0
                killEff = 0.0
            if self.PTAMaking:
                totalOf = round(mid[2] / float(mid[3]), 2) * 100 if mid[3] != 0 else 0.0
            else:
                totalOf = round(mid[2] / total, 2) * 100 if total != 0 else 0.0
            stats.append([kill, killEff, totalOf])

        # generate caption string for middle sets
        captionString = "\n"
        sets = ["31", "51", "61", "FS"]
        for i in range(len(stats)):
            if self.PTAMaking:
                captionString += "{}: {:.2f}% kill, {:.2f}% kill eff, {:.2f}% of total passes \n".format(sets[i],
                                                                                                         stats[i][0],
                                                                                                         stats[i][1],
                                                                                                         stats[i][2])
            else:
                captionString += "{}: {:.2f}% kill, {:.2f}% kill eff, {:.2f}% of total \n".format(sets[i], stats[i][0], stats[i][1], stats[i][2])
        setDumps = "Setter Dumps: {:.0f} kills on {} attempts\n".format(m["D"][0], m["D"][2])
        captionString += setDumps
        percent = []
        killPercent = []
        efficiency = []
        if total > 0:
            for j in range(2):
                row = []
                kpRow = []
                effRow = []
                for i in range(3):
                    kills = numbers[j][i][0]
                    errors = numbers[j][i][1]
                    totalSets = numbers[j][i][2]
                    # percentage of total sets given
                    if self.PTAMaking:
                        total = float(numbers[j][i][3])
                    row.append(totalSets/total if total > 0 else 0.0)
                    if totalSets == 0:
                        kpRow.append(0.0)
                        effRow.append(0.0)
                    else:
                        # kill percentage
                        kpRow.append(kills/float(totalSets))
                        # kill efficiency
                        effRow.append((kills-errors) / float(totalSets))

                percent.append(row)
                killPercent.append(kpRow)
                efficiency.append(effRow)
        arr = np.array(percent)
        kpArr = np.array(killPercent)
        effArr = np.array(efficiency)

        # print(numbers)

        return arr, kpArr, effArr, numbers, captionString

    @staticmethod
    def stripDelims(string):
        actualCall = "None"
        middleCall = string[0]
        middleRuns = ["31", "51", "61"]
        if middleCall == "(":
            actualCall = "51"
        elif middleCall == "[":
            actualCall = "31"
        elif middleCall == "<":
            actualCall = "61"
        elif string in middleRuns:
            actualCall = string

        string = string.translate(str.maketrans("", "", "(){}<>[]"))
        return string, actualCall

    def getInfos(self):
        return (self.locFileInfos, self.callFileInfos, self.ptaFileInfos,
                self.impFileInfos, self.posResetInfos, self.negResetInfos, self.runBreakInfos)

    def isImportantTime(self, score, gameSet):
        if gameSet < 5:
            return (score[0] >= 20 or score[1] >= 20) and abs(score[0] - score[1]) <= 2
        else:
            return (score[0] >= 10 or score[1] >= 10) and abs(score[0] - score[1]) <= 2


