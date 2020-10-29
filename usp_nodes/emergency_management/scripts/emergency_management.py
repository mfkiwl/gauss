#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
# Author: Carlos Capitán Fernández

'''This script is the emergency management module developed in the UTM to decide what is the best action 
to take in the U-space when some Threats are showed up.'''

import rospy
import time
import copy
from gauss_msgs.srv import Threats, ThreatsResponse, ThreatsRequest
from gauss_msgs.srv import PilotAnswer, PilotAnswerResponse, PilotAnswerRequest
from gauss_msgs.srv import ReadOperation, ReadOperationRequest
from gauss_msgs.srv import Notifications, NotificationsRequest
from gauss_msgs.srv import WriteGeofences, WriteGeofencesRequest 
from gauss_msgs.msg import Threat, Circle, Notification, Waypoint, WaypointList, Operation, Geofence, DeconflictionPlan
from gauss_msgs.srv import Deconfliction, DeconflictionRequest

class EmergencyManagement():

    def __init__(self): 
        
        # Initialization
               
        self._notifications_list = []

        self._threats2solve_list = []

        self._dictionary_all_threats = {}     
        
        # Server     

        self._threats_service = rospy.Service('/gauss/threats', Threats, self.service_threats_cb) 
        
        self._pilot_answer_service = rospy.Service('/gauss/pilotanswer', PilotAnswer, self.service_pilot_answer_cb)
        
        # Wait until services are available and create connection
        
        rospy.wait_for_service('/gauss/tactical_deconfliction')                    
        self._requestDeconfliction_service_handle = rospy.ServiceProxy('/gauss/tactical_deconfliction', Deconfliction) 

        #rospy.wait_for_service('/gauss/read_operation')                    
        #self._readOperation_service_handle = rospy.ServiceProxy('/gauss/read_operation', ReadOperation) 

        rospy.wait_for_service('/gauss/write_geofences')                    
        self._writeGeofences_service_handle = rospy.ServiceProxy('/gauss/write_geofences', WriteGeofences) 

        rospy.wait_for_service('/gauss/notifications')                    
        self._notifications_service_handle = rospy.ServiceProxy('/gauss/notifications', Notifications) 

        # Timer

        self.timer = rospy.Timer(rospy.Duration(20), self.timer_cb)
        
        print("Started Emergency Management(EM) module!. This module proposes threats solutions to the USP module.")
    
    def send_notifications(self,notifications):
        request = NotificationsRequest()
        request.notifications = self._notifications_list
        response = self._notifications_service_handle(request)
        return response
    
    def send_threat2deconfliction(self,threat2deconflicted): 
        request = DeconflictionRequest()
        request.tactical = True
        request.threat = threat2deconflicted 
        self._deconfliction_response = self._requestDeconfliction_service_handle(request) 
        return self._deconfliction_response
   
    def select_optimal_route(self):
        'Select the optimal deconfliction route '
        deconfliction_plans_list = self._deconfliction_response.deconfliction_plans
        values = []
        for deconfliction_plan in deconfliction_plans_list:
            alfa = 0.25 # Weight of cost
            beta = 0.75 # Weight of riskiness
            value = alfa*deconfliction_plan.cost + beta*deconfliction_plan.riskiness
            values.append(value)
         
        value_min = min(values)
        pos_min = values.index(min(values))
        best_solution = deconfliction_plans_list[pos_min]
        #print("The best solution is:", best_solution)
        return best_solution

