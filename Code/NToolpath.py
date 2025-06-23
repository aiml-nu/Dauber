# This code generates an "N" toolpath for Dauber, controlled by the Centroid Acorn.

import argparse
import sys
import os
pi = 3.14159

parser = argparse.ArgumentParser(prog='NToolpath',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
# --- Invariants ---
parser.add_argument('-ah', '--approach_height',     help='Height above surface to rapid to when program starts, should be above any screws, [mm]',      type=float, default=20.0)
parser.add_argument('-ad', '--approach_duration',   help='Duration over which to approach the layer height, [s]',                                       type=float, default=30.0)
parser.add_argument('-wd', '--wire_diameter',       help='Diameter of the feedstock wire, [mm]',                                                        type=float, default=0.86)
parser.add_argument('-dd', '--deposition_diameter', help='Estimated diameter of deposition area, [mm]',                                                 type=float, default=3.5)

# --- Process Parameters ---
parser.add_argument('-vl', '--vertical_length',     help='Height of the N, [mm]',                                                                       type=float, default=10.0)
parser.add_argument('-hl', '--horizontal_length',   help='Distance between the two uprights of the N, [mm]',                                            type=float, default=10.0)
parser.add_argument('-nl', '--num_layers',          help='Number of layers to deposit, [unitless]',                                                     type=int,   default=100)
parser.add_argument('-fr', '--feed_rate',           help='Wire feed rate, [mm/s]',                                                                      type=float, default=1.0)
parser.add_argument('-lh', '--layer_height',        help='Height of tool tip above substrate or previous layer, [mm]',                                  type=float, default=0.05)
parser.add_argument('-ss', '--spindle_speed',       help='Spindle speed, [rpm]',                                                                        type=int,   default=24000)
parser.add_argument('-ip', '--initial_pause',       help='Whether to wait at zero height (True) or not (False) for use input to start',                 type=bool,  default=False)

# --- Sample ID ---
parser.add_argument('-sn', '--sample_num',           help='Unique sample number in XXX format (e.g. 006)',                                              type=int,   default=999)
args = parser.parse_args()

sample_id = 'DEP-N-' + str(args.sample_num).zfill(3)
filename = sample_id + '.nc'
output =  '; Sample ID:                {} \n'.format(sample_id)
output += '; ~~~ Arguments used for gcode generation ~~~\n'
output += '; Approach Height:            {:7.2f} [mm] \n'.format(args.approach_height)
output += '; Approach Duration:          {:7.2f} [s] \n'.format(args.approach_duration)
output += '; Wire Diameter:              {:7.2f} [mm] \n'.format(args.wire_diameter)
output += '; Deposition Diameter:        {:7.2f} [mm] \n'.format(args.deposition_diameter)
output += '; Vertical Length:            {:7.2f} [mm] \n'.format(args.vertical_length)
output += '; Horizontal Length:          {:7.2f} [mm] \n'.format(args.horizontal_length)
output += '; Number of Layers:           {:7.0f} [unitless] \n'.format(args.num_layers)
output += '; Wire Feed Rate:             {:7.2f} [mm/s] \n'.format(args.feed_rate)
output += '; Layer Height:               {:7.2f} [mm] \n'.format(args.layer_height)
output += '; Spindle Speed:              {:7.0f} [rpm] \n'.format(args.spindle_speed)
output += '; Initial Preheating Pause:      {} \n'.format(args.initial_pause)

current_height = 0 # Tool position in Z axis, [mm]
current_feed = 0   # Wire position in feeder, [mm]

deposition_area = pi * args.deposition_diameter ** 2 / 4 # Area of deposition under the nozzle
wire_area = pi * args.wire_diameter ** 2 / 4             # Cross-sectional area of the wire, [mm^2]
wire_volumetric_rate = args.feed_rate * wire_area        # Volumetric rate of wire addition, [mm^3 s^-1]

climb_feed_volume = deposition_area * args.layer_height # Volume to be filled while the tool is moving up one layer in Z, [mm^3]
climb_feed_length = climb_feed_volume / wire_area       # Length of material fed while changing layer, [mm]
climb_time = climb_feed_volume / wire_volumetric_rate   # Time taken to feed the wire while changing layer, [s]
climb_rate = args.layer_height / climb_time * 60        # Linear feedrate shown on the controller, [mm/min]

vertical_feed_volume = args.vertical_length * args.deposition_diameter * args.layer_height # Volume to be filled while the tool is making the vertical part of the N, [mm^3]
vertical_feed_length = vertical_feed_volume / wire_area                                    # Length of material fed, [mm]
vertical_time = vertical_feed_volume / wire_volumetric_rate                                # Time taken to feed the wire, [s]
vertical_rate = args.vertical_length / vertical_time * 60                                  # Linear feedrate shown on the controller, [mm/min]

diagonal_length = (args.vertical_length**2 + args.horizontal_length**2)**0.5          # Diagonal length of the N, [mm]
diagonal_feed_volume = diagonal_length * args.deposition_diameter * args.layer_height # Volume to be filled while the tool is making the diagonal part of the N, [mm^3]
diagonal_feed_length = diagonal_feed_volume / wire_area                               # Length of material fed, [mm]
diagonal_time = diagonal_feed_volume / wire_volumetric_rate                           # Time taken to feed the wire, [s]
diagonal_rate = diagonal_length / diagonal_time * 60                             # Linear feedrate shown on the controller, [mm/min]

escape_feed_length = 10                           # Length of wire to feed while escaping, [mm]
escape_time = escape_feed_length / args.feed_rate # Time taken to feed the wire while escaping, [s]
escape_travel = 20                                # How far the Z axis should move upward while escaping, [mm]

total_time = (args.approach_duration + args.num_layers * (2 * vertical_time + diagonal_time + climb_time)) / 60 # Total time for deposition, [min]

output += '; ~~~ Calculated Values ~~~\n'
output += '; Wire Feed Rate:             {:7.2f} [mm/min] \n'.format(args.feed_rate*60)
output += '; Vertical Rate:              {:7.2f} [mm/min] \n'.format(vertical_rate)
output += '; Diagonal Rate:              {:7.2f} [mm/min] \n'.format(diagonal_rate)
output += '; Climb Rate:                 {:7.2f} [mm/min] \n'.format(climb_rate)
output += '; Total Time:                 {:7.2f} [min] \n\n'.format(total_time)

output += 'G17 ; Select XY plane for circular interpolation \n'
output += 'G21 ; Select metric units of [mm] \n'
output += 'G54 ; Select G54 Work Coordinate System \n'
output += 'G90 ; Absolute positioning mode \n\n' 
output += 'G92 C0.0 ; Reset the C axis to zero \n' 
output += 'G0 Z{:.2f} ; Rapid to the approach height \n'.format(args.approach_height) 
output += 'G0 X{:.2f} Y{:.2f} ; Rapid to the start of the N in XY \n'.format(-args.horizontal_length/2, -args.vertical_length/2) 
output += 'M3 S{} ; Start the spindle \n'.format(args.spindle_speed)
output += 'G93 ; Turn on Inverse Time mode \n'
output += '\nG1 Z0.0 F{:.2f} ; Feed down to the substrate in Z \n'.format(60/args.approach_duration)
if (args.initial_pause): 
    output += 'M0 ; Pause for operator to allow preheating \n'
output += 'G1 X{:.2f} Y{:.2f} C{:.2f} F{:.2f} ; Move up the left vertical of the N \n'.format(-args.horizontal_length/2, args.vertical_length/2, current_feed, 60/vertical_time)
output += 'G1 X{:.2f} Y{:.2f} C{:.2f} F{:.2f} ; Move down across the diagonal of the N \n'.format(args.horizontal_length/2, -args.vertical_length/2, current_feed, 60/diagonal_time)
output += 'G1 X{:.2f} Y{:.2f} C{:.2f} F{:.2f} ; Move up the right vertical of the N \n'.format(args.horizontal_length/2, args.vertical_length/2, current_feed, 60/vertical_time)
current_feed += climb_feed_length
current_height += args.layer_height
output += 'G1 Z{:.2f} C{:.2f} F{:.2f} ; Move up one layer height while feeding \n'.format(current_height, current_feed, 60/climb_time)
direction = False # If true, then we are starting at the lower left, if false, starting at the upper right
for i in range(args.num_layers):
    if (direction): 
        current_feed += vertical_feed_length
        output += 'G1 X{:.2f} Y{:.2f} C{:.2f} F{:.2f} ; Move up the left vertical of the N \n'.format(-args.horizontal_length/2, args.vertical_length/2, current_feed, 60/vertical_time)
        current_feed += diagonal_feed_length
        output += 'G1 X{:.2f} Y{:.2f} C{:.2f} F{:.2f} ; Move down across the diagonal of the N \n'.format(args.horizontal_length/2, -args.vertical_length/2, current_feed, 60/diagonal_time)
        current_feed += vertical_feed_length
        output += 'G1 X{:.2f} Y{:.2f} C{:.2f} F{:.2f} ; Move up the right vertical of the N \n'.format(args.horizontal_length/2, args.vertical_length/2, current_feed, 60/vertical_time)
        direction = not direction
    else:
        current_feed += vertical_feed_length
        output += 'G1 X{:.2f} Y{:.2f} C{:.2f} F{:.2f} ; Move down the right vertical of the N \n'.format(args.horizontal_length/2, -args.vertical_length/2, current_feed, 60/vertical_time)
        current_feed += diagonal_feed_length
        output += 'G1 X{:.2f} Y{:.2f} C{:.2f} F{:.2f} ; Move up across the diagonal of the N \n'.format(-args.horizontal_length/2, args.vertical_length/2, current_feed, 60/diagonal_time)
        current_feed += vertical_feed_length
        output += 'G1 X{:.2f} Y{:.2f} C{:.2f} F{:.2f} ; Move down the left vertical of the N \n'.format(-args.horizontal_length/2, -args.vertical_length/2, current_feed, 60/vertical_time)
        direction = not direction
    if (i < args.num_layers-1):
        current_feed += climb_feed_length
        current_height += args.layer_height
        output += 'G1 Z{:.2f} C{:.2f} F{:.2f} ; Move up one layer height while feeding \n'.format(current_height, current_feed, 60/climb_time)
output += '\nG91 ; Relative positioning mode \n' 
output += 'G1 Z{:.2f} C{:.2f} F{:.2f} ; Move up while extruding \n'.format(escape_travel, escape_feed_length, 60/escape_time)
output += 'G94 ; Turn off Inverse Time mode \n'
output += 'M05 ; Turn off spindle'

with open(filename,'w') as file:
    file.write(output)