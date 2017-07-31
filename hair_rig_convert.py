import os, sys
from typing import Optional, List, Union

import bpy
context = bpy.context
scene = context.scene

import mathutils
from mathutils import Vector, Matrix


## ======================================================================
def find_particle_system( name:Union[str,bpy.types.ParticleSystem] ) -> bpy.types.ParticleSystem:
	"""
	Particle systems aren't in bpy.data; you have to search through
	objects for them.

	:param name: Name of the system to search for. If a ParticleSystem object
				is passed in, it will be directly returned.
	:returns: The system, or None on error.
	"""

	if isinstance(name, bpy.types.ParticleSystem):
		return name

	particle_objects = [ x for x in scene.objects if len(x.particle_systems) ]
	for item in particle_objects:
		for system in item.particle_systems:
			if system.name == name:
				return system

	return None


## ======================================================================
def find_particle_object( name:Union[str,bpy.types.ParticleSystem] ) -> bpy.types.Object:
	"""
	Search through bpy.data.objects for the first object to which
	the specified ParticleSystem belongs.

	:param name: Name of the system to search for. If a ParticleSystem object
				is passed in, it will be directly returned.
	:returns: The system, or None on error.
	"""

	if isinstance(name, bpy.types.ParticleSystem):
		return name

	particle_objects = [ x for x in scene.objects if len(x.particle_systems) ]
	for item in particle_objects:
		for system in item.particle_systems:
			if system.name == name:
				return system

	return None


## ======================================================================
"""
Curve Conversion Functions

They're now deprecated because as useful as they are, you can't
animate them as final deformed curve positons aren't available
from Python to use to drive the guide hairs.
"""
## ======================================================================

def convert_guide_single(
		ps:bpy.types.ParticleSystem, index:int,
		name:Optional[str]=None,
		) -> bpy.types.Curve:
	"""
	Converts a single indexed guide hair from the specified particle
	system into a Blender curve.

	:param ps: The Blender ParticleSystem to convert.
	:returns: A single curve for guide[index], or None on failure.
	:throws: ValueError
	"""

	p = ps.particles
	particle_count = len( p )

	if particle_count == 0:
		raise ValueError( 'convert_guide_single: Zero guide hairs on particle system "{}"'.format(ps.name) )

	hair_key_count = len( p[0].hair_keys )
	base_name = ps.name.split('.')[1]

	if not sorted([0, index, particle_count-1])[1] == index:
		raise ValueError( 'convert_guide_single: Index {} is out of bounds ({} total guide hairs)'.format(index, particle_count) )

	if name is None:
		real_index = index
		name = 'crvguide.{}.{:03d}'.format( base_name, real_index )
		while name in bpy.data.objects:
			real_index += 1
			name = 'crvguide.{}.{:03d}'.format( base_name, real_index )
	
	print( 'Attempting to create guide "{}".'.format(name) )

	curve_data = bpy.data.curves.new( name, type='CURVE' )
	curve_data.dimensions = '3D'
	curve_data.use_path = True
	spline = curve_data.splines.new( type='POLY' )
	
	## -1 here because the default spline comes in with a point?
	spline.points.add( hair_key_count - 1 )

	for point, hair_key in zip( spline.points, p[index].hair_keys ):
		point.co = hair_key.co.to_4d()

	ob = bpy.data.objects.new( name, curve_data )
	scene.objects.link( ob )

	ob.select = True
	# ob.hide = ob.hide_render = True
	scene.objects.active = ob

	return ob


