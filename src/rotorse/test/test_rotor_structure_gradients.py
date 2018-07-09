#!/usr/bin/env python
# encoding: utf-8
"""
test_rotor_gradients.py

Created by Andrew Ning on 2013-01-28.
Copyright (c) NREL. All rights reserved.
"""

import pytest
import numpy as np
#from commonse.utilities import check_gradient_unit_test, check_for_missing_unit_tests
from rotorse.rotor_structure import TotalLoads, RootMoment, MassProperties, TipDeflection, \
    ExtremeLoads, GustETM, BladeCurvature, SetupPCModVarSpeed, BladeDeflection, DamageLoads, NREL5MW
from rotorse import TURBULENCE_CLASS
from openmdao.api import IndepVarComp, Problem, Group
from enum import Enum

from commonse_testing import check_gradient_unit_test, init_IndepVar_add, init_IndepVar_set# <- TODO give this a permanent home

##### Input Fixtures #####
@pytest.fixture
def inputs_str():
    data = {}
    data['r'] = np.array([1.54365, 1.84056613, 1.93905988, 2.03755362, 2.14220322, 2.24069697, 2.33919071, 2.90419974, 3.04095864, 3.13945238, 5.63750021, 7.042267, 8.37080006, 10.54495078, 11.7875002, 13.54900997, 15.8874998, 18.55372335, 19.9875, 22.05640713, 24.08750021, 26.16236509, 28.1874998, 32.2875, 33.56786348, 36.38750021, 38.57257686, 40.4874998, 42.58004108, 43.57729024, 44.5875, 46.58134943, 48.6875002, 52.7874998, 56.20419994, 58.9374998, 61.67080026, 63.03135]) + 0.1
    data['theta'] = np.array([13.30937361, 13.37481035, 13.39612366, 13.41723314, 13.4394334, 13.46010775, 13.48056399, 13.59346486, 13.61959151, 13.63810296, 14.00782542, 14.11357563, 14.13048441, 13.9535064, 13.72190245, 13.20522244, 12.09881003, 11.09001613, 10.62423592, 9.95420093, 9.30164854, 8.64364485, 8.01295522, 6.78374285, 6.41610863, 5.63959888, 5.0734068, 4.60587557, 4.11337218, 3.8828887, 3.65235536, 3.20651689, 2.74963602, 1.90574018, 1.25320975, 0.76773924, 0.31732535, 0.10692954])
    data['tilt'] = 5.0
    data['rhoA'] = np.array([1208.94372351, 1230.61068823, 1248.66706375, 1255.72162537, 1263.23121489, 1270.26690172, 1238.20623548, 1145.83450009, 1034.60310635, 1038.82374397, 900.43690091, 785.6054738, 534.12946237, 340.22172835, 335.5946689, 335.82137913, 336.10772984, 326.98228092, 320.81034793, 310.81827871, 299.45892743, 289.73831451, 273.40129825, 246.78352782, 236.07560581, 212.04663993, 196.51931429, 183.18273493, 177.0612769, 168.09294895, 158.88879462, 144.6924585, 127.41803113, 94.99318173, 69.87779352, 51.35407579, 46.55050264, 30.30079248])
    data['totalCone'] = np.array([2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5])
    data['z_az'] = data['r'] - 0.1
    return data

