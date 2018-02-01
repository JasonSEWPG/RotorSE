#!/usr/bin/env python
# encoding: utf-8
"""
rotor.py

Created by Andrew Ning on 2012-02-28.
Copyright (c)  NREL. All rights reserved.
"""

# from __future__ import print_function
import numpy as np
import os
from openmdao.api import IndepVarComp, Component, Group, Problem, Brent, ScipyGMRES

from ccblade.ccblade_component import CCBladeGeometry, CCBladePower

from commonse.distribution import RayleighCDF, WeibullWithMeanCDF
from commonse.utilities import vstack, trapz_deriv, linspace_with_deriv, smooth_min, smooth_abs
from commonse.environment import PowerWind
#from precomp import Profile, Orthotropic2DMaterial, CompositeSection, _precomp
from akima import Akima
from rotor_geometry import GridSetup, RGrid, GeometrySpline, TurbineClass
#import _pBEAM
#import _curvefem

from rotorse import RPM2RS, RS2RPM, TURBINE_CLASS, DRIVETRAIN_TYPE


class VarSpeedMachine(Component):
    """variable speed machines"""
    def __init__(self):
        super(VarSpeedMachine, self).__init__()

        self.add_param('Vin', shape=1, units='m/s', desc='cut-in wind speed')
        self.add_param('Vout', shape=1, units='m/s', desc='cut-out wind speed')
        self.add_param('ratedPower', shape=1, units='W', desc='rated power')
        self.add_param('minOmega', shape=1, units='rpm', desc='minimum allowed rotor rotation speed')
        self.add_param('maxOmega', shape=1, units='rpm', desc='maximum allowed rotor rotation speed')
        self.add_param('tsr', shape=1, desc='tip-speed ratio in Region 2 (should be optimized externally)')
        self.add_param('pitch', shape=1, units='deg', desc='pitch angle in region 2 (and region 3 for fixed pitch machines)')

class FixedSpeedMachine(Component):
    """fixed speed machines"""
    def __init__(self):
        super(FixedSpeedMachine, self).__init__()
        self.add_param('Vin', shape=1, units='m/s', desc='cut-in wind speed')
        self.add_param('Vout', shape=1, units='m/s', desc='cut-out wind speed')
        self.add_param('ratedPower', shape=1, units='W', desc='rated power')
        self.add_param('Omega', shape=1, units='rpm', desc='fixed rotor rotation speed')
        self.add_param('maxOmega', shape=1, units='rpm', desc='maximum allowed rotor rotation speed')
        self.add_param('pitch', shape=1, units='deg', desc='pitch angle in region 2 (and region 3 for fixed pitch machines)')

class RatedConditions(Component):
    """aerodynamic conditions at the rated wind speed"""
    def __init__(self):
        super(RatedConditions, self).__init__()
        self.add_param('V', shape=1, units='m/s', desc='rated wind speed')
        self.add_param('Omega', shape=1, units='rpm', desc='rotor rotation speed at rated')
        self.add_param('pitch', shape=1, units='deg', desc='pitch setting at rated')
        self.add_param('T', shape=1, units='N', desc='rotor aerodynamic thrust at rated')
        self.add_param('T', shape=1, units='N*m', desc='rotor aerodynamic torque at rated')


# ---------------------
# Base Components
# ---------------------


class DrivetrainLossesBase(Component):
    """base component for drivetrain efficiency losses"""
    def __init__(self, npower):
        super(DrivetrainLossesBase, self).__init__()
        self.add_param('aeroPower', shape=npower, units='W', desc='aerodynamic power')
        self.add_param('aeroTorque', shape=npower, units='N*m', desc='aerodynamic torque')
        self.add_param('aeroThrust', shape=npower, units='N', desc='aerodynamic thrust')
        self.add_param('ratedPower', shape=1, units='W', desc='rated power')

        self.add_output('power', shape=npower, units='W', desc='total power after drivetrain losses')
        self.add_output('rpm', shape=npower, units='rpm', desc='rpm curve after drivetrain losses')

# ---------------------
# Components
# ---------------------

# class MaxTipSpeed(Component):

#     R = Float(iotype='in', units='m', desc='rotor radius')
#     Vtip_max = Float(iotype='in', units='m/s', desc='maximum tip speed')

#     Omega_max = Float(iotype='out', units='rpm', desc='maximum rotation speed')

#     def execute(self):

#         self.Omega_max = self.Vtip_max/self.R * RS2RPM


#     def list_deriv_vars(self):

#         inputs = ('R', 'Vtip_max')
#         outputs = ('Omega_max',)

#         return inputs, outputs


#     def provideJ(self):

#         J = np.array([[-self.Vtip_max/self.R**2*RS2RPM, RS2RPM/self.R]])

#         return J

'''
# This Component is now no longer used, but I'll keep it around for now in case that changes.
class Coefficients(Component):
    def __init__(self, npts_coarse_power_curve):
        super(Coefficients, self).__init__()
        """convert power, thrust, torque into nondimensional coefficient form"""

        # inputs
        self.add_param('V', shape=npts_coarse_power_curve, units='m/s', desc='wind speed')
        self.add_param('T', shape=npts_coarse_power_curve, units='N', desc='rotor aerodynamic thrust')
        self.add_param('Q', shape=npts_coarse_power_curve, units='N*m', desc='rotor aerodynamic torque')
        self.add_param('P', shape=npts_coarse_power_curve, units='W', desc='rotor aerodynamic power')

        # inputs used in normalization
        self.add_param('R', shape=1, units='m', desc='rotor radius')
        self.add_param('rho', shape=1, units='kg/m**3', desc='density of fluid')


        # outputs
        self.add_output('CT', shape=npts_coarse_power_curve, desc='rotor aerodynamic thrust')
        self.add_output('CQ', shape=npts_coarse_power_curve, desc='rotor aerodynamic torque')
        self.add_output('CP', shape=npts_coarse_power_curve, desc='rotor aerodynamic power')

	self.deriv_options['form'] = 'central'
	self.deriv_options['step_calc'] = 'relative'


    def solve_nonlinear(self, params, unknowns, resids):

        rho = params['rho']
        V = params['V']
        R = params['R']
        T = params['T']
        Q = params['Q']
        P = params['P']

        q = 0.5 * rho * V**2
        A = pi * R**2
        unknowns['CP'] = P / (q * A * V)
        unknowns['CT'] = T / (q * A)
        unknowns['CQ'] = Q / (q * R * A)


    def list_deriv_vars(self):

        inputs = ('V', 'T', 'Q', 'P', 'R')
        outputs = ('CT', 'CQ', 'CP')

        return inputs, outputs


    def linearize(self, params, unknowns, resids):
        J = {}

        rho = params['rho']
        V = params['V']
        R = params['R']

        n = len(V)
        CP = unknowns['CP']
        CT = unknowns['CT']
        CQ = unknowns['CQ']

        q = 0.5 * rho * V**2
        A = pi * R**2


        J['CT', 'V'] = np.diag(-2.0*CT/V)
        J['CT', 'T'] = np.diag(1.0/(q*A))
        J['CT', 'Q'] = np.zeros((n, n))
        J['CT', 'P'] = np.zeros((n, n))
        J['CT', 'R'] = -2.0*CT/R

        J['CQ', 'V'] = np.diag(-2.0*CQ/V)
        J['CQ', 'T'] = np.zeros((n, n))
        J['CQ', 'Q'] = np.diag(1.0/(q*R*A))
        J['CQ', 'P'] = np.zeros((n, n))
        J['CQ', 'R'] = -3.0*CQ/R

        J['CP', 'V'] = np.diag(-3.0*CP/V)
        J['CP', 'T'] = np.zeros((n, n))
        J['CP', 'Q'] = np.zeros((n, n))
        J['CP', 'P'] = np.diag(1.0/(q*A*V))
        J['CP', 'R'] = -2.0*CP/R

        return J
'''