def attach_driver_guide( system:bpy.types.ParticleSystem, curve:bpy.types.Object, index ):
	"""
	Creates the driver setup on the particle system.

	This looks for an Action block, and if one is not found 
	one is created to hold the drivers.
	:param system:  The Blender ParticleSystem to drive.
	:param curve: The curve object to add as a driver.
	:param index: The index of the guide hair in the ParticleSystem to drive.

	No return value.
	:raises: ValueError
	"""

	if not curve.data or not isinstance(curve.data, bpy.types.Curve):
		raise ValueError( 'attach_driver_guide: "curve" parameter must be a Curve object.' )
	
	base_name = system.name.split('.')[1]

	## the drivers have to be on the object, I think
	## so find the object first-- should only be one
	users = bpy.data.user_map()[system.settings]
	if not len(users) == 1:
		raise ValueError( 'attach_driver_guide: User count for "{}" is not exactly one.'.format(ps.name) )
	
	## it's a set-- have to convert to index
	ob = list(users)[0]

	if ob.animation_data is None:
		ob.animation_data_create()

	##!FIXME: Should I be doing this here, or outside?
	if ob.animation_data.action is None:
		action_name = 'DO_NOT_TOUCH__act.{}.000'.format( base_name )
		action = bpy.data.actions.new( action_name )
		ob.animation_data.action = action
	
	action = ob.animation_data.action

	system_index = [ x for x,y in enumerate(ob.particle_systems) if y.name == system.name ][0]

	print( 'Curve "{}" {}\t>>\t"{}": "{}" ({})'.format(curve.name, index, ob.name, system.name, system_index) )

	## hair keys aren't accessible outside of particle mode
	scene.objects.active = ob

	# mode = bpy.context.mode
	# if not mode == 'PARTICLE':
	# 	bpy.ops.particle.particle_edit_toggle()

	## connect away
	## for each object, you need to do a driver per point, 
	## per axis from curve -> guide curve
	base_particles_path = 'particle_systems["{}"].particles[{}]'.format(system.name, index) + '.hair_keys[{}].co'
	base_bone_path    = 'data.splines[0].points[{}].co[{}]'

	particle = system.particles[index]
	spline   = curve.data.splines[0]

	for index in range( len(particle.hair_keys) ):
		for array_index in range(3):
			data_path = base_particles_path.format(index, array_index)

			## clear first
			try:
				ob.driver_remove( data_path, array_index )
			except TypeError:
				pass

			fcurve = ob.driver_add( data_path, array_index )
			# fcurve.driver.type = 'SCRIPTED'
			## 'SUM' shouldn't use Python, so it should be faster since
			## we're only looking at single variable direct connections
			fcurve.driver.type = 'SUM'

			for mod in fcurve.modifiers:
				fcurve.modifiers.remove( mod )
	
			var = fcurve.driver.variables.new()
			var.name = 'p'
			var.type = 'SINGLE_PROP'
			var.targets[0].id = curve

			target_path = base_bone_path.format( index, array_index )
			var.targets[0].data_path = target_path

			fcurve.driver.show_debug_info = True
			fcurve.driver.expression = 'p'

			## have to have keys properly spaced out
			kp = fcurve.keyframe_points
			for key_index in range(2):
				kp.add()
				kp[key_index].co = [1*key_index] * 2
				kp[key_index].interpolation = 'LINEAR'

			fcurve.update()

			## without this, the driving will be limited
			## to ( 0 ~ 1 )
			fcurve.extrapolation = 'LINEAR'
			fcurve.update()


def do_curve_conversion( system:Union[str,bpy.types.ParticleSystem] ) -> List[bpy.types.Curve]:
	"""
	Converts the specified particle system combed hair guides
	into bezier guide curves with 'vector' handles (linear curves).

	:param system: The Blender ParticleSystem to convert.
	:returns: a list of Curves, one for each of the converted groom hairs.
	"""

	result = []

	if isinstance( system, str ):
		ps = find_particle_system( system )
	else:
		ps = system
	
	if ps is None:
		raise ValueError( 'Particle system "{}" not found.'.format(system) )

	## detach any incoming fields; they're really not compatible
	ps.settings.effector_weights.all   = 0.0
	ps.settings.effector_weights.group = None

	curve_count = len( ps.particles )

	for index in range( curve_count ):
		curve = convert_guide_single(ps, index)
		attach_driver_guide( ps, curve, index )
		result.append( curve )
	
	return result


## ======================================================================
"""
Armature Conversion Functions

They're now deprecated because as useful as they are, you can't
animate them as final deformed curve positons aren't available
from Python to use to drive the guide hairs.
"""
## ======================================================================

