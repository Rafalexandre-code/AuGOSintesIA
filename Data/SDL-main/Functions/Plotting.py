import numpy as np
import matplotlib.pyplot as plt

def saveNoiseLinePlots(Y, noises, beleifmodel='GPR', dimension=3, randsampnum=10, surrogate='ackley', filepath='', ylabel='Best Response'):
    fig, ax = plt.subplots()
    legendvals = [str(noise) + ' Noise' for noise in noises]
    x = np.arange(1, len(Y[0])+1)
    for ii in range(len(legendvals)):
        plt.plot(x, Y[ii], label=legendvals[ii])
    plt.xlabel('Sample Number')
    plt.ylabel(ylabel)
    plt.title(surrogate + ', ' + beleifmodel +  ', ' + str(dimension)+'D, ' + str(randsampnum) + ' Random Samples')
    plt.legend()
    plt.savefig(filepath + '.png', dpi=400)
    plt.close()

def saveDimensionLinePlots(Y, dimensions, surrogate='ackley', filepath='', ylabel='Best Response'):
    """Best-so-far curves of one optimization run per design-space dimension."""
    fig, ax = plt.subplots()
    for ii, dim in enumerate(dimensions):
        plt.plot(np.arange(1, len(Y[ii])+1), Y[ii], label=str(dim) + 'D')
    plt.xlabel('Sample Number')
    plt.ylabel(ylabel)
    plt.title(surrogate + ', dimension screen')
    plt.legend()
    plt.savefig(filepath + '.png', dpi=400)
    plt.close()

def saveBeliefLinePlots(Y, beliefmodels, noise=0, dimension=3, randsampnum=10, surrogate='ackley', filepath='', ylabel='Best Response'):
    fig, ax = plt.subplots()
    legendvals = [beliefmodel for beliefmodel in beliefmodels]
    x = np.arange(1, len(Y[0])+1)
    for ii in range(len(legendvals)):
        plt.plot(x, Y[ii], label=legendvals[ii])
    plt.xlabel('Sample Number')
    plt.ylabel(ylabel)
    plt.title(surrogate + ', ' + str(noise) + ' Noise, ' + str(dimension)+'D, ' + str(randsampnum) + ' Random Samples')
    plt.legend()
    plt.savefig(filepath + '.png', dpi=400)
    plt.close()
