import torch as tc
import numpy as np
import scipy.optimize as opt
import matplotlib.pyplot as plt

tc.set_default_tensor_type(tc.DoubleTensor)


class GPR(object):
    def __init__(self, x, y, cov, hp=None, **kargs):

        self.x = tc.clone(x)
        self.y = tc.clone(y)
        self.cov = cov
        if hp is None:
            self.hp = self.cov(x)
        else:
            self.hp = hp
        self.args = kargs

        self.krn = NotImplemented
        self.wt = NotImplemented
        self.krnchd = NotImplemented

        self.dgn = {}

    def cost_fun(self, hp):
        f = log_likelihood(self.x, self.y, hp, self.cov, **self.args)
        return f

    def jac_cost_fun(self, hp):
        jac_f = jac_log_likelihood(self.x, self.y, hp, self.cov, **self.args)
        return jac_f

    def train(self, method='Nelder-Mead', jac=False):

        if jac:
            res = opt.minimize(self.cost_fun,
                               self.hp,
                               jac=self.jac_cost_fun,
                               method=method)
        else:
            res = opt.minimize(self.cost_fun,
                               self.hp,
                               jac=False,
                               method=method)
        self.hp = res.x

        self.llhd = res.fun
        self.jac_llhd = res.jac

        return res

    def interpolant(self):

        self.krn = self.cov(self.x, hp=self.hp, **self.args)
        self.krnchd = tc.cholesky(self.krn)
        self.wt = tc.squeeze(
            tc.cholesky_solve(self.y.reshape(-1, 1), self.krnchd))

        def interp_fun(xs):
            krns = self.cov(self.x, xs=xs, hp=self.hp, **self.args)

            ys = tc.mv(krns, self.wt)

            krnss = self.cov(xs, hp=self.hp, **self.args)

            lks = tc.cholesky_solve(krns.transpose(0, 1), self.krnchd)

            covars = krnss - tc.mm(krns, lks)

            return ys, covars

        return interp_fun

    def diagnostics(self, xs, ys, covar, ya, diag=False):
        var = tc.diag(covar)
        n = ys.shape[0]
        err = ys - ya

        self.dgn['RMSE'] = tc.sqrt(tc.mean(tc.sum(err**2)))
        self.dgn['SDSUM'] = tc.sqrt(tc.mean(tc.sum(var)))
        self.dgn['RCHI-SQ'] = (1.0 / n) * tc.sum((err**2) / var)

        if diag == True:
            self.dgn['LLHD'] = -0.5 * tc.sum(np.log(var)) \
                    - 0.5 * tc.log( 2 * np.pi) - n * self.dgn['RCHI-SQ']
        else:
            eig, evec = tc.symeig(covar)
            sol, lu = tc.solve(err[:, np.newaxis], covar)
            md = tc.dot(err, sol.squeeze_())
            self.dgn['LLHD'] = -0.5 * tc.sum(tc.log(eig)) \
                    - 0.5 * tc.log(tc.tensor(2 * np.pi)) - md
            self.dgn['MD'] = (1.0 / n) * md

    def plot(self, xs, ys, covars, ya, diag=False):
        if diag:
            sig = tc.sqrt(covars)
        else:
            sig = tc.sqrt(tc.diag(covars))

        min_ys = tc.min(ys)
        max_ys = tc.max(ys)

        fig = plt.figure(constrained_layout=True)
        gs = fig.add_gridspec(2, 2, wspace=0.2, hspace=0.2)

        pred = fig.add_subplot(gs[0, 0])
        sigma = fig.add_subplot(gs[0, 1])
        hpar = fig.add_subplot(gs[1, 0].subgridspec(1, 2)[0])
        jac = fig.add_subplot(gs[1, 0].subgridspec(1, 2)[1])
        mse = fig.add_subplot(gs[1, 1])

        pred.scatter(ys, ya, color='red')
        pred.plot([min_ys, max_ys], [min_ys, max_ys])
        pred.axis('equal')
        pred.set(title='Prediction Vs Exact',
                 xlabel='Y Predicted',
                 ylabel='Y actual')

        sigma.hist(tc.log(sig))
        sigma.set(title='$\sigma$-Predicted',
                  xlabel='$log(\sigma)$',
                  ylabel='Frequency')

        hpar.scatter(range(0, len(self.hp)), self.hp, label='$\\theta$')
        hpar.set(xlabel='S.No')
        hpar.legend()

        jac.scatter(range(0, len(self.hp)),
                    np.log(self.jac_llhd),
                    label='$dL/d\\theta$')
        jac.set(xlabel='S.No')
        jac.legend()

        mse.hist(tc.log(ys - ya))
        mse.set(title='Mean Squared Error', xlabel='MSE', ylabel='Frequency')


def log_likelihood(x, y, hp, cov, **kwargs):

    krn = cov(x, hp=hp, **kwargs)
    krnchd = tc.cholesky(krn)

    wt = tc.squeeze(tc.cholesky_solve(y.reshape(-1, 1), krnchd))

    llhd = 0.5 * tc.dot(wt, y) \
            + tc.sum(tc.log(tc.diag(krnchd))) \
            + 0.5 * len(y) * tc.log(tc.tensor(2 * np.pi))

    return llhd.numpy()


def jac_log_likelihood(x, y, hp, cov, **kwargs):

    krn, dkrn = cov(x, hp=hp, deriv=True, **kwargs)
    krnchd = tc.cholesky(krn)

    wt = tc.cholesky_solve(y.reshape(-1, 1), krnchd).squeeze_()

    jac_llhd = dkrn.matmul(wt).matmul(wt)
    jac_llhd.sub_(tc.sum(tc.diagonal(dkrn, dim1=-1, dim2=-2), 1))
    jac_llhd.mul_(-0.5)

    return jac_llhd.numpy()