@pytest.fixture
def inputs_aeroloads_operating():
    data = {}
    data['aeroloads_r'] = np.array([1.5375, 1.54365, 1.84056613, 1.93905988, 2.03755362, 2.14220322, 2.24069697, 2.33919071, 2.90419974, 3.04095864, 3.13945238, 5.63750021, 7.042267, 8.37080006, 10.54495078, 11.7875002, 13.54900997, 15.8874998, 18.55372335, 19.9875, 22.05640713, 24.08750021, 26.16236509, 28.1874998, 32.2875, 33.56786348, 36.38750021, 38.57257686, 40.4874998, 42.58004108, 43.57729024, 44.5875, 46.58134943, 48.6875002, 52.7874998, 56.20419994, 58.9374998, 61.67080026, 63.03135, 63.0375])
    data['aeroloads_Px'] = np.array([0., 610.90043568, 469.20341791, 529.97827499, 580.02866009, 625.05962708, 661.78185992, 694.27930979, 830.93330879, 856.02758285, 872.85385017, 1155.30591175, 1278.65677079, 1394.84126103, 1598.03834945, 1726.35834871, 1933.87963881, 2271.78104859, 2748.8320438, 3083.27106663, 3677.62201087, 4343.75465079, 5051.54596049, 5731.9904625, 7004.11264534, 7364.31723123, 8093.26478732, 8599.46800605, 9000.96202336, 9390.16142378, 9555.38019573, 9708.33654591, 9964.10107999, 10160.41657631, 10284.8330047, 10072.19130201, 9644.34268454, 8877.83504026, 7799.39529499, 0.])
    data['aeroloads_Py'] = np.array([-0., -144.78495637, -124.72748876, -141.81359748, -155.88095732, -168.54159208, -178.87593197, -188.03239815, -226.67105832, -233.77977156, -238.54367701, -315.58006958, -346.98243408, -376.42732276, -428.40371938, -460.55814935, -514.08253305, -608.45781344, -797.59235326, -945.37444233, -1201.2028286, -1460.69809022, -1699.93141114, -1895.13844916, -2173.05749742, -2231.72002959, -2324.32717937, -2368.68132531, -2391.87757363, -2400.12541632, -2397.52018148, -2390.65909733, -2364.75629832, -2319.62320261, -2178.87813088, -2006.41143031, -1828.46265047, -1590.92929559, -887.78584275, -0.])
    data['aeroloads_Pz'] = np.array([0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.])
    data['aeroloads_Omega'] = 12.0
    data['aeroloads_pitch'] = 0.0
    data['aeroloads_azimuth'] = 0.0
    return data

@pytest.fixture
def inputs_aeroloads_extreme():
    data = {}
    data['aeroloads_r'] = np.array([1.5375, 1.54365, 1.84056613, 1.93905988, 2.03755362, 2.14220322, 2.24069697, 2.33919071, 2.90419974, 3.04095864, 3.13945238, 5.63750021, 7.042267, 8.37080006, 10.54495078, 11.7875002, 13.54900997, 15.8874998, 18.55372335, 19.9875, 22.05640713, 24.08750021, 26.16236509, 28.1874998, 32.2875, 33.56786348, 36.38750021, 38.57257686, 40.4874998, 42.58004108, 43.57729024, 44.5875, 46.58134943, 48.6875002, 52.7874998, 56.20419994, 58.9374998, 61.67080026, 63.03135, 63.0375])
    data['aeroloads_Px'] = np.array([0., 13023.34715857, 13227.41827965, 13294.64767681, 13361.64547849, 13432.57713661, 13499.09800258, 13565.38800704, 13941.21361644, 14031.04688528, 14095.47201707, 15654.39033241, 16469.52571284, 17201.5947746, 18322.04563173, 18920.90929296, 19718.63121999, 20529.98798194, 20765.77056612, 20764.81605267, 20697.7172993, 20558.61007045, 20344.48194624, 20068.58186378, 19323.67505285, 19044.52978453, 18361.45177989, 17775.34457665, 17227.60808079, 16593.90597159, 16278.14091451, 15948.96631629, 15271.07126777, 14513.01109479, 12907.33421615, 11430.58455157, 10153.1352044, 8786.07437854, 8070.9462448, 0.])
    data['aeroloads_Py'] = np.array([-0., -3539.72166293, -3611.45047642, -3635.13187625, -3658.75355824, -3683.78373085, -3707.27536287, -3730.70057174, -3863.68426615, -3895.48506871, -3918.28698863, -4460.86411544, -4726.08530159, -4941.66368807, -5202.22794774, -5289.55445114, -5320.93073426, -5115.73505562, -4786.95370967, -4608.93544588, -4340.31041931, -4067.02862229, -3782.41391136, -3503.30997995, -2949.07257816, -2782.25330523, -2430.65286443, -2176.23797886, -1968.2016328, -1753.24097031, -1654.59059923, -1557.24555451, -1373.00400736, -1190.18045634, -870.7791635, -643.03927481, -486.69162507, -353.42692686, -295.61898055, -0.])
    data['aeroloads_Pz'] = np.array([0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.])
    data['aeroloads_Omega'] = 0.0
    data['aeroloads_pitch'] = 0.0
    data['aeroloads_azimuth'] = 0.0
    return data