class SetupRunFixedSpeed(Component):
    def __init__(self):
        super(SetupRunFixedSpeed, self).__init__()
        """determines approriate conditions to run AeroBase code across the power curve"""

        self.add_param('control:Vin', units='m/s', desc='cut-in wind speed')
        self.add_param('control:Vout', units='m/s', desc='cut-out wind speed')
        self.add_param('control:ratedPower', units='W', desc='rated power')
        self.add_param('control:Omega', units='rpm', desc='fixed rotor rotation speed')
        self.add_param('control:pitch', units='deg', desc='pitch angle in region 2 (and region 3 for fixed pitch machines)')
        self.add_param('control:npts', val=20, desc='number of points to evalute aero code to generate power curve', pass_by_obj=True)

        # outputs
        self.add_output('Uhub', units='m/s', desc='freestream velocities to run')
        self.add_output('Omega', units='rpm', desc='rotation speeds to run')
        self.add_output('pitch', units='deg', desc='pitch angles to run')

        self.deriv_options['step_calc'] = 'absolute'
        self.deriv_options['type'] = 'fd'
        self.deriv_options['step_calc'] = 'relative'

    def solve_nonlinear(self, params, unknowns, resids):
        ctrl = params['control']
        n = ctrl.n

        # velocity sweep
        V = np.linspace(ctrl.Vin, ctrl.Vout, n)

        # store values
        unknowns['Uhub'] = V
        unknowns['Omega'] = ctrl.Omega*np.ones_like(V)
        unknowns['pitch'] = ctrl.pitch*np.ones_like(V)

class SetupRunVarSpeed(Component):
    def __init__(self, npts_coarse_power_curve):
        super(SetupRunVarSpeed, self).__init__()
        """determines approriate conditions to run AeroBase code across the power curve"""

        self.add_param('control:Vin', shape=1, units='m/s', desc='cut-in wind speed')
        self.add_param('control:Vout', shape=1, units='m/s', desc='cut-out wind speed')
        self.add_param('control:ratedPower', shape=1, units='W', desc='rated power')
        self.add_param('control:minOmega', shape=1, units='rpm', desc='minimum allowed rotor rotation speed')
        self.add_param('control:maxOmega', shape=1, units='rpm', desc='maximum allowed rotor rotation speed')
        self.add_param('control:tsr', shape=1, desc='tip-speed ratio in Region 2 (should be optimized externally)')
        self.add_param('control:pitch', shape=1, units='deg', desc='pitch angle in region 2 (and region 3 for fixed pitch machines)')

        self.add_param('R', shape=1, units='m', desc='rotor radius')
        self.add_param('npts', shape=1, val=20, desc='number of points to evalute aero code to generate power curve', pass_by_obj=True)

        # outputs
        self.add_output('Uhub', shape=npts_coarse_power_curve, units='m/s', desc='freestream velocities to run')
        self.add_output('Omega', shape=npts_coarse_power_curve, units='rpm', desc='rotation speeds to run')
        self.add_output('pitch', shape=npts_coarse_power_curve, units='deg', desc='pitch angles to run')


    def solve_nonlinear(self, params, unknowns, resids):

        n = params['npts']
        R = params['R']

        # # attempt to distribute points mostly before rated
        # cpguess = 0.5
        # Vr0 = (ctrl.ratedPower/(cpguess*0.5*rho*pi*R**2))**(1.0/3)
        # Vr0 *= 1.20

        # V1 = np.linspace(Vin, Vr0, 15)
        # V2 = np.linspace(Vr0, Vout, 6)
        # V = np.concatenate([V1, V2[1:]])

        # velocity sweep
        V = np.linspace(params['control:Vin'], params['control:Vout'], n)

        # corresponding rotation speed
        Omega_d = params['control:tsr']*V/R*RS2RPM
        Omega, dOmega_dOmegad, dOmega_dmaxOmega = smooth_min(Omega_d, params['control:maxOmega'], pct_offset=0.01)

        # store values
        unknowns['Uhub'] = V
        unknowns['Omega'] = Omega
        unknowns['pitch'] = params['control:pitch']*np.ones_like(V)

        # gradients
        J = {}
        J['Omega', 'control:tsr'] = dOmega_dOmegad * V/R*RS2RPM
        J['Omega', 'R'] = dOmega_dOmegad * -params['control:tsr']*V/R**2*RS2RPM
        J['Omega', 'control:maxOmega'] = dOmega_dmaxOmega
	J['Uhub', 'control:tsr'] = np.zeros(len(V))
	J['Uhub', 'R'] = np.zeros(len(V))
	J['Uhub', 'control:pitch'] = np.zeros(len(V))
	J['pitch', 'control:tsr'] = np.zeros(len(V))
	J['pitch', 'R'] = np.zeros(len(V))
	J['pitch', 'control:pitch'] = np.zeros(len(V))

        self.J = J

    def list_deriv_vars(self):

        inputs = ('control:tsr', 'R', 'control:maxOmega')
        outputs = ('Uhub', 'Omega', 'pitch', )

        return inputs, outputs

    def linearize(self, params, unknowns, resids):

        return self.J





class UnregulatedPowerCurve(Component):
    def __init__(self, npts_coarse_power_curve, npts_spline_power_curve):
        super(UnregulatedPowerCurve, self).__init__()

        # inputs
        self.add_param('control:Vin', units='m/s', desc='cut-in wind speed')
        self.add_param('control:Vout', units='m/s', desc='cut-out wind speed')
        self.add_param('control:ratedPower', units='W', desc='rated power')
        self.add_param('control:Omega', units='rpm', desc='fixed rotor rotation speed')
        self.add_param('control:pitch', units='deg', desc='pitch angle in region 2 (and region 3 for fixed pitch machines)')
        self.add_param('control:npts', val=20, desc='number of points to evalute aero code to generate power curve', pass_by_obj=True)

        self.add_param('Vcoarse', shape=npts_coarse_power_curve, units='m/s', desc='wind speeds')
        self.add_param('Pcoarse', shape=npts_coarse_power_curve, units='W', desc='unregulated power curve (but after drivetrain losses)')
        self.add_param('Tcoarse', shape=npts_coarse_power_curve, units='N', desc='unregulated thrust curve')
        self.add_param('npts', val=npts_spline_power_curve, desc='number of points for splined power curve', pass_by_obj=True)

        # outputs
        self.add_output('V', units='m/s', desc='wind speeds')
        self.add_output('P', units='W', desc='power')


    def solve_nonlinear(self, params, unknowns, resids):

        ctrl = params['control']
        n = ctrl.n

        # finer power curve
        V, _, _ = linspace_with_deriv(ctrl.Vin, ctrl.Vout, n)
        unknowns['V'] = V
        spline = Akima(params['Vcoarse'], params['Pcoarse'])
        P, dP_dV, dP_dVcoarse, dP_dPcoarse = spline.interp(self.V)
        unknowns['P'] = P

        J = {}
        J['P', 'Vcoarse'] = dP_dVcoarse
        J['P', 'Pcoarse'] = dP_dPcoarse
        self.J = J

    def linearize(self, params, unknowns, resids):

        return self.J


