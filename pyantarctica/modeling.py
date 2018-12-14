#
# Copyright 2017-2018 - Swiss Data Science Center (SDSC)
# A partnership between École Polytechnique Fédérale de Lausanne (EPFL) and
# Eidgenössische Technische Hochschule Zürich (ETHZ).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
import pandas as pd

##############################################################################################################
def retrieve_model_av_std(summary):
    """
        This function takes as argument the dicitonary given by functions in baselines_scripts and returns model averages and standard deviations of accuracies and weightsself.

        :param summary: dictionary of model outputs
        :reuturns: dictionary of summary of summary statistics
    """

    exps_ = [s[:-2] for s in list(summary.keys())]
    exps = set(exps_)

    NUM_REP = int(len(exps_) / len(exps))
    results = {}
    for name_ in exps:
    #     print(name_)
        results[name_] = {}

        init_ = True
        for nre in range(0,NUM_REP,1):
            sub_res = summary[name_ + '_' + str(nre)]
            if init_:
                for sub_, val_ in sub_res.items():
                        exec(sub_ + '= []' )
                        init_ = False

            for sub_, val_ in sub_res.items():
    #             print('-> ', sub_,val_)
                exec(sub_+'.append(val_)')

        for sub_ in sub_res:
            if '_hat' not in sub_:
                exec(sub_ + '= np.array(' + sub_ + ')')
    #         print(eval(sub_))

        for sub_ in sub_res:
            if '_hat' not in sub_:
                exec('results[name_][sub_] = np.append(np.mean([' + sub_ + '], axis=1), np.std([' + sub_ + '], axis=1),axis=0)')
            else:
                exec('results[name_][sub_] =' + sub_)

    return results

##############################################################################################################
def sample_trn_test_index(index,split=2.0/3,mode='final',group=20,
    options={'submode': 'interpolation', 'samples_per_interval': 1, 'temporal_inteval': '1H'}):

    """
        Given a dataframe index, sample indexes for different training and test splits. It is possible to create different test subgroups to test temporal consistency of models.

        :param index: dataframe index from which sample training and test locations from (required to return a dataframe as well, without losing the original indexing)
        :param split: float, training to test datapoints ratios.
        :param group: int or 'all', providing the number of samples in each test subgroup, if needed, and for other things.
        :param mode: string
            |    - 'prediction' : first split used for training, rest for testing
            |    - 'interpolation': pure random sampling

            |    - 'middle' : samples equal groups for training and groups for testing, with size specified by group, independent training are all indexed by 1 and the tests are independent groups with label l in {2,...}, uniformly distributed
            |    - 'initial' : recursively uses 'final' but on inverted indexes
            |    - 'training_shifted' : indexes training points in temporally shifted lags, with group specifying how many points _before_ the training set is sampled.
            |       e.g. 2 2 2 2 2 2 1 1 1 1 1 1 1 1 1 1 1 2 2 2 2 where the first 6 "2"s are def in group
        :param options: additional options, for now only for temporal subsampling.

        :returns: a dataframe with an index column, with integres i denoting wether a datapoint is training (i=1) or test (i=2,...)
    """

    # data size
    s0 = len(index)

    #    mode = mode[0]
    # initial indexing  
    ind_set = np.ones((s0,1))

    # how many training (s1) and test (s2)
    s1 = int(np.floor(s0*split))
    s2 = s0-s1

    if mode == 'prediction':
        if group == 'all':
            ind_set[(s1+1):] = 2
        else:
            for bl, ii in enumerate(range(0,s2,group)):
                ind_set[(s1+1+ii):(s1+ii+1+group)] = bl+2

    elif mode=='interpolation':
        ind_set[s1+1:] = 2
        np.random.shuffle(ind_set)

    elif mode=='temporal_subsampling':

        sub_mode = options['submode'] # interpolation or prediction
        per_temp = options['samples_per_interval'] # how many samples to take per unit of temporal int
        time_int = options['temporal_interval']

        ind_set = np.zeros((s0,1)) # override initial indexing...
        ind_set = pd.DataFrame(ind_set, index=index)

        init = ind_set.index[0].round(time_int[-1])
        endit = ind_set.index[-1].round(time_int[-1])

        samp_ints = pd.date_range(start=init, end=endit, freq=time_int)

        tr_ts_splits = np.ones((len(samp_ints),1))
        tr_ts_splits[int(np.floor(len(samp_ints)*split))+1:] = 2

        if sub_mode == 'interpolation':
            np.random.shuffle(tr_ts_splits)
        elif sub_mode == 'prediction':
            _ = None #do nothing

        # sample per_temp examples every time_int. time_ints are split randomly for training and testing
        b = []

        for t_i, t_ in enumerate(samp_ints[0:]):
            to_time = t_+pd.to_timedelta(time_int)-pd.to_timedelta('1S')
            # print(t_,to_time)
            sub_s = ind_set.loc[t_:to_time,:]

            if per_temp > 1:
                samp_frac = per_temp

            elif (per_temp>0)&(per_temp<=1):
                samp_frac = int(np.floor(per_temp*sub_s.shape[0]))

            # print(per_temp, samp_frac)

            if sub_s.shape[0] > samp_frac:
                inds_to_sam = sub_s.sample(n=samp_frac).sort_index().index
                # print(inds_to_sam)
                ind_set.loc[inds_to_sam] = tr_ts_splits[t_i][0]
                # print(ind_set.loc[inds_to_sam])

        ind_set = ind_set.values

    elif mode == 'middle':
        lab = 2
        for bl, ii in enumerate(range(0,s1+s2,group)):
            print(int((bl%(split))*100))
            if int((bl%(split))) == 0:
                ind_set[(1+ii):(ii+1+group)] = 1
            else:
                ind_set[(1+ii):(ii+1+group)] = lab
                lab += 1

    elif mode=='initial':
        ind_set = sample_trn_test_index(np.ones((len(index),1)),split=2.0/3,N_tst=20,mode='final')
        ind_set = ind_set[-1::-1]

    elif mode=='training_shifted':
        ind_set[0:group] = 2
        ind_set[(group+s1):] = 3

    return pd.DataFrame(ind_set.reshape(-1,1), index=index, columns=['ind'])