##### Tests #####

@pytest.mark.parametrize("inputs_str,inputs_aeroloads", [
    (inputs_str(), inputs_aeroloads_operating()),
    (inputs_str(), inputs_aeroloads_extreme())
])
def test_TotalLoads(inputs_str, inputs_aeroloads):
    npts = np.size(inputs_str['r'])

    prob = Problem()
    prob.root = Group()
    prob.root.add('comp', TotalLoads(npts), promotes=['*'])
    prob = init_IndepVar_add(prob, inputs_str)
    prob = init_IndepVar_add(prob, inputs_aeroloads)
    prob.root.comp.deriv_options['check_step_calc'] = 'relative' 
    prob.root.comp.deriv_options['check_form'] = 'central'
    prob.setup(check=False)

    prob = init_IndepVar_set(prob, inputs_str)
    prob = init_IndepVar_set(prob, inputs_aeroloads)

    check_gradient_unit_test(prob, tol=.01, display=False)

def test_TestRootMoment():

    data_aero = inputs_aeroloads_operating()
    data_str = inputs_str()

    data = {}
    data['aeroloads_r'] = np.array([1.5375, 1.54365, 1.84056613, 1.93905988, 2.03755362, 2.14220322, 2.24069697, 2.33919071, 2.90419974, 3.04095864, 3.13945238, 5.63750021, 7.042267, 8.37080006, 10.54495078, 11.7875002, 13.54900997, 15.8874998, 18.55372335, 19.9875, 22.05640713, 24.08750021, 26.16236509, 28.1874998, 32.2875, 33.56786348, 36.38750021, 38.57257686, 40.4874998, 42.58004108, 43.57729024, 44.5875, 46.58134943, 48.6875002, 52.7874998, 56.20419994, 58.9374998, 61.67080026, 63.03135, 63.0375])
    data['aeroloads_Px'] = np.array([0., 610.90043568, 469.20341791, 529.97827499, 580.02866009, 625.05962708, 661.78185992, 694.27930979, 830.93330879, 856.02758285, 872.85385017, 1155.30591175, 1278.65677079, 1394.84126103, 1598.03834945, 1726.35834871, 1933.87963881, 2271.78104859, 2748.8320438, 3083.27106663, 3677.62201087, 4343.75465079, 5051.54596049, 5731.9904625, 7004.11264534, 7364.31723123, 8093.26478732, 8599.46800605, 9000.96202336, 9390.16142378, 9555.38019573, 9708.33654591, 9964.10107999, 10160.41657631, 10284.8330047, 10072.19130201, 9644.34268454, 8877.83504026, 7799.39529499, 0.])
    data['aeroloads_Py'] = np.array([-0., -144.78495637, -124.72748876, -141.81359748, -155.88095732, -168.54159208, -178.87593197, -188.03239815, -226.67105832, -233.77977156, -238.54367701, -315.58006958, -346.98243408, -376.42732276, -428.40371938, -460.55814935, -514.08253305, -608.45781344, -797.59235326, -945.37444233, -1201.2028286, -1460.69809022, -1699.93141114, -1895.13844916, -2173.05749742, -2231.72002959, -2324.32717937, -2368.68132531, -2391.87757363, -2400.12541632, -2397.52018148, -2390.65909733, -2364.75629832, -2319.62320261, -2178.87813088, -2006.41143031, -1828.46265047, -1590.92929559, -887.78584275, -0.])
    data['aeroloads_Pz'] = np.array([0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.])
    data['r_pts'] = np.array([1.54365, 1.84056613, 1.93905988, 2.03755362, 2.14220322, 2.24069697, 2.33919071, 2.90419974, 3.04095864, 3.13945238, 5.63750021, 7.042267, 8.37080006, 10.54495078, 11.7875002, 13.54900997, 15.8874998, 18.55372335, 19.9875, 22.05640713, 24.08750021, 26.16236509, 28.1874998, 32.2875, 33.56786348, 36.38750021, 38.57257686, 40.4874998, 42.58004108, 43.57729024, 44.5875, 46.58134943, 48.6875002, 52.7874998, 56.20419994, 58.9374998, 61.67080026, 63.03135])
    data['totalCone'] = np.array([2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5])
    data['x_az'] = np.array([0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.])
    data['y_az'] = np.array([0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.])
    data['z_az'] = np.array([1.54365, 1.84056613, 1.93905988, 2.03755362, 2.14220322, 2.24069697, 2.33919071, 2.90419974, 3.04095864, 3.13945238, 5.63750021, 7.042267, 8.37080006, 10.54495078, 11.7875002, 13.54900997, 15.8874998, 18.55372335, 19.9875, 22.05640713, 24.08750021, 26.16236509, 28.1874998, 32.2875, 33.56786348, 36.38750021, 38.57257686, 40.4874998, 42.58004108, 43.57729024, 44.5875, 46.58134943, 48.6875002, 52.7874998, 56.20419994, 58.9374998, 61.67080026, 63.03135])
    data['s'] = np.array([1.54365, 1.84056613, 1.93905988, 2.03755362, 2.14220322, 2.24069697, 2.33919071, 2.90419974, 3.04095864, 3.13945238, 5.63750021, 7.042267, 8.37080006, 10.54495078, 11.7875002, 13.54900997, 15.8874998, 18.55372335, 19.9875, 22.05640713, 24.08750021, 26.16236509, 28.1874998, 32.2875, 33.56786348, 36.38750021, 38.57257686, 40.4874998, 42.58004108, 43.57729024, 44.5875, 46.58134943, 48.6875002, 52.7874998, 56.20419994, 58.9374998, 61.67080026, 63.03135])
    data['r_pts'] = data['r_pts'] + 0.1
    npts = np.size(data['z_az'])

    prob = Problem()
    prob.root = Group()
    prob.root.add('comp', RootMoment(npts), promotes=['*'])
    prob = init_IndepVar_add(prob, data)
    prob.root.comp.deriv_options['form'] = 'central'
    prob.root.comp.deriv_options['check_form'] = 'central'
    prob.root.comp.deriv_options['step_calc'] = 'relative'   
    prob.root.comp.deriv_options['check_step_calc'] = 'relative'
    prob.setup(check=False)

    prob = init_IndepVar_set(prob, data)

    # check_gradient_unit_test(prob, tol=5e-3)
    check_gradient_unit_test(prob, tol=0.05)


