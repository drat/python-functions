'''
Created on Nov 21, 2014

@author: zwicker
'''

from __future__ import division

import numpy as np
from scipy import integrate, misc, optimize, special, stats


    
class StatisticsAccumulator(object):
    """ class that can be used to calculate statistics of sets of arbitrarily
    shaped data sets. This uses an online algorithm, allowing the data to be
    added one after another """
    
    def __init__(self, ddof=0, shape=None, dtype=np.double, ret_cov=False):
        """ initialize the accumulator
        `ddof` is the  delta degrees of freedom, which is used in the formula 
            for the standard deviation.
        `shape` is the shape of the data. If omitted it will be read from the
            first value
        `dtype` is the numpy dtype of the interal accumulator
        `ret_cov` determines whether the covariances are also calculated
        """ 
        self.count = 0
        self.ddof = ddof
        self.dtype = dtype
        self.ret_cov = ret_cov
        
        if shape is None:
            self.shape = None
            self._mean = None
            self._M2 = None
        else:
            self.shape = shape
            size = np.prod(shape)
            self._mean = np.zeros(size, dtype=dtype)
            if ret_cov:
                self._M2 = np.zeros((size, size), dtype=dtype)
            else:
                self._M2 = np.zeros(size, dtype=dtype)
            
            
    @property
    def mean(self):
        """ return the mean """
        if self.shape is None:
            return self._mean
        else:
            return self._mean.reshape(self.shape)
        
        
    @property
    def cov(self):
        """ return the variance """
        if self.count <= self.ddof:
            raise RuntimeError('Too few items to calculate variance')
        elif not self.ret_cov:
            raise ValueError('The covariance matrix was not calculated')
        else:
            return self._M2 / (self.count - self.ddof)
        
        
    @property
    def var(self):
        """ return the variance """
        if self.count <= self.ddof:
            raise RuntimeError('Too few items to calculate variance')
        elif self.ret_cov:
            var = np.diag(self._M2) / (self.count - self.ddof)
        else:
            var = self._M2 / (self.count - self.ddof)

        if self.shape is None:
            return var
        else:
            return var.reshape(self.shape)
        
        
    @property
    def std(self):
        """ return the standard deviation """
        return np.sqrt(self.var)
            
            
    def _initialize(self, value):
        """ initialize the internal state with a given value """
        # state needs to be initialized
        self.count = 1
        if hasattr(value, '__iter__'):
            # make sure the value is a numpy array
            value_arr = np.asarray(value, self.dtype)
            self.shape = value_arr.shape
            size = value_arr.size

            # store 1d version of it
            self._mean = np.ravel(value)
            if self.ret_cov:
                self._M2 = np.zeros((size, size), self.dtype)
            else:
                self._M2 = np.zeros(size, self.dtype)
        else:
            self.shape = None
            self._mean = value
            self._M2 = 0
        
            
    def add(self, value):
        """ add a value to the accumulator """
        if self._mean is None:
            self._initialize(value)
            
        else:
            # update internal state
            if self.shape is not None:
                value = np.ravel(value)
            
            self.count += 1
            delta = value - self._mean
            self._mean += delta / self.count
            if self.ret_cov:
                self._M2 += ((self.count - 1) * np.outer(delta, delta)
                            - self._M2 / self.count)
            else:
                self._M2 += delta * (value - self._mean)
            
    
    def add_many(self, arr_or_iter):
        """ adds many values from an array or an iterator """
        for value in arr_or_iter:
            self.add(value)
    
    

def mean_std_online(arr_or_iter, ddof=0, shape=None):
    """ calculates the mean and the standard deviation of the given data.
    If the data is an iterator, the values are calculated memory efficiently
    with an online algorithm, which does not store all the intermediate data.
    
    `ddof` is the  delta degrees of freedom, which is used in the formula for
        the standard deviation. 
    """
    acc = StatisticsAccumulator(ddof=ddof, shape=shape)
    acc.add_many(arr_or_iter)
    
    if acc.mean is None:
        mean = np.nan
    else:
        mean = acc.mean
    
    try:
        std = acc.std
    except ValueError:
        std = np.nan
        
    return mean, std
    
    
    
def mean_std_frequency_table(frequencies, values=None, ddof=0):
    """ calculates the mean and the standard deviation of the given data.
    `frequencies` is an array with which `values` were observed. If `values` is
    None, it is set to `values = np.arange(len(frequencies))`.
    `ddof` is the  delta degrees of freedom, which is used in the formula for
        the standard deviation. 
    """
    if values is None:
        values = np.arange(len(frequencies))
    
    count = frequencies.sum()
    sum1 = (values * frequencies).sum()
    sum2 = (values**2 * frequencies).sum()
    mean = sum1 / count
    var = (sum2 - sum1**2 / count)/(count - ddof)
    std = np.sqrt(var)
        
    return mean, std
        
        

