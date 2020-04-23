#include <ros/ros.h>
#include <gauss_msgs/Deconfliction.h>
#include <gauss_msgs/Threat.h>
#include <gauss_msgs/Waypoint.h>
#include <gauss_msgs/CheckConflicts.h>
#include <gauss_msgs/ReadTraj.h>
#include <gauss_msgs/ReadFlightPlan.h>
#include <gauss_msgs/ReadGeofences.h>
#include <tactical_deconfliction/path_finder.h>
#include <Eigen/Eigen>

// Class definition
class ConflictSolver
{
public:
    ConflictSolver();

private:
    // Topic Callbacks

    // Service Callbacks
    bool deconflictCB(gauss_msgs::Deconfliction::Request &req, gauss_msgs::Deconfliction::Response &res);

    // Auxilary methods
    geometry_msgs::Point findInitAStarPoint(geometry_msgs::Polygon &_polygon, nav_msgs::Path &_path, int &_init_astar_pos);
    geometry_msgs::Point findGoalAStarPoint(geometry_msgs::Polygon &_polygon, nav_msgs::Path &_path, int &_goal_astar_pos);
    int pnpoly(int nvert, std::vector<float> &vertx, std::vector<float> &verty, float testx, float testy);
    std::vector<double> findGridBorders(geometry_msgs::Polygon &_polygon, nav_msgs::Path &_path, geometry_msgs::Point _init_point, geometry_msgs::Point _goal_point);
    geometry_msgs::Polygon circleToPolygon(float _x, float _y, float _radius, float _nVertices = 8);
    std::pair<std::vector<double>, double> getCoordinatesAndDistance(double _x0, double _y0, double _x1, double _y1, double _x2, double _y2);
    // Auxilary variables
    double rate;
    double dX,dY,dZ,dT;
    ros::NodeHandle nh_;

    // Subscribers

    // Publisher

    // Timer

    // Server
    ros::ServiceServer deconflict_server_;

    // Clients
    ros::ServiceClient check_client_;
    ros::ServiceClient read_trajectory_client_;
    ros::ServiceClient read_flightplan_client_;
    ros::ServiceClient read_geofence_client_;

};

// TacticalDeconfliction Constructor
ConflictSolver::ConflictSolver()
{
    // Read parameters
    nh_.param("/gauss/deltaX",dX,10.0);
    nh_.param("/gauss/deltaY",dY,10.0);
    nh_.param("/gauss/deltaZ",dZ,10.0);
    nh_.param("/gauss/monitoring_rate",rate,0.5);


    // Initialization
    dT=1.0/rate;

    // Publish

    // Subscribe

    // Server
    deconflict_server_=nh_.advertiseService("/gauss/tactical_deconfliction",&ConflictSolver::deconflictCB,this);

    // Cient
    check_client_ = nh_.serviceClient<gauss_msgs::CheckConflicts>("/gauss/check_conflicts");
    read_trajectory_client_ = nh_.serviceClient<gauss_msgs::ReadTraj>("/gauss/read_estimated_trajectory");
    read_flightplan_client_ = nh_.serviceClient<gauss_msgs::ReadFlightPlan>("/gauss/read_flight_plan");
    read_geofence_client_ = nh_.serviceClient<gauss_msgs::ReadGeofences>("/gauss/read_geofences");

    ROS_INFO("Started ConflictSolver node!");
}

int ConflictSolver::pnpoly(int nvert, std::vector<float> &vertx, std::vector<float> &verty, float testx, float testy) {
    int i, j, c = 0;
    for (i = 0, j = nvert - 1; i < nvert; j = i++) {
        if (((verty.at(i) > testy) != (verty.at(j) > testy)) &&
            (testx < (vertx.at(j) - vertx.at(i)) * (testy - verty.at(i)) / (verty.at(j) - verty.at(i)) + vertx.at(i)))
            c = !c;
    }
    return c;
}

