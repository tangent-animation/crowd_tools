import bpy
context = bpy.context
scene = context.scene

action_name = 'HairAction'

if not action_name in bpy.data.actions:
	bpy.data.actions.new( action_name )

action = bpy.data.actions[ action_name ]

def clear_action( a ):
	while len( a.fcurves ):
		a.fcurves.remove( a.fcurves[-1] )

#clear_action( action )

ob = scene.objects['Cube']
ps = ob.particle_systems[0]

def set_key_on_frame( fcurve, frame, value ):
	the_key = None

	for key in fcurve.keyframe_points:
		if key.co[0] == float(frame):
			the_key = key
			break

	if the_key is None:
		fcurve.keyframe_points.add(1)
		fcurve.keyframe_points[-1].co = (frame, value)
	else:
		the_key.co = (frame, value)

def find_curve( index, cv, axis ):
	"""
	Finds a curve in the action block, or makes a new one
	:param index: the hair index
	:param cv: the cv index in the hair
	:param axis: the axis (x=0, y=1, z=2)
	"""

	path = 'particle_systems[0].particles[{}].hair_keys[{}].co'.format( index, cv )
	for fcurve in action.fcurves:
		if fcurve.data_path == path and fcurve.array_index == axis:
			return fcurve
	
	## if we're here, we need to make a new one
	return action.fcurves.new( path, axis )
	

def bake_curve( index ):
	path = 'particle_systems[0].particles[{}].hair_keys[{}].co'

	frame = scene.frame_current

	for cv in range( len(ps.particles[index].hair_keys) ) :
		fcX = find_curve( index, cv, 0 )
		fcY = find_curve( index, cv, 1 )
		fcZ = find_curve( index, cv, 2 )

		set_key_on_frame( fcX, frame, ps.particles[index].hair_keys[cv].co[0] )
		set_key_on_frame( fcY, frame, ps.particles[index].hair_keys[cv].co[1] )
		set_key_on_frame( fcZ, frame, ps.particles[index].hair_keys[cv].co[2] )

for index in range( len(ps.particles) ):
	bake_curve( index )