def test_MassProperties():

    data = {}
    data['blade_mass'] = 17288.717087
    data['blade_moment_of_inertia'] = 11634376.0531
    data['tilt'] = 5.0
    data['nBlades'] = 3

    prob = Problem()
    prob.root = Group()
    prob.root.add('comp', MassProperties(), promotes=['*'])
    prob = init_IndepVar_add(prob, data)
    prob.root.comp.deriv_options['check_form'] = 'central'
    prob.root.comp.deriv_options['check_step_calc'] = 'relative'
    prob.setup(check=False)

    prob = init_IndepVar_set(prob, data)

    check_gradient_unit_test(prob)


def test_TipDeflection():
    data = {}
    data['dx'] = 4.27242809591
    data['dy'] = -0.371550675139
    data['dz'] = 0.0400553989266
    data['theta'] = -0.0878099
    data['pitch'] = 0.0
    data['azimuth'] = 180.0
    data['tilt'] = 5.0
    data['totalConeTip'] = 2.5
    data['dynamicFactor'] = 1.2

    prob = Problem()
    prob.root = Group()
    prob.root.add('comp', TipDeflection(), promotes=['*'])
    prob = init_IndepVar_add(prob, data)
    prob.setup(check=False)
    prob = init_IndepVar_set(prob, data)

    check_gradient_unit_test(prob)