def lognorm_mean_var_to_mu_sigma(mean, variance, definition='scipy'):
    """ determines the parameters of the log-normal distribution such that the
    distribution yields a given mean and variance. The optional parameter
    `definition` can be used to choose a definition of the resulting parameters
    that is suitable for the given software package. """
    mean2 = mean**2
    mu = mean2/np.sqrt(mean2 + variance)
    sigma = np.sqrt(np.log(1 + variance/mean2))
    if definition == 'scipy':
        return mu, sigma
    elif definition == 'numpy':
        return np.log(mu), sigma
    else:
        raise ValueError('Unknown definition `%s`' % definition)



def lognorm_mean_var(mean, variance):
    """ returns a lognormal distribution parameterized by its mean and its
    variance. """
    scale, sigma = lognorm_mean_var_to_mu_sigma(mean, variance, 'scipy')
    return stats.lognorm(scale=scale, s=sigma)



def sampling_distribution_std(x, std, num):
    """
    Sampling distribution of the standard deviation, see
    http://en.wikipedia.org/wiki/Chi_distribution
    """

    if x < 0:
        return 0

    scale = np.sqrt(num)/std
    x *= scale

    res = 2**(1 - 0.5*num)*x**(num - 1)*np.exp(-0.5*x*x)/special.gamma(0.5*num)

    return res*scale



def sampling_distribution_cv(x, cv, num):
    """
    Sampling distribution of the coefficient of variation, see
    W. A. Hendricks and K. W. Robey. The Sampling Distribution of the
    Coefficient of Variation. Ann. Math. Statist. 7, 129-132 (1936).
    """
    if x < 0:
        return 0
    x2 = x*x

    # calculate the sum
    factorial = misc.factorial
    res = sum(
        factorial(num - 1) * special.gamma(0.5*(num - i)) * num**(0.5*i) / (
            factorial(num - 1 - i) * factorial(i) * 2**(0.5*i) * cv**i
            * (1 + x2)**(0.5*i)
        )
        for i in range(1 - num%2, num, 2)
    )

    # multiply by the other terms
    res *= 2./(np.sqrt(np.pi)*special.gamma(0.5*(num-1)))
    res *= x**(num-2)/((1 + x2)**(0.5*num))
    res *= np.exp(-0.5*num/(cv**2)*x2/(1 + x2))

    return res



def confidence_interval(value, distribution=None, args=None, guess=None,
                        confidence=0.95):
    """ returns the confidence interval of `value`, if its value was estimated
    `num` times from the `distribution` """

    if guess is None:
        guess = 0.1*value
    if distribution is None:
        distribution = sampling_distribution_std

    # create partial function
    distr = lambda y: distribution(y, value, *args)

    def rhs(x):
        """ integrand """
        return confidence - integrate.quad(distr, value-x, value+x)[0]

    res = optimize.newton(rhs, guess, tol=1e-4)
    return res



def confidence_interval_mean(std, num, confidence=0.95):
    """ calculates the confidence interval of the mean given a standard
    deviation and a number of observations, assuming a normal distribution """
    sem = std/np.sqrt(num) # estimate of the standard error of the mean

    # get confidence interval from student-t distribution
    factor = stats.t(num - 1).ppf(0.5 + 0.5*confidence)

    return factor*sem



def confidence_interval_std(std, num, confidence=0.95):
    """ calculates the confidence interval of the standard deviation given a 
    standard deviation and a number of observations, assuming a normal
    distribution """
    c = stats.chi(num - 1).ppf(0.5 + 0.5*confidence)
    lower_bound = np.sqrt(num - 1)*std/c

    c = stats.chi(num - 1).ppf(0.5 - 0.5*confidence)
    upper_bound = np.sqrt(num - 1)*std/c

    return 0.5*(upper_bound - lower_bound)



def estimate_mean(data, confidence=0.95):
    """ estimate mean and the associated standard error of the mean of a
    data set """
    mean = data.mean()
    std = data.std(ddof=1)

    err = confidence_interval_mean(std, len(data), confidence)

    return mean, err



def estimate_std(data, confidence=0.95):
    """ estimate the standard deviation and the associated error of a
    data set """
    std = data.std()
    err = confidence_interval_std(std, len(data), confidence)

    return std, err



def estimate_cv(data, confidence=0.95):
    """ estimate the coefficient of variation and the associated error """
    mean = data.mean()
    std = data.std()
    cv = std/mean

    err = confidence_interval(cv, sampling_distribution_cv, (len(data),))

    return cv, err



if __name__ == '__main__':
    print("This file is intended to be used as a module only.")