##############################################################################################################
def compute_mutual_information(X,Y,nbins=128,sigma_smooth=2):
    from scipy import ndimage

    # 1: pair data and drop nans
    V = pd.concat([X,Y], axis=1).dropna()
    v1, v2 = (V.iloc[:,0], V.iloc[:,1]) # could add +1 to both to avoid 0 counts.

    pxy, xedges, yedges = np.histogram2d(v1, v2, bins=nbins, normed=True, weights=None)

    # smooth the 2d hist, to be more distribution-y
    ndimage.gaussian_filter(pxy, sigma=sigma_smooth, mode='constant', output=pxy)

    if 0:
        plt.figure()
        plt.imshow(pxy, origin='low', aspect='auto',
                    extent=[xedges[0], xedges[-1], yedges[0], yedges[-1]])

    # compute marginal histograms (achtung zeros when dividing)
    pxy = pxy + 1E-12
    norm = np.sum(pxy)
    pxy = pxy / norm
    py = np.sum(pxy, axis=0).reshape((-1, nbins))
    px = np.sum(pxy, axis=1).reshape((nbins, -1))

    # Normalised Mutual Information of:
    # Studholme,  jhill & jhawkes (1998).
    # "A normalized entropy measure of 3-D medical image alignment".
    # in Proc. Medical Imaging 1998, vol. 3338, San Diego, CA, pp. 132-143.

    return - np.sum(py * np.log(py)) - np.sum(px * np.log(px)) + np.sum(pxy * np.log(pxy))

##############################################################################################################
def compute_normalized_mutual_information():
    return None
    #NMI[i1,i2] = ((np.sum(py * np.log(py)) + np.sum(px * np.log(px))) / np.sum(pxy * np.log(pxy))) - 1

