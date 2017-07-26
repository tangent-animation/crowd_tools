import os, sys
from typing import Optional, List, Union

import bpy
context = bpy.context
scene = context.scene


def convert_guide_single(
		ps:bpy.types.ParticleSystem, index:int,
		name:Optional[str]=None,
		) -> Optional[bpy.types.Curve]:
	"""
	Converts a single indexed guide hair from the specified particle
	system into a Blender curve.

	:param ps: The Blender ParticleSystem to convert.
	:returns: A single curve for guide[index], or None on failure.
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
		name = 'crvguide.{}.{:03d}'.format( base_name, index )
		print( name )

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

	return ob


def do_conversion( ps:Union[str,bpy.types.ParticleSystem] ) -> List[bpy.types.Curve]:
	"""
	Converts the specified particle system combed hair guides
	into bezier guide curves with 'vector' handles (linear curves).

	:param ps: The Blender ParticleSystem to convert.
	:returns: a list of Curves, one for each of the converted groom hairs.
	"""

