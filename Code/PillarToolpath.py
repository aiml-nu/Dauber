# This code generates a pillar toolpath for Dauber, controlled by the Centroid Acorn.

import argparse
import sys
import os
pi = 3.14159

parser = argparse.ArgumentParser(prog='pillarToolpath',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
# --- Invariants ---
parser.add_argument('-ah', '--approach_height',     help='Height above surface to rapid to when program starts, should be above any screws, [mm]',      type=float, default=20.0)
parser.add_argument('-ad', '--approach_duration',   help='Duration over which to approach the layer height, [s]',                                       type=float, default=30.0)
parser.add_argument('-wd', '--wire_diameter',       help='Diameter of the feedstock wire, [mm]',                                                        type=float, default=0.9)
parser.add_argument('-dd', '--deposition_diameter', help='Estimated diameter of deposition area, [mm]',                                                 type=float, default=4.0)

# --- Process Parameters ---
parser.add_argument('-ph', '--pillar_height',       help='Height of the pillar, [mm]',                                                                  type=float, default=10.0)
parser.add_argument('-fr', '--feed_rate',           help='Wire feed rate, [mm/s]',                                                                      type=float, default=1.0)
parser.add_argument('-ss', '--spindle_speed',       help='Spindle speed, [rpm]',                                                                        type=int,   default=24000)
parser.add_argument('-ip', '--initial_pause',       help='Time spent paused at zero height, [s]',                                                       type=float, default=5.0)

# --- Sample ID ---
parser.add_argument('-sn', '--sample_num',           help='Unique sample number in XXX format (e.g. 006)',                                              type=int,   default=999)
args = parser.parse_args()

sample_id = 'DEP-P-' + str(args.sample_num).zfill(3)
filename = sample_id + '.nc'
output =  '; Sample ID:           {} \n'.format(sample_id)
output += '; ~~~ Arguments used for gcode generation ~~~\n'
output += '; Approach Height:     {:7.2f} [mm] \n'.format(args.approach_height)
output += '; Approach Duration:   {:7.2f} [s] \n'.format(args.approach_duration)
output += '; Wire Diameter:       {:7.2f} [mm] \n'.format(args.wire_diameter)
output += '; Deposition Diameter: {:7.2f} [mm] \n'.format(args.deposition_diameter)
output += '; pillar Height:       {:7.2f} [mm] \n'.format(args.pillar_height)
output += '; Wire Feed Rate:      {:7.2f} [mm/s] \n'.format(args.feed_rate)
output += '; Spindle Speed        {:7.0f} [rpm] \n'.format(args.spindle_speed)
output += '; Initial Pause:       {:7.2f} [s] \n'.format(args.initial_pause)

current_height = 0 # Tool position in Z axis, [mm]
current_feed = 0   # Wire position in feeder, [mm]

deposition_area = pi * args.deposition_diameter ** 2 / 4 # Area of deposition under the nozzle
wire_area = pi * args.wire_diameter ** 2 / 4             # Cross-sectional area of the wire, [mm^2]
wire_volumetric_rate = args.feed_rate * wire_area        # Volumetric rate of wire addition, [mm^3 s^-1]

climb_feed_volume = deposition_area * args.pillar_height  # Volume to be filled for the entire pillar, [mm^3]
climb_feed_length = climb_feed_volume / wire_area         # Length of material fed while changing layer, [mm]
climb_time = climb_feed_volume / wire_volumetric_rate     # Time taken to feed the wire while changing layer, [s]
climb_rate = args.pillar_height / climb_time * 60          # Linear feedrate shown on the controller, [mm/min]

total_time = (climb_time + args.initial_pause + args.approach_duration) / 60 # Total time for deposition, [min]

output += '; ~~~ Calculated Values ~~~\n'
output += '; Climb rate:          {:7.2f} [mm/min] \n'.format(climb_rate)
output += '; Total time:          {:7.2f} [min] \n\n'.format(total_time)

output += 'G17 ; Select XY plane for circular interpolation \n'
output += 'G21 ; Select metric units of [mm] \n'
output += 'G54 ; Select G54 Work Coordinate System \n'
output += 'G90 ; Absolute positioning mode \n\n' 
output += 'G92 C0.0 ; Reset the C axis to zero \n' 
output += 'G0 Z{:.2f} ; Rapid to the approach height \n'.format(args.approach_height) 
output += 'G0 X0.0 Y0.0; Rapid to the start of the pillar in XY \n'
output += 'M3 S{} ; Start the spindle \n'.format(args.spindle_speed)
output += 'G93 ; Turn on Inverse Time mode \n\n'
output += 'G1 Z0.0 F{:.2f} ; Feed down to the substrate in Z \n'.format(60/args.approach_duration)
output += 'G4 P{:.2f} ; Pause at zero height \n'.format(args.initial_pause)
current_height += args.pillar_height
current_feed += climb_feed_length
output += 'G1 Z{:.2f} C{:.2f} F{:.2f} ; Move up to the pillar height while feeding \n'.format(current_height, current_feed, 60/climb_time)
output += '\nG94 ; Turn off Inverse Time mode \n'
output += 'G91 ; Relative positioning mode \n\n' 
output += 'G1 Z15.0 C10.0 F60.0; Move up while extruding \n'
output += 'M05 ; Turn off spindle'

with open(filename,'w') as file:
    file.write(output)