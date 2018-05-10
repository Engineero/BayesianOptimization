from __future__ import print_function
from __future__ import division
import unittest
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern
from bayes_opt.helpers import UtilityFunction, acq_max, ensure_rng


def get_globals():
    X = np.array([
        [0.00, 0.00],
        [0.99, 0.99],
        [0.00, 0.99],
        [0.99, 0.00],
        [0.50, 0.50],
        [0.25, 0.50],
        [0.50, 0.25],
        [0.75, 0.50],
        [0.50, 0.75],
    ])

    def get_y(X):
        return -(X[:, 0] - 0.3) ** 2 - 0.5 * (X[:, 1] - 0.6)**2 + 2
    y = get_y(X)

    mesh = np.dstack(
        np.meshgrid(np.arange(0, 1, 0.01), np.arange(0, 1, 0.01))
    ).reshape(-1, 2)

    mesh_lt = np.dstack(
        np.tril(np.meshgrid(np.arange(0, 1, 0.01), np.arange(0, 1, 0.01)))
    ).reshape(-1, 2)
    mesh_lt = mesh_lt[~np.all(mesh == 0, axis=1)]

    mesh_ut = np.dstack(
        np.triu(np.meshgrid(np.arange(0, 1, 0.01), np.arange(0, 1, 0.01)), k=1)
    ).reshape(-1, 2)
    mesh_ut = mesh_ut[~np.all(mesh == 0, axis=1)]

    GP = GaussianProcessRegressor(
        kernel=Matern(),
        n_restarts_optimizer=25,
    )
    GP.fit(X, y)

    return {'x': X, 'y': y, 'gp': GP, 'mesh': mesh, 'mesh_lt': mesh_lt,
            'mesh_ut': mesh_ut}


def brute_force_maximum(MESH, GP, kind='ucb', kappa=1.0, xi=1e-6):
    uf = UtilityFunction(kind=kind, kappa=kappa, xi=xi)

    mesh_vals = uf.utility(MESH, GP, 2)
    max_val = mesh_vals.max()
    max_arg_val = MESH[np.argmax(mesh_vals)]

    return max_val, max_arg_val


GLOB = get_globals()
X, Y, GP, MESH = GLOB['x'], GLOB['y'], GLOB['gp'], GLOB['mesh']
MESH_LT, MESH_UT = GLOB['mesh_lt'], GLOB['mesh_ut']


class TestMaximizationOfAcquisitionFunction(unittest.TestCase):

    def setUp(self, kind='ucb', kappa=1.0, xi=1e-6):
        self.util = UtilityFunction(kind=kind, kappa=kappa, xi=xi)
        self.epsilon = 1e-2
        self.y_max = 2.0
        self.random_state = ensure_rng(0)
        self.constraints = [{'type': 'ineq',
                             'fun': lambda x: x[0] - x[1]}]

    def test_acq_max_function_with_ucb_algo(self):
        self.setUp(kind='ucb', kappa=1.0, xi=1.0)
        max_arg = acq_max(
            self.util.utility, GP, self.y_max, bounds=np.array([[0, 1], [0, 1]]),
            random_state=self.random_state, n_iter=20
        )
        _, brute_max_arg = brute_force_maximum(MESH, GP)

        self.assertTrue( all(abs(brute_max_arg - max_arg) < self.epsilon))

        # Define an inequality constraint such that x[0] > x[1]. Inequality
        # constraints must evaluate to >0.
        max_arg = acq_max(
            self.util.utility, GP, self.y_max, bounds=np.array([[0, 1], [0, 1]]),
            random_state=self.random_state, n_iter=20,
            constraints=self.constraints
        )
        _, brute_max_arg = brute_force_maximum(MESH_LT, GP)
        self.assertTrue(all(abs(brute_max_arg - max_arg) < self.epsilon),
                        msg='Constrained maximization failed with ucb!')
        _, brute_max_arg = brute_force_maximum(MESH_UT, GP)
        self.assertTrue(all(abs(brute_max_arg - max_arg) > self.epsilon),
                        msg='Unexpectedly similar values with constraints!')

    def test_ei_max_function_with_ucb_algo(self):
        self.setUp(kind='ei', kappa=1.0, xi=1e-6)
        max_arg = acq_max(
            self.util.utility, GP, self.y_max, bounds=np.array([[0, 1], [0, 1]]),
            random_state=self.random_state, n_iter=20
        )
        _, brute_max_arg = brute_force_maximum(MESH, GP, kind='ei')

        self.assertTrue( all(abs(brute_max_arg - max_arg) < self.epsilon))
        # Define an inequality constraint such that x[0] > x[1]. Inequality
        # constraints must evaluate to >0.
        constraints = [{'type': 'ineq',
                        'fun': lambda x: x[0] - x[1]}]
        max_arg = acq_max(
            self.util.utility, GP, self.y_max, bounds=np.array([[0, 1], [0, 1]]),
            random_state=self.random_state, n_iter=20,
            constraints=self.constraints
        )
        _, brute_max_arg = brute_force_maximum(MESH_LT, GP)
        self.assertTrue(all(abs(brute_max_arg - max_arg) < self.epsilon),
                        msg='Constrained maximization failed with ei!')
        _, brute_max_arg = brute_force_maximum(MESH_UT, GP)
        self.assertTrue(all(abs(brute_max_arg - max_arg) > self.epsilon),
                        msg='Unexpectedly similar values with constraints!')


if __name__ == '__main__':
    r"""
    CommandLine:
        python tests/test_target_space.py
    """
    # unittest.main()
    import pytest
    pytest.main([__file__])