def test_ExtremeLoads():

    data = {}
    data['T'] = np.array([2414072.40260361, 188461.59444074])
    data['Q']= np.array([10926313.24295958, -8041330.51312603])
    data['nBlades'] = 3

    prob = Problem()
    prob.root = Group()
    prob.root.add('comp', ExtremeLoads(), promotes=['*'])
    prob = init_IndepVar_add(prob, data)
    prob.setup(check=False)
    prob = init_IndepVar_set(prob, data)

    check_gradient_unit_test(prob, tol=1.5e-4)



def test_GustETM():

    data = {}
    data['V_mean'] = 10.0
    data['V_hub'] = 11.7733866478
    data['std'] = 3
    data['turbulence_class'] = TURBULENCE_CLASS['B']

    prob = Problem()
    prob.root = Group()
    prob.root.add('comp', GustETM(), promotes=['*'])
    prob = init_IndepVar_add(prob, data)
    prob.setup(check=False)
    prob = init_IndepVar_set(prob, data)

    check_gradient_unit_test(prob)


def test_BladeCurvature():

    data = {}
    data['r'] = np.array([1.5375, 1.84056613137, 1.93905987557, 2.03755361977, 2.14220322299, 2.24069696719, 2.33919071139, 2.90419974, 3.04095863882, 3.13945238302, 5.637500205, 7.04226699698, 8.370800055, 11.8494282928, 13.8375, 14.7182548841, 15.887499795, 18.5537233505, 19.9875, 22.0564071286, 24.087500205, 26.16236509, 28.187499795, 32.2875, 33.5678634821, 36.387500205, 38.5725768593, 40.487499795, 40.6967540173, 40.7964789782, 40.8975, 42.6919644014, 44.5875, 52.787499795, 56.204199945, 58.937499795, 61.67080026, 63.0375])
    data['precurve'] = np.array([0.0, 0.043324361025, 0.0573893371698, 0.0714469497372, 0.0863751069858, 0.100417566593, 0.114452695996, 0.194824077331, 0.214241777459, 0.228217752953, 0.580295739194, 0.776308800624, 0.960411633829, 1.4368012564, 1.7055214864, 1.823777005, 1.98003324362, 2.32762426752, 2.50856911855, 2.76432512112, 3.0113656418, 3.26199245912, 3.50723775206, 4.0150233695, 4.17901272929, 4.55356019347, 4.85962948702, 5.14086873143, 5.17214747287, 5.18708601127, 5.20223968442, 5.47491847385, 5.77007321175, 7.12818875977, 7.7314427824, 8.22913789456, 8.73985955154, 9.0])
    data['presweep'] = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    data['precone'] = 2.5
    npts = np.size(data['r'])

    prob = Problem()
    prob.root = Group()
    prob.root.add('comp', BladeCurvature(npts), promotes=['*'])
    prob = init_IndepVar_add(prob, data)
    prob.setup(check=False)
    prob = init_IndepVar_set(prob, data)

    check_gradient_unit_test(prob, tol=5e-5)


