
'''
femmodel

This module provide many fem model 

'''

from .BilinearForm import BilinearForm

from .TrussStructureIntegrator import TrussStructureIntegrator
from .MassIntegrator import MassIntegrator
from .DiffusionIntegrator import DiffusionIntegrator
from .ConvectionIntegrator import ConvectionIntegrator

from .ProvidesSymmetricTangentOperatorIntegrator import ProvidesSymmetricTangentOperatorIntegrator


from .LinearForm import LinearForm
from .SourceIntegrator import SourceIntegrator


from .DirichletBC import DirichletBC