geometry_msgs::Point ConflictSolver::findInitAStarPoint(geometry_msgs::Polygon &_polygon, nav_msgs::Path &_path, int &_init_astar_pos) {
    geometry_msgs::Point out_point;
    std::vector<float> vert_x, vert_y;
    for (int i = 0; i < _polygon.points.size(); i++) {
        vert_x.push_back(_polygon.points.at(i).x);
        vert_y.push_back(_polygon.points.at(i).y);
    }
    vert_x.push_back(_polygon.points.front().x);
    vert_y.push_back(_polygon.points.front().y);
    for (int i = 0; i < _path.poses.size(); i++) {
        if (pnpoly(vert_x.size(), vert_x, vert_y, _path.poses.at(i).pose.position.x, _path.poses.at(i).pose.position.y)) {
            out_point.x = _path.poses.at(i - 1).pose.position.x;
            out_point.y = _path.poses.at(i - 1).pose.position.y;
            out_point.z = _path.poses.at(i - 1).pose.position.z;
            _init_astar_pos = i - 1;
            break;
        }
    }
    return out_point;
}

geometry_msgs::Point ConflictSolver::findGoalAStarPoint(geometry_msgs::Polygon &_polygon, nav_msgs::Path &_path, int &_goal_astar_pos) {
    bool flag1 = false;
    bool flag2 = false;
    geometry_msgs::Point out_point;
    std::vector<float> vert_x, vert_y;
    for (int i = 0; i < _polygon.points.size(); i++) {
        vert_x.push_back(_polygon.points.at(i).x);
        vert_y.push_back(_polygon.points.at(i).y);
    }
    vert_x.push_back(_polygon.points.front().x);
    vert_y.push_back(_polygon.points.front().y);
    for (int i = 0; i < _path.poses.size(); i++) {
        bool in_obstacle = pnpoly(vert_x.size(), vert_x, vert_y, _path.poses.at(i).pose.position.x, _path.poses.at(i).pose.position.y);
        if (in_obstacle && !flag1 && !flag2) flag1 = true;
        if (!in_obstacle && flag1 && !flag2) flag2 = true;
        if (!in_obstacle && flag1 && flag2) {
            out_point.x = _path.poses.at(i).pose.position.x;
            out_point.y = _path.poses.at(i).pose.position.y;
            out_point.z = _path.poses.at(i).pose.position.z;
            _goal_astar_pos = i;
            break;
        }
    }

    if (out_point.x == 0.0 || out_point.y == 0.0) {
        out_point.x = _path.poses.back().pose.position.x;
        out_point.y = _path.poses.back().pose.position.y;
        out_point.z = _path.poses.back().pose.position.z;
    }

    return out_point;
}

std::vector<double> ConflictSolver::findGridBorders(geometry_msgs::Polygon &_polygon, nav_msgs::Path &_path, geometry_msgs::Point _init_point, geometry_msgs::Point _goal_point) {
    geometry_msgs::Point obs_min, obs_max, out_point;
    std::vector<float> vert_x, vert_y;
    for (int i = 0; i < _polygon.points.size(); i++) {
        vert_x.push_back(_polygon.points.at(i).x);
        vert_y.push_back(_polygon.points.at(i).y);
    }
    vert_x.push_back(_polygon.points.front().x);
    vert_y.push_back(_polygon.points.front().y);
    obs_min.x = *std::min_element(vert_x.begin(), vert_x.end());
    obs_min.y = *std::min_element(vert_y.begin(), vert_y.end());
    obs_max.x = *std::max_element(vert_x.begin(), vert_x.end());
    obs_max.y = *std::max_element(vert_y.begin(), vert_y.end());

    std::vector<double> out_grid_borders, temp_x, temp_y;
    temp_x.push_back(_init_point.x);
    temp_x.push_back(_goal_point.x);
    temp_y.push_back(_init_point.y);
    temp_y.push_back(_goal_point.y);
    double min_x = *std::min_element(temp_x.begin(), temp_x.end());
    double min_y = *std::min_element(temp_y.begin(), temp_y.end());
    double max_x = *std::max_element(temp_x.begin(), temp_x.end());
    double max_y = *std::max_element(temp_y.begin(), temp_y.end());

    while (min_x >= obs_min.x || min_y >= obs_min.y || max_x <= obs_max.x || max_y <= obs_max.y) {
        if (min_x >= obs_min.x) min_x = min_x - 1.0;
        if (min_y >= obs_min.y) min_y = min_y - 1.0;
        if (max_x <= obs_max.x) max_x = max_x + 1.0;
        if (max_y <= obs_max.y) max_y = max_y + 1.0;
    }

    out_grid_borders.push_back(min_x);
    out_grid_borders.push_back(min_y);
    out_grid_borders.push_back(max_x);
    out_grid_borders.push_back(max_y);

    return out_grid_borders;
}

