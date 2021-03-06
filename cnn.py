#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# cnn classifier
import lasagne
import theano
import theano.tensor as T
import numpy as np
import time

from src.ui import *
from src.general import *
from src.files import *

from src.features import *
from src.dataset import *
from src.evaluation import *
import batch
import pdb
from utils import *

def reshape(x):
    x =np.expand_dims(x, axis=1)
    return x
def calc_error(data_test, predict):
    ''' return error, cost on that set'''

    b = batch.Batch(data_test, max_batchsize=500, seg_window=100, seg_hop=100)
    err = 0
    cost_val=0
    eps = 1e-10
    for (x,y_lab,_) in b:
        x = reshape(x)
        decision=predict(x) + eps
        pred_label= np.argmax(decision,axis=-1)
        y = onehot(y_lab)

        cost_val += -np.sum(y*np.log(decision))
        err += np.sum( np.expand_dims(pred_label, axis = 1)!= y_lab )
        assert(not np.isnan(cost_val))
    err = err/float(len(b.index_bkup))
    cost_val = cost_val /len(b.index_bkup)
    return err , cost_val

# create neural network
def build(input_var, type='residual', n=1, num_filters=8,num_class=10, feat_dim=60, max_length=100):
    # feature_data: numpy.ndarray [shape=(t, feature vector length)]
    # depth: number of hidden layers
    # width: number of units in each hidden layer
    #feature_length = feature_data.shape[1]    # feature_data shape???
    if type == 'vgg16':
        import vgg16
        layers = vgg16.build()
    if type == 'residual':
        import residual_network
        network = residual_network.build_cnn(input_var, n=n, num_filters= num_filters, cudnn='no',num_class=num_class, feat_dim=feat_dim, max_length=max_length)
    return network

# train dnn
def do_train(data, data_val, data_test,  **classifier_parameters):
    '''
    return ??
    '''

    batch_maker = batch.Batch(data, isShuffle = True, seg_window=100, seg_hop=20 ,max_batchsize=50)
    num_epochs = 10000
    #num_epochs = 3
    # prepare theano variables for inputs and targets
    input_var = T.tensor4('inputs')
    target_var = T.imatrix('targets')  # ??

    network = build(input_var,**classifier_parameters)

    # create a loss expression for training
    prediction = lasagne.layers.get_output(network)
    loss = lasagne.objectives.categorical_crossentropy(prediction,target_var)
    loss = loss.mean()

    # create update expressions for training: SGD with momentum
    params = lasagne.layers.get_all_params(network, trainable=True)
    updates = lasagne.updates.adadelta(
        loss, params, learning_rate=1)

    train = theano.function([input_var, target_var],loss , updates=updates)
    # create a loss expression for validation/testing
    # 'deterministic' disable dropout layers
    test_prediction = lasagne.layers.get_output(network, deterministic=True)
    test_loss = lasagne.objectives.categorical_crossentropy(test_prediction, target_var)
    test_loss = test_loss.mean()
    predict = theano.function( [input_var], lasagne.layers.get_output(network, deterministic=True))

    # training loop
    print("Starting training...")
    epoch = 0
    #no_best = 1
    no_best = 10
    best_cost = np.inf
    best_epoch = epoch
    model_params = []
    # TO REMOVE
    #model_params.append(lasagne.layers.get_all_param_values(nnet))
    while epoch < num_epochs:

        try:
            start_time = time.time()
            cost_train = 0
            for _, (x ,y ,_) in enumerate(batch_maker):
                x = reshape(x)
                y=onehot(y)

                assert(not np.any(np.isnan(x)))
                cost_train+= train(x, y) *x .shape[0]#*x .shape[1]
                assert(not np.isnan(cost_train))
            cost_train = cost_train/ len(batch_maker.index_bkup)
            err_val, cost_val = calc_error(data_val,predict)
            err_test, cost_test = calc_error(data_test,predict)
            #import pdb; pdb.set_trace()
                #cost_val, err_val = 0, 0
            #pdb.set_trace()
            end_time = time.time()

            is_better = False
            if cost_val < best_cost:
                best_cost =cost_val
                best_epoch = epoch
                is_better = True

            if is_better:
                print "epoch: {} ({}s), training cost: {}, val cost: {}, val err: {}, test cost {}, test err: {}, New best.".format(epoch, end_time-start_time, cost_train, cost_val, err_val, cost_test, err_test)
            else:
                print "epoch: {} ({}s), training cost: {}, val cost: {}, val err: {}, test cost {}, test err: {}".format(epoch, end_time-start_time, cost_train, cost_val, err_val, cost_test, err_test)

            sys.stdout.flush()
            model_params.append(lasagne.layers.get_all_param_values(network))
        #check_path('dnn')
        #save_data('dnn/epoch_{}.autosave'.format(epoch), (classifier_parameters, model_params[best_epoch]))
        #savename = os.path.join(modelDir,'epoch_{}.npz'.format(epoch))
        #files.save_model(savename,structureDic,lasagne.layers.get_all_param_values(nnet))
            if epoch - best_epoch >= no_best:
                ## Early stoping
                break
            epoch += 1
        except:
            if best_epoch == 0:
                return (classifier_parameters, model_params[-1])
            else:
                return (classifier_parameters, model_params[best_epoch])

    return (classifier_parameters, model_params[best_epoch])



def build_model(model_params, return_model=False):
    input_var = T.tensor4('inputs')

    network = build(input_var, **model_params[0])
    lasagne.layers.set_all_param_values(network,model_params[1])

    prediction = lasagne.layers.get_output(network, deterministic=True)

    predict = theano.function([input_var], prediction)
    if return_model:
        return predict, network

    return predict

# do_classification_dnn: classification for given feature data
def do_classification(feature_data, predict, params):
    '''
    input feature_data
    return classification results
    '''
    # ???
    #import pdb; pdb.set_trace()
    x, _ = batch.make_batch(feature_data,params[0]['max_length'],params[0]['max_length'])
    x = reshape(x)
    decision = predict(x)
    return decision

def postprocess(decision):
    pred_label = np.argmax(np.sum(decision,axis=0), axis = -1)
    return batch.labels[pred_label]
