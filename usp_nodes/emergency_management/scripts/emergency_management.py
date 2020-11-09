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
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path

class EmergencyManagement():
    
    class Threat2Solve:
        def __init__(self, threat_time, threat_status, threat):
            self.timestamp = threat_time 
            self.status = threat_status 
            self.threat_msg = threat 

    def __init__(self): 
        
        # Initialization

        self._threats_list = [] # Lista de objetos Threat2Solve()               

        self._notifications_list = []   

        self._conflictive_operations = []
        self._conflictive_geofences = []

        self._dictionary_all_threats = {}     
        
        # Server     

        self._threats_service = rospy.Service('/gauss/threats', Threats, self.service_threats_cb) 
        
        self._pilot_answer_service = rospy.Service('/gauss/pilotanswer', PilotAnswer, self.service_pilot_answer_cb)
        
        # Wait until services are available and create connection
        
        rospy.wait_for_service('/gauss/tactical_deconfliction')                    
        self._reqDeconfliction_service_handle = rospy.ServiceProxy('/gauss/tactical_deconfliction', Deconfliction) 

        rospy.wait_for_service('/gauss/write_geofences')                    
        self._writeGeofences_service_handle = rospy.ServiceProxy('/gauss/write_geofences', WriteGeofences) 

        rospy.wait_for_service('/gauss/notifications')                    
        self._notifications_service_handle = rospy.ServiceProxy('/gauss/notifications', Notifications) 

        # Timer

        self.timer = rospy.Timer(rospy.Duration(20), self.timer_cb)
        
        print("Started Emergency Management(EM) module!. This module proposes threats solutions to the USP module.")
    
    # def create_new_flight_plan(self, flightplan, threat, maneuver):
    #     flightplan = flightplan # Es un WaypointList
    #     new_flight_plan = Path() # Es un mensaje Path
    #     merge2end = False
    #     flighplansection = 0
    #     threat = Threat(threat) #no es necesaria.
    #     maneuver = maneuver

    #     if threat.threat_type == threat.GEOFENCE_CONFLICT:
    #         if maneuver == 1: # Route to my destination avoiding a geofence.
    #             merge2end = True
    #             flighplansection = 0
    #             break
    #         if maneuver == 3: # Route for going back home.
    #             merge2end = False
    #             flighplansection = 2
    #             break
    #         break

    #     elif threat.threat_type == threat.GEOFENCE_INTRUSION:
    #         if maneuver == 2: # Route to my destination by the shortest way.
    #             merge2end = False
    #             flighplansection = 2
    #             break
    #         if maneuver == 3: # Route for going back home.
    #             merge2end = False
    #             flighplansection = 2
    #             break
    #         if maneuver == 6: # Route to my destination leaving the geofence asap.
    #             merge2end = False
    #             flighplansection = 2
    #             break
    #         break   

    #     elif threat.threat_type == threat.GNSS_DEGRADATION:
    #         if maneuver == 5: # Route for landing in a landing spot.
    #             merge2end = False
    #             flighplansection = 2
    #             break
    #         break

    #     elif threat.threat_type == threat.LACK_OF_BATTERY:
    #         if maneuver == 5: # Route for landing in a landing spot.
    #             merge2end = False
    #             flighplansection = 2
    #             break 
    #         break

    #     elif threat.threat_type == threat.LOSS_OF_SEPARATION:
    #         merge2end = True
    #         flighplansection = 0
    #         break

    #     elif threat.threat_type == threat.UAS_OUT_OV:
    #         if maneuver == 9: # Route for going back to the flight geometry and its flight plan.
    #             merge2end = True
    #             flighplansection = 2
    #             break    
    #         if maneuver == 10: # Route to keep the flight plan. No matter how much the uav is out of the OV.
    #             merge2end = True
    #             flighplansection = 2
    #             break    
    #         break
        
    #     change_path_ref = False
    #     for i in range(len(flightplan.waypoints)):
    #         temp_pose = PoseStamped()
            
    #         if flighplansection == 0: # Fist section. Do anything until current waypoint.
    #             if (flightplan.waypoints[i].x == flightplan.waypoints[current_wp].x and
    #             flightplan.waypoints[i].y == flightplan.waypoints[current_wp].y and
    #             flightplan.waypoints[i].z == flightplan.waypoints[current_wp].z):
    #                 flighplansection = 1
    #             else:
    #                 break
    #         elif flighplansection = 1: # Introduce waypoints between the current waypoint and the first one of the solution
    #             if (flightplan.waypoints[i].x == notification.waypoints[0].x and
    #             flightplan.waypoints[i].y == notification.waypoints[0].y and
    #             flightplan.waypoints[i].z == notification.waypoints[0].z):
    #                 flighplansection = 2 
    #             else:
    #                 temp_pose.pose.position.x = notification.waypoints[i].x
    #                 temp_pose.pose.position.y = notification.waypoints[i].y
    #                 temp_pose.pose.position.z = notification.waypoints[i].z
    #                 temp_pose.header.stamp = notification.waypoints[i].stamp
    #                 new_flight_plan.poses.append(temp_pose)    
    #             break

    #         elif flighplansection = 2: #Introduce the solution
    #             for i in range(len(notification.waypoints)):
    #                 temp_pose.pose.position.x = notification.waypoints[i].x
    #                 temp_pose.pose.position.y = notification.waypoints[i].y
    #                 temp_pose.pose.position.z = notification.waypoints[i].z
    #                 temp_pose.pose.position.stamp = notification.waypoints[i].stamp
    #                 new_flight_plan.poses.append(temp_pose)
    #             if merge2end:
    #                 flighplansection = 3
    #             else:
    #                 i = len(flightplan.waypoints)

    #         elif flighplansection = 3: #Do nothing until matching the solution with the flight plan
    #             if (flightplan.waypoints[i].x == notification.waypoints[-1].x and
    #             flightplan.waypoints[i].y == notification.waypoints[-1].y and
    #             flightplan.waypoints[i].z == notification.waypoints[-1].z):
    #                 flighplansection = 4
    #             break

    #         elif flighplansection = 4: #Introduce the rest of the flight plan
    #             temp_pose.pose.position.x = flightplan.waypoints[i].x
    #             temp_pose.pose.position.y = flightplan.waypoints[i].y
    #             temp_pose.pose.position.z = flightplan.waypoints[i].z
    #             temp_pose.header.stamp = flightplan.waypoints[i].stamp
    #             new_flight_plan.poses.append(temp_pose)    
    #             break
    #     return new_flight_plan

    def send_notifications(self,notifications):
        req = NotificationsRequest()
        req.notifications = self._notifications_list
        req.operations = self._conflictive_operations
        res = self._notifications_service_handle(req)
        return res
    
    def send_threat2deconfliction(self,threat2deconflicted): 
        req = DeconflictionRequest()
        req.tactical = True
        req.threat = threat2deconflicted 
        req.operations = self._conflictive_operations
        req.geofences = self._conflictive_geofences
        self._deconfliction_response = self._requestDeconfliction_service_handle(req) 
        return self._deconfliction_response
   
    def select_optimal_route(self):
        'Select the optimal deconfliction route '
        deconfliction_plans_list = self._deconfliction_res.deconfliction_plans
        values = []
        for deconfliction_plan in deconfliction_plans_list:
            alfa = 0.25 # Weight of cost
            beta = 0.75 # Weight of riskiness
            value = alfa*deconfliction_plan.cost + beta*deconfliction_plan.riskiness
            values.append(value)
         
        value_min = min(values)
        pos_min = values.index(min(values))
        best_solution = deconfliction_plans_list[pos_min]
        return best_solution

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
        notification.threat = threat
        
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
                #AQUI HABRIA QUE LLAMAR A LA FUNCION MERGE?
                notification.waypoints = best_solution.waypoint_list
                self._notifications_list.append(notification) 

            '''Threat LOSS OF SEPARATION: we ask to tactical possible solution trajectories'''

            if threat_type == Threat.LOSS_OF_SEPARATION:
                self.send_threat2deconfliction(threat)
                for uav in uavs_threatened:
                    if uav == self._deconfliction_response.deconfliction_plans[0].uav_id:
                        best_solution = self.select_optimal_route()
                notification.uav_id = best_solution.uav_id
                notification.action = best_solution.maneuver_type
                notification.description = actions_dictionary[notification.action]
                #AQUI HABRIA QUE LLAMAR A LA FUNCION MERGE?
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
                req = WriteGeofencesRequest()
                req.geofence_ids = [geofence.id]
                req.geofences = [geofence]
                res = self._writeGeofences_service_handle(req)
                res.message = "Geofence stored in the Data Base."   

            '''Threat GEOFENCE INTRUSION: we ask to tactical possible solution trajectories'''

            if threat_type == Threat.GEOFENCE_INTRUSION:   
                #Publish the action which the UAV has to make.
                self.send_threat2deconfliction(threat)
                best_solution = self.select_optimal_route()
                notification.uav_id = best_solution.uav_id
                notification.action = best_solution.maneuver_type
                notification.description = actions_dictionary[notification.action]
                #AQUI HABRIA QUE LLAMAR A LA FUNCION MERGE?
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
                #AQUI HABRIA QUE LLAMAR A LA FUNCION MERGE?
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
                req = WriteGeofencesRequest()
                req.geofence_ids = [geofence.id]
                req.geofences = [geofence]
                res = self._writeGeofences_service_handle(req)
                res.message = "Geofence stored in the Data Base."

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
                #AQUI HABRIA QUE LLAMAR A LA FUNCION MERGE?
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
                req = WriteGeofencesRequest()
                req.geofence_ids = [geofence.id]
                req.geofences = [geofence]
                res = self._writeGeofences_service_handle(req)
                res.message = "Geofence stored in the Data Base."       

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
                req = WriteGeofencesRequest()
                req.geofence_ids = [geofence.id]
                req.geofences = [geofence]
                res = self._writeGeofences_service_handle(req)
                res.message = "Geofence stored in the Data Base."   

            '''Threat GNSS DEGRADATION: we wait a period of time and then we ask to tactical
                possible trajectories to landing spots'''

            if threat_type == Threat.GNSS_DEGRADATION: 
                #Publish the action which the UAV has to make.
                self.send_threat2deconfliction(threat)
                best_solution = self.select_optimal_route()
                notification.uav_id = best_solution.uav_id
                notification.action = best_solution.maneuver_type
                notification.description = actions_dictionary[notification.action]
                #AQUI HABRIA QUE LLAMAR A LA FUNCION MERGE?
                notification.waypoints = best_solution.waypoint_list
                self._notifications_list.append(notification) 

    def service_threats_cb(self, request):
        req = ThreatsRequest()
        req = copy.deepcopy(request)
        print(req)
        num = len(req.threats) 
        rospy.loginfo("EM has received %d threats!", num) 
        zero_time = rospy.Time()
        for i in range(num):
            threat = EmergencyManagement.Threat2Solve(rospy.Time.now(), 'TODO', req.threats[i])
            self._threats_list.append(threat)        
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
                self._threats_list[i].status = answers[i] 
                if answers[i] == 'REJECTED':
                    self._threats_list[i].status = 'TODO'
                    break 
                # if answers[i] == 'ACCEPTED':
                #     del self._dictionary_all_threats[threat_ids[i]]
                #     index2delete = 0
                #     for threat in self._threats2solve_list:
                #         key = threat.threat_id
                #         if key == threat_ids[i]:
                #             break
                #         else:
                #             index2delete = index2delete + 1 
                #     if index2delete < len(self._threats2solve_list):
                #         self._threats2solve_list.pop(index2delete)
                #     if index2delete < len(self._notifications_list):
                #         self._notifications_list.pop(index2delete)
        #print(self._threats_list)
        #print(self._dictionary_all_threats)
        res = PilotAnswerResponse()
        res.success = True
        return res

    def timer_cb(self, timer):
        num = len(self._threats_list)
        rospy.loginfo("Right now, there are %d active threats in the U-space", num)
        if num > 0:
            for threat2solve in self._threats_list:           
                if threat2solve.status == 'TODO':
                    self.action_decision_maker(threat2solve.threat_msg)
                    threat2solve.status = 'DONE'
            self.send_notifications(self._notifications_list)
            
        rospy.loginfo("The number of Threats active in the U-space is %d", num)
        print(self._notifications_list)

''' The node and the EmergencyManagement class are initialized'''

if __name__=='__main__':

    rospy.init_node('emergency_management')
    e = EmergencyManagement()
    rospy.spin()   




    