class RegulatedPowerCurve(Component): # Implicit COMPONENT


    def __init__(self, npts_coarse_power_curve, npts_spline_power_curve):
        super(RegulatedPowerCurve, self).__init__()

        self.eval_only = True  # allows an external solver to converge this, otherwise it will converge itself to mimic an explicit comp
        """Fit a spline to the coarse sampled power curve (and thrust curve),
        find rated speed through a residual convergence strategy,
        then compute the regulated power curve and rated conditions"""

        # inputs
        self.add_param('control:Vin', val=0.0, units='m/s', desc='cut-in wind speed')
        self.add_param('control:Vout', shape=1, units='m/s', desc='cut-out wind speed')
        self.add_param('control:ratedPower', shape=1, units='W', desc='rated power')
        self.add_param('control:minOmega', shape=1, units='rpm', desc='minimum allowed rotor rotation speed')
        self.add_param('control:maxOmega', shape=1, units='rpm', desc='maximum allowed rotor rotation speed')
        self.add_param('control:tsr', shape=1, desc='tip-speed ratio in Region 2 (should be optimized externally)')
        self.add_param('control:pitch', shape=1, units='deg', desc='pitch angle in region 2 (and region 3 for fixed pitch machines)')

        self.add_param('Vcoarse', shape=npts_coarse_power_curve, units='m/s', desc='wind speeds')
        self.add_param('Pcoarse', shape=npts_coarse_power_curve, units='W', desc='unregulated power curve (but after drivetrain losses)')
        self.add_param('Tcoarse', shape=npts_coarse_power_curve, units='N', desc='unregulated thrust curve')
        self.add_param('R', shape=1, units='m', desc='rotor radius')
        self.add_param('npts', val=npts_spline_power_curve, desc='number of points for splined power curve', pass_by_obj=True)

        # state
        self.add_state('Vrated', val=11.0, units='m/s', desc='rated wind speed', lower=-1e-15, upper=1e15)

        # residual
        # self.add_state('residual', shape=1)

        # outputs
        self.add_output('V', shape=npts_spline_power_curve, units='m/s', desc='wind speeds')
        self.add_output('P', shape=npts_spline_power_curve, units='W', desc='power')

        self.add_output('ratedConditions:V', shape=1, units='m/s', desc='rated wind speed')
        self.add_output('ratedConditions:Omega', shape=1, units='rpm', desc='rotor rotation speed at rated')
        self.add_output('ratedConditions:pitch', shape=1, units='deg', desc='pitch setting at rated')
        self.add_output('ratedConditions:T', shape=1, units='N', desc='rotor aerodynamic thrust at rated')
        self.add_output('ratedConditions:Q', shape=1, units='N*m', desc='rotor aerodynamic torque at rated')

        self.add_output('azimuth', shape=1, units='deg', desc='azimuth load')


	self.deriv_options['step_calc'] = 'relative'
	self.deriv_options['form'] = 'central'
	self.deriv_options['type'] = 'fd'
	self.deriv_options['check_step_calc'] = 'relative'
	self.deriv_options['check_form'] = 'central'

    def solve_nonlinear(self, params, unknowns, resids):
        n = params['npts']
        Vrated = unknowns['Vrated']

        # residual
        spline = Akima(params['Vcoarse'], params['Pcoarse'])
        P, dres_dVrated, dres_dVcoarse, dres_dPcoarse = spline.interp(Vrated)
        # resids['residual'] = P - ctrl.ratedPower
        #resids['Vrated'] = P - params['control:ratedPower']
        # functional

        # place half of points in region 2, half in region 3
        # even though region 3 is constant we still need lots of points there
        # because we will be integrating against a discretized wind
        # speed distribution

        # region 2
        V2, _, dV2_dVrated = linspace_with_deriv(params['control:Vin'], Vrated, n/2)
        P2, dP2_dV2, dP2_dVcoarse, dP2_dPcoarse = spline.interp(V2)

        # region 3
        V3, dV3_dVrated, _ = linspace_with_deriv(Vrated, params['control:Vout'], n/2+1)
        V3 = V3[1:]  # remove duplicate point
        dV3_dVrated = dV3_dVrated[1:]
        P3 = params['control:ratedPower']*np.ones_like(V3)

        # concatenate
        unknowns['V'] = np.concatenate([V2, V3])
        unknowns['P'] = np.concatenate([P2, P3])

        R = params['R']
        # rated speed conditions
        Omega_d = params['control:tsr']*Vrated/R*RS2RPM
        OmegaRated, dOmegaRated_dOmegad, dOmegaRated_dmaxOmega \
            = smooth_min(Omega_d, params['control:maxOmega'], pct_offset=0.01)

        splineT = Akima(params['Vcoarse'], params['Tcoarse'])
        Trated, dT_dVrated, dT_dVcoarse, dT_dTcoarse = splineT.interp(Vrated)

        unknowns['ratedConditions:V'] = Vrated
        unknowns['ratedConditions:Omega'] = OmegaRated
        unknowns['ratedConditions:pitch'] = params['control:pitch']
        unknowns['ratedConditions:T'] = Trated
        unknowns['ratedConditions:Q'] = params['control:ratedPower'] / (OmegaRated * RPM2RS)
        unknowns['azimuth'] = 180.0


    def apply_nonlinear(self, params, unknowns, resids):

        n = params['npts']
        Vrated = unknowns['Vrated']

        # residual
        spline = Akima(params['Vcoarse'], params['Pcoarse'])
        P, dres_dVrated, dres_dVcoarse, dres_dPcoarse = spline.interp(Vrated)
        # resids['residual'] = P - ctrl.ratedPower
        resids['Vrated'] = P - params['control:ratedPower']
        # functional

        # place half of points in region 2, half in region 3
        # even though region 3 is constant we still need lots of points there
        # because we will be integrating against a discretized wind
        # speed distribution

        # region 2
        V2, _, dV2_dVrated = linspace_with_deriv(params['control:Vin'], Vrated, n/2)
        P2, dP2_dV2, dP2_dVcoarse, dP2_dPcoarse = spline.interp(V2)

        # region 3
        V3, dV3_dVrated, _ = linspace_with_deriv(Vrated, params['control:Vout'], n/2+1)
        V3 = V3[1:]  # remove duplicate point
        dV3_dVrated = dV3_dVrated[1:]
        P3 = params['control:ratedPower']*np.ones_like(V3)

        # concatenate
        unknowns['V'] = np.concatenate([V2, V3])
        unknowns['P'] = np.concatenate([P2, P3])

        R = params['R']
        # rated speed conditions
        Omega_d = params['control:tsr']*Vrated/R*RS2RPM
        OmegaRated, dOmegaRated_dOmegad, dOmegaRated_dmaxOmega \
            = smooth_min(Omega_d, params['control:maxOmega'], pct_offset=0.01)

        splineT = Akima(params['Vcoarse'], params['Tcoarse'])
        Trated, dT_dVrated, dT_dVcoarse, dT_dTcoarse = splineT.interp(Vrated)

        unknowns['ratedConditions:V'] = Vrated
        unknowns['ratedConditions:Omega'] = OmegaRated
        unknowns['ratedConditions:pitch'] = params['control:pitch']
        unknowns['ratedConditions:T'] = Trated
        unknowns['ratedConditions:Q'] = params['control:ratedPower'] / (OmegaRated * RPM2RS)
        unknowns['azimuth'] = 180.0

        # gradients
        ncoarse = len(params['Vcoarse'])

        dV_dVrated = np.concatenate([dV2_dVrated, dV3_dVrated])

        dP_dVcoarse = vstack([dP2_dVcoarse, np.zeros((n/2, ncoarse))])
        dP_dPcoarse = vstack([dP2_dPcoarse, np.zeros((n/2, ncoarse))])
        dP_dVrated = np.concatenate([dP2_dV2*dV2_dVrated, np.zeros(n/2)])

        drOmega = np.concatenate([[dOmegaRated_dOmegad*Vrated/R*RS2RPM], np.zeros(3*ncoarse),
            [dOmegaRated_dOmegad*params['control:tsr']/R*RS2RPM, -dOmegaRated_dOmegad*params['control:tsr']*Vrated/R**2*RS2RPM,
            dOmegaRated_dmaxOmega]])
        drQ = -params['control:ratedPower'] / (OmegaRated**2 * RPM2RS) * drOmega

        J = {}

	J['Vrated', 'Vcoarse'] = np.reshape(dres_dVcoarse, (1, len(dres_dVcoarse)))
        J['Vrated', 'Pcoarse'] = np.reshape(dres_dPcoarse, (1, len(dres_dPcoarse)))
        J['Vrated', 'Vrated'] = dres_dVrated
	J['Vrated', 'control:ratedPower'] = -1
	J['Vrated', 'control:tsr'] = 0
	


        J['V', 'Vrated'] = dV_dVrated
        J['P', 'Vrated'] = dP_dVrated
        J['P', 'Vcoarse'] = dP_dVcoarse
        J['P', 'Pcoarse'] = dP_dPcoarse
        J['ratedConditions:V', 'Vrated'] = 1.0
        J['ratedConditions:Omega', 'control:tsr'] = dOmegaRated_dOmegad*Vrated/R*RS2RPM
        J['ratedConditions:Omega', 'Vrated'] = dOmegaRated_dOmegad*params['control:tsr']/R*RS2RPM
        J['ratedConditions:Omega', 'R'] = -dOmegaRated_dOmegad*params['control:tsr']*Vrated/R**2*RS2RPM
        J['ratedConditions:Omega', 'control:maxOmega'] = dOmegaRated_dmaxOmega
        J['ratedConditions:T', 'Vcoarse'] = np.reshape(dT_dVcoarse, (1, len(dT_dVcoarse)))
        J['ratedConditions:T', 'Tcoarse'] = np.reshape(dT_dTcoarse, (1, len(dT_dTcoarse)))
        J['ratedConditions:T', 'Vrated'] = dT_dVrated
        J['ratedConditions:Q', 'control:tsr'] = drQ[0]
        J['ratedConditions:Q', 'Vrated'] = drQ[-3]
        J['ratedConditions:Q', 'R'] = drQ[-2]
        J['ratedConditions:Q', 'control:maxOmega'] = drQ[-1]

        self.J = J


    def linearize(self, params, unknowns, resids):

        return self.J

    
