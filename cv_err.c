#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <math.h>
#include <lib_rng/lib_rng.h>
#include "lib_gpr.h"

void get_subsample_cv_holdout(double *ytst, double *xtst, unsigned long ntst, double *ytrn,
			      double *xtrn, unsigned long ntrn, const double *y, const double *x,
			      unsigned long n, unsigned int dim, unsigned long k)
{
	unsigned long nsub, i, j, l, m, d;

	assert(n % ntst == 0 && "Subsample does not divide sample!!");
	assert(ntrn == n - ntst);

	nsub = n / ntst;

	for (j = 0; j < ntst; j++) {

		for (d = 0; d < dim; d++) {
			xtst[j * dim + d] = x[(k * ntst + j) * dim + d];
		}

		ytst[j] = y[k * ntst + j];
	}

	m = 0;
	for (l = 0; l < n; l++) {

		for (d = 0; d < dim; d++) {
			xtrn[m * dim + d] = x[l * dim + d];
		}

		ytrn[m] = y[l];

		if (l < k * ntst || (k + 1) * ntst <= l) {
			m++;
		}
	}
}

void get_gpr_cv_holdout_rmse_batch(unsigned long k, double *cv_rmse_rel, unsigned long ntst,
				   const double *x, const double *y, unsigned long n,
				   unsigned int dim, double *hp, unsigned long nhp)
{
	double *ytrn, *xtrn, *ytst, *ytst_gpr, *xtst, diff;
	unsigned long ntrn, i;

	ntrn = n - ntst;

	ytrn = malloc(ntrn * sizeof(double));
	assert(ytrn);
	ytst = malloc(ntst * sizeof(double));
	assert(ytst);
	ytst_gpr = malloc(ntst * sizeof(double));
	assert(ytst_gpr);

	xtrn = malloc(ntrn * dim * sizeof(double));
	assert(xtrn);
	xtst = malloc(ntst * dim * sizeof(double));
	assert(xtst);

	get_subsample_cv_holdout(ytst, xtst, ntst, ytrn, xtrn, ntrn, y, x, n, dim, k);

	gpr_interpolate(xtst, ytst_gpr, ntst, xtrn, ytrn, ntrn, dim, hp, nhp, NULL, 0);

	for (i = 0; i < ntst; i++) {

		diff = ytst[i] - ytst_gpr[i];
		cv_rmse_rel[i] = sqrt(diff * diff) / fabs(ytst[i]);
	}

	free(xtrn);
	free(xtst);
	free(ytrn);
	free(ytst);
}

void get_gpr_cv_holdout_rmse(double *cv_rmse_rel, const double *x, const double *y, unsigned long n,
			     unsigned int dim, double *hp, unsigned long nhp, unsigned long ntst)
{
	unsigned long k, nk;

	assert(n % ntst == 0);
	nk = n / ntst;

	for (k = 0; k < nk; k++) {

		get_gpr_cv_holdout_rmse_batch(k, &cv_rmse_rel[k * ntst], ntst, x, y, n, dim, hp,
					      nhp);
	}
}

void test_get_subsample_cv_holdout(unsigned long n, unsigned long ntst, unsigned long k,
				   unsigned int dim, int seed)
{
	double *ytst, *ytrn, *xtst, *xtrn, *y, *x, tmp;
	unsigned long ntrn, i, d;
	dsfmt_t drng;

	ntrn = n - ntst;

	x = malloc(n * dim * sizeof(double));
	assert(x);
	y = malloc(n * sizeof(double));
	assert(y);

	xtst = malloc(ntst * dim * sizeof(double));
	assert(xtst);
	ytst = malloc(ntst * sizeof(double));
	assert(ytst);

	xtrn = malloc(ntrn * dim * sizeof(double));
	assert(xtrn);
	ytrn = malloc(ntrn * sizeof(double));
	assert(ytrn);

	dsfmt_init_gen_rand(&drng, seed);

	for (i = 0; i < n; i++) {

		tmp = 0;
		for (d = 0; d < dim; d++) {
			x[i * dim + d] = dsfmt_genrand_close_open(&drng);
			tmp += x[i * dim + d];
		}

		y[i] = tmp;
	}

	get_subsample_cv_holdout(ytst, xtst, ntst, ytrn, xtrn, ntrn, y, x, n, dim, k);

	printf("## x \t y \n\n");

	for (i = 0; i < n; i++) {
		printf("%3ld ", i + 1);
		for (d = 0; d < dim; d++) {
			printf("%+.15E ", x[i * dim + d]);
		}
		printf("%+.15E\n", y[i]);
	}

	printf("\n\n## xtst \t ytst \n\n");

	for (i = 0; i < ntst; i++) {
		printf("%3ld ", i + 1);
		for (d = 0; d < dim; d++) {
			printf("%+.15E ", xtst[i * dim + d]);
		}
		printf("%+.15E\n", ytst[i]);
	}

	printf("\n\n## xtrn \t ytrn \n\n");

	for (i = 0; i < ntrn; i++) {
		printf("%3ld ", i + 1);
		for (d = 0; d < dim; d++) {
			printf("%+.15E ", xtrn[i * dim + d]);
		}
		printf("%+.15E\n", ytrn[i]);
	}

	free(x);
	free(y);
	free(xtst);
	free(ytst);
	free(xtrn);
	free(ytrn);
}