import numpy as np
import pandas as pd
import ForestSelection
import kernels
import ecologydata as ecodata
from scipy.spatial.distance import cdist
from simple_queue import redis_queue
import redis
import time
import os
import logging

REDIS_HOST=os.environ["REDIS_HOST"]
REDIS_PORT=6379
rq = redis_queue(redis_host = REDIS_HOST, redis_port=REDIS_PORT)
rq.q_delete("queue")
rq.q_delete("wip")

# Run this on a computer in which the 'tree' package is installed
import tree

#################################################################################################### 
# Program starts here
# Note: I got rid of all the printing and plotting steps in this script, just to simplify things. We can add 
# it back later on if we want to.

# To save time, this function can remove the candidate forests nearby the training forests within a radius of 0.05
# This is so that our program avoid checking forests that we are already sure we don't want to check anyway
def removeClosebyCandidates(candidateCharacteristics, trainingCharacteristics):

    distsq = cdist(candidateCharacteristics, trainingCharacteristics, 'sqeuclidean')
    (c, t) = distsq.shape
    distmask = np.ones((c, t), dtype = bool)
    distmask[distsq < 0.05**2] = False
    charmask = np.ones(c, dtype = bool) 
    charmask[distmask.sum(axis = 1) < t] = False
    return(candidateCharacteristics[charmask])

def main():    

    # This is the total number of jobs we would like to do
    TOTALJOBS = 15

    ### Initialisation stage
    # We will be using the Matern 3/2 Kernel
    kernelchoice = kernels.m32

    # This is the maximum number of training forests we will start off with
    numberOfTrainingForests = 10
    numberOfCandidateForests = 500

    # We will be using these trait values for now
    traits = np.linspace(-5, 0, num = 50)

    ### Set Randomisation and Generation Stage
    # Permute all the possible forest IDs to randomise the training forest choices
    allForestIDsPermutated = np.random.permutation(int(np.max(ecodata.ID)))

    # Determining training set
    trainingForestIDs = allForestIDsPermutated[:numberOfTrainingForests]

    # Getting our actual training set
    (Xt, yt, idt) = ecodata.getForests(trainingForestIDs, logtimedisturbance = True)
    actualTrainingForestIDs = pd.unique(idt)
    actualNumberOfTrainingForests = actualTrainingForestIDs.shape[0]
    actualNumberOfTrainingDataPoints = idt.shape[0]

    # Obtain the forest characteristics of the training set
    trainingCharacteristics = ecodata.getForestCharacteristics(trainingForestIDs, logtimedisturbance = True)[0]

    # Initialise the Gaussian Process Forest Selection Class
    gpfs = ForestSelection.ForestSelectionProcess(Xt, yt, kernel = kernelchoice)

    # Train the model, starting with the following parameters to maybe speed up the initial training stage
    initialParams = np.array([5.2548212808, 6.1294312135, 0.8751383158, 1.4410416625])
    initialSigma = 3.51958264701e-05
    gpfs.setInitialKernelParams(initialParams)
    gpfs.setInitialSigma(initialSigma)
    gpfs.learn()

    # So far we have not allocated any jobs
    currentNumberOfJobs = 0

    # This is the last time we displayed anything (only for printing purposes)
    displaytime = 0

    # Simulations
    simulation = 1

    ### Selection Stage
    stop = False
    while not stop:
        #stop = currentNumberOfJobs >= TOTALJOBS

        # Fill the queue if not filled
        if currentNumberOfJobs <= TOTALJOBS:

            # Re-Generate 500 candidate forests randomly where logTD is in [0, 5] and B4 is in [0, 3]
            candidateCharacteristicsAll = np.random.rand(500, 2)
            candidateCharacteristicsAll *= np.array([5, 3])

            # Remove candidates nearby the training forests to save some time
            candidateCharacteristics = removeClosebyCandidates(candidateCharacteristicsAll, trainingCharacteristics)

            # Choose the best forest characteristics to look at 
            (oneBestChars, oneVirtualIndices) = gpfs.selectMultipleBestForests(candidateCharacteristics, traits, topN = 1)
            LOGGER.info("Selected: {0}".format(oneBestChars[0]))

            rq.q_push("queue",simulation)
            rq.dict_update(simulation,"p1",np.exp(oneBestChars[0][0]))
            rq.dict_update(simulation,"p2",oneBestChars[0][1])
            rq.dict_update(simulation,"traits",str(traits))
            rq.dict_update(simulation,"virtualIndex",oneVirtualIndices[0])
            rq.dict_update(simulation,"status","queue")
            simulation += 1
            
            currentNumberOfJobs += 1

        wip_simulations = rq.q_get("wip")
        for i in wip_simulations:
            if rq.dict_get(i).get("status") != "done":
               continue 

            # One job has finished
            currentNumberOfJobs -= 1

            # Grab the first result
            yActual = rq.dict_get(i).get("yActual")
            finishedVirtualIndex = rq.dict_get(i).get("virtualIndex")
            rq.q_remove("wip",i)

            charBeingUpdated = gpfs.getCharacteristicFromVirtualIndex(finishedVirtualIndex)

            # Update our model
            LOGGER.info("{0}".format(charBeingUpdated))
            gpfs.updateOneVirtualForest(finishedVirtualIndex, yActual)
            LOGGER.info("Finished Updating Forest [ {0} more to update]".format(rq.q_len("wip")))
       
        time.sleep(5)

if __name__ == "__main__":
    log_filename = "/home/data/logs/tree.log"
    LOGGER = logging.getLogger()
    syslog_format = (' %(levelname)s ' + '%(filename)s:%(lineno)d: %(message)s')
    logging.basicConfig(
        level=logging.INFO,
        filename=log_filename,
        format='%(asctime)s.%(msecs)d localhost ' + syslog_format,
        datefmt='%Y-%m-%dT%H:%M:%S')

    main()