geometry_msgs::Polygon ConflictSolver::circleToPolygon(float _x, float _y, float _radius, float _nVertices){
    geometry_msgs::Polygon out_polygon;
    Eigen::Vector2d centerToVertex(_radius, 0.0), centerToVertexTemp;
    for (int i = 0; i < _nVertices; i++) {
        double theta = i * 2 * M_PI / (_nVertices - 1);
        Eigen::Rotation2D<double> rot2d(theta);
        centerToVertexTemp = rot2d.toRotationMatrix() * centerToVertex;
        geometry_msgs::Point32 temp_point;
        temp_point.x = _x + centerToVertexTemp[0];
        temp_point.y = _y + centerToVertexTemp[1];
        out_polygon.points.push_back(temp_point);
    }

    return out_polygon;
}

template<typename KeyType, typename ValueType> 
std::pair<KeyType,ValueType> get_min( const std::map<KeyType,ValueType>& x ) {
  using pairtype=std::pair<KeyType,ValueType>; 
  return *std::min_element(x.begin(), x.end(), [] (const pairtype & p1, const pairtype & p2) {
        return p1.second < p2.second;
  }); 
}

std::pair<std::vector<double>, double> ConflictSolver::getCoordinatesAndDistance(double _x0, double _y0, double _x1, double _y1, double _x2, double _y2){
    std::vector<double> coordinates;
    double distance = 1000000;
    std::vector<double> point_xs, point_ys;
    point_xs.push_back(_x1);
    point_xs.push_back(_x2);
    point_ys.push_back(_y1);
    point_ys.push_back(_y2);
    // Get abc -> ax + by + c = 0 
    double a = _y2 - _y1;
    double b = _x1 - _x2;
    double c = - (a*_x1 + b*_y1);
    // get XY outpoint
    coordinates.push_back((b*(b*_x0-a*_y0) - a*c) / (a*a + b*b)); 
    coordinates.push_back((a*(a*_y0-b*_x0) - b*c) / (a*a + b*b)); 
    // check if xy is between p1 and p2
    double max_x = *std::max_element(point_xs.begin(), point_xs.end());
    double min_x = *std::min_element(point_xs.begin(), point_xs.end());
    double max_y = *std::max_element(point_ys.begin(), point_ys.end());
    double min_y = *std::min_element(point_ys.begin(), point_ys.end());
    if (max_x >= coordinates.front() && coordinates.front() >= min_x && max_y >= coordinates.back() && coordinates.back() >= min_y){
        // get distance
        distance = (double)(abs((_y2-_y1)*_x0 - (_x2-_x1)*_y0 + _x2*_y1 - _y2*_x1) / 
                   sqrt(pow(_y2-_y1, 2) + pow(_x2-_x1, 2)));   
    }
    // std::cout << max_x << ">" << coordinates.front() << ">" << min_x << " | " << max_y << ">" << coordinates.back() << ">" << min_y << " | d = " << distance << std::endl;
    return std::make_pair(coordinates, distance);
} 