#TODO crear notificaciones y llamar a la función que las manda.

    def action_decision_maker(self, threat2solve):
        threat = Threat()
        threat = threat2solve
        threat_type = threat.threat_type
        threat_time = threat.header.stamp
        uavs_threatened = threat.uav_ids
        actions_dictionary = {1:'Route to my destiny avoiding a geofence', 2:'Route to my destiny for the shortest way',
        3:'Route back home', 4:'Hovering waiting for geofence deactivation', 5:'Route landing in a landing spot',
        6:'Route to my destiny leaving the geofence asap', 7:'Hovering', 8:'Route avoiding the conflict object',
        9:'Route for going back asap to the Flight Geometry and keeping with the Flight Plan'}
        notification = Notification()
        
        if len(uavs_threatened) > 0: 

            '''Threat UAS IN CV: we send a message to the UAV in conflict for going back to the FG.'''
            if threat_type == Threat.UAS_IN_CV:   

                uav_threatened = uavs_threatened[0]
                notification.description = 'Go back to your flight plan.'
                notification.uav_id = uav_threatened
                self._notifications_list.append(notification)
                            
            '''Threat UAS OUT OV: we ask to tactical possible solution trajectories'''

            if threat_type == Threat.UAS_OUT_OV: 

                self.send_threat2deconfliction(threat)
                best_solution = self.select_optimal_route()                
                notification.uav_id = best_solution.uav_id
                notification.action = best_solution.maneuver_type
                notification.description = actions_dictionary[notification.action]
                notification.waypoints = best_solution.waypoint_list
                self._notifications_list.append(notification) 

            '''Threat LOSS OF SEPARATION: we ask to tactical possible solution trajectories'''

            if threat_type == Threat.LOSS_OF_SEPARATION:
                self.send_threat2deconfliction(threat)
                best_solution = self.select_optimal_route()
                notification.uav_id = best_solution.uav_id
                notification.action = best_solution.maneuver_type
                notification.description = actions_dictionary[notification.action]
                notification.waypoints = best_solution.waypoint_list
                self._notifications_list.append(notification) 

            '''Threat ALERT WARNING: we create a cylindrical geofence with center in "location". Besides, we notifies to all UAVs the alert detected'''
               
            if threat_type == Threat.ALERT_WARNING:    
                #We send a notification for every UAV.
                for uav in uavs_threatened:
                    notification.description = 'Alert Warning: Bad weather Fire or NDZ detected in the zone.'
                    notification.uav_id = uavs_threatened[uav]
                    self._notifications_list.append(notification) 
                    
                #Creation of the NDZ.
                geofence_base = Circle()
                alarm_center = threat.location
                geofence_base.x_center = alarm_center.x
                geofence_base.y_center = alarm_center.y
                geofence = Geofence()          
                geofence.id = 3
                geofence.min_altitude = 0.0
                geofence.max_altitude = 50.0
                geofence.circle = geofence_base

                # We write a geofence.
                request = WriteGeofencesRequest()
                request.geofence_ids = [geofence.id]
                request.geofences = [geofence]
                response = self._writeGeofences_service_handle(request)
                response.message = "Geofence stored in the Data Base."   

            '''Threat GEOFENCE INTRUSION: we ask to tactical possible solution trajectories'''

            if threat_type == Threat.GEOFENCE_INTRUSION:   
                #Publish the action which the UAV has to make.
                    
                self.send_threat2deconfliction(threat)
                best_solution = self.select_optimal_route()
                notification.uav_id = best_solution.uav_id
                notification.action = best_solution.maneuver_type
                notification.description = actions_dictionary[notification.action]
                notification.waypoints = best_solution.waypoint_list
                self._notifications_list.append(notification) 
                    
            '''Threat GEOFENCE CONFLICT: we ask to tactical possible solution trajectories'''

            if threat_type == Threat.GEOFENCE_CONFLICT:  
                #Publish the action which the UAV has to make.
                    
                self.send_threat2deconfliction(threat)
                best_solution = self.select_optimal_route()
                notification.uav_id = best_solution.uav_id
                notification.action = best_solution.maneuver_type
                notification.description = actions_dictionary[notification.action]
                notification.waypoints = best_solution.waypoint_list
                self._notifications_list.append(notification) 
                
            '''Threat TECHNICAL FAILURE: we send a message to the UAV in conflict for landing now.'''

            if threat_type == Threat.TECHNICAL_FAILURE:  
                #Publish the action which the UAV has to make.
                uav_threatened = uavs_threatened[0]
                notification.description = 'URGENT: Land now.'
                notification.uav_id = uav_threatened
                self._notifications_list.append(notification) 
                
                # We create a geofence.
                geofence = Geofence()
                geofence.id = 3
                geofence.min_altitude = 0.0
                geofence.max_altitude = 100.0
                    
                # We write a geofence.
                request = WriteGeofencesRequest()
                request.geofence_ids = [geofence.id]
                request.geofences = [geofence]
                response = self._writeGeofences_service_handle(request)
                response.message = "Geofence stored in the Data Base."

            '''Threat COMMUNICATION FAILURE: we EM can not do anything if there is a lost of the link communication between the GCS and/or the
                UAV and USP.'''

            if threat_type == Threat.COMMUNICATION_FAILURE: 
                    
                #Publish the action which the UAV has to make.
                uav_threatened = uavs_threatened[0]
                notification.description = 'Change UAV control mode from autonomous to manual.'
                notification.uav_id = uav_threatened
                self._notifications_list.append(notification) 
                    
            '''Threat LACK OF BATTERY: we ask to tactical possible solution trajectories'''

            if threat_type == Threat.LACK_OF_BATTERY:  
                #Publish the action which the UAV has to make.
                self.send_threat2deconfliction(threat)
                best_solution = self.select_optimal_route()
                notification.uav_id = best_solution.uav_id
                notification.action = best_solution.maneuver_type
                notification.description = actions_dictionary[notification.action]
                notification.waypoints = best_solution.waypoint_list
                self._notifications_list.append(notification) 
                    
            '''Threat JAMMING ATTACK: We send a message for landing within the geofence created
                around the UAV.'''
            if threat_type == Threat.JAMMING_ATTACK: 
                #Publish the action which the UAV has to make.
                uav_threatened = uavs_threatened[0]
                notification.description = 'Land within the geofence created around the UAV.'
                notification.uav_id = uav_threatened
                self._notifications_list.append(notification) 
                
                # We create a geofence.
                geofence = Geofence()
                geofence.id = 3
                geofence.min_altitude = 0.0
                geofence.max_altitude = 100.0
                    
                # We write a geofence.
                request = WriteGeofencesRequest()
                request.geofence_ids = [geofence.id]
                request.geofences = [geofence]
                response = self._writeGeofences_service_handle(request)
                response.message = "Geofence stored in the Data Base."       

            '''Threat SPOOFING ATTACK: We send a recommendation to the UAV in order to activate the FTS
                and we create a geofence around the UAV.'''

            if threat_type == Threat.SPOOFING_ATTACK: 
                
                #Publish the action which the UAV has to make.
                uav_threatened = uavs_threatened[0]
                notification.description = 'Activate the Flight Termination System (FTS) of the UAV.'
                notification.uav_id = uav_threatened
                self._notifications_list.append(notification) 
            
                # We create a geofence.
                geofence = Geofence()
                geofence.id = 3
                geofence.min_altitude = 0.0
                geofence.max_altitude = 100.0
                    
                # We write a geofence.
                request = WriteGeofencesRequest()
                request.geofence_ids = [geofence.id]
                request.geofences = [geofence]
                response = self._writeGeofences_service_handle(request)
                response.message = "Geofence stored in the Data Base."   

            '''Threat GNSS DEGRADATION: we wait a period of time and then we ask to tactical
                possible trajectories to landing spots'''

            if threat_type == Threat.GNSS_DEGRADATION: 
                    
                #Publish the action which the UAV has to make.
                    
                self.send_threat2deconfliction(threat)
                best_solution = self.select_optimal_route()
                notification.uav_id = best_solution.uav_id
                notification.action = best_solution.maneuver_type
                notification.description = actions_dictionary[notification.action]
                notification.waypoints = best_solution.waypoint_list
                self._notifications_list.append(notification) 

    def service_threats_cb(self, request):
        req = ThreatsRequest()
        req = copy.deepcopy(request)
        num = len(req.threats)
        rospy.loginfo("EM has received %d threats!", num) 
        for i in range(num): # Bucle para RELLENAR la lista de Threats recibido.
            self._threats2solve_list.append(req.threats[i])
        
        #ordenamos la lista de mayor a menor severidad.
        self._threats2solve_list = sorted(self._threats2solve_list, key=lambda x:x.threat_type) 
        
        for threat in self._threats2solve_list: # Bucle para RELLENAR un diccionario con todos los threat_id y su estado actual.
            key = threat.threat_id
            value = 'TODO'
            self._dictionary_all_threats[key] = value
        #print("This is the list of Threat_ids and their status:", self._dictionary_all_threats)
        res = ThreatsResponse()
        res.success = True
        return res 

    def service_pilot_answer_cb(self, request):
        req = PilotAnswerRequest()
        req = copy.deepcopy(request)
        rospy.loginfo("There are new pilot answers")
        threat_ids = req.threat_ids 
        answers = req.pilot_answers 
        num = len(threat_ids)
        if num > 0:
            for i in range(num):
                # Actualizamos el diccionario con las respuestas del piloto.
                self._dictionary_all_threats[threat_ids[i]] = answers[i] 
                if answers[i] == 'ACCEPTED':
                    del self._dictionary_all_threats[threat_ids[i]]
                    index2delete = 0
                    for threat in self._threats2solve_list:
                        key = threat.threat_id
                        if key == threat_ids[i]:
                            break
                        else:
                            index2delete = index2delete + 1 
                    if index2delete < len(self._threats2solve_list):
                        self._threats2solve_list.pop(index2delete)
                    if index2delete < len(self._notifications_list):
                        self._notifications_list.pop(index2delete)
        #print(self._threats2solve_list)
        #print(self._dictionary_all_threats)
        res = PilotAnswerResponse()
        res.success = True
        return res

    def timer_cb(self, timer):
        num = len(self._threats2solve_list)
        rospy.loginfo("Right now, there are %d active threats in the U-space", num)
        if num > 0:
            # Bucle para RESOLVER los Threats en estado TODO.
            for threat in self._threats2solve_list: 
                key = threat.threat_id
                if self._dictionary_all_threats[key] == 'TODO':
                    if self._dictionary_all_threats[key] == 'TODO':
                        self.action_decision_maker(threat)
                    self.send_notifications(self._notifications_list)
            # Bucle para CAMBIAR el estado de los Threats de TODO a NOTIFIED
            for threat in self._threats2solve_list: 
                key = threat.threat_id
                if self._dictionary_all_threats[key] == 'TODO':
                    self._dictionary_all_threats[key] = 'NOTIFIED'
        rospy.loginfo("The number of Threats active in the U-space is %d", num)
        print(self._notifications_list)
''' The node and the EmergencyManagement class are initialized'''

if __name__=='__main__':

    rospy.init_node('emergency_management')
    e = EmergencyManagement()
    rospy.spin()   




    
