# This code generates a linear toolpath for Dauber, controlled by the Centroid Acorn.

import argparse
import sys
import os
pi = 3.14159

parser = argparse.ArgumentParser(prog='LineToolpath',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
# --- Invariants ---
parser.add_argument('-ah', '--approach_height',     help='Height above surface to rapid to when program starts, should be above any screws, [mm]',      type=float, default=20.0)
parser.add_argument('-ad', '--approach_duration',   help='Duration over which to approach the layer height, [s]',                                       type=float, default=30.0)
parser.add_argument('-wd', '--wire_diameter',       help='Diameter of the feedstock wire, [mm]',                                                        type=float, default=0.9)
parser.add_argument('-dd', '--deposition_diameter', help='Estimated diameter of deposition area, [mm]',                                                 type=float, default=3.3)

# --- Process Parameters ---
parser.add_argument('-ll', '--line_length',         help='Length of the line, [mm]',                                                                    type=float, default=10.0)
parser.add_argument('-nl', '--num_layers',          help='Number of layers to deposit, [unitless]',                                                     type=int,   default=5)
parser.add_argument('-fr', '--feed_rate',           help='Wire feed rate, [mm/s]',                                                                      type=float, default=1.0)
parser.add_argument('-lh', '--layer_height',        help='Height of tool tip above substrate or previous layer, [mm]',                                  type=float, default=0.05)
parser.add_argument('-ss', '--spindle_speed',       help='Spindle speed, [rpm]',                                                                        type=int,   default=24000)
parser.add_argument('-lr', '--left_right',          help='Whether to start going left (True) or right (False)',                                         type=bool,  default=False)
parser.add_argument('-fp', '--first_pass',          help='Whether to do a blank first pass (True) or not (False) at zero height',                       type=bool,  default=False)
parser.add_argument('-ip', '--initial_pause',       help='Whether to wait at zero height (True) or not (False) for use input to start',                 type=bool,  default=False)

# --- Sample ID ---
parser.add_argument('-sn', '--sample_num',           help='Unique sample number in XXX format (e.g. 006)',                                              type=int,   default=999)
args = parser.parse_args()

sample_id = 'DEP-L-' + str(args.sample_num).zfill(3)
filename = sample_id + '.nc'
output =  '; Sample ID:                {} \n'.format(sample_id)
output += '; ~~~ Arguments used for gcode generation ~~~\n'
output += '; Approach Height:            {:7.2f} [mm] \n'.format(args.approach_height)
output += '; Approach Duration:          {:7.2f} [s] \n'.format(args.approach_duration)
output += '; Wire Diameter:              {:7.2f} [mm] \n'.format(args.wire_diameter)
output += '; Deposition Diameter:        {:7.2f} [mm] \n'.format(args.deposition_diameter)
output += '; Line Length:                {:7.2f} [mm] \n'.format(args.line_length)
output += '; Number of Layers:           {:7.0f} [unitless] \n'.format(args.num_layers)
output += '; Wire Feed Rate:             {:7.2f} [mm/s] \n'.format(args.feed_rate)
output += '; Layer Height:               {:7.2f} [mm] \n'.format(args.layer_height)
output += '; Spindle Speed:              {:7.0f} [rpm] \n'.format(args.spindle_speed)
output += '; Initial Pass Left-to-Right:    {} \n'.format(args.left_right)
output += '; Dummy First Pass:              {} \n'.format(args.first_pass)
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

traverse_feed_volume = args.line_length * args.deposition_diameter * args.layer_height # Volume to be filled while the tool is traversing in XY, [mm^3]
traverse_feed_length = traverse_feed_volume / wire_area                                # Length of material fed while traversing, [mm]
traverse_time = traverse_feed_volume / wire_volumetric_rate                            # Time taken to feed the wire while traversing, [s]
traverse_rate = args.line_length / traverse_time * 60                                  # Linear feedrate shown on the controller, [mm/min]

escape_feed_length = 10                           # Length of wire to feed while escaping, [mm]
escape_time = escape_feed_length / args.feed_rate # Time taken to feed the wire while escaping, [s]
escape_travel = 20                                # How far the Z axis should move upward while escaping, [mm]

total_time = (args.approach_duration + args.num_layers * (traverse_time + climb_time)) / 60 # Total time for deposition, [min]

if (args.left_right):
    direction = 1
else:
    direction = -1

output += '; ~~~ Calculated Values ~~~\n'
output += '; Wire Feed Rate:             {:7.2f} [mm/min] \n'.format(args.feed_rate*60)
output += '; Traverse Rate:              {:7.2f} [mm/min] \n'.format(traverse_rate)
output += '; Climb Rate:                 {:7.2f} [mm/min] \n'.format(climb_rate)
output += '; Total Time:                 {:7.2f} [min] \n\n'.format(total_time)

output += 'G17 ; Select XY plane for circular interpolation \n'
output += 'G21 ; Select metric units of [mm] \n'
output += 'G54 ; Select G54 Work Coordinate System \n'
output += 'G90 ; Absolute positioning mode \n\n' 
output += 'G92 C0.0 ; Reset the C axis to zero \n' 
output += 'G0 Z{:.2f} ; Rapid to the approach height \n'.format(args.approach_height) 
output += 'G0 X{:.2f} Y0.0 ; Rapid to the start of the line in XY \n'.format(-direction * args.line_length/2) 
output += 'M3 S{} ; Start the spindle \n'.format(args.spindle_speed)
output += 'G93 ; Turn on Inverse Time mode \n'
output += '\nG1 Z0.0 F{:.2f} ; Feed down to the substrate in Z \n'.format(60/args.approach_duration)
if (args.initial_pause): 
    output += 'M0 ; Pause for operator to allow preheating \n'
if (args.first_pass): 
    output += 'G1 X{:.2f} Y0.0 C{:.2f} F{:.2f} ; Blank pass \n'.format(direction * args.line_length/2, current_feed, 60/traverse_time)
    direction = direction * -1
current_height += args.layer_height
current_feed += climb_feed_length
output += '\nG1 Z{:.2f} C{:.2f} F{:.2f} ; Move up to layer 1 \n'.format(current_height, current_feed, 60/climb_time)
for i in range(args.num_layers):
    current_feed += traverse_feed_length
    output += 'G1 X{:.2f} Y0.0 C{:.2f} F{:.2f} ; Feed across layer {} \n'.format(direction * args.line_length/2, current_feed, 60/traverse_time, i+1)
    direction = direction * -1
    if i < args.num_layers-1:
        current_height += args.layer_height
        current_feed += climb_feed_length
        output = output + 'G1 Z{:.2f} C{:.2f} F{:.2f} ; Move up to layer {} \n'.format(current_height, current_feed, 60/climb_time, i+2)
output += '\nG91 ; Relative positioning mode \n' 
output += 'G1 Z{:.2f} C{:.2f} F{:.2f} ; Move up while extruding \n'.format(escape_travel, escape_feed_length, 60/escape_time)
output += 'G94 ; Turn off Inverse Time mode \n'
output += 'M05 ; Turn off spindle'

with open(filename,'w') as file:
    file.write(output)