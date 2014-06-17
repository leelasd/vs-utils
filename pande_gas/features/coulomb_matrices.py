"""
Generate coulomb matrices for molecules.

See _Montavon et al., New Journal of Physics_ __15__ (2013) 095003.
"""

__author__ = "Steven Kearnes"
__copyright__ = "Copyright 2014, Stanford University"
__license__ = "BSD 3-clause"

import numpy as np

from pande_gas.features import Featurizer
from pande_gas.utils import pad_array
from pande_gas.utils.rdkit_utils import interatomic_distances


class CoulombMatrix(Featurizer):
    """
    Calculate Coulomb matrices for molecules.

    Parameters
    ----------
    max_atoms : int, optional
        Maximum number of atoms for any molecule in the dataset. Used to
        pad the Coulomb matrix.
    randomize : bool, optional (default True)
        Whether to randomize Coulomb matrices to remove dependence on atom
        index order.
    n_samples : int, optional (default 1)
        Number of random Coulomb matrices to generate if randomize is True.
    seed : int, optional
        Random seed.
    """
    conformers = True
    name = 'coulomb_matrix'

    def __init__(self, max_atoms=None, randomize=True, n_samples=1, seed=None):
        self.max_atoms = max_atoms
        self.randomize = randomize
        self.n_samples = n_samples
        self.seed = seed

    def featurize(self, mols):
        """
        Calculate Coulomb matrices for molecules. Also calculate max_atoms
        for this batch, if not already set.

        Parameters
        ----------
        mols : iterable
            RDKit Mol objects.
        """
        reset = False
        if self.max_atoms is None:
            reset = True
            self.max_atoms = max([mol.GetNumAtoms() for mol in mols])
        features = super(CoulombMatrix, self).featurize(mols)
        if reset:
            self.max_atoms = None
        return features

    def _featurize(self, mol):
        """
        Calculate Coulomb matrices for molecules.

        Parameters
        ----------
        mol : RDKit Mol
            Molecule.
        """
        features = self.coulomb_matrix(mol)
        features = [f[np.triu_indices_from(f)] for f in features]
        return features

    def coulomb_matrix(self, mol):
        """
        Generate Coulomb matrices for each conformer of the given molecule.

        Parameters
        ----------
        mol : RDKit Mol
            Molecule.
        """
        n_atoms = mol.GetNumAtoms()
        z = [atom.GetAtomicNum() for atom in mol.GetAtoms()]
        rval = []
        for conf in mol.GetConformers():
            d = interatomic_distances(conf)
            m = np.zeros((n_atoms, n_atoms))
            for i in xrange(mol.GetNumAtoms()):
                for j in xrange(mol.GetNumAtoms()):
                    if i == j:
                        m[i, j] = 0.5 * z[i] ** 2.4
                    elif i < j:
                        m[i, j] = (z[i] * z[j]) / d[i, j]
                        m[j, i] = m[i, j]
                    else:
                        continue
            if self.randomize:
                for random_m in self.randomize_coulomb_matrix(m):
                    random_m = pad_array(random_m, self.max_atoms)
                    rval.append(random_m)
            else:
                m = pad_array(m, self.max_atoms)
                rval.append(m)
        return rval

    def randomize_coulomb_matrix(self, m):
        """
        Randomize a Coulomb matrix as decribed in Montavon et al., _New Journal
        of Physics_ __15__ (2013) 095003:

            1. Compute row norms for M in a vector row_norms.
            2. Sample a zero-mean unit-variance noise vector e with dimension
               equal to row_norms.
            3. Permute the rows and columns of M with the permutation that
               sorts row_norms + e.

        Parameters
        ----------
        m : ndarray
            Coulomb matrix.
        n_samples : int, optional (default 1)
            Number of random matrices to generate.
        seed : int, optional
            Random seed.
        """
        rval = []
        row_norms = np.asarray([np.linalg.norm(row) for row in m], dtype=float)
        rng = np.random.RandomState(self.seed)
        for i in xrange(self.n_samples):
            e = rng.normal(size=row_norms.size)
            p = np.argsort(row_norms + e)
            new = m[p][:, p]  # permute rows first, then columns
            rval.append(new)
        return rval