class RegulatedPowerCurveGroup(Group):
    def __init__(self, npts_coarse_power_curve, npts_spline_power_curve):
        super(RegulatedPowerCurveGroup, self).__init__()
        self.add('powercurve_comp', RegulatedPowerCurve(npts_coarse_power_curve, npts_spline_power_curve), promotes=['*'])
        self.nl_solver = Brent()
        self.ln_solver = ScipyGMRES()
        self.nl_solver.options['var_lower_bound'] = 'powercurve.control:Vin'
        self.nl_solver.options['var_upper_bound'] = 'powercurve.control:Vout'
        self.nl_solver.options['state_var'] = 'Vrated'

        self.deriv_options['form'] = 'central'
        self.deriv_options['type'] = 'fd'
        self.deriv_options['step_calc'] = 'relative'

    def list_deriv_vars(self):

        inputs = ('control:tsr', 'Vcoarse', 'Pcoarse', 'Tcoarse', 'Vrated', 'R', 'control:maxOmega')
        outputs = ('Vrated', 'V', 'P', 'ratedConditions:V', 'ratedConditions:Omega',
            'ratedConditions:pitch', 'ratedConditions:T', 'ratedConditions:Q')

        return inputs, outputs

    
class AEP(Component):
    def __init__(self, npts_spline_power_curve):
        super(AEP, self).__init__()
        """integrate to find annual energy production"""

        # inputs
        self.add_param('CDF_V', shape=npts_spline_power_curve, units='m/s', desc='cumulative distribution function evaluated at each wind speed')
        self.add_param('P', shape=npts_spline_power_curve, units='W', desc='power curve (power)')
        self.add_param('lossFactor', shape=1, desc='multiplicative factor for availability and other losses (soiling, array, etc.)')

        # outputs
        self.add_output('AEP', shape=1, units='kW*h', desc='annual energy production')

	self.deriv_options['step_size'] = 1.0
	self.deriv_options['form'] = 'central'
	self.deriv_options['step_calc'] = 'relative'	

    def solve_nonlinear(self, params, unknowns, resids):

        unknowns['AEP'] = params['lossFactor']*np.trapz(params['P'], params['CDF_V'])/1e3*365.0*24.0  # in kWh

    def list_deriv_vars(self):

        inputs = ('CDF_V', 'P', 'lossFactor')
        outputs = ('AEP',)

        return inputs, outputs


    def linearize(self, params, unknowns, resids):

        lossFactor = params['lossFactor']
        P = params['P']
        factor = lossFactor/1e3*365.0*24.0

        dAEP_dP, dAEP_dCDF = trapz_deriv(P, params['CDF_V'])
        dAEP_dP *= factor
        dAEP_dCDF *= factor

        dAEP_dlossFactor = np.array([unknowns['AEP']/lossFactor])

        J = {}
        J['AEP', 'CDF_V'] = np.reshape(dAEP_dCDF, (1, len(dAEP_dCDF)))
        J['AEP', 'P'] = np.reshape(dAEP_dP, (1, len(dAEP_dP)))
        J['AEP', 'lossFactor'] = dAEP_dlossFactor

        return J


class CSMDrivetrain(DrivetrainLossesBase):
    def __init__(self, n):
        super(CSMDrivetrain, self).__init__(n)
        """drivetrain losses from NREL cost and scaling model"""

        self.add_param('drivetrainType', val=DRIVETRAIN_TYPE['GEARED'], pass_by_obj=True)
	self.deriv_options['form'] = 'central'
	self.deriv_options['step_calc'] = 'relative'

    def solve_nonlinear(self, params, unknowns, resids):

        drivetrainType = params['drivetrainType']
        aeroPower = params['aeroPower']
        aeroTorque = params['aeroTorque']
        ratedPower = params['ratedPower']

        if drivetrainType == DRIVETRAIN_TYPE['GEARED']:
            constant = 0.01289
            linear = 0.08510
            quadratic = 0.0

        elif drivetrainType == DRIVETRAIN_TYPE['SINGLE_STAGE']:
            constant = 0.01331
            linear = 0.03655
            quadratic = 0.06107

        elif drivetrainType == DRIVETRAIN_TYPE['MULTI_DRIVE']:
            constant = 0.01547
            linear = 0.04463
            quadratic = 0.05790

        elif drivetrainType == DRIVETRAIN_TYPE['PM_DIRECT_DRIVE']:
            constant = 0.01007
            linear = 0.02000
            quadratic = 0.06899


        Pbar0 = aeroPower / ratedPower

        # handle negative power case (with absolute value)
        Pbar1, dPbar1_dPbar0 = smooth_abs(Pbar0, dx=0.01)

        # truncate idealized power curve for purposes of efficiency calculation
        Pbar, dPbar_dPbar1, _ = smooth_min(Pbar1, 1.0, pct_offset=0.01)

        # compute efficiency
        eff = 1.0 - (constant/Pbar + linear + quadratic*Pbar)

        unknowns['power'] = aeroPower * eff

        # gradients
        dPbar_dPa = dPbar_dPbar1*dPbar1_dPbar0/ratedPower
        dPbar_dPr = -dPbar_dPbar1*dPbar1_dPbar0*aeroPower/ratedPower**2

        deff_dPa = dPbar_dPa*(constant/Pbar**2 - quadratic)
        deff_dPr = dPbar_dPr*(constant/Pbar**2 - quadratic)

        dP_dPa = eff + aeroPower*deff_dPa
        dP_dPr = aeroPower*deff_dPr
        
        J = {}
        J['power', 'aeroPower'] = np.diag(dP_dPa)
        J['power', 'ratedPower'] = dP_dPr
        self.J = J


    def list_deriv_vars(self):

        inputs = ('aeroPower', 'ratedPower')
        outputs = ('power',)

        return inputs, outputs

    def linearize(self, params, unknowns, resids):

        return self.J
    

