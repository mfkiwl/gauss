#!/usr/bin/env python
import rospy
from gauss_msgs.srv import Threats, ThreatsRequest, ThreatsResponse
from gauss_msgs.msg import Threat

def threat_monitoring_client(uas_ids, conflict_flaged):
    rospy.wait_for_service('threats')
    try:
        client = rospy.ServiceProxy('threats', Threats)
        
        request = ThreatsRequest()
        request.uas_ids = uas_ids # This is a list.
        request.threats_flaged = conflict_flaged # This is a list of messages type Threat.  

        response = client(request)
        
    except rospy.ServiceException, e:
        print "Service call failed: %s"%e

conflict_flaged = []
conflict = Threat()
conflict.threat_id = 0
conflict.uas_ids = [1, 2]
conflict.wp_ids = [2, 3]
conflict_flaged.append (conflict)

rospy.init_node('monitoring_node', anonymous=True) # we initialize the node

threat_monitoring_client(conflict.uas_ids, conflict_flaged)
print(conflict)