// deconflictCB callback
bool ConflictSolver::deconflictCB(gauss_msgs::Deconfliction::Request &req, gauss_msgs::Deconfliction::Response &res)
{

    //Deconfliction
    if (req.tactical)
    {
        gauss_msgs::Threat conflict;
        if (req.threat.threat_id==req.threat.LOSS_OF_SEPARATION)
        {
            gauss_msgs::Waypoint newwp1,newwp2;
            conflict=req.threat;


            int num_conflicts=1;
            while (num_conflicts>0)
            {
                bool included1=false;
                bool included2=false;
                for (int i=0;i<res.uav_ids.size();i++)
                {
                    if (conflict.uav_ids.at(0)==res.uav_ids.at(i))
                        included1=true;
                    if (conflict.uav_ids.at(1)==res.uav_ids.at(i))
                        included2=true;
                }
                if (included1=false)
                    res.uav_ids.push_back(conflict.uav_ids.at(0));
                if (included2=false)
                    res.uav_ids.push_back(conflict.uav_ids.at(1));

                num_conflicts=0;
                gauss_msgs::ReadTraj traj_msg;
                traj_msg.request.uav_ids.push_back(conflict.uav_ids.at(0));
                traj_msg.request.uav_ids.push_back(conflict.uav_ids.at(1));
                if (!read_trajectory_client_.call(traj_msg) || !traj_msg.response.success)
                {
                    ROS_ERROR("Failed to read a trajectory");
                    res.success=false;
                    return false;
                }
                int j=0;
                gauss_msgs::Waypoint wp1,wp2;
                gauss_msgs::WaypointList traj1=traj_msg.response.tracks.at(0);
                gauss_msgs::WaypointList traj2=traj_msg.response.tracks.at(1);
                int UAV1=req.threat.uav_ids.at(0);
                int UAV2=req.threat.uav_ids.at(1);

                while (abs(traj1.waypoints.at(j).stamp.toSec()-conflict.times.at(0).toSec())>dT);
                wp1=traj1.waypoints.at(j);
                j=0;
                while (abs(traj2.waypoints.at(j).stamp.toSec()-conflict.times.at(1).toSec())>dT);
                wp2=traj2.waypoints.at(j);

                double distance=sqrt(pow(wp2.x-wp1.x,2)+pow(wp2.y-wp1.y,2)+pow(wp2.z-wp1.z,2));
                double separation=0;
                double mod1=sqrt(pow(wp1.x,2)+pow(wp1.y,2)+pow(wp1.z,2));
                double mod2=sqrt(pow(wp2.x,2)+pow(wp2.y,2)+pow(wp2.z,2));
                if (distance<dX)
                    separation=(dX-distance)/2;
                newwp1.x=wp1.x+separation*(wp1.x-wp2.x)/distance;
                newwp1.y=wp1.y+separation*(wp1.y-wp2.y)/distance;
                newwp1.z=wp1.z+separation*(wp1.z-wp2.z)/distance;
                newwp1.stamp=wp1.stamp;
                newwp2.x=wp2.x-separation*(wp1.x-wp2.x)/distance;
                newwp2.y=wp2.y-separation*(wp1.y-wp2.y)/distance;
                newwp2.z=wp2.z-separation*(wp1.z-wp2.z)/distance;
                newwp2.stamp=wp2.stamp;

                gauss_msgs::CheckConflicts check_msg;
                check_msg.request.deconflicted_wp.push_back(newwp1);
                check_msg.request.deconflicted_wp.push_back(newwp2);
                check_msg.request.threat.threat_id=check_msg.request.threat.LOSS_OF_SEPARATION;
                check_msg.request.threat.uav_ids.push_back(UAV1);
                check_msg.request.threat.uav_ids.push_back(UAV2);
                check_msg.request.threat.times.push_back(newwp1.stamp);
                check_msg.request.threat.times.push_back(newwp2.stamp);
                if (!check_client_.call(check_msg) || !check_msg.response.success)
                {
                    ROS_ERROR("Failed checking new conflicts");
                    res.success=false;
                    return false;
                }

                num_conflicts=check_msg.response.threats.size();

                if (num_conflicts>0)
                    conflict=check_msg.response.threats.at(0);
            }
            // Leer flight plans, modificarlo (tiempo y posicion) segun los newwp1 y newwp2
            // incluir nuevos flight plans en

            gauss_msgs::ReadFlightPlan plan_msg;
            for (int i=0;i<res.uav_ids.size();i++)
                plan_msg.request.uav_ids.push_back(res.uav_ids.at(i));
            if (!read_flightplan_client_.call(plan_msg) || !plan_msg.response.success)
            {
                ROS_ERROR("Failed to read a flight plan");
                res.success=false;
                return false;
            }

            res.deconflicted_plans.at(0);
            res.deconflicted_plans.at(1);

            res.success=true;

        }
        else if (req.threat.threat_id==req.threat.GEOFENCE_CONFLICT)
        {
            gauss_msgs::ReadFlightPlan plan_msg;
            plan_msg.request.uav_ids.push_back(req.threat.uav_ids.front());
            if (!read_flightplan_client_.call(plan_msg) || !plan_msg.response.success)
            {
                ROS_ERROR("Failed to read a flight plan");
                res.success=false;
                return false;
            }
            nav_msgs::Path res_path;
            std::vector<double> res_times;
            for (int i = 0; i < plan_msg.response.plans.front().waypoints.size(); i++){
                geometry_msgs::PoseStamped temp_pose;
                temp_pose.pose.position.x = plan_msg.response.plans.front().waypoints.at(i).x;
                temp_pose.pose.position.y = plan_msg.response.plans.front().waypoints.at(i).y;
                temp_pose.pose.position.z = plan_msg.response.plans.front().waypoints.at(i).z;
                res_path.poses.push_back(temp_pose);
                res_times.push_back(plan_msg.response.plans.front().waypoints.at(i).stamp.toSec());
            }
            gauss_msgs::ReadGeofences geofence_msg;
            geofence_msg.request.geofences_ids.push_back(req.threat.geofence_ids.front());
            if (!read_geofence_client_.call(geofence_msg) || !geofence_msg.response.success)
            {
                ROS_ERROR("Failed to read a geofence");
                res.success=false;
                return false;
            }
            geometry_msgs::Polygon res_polygon;
            if (geofence_msg.response.geofences.front().cylinder_shape){
                res_polygon = circleToPolygon(geofence_msg.response.geofences.front().circle.x_center, 
                                              geofence_msg.response.geofences.front().circle.y_center,
                                              geofence_msg.response.geofences.front().circle.radius);
            } else {
                for (int i = 0; i < geofence_msg.response.geofences.front().polygon.x.size(); i++){
                    geometry_msgs::Point32 temp_points;
                    temp_points.x = geofence_msg.response.geofences.front().polygon.x.at(i);
                    temp_points.y = geofence_msg.response.geofences.front().polygon.y.at(i);
                    res_polygon.points.push_back(temp_points);
                }
            }
            geometry_msgs::Point init_astar_point, goal_astar_point, min_grid_point, max_grid_point;
            int init_astar_pos, goal_astar_pos;
            init_astar_point = findInitAStarPoint(res_polygon, res_path, init_astar_pos);
            goal_astar_point = findGoalAStarPoint(res_polygon, res_path, goal_astar_pos);
            std::vector<double> grid_borders = findGridBorders(res_polygon, res_path, init_astar_point, goal_astar_point);
            min_grid_point.x = grid_borders[0];
            min_grid_point.y = grid_borders[1];
            max_grid_point.x = grid_borders[2];
            max_grid_point.y = grid_borders[3];
            PathFinder path_finder(res_path, init_astar_point, goal_astar_point, res_polygon, min_grid_point, max_grid_point);
            nav_msgs::Path a_star_path_res = path_finder.findNewPath();
            static upat_follower::Generator generator(1.0, 1.0, 1.0);
            std::vector<double> interp_times, a_star_times_res;
            interp_times.push_back(res_times.at(init_astar_pos));
            interp_times.push_back(res_times.at(goal_astar_pos));
            a_star_times_res = generator.interpWaypointList(interp_times, a_star_path_res.poses.size()-1);
            a_star_times_res.push_back(res_times.at(goal_astar_pos));
            // Solutions of conflict solver are a_star_path_res and a_star_times_res
            gauss_msgs::Waypoint temp_wp;
            gauss_msgs::WaypointList temp_wp_list;
            for (int i = 0; i < a_star_path_res.poses.size(); i++){
                temp_wp.x = a_star_path_res.poses.at(i).pose.position.x;
                temp_wp.y = a_star_path_res.poses.at(i).pose.position.y;
                temp_wp.z = a_star_path_res.poses.at(i).pose.position.z;
                temp_wp.stamp = ros::Time(a_star_times_res.at(i));
                temp_wp_list.waypoints.push_back(temp_wp);
            }

            res.deconflicted_plans.push_back(temp_wp_list);
            res.success = true;
        } 
        else if (req.threat.threat_id==req.threat.GEOFENCE_INTRUSION) 
        {
            gauss_msgs::ReadFlightPlan plan_msg;
            plan_msg.request.uav_ids.push_back(req.threat.uav_ids.front());
            if (!read_flightplan_client_.call(plan_msg) || !plan_msg.response.success)
            {
                ROS_ERROR("Failed to read a flight plan");
                res.success=false;
                return false;
            }
            nav_msgs::Path res_path;
            std::vector<double> res_times;
            for (int i = 0; i < plan_msg.response.plans.front().waypoints.size(); i++){
                geometry_msgs::PoseStamped temp_pose;
                temp_pose.pose.position.x = plan_msg.response.plans.front().waypoints.at(i).x;
                temp_pose.pose.position.y = plan_msg.response.plans.front().waypoints.at(i).y;
                temp_pose.pose.position.z = plan_msg.response.plans.front().waypoints.at(i).z;
                res_path.poses.push_back(temp_pose);
                res_times.push_back(plan_msg.response.plans.front().waypoints.at(i).stamp.toSec());
            }
            gauss_msgs::ReadGeofences geofence_msg;
            geofence_msg.request.geofences_ids.push_back(req.threat.geofence_ids.front());
            if (!read_geofence_client_.call(geofence_msg) || !geofence_msg.response.success)
            {
                ROS_ERROR("Failed to read a geofence");
                res.success=false;
                return false;
            }
            geometry_msgs::Polygon res_polygon;
            if (geofence_msg.response.geofences.front().cylinder_shape){
                res_polygon = circleToPolygon(geofence_msg.response.geofences.front().circle.x_center, 
                                              geofence_msg.response.geofences.front().circle.y_center,
                                              geofence_msg.response.geofences.front().circle.radius);
            } else {
                for (int i = 0; i < geofence_msg.response.geofences.front().polygon.x.size(); i++){
                    geometry_msgs::Point32 temp_points;
                    temp_points.x = geofence_msg.response.geofences.front().polygon.x.at(i);
                    temp_points.y = geofence_msg.response.geofences.front().polygon.y.at(i);
                    res_polygon.points.push_back(temp_points);
                }
            }
            // Get min distance to polygon border
            geometry_msgs::Point32 conflict_point;
            conflict_point.x = 5.5;
            conflict_point.y = 4.0;
            conflict_point.z = 1.0;
            std::map <std::vector<double> , double> point_and_distance;
            for (auto vertex : res_polygon.points){
                std::vector<double> point;
                point.push_back(vertex.x);
                point.push_back(vertex.y);
                point_and_distance.insert(std::make_pair(point, sqrt(pow(vertex.x - conflict_point.x, 2) + 
                                                                     pow(vertex.y - conflict_point.y, 2))));
            }
            for (int i = 0; i < res_polygon.points.size() - 1; i++){
                point_and_distance.insert(getCoordinatesAndDistance(conflict_point.x, conflict_point.y, 
                                                                    res_polygon.points.at(i).x, res_polygon.points.at(i).y, 
                                                                    res_polygon.points.at(i+1).x, res_polygon.points.at(+1).y));
            }
            point_and_distance.insert(getCoordinatesAndDistance(conflict_point.x, conflict_point.y, 
                                                    res_polygon.points.front().x, res_polygon.points.front().y, 
                                                    res_polygon.points.back().x, res_polygon.points.back().y));
            // for (auto i : point_and_distance){
            //     std::cout << "x: " << i.first.front() << " y: " << i.first.back() << " d: " << i.second << std::endl;
            // }
            auto min_distance = get_min(point_and_distance);
            // std::cout << " -- " << std::endl;
            // std::cout << "x: " << min_distance.first.front() << " y: " << min_distance.first.back() << " d: " << min_distance.second << std::endl;
            Eigen::Vector2f p_conflict, p_min_distance, unit_vec, p_out_polygon;
            p_conflict = Eigen::Vector2f(conflict_point.x, conflict_point.y);
            p_min_distance = Eigen::Vector2f(min_distance.first.front(), min_distance.first.back()); 
            unit_vec = (p_min_distance - p_conflict) / (p_min_distance - p_conflict).norm();
            double safety_distance = 1.0;
            p_out_polygon = unit_vec * safety_distance;
            geometry_msgs::Point init_astar_point, goal_astar_point, min_grid_point, max_grid_point;
            init_astar_point.x = min_distance.first.front() + p_out_polygon(0);
            init_astar_point.y = min_distance.first.back() + p_out_polygon(1);
            int init_astar_pos, goal_astar_pos;
            // init_astar_point.x = min_distance.first.front();
            // init_astar_point.y = min_distance.first.back();
            goal_astar_point = findGoalAStarPoint(res_polygon, res_path, goal_astar_pos);
            std::vector<double> grid_borders = findGridBorders(res_polygon, res_path, init_astar_point, goal_astar_point);
            min_grid_point.x = grid_borders[0];
            min_grid_point.y = grid_borders[1];
            max_grid_point.x = grid_borders[2];
            max_grid_point.y = grid_borders[3];
            PathFinder path_finder(res_path, init_astar_point, goal_astar_point, res_polygon, min_grid_point, max_grid_point);
            nav_msgs::Path a_star_path_res = path_finder.findNewPath();
            static upat_follower::Generator generator(1.0, 1.0, 1.0);
            std::vector<double> interp_times, a_star_times_res;
            interp_times.push_back(0.0); // init astar pos time
            interp_times.push_back(res_times.at(goal_astar_pos));
            a_star_times_res = generator.interpWaypointList(interp_times, a_star_path_res.poses.size()-1);
            a_star_times_res.push_back(res_times.at(goal_astar_pos));
            // Solutions of conflict solver are a_star_path_res and a_star_times_res
            gauss_msgs::Waypoint temp_wp;
            gauss_msgs::WaypointList temp_wp_list;
            for (int i = 0; i < a_star_path_res.poses.size(); i++){
                temp_wp.x = a_star_path_res.poses.at(i).pose.position.x;
                temp_wp.y = a_star_path_res.poses.at(i).pose.position.y;
                temp_wp.z = a_star_path_res.poses.at(i).pose.position.z;
                temp_wp.stamp = ros::Time(a_star_times_res.at(i));
                temp_wp_list.waypoints.push_back(temp_wp);
            }

            res.deconflicted_plans.push_back(temp_wp_list);            

            
            res.success = true;
            res.message = "Conflict solved";

            // gauss_msgs::Waypoint temp_wp;
            // gauss_msgs::WaypointList temp_wp_list;
            // temp_wp.x = conflict_point.x;
            // temp_wp.y = conflict_point.y;
            // temp_wp.z = conflict_point.z;
            // temp_wp.stamp = ros::Time(0.0);
            // temp_wp_list.waypoints.push_back(temp_wp);
            // res.deconflicted_plans.push_back(temp_wp_list);
            // temp_wp.x = min_distance.first.front();
            // temp_wp.y = min_distance.first.back();
            // temp_wp.z = conflict_point.z;
            // temp_wp.stamp = ros::Time(0.0);
            // temp_wp_list.waypoints.push_back(temp_wp);
            // res.deconflicted_plans.push_back(temp_wp_list);                
        }
    }



    return true;
}



// MAIN function
int main(int argc, char *argv[])
{
    ros::init(argc,argv,"conflict_solver");

    // Create a ConflictSolver object
    ConflictSolver *conflict_solver = new ConflictSolver();

    ros::spin();
}
