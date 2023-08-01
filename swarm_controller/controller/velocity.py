import airsim
import numpy as np
from configuration import Configuration
from scipy.spatial import Voronoi

class VelocityComputation():
    def __init__(self):
        # Build a connection with AirSim
        self.client = airsim.MultirotorClient()
        self.client.confirmConnection()
        self.config = Configuration()
        
        # Define the origin position of the swarm
        self.origin = self.config.origin
        self.origin_x = self.config.origin_x
        self.origin_y = self.config.origin_y
        self.num_uavs = self.config.num_uavs
      
    def set_parameters(self, v_max=0, r_max=20, k_sep=0, k_coh=0, k_mig=1, k_rep=0, r_repulsion=0, d_desired=0):
        self.v_max = v_max
        self.r_max = r_max
        self.k_sep = k_sep
        self.k_coh = k_coh
        self.k_mig = k_mig
        self.r_repulsion = r_repulsion
        self.d_desired = d_desired
        self.k_rep = k_rep
        self.adjust = 0
        
        self.v_cmd = np.zeros([2, self.num_uavs])
        self.v_rep = np.zeros([2, 1])
        self.v_coh = np.zeros([2, 1])
        self.v_sep = np.zeros([2, 1])
        self.z_cmd = self.get_avg_altitude()
        self.pos_mig = np.array([[0], [0]])
        
    def get_UAV_pos(self, vehicle_name="SimpleFlight"):
        state = self.client.simGetGroundTruthKinematics(vehicle_name=vehicle_name)
        x = state.position.x_val
        y = state.position.y_val
        i = int(vehicle_name[3])
        x += self.origin_x[i - 1]
        y += self.origin_y[i - 1]
        pos = np.array([[x], [y]]) # Return a 2D array
        return pos

    def get_avg_altitude(self):
        # get current z position of all UAVs
        swarm_altitude = [
            self.client.getMultirotorState(vehicle_name="UAV" + str(i + 1))
            .kinematics_estimated.position.z_val for i in range(self.num_uavs)
        ]
        z_cmd = np.mean(swarm_altitude)
        
        return z_cmd   
    
    def get_swarm_center(self):
        # get center position of all UAVs
        temp_pos = []
        for i in range(self.num_uavs):
            name_i = "UAV"+str(i+1)
            temp_pos.append(self.get_UAV_pos(vehicle_name=name_i))
            
        return np.mean(temp_pos, axis=0)
    
    def compute_separation_force(self, pos_i, pos_j):
        r_ij = pos_j - pos_i
        distance = np.linalg.norm(r_ij)
        if distance != 0:
            return -self.k_sep * r_ij / distance
        else:
            return np.zeros(2)
    
    def compute_cohesion_force(self, pos_i, pos_j):
        r_ij = pos_j - pos_i
        return self.k_coh * r_ij
        
    # def compute_repulsion_force(self, pos_i, pos_j, repulsion_distance, safe_distance_uav, K_rep):
    #     r_ij = pos_j - pos_i
    #     distance = np.linalg.norm(r_ij)

    #     if distance < repulsion_distance:
    #         repulsion_vector = -K_rep * r_ij / distance
    #         if distance < safe_distance_uav:
    #             repulsion_vector *= 2
    #     else:
    #         repulsion_vector = np.zeros([2, 1])  # No repulsion force if distance >= repulsion_distance

    #     return repulsion_vector
    
    #### another repulsion force ####
    def compute_repulsion_force(self, pos_i, pos_j, repulsion_distance, safe_distance_uav, K_rep):
        r_ij = pos_j - pos_i
        distance = np.linalg.norm(r_ij)
        if distance < repulsion_distance:
            #repulsion_vector = -K_rep * (repulsion_distance - distance) * ((pos_j - pos_i) / distance)
            repulsion_vector = -K_rep * (repulsion_distance - distance) * (r_ij/distance)
        else:
            repulsion_vector = np.zeros([2, 1])
        return repulsion_vector
    
    def v_avoid(self):
        """
        This is used to avoid obstacles (not implemented yet), but the theory is the same as repulsion force
        """
        # obstacles =[[],[],[]]
        
        pass
    
    def v_alignmnet(self, pos_i, pos_j):
        r_ij = pos_j - pos_i
        align_vector = 0.5 * r_ij
        
        

    def compute_forces(self, pos_i, pos_j, rep_dis, safe_dis, add_rep):
        # Calculate the norm
        norm = np.linalg.norm(pos_j - pos_i)
        # Initialize forces
        v_sep = v_coh = v_rep = 0

        if norm < self.r_max:
            v_sep = self.compute_separation_force(pos_i, pos_j)
            v_coh = self.compute_cohesion_force(pos_i, pos_j)
            if add_rep:
                v_rep = self.compute_repulsion_force(pos_i, pos_j, rep_dis, safe_dis, self.k_rep)
                
        return v_sep, v_coh, v_rep
     
    def compute_velocity(self, rep_dis, safe_dis, add_rep):
        # Loop through i-th UAV
        for i in range(self.num_uavs):
            name_i = "UAV" + str(i + 1)
            pos_i = self.get_UAV_pos(vehicle_name=name_i)
             # vector from UAV to migration point
            r_mig = self.pos_mig - pos_i
            N_i = 0
            
            if np.linalg.norm(r_mig) != 0:
                v_mig = self.k_mig * r_mig / np.linalg.norm(r_mig)
            else:
                v_mig = np.zeros([2, 1])
            
            # Loop through j-th UAV
            for j in range(self.num_uavs):
                if j != i:
                    N_i += 1
                    name_j = "UAV" + str(j + 1)
                    pos_j = self.get_UAV_pos(vehicle_name=name_j)
                    
                    if np.linalg.norm(pos_j - pos_i) < self.r_max:

                        v_sep, v_coh, v_rep = self.compute_forces(pos_i, pos_j, rep_dis, safe_dis, add_rep)
                        self.v_sep += v_sep
                        self.v_coh += v_coh
                        self.v_rep += v_rep
                        
            self.v_sep /= N_i
            self.v_coh /= N_i
            self.v_rep /= N_i

            self.v_cmd[:, i:i + 1] = self.v_sep + self.v_coh + self.v_rep + v_mig
            self.v_cmd[:, i:i + 1] = np.minimum(self.v_cmd[:, i:i + 1], self.v_max)
            
            # # limit the velocity
            # if self.v_cmd[0, i] > self.v_max:
            #     self.v_cmd[0, i] = self.v_max
    
    def move_UAVs(self, z_cmd):
        for i in range(self.num_uavs):
            name_i = "UAV" + str(i + 1)
            self.client.moveByVelocityZAsync(self.v_cmd[0, i], self.v_cmd[1, i], z_cmd, 0.1, vehicle_name=name_i)

    
    ################################# Formation Generation #################################
    # define the generator function for the formation points
    def point_generator(self, type, spacing):
        group_center = np.array([[0], [0]]) #self.get_swarm_center()
        if type == 'circle':
            formation_angle_offset = 2 * np.pi / self.num_uavs
            for i in range(self.num_uavs):
                formation_angle = formation_angle_offset * i
                yield group_center + spacing * np.array([[np.cos(formation_angle)], [np.sin(formation_angle)]])
                
        elif type == 'line':
            for i in range(self.num_uavs):
                yield np.array([[i * spacing], [group_center[1, 0]]])
                     
        elif type == 'diagonal':
            for i in range(self.num_uavs):
                row = col = i  # For a diagonal, row index equals column index
                yield np.array([[group_center[0, 0] + (col * spacing)], 
                                [group_center[1, 0] + row * spacing]])
                         
        elif type == 'V':
            for i in range(self.num_uavs):
                yield group_center + np.array([[abs((i - self.num_uavs // 2)) * spacing], 
                                            [(i - self.num_uavs // 2) * spacing]])
        else:
            raise ValueError(f'Unknown formation type: {type}')

    def calculate_formation_velocity(self, rep_dis, safe_dis, formation_point_gen):
        v_sep, v_rep, v_coh, N_i = 0, 0, 0, 0
        for i, formation_point in enumerate(formation_point_gen):
            # Define the name and position of the current UAV
            name_i = "UAV" + str(i + 1)
            pos_i = self.get_UAV_pos(vehicle_name=name_i)

            # Compute the desired velocity for the current UAV
            v_mig = self.k_mig * (formation_point - pos_i)
            N_i += 1

            # Compute the repulsion vector if the other UAVs are within the repulsion distance
            for j in range(self.num_uavs):
                if j != i:
                    # Define the name and position of the other UAV
                    name_j = "UAV" + str(j + 1)
                    pos_j = self.get_UAV_pos(vehicle_name=name_j)
                    dist_ij = np.linalg.norm(pos_j - pos_i)
                    
                    if dist_ij < self.r_max:
                        # Compute the repulsion force
                        repulsion_force = self.compute_repulsion_force(pos_i, pos_j, rep_dis, safe_dis, self.k_rep)
                        # Add repulsion force to the repulsion velocit
                        v_rep += repulsion_force
                        v_sep += self.compute_separation_force(pos_i, pos_j)
                        v_coh += self.compute_cohesion_force(pos_i, pos_j)
                           

            v_rep /= N_i
            v_sep /= N_i
            v_coh /= N_i
            # Calculate the final desired velocity
            v_desired = v_mig + v_rep + v_sep + v_coh
        
            # Limit the velocity to the maximum allowed speed
            v_desired_norm = np.linalg.norm(v_desired)
            if v_desired_norm > self.v_max:
                v_desired = self.v_max * v_desired / v_desired_norm

            self.v_cmd[:, i:i + 1] = v_desired
    
    # define form functions
    def form_circle(self, rep_dis, safe_dis, spacing=15):
        formation_points = self.point_generator('circle', spacing)
        self.calculate_formation_velocity(rep_dis, safe_dis, formation_points)

    def form_line(self, rep_dis, safe_dis, spacing=12):
        formation_points = self.point_generator('line', spacing)
        self.calculate_formation_velocity(rep_dis, safe_dis, formation_points)

    def form_V(self, rep_dis, safe_dis, spacing=8):
        formation_points = self.point_generator('V', spacing)
        self.calculate_formation_velocity(rep_dis, safe_dis, formation_points)

    def form_diagonal(self, rep_dis, safe_dis, spacing=10):
        formation_points = self.point_generator('diagonal', spacing)
        self.calculate_formation_velocity(rep_dis, safe_dis, formation_points)
        
    # find the position of the UAV
    def get_all_UAV_positions(self):
        positions = np.zeros((self.num_uavs, 2))
        for i in range(self.num_uavs):
            name_i = "UAV" + str(i + 1)
            positions[i, :] = self.get_UAV_pos(vehicle_name=name_i).flatten()
        return positions
    
    # compute the density of the swarm
    def compute_density(self):
        positions = self.get_all_UAV_positions()
    
        # Subtract each row from each other row
        diff = positions[:, np.newaxis, :] - positions[np.newaxis, :, :]
        
        # Compute the Euclidean distance
        distances = np.sqrt((diff ** 2).sum(axis=-1))
        
        # Mask the diagonal (distance of each UAV to itself)
        mask = np.eye(distances.shape[0], dtype=bool)
        distances = distances[~mask]

        # Compute the average distance
        density = distances.mean()
        print(f'Density: {density}')

        return density

    #################################### TASK Velocity ####################################
    def circle_move_circle(self):
        for t in range(600):
            # Use a non-linear function for angle calculation
            angle = 2 * np.pi * t / 600  # Angle based on the current time step（we hope have a circle movement）

            #angle = 2 * np.pi * t / 600  # Angle based on the current time step（we hope have a circle movement）
            group_center_radius = 60 # Set the radius of the circle for the group center
            # Calculate the swarm center point
            group_center = group_center_radius * np.array([[np.cos(angle)], [np.sin(angle)]])
            
            for i in range(self.num_uavs):
                
                name_i = "UAV" + str(i + 1)
                pos_i = self.get_UAV_pos(vehicle_name=name_i)  # store the position of the current UAV

                # Define the formation points for each UAV within the group
                formation_radius = 15  # Distance between the UAVs in the formation
                formation_angle_offset = 2 * np.pi / 9  # Angular offset between UAVs in the formation
                formation_angle = formation_angle_offset * i  # calculates the specific angle for the current UAV based on its index
                formation_point = group_center + formation_radius * np.array(
                    [[np.cos(formation_angle)], [np.sin(formation_angle)]])

                # Calculate the desired velocity for each UAV to reach its formation point
                v_mig = self.k_mig * (formation_point - pos_i)
                # Collision avoidance
                v_rep = np.zeros([2, 1])
                N_i = 0 
               
                
                for j in range(self.num_uavs):
                    if j != i:
                        N_i += 1
                        name_j = "UAV" + str(j + 1)
                        pos_j = self.get_UAV_pos(vehicle_name=name_j)
                        if np.linalg.norm(pos_j - pos_i) < self.r_max:
                            v_sep, v_coh, v_rep = self.compute_forces(pos_i, pos_j, 7, 5, True)
                            self.v_sep += v_sep
                            self.v_coh += v_coh
                            self.v_rep += v_rep
                            
                self.v_sep /= N_i
                self.v_coh /= N_i
                self.v_rep /= N_i
                
                self.v_cmd[:, i:i + 1] = self.v_sep + self.v_coh + self.v_rep + v_mig
                if np.linalg.norm(self.v_cmd[:, i:i + 1]) > self.v_max:
                    self.v_cmd[:, i:i + 1] = self.v_max * self.v_cmd[:, i:i + 1] / np.linalg.norm(self.v_cmd[:, i:i + 1])
                
            # Set the velocity for each UAV
            for i in range(self.num_uavs):
                name_i = "UAV" + str(i + 1)
                print("test")
                self.client.moveByVelocityZAsync(self.v_cmd[0, i], self.v_cmd[1, i], self.z_cmd, 0.1, vehicle_name=name_i)

            # # Set the velocity for each UAV
            self.move_UAVs(self.z_cmd)
        
    def V_move_circle(self):
        for t in range(800):
            angle =  2 * np.pi * t / 800
            group_center_radius = 70 
            spacing = 8
            group_center = group_center_radius * np.array([[np.cos(angle)], [np.sin(angle)]])

            # Generate the formation points for the V-shape
            formation_points = []
            for i in range(self.num_uavs):
                point = np.array([[abs((i - self.num_uavs // 2)) * spacing], 
                                [(i - self.num_uavs // 2) * spacing ]])
                # Compute the rotation matrix based on the current angle
                formation_angle = angle - np.pi/2
                rotation_matrix = np.array([[np.cos(formation_angle), -np.sin(formation_angle)], 
                                             [np.sin(formation_angle), np.cos(formation_angle)]])
                # # Rotate the point and add the group center
                rotated_point = np.dot(rotation_matrix, point) + group_center
                formation_points.append(rotated_point)
  

            for i, formation_point in enumerate(formation_points):
                N_i = 0
                name_i = "UAV" + str(i + 1)
                pos_i = self.get_UAV_pos(vehicle_name=name_i)
                v_mig = self.k_mig * (formation_point - pos_i)
                
                # Perform collision avoidance with other drones
                for j in range(self.num_uavs):
                    if j != i:
                        N_i += 1
                        name_j = "UAV" + str(j + 1)
                        pos_j = self.get_UAV_pos(vehicle_name=name_j)

                        if np.linalg.norm(pos_j - pos_i) < self.r_max:
                            v_sep, v_coh, v_rep = self.compute_forces(pos_i, pos_j, 8, 3, True)
                            self.v_sep += v_sep
                            self.v_coh += v_coh
                            self.v_rep += v_rep * 2
                   
                self.v_sep /= N_i
                self.v_coh /= N_i
                self.v_rep /= N_i
        
                self.v_cmd[:, i:i + 1] = self.v_sep + self.v_coh + self.v_rep + v_mig
                # if np.linalg.norm(self.v_cmd[:, i:i + 1]) > self.v_max:
                #     self.v_cmd[:, i:i + 1] = self.v_max * self.v_cmd[:, i:i + 1] / np.linalg.norm(self.v_cmd[:, i:i + 1])
            
            # Set the velocity for each UAV
            for i in range(self.num_uavs):
                name_i = "UAV" + str(i + 1)
                self.client.moveByVelocityZAsync(self.v_cmd[0, i], self.v_cmd[1, i], self.z_cmd, 0.1, vehicle_name=name_i)
    

    # space occupation          
    def space_ccupation(self):
          for t in range(600):
            target_point = np.zeros([2, 1])
            x = target_point[0][0]  # x coordinate
            y = target_point[1][0]  # y coordinate
            y_max = y -70
            y_min = y + 70
            x_max = x - 70
            x_min = x + 70
            
            n_drones = self.num_uavs
            # Randomly generating drone positions within the specified area
            np.random.seed(0)  # for consistency
            drone_positions = np.random.rand(n_drones, 2) * [x_max - x_min, y_max - y_min] + [x_min, y_min]
            vor = Voronoi(drone_positions)
            
            
            for i in range(self.num_uavs):
                name_i = "UAV" + str(i + 1)
                pos_i = self.get_UAV_pos(vehicle_name=name_i) # (2, 1)
                pos_i = np.squeeze(pos_i)                 
                # # vector from UAV to migration point
                r_mig = drone_positions[i] - pos_i
                r_mig = np.expand_dims(r_mig, axis=1)
                # # Calculate the desired velocity for each UAV to reach its formation point
                
                v_mig = self.k_mig * r_mig / np.linalg.norm(r_mig)                
                N_i = 0
                
                # Get the region corresponding to the current drone
                region = vor.point_region[i]
                if not -1 in vor.regions[region]:
                    polygon = [vor.vertices[j] for j in vor.regions[region]]
                    # Compute centroid of the Voronoi cell
                    centroid = np.mean(polygon, axis=0)

                    # Movement code here - move towards centroid
                    name_i = "UAV" + str(i + 1)
                    pos_i = self.get_UAV_pos(vehicle_name=name_i) # (2, 1)
                    pos_i = np.squeeze(pos_i)                 
                    # vector from UAV to centroid
                    r_mig = centroid - pos_i
                    r_mig = np.expand_dims(r_mig, axis=1)
                    # Calculate the desired velocity for each UAV to reach its formation point
                    v_mig = self.k_mig * r_mig / np.linalg.norm(r_mig)                
                
                for j in range(self.num_uavs):
                    if j != i:
                        N_i += 1
                        name_j = "UAV" + str(j + 1)
                        pos_j = self.get_UAV_pos(vehicle_name=name_j)
                        
                        if np.linalg.norm(pos_j - pos_i) < self.r_max:
                            v_sep, v_coh, v_rep = self.compute_forces(pos_i, pos_j, 10, 5, True)
                            
                            self.v_sep += np.mean(v_sep, axis=1, keepdims=True) 
                            self.v_coh += np.mean(v_coh, axis=1, keepdims=True) 
                            self.v_rep += 2 * np.mean(v_rep, axis=1, keepdims=True)
                
                self.v_sep /= N_i
                self.v_coh /= N_i
                self.v_rep /= N_i
        
                self.v_cmd[:, i:i + 1] = self.v_sep + self.v_coh + self.v_rep + v_mig
                if np.linalg.norm(self.v_cmd[:, i:i + 1]) > self.v_max:
                    self.v_cmd[:, i:i + 1] = self.v_max * self.v_cmd[:, i:i + 1] / np.linalg.norm(self.v_cmd[:, i:i + 1])
             
                

            # Set the velocity for each UAV
            for i in range(self.num_uavs):
                name_i = "UAV" + str(i + 1)
                self.client.moveByVelocityZAsync(self.v_cmd[0, i], self.v_cmd[1, i], self.z_cmd, 0.1, vehicle_name=name_i)

        # line search
    def line_search(self, spacing=12):
        target = np.array([[-300], [-300]])
        
        # Calculate the initial formation points
        group_center = self.get_swarm_center()
        initial_formation_points = [group_center + np.array([[i * spacing], [0]]) for i in range(self.num_uavs)]

        for t in range(600):
            group_center = self.get_swarm_center()
            v_center_to_target = target - group_center

            for i, initial_formation_point in enumerate(initial_formation_points):
                # Calculate the target point for the UAV by adding the group movement to the initial formation point
                formation_point = initial_formation_point + v_center_to_target

                name_i = "UAV" + str(i + 1)
                pos_i = self.get_UAV_pos(vehicle_name=name_i)

                # Calculate the desired velocity for each UAV to reach its formation point
                v_mig = self.k_mig * (formation_point - pos_i)
                N_i = 0

                # Perform collision avoidance with other drones
                for j in range(self.num_uavs):
                    if j != i:
                        N_i += 1
                        name_j = "UAV" + str(j + 1)
                        pos_j = self.get_UAV_pos(vehicle_name=name_j)
                        if np.linalg.norm(pos_j - pos_i) < self.r_max:
                            v_sep, v_coh, v_rep = self.compute_forces(pos_i, pos_j, 10, 3, True)
                            self.v_sep += v_sep
                            self.v_coh += v_coh
                            self.v_rep += v_rep * 2

                self.v_sep /= N_i
                self.v_coh /= N_i
                self.v_rep /= N_i

                self.v_cmd[:, i:i + 1] = self.v_sep + self.v_coh + self.v_rep + v_mig
                if np.linalg.norm(self.v_cmd[:, i:i + 1]) > self.v_max:
                    self.v_cmd[:, i:i + 1] = self.v_max * self.v_cmd[:, i:i + 1] / np.linalg.norm(self.v_cmd[:, i:i + 1])
                
            # Set the velocity for each UAV
            for i in range(self.num_uavs):
                name_i = "UAV" + str(i + 1)
                self.client.moveByVelocityZAsync(self.v_cmd[0, i], self.v_cmd[1, i], self.z_cmd, 0.1, vehicle_name=name_i)
                