def attach_driver_chain( system:bpy.types.ParticleSystem, chain:List[bpy.types.PoseBone], index ):
	"""
	Creates the driver setup on the particle system, attaching the specified chain
	of bones to the guide hair specified by index.

	This looks for an Action block, and if one is not found 
	one is created to hold the drivers.

	:param system: The Blender ParticleSystem to drive.
	:param chain:  The chain of PoseBones that should be used to drive the guide hair.
	:param index:  The index of the guide hair in the ParticleSystem to drive.

	No return value.
	:raises: ValueError
	"""

	if not isinstance(chain, (list, tuple)):
		raise ValueError( '"chain" parameter must be a list of PoseBones.' )
	
	chain_length = len( chain )

	if not sum( [ 1 for x in chain if isinstance(x, bpy.types.PoseBone)] ) == chain_length:
		raise ValueError( '"chain" contains items that are not PoseBones.' )
	
	target_hair = system.particles[index]
	target_hair_length = len(target_hair.hair_keys)
	if not chain_length == target_hair_length:
		raise ValueError( 'chain length ({}) does not match guide hair length ({}).'.format(chain_length, target_hair_length-1) )

	base_name = system.name.split('.')[1]

	## the drivers have to be on the object, I think
	## so find the object first-- should only be one
	users = bpy.data.user_map()[system.settings]
	if not len(users) == 1:
		raise ValueError( 'attach_driver_guide: User count for "{}" is not exactly one.'.format(system.name) )
	
	## it's a set-- have to convert to index
	ob = list(users)[0]

	if ob.animation_data is None:
		ob.animation_data_create()

	##!FIXME: Should I be doing this here, or outside?
	if ob.animation_data.action is None:
		action_name = 'DO_NOT_TOUCH__act.{}.000'.format( base_name )
		action = bpy.data.actions.new( action_name )
		ob.animation_data.action = action

	action = ob.animation_data.action
	scene.objects.active = ob

	## connect away
	## for each object, you need to do a driver per 
	## point, per axis from bone -> guide curve cv
	base_particles_path = 'particle_systems["{}"].particles[{}]'.format(system.name, index) + '.hair_keys[{}].co'
	base_bone_path      = 'pose.bones["{}"].matrix.translation[{}]'

	armature = chain[0].id_data

	for index in range( target_hair_length ):
		bone = chain[index]

		for array_index, transform_type in zip( range(3), ('LOC_X', 'LOC_Y', 'LOC_Z') ):
			data_path = base_particles_path.format(index, array_index)

			## clear first
			try:
				ob.driver_remove( data_path, array_index )
			except TypeError:
				pass

			fcurve = ob.driver_add( data_path, array_index )
			# fcurve.driver.type = 'SCRIPTED'
			## 'SUM' shouldn't use Python, so it should be faster since
			## we're only looking at single variable direct connections
			fcurve.driver.type = 'SUM'

			for mod in fcurve.modifiers:
				fcurve.modifiers.remove( mod )
	
			var = fcurve.driver.variables.new()
			var.name = 'p'
			# var.type = 'SINGLE_PROP'
			var.type = 'TRANSFORMS'
			var.targets[0].id = armature
			var.targets[0].bone_target = bone.name
			var.targets[0].transform_space = 'WORLD_SPACE'
			var.targets[0].transform_type = transform_type

			target_path = base_bone_path.format( bone.name, array_index )
			var.targets[0].data_path = target_path

			fcurve.driver.show_debug_info = True
			fcurve.driver.expression = 'p'

			## have to have keys properly spaced out
			kp = fcurve.keyframe_points
			for key_index in range(2):
				kp.add()
				kp[key_index].co = [1*key_index] * 2
				kp[key_index].interpolation = 'LINEAR'

			fcurve.update()

			## without this, the driving will be limited
			## to ( 0 ~ 1 )
			fcurve.extrapolation = 'LINEAR'
			fcurve.update()


def build_chain_single(
		ps:bpy.types.ParticleSystem, index:int,
		armature:bpy.types.Armature,
		) -> List[bpy.types.PoseBone]:
	"""
	Converts a single indexed guide hair from the specified particle
	system into a chain of bones in the specified Armature.

	:param ps:       The Blender ParticleSystem to convert.
	:param index:    The index of the guide hair particle to use.
	:param Armature: The Armature in which to create the new bones.
	:returns: A single curve for guide[index], or None on failure.
	:throws: ValueError
	"""

	p = ps.particles
	particle_count = len( p )

	if particle_count == 0:
		raise ValueError( 'convert_guide_single: Zero guide hairs on particle system "{}"'.format(ps.name) )

	if not sorted([0, index, particle_count-1])[1] == index:
		raise ValueError( 'convert_guide_single: Index {} is out of bounds ({} total guide hairs)'.format(index, particle_count) )

	hair_key_count = len( p[0].hair_keys )
	base_name = ps.name.split('.')[1]

	base_bone_name  = 'guide.{}_{:03d}'.format(ps.name, index) + '.{:03d}'
	all_points = [ x.co.copy() for x in p[index].hair_keys ]

	## for that last bone
	all_points.append( (all_points[-1] - all_points[-2]) + all_points[-1] )

	edit_bones = []
	bone_names = []
	armature.hide = armature.hide_select = False
	scene.objects.active = armature

	bpy.ops.object.mode_set( mode='OBJECT' )
	scene.update()
	bpy.ops.object.mode_set( mode='EDIT' )

	root_bone = armature.data.edit_bones[ 'root' ]

	for index in range(hair_key_count):
		bone = armature.data.edit_bones.new( base_bone_name.format(index) )
		if len(edit_bones):
			bone.parent = edit_bones[-1]
		else:
			bone.parent = root_bone

		bone.head = all_points[index]
		bone.tail = all_points[index+1]

		edit_bones.append( bone )
		bone_names.append( bone.name )

	armature.update_from_editmode()
	
	bpy.ops.object.mode_set( mode='POSE' )
	## avoid a crash
	del edit_bones

	result = [ armature.pose.bones[x] for x in bone_names ]
	return result