##############################################################################################################
def compute_approximate_HSIC(X,Y, ncom=100, gamma=[None, None], ntrials=100, random_state=1, sigma_prior = 1):
    """
        Using approximations, computes the HSIC score between two different data series. Apprixmations are subsampling for the RBF kernel bandwidth selection and random kitchen sinks to approximate kernels (adn therefore directly using inner products to estimate the cross-covariance operator in the approximate RKHS)

        :param X, Y: (mutlivariate) data series
        :param ncom: number of components to use in the random kernel approximation
        :param gamma: bandwidth for the RBF kernels
        :param ntrials: number of trials, on which HSIC is averaged
        :param random_state: set initial random state for reproducibility
        :param sigma_prior: scaling for the sigmas
    """

    from sklearn.kernel_approximation import RBFSampler
    import random
    if random_state is not None:
        random.seed(random_state)

    def centering(K):
        """
            center kernel matrix
        """
        n = K.shape[0]
        unit = np.ones([n, n])
        I = np.eye(n)
        Q = I - unit/n
        return np.dot(np.dot(Q, K), Q)

    def rbf(X, sigma=None):
        """
            define RBF kernel + its parameter
        """
        GX = np.dot(X, X.T)
        KX = np.diag(GX) - GX + (np.diag(GX) - GX).T
        if sigma is None:
            mdist = np.median(KX[KX != 0])
            sigma = np.sqrt(mdist)
        KX *= - 0.5 / sigma / sigma
        np.exp(KX, KX)
        return KX

    if gamma[0] is None:

        if X.shape[0] > 1000:
            yy = np.random.choice(len(X),1000)
            x_ = X[yy]
            del yy
        else:
            x_ = X

        GX = np.dot(x_, x_.T)
        KX = np.diag(GX) - GX + (np.diag(GX) - GX).T
        mdist = np.median(KX[KX != 0])
        gamma[0] = 1/(np.sqrt(sigma_prior*mdist)**2)
        del GX, KX, mdist

    if gamma[1] is None:
        if Y.shape[0] > 1000:
            yy = np.random.choice(len(Y),1000)
            y_ = Y[yy]
            del yy
        else:
            y_ = Y

        GY = np.dot(y_, y_.T)
        KY = np.diag(GY) - GY + (np.diag(GY) - GY).T
        mdist = np.median(KY[KY != 0])
        gamma[1] = 1/(np.sqrt(sigma_prior*mdist)**2)
        del GY, KY, mdist

    hs_a = 0
    rbf_feature_x = RBFSampler(gamma=gamma[0], random_state=random_state, n_components=ncom)
    rbf_feature_y = RBFSampler(gamma=gamma[1], random_state=random_state, n_components=ncom)

    for trial in range(ntrials):
        if (X.shape[0] < 1)|(Y.shape[0] < 1):
            continue

        X_f = rbf_feature_x.fit_transform(X)
        X_f -= np.mean(X_f,axis=0)
        Y_f = rbf_feature_y.fit_transform(Y)
        Y_f -= np.mean(Y_f,axis=0)

        A = X_f.T.dot(Y_f)
        B = Y_f.T.dot(X_f)
        C = A.dot(B)
        hs_a += 1/X_f.shape[0]**2 * np.trace(C)

    return hs_a / ntrials

##############################################################################################################
def dependency_measures_per_dataset(series_1, series_2):
    from tqdm import tqdm
    file_string = 'part_waves'

    COR = np.zeros((series_1.shape[1],series_2.shape[1]))
    MI = np.zeros((series_1.shape[1],series_2.shape[1]))
    HSIC = np.zeros((series_1.shape[1],series_2.shape[1]))
    NSAMP = np.zeros((series_1.shape[1],series_2.shape[1]))

    for i1, pa1 in enumerate(series_1.columns.tolist()):
        print(i1, end=' ')
        for i2, pa2 in enumerate(series_2.columns.tolist()):
    #         print('.',end='')
            if set(series_1.columns.tolist())==set(series_2.columns.tolist()): # True:
                if i2 >= i1:
                    # print(pa1, pa2, end=' ')
                    # 1: pair data and drop nans
                    V = pd.concat([series_1.iloc[:,i1],series_2.iloc[:,i2]], axis=1).dropna()
                    v1, v2 = (V.iloc[:,0], V.iloc[:,1]) # could add +1 to both to avoid 0 counts.

                    rho = np.corrcoef(V.transpose())#.iloc[:,0], V.iloc[:,1])
                    COR[i1,i2] = rho[0,1]
                    MI[i1,i2] = compute_mutual_information(v1,v2,nbins=128,sigma_smooth=2)
                    HSIC[i1,i2] = compute_approximate_HSIC(v1.values.reshape(-1,1),v2.values.reshape(-1,1), ncom=100, gamma=[None, None], ntrials=100, random_state=1, sigma_prior=1)
            else:
                V = pd.concat([series_1.iloc[:,i1],series_2.iloc[:,i2]], axis=1).dropna()
                v1, v2 = (V.iloc[:,0], V.iloc[:,1]) # could add +1 to both to avoid 0 counts.

                rho = np.corrcoef(V.transpose())#.iloc[:,0], V.iloc[:,1])
                COR[i1,i2] = rho[0,1]
                MI[i1,i2] = compute_mutual_information(v1,v2,nbins=128,sigma_smooth=2)
                HSIC[i1,i2] = compute_approximate_HSIC(v1.values.reshape(-1,1),v2.values.reshape(-1,1), ncom=100, gamma=[None, None], ntrials=5, random_state=1, sigma_prior = 1)
                NSAMP[i1,i2] = V.shape[0]

    if set(series_1.columns.tolist())==set(series_2.columns.tolist()): # True:
        COR = (COR + COR.T) - np.diag(np.diag(COR))
        MI = (MI + MI.T) - np.diag(np.diag(MI))
        HSIC = (HSIC + HSIC.T) - np.diag(np.diag(HSIC))
        NSAMP = (NSAMP + NSAMP.T) - np.diag(np.diag(NSAMP))

    return COR, MI, HSIC, NSAMP

