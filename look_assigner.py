import os, re, sys

import bpy
from bpy.types import Object, Mesh, Armature


## ======================================================================
def clear_material_objects():
	context = bpy.context
	scene   = context.scene

	for ob in scene.objects:
		if ob.name.startswith( 'MTL__' ):
			scene.objects.unlink( ob )


## ======================================================================
def do_assign( file_name:str ):
	context = bpy.context
	scene   = context.scene

	if not os.path.exists( file_name ):
		raise ValueError( 'do_assign: File "{}" does not exist.'.format(file_name) )

	base_name = os.path.basename(file_name).partition(".")[0]
	print( "\n\n\n" + base_name + "\n\n" )

	if not base_name in bpy.data.groups:
		bpy.data.groups.new( base_name )
	ref_grp = bpy.data.groups[base_name]

	with bpy.data.libraries.load(file_name) as (data_from, data_to):
		data_to.objects = [ x for x in data_from.objects
							if x.startswith('geo') ]

	clear_material_objects()

	for ob in data_to.objects:
		item = bpy.data.objects.new( 'MTL__' + ob.name, ob.data )
		scene.objects.link( item )
		ref_grp.objects.link( item )

	## reattach
	name_match = re.compile( r"""(MTL__)?geo(\.|_)([A-Za-z0-9_]+)(\.[0-9]{3})?""" )

	def get_token( ob ):
		match = name_match.match( ob.name )
		if match:
			return match.group( 3 )
		return None

	def find_match( ob ):
		token = get_token( ob )
		print('Searching for matching token "{}"'.format(token))
		for target in [ x for x in scene.objects if x.name in ref_grp.objects ]:
			match_token = get_token( target )
			print( '\tTesting "{}" ("{}")...'.format(target.name, match_token) )
			if match_token == token:
				return target
		return None

	sel = [ x for x in scene.objects if x.select and not x.name == ref_grp.objects ]
	for item in sel:
		materials = item.data.materials
		materials.clear()

		match = find_match( item )
		if match:
			print( 'Found match for "{}": "{}".'.format(item.name, match.name) )
			for material in match.data.materials:
				materials.append( material )
			for index, target_face in enumerate( match.data.polygons ):
				item.data.polygons[index].material_index = target_face.material_index
		else:
			print( 'No match found for "{}".'.format(item.name) )

	clear_material_objects()
	bpy.data.groups.remove( ref_grp )