class OutputsAero(Component):
    def __init__(self, npts_spline_power_curve):
        super(OutputsAero, self).__init__()

        # --- outputs ---
        self.add_param('AEP_in', shape=1, units='kW*h', desc='annual energy production')
        self.add_param('V_in', shape=npts_spline_power_curve, units='m/s', desc='wind speeds (power curve)')
        self.add_param('P_in', shape=npts_spline_power_curve, units='W', desc='power (power curve)')

        self.add_param('ratedConditions:V_in', shape=1, units='m/s', desc='rated wind speed')
        self.add_param('ratedConditions:Omega_in', shape=1, units='rpm', desc='rotor rotation speed at rated')
        self.add_param('ratedConditions:pitch_in', shape=1, units='deg', desc='pitch setting at rated')
        self.add_param('ratedConditions:T_in', shape=1, units='N', desc='rotor aerodynamic thrust at rated')
        self.add_param('ratedConditions:Q_in', shape=1, units='N*m', desc='rotor aerodynamic torque at rated')

        self.add_param('hub_diameter_in', shape=1, units='m', desc='hub diameter')
        self.add_param('diameter_in', shape=1, units='m', desc='rotor diameter')
        self.add_param('V_extreme_in', shape=1, units='m/s', desc='survival wind speed')
        self.add_param('T_extreme_in', shape=1, units='N', desc='thrust at survival wind condition')
        self.add_param('Q_extreme_in', shape=1, units='N*m', desc='thrust at survival wind condition')

        # internal use outputs
        self.add_param('Rtip_in', shape=1, units='m', desc='tip location in z_b')
        self.add_param('precurveTip_in', shape=1, units='m', desc='tip location in x_b')
        self.add_param('presweepTip_in', val=0.0, units='m', desc='tip location in y_b')  # TODO: connect later

        # --- outputs ---
        self.add_output('AEP', shape=1, units='kW*h', desc='annual energy production')
        self.add_output('V', shape=npts_spline_power_curve, units='m/s', desc='wind speeds (power curve)')
        self.add_output('P', shape=npts_spline_power_curve, units='W', desc='power (power curve)')

        self.add_output('ratedConditions:V', shape=1, units='m/s', desc='rated wind speed')
        self.add_output('ratedConditions:Omega', shape=1, units='rpm', desc='rotor rotation speed at rated')
        self.add_output('ratedConditions:pitch', shape=1, units='deg', desc='pitch setting at rated')
        self.add_output('ratedConditions:T', shape=1, units='N', desc='rotor aerodynamic thrust at rated')
        self.add_output('ratedConditions:Q', shape=1, units='N*m', desc='rotor aerodynamic torque at rated')

        self.add_output('hub_diameter', shape=1, units='m', desc='hub diameter')
        self.add_output('diameter', shape=1, units='m', desc='rotor diameter')
        self.add_output('V_extreme', shape=1, units='m/s', desc='survival wind speed')
        self.add_output('T_extreme', shape=1, units='N', desc='thrust at survival wind condition')
        self.add_output('Q_extreme', shape=1, units='N*m', desc='thrust at survival wind condition')

        # internal use outputs
        self.add_output('Rtip', shape=1, units='m', desc='tip location in z_b')
        self.add_output('precurveTip', shape=1, units='m', desc='tip location in x_b')
        self.add_output('presweepTip', val=0.0, units='m', desc='tip location in y_b')  # TODO: connect later

    def solve_nonlinear(self, params, unknowns, resids):
        unknowns['AEP'] = params['AEP_in']
        unknowns['V'] = params['V_in']
        unknowns['P'] = params['P_in']
        unknowns['ratedConditions:V'] = params['ratedConditions:V_in']
        unknowns['ratedConditions:Omega'] = params['ratedConditions:Omega_in']
        unknowns['ratedConditions:pitch'] = params['ratedConditions:pitch_in']
        unknowns['ratedConditions:T'] = params['ratedConditions:T_in']
        unknowns['ratedConditions:Q'] = params['ratedConditions:Q_in']
        unknowns['hub_diameter'] = params['hub_diameter_in']
        unknowns['diameter'] = params['diameter_in']
        unknowns['V_extreme'] = params['V_extreme_in']
        unknowns['T_extreme'] = params['T_extreme_in']
        unknowns['Q_extreme'] = params['Q_extreme_in']
        unknowns['Rtip'] = params['Rtip_in']
        unknowns['precurveTip'] = params['precurveTip_in']
        unknowns['presweepTip'] = params['presweepTip_in']

    def linearize(self, params, unknowns,resids):
        J = {}
        J['AEP', 'AEP_in'] = 1
        J['V', 'V_in'] = np.diag(np.ones(len(params['V_in'])))
        J['P', 'P_in'] = np.diag(np.ones(len(params['P_in'])))
        J['ratedConditions:V', 'ratedConditions:V_in'] = 1
        J['ratedConditions:Omega', 'ratedConditions:Omega_in'] = 1
        J['ratedConditions:pitch', 'ratedConditions:pitch_in'] = 1
        J['ratedConditions:T', 'ratedConditions:T_in'] = 1
        J['ratedConditions:Q', 'ratedConditions:Q_in'] = 1
        J['hub_diameter', 'hub_diameter_in'] = 1
        J['diameter', 'diameter_in'] = 1
        J['V_extreme', 'V_extreme_in'] = 1
        J['T_extreme', 'T_extreme_in'] = 1
        J['Q_extreme', 'Q_extreme_in'] = 1
        J['Rtip', 'Rtip_in'] = 1
        J['precurveTip', 'precurveTip_in'] = 1
        J['presweepTip', 'T_presweepTip_in'] = 1

        return J