def test_SetupPCModVarSpeed():

    data = {}
    data['control_tsr'] = 8.0
    data['control_pitch'] = 1.0
    data['Vrated'] = 12.0
    data['R'] = 63.0
    data['Vfactor'] = 0.7

    prob = Problem()
    prob.root = Group()
    prob.root.add('comp', SetupPCModVarSpeed(), promotes=['*'])
    prob = init_IndepVar_add(prob, data)
    prob.setup(check=False)
    prob = init_IndepVar_set(prob, data)

    check_gradient_unit_test(prob)


def test_BladeDeflection():
    NINPUT = 5

    data = {}
    data['dx'] = np.array([0.0, 1.39292987639e-05, 2.42964362361e-05, 3.73611415086e-05, 5.41276445811e-05, 7.25773833888e-05, 9.35928069108e-05, 0.000268596883961, 0.000326596195925, 0.000372259193056, 0.00253285667923, 0.00455502505195, 0.00706548815047, 0.017530829505, 0.0272151750396, 0.0326222002275, 0.0410034329532, 0.0655343595834, 0.0818962168404, 0.109404026845, 0.140873579829, 0.177728457961, 0.218834564559, 0.318921553007, 0.354759106888, 0.442199496033, 0.51925808593, 0.593774567144, 0.602307030873, 0.606403310701, 0.610574803156, 0.688594372351, 0.779039709944, 1.2575016857, 1.49348304065, 1.69400834707, 1.90049599542, 2.00437890947])
    data['dy'] = np.array([0.0, -9.11673273998e-07, -1.59100573731e-06, -2.44958708331e-06, -3.55417484862e-06, -4.77185559999e-06, -6.16078184177e-06, -1.77741315033e-05, -2.16387627714e-05, -2.46907649535e-05, -0.000177142122562, -0.00032886393339, -0.000523351402122, -0.00136667950935, -0.00215626107629, -0.00258384925494, -0.00322230578732, -0.00497009730837, -0.00607094164543, -0.00784913963514, -0.00980572470543, -0.0120149227037, -0.0143773305481, -0.0197932419212, -0.0216584171821, -0.0260612290834, -0.0297556792352, -0.0331954636074, -0.0335827012855, -0.0337680683508, -0.0339563913295, -0.0373950218981, -0.0412189884014, -0.0597108654077, -0.0681209435104, -0.0750137913709, -0.0819682184214, -0.085450339495])
    data['dz'] = np.array([0.0, 0.000190681386865, 0.000249594803444, 0.000305808888278, 0.000363037181592, 0.000414559803159, 0.000465006717172, 0.00079021115147, 0.000878140045153, 0.000937905765842, 0.00236994444878, 0.003141201122, 0.00385188728597, 0.0059090995974, 0.00721749042255, 0.00775193614485, 0.00838246793108, 0.00965065210961, 0.010256099836, 0.0110346081014, 0.0117147556349, 0.0123373351129, 0.0128834601832, 0.0138847141125, 0.014168689932, 0.0147331399477, 0.0151335663707, 0.015450772371, 0.015480903206, 0.0154926033582, 0.0155017716157, 0.0156218668894, 0.0157089720273, 0.0159512118376, 0.0160321965202, 0.0160695719649, 0.0160814363339, 0.0160814363339])
    data['pitch'] = 0.0
    data['theta'] = np.array([13.2783, 13.2783, 13.2783, 13.2783, 13.2783, 13.2783, 13.2783, 13.2783, 13.2783, 13.2783, 13.2783, 13.2783, 13.2783, 13.2783, 13.2783, 12.9342399734, 12.4835173655, 11.4807910924, 10.9555299481, 10.2141623046, 9.50473135323, 8.7980712345, 8.12522342051, 6.81383731475, 6.42068577363, 5.58414615907, 4.96394315694, 4.44088253161, 4.38489418276, 4.35829308634, 4.33139992746, 3.86272702658, 3.38639207628, 1.57773054352, 0.953410121155, 0.504987738102, 0.0995174088527, -0.0878099])
    data['r_in0'] = np.array([1.5375, 13.2620872, 17.35321975, 40.19535987, 63.0375])
    data['Rhub0'] = 1.5375
    data['r_pts0'] = np.array([1.5375, 1.84056613137, 1.93905987557, 2.03755361977, 2.14220322299, 2.24069696719, 2.33919071139, 2.90419974, 3.04095863882, 3.13945238302, 5.637500205, 7.04226699698, 8.370800055, 11.8494282928, 13.8375, 14.7182548841, 15.887499795, 18.5537233505, 19.9875, 22.0564071286, 24.087500205, 26.16236509, 28.187499795, 32.2875, 33.5678634821, 36.387500205, 38.5725768593, 40.487499795, 40.6967540173, 40.7964789782, 40.8975, 42.6919644014, 44.5875, 52.787499795, 56.204199945, 58.937499795, 61.67080026, 63.0375])
    data['precurve0'] = np.zeros_like(data['dx']) #np.linspace(0.0, 5.0, np.size(data['dx']))
    data['bladeLength0'] = 61.5
    npts = np.size(data['dx'])

    prob = Problem()
    prob.root = Group()
    prob.root.add('comp', BladeDeflection(npts), promotes=['*'])
    prob = init_IndepVar_add(prob, data)
    prob.setup(check=False)
    prob = init_IndepVar_set(prob, data)

    check_gradient_unit_test(prob, tol=1e-4)