##############################################################################################################
def smooth_weight_ridge_regression(data, labels, opts, ITERS=100, THRESH=1e-6):
    """
        Define a multitask regression problem in which tasks are locally smooth (e.g. bin size prediction), and introduce a penalty in which weights of regressors of related tasks are encouraged to be similar.
    """
    def retrieve_mt_norm(W,ind_w):
        if ind_w == 0:
            W_subs = W[:,ind_w+1]#:ind_w+1]
        #         elif ind_w == T-2:
        #             W_subs = W[:,ind_w-2:T]
        #         elif ind_w == 1:
        #             W_subs = W[:,ind_w-1]
        elif ind_w == T-1:
            W_subs = W[:,ind_w-1]
        else:
            W_subs = 0.5*(W[:,ind_w-1] + W[:,ind_w+1])

        return W_subs

    D = data.shape[1]
    T = labels.shape[1]

    print(opts)

    par1 = opts['par1']
    par2 = opts['par2']
    tr_ts_split = opts['tr_ts_split']

    W_old = np.ones((D,T))
    W = np.random.rand(D,T)

    # init stuff
    k = 0
    epsi = 1000
    loss = []
    data_mean = data.mean(axis=0)
    data_std = data.std(axis=0)
    label_mean = labels.mean(axis=0)
    label_std = labels.std(axis=0)

    fi_loop = True
    inds = np.zeros((data.shape[0], T))

    while (epsi > opts['THRESH'])&(k < opts['ITERS']):
        schedule = np.random.permutation(range(T))
        W_old = W.copy()
        for ind_w in schedule:
            X_Y = data.assign(y=labels.iloc[:,ind_w])

            if fi_loop:
                n_na = np.where(~X_Y.isnull().any(axis=1))[0]
                n_na = np.random.permutation(n_na)
                tr = n_na[:int(np.floor(tr_ts_split*len(n_na)))]
                ts = n_na[int(np.floor(tr_ts_split*len(n_na))):]
                inds[tr,ind_w] = 1
                inds[ts,ind_w] = 2

            train_X = X_Y.iloc[inds[:,ind_w] == 1, :-1]
            train_Y = X_Y.iloc[inds[:,ind_w] == 1, -1]

            N = train_X.shape[0]

            W_mt_n = retrieve_mt_norm(W,ind_w)
            A = 1/N * np.dot(train_X.T,train_X) + par1*np.eye(D) + par2*np.eye(D)
            A = np.linalg.inv(A)

            B = 1/N * np.dot(train_X.T,train_Y) + par2*W_mt_n

            W[:,ind_w] = np.matmul(A,B)

        if fi_loop:
            fi_loop = False

        epsi = np.abs(np.sum(np.sum(W-W_old)))
        loss.append(epsi)
        print(k, end=' ')
        k += 1

    print(k, epsi)
    return W, loss, inds
