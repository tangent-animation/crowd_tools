import math
import bpy, bmesh, mathutils
from mathutils import Vector, Matrix


## ======================================================================
def add_shape_key( ob:bpy.types.Object, name ):
	"""
	Adds a shapekey to the mesh. If the Basis key does not exist,
	it is created first.

	:param ob: The target Object on which to add the key. Assumes the object has mesh data.
	:param name: The name of the shape key.
	:returns: The created ShapeKey, or the original shape key by specified name if it
			 already exists.
	"""

	if ob.data.shape_keys is None or not 'Basis' in ob.data.shape_keys.key_blocks:
		basis = ob.shape_key_add( name='Basis', from_mix=False )
	else:
		basis = ob.data.shape_keys.key_blocks['Basis']
	
	# ob.data.shape_keys.use_relative = False

	if name == 'Basis':
		return basis

	if name in ob.data.shape_keys.key_blocks:
		return ob.data.shape_keys.key_blocks[name]
	else:
		result = ob.shape_key_add( name=name, from_mix=False )
		# result.relative_key = basis 
		return result


## ======================================================================
def bake_frame( ob:bpy.types.Object, frame:int, export_obj=None ):
	scene = bpy.context.scene
	
	shape_name = 'cache__F{:04d}'.format(frame)
	data_path = 'key_blocks["{}"].value'.format( shape_name )

	## clean out the old keys
	if ob.data.shape_keys.animation_data and ob.data.shape_keys.animation_data.action:
		action = ob.data.shape_keys.animation_data.action
		for curve in action.fcurves:
			if curve.data_path == data_path:
				action.fcurves.remove(curve)
				break

	scene.frame_set( frame )

	mesh = ob.to_mesh( scene, apply_modifiers=True, settings="RENDER" )
	shape = add_shape_key( ob, shape_name )

	for index in range( len(ob.data.vertices) ):
		shape.data[index].co = mesh.vertices[index].co

	## this keys them on for the duration of the animation
	shape.value = 0.0
	ob.data.shape_keys.keyframe_insert( data_path, frame=frame-1 )
	shape.value = 1.0
	ob.data.shape_keys.keyframe_insert( data_path, frame=frame )
	shape.value = 0.0
	ob.data.shape_keys.keyframe_insert( data_path, frame=frame+1 )

	if export_obj:
		## the blender OBJ importer adjusts for Y up in other packages
		## so rotate the mesh here before export
		rotate_mat = mathutils.Matrix.Rotation(-math.pi/2, 4, 'X')
		mesh.transform( rotate_mat )

		## man the OBJ format is simple. No wonder people love it.
		print( '+ Exporting frame {} to "{}"'.format(frame, export_obj) )
		with open( export_obj, 'w' ) as fp:
			for v in mesh.vertices:
				fp.write( 'v {:6f} {:6f} {:6f}\n'.format(v.co[0], v.co[1], v.co[2]) )

			## smoothing
			# fp.write( 's 1\n' )

			for f in mesh.polygons:
				msg = "f"
				for v in f.vertices:
					msg += ' {:d}'.format(v+1)
				msg += '\n'
				fp.write( msg )

			## one extra line at the end
			fp.write( '\n' )

	bpy.data.meshes.remove( mesh )


## ======================================================================
def clear_shape_keys( ob:bpy.types.Object ):
	if not ob.data.shape_keys:
		return

	keys = ob.data.shape_keys.key_blocks
	for key in keys:
		ob.shape_key_remove( key )
	

## ======================================================================
def bake_to_shape_keys( ob:bpy.types.Object, start_frame=None, end_frame=None,
		export_path=None ):
	"""
	Steps through the timeline from start_frame to end_frame and 
	bakes the final mesh to shape keys.

	:param ob: The target Object on which to add the cache keys.
				Assumes the object has mesh data.
	:param start_frame: The first frame to bake, inclusive.
	:param end_frame: The last frame to bake, inclusive.
	:param export_path: The path to export files, minus the frame and extension
	:returns: The number of frames baked, or 0 on error.
	"""

	scene = bpy.context.scene
	wm    = bpy.context.window_manager

	if start_frame is None:
		start_frame = scene.frame_start
	
	if end_frame is None:
		end_frame = scene.frame_end

	basis = add_shape_key( ob, 'Basis' )

	if start_frame > end_frame:
		return 0

	## disable subsurf
	disabled = {}
	for mod in ob.modifiers:
		if mod.type == 'SUBSURF':
			disabled[mod.name] = {
				'show_render': mod.show_render,
				'show_viewport': mod.show_viewport,
			}

			mod.show_render = mod.show_viewport = False

	wm.progress_begin( start_frame, end_frame+1 )
	for frame in range( start_frame, end_frame+1 ):
		wm.progress_update(frame)

		export_name = (export_path + '.{:04d}.obj'.format(frame)) if export_path else None
		bake_frame( ob, frame, export_obj=export_name )
		# bake_frame( ob, frame, export_name )

	wm.progress_end()

	for mod in ob.modifiers:
		mod.show_render = mod.show_viewport = False
	
	for key in ob.data.shape_keys.key_blocks:
		if not key.name.startswith('cache__') and not key.name.startswith('fix__'):
			key.mute = True

	## re-enable any subsurf modifiers
	for mod_name, values in disabled.items():
		for key, value in values.items():
			setattr( ob.modifiers[mod_name], key, value )

	print("Baked {} frames.".format(end_frame - start_frame + 1))
	return end_frame - start_frame + 1


"""
## ======================================================================
def bake_to_shape_keys( ob:bpy.types.Object, start_frame=None, end_frame=None,
			export_path=None ):

	bake_frame( ob, frame, export_obj=None )
"""