def test_DamageLoads():

    data = {}
    data['r'] = np.array([2.8667, 5.6, 8.3333, 11.75, 15.85, 19.95, 24.05, 28.15, 32.25, 36.35, 40.45, 44.55, 48.65, 52.75, 56.1667, 58.9, 61.6333])  # (Array): new aerodynamic grid on unit radius
    data['rstar'] = np.array([0.000, 0.022, 0.067, 0.111, 0.167, 0.233, 0.300, 0.367, 0.433, 0.500,
        0.567, 0.633, 0.700, 0.767, 0.833, 0.889, 0.933, 0.978])  # (Array): nondimensional radial locations of damage equivalent moments
    data['Mxb'] = 1e3*np.array([2.3743E+003, 2.0834E+003, 1.8108E+003, 1.5705E+003, 1.3104E+003,
        1.0488E+003, 8.2367E+002, 6.3407E+002, 4.7727E+002, 3.4804E+002, 2.4458E+002, 1.6339E+002,
        1.0252E+002, 5.7842E+001, 2.7349E+001, 1.1262E+001, 3.8549E+000, 4.4738E-001])  # (Array, N*m): damage equivalent moments about blade c.s. x-direction
    data['Myb'] = 1e3*np.array([2.7732E+003, 2.8155E+003, 2.6004E+003, 2.3933E+003, 2.1371E+003,
        1.8459E+003, 1.5582E+003, 1.2896E+003, 1.0427E+003, 8.2015E+002, 6.2449E+002, 4.5229E+002,
        3.0658E+002, 1.8746E+002, 9.6475E+001, 4.2677E+001, 1.5409E+001, 1.8426E+000])  # (Array, N*m): damage equivalent moments about blade c.s. y-direction
    data['theta'] = np.array([13.308, 13.308, 13.308, 13.308, 11.48, 10.162, 9.011, 7.795, 6.544, 5.361, 4.188, 3.125, 2.319, 1.526, 0.863, 0.37, 0.106])
    npts = np.size(data['r'])

    prob = Problem()
    prob.root = Group()
    prob.root.add('comp', DamageLoads(npts), promotes=['*'])
    prob = init_IndepVar_add(prob, data)
    prob.root.comp.deriv_options['check_form'] = 'central'
    prob.root.comp.deriv_options['check_step_calc'] = 'relative'   
    prob.setup(check=False)
    prob = init_IndepVar_set(prob, data)

    check_gradient_unit_test(prob, tol=5e-5)

