#  This file is part of Pynguin.
#
#  SPDX-FileCopyrightText: 2019–2020 Pynguin Contributors
#
#  SPDX-License-Identifier: LGPL-3.0-or-later
#
from unittest.mock import MagicMock

import pytest

import pynguin.ga.chromosome as chrom
import pynguin.ga.fitnessfunction as ff
from pynguin.ga.chromosome import Chromosome


@pytest.fixture
def fitness_function():
    fitness = MagicMock(ff.FitnessFunction)
    fitness.is_maximisation_function.return_value = False
    return fitness


@pytest.fixture
def chromosome():
    class DummyChromosome(chrom.Chromosome):
        def mutate(self):
            pass

        def size(self) -> int:
            return 0

        def clone(self) -> Chromosome:
            pass

        def cross_over(
            self, other: chrom.Chromosome, position1: int, position2: int
        ) -> None:
            pass

        def __hash__(self):
            return 0

        def __eq__(self, other):
            return True

        def length(self) -> int:
            return 0

    return DummyChromosome()


def test_fitness_no_fitness_values(chromosome):
    with pytest.raises(AssertionError):
        assert chromosome.get_fitness()


def test_fitness_one_fitness_function(chromosome, fitness_function):
    chromosome.add_fitness_function(fitness_function)
    chromosome._update_fitness_values(fitness_function, ff.FitnessValues(5, 0.9))
    chromosome.set_changed(False)
    assert chromosome.get_fitness() == 5
    assert chromosome.get_coverage() == 0.9


def test_fitness_two_fitness_functions(chromosome, fitness_function):
    chromosome.add_fitness_function(fitness_function)
    chromosome._update_fitness_values(fitness_function, ff.FitnessValues(0.42, 0.1))
    fitness_func2 = MagicMock(ff.FitnessFunction)
    fitness_func2.is_maximisation_function.return_value = False
    chromosome.add_fitness_function(fitness_func2)
    chromosome._update_fitness_values(fitness_func2, ff.FitnessValues(0.23, 0.5))
    chromosome.set_changed(False)
    assert chromosome.get_fitness() == 0.65
    assert chromosome.get_coverage() == 0.3


def test_values_for_fitness_function(chromosome, fitness_function):
    chromosome.add_fitness_function(fitness_function)
    chromosome._update_fitness_values(fitness_function, ff.FitnessValues(5, 0.5))
    chromosome.set_changed(False)
    assert chromosome.get_fitness_for(fitness_function) == 5
    assert chromosome.get_coverage_for(fitness_function) == 0.5


def test_has_changed_default(chromosome):
    assert chromosome.has_changed()


def test_has_changed(chromosome):
    chromosome.set_changed(False)
    assert not chromosome.has_changed()


def test_caching(chromosome, fitness_function):
    fitness_function.compute_fitness_values.side_effect = [
        ff.FitnessValues(5, 0.5),
        ff.FitnessValues(6, 0.6),
    ]
    chromosome.add_fitness_function(fitness_function)
    assert chromosome.get_fitness() == 5
    assert chromosome.get_coverage() == 0.5
    assert not chromosome.has_changed()
    assert chromosome.get_number_of_evaluations() == 1

    chromosome.set_changed(True)
    assert chromosome.get_fitness() == 6
    assert chromosome.get_coverage() == 0.6
    assert not chromosome.has_changed()
    assert chromosome.get_number_of_evaluations() == 2


def test_illegal_values(chromosome, fitness_function):
    fitness_function.compute_fitness_values.return_value = ff.FitnessValues(-1, 1.5)
    chromosome.add_fitness_function(fitness_function)
    with pytest.raises(RuntimeError):
        chromosome.get_fitness()


def test_get_fitness_functions(chromosome):
    func1 = MagicMock(ff.FitnessFunction)
    func1.is_maximisation_function.return_value = False
    func2 = MagicMock(ff.FitnessFunction)
    func2.is_maximisation_function.return_value = False
    chromosome.add_fitness_function(func1)
    chromosome.add_fitness_function(func2)
    assert chromosome.get_fitness_functions() == [func1, func2]
