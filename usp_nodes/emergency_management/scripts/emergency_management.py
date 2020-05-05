#!/usr/bin/env python
# this Python file uses the following encoding: utf-8

## This script is the emergency manager node developed to decide what is the best action 
# to take in the U-space when some Threats are showed up.

import os, sys
import rospy
import time
from math import sqrt
from gauss_msgs.srv import Threats, ThreatsResponse, ThreatsRequest
from gauss_msgs.srv import ReadOperation, ReadOperationRequest
#from gauss_msgs.srv import WriteGeofences, WriteGeofencesRequest
from gauss_msgs.msg import Threat, Notification, Waypoint, WaypointList, Operation, Geofence
#from gauss_msgs.srv import Deconfliction, DeconflictionRequest

class EmergencyManagement():

    def __init__(self): 
        
        # Initialization
        self.threats2solve = ThreatsRequest()        

        # Publish

        #self._notification_publisher = rospy.Publisher("notification", Notification, queue_size=1)
        
        # Wait until service is available and creat connection
        
        #rospy.wait_for_service('/gauss/deconfliction')                    
        #self._requestDeconfliction_service_handle = rospy.ServiceProxy('/gauss/deconfliction', Deconfliction) 

        rospy.wait_for_service('/gauss/read_operation')                    
        self._readOperation_service_handle = rospy.ServiceProxy('/gauss/read_operation', ReadOperation) 

        #rospy.wait_for_service('gauss/write_geofences')                    
        #self._writeGeofences_service_handle = rospy.ServiceProxy('gauss/write_geofences', WriteGeofences) 
               
    # Server     

        self._threats_service = rospy.Service('gauss/threats', Threats, self.service_threats_cb) 
        print("Ready to add a threat request")
    
    #TODO link Threats severity/probability with the SoA references.
        #self._threats2solve = ThreatsRequest()
    
    def assign_threat_severity(self):
        self._threats_definition = {
                                    Threat.UAS_IN_CV: {'type': 'conflict', 'severity': 1},
                      	            Threat.UAS_OUT_OV: {'type': 'conflict', 'severity': 2},
                                    Threat.LOSS_OF_SEPARATION: {'type': 'conflict', 'severity': 2},
                                    Threat.ALERT_WARNING: {'type': 'alert', 'severity': 2},
                                    Threat.GEOFENCE_INTRUSION: {'type': 'conflict', 'severity': 2},
                                    Threat.GEOFENCE_CONFLICT: {'type': 'conflict', 'severity': 1},
                                    Threat.TECHNICAL_FAILURE: {'type': 'alert', 'severity': 3},
                                    Threat.COMMUNICATION_FAILURE: {'type': 'alert', 'severity': 3},
                                    Threat.LACK_OF_BATTERY: {'type': 'conflict', 'severity': 1},
                                    Threat.JAMMING_ATTACK: {'type': 'alert', 'severity': 2},
                                    Threat.SPOOFING_ATTACK: {'type': 'alert', 'severity': 3}
                                    }
   
    def action_decision_maker(self,threats2solve):
        events = threats2solve.threats
        threat_id = events[0].threat_id
        threat_type = self._threats_definition[threat_id]['type']
        threat_severity = self._threats_definition[threat_id]['severity']
        #first_operation_priority = self._operation_info_from_db['operations'][0]['priority']
        #second_operation_priority = self._operation_info_from_db['operations'][1]['priority']
    
        if threat_severity == 3:
            # We define and send the notification.
            uav_ids = events[0].uav_ids # Esto sería la lista de uavs implicados.
            action = 'URGENT: Land as soon as possible.'  
            #notification = self.declare_notification_parameters(uav_ids, action)
            #self.send_notification(notification)
            # We define and write a geofence.
            #self.send_geofence_creation()
                    
        if threat_severity == 2:

            if threat_id == 1: #UAS_OUT_OV
                action = 'URGENT: Land as soon as possible.'  
               
            if threat_id == 2: #LOSS_OF_SEPARATION
                action = 'Send new trajectories recommendations to the UAS involved in the conflict.' 
            
            if threat_id == 3: #ALERT_WARNING
                action = 'Ask for a Geofence creation and send an alert report to all the pilots.' 
            
            if threat_id == 4: #GEOFENCE_INTRUSION
                action = 'Ask for leaving the geofence asap and continue its operation.' 
            
            if threat_id == 9: #JAMMING_ATTACK
                action = 'URGENT: Land as soon as possible.'  
            
        if threat_severity == 1:

            if threat_id == 0: #UAS_IN_CV
                action = 'Send new trajectory to get into the FG.' 
            
            if threat_id == 5: #GEOFENCE_CONFLICT
                action = 'Send new trajectory recommendation to the UAS involved in the conflict.'     
            
            if threat_id == 8: #LACK_OF_BATTERY
                action = 'Please, land in the defined landing spot.'         
        print(action)

    def service_threats_cb(self, request):
        rospy.loginfo("New threat received:") 
        response = ThreatsResponse()
        response.success = True
        self.threats2solve = request # ThreatsRequest
        self.action_decision_maker(self.threats2solve)      
        return response        

   ## Since a Threat has been received. It is request operation info of the UAV linked to
   # the Threat. 

    def read_operations_info(self):
        request = ReadOperationRequest()
        request.uav_ids = self._threats2solve.threats[0].uav_ids
        self._operation_info_from_db = self._readOperation_service_handle(request)
        response = self._readOperation_service_handle(request)
        print(response)
        return response
        # almacena la info de las dos operaciones definidas en la DataBase en esa variable global.
        # debiera ser un diccionario.

    ## This function decide what is the fittest action to take.
    #def declare_notification_parameters(self, uav_id, action):
    #    notification = Notification()
    #    notification.uav_id = uav_id
    #    notification.action = action
    #    return notification

    #def send_notification(self, message): 
    #    self._notification_publisher.publish(message)
    
    #def declare_geofence_parameters(self):
    #    geofence = Geofence()
    #    geofence.id = 3
    #    geofence.static_geofence = False 
    #    geofence.cylinder_shape = True 
    #    geofence.min_altitude = 0
    #    geofence.max_altitude = 10
    #    geofence.start_time = 0
    #    geofence.end_time = 1000
    #    geofence.circle.x_center = 0 
    #    geofence.circle.y_center = 0
    #    geofence.circle.radius = 5
    #    return geofence

    #def send_geofence_creation(self):
    #    request = WriteGeofencesRequest()
    #    request.geofence_ids = self.declare_geofence_parameters.geofence.id #pinta raro.
    #    request.geofences[0] = self.declare_geofence_parameters()
    #    return request
    
    
    #def declare_new_trajectory_parameters (self):
    #    pass

    #def request_new_trajectory(self):
    #    request = DeconflictionRequest()
    #    #TODO, rellenar la info necesaria para que me envien una nueva trayectoria.
    #    pass
    
    #def write_new_flight_plan(self):
    #    request = WriteFlightPlanRequest()
    #    #TODO, rellenar la info necesaria para poder escribir un nuevo flight plan.
    #    pass

    #def activate_fts(self, fts_signal): # Flight Termination System
    #    self._notification_publisher.publish(fts_signal)

    #TODO, definir los parametros para usar esta función.
    
    #def calculate_best_landingspot(self):
    #    pass

''' The node and the EmergencyManagement class are initialized'''

if __name__=='__main__':

    rospy.init_node('emergency_management')
    e = EmergencyManagement()

    while not rospy.is_shutdown():
        
        e.assign_threat_severity()
        e.read_operations_info()
                    
        time.sleep(0.1)