def make_bone( armature:bpy.types.Armature, name:str, head:Optional(Vector)=None, 
				tail:Optional(Vector)=None, up:Optional(Vector)=None,
				parent:Optional(bpy.types.EditBone) ) -> bpy.types.EditBone:
	"""
	Creates a new bone in the specified armature and returns the EditBone representing it.

	:param armature: The Armature data in which to create the new bone.
	:param name: Name of the new bone to create.
	:param head: If not None, the head position of the new bone.
	:param tail: If not None, the tail position of the new bone.
	:param up: If not None, the up vector of the new bone for roll calculation.
	:param parent: Parent EditBone of this new bone.
	:return: an EditBone.
	:throws: ValueError if head, tail, or up are not mathutils.Vectors, if the Armature is not in edit mode,
			or if a bone by the specified name already exists
	"""

	if not bpy.context.mode == 'EDIT':
		raise ValueError( 'Armature "{}" not in Edit mode.'.format(armature.name) )

	for vector in head, tail, up:
		if vector and not isinstance(vector, Vector):
			raise ValueError( 'head, tail, and up must be None or mathutils.Vector.' )

	if name in armature.edit_bones:
		raise ValueError( 'A bone named "{}" already exists in Armature "{}".'.format(name, armature.name) )

	if head is None:
		head = Vector( [0,0,0] )

	if tail is None:
		tail = Vector( [0,2,0] )

	bone = armature.edit_bones.new()

	## copies are here to protect against passing another bone.head or bone.tail
	bone.head = head.copy()
	bone.tail = tail.copy()

	if up:
		bone.align_roll( up )
	
	if parent:
		bone.parent = parent

	return bone


def do_armature_conversion( base_ob:bpy.types.Object, system:Union[str,bpy.types.ParticleSystem] ) -> bpy.types.Armature: 
	"""
	Converts the specified particle system combed hair guides
	into a series of bone chains for animated guide driving.

	:param base_ob: The object on which to look for the particle system
	:param system: The Blender ParticleSystem to convert.
	:returns: A new armature with a bone chain per guide curve hair, each chain
			containing a bone per guide hair CV
	"""

	result = []

	ps = find_particle_system( system )
	if ps is None:
		raise ValueError( 'Particle system "{}" not found.'.format(system) )

	## detach any incoming fields; they're really not compatible
	ps.settings.effector_weights.all   = 0.0
	ps.settings.effector_weights.group = None

	curve_count = len( ps.particles )

	## make the armature
	base_name = ps.name.split('.')[1]

	rig_name = 'rig.{}.000'.format( base_ob.name )
	arm_name = 'arm.{}.000'.format( base_ob.name )

	if not rig_name in bpy.data.objects:
		arm = bpy.data.armatures.new( arm_name )
		ob  = bpy.data.objects.new( rig_name, arm )
		scene.objects.link( ob )
	else:
		ob  = bpy.context.scene.objects[ rig_name ]
		ob.hide = False
		arm = ob.data

	ob.select = True
	scene.objects.active = ob

	## root bone
	bpy.ops.object.mode_set( mode='EDIT' )
	if not 'root' in arm.edit_bones:
		root_bone = arm.edit_bones.new( 'root' )
		root_bone.head = Vector( [0,0,0] )
		root_bone.tail = Vector( [0,2,0] )
		ob.update_from_editmode()

	for index in range( curve_count ):
		chain = build_chain_single( ps, index, ob )
		attach_driver_chain( ps, chain, index )

		result.append( chain )
	
	## bugfix: make sure the armature object itself is scaled up to match
	# scale = base_ob.world_matrix.to_scale()
	# ob.scale = scale

	ob.hide = True
	scene.update()

	return result