class RotorAeroPower(Group):
    def __init__(self, naero=17, nstr=38, npts_coarse_power_curve=20, npts_spline_power_curve=200):
        super(RotorAeroPower, self).__init__()
        """rotor model"""

        self.add('initial_aero_grid', IndepVarComp('initial_aero_grid', np.zeros(naero)), promotes=['*'])
        self.add('initial_str_grid', IndepVarComp('initial_str_grid', np.zeros(nstr)), promotes=['*'])
        self.add('idx_cylinder_aero', IndepVarComp('idx_cylinder_aero', 0, pass_by_obj=True), promotes=['*'])
        self.add('idx_cylinder_str', IndepVarComp('idx_cylinder_str', 0, pass_by_obj=True), promotes=['*'])
        self.add('hubFraction', IndepVarComp('hubFraction', 0.0), promotes=['*'])
        self.add('r_aero', IndepVarComp('r_aero', np.zeros(naero)), promotes=['*'])
        self.add('r_max_chord', IndepVarComp('r_max_chord', 0.0), promotes=['*'])
        self.add('chord_sub', IndepVarComp('chord_sub', np.zeros(4),units='m'), promotes=['*'])
        self.add('theta_sub', IndepVarComp('theta_sub', np.zeros(4), units='deg'), promotes=['*'])
        self.add('precurve_sub', IndepVarComp('precurve_sub', np.zeros(3), units='m'), promotes=['*'])
        self.add('bladeLength', IndepVarComp('bladeLength', 0.0, units='m'), promotes=['*'])
        self.add('precone', IndepVarComp('precone', 0.0, units='deg'), promotes=['*'])
        self.add('tilt', IndepVarComp('tilt', 0.0, units='deg'), promotes=['*'])
        self.add('yaw', IndepVarComp('yaw', 0.0, units='deg'), promotes=['*'])
        self.add('nBlades', IndepVarComp('nBlades', 3, pass_by_obj=True), promotes=['*'])
        self.add('airfoil_files', IndepVarComp('airfoil_files', val=np.zeros(naero), pass_by_obj=True), promotes=['*'])
        #self.add('rho', IndepVarComp('rho', val=1.225, units='kg/m**3', desc='density of air', pass_by_obj=True), promotes=['*'])
        #self.add('mu', IndepVarComp('mu', val=1.81206e-5, units='kg/m/s', desc='dynamic viscosity of air', pass_by_obj=True), promotes=['*'])
        #self.add('shearExp', IndepVarComp('shearExp', val=0.2, desc='shear exponent', pass_by_obj=True), promotes=['*'])
        #self.add('hubHt', IndepVarComp('hubHt', val=np.zeros(1), units='m', desc='hub height'), promotes=['*'])
        self.add('turbine_class', IndepVarComp('turbine_class', val=TURBINE_CLASS['I'], desc='IEC turbine class', pass_by_obj=True), promotes=['*'])
        self.add('cdf_reference_height_wind_speed', IndepVarComp('cdf_reference_height_wind_speed', val=0.0, units='m', desc='reference hub height for IEC wind speed (used in CDF calculation)'), promotes=['*'])

        self.add('tiploss', IndepVarComp('tiploss', True, pass_by_obj=True), promotes=['*'])
        self.add('hubloss', IndepVarComp('hubloss', True, pass_by_obj=True), promotes=['*'])
        self.add('wakerotation', IndepVarComp('wakerotation', True, pass_by_obj=True), promotes=['*'])
        self.add('usecd', IndepVarComp('usecd', True, pass_by_obj=True), promotes=['*'])
        
        # --- composite sections ---
        self.add('sparT', IndepVarComp('sparT', val=np.zeros(5), units='m', desc='spar cap thickness parameters'), promotes=['*'])
        self.add('teT', IndepVarComp('teT', val=np.zeros(5), units='m', desc='trailing-edge thickness parameters'), promotes=['*'])

        # --- control ---
        self.add('c_Vin', IndepVarComp('control:Vin', val=0.0, units='m/s', desc='cut-in wind speed'), promotes=['*'])
        self.add('c_Vout', IndepVarComp('control:Vout', val=0.0, units='m/s', desc='cut-out wind speed'), promotes=['*'])
        self.add('c_ratedPower', IndepVarComp('control:ratedPower', val=0.0,  units='W', desc='rated power'), promotes=['*'])
        self.add('c_minOmega', IndepVarComp('control:minOmega', val=0.0, units='rpm', desc='minimum allowed rotor rotation speed'), promotes=['*'])
        self.add('c_maxOmega', IndepVarComp('control:maxOmega', val=0.0, units='rpm', desc='maximum allowed rotor rotation speed'), promotes=['*'])
        self.add('c_tsr', IndepVarComp('control:tsr', val=0.0, desc='tip-speed ratio in Region 2 (should be optimized externally)'), promotes=['*'])
        self.add('c_pitch', IndepVarComp('control:pitch', val=0.0, units='deg', desc='pitch angle in region 2 (and region 3 for fixed pitch machines)'), promotes=['*'])

        # --- drivetrain efficiency ---
        self.add('drivetrainType', IndepVarComp('drivetrainType', val=DRIVETRAIN_TYPE['GEARED'], pass_by_obj=True), promotes=['*'])


        # --- options ---
        self.add('nSector', IndepVarComp('nSector', val=4, iotype='in', desc='number of sectors to divide rotor face into in computing thrust and power', pass_by_obj=True), promotes=['*'])
        self.add('npts_coarse_power_curve', IndepVarComp('npts_coarse_power_curve', val=20, desc='number of points to evaluate aero analysis at', pass_by_obj=True), promotes=['*'])
        self.add('npts_spline_power_curve', IndepVarComp('npts_spline_power_curve', val=200, desc='number of points to use in fitting spline to power curve', pass_by_obj=True), promotes=['*'])
        self.add('AEP_loss_factor', IndepVarComp('AEP_loss_factor', val=1.0, desc='availability and other losses (soiling, array, etc.)'), promotes=['*'])

        #self.add('weibull_shape', IndepVarComp('weibull_shape', val=0.0), promotes=['*'])

        
        # --- Rotor Aero & Power ---
        self.add('turbineclass', TurbineClass())
        self.add('gridsetup', GridSetup(naero, nstr))
        self.add('grid', RGrid(naero, nstr))
        self.add('spline0', GeometrySpline(naero, nstr))
        self.add('spline', GeometrySpline(naero, nstr))
        self.add('geom', CCBladeGeometry())
        # self.add('tipspeed', MaxTipSpeed())
        self.add('setup', SetupRunVarSpeed(npts_coarse_power_curve))
        self.add('analysis', CCBladePower(naero, npts_coarse_power_curve))
        self.add('dt', CSMDrivetrain(npts_coarse_power_curve))
        self.add('powercurve', RegulatedPowerCurveGroup(npts_coarse_power_curve, npts_spline_power_curve))
        self.add('wind', PowerWind(1))
        # self.add('cdf', WeibullWithMeanCDF(npts_spline_power_curve))
        self.add('cdf', RayleighCDF(npts_spline_power_curve))
        self.add('aep', AEP(npts_spline_power_curve))

        self.add('outputs_aero', OutputsAero(npts_spline_power_curve), promotes=['*'])

        
        # connections to turbineclass
        self.connect('turbine_class', 'turbineclass.turbine_class')

        # connections to gridsetup
        self.connect('initial_aero_grid', 'gridsetup.initial_aero_grid')
        self.connect('initial_str_grid', 'gridsetup.initial_str_grid')

        # connections to grid
        self.connect('r_aero', 'grid.r_aero')
        self.connect('gridsetup.fraction', 'grid.fraction')
        self.connect('gridsetup.idxj', 'grid.idxj')

        # connections to spline0
        self.connect('r_aero', 'spline0.r_aero_unit')
        self.connect('grid.r_str', 'spline0.r_str_unit')
        self.connect('r_max_chord', 'spline0.r_max_chord')
        self.connect('chord_sub', 'spline0.chord_sub')
        self.connect('theta_sub', 'spline0.theta_sub')
        self.connect('precurve_sub', 'spline0.precurve_sub')
        self.connect('bladeLength', 'spline0.bladeLength')
        self.connect('idx_cylinder_aero', 'spline0.idx_cylinder_aero')
        self.connect('idx_cylinder_str', 'spline0.idx_cylinder_str')
        self.connect('hubFraction', 'spline0.hubFraction')
        self.connect('sparT', 'spline0.sparT')
        self.connect('teT', 'spline0.teT')

        # connections to spline
        self.connect('r_aero', 'spline.r_aero_unit')
        self.connect('grid.r_str', 'spline.r_str_unit')
        self.connect('r_max_chord', 'spline.r_max_chord')
        self.connect('chord_sub', 'spline.chord_sub')
        self.connect('theta_sub', 'spline.theta_sub')
        self.connect('precurve_sub', 'spline.precurve_sub')
        self.connect('bladeLength', 'spline.bladeLength')
        self.connect('idx_cylinder_aero', 'spline.idx_cylinder_aero')
        self.connect('idx_cylinder_str', 'spline.idx_cylinder_str')
        self.connect('hubFraction', 'spline.hubFraction')
        self.connect('sparT', 'spline.sparT')
        self.connect('teT', 'spline.teT')

        # connections to geom
        # self.spline['precurve_str'] = np.zeros(1)
        self.connect('spline.Rtip', 'geom.Rtip')
        self.connect('precone', 'geom.precone')
        self.connect('spline.precurve_str', 'geom.precurveTip', src_indices=[naero-1])

        # # connectiosn to tipspeed
        # self.connect('geom.R', 'tipspeed.R')
        # self.connect('max_tip_speed', 'tipspeed.Vtip_max')
        # self.connect('tipspeed.Omega_max', 'control:maxOmega')

        # connections to setup
        # self.connect('control', 'setup.control')
        self.connect('control:Vin', 'setup.control:Vin')
        self.connect('control:Vout', 'setup.control:Vout')
        self.connect('control:maxOmega', 'setup.control:maxOmega')
        self.connect('control:minOmega', 'setup.control:minOmega')
        self.connect('control:pitch', 'setup.control:pitch')
        self.connect('control:ratedPower', 'setup.control:ratedPower')
        self.connect('control:tsr', 'setup.control:tsr')
        self.connect('geom.R', 'setup.R')
        self.connect('npts_coarse_power_curve', 'setup.npts')

        # connections to analysis
        self.connect('spline.r_aero', 'analysis.r')
        self.connect('spline.chord_aero', 'analysis.chord')
        self.connect('spline.theta_aero', 'analysis.theta')
        self.connect('spline.precurve_aero', 'analysis.precurve')
        self.connect('spline.precurve_str', 'analysis.precurveTip', src_indices=[nstr-1])
        self.connect('spline.Rhub', 'analysis.Rhub')
        self.connect('spline.Rtip', 'analysis.Rtip')
        #self.connect('hubHt', 'analysis.hubHt')
        self.connect('precone', 'analysis.precone')
        self.connect('tilt', 'analysis.tilt')
        self.connect('yaw', 'analysis.yaw')
        self.connect('airfoil_files', 'analysis.airfoil_files')
        self.connect('nBlades', 'analysis.B')
        #self.connect('rho', 'analysis.rho')
        #self.connect('mu', 'analysis.mu')
        #self.connect('shearExp', 'analysis.shearExp')
        self.connect('nSector', 'analysis.nSector')
        self.connect('setup.Uhub', 'analysis.Uhub')
        self.connect('setup.Omega', 'analysis.Omega')
        self.connect('setup.pitch', 'analysis.pitch')
        self.connect('tiploss', 'analysis.tiploss')
        self.connect('hubloss', 'analysis.hubloss')
        self.connect('wakerotation', 'analysis.wakerotation')
        self.connect('usecd', 'analysis.usecd')

        # connections to drivetrain
        self.connect('analysis.P', 'dt.aeroPower')
        self.connect('analysis.Q', 'dt.aeroTorque')
        self.connect('analysis.T', 'dt.aeroThrust')
        self.connect('control:ratedPower', 'dt.ratedPower')
        self.connect('drivetrainType', 'dt.drivetrainType')

        # connections to powercurve
        self.connect('control:Vin', 'powercurve.control:Vin')
        self.connect('control:Vout', 'powercurve.control:Vout')
        self.connect('control:maxOmega', 'powercurve.control:maxOmega')
        self.connect('control:minOmega', 'powercurve.control:minOmega')
        self.connect('control:pitch', 'powercurve.control:pitch')
        self.connect('control:ratedPower', 'powercurve.control:ratedPower')
        self.connect('control:tsr', 'powercurve.control:tsr')
        self.connect('setup.Uhub', 'powercurve.Vcoarse')
        self.connect('dt.power', 'powercurve.Pcoarse')
        self.connect('analysis.T', 'powercurve.Tcoarse')
        self.connect('geom.R', 'powercurve.R')
        self.connect('npts_spline_power_curve', 'powercurve.npts')

        # # setup Brent method to find rated speed
        # self.connect('control:Vin', 'brent.lower_bound')
        # self.connect('control:Vout', 'brent.upper_bound')
        # self.brent.add_param('powercurve.Vrated', low=-1e-15, high=1e15)
        # self.brent.add_constraint('powercurve.residual = 0')
        # self.brent.invalid_bracket_return = 1.0

        # connections to wind
        #self.wind.z = np.zeros(1)
        #self.wind.U = np.zeros(1)
        # self.connect('cdf_reference_mean_wind_speed', 'wind.Uref')
        self.connect('turbineclass.V_mean', 'wind.Uref')
        self.connect('cdf_reference_height_wind_speed', 'wind.zref')
        #self.connect('hubHt', 'wind.z', src_indices=[0])
        #self.connect('shearExp', 'wind.shearExp')

        # connections to cdf
        self.connect('powercurve.V', 'cdf.x')
        self.connect('wind.U', 'cdf.xbar', src_indices=[0])
        # self.connect('weibull_shape', 'cdf.k') #TODO

        # connections to aep
        self.connect('cdf.F', 'aep.CDF_V')
        self.connect('powercurve.P', 'aep.P')
        self.connect('AEP_loss_factor', 'aep.lossFactor')

        # connections to outputs
        self.connect('powercurve.V', 'V_in')
        self.connect('powercurve.P', 'P_in')
        self.connect('aep.AEP', 'AEP_in')
        self.connect('powercurve.ratedConditions:V', 'ratedConditions:V_in')
        self.connect('powercurve.ratedConditions:Omega', 'ratedConditions:Omega_in')
        self.connect('powercurve.ratedConditions:pitch', 'ratedConditions:pitch_in')
        self.connect('powercurve.ratedConditions:T', 'ratedConditions:T_in')
        self.connect('powercurve.ratedConditions:Q', 'ratedConditions:Q_in')


        self.connect('spline.diameter', 'hub_diameter_in')
        self.connect('geom.diameter', 'diameter_in')


        # connect to outputs
        self.connect('turbineclass.V_extreme', 'V_extreme_in')
        self.connect('spline.Rtip', 'Rtip_in')
        self.connect('spline.precurve_str', 'precurveTip_in', src_indices=[nstr-1])
        self.connect('spline.presweep_str', 'presweepTip_in', src_indices=[nstr-1])


if __name__ == '__main__':

	initial_aero_grid = np.array([0.02222276, 0.06666667, 0.11111057, 0.16666667, 0.23333333, 0.3, 0.36666667,
	    0.43333333, 0.5, 0.56666667, 0.63333333, 0.7, 0.76666667, 0.83333333, 0.88888943, 0.93333333,
	    0.97777724])  # (Array): initial aerodynamic grid on unit radius
	initial_str_grid = np.array([0.0, 0.00492790457512, 0.00652942887106, 0.00813095316699, 0.00983257273154,
	    0.0114340970275, 0.0130356213234, 0.02222276, 0.024446481932, 0.026048006228, 0.06666667, 0.089508406455,
	    0.11111057, 0.146462614229, 0.16666667, 0.195309105255, 0.23333333, 0.276686558545, 0.3, 0.333640766319,
	    0.36666667, 0.400404310407, 0.43333333, 0.5, 0.520818918408, 0.56666667, 0.602196371696, 0.63333333,
	    0.667358391486, 0.683573824984, 0.7, 0.73242031601, 0.76666667, 0.83333333, 0.88888943, 0.93333333, 0.97777724,
	    1.0])  # (Array): initial structural grid on unit radius


	rotor = Problem()
	naero = len(initial_aero_grid)
	nstr = len(initial_str_grid)
	npts_coarse_power_curve = 20 # (Int): number of points to evaluate aero analysis at
	npts_spline_power_curve = 200  # (Int): number of points to use in fitting spline to power curve

	rotor.root = RotorAeroPower(naero, nstr, npts_coarse_power_curve, npts_spline_power_curve)

	#rotor.setup(check=False)
	rotor.setup()

	# === blade grid ===
	rotor['initial_aero_grid'] = initial_aero_grid  # (Array): initial aerodynamic grid on unit radius
	rotor['initial_str_grid'] = initial_str_grid  # (Array): initial structural grid on unit radius
	rotor['idx_cylinder_aero'] = 3  # (Int): first idx in r_aero_unit of non-cylindrical section, constant twist inboard of here
	rotor['idx_cylinder_str'] = 14  # (Int): first idx in r_str_unit of non-cylindrical section
	rotor['hubFraction'] = 0.025  # (Float): hub location as fraction of radius
	# ------------------

	# === blade geometry ===
	rotor['r_aero'] = np.array([0.02222276, 0.06666667, 0.11111057, 0.2, 0.23333333, 0.3, 0.36666667, 0.43333333,
	    0.5, 0.56666667, 0.63333333, 0.64, 0.7, 0.83333333, 0.88888943, 0.93333333,
	    0.97777724])  # (Array): new aerodynamic grid on unit radius
	rotor['r_max_chord'] = 0.23577  # (Float): location of max chord on unit radius
	rotor['chord_sub'] = np.array([3.2612, 4.5709, 3.3178, 1.4621])  # (Array, m): chord at control points. defined at hub, then at linearly spaced locations from r_max_chord to tip
	rotor['theta_sub'] = np.array([13.2783, 7.46036, 2.89317, -0.0878099])  # (Array, deg): twist at control points.  defined at linearly spaced locations from r[idx_cylinder] to tip
	rotor['precurve_sub'] = np.array([0.0, 0.0, 0.0])  # (Array, m): precurve at control points.  defined at same locations at chord, starting at 2nd control point (root must be zero precurve)
	# rotor['delta_precurve_sub'] = np.array([0.0, 0.0, 0.0])  # (Array, m): adjustment to precurve to account for curvature from loading
	rotor['sparT'] = np.array([0.05, 0.047754, 0.045376, 0.031085, 0.0061398])  # (Array, m): spar cap thickness parameters
	rotor['teT'] = np.array([0.1, 0.09569, 0.06569, 0.02569, 0.00569])  # (Array, m): trailing-edge thickness parameters
	rotor['bladeLength'] = 61.5  # (Float, m): blade length (if not precurved or swept) otherwise length of blade before curvature
	# rotor['delta_bladeLength'] = 0.0  # (Float, m): adjustment to blade length to account for curvature from loading
	rotor['precone'] = 2.5  # (Float, deg): precone angle
	rotor['tilt'] = 5.0  # (Float, deg): shaft tilt
	rotor['yaw'] = 0.0  # (Float, deg): yaw error
	rotor['nBlades'] = 3  # (Int): number of blades
	# ------------------

	# === airfoil files ===
	basepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '5MW_AFFiles')

	# load all airfoils
	airfoil_types = [0]*8
	airfoil_types[0] = os.path.join(basepath, 'Cylinder1.dat')
	airfoil_types[1] = os.path.join(basepath, 'Cylinder2.dat')
	airfoil_types[2] = os.path.join(basepath, 'DU40_A17.dat')
	airfoil_types[3] = os.path.join(basepath, 'DU35_A17.dat')
	airfoil_types[4] = os.path.join(basepath, 'DU30_A17.dat')
	airfoil_types[5] = os.path.join(basepath, 'DU25_A17.dat')
	airfoil_types[6] = os.path.join(basepath, 'DU21_A17.dat')
	airfoil_types[7] = os.path.join(basepath, 'NACA64_A17.dat')

	# place at appropriate radial stations
	af_idx = [0, 0, 1, 2, 3, 3, 4, 5, 5, 6, 6, 7, 7, 7, 7, 7, 7]

	n = len(af_idx)
	af = [0]*n
	for i in range(n):
	    af[i] = airfoil_types[af_idx[i]]
	rotor['airfoil_files'] = af  # (List): names of airfoil file
	# ----------------------

	# === atmosphere ===
	rotor['analysis.rho'] = 1.225  # (Float, kg/m**3): density of air
	rotor['analysis.mu'] = 1.81206e-5  # (Float, kg/m/s): dynamic viscosity of air
        rotor['wind.z0'] = rotor['wind.betaWind'] = 0.0
	rotor['analysis.shearExp'] = rotor['wind.shearExp'] = 0.25  # (Float): shear exponent
	rotor['analysis.hubHt'] = rotor['wind.z'] = np.array([90.0])  # (Float, m): hub height
	rotor['turbine_class'] = TURBINE_CLASS['I']  # (Enum): IEC turbine class
	rotor['cdf_reference_height_wind_speed'] = 90.0  # (Float): reference hub height for IEC wind speed (used in CDF calculation)
	# ----------------------

	# === control ===
        rotor['control:Vin'] = 3.0  # (Float, m/s): cut-in wind speed
        rotor['control:Vout'] = 25.0  # (Float, m/s): cut-out wind speed
	rotor['control:ratedPower'] = 5e6  # (Float, W): rated power
	rotor['control:minOmega'] = 0.0  # (Float, rpm): minimum allowed rotor rotation speed
	rotor['control:maxOmega'] = 12.0  # (Float, rpm): maximum allowed rotor rotation speed
	rotor['control:tsr'] = 7.55  # (Float): tip-speed ratio in Region 2 (should be optimized externally)
	rotor['control:pitch'] = 0.0  # (Float, deg): pitch angle in region 2 (and region 3 for fixed pitch machines)
	# ----------------------

	# === aero and structural analysis options ===
	rotor['nSector'] = 4  # (Int): number of sectors to divide rotor face into in computing thrust and power
	rotor['npts_coarse_power_curve'] = npts_coarse_power_curve  # (Int): number of points to evaluate aero analysis at
	rotor['npts_spline_power_curve'] = npts_spline_power_curve  # (Int): number of points to use in fitting spline to power curve
	rotor['AEP_loss_factor'] = 1.0  # (Float): availability and other losses (soiling, array, etc.)
	rotor['drivetrainType'] = DRIVETRAIN_TYPE['GEARED']  # (Enum)
	# ----------------------

	# === materials and composite layup  ===
	basepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '5MW_PreCompFiles')

	# === run and outputs ===
	rotor.run()

	print 'AEP =', rotor['AEP']
	print 'diameter =', rotor['diameter']
	print 'ratedConditions.V =', rotor['ratedConditions:V']
	print 'ratedConditions.Omega =', rotor['ratedConditions:Omega']
	print 'ratedConditions.pitch =', rotor['ratedConditions:pitch']
	print 'ratedConditions.T =', rotor['ratedConditions:T']
	print 'ratedConditions.Q =', rotor['ratedConditions:Q']
        #for io in rotor.root.unknowns:
        #    print(io + ' ' + str(rotor.root.unknowns[io]))



        import matplotlib.pyplot as plt
        plt.figure()
	plt.plot(rotor['V'], rotor['P']/1e6)
	plt.xlabel('wind speed (m/s)')
	plt.xlabel('power (W)')

	plt.show()
	# ----------------